from megamock.megamocks import MegaMock
from tests.simple_app.foo import Foo


def megamock_type_hints():
    """
    This is a manual test. Check the type hints look correct in your IDE

    There's no expectation to run this function
    """
    no_instance_param = MegaMock.it(Foo)  # type hint should NOT have type[Foo] in it
    no_instance_param.takes_args("arg1", "arg2")  # should NOT show self as an argument

    # mock class object type hints
    # should have type[Foo]
    instance_is_false = MegaMock.this(Foo)
    # should have self argument
    instance_is_false.takes_args(no_instance_param, "arg1", "arg2")
