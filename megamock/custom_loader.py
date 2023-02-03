import inspect
import sys

from importlib.abc import Finder, Loader, MetaPathFinder
import traceback
import types

from megamock.import_references import References


class WrappedObject:
    def __new__(cls, module, name, orig_obj):
        if orig_obj is None:
            return type(
                "WrappedNone",
                (cls,),
                {"__module": module, "__name": name, "_orig_obj": None},
            )
        return type(
            orig_obj.__class__.__name__,
            (orig_obj.__class__, cls),
            {"__module": module, "__name": name, "_orig_obj": orig_obj},
        )

    def __eq__(self, other):
        if isinstance(other, WrappedObject):
            return self._orig_obj == other._orig_obj
        return self._orig_obj == other

    def __lt__(self, other):
        if isinstance(other, WrappedObject):
            return self._orig_obj < other._orig_obj
        return self._orig_obj < other

    # def __init__(self, module, name, orig_obj):
    #     self.__initialized = False
    #     self.__module = module
    #     self.__name = name
    #     # self.__class__ = type(orig_obj)
    #     self._orig_obj = orig_obj
    #     # self.__name__ = type(orig_obj).__name__
    #     self.__initialized = True
    #     # for item in dir(obj):
    #     self.__dict__[item] = lambda:
    # self.__class__ = type(
    #     obj.__class__.__name__, (self.__class__, obj.__class__), {}
    # )
    # self._obj = obj
    # if hasattr(obj, "__dict__"):
    #     self.__dict__ = obj.__dict__

    @property
    def _obj(self):
        return getattr(self.__module, self.__name)._orig_obj

    def __getattr__(self, name):
        if name == "_orig_obj":
            return self.__dict__["_orig_obj"]
        return getattr(self._obj, name)

    def __setattr__(self, name, value):
        if True or (
            name != "_WrappedObject__initialized"
            and name != "_orig_obj"
            and self.__initialized
        ):
            setattr(self._obj, name, value)
        else:
            self.__dict__[name] = value

    def __call__(self, *args, **kwargs):
        return self._obj(*args, **kwargs)


class WrappedModule:
    def __init__(self, module):
        self._module = module
        for k, v in list(module.__dict__.items()):
            module.__dict__[k] = WrappedObject(module, k, v)

    # def __getattr__(self, name):
    #     return WrappedObject(getattr(self._module, name))


class WrapperFinder(MetaPathFinder):
    def __init__(self, finders):
        self._finders = finders

    def find_module(self, fullname, path=None):
        if path is None:
            return None
        for finder in self._finders:
            if hasattr(finder, "find_module"):
                if module := finder.find_module(fullname, path):
                    # module = self._finder.find_module(fullname, path)
                    # if module is None:
                    #     return None
                    return WrapperLoader(module)
        return None

    def find_spec(self, *args, **kwargs):
        for finder in self._finders:
            try:
                if isinstance(args[1], WrappedObject):
                    args = (args[0], args[1]._obj) + args[2:]
                result = finder.find_spec(*args, **kwargs)
            except Exception as exc:
                pass
                raise
            if result is not None:
                result.loader = WrapperLoader(result.loader)
                return result
        return None


class WrapperLoader(Loader):
    def __init__(self, loader):
        self._loader = loader

    # def load_module(self, fullname: str) -> types.ModuleType:
    #     # not called it seems like
    #     calling_module = inspect.getmodule(inspect.stack()[1][0])

    #     return WrappedModule(super().load_module(fullname))

    def create_module(self, *args, **kwargs):
        module = self._loader.create_module(*args, **kwargs)
        return module
        return WrappedModule(module)

    def exec_module(self, module, *args, **kwargs):
        self._loader.exec_module(module, *args, **kwargs)

        stack = inspect.stack()
        # bunch of intermediate frames, may need to scan for good one, starting from 3
        for frame in stack[3:]:
            calling_module = inspect.getmodule(frame[0])
            if calling_module:
                break
        assert calling_module
        for k in dir(sys.modules[module.__name__]):
            References.add_reference(module, calling_module, k)
        # sys.modules[module.__name__] = WrappedModule(sys.modules[module.__name__])
