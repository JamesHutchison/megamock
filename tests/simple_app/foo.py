from functools import cached_property

from tests.simple_app.helpful_manager import HelpfulManager

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

    def some_method(self) -> str:
        return "value"

    def what_moos(self) -> str:
        return f"The {self.moo} moos"

    def get_a_manager(self) -> HelpfulManager:
        return HelpfulManager()


foo_instance = Foo("global")
