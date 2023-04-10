import builtins
import inspect
import linecache
import re
import sys
from types import ModuleType
from typing import Callable

from megamock.import_references import References

orig_import = builtins.__import__

skip_modules = {
    "typing",
    "functools",
    "asttokens",
}


def _reconstruct_full_line(
    frame: inspect.FrameInfo, getline: Callable = linecache.getline
) -> str:
    """
    Pytest uses linecache.getline to rewrite assertions, so providing
    getline as a parameter for testing purposes
    """
    code_lines: list[str] | None = frame.code_context
    if code_lines:
        if re.search(r"[\\|\(]", code_lines[0]):
            # reconstruct the full line
            filename = frame.filename
            linenum = frame.lineno + 1

            lines = [code_lines[0]]
            paren_count = code_lines[0].count("(") - code_lines[0].count(")")
            next_line = code_lines[0]
            while paren_count > 0 or next_line.rstrip().endswith("\\"):
                next_line = getline(filename, linenum)
                lines.append(next_line)
                paren_count -= next_line.count(")")
                linenum += 1
            return "".join(lines)
        return code_lines[0]
    return ""


def start_import_mod() -> None:
    """
    Start the import modification

    This should be done as one of the first things when testing
    """

    def new_import(*args, **kwargs) -> ModuleType:
        result = orig_import(*args, **kwargs)

        module_name = args[0]
        if (
            module_name not in skip_modules
            and not module_name.startswith("_")
            and (target_module := sys.modules.get(module_name))
            and len(args) > 3
            and (names := args[3])
        ):
            stack = inspect.stack()
            for frame in stack:
                if frame.code_context is None:
                    continue
                if frame.function == "new_import":
                    continue
                calling_module = inspect.getmodule(frame[0])
                if calling_module:
                    break
            assert calling_module
            full_line = _reconstruct_full_line(frame)
            for k in names:
                if full_line and (
                    renamed_result := re.search(
                        rf"\s*from \S+ import.*{k}\s+as\s+(\w+)", full_line, re.DOTALL
                    )
                ):
                    renamed_to = renamed_result.group(1)
                else:
                    renamed_to = k
                References.add_reference(target_module, calling_module, k, renamed_to)

        return result

    builtins.__import__ = new_import
