from __future__ import annotations

from typing import Any, Generic, TypeVar
from megamocks import MegaMock

T = TypeVar("T")


class MegaWrapper(Generic[T]):

    # def __new__(cls, thing: MegaMock[T]) -> [T]:
    #     return super().__new__(cls)

    def __init__(self, thing: MegaMock[T]) -> None:
        self._megawrapped_thing = thing

    def __getattr__(self, name: str) -> MegaWrapper[Any]:
        return getattr(self._megawrapped_thing, name)

    @property
    def return_value(self) -> Any:
        return self._megawrapped_thing.return_value

    @return_value.setter
    def return_value(self, value) -> None:
        self._megawrapped_thing.return_value = value


class Foo:
    def moo(self, a: int) -> str:
        return str(a)


MegaWrapper(MegaMock(Foo)).
