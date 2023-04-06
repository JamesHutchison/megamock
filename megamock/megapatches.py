from __future__ import annotations

import inspect
import logging
import sys
from functools import cached_property
from types import ModuleType
from typing import Any, Callable, Generic, Iterable, TypeVar, cast
from unittest import mock

from varname import argname  # type: ignore

from megamock.import_references import References
from megamock.megamocks import MegaMock, _MegaMockMixin, _UseRealLogic

logger = logging.getLogger(__name__)

T = TypeVar("T")
U = TypeVar("U")


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


class MegaPatch(Generic[T, U]):
    __reserved_names = {"_patches", "_thing", "_path", "_mocked_value", "_return_value"}
    _active_patches: set[MegaPatch] = set()

    default_mocker: ModuleType | object = mock

    def __init__(
        self,
        *,
        thing: Any,
        patches: list[mock._patch],
        new_value: MegaMock | Any,
        return_value: Any,
        mocker: ModuleType | object
        # _merged_type: type[U] | None = None,
    ) -> None:
        self._patches = patches
        self._thing: Any | None = thing
        self._new_value: MegaMock = new_value
        self._return_value = return_value
        self._mocker = mocker

    @property
    def patches(self) -> list[mock._patch]:
        return list(self._patches)

    @property
    def thing(self) -> Any:
        return self._thing

    @property
    def new_value(self) -> MegaMock[T, U] | Any:
        return self._new_value

    @property
    def mock(self) -> MegaMock[T, U]:
        val = self.new_value
        if not isinstance(val, MegaMock) and not hasattr(val, "return_value"):
            raise ValueError(f"New value {val!r} is not a mock!")
        return val

    @property
    def megainstance(self) -> U:
        return self.mock.megainstance

    @property
    def return_value(self) -> MegaMock[T, U]:
        return cast(MegaMock[T, U], self._return_value)

    def set_context_manager_return_value(self, new_return_value: Any) -> None:
        """
        Use to modify the result of entering a context manager

        megapatch = MegaPatch.it(my_context_manager)
        megapatch.set_context_manager_return_value("foo")

        with my_context_manager() as val:
            assert val == "foo"
        """
        try:
            self.return_value.__enter__.return_value = new_return_value  # type: ignore
        except AttributeError:
            raise ValueError("Not a context manager")

    def set_context_manager_side_effect(self, new_side_effect: Any) -> None:
        """
        Use to set the side effect when entering the context manager. As with
        normal side-effect usage, an exception will result in it being raised,
        and an iterable will change the result on subsequent calls
        """
        try:
            self.return_value.__enter__.side_effect = new_side_effect  # type: ignore
        except AttributeError:
            raise ValueError("Not a context manager")

    def set_context_manager_exit_side_effect(self, new_side_effect: Any) -> None:
        """
        Use to set the side effect when exiting the context manager. As with
        normal side-effect usage, an exception will result in it being raised,
        and an iterable will change the result on subsequent calls
        """
        try:
            self.return_value.__exit__.side_effect = new_side_effect  # type: ignore
        except AttributeError:
            raise ValueError("Not a context manager")

    def start(self) -> None:
        # support for pytest-mock and similar
        if not hasattr(self._mocker, "stopall"):
            # built-in mock
            for patch in self._patches:
                patch.start()
        MegaPatch._active_patches.add(self)

    def stop(self) -> None:
        # support for pytest-mock and similar
        if hasattr(self._mocker, "stopall"):
            self._mocker.stopall()
        else:
            # built-in mock
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
        behavior: MegaPatchBehavior,
        thing: Any,
        spec_set: bool,
        return_value: Any,
        side_effect: Iterable | Exception | None,
    ) -> tuple[Any, Any]:
        if behavior.autospec:
            autospeced = mock.create_autospec(thing, spec_set=spec_set)
            if inspect.isfunction(autospeced):
                assert hasattr(autospeced, "return_value")
                if return_value is not _MISSING:
                    autospeced.return_value = return_value
                if side_effect is not None:
                    autospeced.side_effect = side_effect  # type: ignore
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
        thing: T,
        /,
        new: Any | None = None,
        spec_set: bool = True,
        behavior: MegaPatchBehavior | None = None,
        autostart: bool = True,
        mocker: ModuleType | object | None = None,
        new_callable: Callable | None = None,
        **kwargs: Any,
    ):
        """
        MegaPatch something.

        :param thing: The thing to patch
        :param spec_set: If true, then raise an attribute error when setting an
            attribute that doesn't exist on a class
        :param behavior: The behavior to use when mocking
        :param autostart: If true, then start the patch immediately
        :param mocker: The object to use for patching. If None, then use the default
        :param new_callable: A callable function or object that returns the replacement
            object to return. This is usually some replacement Mock bject.
            This is mainly for legacy support and is not recommended since it can't be
            combined with autospec.
        """
        if mocker is None:
            mocker = MegaPatch.default_mocker
        else:
            assert hasattr(
                mocker, "patch"
            ), "mocker does not appear to be a Mocker object"

        if autostart is False and not hasattr(mocker.patch, "start"):
            logger.warning(
                "Disabling autostart doesn't appear to be supported by mocker. "
                "Falling back to built in mock"
            )
            mocker = mock

        if isinstance(thing, _MegaMockMixin):
            parent_mock = thing.megamock.parent
            assert thing.megamock.spec is not None
            thing = thing.megamock.spec
        else:
            parent_mock = None

        if behavior is None:
            behavior = MegaPatchBehavior.for_thing(thing)
        if new_callable is not None:
            if new is None:
                new = mock.DEFAULT
            return_value = kwargs.get("return_value")
            kwargs["new_callable"] = new_callable
        else:
            if (autospec := kwargs.pop("autospec", None)) in (True, False):
                behavior.autospec = autospec
            new, return_value = MegaPatch._new_return_value(
                thing, spec_set, new, kwargs, behavior
            )
        if isinstance(thing, cached_property):
            thing = thing.func  # type: ignore

        passed_in_name = argname("thing", func=MegaPatch.it, vars_only=False)

        module_path = MegaPatch._determine_module_path(thing, passed_in_name)

        patches = MegaPatch._build_patches(
            mocker, module_path, passed_in_name, new, kwargs
        )

        mega_patch = MegaPatch[T, type[MegaMock | T]](
            thing=thing,
            patches=patches,
            new_value=new,
            return_value=return_value,
            mocker=mocker,
        )
        if autostart:
            mega_patch.start()

        MegaPatch._maybe_assign_link(parent_mock, passed_in_name, mega_patch)

        return mega_patch

    @staticmethod
    def _maybe_assign_link(
        parent_mock: _MegaMockMixin | None, passed_in_name: str, mega_patch: MegaPatch
    ) -> None:
        if parent_mock is not None:
            assert passed_in_name
            this_name = passed_in_name.split(".")[-1]
            try:
                cast(
                    MegaMock, getattr(parent_mock.megainstance, this_name)
                )._megalink_to(mega_patch.mock)
            except ValueError:
                pass  # not a mock

    @staticmethod
    def _new_return_value(
        thing: Any,
        spec_set: bool,
        new_given: Any,
        kwargs: dict,
        behavior: MegaPatchBehavior,
    ) -> tuple[Any, Any]:
        provided_return_value = kwargs.pop("return_value", _MISSING)
        side_effect = kwargs.pop("side_effect", None)

        MegaPatch._gotcha_check(provided_return_value, behavior)

        if new_given is None:
            if behavior.autospec:
                new, return_value = MegaPatch._get_new_and_return_value_with_autospec(
                    behavior,
                    thing,
                    spec_set,
                    provided_return_value,
                    side_effect=side_effect,
                )
            else:
                if provided_return_value is _MISSING:
                    return_value = MegaMock()
                else:
                    return_value = provided_return_value
                new = MegaMock[None, None](return_value=return_value)
        else:
            new = new_given
            if provided_return_value is not _MISSING:
                logger.warning("Ignoring return_value argument when 'new' is provided")
            if hasattr(new, "return_value"):
                return_value = new.return_value
            else:
                return_value = None

        assert return_value is not _MISSING

        return new, return_value

    @staticmethod
    def _gotcha_check(return_value: Any, behavior: MegaPatchBehavior) -> None:
        # autospec does not use the MegaMock code path when building return values
        # so this does not work as expected. It ends up returning a UseRealLogic object
        if behavior.autospec and isinstance(return_value, _UseRealLogic):
            raise ValueError(
                "Setting the return value within MegaPatch.it "
                "is currently not supported"
            )

    @staticmethod
    def _determine_module_path(thing: Any, passed_in_name: str) -> str:
        if not (module_path := getattr(thing, "__module__", None)):
            owning_class = MegaPatch._get_owning_class(passed_in_name)
            if owning_class:
                module_path = owning_class.__module__
        if module_path is None:
            module_path = MegaPatch._get_module_path_for_nonclass()

        if module_path is None:
            raise Exception(f"Unable to determine module path for: {thing!r}")
        return module_path

    @staticmethod
    def _build_patches(
        mocker: Any, module_path: str, passed_in_name: str, new: Any, kwargs: dict
    ) -> list[mock._patch]:  # type: ignore  # mypy bug?
        patches = []
        for path in (
            References.get_references(module_path, passed_in_name)
            | References.reverse_references[module_path][passed_in_name]
            | {module_path}
        ):
            mock_path = f"{path}.{passed_in_name}"
            p = mocker.patch(mock_path, new, **kwargs)
            patches.append(p)

        return patches

    @staticmethod
    def _get_module_path_for_nonclass() -> str:
        stack = inspect.stack()
        module = inspect.getmodule(stack[3][0])
        assert module
        return module.__name__

    @staticmethod
    def _get_owning_class(name: str) -> str | None:
        if "." not in name:
            return None
        owning_class_name, attr_name = name.rsplit(".", 1)
        calling_frame = sys._getframe(1)
        return calling_frame.f_locals.get(owning_class_name, None)
