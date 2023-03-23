from __future__ import annotations

import copy
from dataclasses import dataclass, field
import re
import time
import traceback
from abc import ABCMeta
from collections import defaultdict
from inspect import isawaitable, isclass, iscoroutinefunction
from typing import Any, Callable, Generic, TypeVar, cast
from unittest import mock

from megamock.type_util import MISSING_TYPE, MISSING


T = TypeVar("T")


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

    _wrapped_mock: _base_mock_types | None = None


class _MegaMockMixin(Generic[T]):
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
    }

    megamock: MegaMockAttributes = None  # type: ignore
    _wrapped_legacy_mock: _base_mock_types | None
    _mock_return_value_cache: Any | MISSING_TYPE = None

    def __init__(
        self,
        spec: T | None = None,
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
        _parent_mega_mock: _MegaMockMixin | None = None,
        # warning: kwargs to MagicMock may not work correctly! Use at your own risk!
        **kwargs,
    ) -> None:
        """
        :param spec: The MegaMock's specification (template object)
        :param _wraps_mock: the wrapped mock, for internal use
        :param wraps: An object to wrap, this is included for legacy support. Prefer spy
        :param spy: An object to spy on. The mock will maintain the real behavior of the
            object, but will also track attribute access and assignments
        :param spec_set: If True, only attributes in the spec will be allowed. Assigning
            attributes not part of the spec will result in a AttributeError
        :param instance: If True, the mock will be an instance of the spec. If False,
            the mock will be a class. By default this is True. This must be omitted or
            False for the AsyncMock
        :param _parent_mega_mock: The parent MegaMock, for internal use
        """
        megamock_attrs = MegaMockAttributes()
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

    @property
    def megacast(self) -> T:
        return cast(T, self)

    @property
    def megainstance(self) -> T:
        """
        Access the instance of a class mock.
        Note that this will type as the class itself, not an instance,
        due to limitations in mypy
        """
        if not callable(self) and not isclass(self.megamock.spec):
            raise Exception("The megainstance property was intended for class mocks")
        assert callable(self)  # make mypy happy
        return cast(T, self.return_value)

    @property
    def _mock_return_value(self) -> Any:
        if self._wrapped_legacy_mock is not None:
            if (val := self._mock_return_value_cache) is MISSING:
                if isinstance(
                    self._mock_return_value_,
                    mock.NonCallableMagicMock | mock.NonCallableMock,
                ):
                    val = self._mock_return_value_cache = MegaMock.from_legacy_mock(
                        self._mock_return_value_, None, self.megamock.wraps
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

        if (wrapped := self._wrapped_legacy_mock) is not None:
            result = getattr(wrapped, key)
            if not isinstance(result, _MegaMockMixin) and isinstance(
                result, mock.NonCallableMock | mock.NonCallableMagicMock
            ):
                mega_result = MegaMock.from_legacy_mock(
                    result,
                    getattr(self.megamock.spec, key, None),
                    self.megamock.wraps,
                    parent_megamock=self,
                )
                setattr(wrapped, key, mega_result)
                return mega_result
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
                    # do not check type if assigning a mock object
                    # note that MegaMock is a subclass of NonCallableMagicMock
                    if not isinstance(
                        value, mock.NonCallableMock | mock.NonCallableMagicMock
                    ):
                        allowed_values = self.megamock.spec.__annotations__[key]
                        if not isinstance(value, allowed_values):
                            raise TypeError(
                                f"{value!r} is not an instance of {allowed_values}"
                            )
                    wrapped.__dict__[key] = value
                else:
                    raise
        else:
            self.__dict__[key] = value

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


class MegaMock(_MegaMockMixin[T], mock.MagicMock, Generic[T]):
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
    ) -> NonCallableMegaMock[T] | MegaMock[T]:
        if not isinstance(mock_obj, (mock.MagicMock, mock.Mock)):
            if isinstance(mock_obj, mock.AsyncMock):
                return AsyncMegaMock(
                    _wraps_mock=mock_obj,
                    spec=spec,
                    wraps=wraps,
                    _parent_mega_mock=parent_megamock,
                )
            return NonCallableMegaMock(
                _wraps_mock=mock_obj,
                spec=spec,
                wraps=wraps,
                _parent_mega_mock=parent_megamock,
            )
        return MegaMock(
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
            if wrapped.__dict__.get("_mock_return_value") is UseRealLogic:
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
            result = wrapped(*args, **kwargs)
            if not isinstance(result, _MegaMockMixin) and isinstance(
                result, mock.NonCallableMock | mock.NonCallableMagicMock
            ):
                mega_result = MegaMock.from_legacy_mock(
                    result,
                    None,
                    self.megamock.wraps,
                )
                return mega_result
            return result
        return super().__call__(*args, **kwargs)


class NonCallableMegaMock(_MegaMockMixin[T], mock.NonCallableMagicMock, Generic[T]):
    pass


class AsyncMegaMock(MegaMock[T], mock.AsyncMock, Generic[T]):
    def __init__(self, *args, **kwargs) -> None:
        super(MegaMock, self).__init__(*args, **kwargs)

    def _get_child_mock(self, /, **kw) -> AsyncMegaMock:
        return AsyncMegaMock(**kw)
