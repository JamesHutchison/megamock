from __future__ import annotations
from abc import ABCMeta
from collections import defaultdict
import copy
import re
import time
import traceback
from typing import Any
from unittest import mock


class _MISSING:
    """
    Class to indicate a missing value
    """


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


class _MegaMockMixin:
    def __init__(
        self,
        spec: Any = None,
        _wraps_mock: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
            | None
        ) = None,
        wraps: Any = None,
        spy: Any = None,
        spec_set=True,
        instance=True,
        # warning: kwargs to MagicMock may not work correctly! Use at your own risk!
        **kwargs,
    ) -> None:
        self.megamock_spied_access: defaultdict[str, list[SpyAccess]] = defaultdict(
            list
        )
        # self.megamock_spy = spy
        if wraps and spy:
            # if spy is used, then the spied value is also wrapped
            raise Exception("Cannot both wrap and spy")

        self.megamock_wraps = wraps = wraps or spy
        self.megamock_spec = spec
        self.megamock_attr_assignments: defaultdict[
            str, list[AttributeAssignment]
        ] = defaultdict(list)
        if wraps and not _wraps_mock:
            _wraps_mock = mock.MagicMock(wraps=wraps)

        self.megamock_spy = spy
        # !important!
        # once __wrapped is set, future assignments will be on the wrapped object
        # __wrapped becomes "_MegaMockMixin__wrapped"
        # it MUST be last
        if _wraps_mock is None:
            if spec is not None:
                autospeced_legacy_mock = mock.create_autospec(
                    spec, spec_set=spec_set, instance=instance, **kwargs
                )
                self.__wrapped = autospeced_legacy_mock
            else:
                super().__init__(**kwargs)
        else:
            # there is a bug where simply checking for "return_value"
            # on a MagicMock will set it, breaking the wrapped value
            if not wraps:
                self._mock_return_value_ = _wraps_mock.return_value
            else:
                self._mock_return_value_ = None
            self.__wrapped = _wraps_mock

    @property
    def _mock_return_value(self) -> Any:
        if self.__dict__.get("_MegaMockMixin__wrapped"):
            if (
                val := self.__dict__.get("_mock_return_value_cache", _MISSING)
            ) == _MISSING:
                if isinstance(
                    self._mock_return_value_,
                    mock.NonCallableMagicMock | mock.NonCallableMock,
                ):
                    val = self._mock_return_value_cache = MegaMock.from_legacy_mock(
                        self._mock_return_value_, None, self.megamock_wraps
                    )
                else:
                    val = self._mock_return_value_cache = self._mock_return_value_
            return val
        return self.__dict__.get(
            "_mock_return_value", self.__class__._mock_return_value
        )

    def _get_child_mock(self, /, **kw) -> MegaMock:
        return MegaMock(**kw)

    def __getattr__(self, key) -> Any:
        if key not in ("megamock_spy", "megamock_spied_access") and self.megamock_spy:
            result = getattr(self.megamock_spy, key)
            # if result is callable let wrapped handle it so that it's a mock object
            if not callable(result):
                self.megamock_spied_access[key].append(
                    SpyAccess.for_current_stack(key, result)
                )
                return result

        if (wrapped := self.__dict__.get("_MegaMockMixin__wrapped")) is not None:
            result = getattr(wrapped, key)
            if not isinstance(result, _MegaMockMixin) and isinstance(
                result, mock.NonCallableMock | mock.NonCallableMagicMock
            ):
                mega_result = MegaMock.from_legacy_mock(
                    result, getattr(self.megamock_spec, key, None), self.megamock_wraps
                )
                setattr(wrapped, key, mega_result)
                return mega_result
            return result
        raise AttributeError(key)

    def __setattr__(self, key, value) -> None:
        if key != "_MegaMockMixin__wrapped" and self.__dict__.get("megamock_spy"):
            setattr(self.megamock_spy, key, value)
        elif (wrapped := self.__dict__.get("_MegaMockMixin__wrapped")) is not None:
            try:
                setattr(wrapped, key, value)
            except AttributeError:
                # mock won't allow assignment of values assigned in __init__ or
                # elsewhere when spec_set is set. Check spec annotations and if the
                # value exists, allow assignment
                if key in self.megamock_spec.__annotations__:
                    # do not check type if assigning a mock object
                    # note that MegaMock is a subclass of NonCallableMagicMock
                    if not isinstance(
                        value, mock.NonCallableMock | mock.NonCallableMagicMock
                    ):
                        allowed_values = self.megamock_spec.__annotations__[key]
                        if not isinstance(value, allowed_values):
                            raise TypeError(
                                f"{value!r} is not an instance of {allowed_values}"
                            )
                    wrapped.__dict__[key] = value
                else:
                    raise
        else:
            self.__dict__[key] = value

        if "megamock_attr_assignments" in self.__dict__:
            self.megamock_attr_assignments[key].append(
                AttributeAssignment.for_current_stack(key, value)
            )


class MegaMock(_MegaMockMixin, mock.MagicMock):
    @staticmethod
    def from_legacy_mock(
        mock_obj: (
            mock.Mock
            | mock.MagicMock
            | mock.NonCallableMock
            | mock.NonCallableMagicMock
        ),
        spec: Any,
        wraps: Any = None,
    ) -> NonCallableMegaMock | MegaMock:
        if not isinstance(mock_obj, (mock.MagicMock, mock.Mock)):
            return NonCallableMegaMock(_wraps_mock=mock_obj, spec=spec, wraps=wraps)
        return MegaMock(_wraps_mock=mock_obj, spec=spec, wraps=wraps)

    def __call__(self, *args, **kwargs) -> Any:
        if self.__dict__.get("_MegaMockMixin__wrapped"):
            return self.__dict__["_MegaMockMixin__wrapped"](*args, **kwargs)
        return super().__call__(*args, **kwargs)


class NonCallableMegaMock(_MegaMockMixin, mock.NonCallableMagicMock):
    pass
