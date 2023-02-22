import pytest

from megamock import start_loader, MegaPatch

start_loader()


class SomeClass:
    a: str | None

    def __init__(self, a: str | None) -> None:
        self.a = a

    def b(self) -> str:
        return "b"

    c = 1


@pytest.fixture(autouse=True)
def stop_all_patches() -> None:
    MegaPatch.stop_all()
