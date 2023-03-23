from typing import TypeVar, Union


class MISSING_TYPE:
    """
    Class to indicate a missing value
    """


_T = TypeVar("_T")


Opt = Union[_T, MISSING_TYPE]

MISSING = MISSING_TYPE()
