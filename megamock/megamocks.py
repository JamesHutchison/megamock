from __future__ import annotations
from typing import Any
from unittest import mock


class _MISSING:
    """
    Class to indicate a missing value
    """


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
        spec_set=True,
        instance=True,
        **kwargs,
    ) -> None:
        self._megamock_spec = spec

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
            self._mock_return_value_ = _wraps_mock.return_value
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
                        self._mock_return_value_, None
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
                    result, getattr(self._megamock_spec, key, None)
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
                if key in self._megamock_spec.__annotations__:
                    # do not check type if assigning a mock object
                    # note that MegaMock is a subclass of NonCallableMagicMock
                    if not isinstance(
                        value, mock.NonCallableMock | mock.NonCallableMagicMock
                    ):
                        allowed_values = self._megamock_spec.__annotations__[key]
                        if not isinstance(value, allowed_values):
                            raise TypeError(
                                f"{value!r} is not an instance of {allowed_values}"
                            )
                    wrapped.__dict__[key] = value
                else:
                    raise
        else:
            self.__dict__[key] = value


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
