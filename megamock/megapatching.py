from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
import inspect
import sys
from typing import Any
from unittest import mock
from varname import argname  # type: ignore

from megamock.import_references import References

# from megamock.custom_loader import WrappedObject


class _MegaMockMixin:
    def __init__(self, *args, _wraps_mock=None, **kwargs):
        self._megamock_spec = kwargs.get("spec")

        # must be last
        self.__wrapped = _wraps_mock
        if _wraps_mock is None:
            super().__init__(*args, **kwargs)

    def _get_child_mock(self, /, **kw):
        return MegaMock(**kw)

    def __getattr__(self, key):
        if (wrapped := self.__dict__.get("_MegaMockMixin__wrapped")) is not None:
            result = getattr(wrapped, key)
            if isinstance(result, (mock.NonCallableMock, mock.NonCallableMagicMock)):
                mega_result = MegaMock.from_legacy_mock(
                    result, getattr(self._megamock_spec, key, None)
                )
                setattr(wrapped, key, mega_result)
                return mega_result
            return result
        raise AttributeError(key)

    def __setattr__(self, key, value):
        if (wrapped := self.__dict__.get("_MegaMockMixin__wrapped")) is not None:
            setattr(wrapped, key, value)
        else:
            self.__dict__[key] = value


class MegaMock(_MegaMockMixin, mock.MagicMock):
    # @staticmethod
    # def from_legacy_mock(
    #     mock_obj: (
    #         mock.Mock
    #         | mock.MagicMock
    #         | mock.NonCallableMock
    #         | mock.NonCallableMagicMock
    #     ),
    #     spec: Any,
    # ) -> NonCallableMegaMock | MegaMock:
    #     for k, v in list(mock_obj.__dict__.items()):
    #         if isinstance(v, _MegaMockMixin):
    #             continue
    #         if isinstance(v, (mock.NonCallableMock, mock.NonCallableMagicMock)):
    #             mock_obj.__dict__[k] = MegaMock._from_legacy_mock(
    #                 v, spec=getattr(spec, k, None)
    #             )
    #     return MegaMock._from_legacy_mock(mock_obj, spec)

    @staticmethod
    def from_legacy_mock(
        mock_obj: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
        ),
        spec: Any,
    ) -> NonCallableMegaMock | MegaMock:
        if not isinstance(mock_obj, (mock.MagicMock, mock.Mock)):
            return NonCallableMegaMock(_wraps_mock=mock_obj, spec=spec)
        return MegaMock(_wraps_mock=mock_obj, spec=spec)

    def __call__(self, *args, **kwargs) -> Any:
        if self.__dict__.get("_MegaMockMixin__wrapped"):
            return self.__dict__["_MegaMockMixin__wrapped"](*args, **kwargs)
        return super().__call__(*args, **kwargs)


class NonCallableMegaMock(_MegaMockMixin, mock.NonCallableMagicMock):
    pass


class MegaMockBehavior:
    def __init__(
        self,
        *,
        autospec: bool,
        nested_return_value: bool,
    ) -> None:
        """
        Define the mocking behavior.

        By default, MegaMock.it(...) will determine the behavior from the passed in type.
        Pass in this class as the `behavior` argument to explicitly set the behavior.

        :param autospec: Autospec the thing being mocked
        :param nested_return_value: The return value attribute in MegaMock is the return value of the return value
        """
        self.autospec = autospec
        self.nested_return_value = nested_return_value

    @staticmethod
    def from_thing(thing: Any) -> MegaMockBehavior:
        if inspect.isclass(thing):
            return MegaMockBehavior(
                autospec=True,
                nested_return_value=True
                # spec_return_value=True,
            )
        if inspect.isfunction(thing):
            return MegaMockBehavior(autospec=True, nested_return_value=False)
        return MegaMockBehavior(autospec=True, nested_return_value=False)


