import builtins
import inspect
import linecache
import os
import re
import sys
import time
from types import FrameType, ModuleType
from typing import Callable

from megamock.import_references import References

MEASURE_TIMES = os.environ.get("MEASURE_TIMES", "0") == "1"

orig_import = builtins.__import__

skip_modules = {
    "typing",
    "functools",
    "asttokens",
}

perf_stats = {
    "num_imports": 0,
    "total_orig_import": 0.0,
    "total_if_check": 0.0,
    "total_get_frame": 0.0,
    "total_reconstruct": 0.0,
    "total_renamed_to": 0.0,
    "total_add_reference": 0.0,
}
perf_start_time = 0.0


if MEASURE_TIMES:

    def measure_start() -> None:
        global perf_start_time
        perf_start_time = time.time()

    def measure(name: str) -> None:
        global perf_start_time
        perf_stats[name] += time.time() - perf_start_time

else:

    def measure_start() -> None:
        pass

    def measure(name: str) -> None:
        pass


pat = re.compile(r"^(\s*def\s)|(\s*async\s+def\s)|(.*(?<!\w)lambda(:|\s))|^(\s*@)")


def findsource(object):
    """
    A streamlined version of inspect.findsource
    """

    file = inspect.getsourcefile(object)
    if file:
        # Invalidate cache if needed.
        linecache.checkcache(file)
    else:
        file = inspect.getfile(object)
        # Allow filenames in form of "<something>" to pass through.
        # `doctest` monkeypatches `linecache` module to enable
        # inspection, so let `linecache.getlines` to be called.
        if not (file.startswith("<") and file.endswith(">")):
            raise OSError("source code not available")

    module = inspect.getmodule(object, file)
    if module:
        lines = linecache.getlines(file, module.__dict__)
    else:
        lines = linecache.getlines(file)
    if not lines:
        raise OSError("could not get source code")
    return lines


def _get_code_lines(frame: FrameType) -> tuple[list[str], int]:
    """
    Streamlined logic to get code lines from a frame
    """
    lines = findsource(frame)
    lineno = frame.f_lineno
    start = lineno - 1
    start = max(0, min(start, len(lines) - 1))
    code_lines = lines[start : start + 1]

    return code_lines, lineno


def _reconstruct_full_line(
    frame: FrameType, getline: Callable = linecache.getline
) -> str:
    """
    Given an import frame, reconstruct the full import line, which
    may span multiple lines of code via parenthesis or backslashes

    :param frame: The frame of the import
    :param getline: Pytest uses linecache.getline to rewrite assertions, so providing
        getline as a parameter for testing purposes
    """

    code_lines, lineno = _get_code_lines(frame)
    if code_lines:
        # if this is a multiline import, reconstruct the full line
        # the absense of '(' or '\' indicates a single line import
        next_line = code_lines[0]
        # note: timit gives 0.078569 for this vs 0.134779 for a compiled regex
        if "(" in next_line or "\\" in next_line:
            filename = frame.f_code.co_filename
            linenum = lineno + 1

            lines = [next_line]
            paren_count = next_line.count("(") - next_line.count(")")
            while paren_count > 0 or next_line.rstrip("\n\r").endswith("\\"):
                next_line = getline(filename, linenum)
                lines.append(next_line)
                paren_count -= next_line.count(")")
                linenum += 1
            return "".join(lines)
        return next_line
    return ""


has_rename_regex = re.compile(r"\s*from \S+ import.*\s+as\s", re.DOTALL)


def start_import_mod() -> None:
    """
    Start the import modification

    This should be done as one of the first things when testing
    """

    def new_import(*args, **kwargs) -> ModuleType:
        target_module: ModuleType | None = None
        calling_module: ModuleType | None = None
        frame: FrameType | None = None
        names: tuple[str] | None = None

        perf_stats["num_imports"] += 1
        measure_start()
        imported_module = orig_import(*args, **kwargs)
        measure("total_orig_import")

        measure_start()
        module_name = args[0]
        proceed = (
            module_name not in skip_modules
            and not module_name.startswith("_")  # skip private or C modules
            and (target_module := imported_module or sys.modules.get(module_name))
            and len(args) > 3
            and (names := args[3])
        )
        measure("total_if_check")
        if proceed:
            assert target_module is not None
            measure_start()
            for i in range(1, 5):
                frame = sys._getframe(i)
                if frame.f_code.co_name == "new_import":
                    continue
                calling_module = inspect.getmodule(frame)
                if calling_module:
                    break
            measure("total_get_frame")
            assert calling_module
            measure_start()
            assert frame
            full_line = _reconstruct_full_line(frame)
            measure("total_reconstruct")
            assert names
            for k in names:
                measure_start()
                if full_line and (
                    has_rename_regex.search(full_line)
                    and (
                        renamed_result := re.search(
                            rf"\s*from \S+ import.*{k}\s+as\s+(\w+)",
                            full_line,
                            re.DOTALL,
                        )
                    )
                ):
                    renamed_to = renamed_result.group(1)
                else:
                    renamed_to = k
                measure("total_renamed_to")
                measure_start()
                References.add_reference(target_module, calling_module, k, renamed_to)
                measure("total_add_reference")

        return imported_module

    builtins.__import__ = new_import
