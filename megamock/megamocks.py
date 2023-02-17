from __future__ import annotations
from typing import Any
from unittest import mock


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
