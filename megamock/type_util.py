from typing import TypeVar, Union
from unittest.mock import _Call  # noqa


class MISSING_TYPE:
    """
    Class to indicate a missing value
    """


_T = TypeVar("_T")


Opt = Union[_T, MISSING_TYPE]

MISSING = MISSING_TYPE()

Call = _Call
call = Call(from_kall=False)
