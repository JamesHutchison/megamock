from __future__ import annotations
from collections import defaultdict
import time
import traceback
from typing import Any
from unittest import mock


class _MISSING:
    """
    Class to indicate a missing value
    """


class AttributeAssignment:
    def __init__(self, attr_name: str, attr_value: Any, stacktrace) -> None:
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
        spec_set=True,
        instance=True,
        # warning: kwargs to MagicMock may not work correctly! Use at your own risk!
        **kwargs,
    ) -> None:
        self.wraps = wraps
        self.megamock_spec = spec
        self.megamock_attr_assignments: defaultdict[
            str, list[AttributeAssignment]
        ] = defaultdict(list)
        if wraps and not _wraps_mock:
            _wraps_mock = mock.MagicMock(wraps=wraps)

        # !important!
        # once __wrapped is set, future assignments will be on the wrapped object
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
                        self._mock_return_value_, None, self.wraps
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
        if (wrapped := self.__dict__.get("_MegaMockMixin__wrapped")) is not None:
            result = getattr(wrapped, key)
            if not isinstance(result, _MegaMockMixin) and isinstance(
                result, mock.NonCallableMock | mock.NonCallableMagicMock
            ):
                mega_result = MegaMock.from_legacy_mock(
                    result, getattr(self.megamock_spec, key, None), self.wraps
                )
                setattr(wrapped, key, mega_result)
                return mega_result
            return result
        raise AttributeError(key)

    def __setattr__(self, key, value) -> None:
        if (wrapped := self.__dict__.get("_MegaMockMixin__wrapped")) is not None:
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
