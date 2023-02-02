from __future__ import annotations
import sys
from typing import Any
from unittest import mock
from varname import argname


class MegaPatch:
    __reserved_names = {"_patch", "_thing", "_path", "_mocked_value"}

    def __init__(
        self, thing: Any, path: str, patch: Any, mocked_value: mock.Mock
    ) -> None:
        self._patch = patch
        self._thing = thing
        self._path = path
        self._mocked_value: mock.Mock = mocked_value

    def start(self) -> None:
        self._patch.start()

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
        if module_path := getattr(thing, "__module__"):
            mock_path = f"{module_path}.{passed_in_name}"
        else:
            owning_class = MegaPatch._get_owning_class(passed_in_name)
            if owning_class:
                mock_path = f"{owning_class.__module__}.{passed_in_name}"
        mocked_value = mock.MagicMock(spec=thing)
        patch_kwargs = {"return_value": mocked_value}
        p = mocker.patch(mock_path, **(patch_kwargs | kwargs))

        if autostart:
            p.start()
        return MegaPatch(thing, mock_path, p, mocked_value)

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
