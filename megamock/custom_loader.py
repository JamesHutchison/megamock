import inspect
import sys

from importlib.abc import Loader, MetaPathFinder

from megamock.import_references import References


class ReferenceTrackerFinder(MetaPathFinder):
    def __init__(self, finders):
        self._finders = finders

    def find_module(self, fullname, path=None):
        if path is None:
            return None
        for finder in self._finders:
            if hasattr(finder, "find_module"):
                if module := finder.find_module(fullname, path):
                    return ReferenceTrackerLoader(module)
        return None

    def find_spec(self, *args, **kwargs):
        for finder in self._finders:
            result = finder.find_spec(*args, **kwargs)
            if result is not None:
                result.loader = ReferenceTrackerLoader(result.loader)
                return result
        return None


class ReferenceTrackerLoader(Loader):
    def __init__(self, loader):
        self._loader = loader

    def create_module(self, *args, **kwargs):
        module = self._loader.create_module(*args, **kwargs)
        return module

    def exec_module(self, module, *args, **kwargs):
        self._loader.exec_module(module, *args, **kwargs)

        stack = inspect.stack()
        for frame in stack[2:]:
            if frame.code_context is None:
                continue
            calling_module = inspect.getmodule(frame[0])
            if calling_module:
                break
        assert calling_module
        if calling_module.__name__ == "importlib":
            return
        for k in dir(sys.modules[module.__name__]):
            References.add_reference(module, calling_module, k)
