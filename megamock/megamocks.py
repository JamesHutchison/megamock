from __future__ import annotations

import copy
import random
import re
import time
import traceback
from abc import ABCMeta
from collections import defaultdict
from dataclasses import dataclass, field
from inspect import isawaitable, isclass, iscoroutinefunction
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    TypeVar,
    Union,
    cast,
    get_origin,
    get_type_hints,
    no_type_check,
    overload,
)
from unittest import mock
from unittest.mock import create_autospec

from megamock import name_words
from megamock.type_util import MISSING, MISSING_TYPE

T = TypeVar("T")
U = TypeVar("U")
M = TypeVar("M")


class SpecRequiredException(Exception):
    """
    Raised when a spec is required but not provided
    """

    def __str__(self) -> str:
        return "Spec is required but not provided"


class _UseRealLogic:
    """
    Class to indicate that the real logic should be used
    """


UseRealLogic = _UseRealLogic()


class AttributeTrackingBase(metaclass=ABCMeta):
    stacktrace: list[traceback.FrameSummary]

    @property
    def top_of_stacktrace(self) -> list[str]:
        """
        Convenience property for quickly viewing the stacktrace in an IDE debugger.

        This displays the folder / file and then the rest of the stacktrace
        """
        ret = []
        for x in self.format_stacktrace(5):
            if rslt := re.search(
                r"[^/\\]+[/\\][\w\.]+\", line \d+,.*", x, re.MULTILINE | re.DOTALL
            ):
                lines = rslt.group(0).splitlines()
                lines[0] = "..." + lines[0]
                ret.extend([line for line in lines if line])
            else:
                ret.append(x)
        return ret

    def format_stacktrace(self, max_depth=100) -> list[str]:
        # for lists, the first frame is the most recent
        return traceback.format_list(self.stacktrace[:max_depth])

    def print_stacktrace(self, max_depth=100) -> None:
        # when printing stacktraces, display the most recent frame last
        traceback.print_list(self.stacktrace[:-max_depth:-1])


class AttributeAssignment(AttributeTrackingBase):
    def __init__(
        self, attr_name: str, attr_value: Any, stacktrace: list[traceback.FrameSummary]
    ) -> None:
        self.attr_name = attr_name
        self.attr_value = attr_value
        self.stacktrace = stacktrace  # 0 is most recent frame, not oldest frame
        self.time = time.time()

    @staticmethod
    def for_current_stack(
        attr_name: str, attr_value: Any, starting_depth=3
    ) -> AttributeAssignment:
        stacktrace = traceback.extract_stack()[-starting_depth::-1]
        return AttributeAssignment(attr_name, attr_value, stacktrace)


class SpyAccess(AttributeTrackingBase):
    def __init__(
        self, attr_name: str, attr_value: Any, stacktrace: list[traceback.FrameSummary]
    ) -> None:
        self.attr_name = attr_name
        self.attr_value = copy.copy(
            attr_value  # just doing shallow copy, may need to revisit in future
        )
        self.stacktrace = stacktrace  # 0 is most recent frame, not oldest frame
        self.time = time.time()

    @staticmethod
    def for_current_stack(
        attr_name: str, attr_value: Any, starting_depth=3
    ) -> SpyAccess:
        stacktrace = traceback.extract_stack()[-starting_depth::-1]
        return SpyAccess(attr_name, attr_value, stacktrace)


_base_mock_types = (
    mock.Mock
    | mock.MagicMock
    | mock.NonCallableMock
    | mock.NonCallableMagicMock
    | mock.AsyncMock
)


@dataclass
class MegaMockAttributes:
    parent: _MegaMockMixin | None = None
    spec: Any | None = None
    wraps: Any | None = None
    spy: Any | None = None
    attr_assignments: dict[str, list[AttributeAssignment]] = field(
        default_factory=lambda: defaultdict(list)
    )
    spied_access: dict[str, list[SpyAccess]] = field(
        default_factory=lambda: defaultdict(list)
    )
    name: str | None = None

    _wrapped_mock: _base_mock_types | None = None


