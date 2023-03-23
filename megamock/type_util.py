from typing import TypeVar, Union


class _MISSING:
    """
    Class to indicate a missing value
    """


_T = TypeVar("_T")


Opt = Union[_T, _MISSING]

MISSING = _MISSING()
