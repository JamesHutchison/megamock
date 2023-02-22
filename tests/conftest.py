import pytest

from megamock import start_loader, MegaPatch

start_loader()


class SomeObject:
    def __init__(self, a):
        self.a = a

    def b(self) -> str:
        return "b"

    c = 1


@pytest.fixture
def some_object() -> type[SomeObject]:
    return SomeObject


@pytest.fixture(autouse=True)
def stop_all_patches() -> None:
    MegaPatch.stop_all()