class _MegaMockMixin(Generic[T, U]):
    """
    Mixin used by MegaMock, NonCallableMegaMock, and AsyncMegaMock
    """

    USE_SUPER_SETATTR = {
        # properties where the actual value uses a different name
        # __setattr__ comes before property evaluation
        "side_effect",
        "called",
        "call_count",
        "call_args",
        "call_args_list",
        "await_count",
        "await_args",
        "await_args_list",
        "return_value",
    }

    meganame: str  # a human friendly name, "<ADJECTIVE> <VERB> <INTEGER>"
    megamock: MegaMockAttributes = None  # type: ignore
    _wrapped_legacy_mock: _base_mock_types | None
    _mock_return_value_cache: Any | MISSING_TYPE = None
    # link call behavior to this mock
    _linked_mock: MegaMock[T, U] | None = None

    def __init__(
        self,
        spec: T | type[T] | None = None,
        *,
        wraps: T | None = None,
        spy: T | None = None,
        spec_set: bool = True,
        instance: bool | None = None,
        side_effect: Any = None,
        return_value: Any = MISSING,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ) = None,
        _parent_mega_mock: _MegaMockMixin | None = None,
        _name: str | None = None,
        _merged_type: type[U] | None = None,
        # warning: kwargs to MagicMock may not work correctly! Use at your own risk!
        **kwargs,
    ) -> None:
        """
        :param spec: The MegaMock's specification (template object)
        :param wraps: An object to wrap, this is included for legacy support. Prefer spy
        :param spy: An object to spy on. The mock will maintain the real behavior of the
            object, but will also track attribute access and assignments
        :param spec_set: If True, only attributes in the spec will be allowed. Assigning
            attributes not part of the spec will result in a AttributeError
        :param instance: If True, the mock will be an instance of the spec. If False,
            the mock will be a class. By default this is True. This must be omitted or
            False for the AsyncMock
        :param side_effect: The side effect to use for the mock. Exceptions are raised,
            fuctions are called, and iterables are returned in order in subsequent calls
        :param return_value: The return value to use for the mock.
        :param _wraps_mock: the wrapped mock, for internal use
        :param _parent_mega_mock: The parent MegaMock, for internal use
        :param _name: The name of the mock, for internal use
        """
        self.meganame = self._generate_meganame()

        self._linked_mock = None
        megamock_attrs = MegaMockAttributes()
        megamock_attrs.name = self._generate_mock_name(spec, _parent_mega_mock, _name)
        self._wrapped_legacy_mock = None
        self._mock_return_value_cache = MISSING

        megamock_attrs.parent = _parent_mega_mock
        if instance is None:
            if iscoroutinefunction(spec) or isawaitable(spec):
                instance = False
            else:
                instance = True

        if wraps and spy:
            # if spy is used, then the spied value is also wrapped
            raise Exception("Cannot both wrap and spy")

        megamock_attrs.wraps = wraps = wraps or spy
        megamock_attrs.spec = spec
        if wraps and not _wraps_mock:
            _wraps_mock = mock.MagicMock(wraps=wraps)

        megamock_attrs.spy = spy
        if return_value is not MISSING:
            kwargs["return_value"] = return_value
        kwargs["side_effect"] = side_effect

        if _wraps_mock is None:
            if spec is not None:
                autospeced_legacy_mock = mock.create_autospec(
                    spec, spec_set=spec_set, instance=instance, **kwargs
                )
                megamock_attrs._wrapped_mock = autospeced_legacy_mock
            else:
                # not wrapping a Mock object, so do init for super
                # this is not done when __wrapped is set because things like
                # mock calls occur on the wrapped object, but calling init
                # would set values like call_args_list on this object
                super().__init__(**kwargs)
        else:
            # there is a bug where simply checking for "return_value"
            # on a MagicMock will set it, breaking the wrapped value
            if not wraps:
                self._mock_return_value_ = _wraps_mock.return_value
            else:
                self._mock_return_value_ = None
            megamock_attrs._wrapped_mock = _wraps_mock

        # must be last as the setattr behavior will change after this
        self.megamock = megamock_attrs
        # shortcut to the wrapped mock to avoid performance penalty
        self._wrapped_legacy_mock = megamock_attrs._wrapped_mock

    def _generate_mock_name(
        self,
        spec: Any,
        parent_mega_mock: _MegaMockMixin | None,
        name: str | None,
    ) -> str:
        mock_name = ""
        if spec is None:
            mock_name = "MegaMock()"
        if parent_mega_mock is not None:
            mock_name = parent_mega_mock.megamock.name or "MegaMock()"
            mock_name += f".{name}" if name else "()"
        try:
            if spec is not None:
                spec_name = getattr(spec, "__name__", None)
                if spec_name is not None:
                    if mock_name:
                        mock_name += "."
                    mock_name += spec_name
                else:
                    if mock_name:
                        mock_name += " -> "
                    mock_name += spec.__class__.__name__
        except AttributeError:
            mock_name += "mock"
            if parent_mega_mock:
                mock_name += "()"
        return mock_name

    def _generate_meganame(self) -> str:
        """
        Generate a random adjective / noun / number name for the mock
        """
        return (
            f"{random.choice(name_words.ADJECTIVES)} "
            f"{random.choice(name_words.NOUNS)} "
            f"{random.randint(0, 10000)}"
        )

    @property
    def megainstance(self) -> U | Any:  # Any is needed for mypy
        """
        Access the instance of a class mock.
        """
        if not isinstance(
            self.megamock._wrapped_mock,
            (mock.MagicMock, mock.Mock),  # callable mocks
        ) or not isclass(self.megamock.spec):
            raise Exception("The megainstance property was intended for class mocks")
        return cast(U, self.return_value)

    @property
    def _mock_return_value(self) -> Any:
        if self._wrapped_legacy_mock is not None:
            if (val := self._mock_return_value_cache) is MISSING:
                if isinstance(
                    self._mock_return_value_,
                    mock.NonCallableMagicMock | mock.NonCallableMock,
                ):
                    val = self._mock_return_value_cache = MegaMock.from_legacy_mock(
                        self._mock_return_value_,
                        None,
                        self.megamock.wraps,
                    )
                else:
                    val = self._mock_return_value_cache = self._mock_return_value_
            return val
        return self.__dict__.get(
            "_mock_return_value", self.__class__._mock_return_value
        )

    def _get_child_mock(self, /, **kw) -> MegaMock:
        return MegaMock(_parent_mega_mock=self, **kw)

    def __getattr__(self, key) -> Any:
        if key != "megamock" and self.megamock.spy is not None:
            result = getattr(self.megamock.spy, key)
            # if result is callable let wrapped handle it so that it's a mock object
            if not callable(result):
                self.megamock.spied_access[key].append(
                    SpyAccess.for_current_stack(key, result)
                )
                return result

        if key == "_spec_signature":
            return self.__signature__

        if (wrapped := self._wrapped_legacy_mock) is not None:
            result = getattr(wrapped, key)
            if not isinstance(result, _MegaMockMixin) and isinstance(
                result, mock.NonCallableMock | mock.NonCallableMagicMock
            ):
                mega_result = MegaMock.from_legacy_mock(
                    result,
                    getattr(self.megamock.spec, key, self.megamock.spec),
                    self.megamock.wraps,
                    parent_megamock=self,
                )
                assert mega_result
                # return_value is referenced when a call is made.
                # This actually accesses _mock_return_value
                if key == "_mock_return_value":
                    mega_result.megamock.name = f"{self.megamock.name}()"
                else:
                    mega_result.megamock.name = f"{self.megamock.name}.{key}"
                setattr(wrapped, key, mega_result)
                return mega_result
            return result
        if not self.megamock.spec and not self.megamock.wraps:
            result = self._get_child_mock(_name=key)
            setattr(self, key, result)
            return result
        raise AttributeError(key)

    def __setattr__(self, key, value) -> None:
        if key in ("megamock", "_wrapped_legacy_mock"):
            self.__dict__[key] = value
            return
        if key in self.USE_SUPER_SETATTR:
            super().__setattr__(key, value)
        if self.megamock is not None:
            self._megamock_set_attr(key, value)
            self.megamock.attr_assignments[key].append(
                AttributeAssignment.for_current_stack(key, value)
            )
        else:
            self.__dict__[key] = value

    def _megamock_set_attr(self, key, value) -> None:
        if self.megamock.spy is not None:
            setattr(self.megamock.spy, key, value)
        elif (wrapped := self._wrapped_legacy_mock) is not None:
            try:
                setattr(wrapped, key, value)
            except AttributeError:
                # mock won't allow assignment of values assigned in __init__ or
                # elsewhere when spec_set is set. Check spec annotations and if the
                # value exists, allow assignment
                if key in self.megamock.spec.__annotations__:
                    self._set_attr_annotations_check(key, value)
                    wrapped.__dict__[key] = value
                else:
                    raise
        else:
            self.__dict__[key] = value

    def _set_attr_annotations_check(self, key: str, value: Any) -> None:
        # do not check type if assigning a mock object
        # note that MegaMock is a subclass of NonCallableMagicMock
        if not isinstance(value, mock.NonCallableMock | mock.NonCallableMagicMock):
            allowed_values = get_type_hints(self.megamock.spec)[key]

            def raise_type_error() -> None:
                raise TypeError(f"{value!r} is not an instance of {allowed_values}")

            # This is pretty basic but should handle most cases
            # Perhaps in the future this could handle things perfectly
            try:
                is_allowed_type = isinstance(value, allowed_values)
            except TypeError:
                origin = get_origin(allowed_values)
                if not origin:
                    raise
                if not isinstance(value, origin):
                    raise_type_error()
            else:
                if not is_allowed_type:
                    raise_type_error()

    def _get_spec_from_parents(
        self, _parent_stack: list[_MegaMockMixin] | None = None
    ) -> Any:
        """
        The built-in generate autospec function creates a few issues because
        it bypasses some of the tooling, so the whole tree of mocks are created
        without hitting MegaMock anywhere.

        This function walks up the megamock parent tree to find the root,
        then grabs the spec from there. It then walks back down, checking
        the children of the wrapped mock for each MegaMock to see if one
        of the legacy children mocks matches the wrapped mock from the
        MegaMock that called this function. It then grabs the attribute
        based on the name and the currently focused spec.
        """
        # to start, parent_stack is always empty
        parent_stack = _parent_stack or []

        # if this is a child mock, get the parent's spec
        if self.megamock.parent:
            cur_spec = self.megamock.parent._get_spec_from_parents(
                parent_stack + [self]
            )
            # abort if for some reason there is no parent spec
            if cur_spec is None:
                return None
        else:
            # the root MegaMock will hit this logic branch
            cur_spec = self.megamock.spec
        if cur_spec:
            if not (wrapped := self._wrapped_legacy_mock):
                return None
            if parent_stack:
                # the oldest item is the first element. The child that called this
                # will be the last element of parent_stack.
                child_that_called_me = parent_stack[-1]
                for child_name, obj in wrapped._mock_children.items():
                    if obj is child_that_called_me._wrapped_legacy_mock:
                        return getattr(cur_spec, child_name)
            else:
                return cur_spec
            # this is a class, and the child is an instance
            if isinstance(cur_spec, type):
                return cur_spec
        # this will happen if the root has no spec
        # or if the child that called this method cannot be located
        return None

    def __enter__(self) -> U:
        if self.megamock.wraps is not None:
            return self.megamock.wraps.__enter__()
        try:
            if self.using_real_logic():
                return self.megamock.spec.__enter__()  # type: ignore
            return self.__getattr__("__enter__")
        except AttributeError:
            if hasattr(self.megamock.spec, "__name__"):
                name_str = f"'{self.megamock.spec.__name__}' "  # type: ignore
            else:
                name_str = ""
            raise TypeError(
                f"{name_str}object does not support the context manager protocol"
            )

    def __exit__(self, exc_type, exc_value, traceback):
        if self.megamock.wraps is not None:
            self.megamock.wraps.__exit__(exc_type, exc_value, traceback)
        if self.using_real_logic():
            assert self.megamock.spec
            return self.megamock.spec.__exit__(exc_type, exc_value, traceback)
        return self.__getattr__("__exit__")

    def using_real_logic(self) -> bool:
        return (
            self._wrapped_legacy_mock.__dict__.get("_mock_return_value") is UseRealLogic
        )

    def _megalink_to(self, other: MegaMock[T, U]) -> None:
        """
        Link the call behavior to another mock. This is currently used by `MegaPatch.it`
        to link the class (type) mock with the class (instance) mock.
        """
        self.__dict__["_linked_mock"] = other

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name='{self.megamock.name}' "
            f"| {self.meganame}>"
        )


