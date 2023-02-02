from functools import cached_property

from tests.simple_app.helpful_manager import HelpfulManager

bar = "bar"


class Foo:
    moo = "cow"

    def __init__(self, s: str) -> None:
        self._s = s

    @property
    def s(self) -> str:
        return self._s

    @cached_property
    def helpful_manager(self) -> HelpfulManager:
        return HelpfulManager()