class MegaPatch:
    __reserved_names = {"_patches", "_thing", "_path", "_mocked_value", "_return_value"}
    _active_patches: set[MegaPatch] = set()

    def __init__(
        self,
        thing: Any,
        path: str,
        patches: list[mock._patch],
        new_value: MegaMock | Any,
        return_value: Any,
    ) -> None:
        self._patches = patches
        self._thing = thing
        self._path = path
        self._new_value: MegaMock = new_value
        self._return_value = return_value

    @property
    def patches(self) -> list[mock._patch]:
        return list(self._patches)

    @property
    def thing(self) -> Any:
        return self._thing

    @property
    def path(self) -> str:
        return self._path

    @property
    def new_value(self) -> MegaMock | Any:
        return self._new_value

    @property
    def return_value(self) -> Any:
        return self._return_value

    def start(self) -> None:
        for patch in self._patches:
            patch.start()
        MegaPatch._active_patches.add(self)

    def stop(self) -> None:
        for patch in self._patches:
            patch.stop()
        MegaPatch._active_patches.remove(self)

    @staticmethod
    def active_patches() -> list[MegaPatch]:
        return list(MegaPatch._active_patches)

    @staticmethod
    def stop_all() -> None:
        for megapatch in list(MegaPatch._active_patches):
            megapatch.stop()

    @staticmethod
    def it(
        thing: Any = None,
        /,
        new: Any | None = None,
        spec_set=True,
        behavior: MegaMockBehavior | None = None,
        autostart: bool = True,
        mocker: object | None = None,
        **kwargs: Any,
    ) -> MegaPatch:
        if mocker is None:
            mocker = mock
        else:
            assert hasattr(
                mocker, "patch"
            ), "mocker does not appear to be a Mocker object"

        if behavior is None:
            behavior = MegaMockBehavior.from_thing(thing)
        return_value = kwargs.pop("return_value", MegaMock())
        if new is None:
            # mock_kwargs = {}
            if behavior.autospec:
                new = MegaMock.from_legacy_mock(
                    mock.create_autospec(thing, spec_set=spec_set), spec=thing
                )
                return_value = new.return_value

                # mock_kwargs["spec"] = thing
            # if behavior.spec_return_value:
            #     return_value = MegaMock(spec=thing)
            else:
                new = MegaMock(return_value=return_value)  # , **mock_kwargs)

        if isinstance(thing, _MegaMockMixin):
            thing = thing._megamock_spec
        if isinstance(thing, cached_property):
            thing = thing.func
        #     is_cached_property = True
        # else:
        #     is_cached_property = False

        passed_in_name = argname("thing", vars_only=False)
        # if isinstance(thing, WrappedObject):
        #     thing = thing._obj

        if not (module_path := getattr(thing, "__module__", None)):
            owning_class = MegaPatch._get_owning_class(passed_in_name)
            if owning_class:
                module_path = owning_class.__module__
        if module_path is None:
            module_path = MegaPatch.get_module_path_for_nonclass(passed_in_name)
            # mocked_value = kwargs.get("new", MegaMock())
            # patch_kwargs = {"new": mocked_value}
        # else:
        # mock_kwargs = {"spec": thing}
        # if is_cached_property:
        #     mocked_value = kwargs.get("new", MegaMock())
        # else:
        # #     mocked_value = MegaMock(**mock_kwargs)
        # patch_kwargs = {"new": mocked_value}
        # if klass:
        #     mock_kwargs["return_value"] = mocked_value
        #     patch_kwargs["new"] = MegaMock(**mock_kwargs)

        patches = []
        for path in (
            References.get_references(module_path, passed_in_name)
            | References.reverse_references[module_path][passed_in_name]
            | {module_path}
        ):
            mock_path = f"{path}.{passed_in_name}"
            p = mocker.patch(mock_path, new)
            patches.append(p)

        mega_patch = MegaPatch(thing, mock_path, patches, new, return_value)
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

    # def __getattr__(self, name: str) -> Any:
    #     return getattr(self._mocked_value, name)

    # def __setattr__(self, name: str, value: Any) -> None:
    #     if name in self.__reserved_names:
    #         self.__dict__[name] = value
    #         return
    #     setattr(self._mocked_value, name, value)
