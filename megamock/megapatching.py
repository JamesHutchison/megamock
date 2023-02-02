from __future__ import annotations
import inspect
import sys
from typing import Any
from unittest import mock
from varname import argname

from megamock.import_references import References

# from megamock.custom_loader import WrappedObject


class MegaPatch:
    __reserved_names = {"_patches", "_thing", "_path", "_mocked_value"}

    def __init__(
        self, thing: Any, path: str, patches: Any, mocked_value: mock.Mock
    ) -> None:
        self._patches = patches
        self._thing = thing
        self._path = path
        self._mocked_value: mock.Mock = mocked_value

    def start(self) -> None:
        for patch in self._patches:
            patch.start()

    @staticmethod
    def it(
        thing: Any, autostart: bool = True, mocker: object | None = None, **kwargs: Any
    ) -> MegaPatch:
        if mocker is None:
            mocker = mock
        else:
            assert hasattr(
                mocker, "patch"
            ), "mocker does not appear to be a Mocker object"

        passed_in_name = argname("thing")
        # if isinstance(thing, WrappedObject):
        #     thing = thing._obj
        if not (module_path := getattr(thing, "__module__", None)):
            owning_class = MegaPatch._get_owning_class(passed_in_name)
            if owning_class:
                module_path = owning_class.__module__
        if module_path is None:
            module_path = MegaPatch.get_module_path_for_nonclass(passed_in_name)
            patch_kwargs = {}
            mocked_value = kwargs.get("new")
        else:
            mocked_value = mock.MagicMock(spec=thing)
            patch_kwargs = {"return_value": mocked_value}
        # mock_path = f"{module_path}.{passed_in_name}"

        # if isinstance(getattr(sys.modules[module_path], passed_in_name), WrappedObject):
        #     mock_path += "._orig_obj"
        patches = []
        for path in (
            References.get_references(module_path, passed_in_name)
            | References.reverse_references[module_path][passed_in_name]
            | {module_path}
        ):
            mock_path = f"{path}.{passed_in_name}"
            p = mocker.patch(mock_path, **(patch_kwargs | kwargs))
            patches.append(p)

        mega_patch = MegaPatch(thing, mock_path, patches, mocked_value)
        if autostart:
            mega_patch.start()
        return mega_patch

    @staticmethod
    def get_module_path_for_nonclass(passed_in_name: str) -> str:
        stack = inspect.stack()
        return inspect.getmodule(stack[2][0]).__name__
        pass

    @staticmethod
    def _get_owning_class(name: str) -> str | None:
        if "." not in name:
            return None
        owning_class_name, attr_name = name.rsplit(".", 1)
        calling_frame = sys._getframe(1)
        return calling_frame.f_locals.get(owning_class_name, None)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._mocked_value, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.__reserved_names:
            self.__dict__[name] = value
            return
        setattr(self._mocked_value, name, value)
