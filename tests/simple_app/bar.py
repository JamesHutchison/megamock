from contextlib import contextmanager
from typing import Generator


def some_func(val: str) -> str:
    return val + "a"


class Bar:
    def __call__(self) -> str:
        return "called"


@contextmanager
def some_context_manager() -> Generator[str, None, None]:
    yield "foo"
