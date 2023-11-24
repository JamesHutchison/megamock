from .foo import Foo as MyFoo

foo_instance = MyFoo("something")


def func_that_uses_foo() -> str:
    foo_instance = MyFoo("something else")
    return foo_instance.some_method()
