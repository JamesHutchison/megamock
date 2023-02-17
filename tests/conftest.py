import pytest


class SomeObject:
    def __init__(self, a):
        self.a = a

    def b(self) -> str:
        return "b"

    c = 1


@pytest.fixture
def some_object() -> type[SomeObject]:
    return SomeObject
