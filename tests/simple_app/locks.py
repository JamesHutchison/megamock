class SomeLock:
    def __init__(self) -> None:
        self.acquired = False

    def __enter__(self) -> None:
        if self.acquired is True:
            raise Exception("Could not acquire lock")
        self.acquired = True

    def __exit__(self, *args, **kwargs) -> None:
        self.acquired = False
