import time
from functools import cached_property

from tests.unit.simple_app.helpful_manager import HelpfulManager

bar = "bar"


class Foo:
    moo = "cow"
    z = "z"

    def __init__(self, s: str) -> None:
        self._s = s

    @property
    def s(self) -> str:
        return self._s

    @property
    def zzz(self) -> str:
        return self.z

    @cached_property
    def helpful_manager(self) -> HelpfulManager:
        return HelpfulManager()

    @property
    def get_time(self) -> float:
        return self._get_time()

    def _get_time(self) -> float:
        return time.time()

    def some_method(self) -> str:
        return "value"

    def what_moos(self) -> str:
        return f"The {self.moo} moos"

    def get_a_manager(self) -> HelpfulManager:
        return HelpfulManager()

    def takes_args(self, arg1: str, arg2: str) -> tuple[str, str]:
        return (arg1, arg2)


foo_instance = Foo("global")
