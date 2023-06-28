import pytest
from megamock.megapatches import MegaPatch

from tests.unit.simple_app.for_autouse_1 import modified_function


class SomeClass:
    a: str | None

    def __init__(self, a: str | None) -> None:
        self.a = a

    def b(self) -> str:
        return "b"

    c = 1


@pytest.fixture(autouse=True)
def some_autouse_fixture() -> None:
    MegaPatch.it(modified_function, return_value="modified")
