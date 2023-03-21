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


# class MockUnion(typing.Generic[_T, _U]):  # type: ignore


# class MockUnion(Optional[T]):
#     def relevant_items(self) -> Iterable[type]:
#         return []

#     def __instancecheck__(self, instance: Any) -> bool:
#         if instance is Union:
#             return True
#         return False
