import builtins
import sys
import inspect
from types import ModuleType

from megamock.import_references import References
from .megapatches import MegaPatch
from .megamocks import MegaMock
from .megas import Mega
from .type_util import Call

orig_import = builtins.__import__

skip_modules = {
    "typing",
    "functools",
    "asttokens",
}


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
            for k in names:
                References.add_reference(target_module, calling_module, k)

        return result

    builtins.__import__ = new_import


__all__ = [
    "Call",
    "Mega",
    "MegaMock",
    "MegaPatch",
    "start_import_mod",
    "UseRealLogic",
]
