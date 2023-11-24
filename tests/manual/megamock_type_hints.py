from megamock.megamocks import MegaMock
from tests.unit.simple_app.foo import Foo


def megamock_type_hints():
    """
    This is a manual test. Check the type hints look correct in your IDE

    There's no expectation to run this function
    """
    instance_mock = MegaMock.it(Foo)  # type hint should NOT have type[Foo] in it
    instance_mock.takes_args("arg1", "arg2")  # should NOT show self as an argument

    # mock class object type hints
    # should have type[Foo]
    class_mock = MegaMock.the_class(Foo)
    # should have self argument
    class_mock.takes_args(instance_mock, "arg1", "arg2")
    MegaMock(class_mock).megainstance.moo = "bull"  # nothing should be unknown