class MegaMock(_MegaMockMixin[T, U], mock.MagicMock, Generic[T, U]):
    """
    The primary MegaMock class. Use MegaMock.it if providing a spec,
    spy, or wraps argument to ensure that type inference works correctly.

    Instead of: MegaMock(spec=MySpecClass)
    Use: MegaMock.it(MySpecClass)
    """

    # Passthrough logic for quickly casting to a MegaMock
    def __new__(
        cls, _existing: T | _MegaMockMixin[T, U] | None = None, *args, **kwargs
    ):
        if hasattr(_existing, "megamock"):
            return cast(MegaMock[T, U], _existing)
        return super().__new__(cls, *args, **kwargs)

    # Types MegaMock()
    @overload
    def __init__(self: MegaMock[None, None]) -> None:
        ...

    # Types MegaMock(existing_megamock)
    @overload
    def __init__(
        self: Union[MegaMock[T, U], Any],
        _existing: _MegaMockMixin[T, U] | Union[_MegaMockMixin[T, U], T],
    ) -> None:
        ...

    # types MegaMock(spec=SomeClass, instance=False, ...)
    @overload
    def __init__(
        self: _MegaMockMixin[T, U],
        _existing: None = None,
        *,
        spec: type[T],
        instance: Literal[False] = False,
        side_effect: Any = None,
        return_value: Any = MISSING,
        wraps: None = None,
        spy: None = None,
        spec_set: bool = True,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ) = None,
        _parent_mega_mock: _MegaMockMixin | None = None,
        _merged_type: type[U],
    ) -> None:
        ...

    # types MegaMock(spec=SomeInstance)
    @overload
    def __init__(
        self: _MegaMockMixin[T, U],
        _existing: None = None,
        *,
        spec: T,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ) = None,
        instance: bool | None = None,
        side_effect: Any = None,
        return_value: Any = MISSING,
        wraps: Any = None,
        spy: Any = None,
        spec_set: bool = True,
        _parent_mega_mock: _MegaMockMixin | None = None,
        _merged_type: type[U],
    ) -> None:
        ...

    # types MegaMock when spec is not provided
    @overload
    def __init__(
        self: MegaMock[T, T],
        _existing: None = None,
        *,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ) = None,
        wraps: T | None = None,
        spy: T | None = None,
        spec_set: bool = True,
        instance: bool | None = None,
        side_effect: T | None = None,
        return_value: T | None = None,
        _parent_mega_mock: _MegaMockMixin | None = None,
        _merged_type: type[U] | None = None,
    ) -> None:
        ...

    def __init__(
        self,
        _existing: Any | None = None,
        *,
        spec: T | type[T] | None = None,
        wraps: T | None = None,
        spy: T | None = None,
        spec_set: bool = True,
        instance: bool | None = None,
        side_effect: Any = None,
        return_value: Any = MISSING,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ) = None,
        _parent_mega_mock: _MegaMockMixin | None = None,
        _merged_type: type[U] | None = None,
        # warning: kwargs to MagicMock may not work correctly! Use at your own risk!
        **kwargs,
    ) -> None:
        """
        :param spec: The MegaMock's specification (template object)
        :param wraps: An object to wrap, this is included for legacy support. Prefer spy
        :param spy: An object to spy on. The mock will maintain the real behavior of the
            object, but will also track attribute access and assignments
        :param spec_set: If True, only attributes in the spec will be allowed. Assigning
            attributes not part of the spec will result in a AttributeError
        :param instance: If True, the mock will be an instance of the spec. If False,
            the mock will be a class. By default this is True. This must be omitted or
            False for the AsyncMock
        :param side_effect: The side effect to use for the mock. Exceptions are raised,
            fuctions are called, and iterables are returned in order in subsequent calls
        :param return_value: The return value to use for the mock.
        :param _wraps_mock: the wrapped mock, for internal use
        :param _parent_mega_mock: The parent MegaMock, for internal use
        """
        if _existing:
            if hasattr(_existing, "megamock"):
                return
            raise Exception("Use MegaMock.it(...) for new mocks, not MegaMock")
        super().__init__(
            spec,
            wraps=wraps,
            spy=spy,
            spec_set=spec_set,
            instance=instance,
            side_effect=side_effect,
            return_value=return_value,
            _wraps_mock=_wraps_mock,
            _parent_mega_mock=_parent_mega_mock,
            _merged_type=_merged_type,
            **kwargs,
        )

    @no_type_check
    @staticmethod
    def it(
        spec: type[T] | None = None,
        *,
        spec_set: bool = True,
        side_effect: Any = None,
        return_value: Any = MISSING,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ) = None,
        _parent_mega_mock: _MegaMockMixin | None = None,
        # warning: kwargs to MagicMock may not work correctly! Use at your own risk!
        **kwargs,
    ) -> T | MegaMock[T, MegaMock | T]:
        """
        MegaMock a class instance.

        Use `it` for creating mock instances of classes. Use `this` for everything else.

        Note that spec_set defaults to True, which means attempts to set
        an attribute that doesn't exist will result in an error.

        The recommended way to use classes with MegaMock is to define
        the type annotations in the class. It does not know what is set
        inside the __init__ function.

        If you do not own the class and cannot change it, set spec_set to False.

        :param spec: The class to create a mock instance of
        :param spec_set: If True, only attributes in the spec will be allowed. Assigning
            attributes not part of the spec will result in a AttributeError
        :param side_effect: The side effect to use for the mock.
        :param return_value: The return value to use for the mock. Since this is for
            a class instance, it would be setting the return value of __call__
        """

        return MegaMock(
            spec=spec,
            spec_set=spec_set,
            instance=True,
            side_effect=side_effect,
            return_value=return_value,
            _wraps_mock=_wraps_mock,
            _parent_mega_mock=_parent_mega_mock,
            _merged_type=type(MegaMock | spec.__class__),  # type: ignore
            **kwargs,
        )

    @no_type_check
    @staticmethod
    def the_class(
        spec: type[T], *, spec_set: bool = True, **kwargs
    ) -> type[T] | MegaMock[type[T], MegaMock[Any, Any] | T]:
        """
        MegaMock a class.

        Use `the_class` for creating mocks of classes. Use `this` for everything else.

        Note that spec_set defaults to True, which means attempts to set
        an attribute that doesn't exist will result in an error.

        The recommended way to use classes with MegaMock is to define
        the type annotations in the class. It does not know what is set
        inside the __init__ function.

        If you do not own the class and cannot change it, set spec_set to False.

        :param spec: The class to create a mock instance of
        :param spec_set: If True, only attributes in the spec will be allowed. Assigning
            attributes not part of the spec will result in a AttributeError
        :param side_effect: The side effect to use for the mock.
        :param return_value: The return value to use for the mock. Since this is for
            a class instance, it would be setting the return value of __call__
        """
        return MegaMock._the_class(spec, spec_set=spec_set, _spec_too=spec, **kwargs)

    @no_type_check
    @staticmethod
    def _the_class(
        spec: type[T],
        *,
        spec_set: bool = True,
        # warning: kwargs to MagicMock may not work correctly! Use at your own risk!
        _spec_too: M,
        **kwargs,
    ) -> M | MegaMock[M, MegaMock | T]:
        if not isclass(spec):
            raise Exception("MegaMock.the_class should be used with classes")
        return_value = MegaMock.it(spec, spec_set=spec_set)

        return MegaMock(
            spec=spec,
            spec_set=spec_set,
            instance=False,
            return_value=return_value,
            _merged_type=type(MegaMock | spec),
            **kwargs,
        )

    @no_type_check
    @staticmethod
    def this(
        spec: T | None = None,
        *,
        wraps: T | None = None,
        spy: T | None = None,
        spec_set: bool = True,
        side_effect: Any = None,
        return_value: Any = MISSING,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ) = None,
        _parent_mega_mock: _MegaMockMixin | None = None,
        # warning: kwargs to MagicMock may not work correctly! Use at your own risk!
        **kwargs,
    ) -> T | MegaMock[T, MegaMock | T]:
        """
        MegaMock something.

        Use `it` for creating mock instances of classes. Use `this` for everything else.

        :param wraps: An object to wrap, this is included for legacy support. Prefer spy
        :param spy: An object to spy on. The mock will maintain the real behavior of the
            object, but will also track attribute access and assignments
        :param spec_set: If True, only attributes in the spec will be allowed. Assigning
            attributes not part of the spec will result in a AttributeError
        :param side_effect: The side effect to use for the mock. Exceptions are raised,
            fuctions are called, and iterables are returned in order in subsequent
            calls
        :param return_value: The return value to use for the mock.
        """

        return MegaMock(
            spec=spec,
            wraps=wraps,
            spy=spy,
            spec_set=spec_set,
            instance=False,
            side_effect=side_effect,
            return_value=return_value,
            _wraps_mock=_wraps_mock,
            _parent_mega_mock=_parent_mega_mock,
            _merged_type=type(MegaMock | spec.__class__),
            **kwargs,
        )

    @staticmethod
    def from_legacy_mock(
        mock_obj: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
        ),
        spec: T,
        wraps: Any = None,
        parent_megamock: MegaMock | _MegaMockMixin | None = None,
    ):
        if not isinstance(mock_obj, (mock.MagicMock, mock.Mock)):
            if isinstance(mock_obj, mock.AsyncMock):
                return AsyncMegaMock(
                    _wraps_mock=mock_obj,
                    spec=spec,
                    wraps=wraps,
                    _parent_mega_mock=parent_megamock,
                )
            return NonCallableMegaMock.it(
                _wraps_mock=mock_obj,
                spec=spec,
                wraps=wraps,
                _parent_mega_mock=parent_megamock,
            )
        return MegaMock.this(
            _wraps_mock=mock_obj,
            spec=spec,
            wraps=wraps,
            _parent_mega_mock=parent_megamock,
        )

    def __call__(self, *args, **kwargs) -> Any:
        if wrapped := self._wrapped_legacy_mock:
            # cannot use wrapped.return_value because it will create a new
            # return_value object and use that
            # TODO: both the megamock and wrapped mock have return values
            #       and they're both importnat, we're not just looking at one.
            if self.using_real_logic():
                if not (spec := self.megamock.spec):
                    spec = self._get_spec_from_parents()
                    if not spec:
                        raise SpecRequiredException()
                if self.megamock.parent:
                    if hasattr(spec, "__func__"):
                        # convert from bound method to unbound method
                        return spec.__func__(self.megamock.parent, *args, **kwargs)
                    # instance of a class Mock
                    return cast(Callable, spec)(self.megamock.parent, *args, **kwargs)
                return cast(Callable, spec)(*args, **kwargs)
            if self._linked_mock is not None:
                # why is the mock not called as a bound method
                return self._linked_mock(self, *args, **kwargs)
            result = wrapped(*args, **kwargs)
            self._validate_spec_was_callable()
            if not isinstance(result, _MegaMockMixin) and isinstance(
                result, mock.NonCallableMock | mock.NonCallableMagicMock
            ):
                call_spec = self._get_call_spec()
                mega_result = MegaMock.from_legacy_mock(
                    result, call_spec, self.megamock.wraps, parent_megamock=self
                )
                return mega_result
            return result
        return super().__call__(*args, **kwargs)

    def _validate_spec_was_callable(self) -> None:
        """
        The create_autospec functionality properly creates a non-callable mock object.
        So, for example, MegaMock.it(Foo) properly indicates that the instance Foo is
        not callable.

        However, a nested call to a non-callable mock object will not be properly
        indicated as non-callable. For example, if we have a class Foo with a mocked
        method that returns a non-callable Bar, then the autospec'ed object will create
        a callable mock object in place of a mock Bar.

        In this case, _get_call_spec is used to give the mocked method a spec for a Bar
        instance, based on the return type annotation. This function then checks that
        spec and enforces the callability of it.

        In other words:

        MegaMock.it(Foo)()  <-- _validate_spec_was_callable is not needed
        MegaMock.it(Foo).do_something()() <-- _validate_spec_was_callable is needed
        """
        if self.megamock.wraps is not None:
            return
        if self.megamock.spec is None:
            return
        if not callable(self.megamock.spec):
            raise TypeError(f"{self.megamock.spec} is not callable")

    def _get_call_spec(self) -> Any:
        """
        Determine what the spec is for a function's return based on the annnotations.

        This is used to a create a mock object with the same traits as the spec.
        """
        if self.megamock.spec is None:
            return None
        if isclass(self.megamock.spec) and hasattr(self.megamock.spec, "__call__"):
            spec = self.megamock.spec.__call__
        else:
            spec = self.megamock.spec
        annotations = getattr(spec, "__annotations__", {})
        return_type = annotations.get("return", None)
        if return_type is None:
            return None
        return create_autospec(return_type, instance=True)


