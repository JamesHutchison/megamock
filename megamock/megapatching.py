from __future__ import annotations
from functools import cached_property
import inspect
import sys
from typing import Any
from unittest import mock
from varname import argname  # type: ignore

from megamock.import_references import References

# from megamock.custom_loader import WrappedObject


class MegaMock(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._megamock_spec = kwargs.get("spec")

    def _get_child_mock(self, /, **kw):
        return MegaMock(**kw)


class MegaPatch:
    __reserved_names = {"_patches", "_thing", "_path", "_mocked_value"}
    _active_patches: set[MegaPatch] = set()

    def __init__(
        self, thing: Any, path: str, patches: Any, mocked_value: MegaMock | Any
    ) -> None:
        self._patches = patches
        self._thing = thing
        self._path = path
        self._mocked_value: MegaMock = mocked_value

    def start(self) -> None:
        for patch in self._patches:
            patch.start()
        MegaPatch._active_patches.add(self)

    def stop(self) -> None:
        for patch in self._patches:
            patch.stop()
        MegaPatch._active_patches.remove(self)

    @staticmethod
    def stop_all() -> None:
        for megapatch in list(MegaPatch._active_patches):
            megapatch.stop()

    @staticmethod
    def it(
        thing: Any = None,
        klass=None,
        autostart: bool = True,
        mocker: object | None = None,
        **kwargs: Any,
    ) -> MegaPatch:
        if thing is None and klass is None:
            raise Exception("thing or klass required")
        if thing and klass:
            raise Exception("Use either thing or klass but not both")
        if mocker is None:
            mocker = mock
        else:
            assert hasattr(
                mocker, "patch"
            ), "mocker does not appear to be a Mocker object"

        if klass is not None:
            thing = klass
            given_arg = "klass"
        else:
            given_arg = "thing"
        if isinstance(thing, MegaMock):
            thing = thing._megamock_spec
        if isinstance(thing, cached_property):
            thing = thing.func
            is_cached_property = True
        else:
            is_cached_property = False

        passed_in_name = argname(given_arg, vars_only=False)
        # if isinstance(thing, WrappedObject):
        #     thing = thing._obj

        if not (module_path := getattr(thing, "__module__", None)):
            owning_class = MegaPatch._get_owning_class(passed_in_name)
            if owning_class:
                module_path = owning_class.__module__
        if module_path is None:
            module_path = MegaPatch.get_module_path_for_nonclass(passed_in_name)
            mocked_value = kwargs.get("new", MegaMock())
            patch_kwargs = {"new": mocked_value}
        else:
            mock_kwargs = {"spec": thing}
            if is_cached_property:
                mocked_value = kwargs.get("new", MegaMock())
            else:
                mocked_value = MegaMock(**mock_kwargs)
            patch_kwargs = {"new": mocked_value}
            if klass:
                mock_kwargs["return_value"] = mocked_value
                patch_kwargs["new"] = MegaMock(**mock_kwargs)

        patches = []
        for path in (
            References.get_references(module_path, passed_in_name)
            | References.reverse_references[module_path][passed_in_name]
            | {module_path}
        ):
            mock_path = f"{path}.{passed_in_name}"
            p = mocker.patch(mock_path, **(patch_kwargs))
            patches.append(p)

        mega_patch = MegaPatch(thing, mock_path, patches, mocked_value)
        if autostart:
            mega_patch.start()
        return mega_patch

    @staticmethod
    def get_module_path_for_nonclass(passed_in_name: str) -> str:
        stack = inspect.stack()
        module = inspect.getmodule(stack[2][0])
        assert module
        return module.__name__

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
