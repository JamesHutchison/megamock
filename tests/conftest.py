class SomeClass:
    a: str | None

    def __init__(self, a: str | None) -> None:
        self.a = a

    def b(self) -> str:
        return "b"

    c = 1
