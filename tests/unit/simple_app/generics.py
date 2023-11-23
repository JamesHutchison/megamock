from typing import Callable, Collection, Iterable


class UsesGenerics:
    my_func: Callable[[int], str]
    my_thing: Collection[str]
    my_iter: Iterable[Collection[str]]
