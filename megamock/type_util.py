from typing import Any, Iterable, Optional, TypeVar, Union
import typing


class _MISSING:
    """
    Class to indicate a missing value
    """


_T = TypeVar("_T")
_U = TypeVar("_U")

Opt = Union[_T, _MISSING]

MISSING = _MISSING()
