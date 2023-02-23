from __future__ import annotations
from functools import cached_property
import inspect
import logging
import sys
from typing import Any
from unittest import mock
from varname import argname  # type: ignore

from megamock.import_references import References
from megamock.megamocks import _MegaMockMixin, MegaMock

logger = logging.getLogger(__name__)


class _MISSING:
    """
    Class to indicate a missing argument
    """


class MegaPatchBehavior:
    def __init__(
        self,
        *,
        autospec: bool,
    ) -> None:
        """
        Define the mocking behavior.

        By default, MegaMock.it(...) will determine the behavior from the passed in
        type. Pass in this class as the `behavior` argument to explicitly set the
        behavior.

        :param autospec: Autospec the thing being mocked
        """
        self.autospec = autospec

    @staticmethod
    def for_thing(thing: Any) -> MegaPatchBehavior:
        return MegaPatchBehavior(autospec=True)


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
    def mock(self) -> MegaMock:
        val = self.new_value
        if not isinstance(val, MegaMock) and not hasattr(val, "return_value"):
            raise ValueError(f"New value {val!r} is not a mock!")
        return val

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
    def _get_new_and_return_value_with_autospec(
        behavior: MegaPatchBehavior, thing: Any, spec_set: bool, return_value: Any
    ) -> tuple[Any, Any]:
        if behavior.autospec:
            autospeced = mock.create_autospec(thing, spec_set=spec_set)
            if inspect.isfunction(autospeced):
                assert hasattr(autospeced, "return_value")
                if return_value is not _MISSING:
                    autospeced.return_value = return_value
                new = autospeced
            else:
                new = MegaMock.from_legacy_mock(autospeced, spec=thing)
            return_value = new.return_value
        else:
            if return_value is _MISSING:
                return_value = MegaMock()
            new = MegaMock(return_value=return_value)
        return new, return_value

    @staticmethod
    def it(
        thing: Any = None,
        /,
        new: Any | None = None,
        spec_set=True,
        behavior: MegaPatchBehavior | None = None,
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
            behavior = MegaPatchBehavior.for_thing(thing)
        if (autospec := kwargs.pop("autospec", None)) in (True, False):
            behavior.autospec = autospec
        provided_return_value = kwargs.pop("return_value", _MISSING)
        if new is None:
            if behavior.autospec:
                new, return_value = MegaPatch._get_new_and_return_value_with_autospec(
                    behavior, thing, spec_set, provided_return_value
                )
            else:
                if provided_return_value is _MISSING:
                    return_value = MegaMock()
                else:
                    return_value = provided_return_value
                new = MegaMock(return_value=return_value)
        else:
            if hasattr(new, "return_value"):
                logger.warning("Ignoring return_value argument when 'new' is provided")
                return_value = new.return_value
            else:
                return_value = None

        assert return_value is not _MISSING

        if isinstance(thing, _MegaMockMixin):
            thing = thing._megamock_spec
        if isinstance(thing, cached_property):
            thing = thing.func

        passed_in_name = argname("thing", vars_only=False)

        if not (module_path := getattr(thing, "__module__", None)):
            owning_class = MegaPatch._get_owning_class(passed_in_name)
            if owning_class:
                module_path = owning_class.__module__
        if module_path is None:
            module_path = MegaPatch.get_module_path_for_nonclass(passed_in_name)

        patches = []
        for path in (
            References.get_references(module_path, passed_in_name)
            | References.reverse_references[module_path][passed_in_name]
            | {module_path}
        ):
            mock_path = f"{path}.{passed_in_name}"
            p = mocker.patch(mock_path, new, **kwargs)
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