MegaMockType = type[MegaMock[T, MegaMock | T] | T]


class NonCallableMegaMock(
    _MegaMockMixin[T, U], mock.NonCallableMagicMock, Generic[T, U]
):
    @staticmethod
    def it(
        spec: T | None = None,
        *,
        wraps: T | None = None,
        spy: T | None = None,
        spec_set: bool = True,
        instance: bool | None = None,
        side_effect: Any = None,
        return_value: Any = MISSING,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ),
        _parent_mega_mock: _MegaMockMixin | None = None,
        **kwargs,
    ):
        # hack to get static type inference to think this is a true union
        # of the two classes
        def helper(obj) -> type[NonCallableMegaMock[T, NonCallableMegaMock | T] | T]:
            return cast(type[NonCallableMegaMock | T], lambda: obj)

        return helper(
            NonCallableMegaMock(
                spec,
                wraps=wraps,
                spy=spy,
                spec_set=spec_set,
                instance=instance,
                side_effect=side_effect,
                return_value=return_value,
                _wraps_mock=_wraps_mock,
                _parent_mega_mock=_parent_mega_mock,
                _merged_type=type(NonCallableMegaMock | spec.__class__),
                **kwargs,
            ),
        )()


class AsyncMegaMock(MegaMock[T, U], mock.AsyncMock, Generic[T, U]):
    def __init__(self, *args, **kwargs) -> None:
        super(MegaMock, self).__init__(*args, **kwargs)

    def _get_child_mock(self, /, **kw) -> AsyncMegaMock:
        return AsyncMegaMock(**kw)

    @staticmethod
    def it(  # type: ignore
        spec: T | None = None,
        *,
        wraps: T | None = None,
        spy: T | None = None,
        spec_set: bool = True,
        instance: bool | None = None,
        side_effect: Any = None,
        return_value: Any = MISSING,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ),
        _parent_mega_mock: _MegaMockMixin | None = None,
        **kwargs,
    ):
        # hack to get static type inference to think this is a true union
        # of the two classes
        def helper(obj) -> type[AsyncMegaMock[T, AsyncMegaMock | T] | T]:
            return cast(type[AsyncMegaMock | T], lambda: obj)

        return helper(
            AsyncMegaMock(
                spec,
                wraps=wraps,
                spy=spy,
                spec_set=spec_set,
                instance=instance,
                side_effect=side_effect,
                return_value=return_value,
                _wraps_mock=_wraps_mock,
                _parent_mega_mock=_parent_mega_mock,
                _merged_type=type(AsyncMegaMock | spec.__class__),
                **kwargs,
            ),
        )
