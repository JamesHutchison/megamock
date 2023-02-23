import pytest
from megamock import MegaPatch
from megamock.megapatches import MegaMock
from tests.simple_app.bar import some_func, Bar
from tests.simple_app.foo import Foo, bar, foo_instance
from tests.simple_app.foo import Foo as OtherFoo
from tests.simple_app import foo
from tests.simple_app.helpful_manager import HelpfulManager
from tests.simple_app.nested_classes import NestedParent
from tests.simple_app.uses_nested_classes import (
    get_nested_class_function_value,
    get_nested_class_attribute_value,
)


class TestMegaPatchPatching:
    def test_patch_class_itself(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.new_value.z = "a"

        assert Foo.z == "a"
        Foo("s")  # should work

        # sanity check, instance should NOT work because it doesn't support calling
        with pytest.raises(TypeError):
            Foo("s")()  # type: ignore

    def test_patch_class_instance(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.return_value.z = "b"

        assert Foo("").z == "b"

    def test_patch_global_module_variable(self) -> None:
        MegaPatch.it(bar, new="a")

        assert foo.bar == "a"

    def test_patch_class_attribute(self) -> None:
        MegaPatch.it(Foo.moo, new="dog")

        assert Foo.moo == "dog"

    def test_patch_class_method_supports_return_value_as_arg(self) -> None:
        MegaPatch.it(Foo.some_method, return_value="foo")
        assert Foo("s").some_method() == "foo"

    def test_patch_class_method_supports_return_value_as_attribute(self) -> None:
        megapatch = MegaPatch.it(Foo.some_method)
        megapatch.new_value.return_value = "foo"
        assert Foo("s").some_method() == "foo"

    def test_mock_is_synonym_for_new_value_when_a_mock(self) -> None:
        megapatch = MegaPatch.it(Foo.some_method)
        megapatch.mock.return_value = "foo"
        assert Foo("s").some_method() == "foo"

    def test_mock_raises_type_error_if_new_value_is_not_a_mock(self) -> None:
        megapatch = MegaPatch.it(Foo.some_method, new="foo")

        with pytest.raises(ValueError) as exc:
            megapatch.mock

        assert str(exc.value) == "New value 'foo' is not a mock!"

    def test_patch_megamock_object(self) -> None:
        MegaPatch.it(Foo)
        MegaPatch.it(Foo.moo, new="dog")

    def test_patch_property(self) -> None:
        expected = "dog"
        MegaPatch.it(Foo.moo, new=expected)

        assert Foo("").moo == expected

    def test_patch_cached_property(self) -> None:
        expected = MegaMock(spec=HelpfulManager)
        MegaPatch.it(Foo.helpful_manager, new=expected)

        assert Foo("").helpful_manager is expected

    def test_patch_nested_class_function(self) -> None:
        MegaPatch.it(NestedParent.NestedChild.AnotherNestedChild.z, return_value="a")

        assert get_nested_class_function_value() == "a"

    def test_patch_nested_class_attribute(self) -> None:
        MegaPatch.it(NestedParent.NestedChild.AnotherNestedChild.a, new="z")

        assert get_nested_class_attribute_value() == "z"

    # Issue https://github.com/JamesHutchison/megamock/issues/13
    @pytest.mark.xfail
    def test_patch_renamed_var(self) -> None:
        MegaPatch.it(OtherFoo.some_method, return_value="sm")

        assert Foo("s").some_method() == "sm"


class TestMegaPatchAutoStart:
    def test_enabled_by_default(self) -> None:
        MegaPatch.it(Foo.helpful_manager, new="something")

        assert Foo("").helpful_manager == "something"

    def test_can_be_disabled(self) -> None:
        MegaPatch.it(Foo.helpful_manager, new="something", autostart=False)

        assert isinstance(Foo("").helpful_manager, HelpfulManager)


class TestMegaPatchSpec:
    def test_uses_autospec(self) -> None:
        MegaPatch.it(Foo)

        with pytest.raises(TypeError):
            Foo()  # type: ignore

    def test_can_override_autospec(self) -> None:
        MegaPatch.it(Foo, autospec=False)

        Foo()  # type: ignore


class TestMegaPatchReturnValue:
    def test_when_new_is_not_a_function_then_return_value_is_none(self) -> None:
        patch = MegaPatch.it(bar, new="a")

        assert patch.return_value is None

    def test_return_value_when_mocking_a_function(self) -> None:
        patch = MegaPatch.it(some_func)

        assert patch.return_value is some_func("a")

    def test_return_value_for_class_is_the_instance_object(self) -> None:
        patch = MegaPatch.it(Foo)

        assert patch.return_value is Foo("s")

    def test_provided_return_value_is_the_return_value(self) -> None:
        ret_val = MegaMock()
        patch = MegaPatch.it(some_func, return_value=ret_val)

        assert patch.return_value is ret_val

    def test_patch_return_value_is_not_assignable(self) -> None:
        patch = MegaPatch.it(Foo)

        with pytest.raises(AttributeError):
            patch.return_value = 5  # type: ignore

    def test_return_value_has_changable_return_value(self) -> None:
        patch = MegaPatch.it(Bar)

        patch.return_value.return_value = "something"

        assert Bar()() == "something"


class TestMegaPatchObject:

    # Issue https://github.com/JamesHutchison/megamock/issues/8
    @pytest.mark.xfail
    def test_patching_local_object(self) -> None:
        my_obj = Foo("s")
        MegaPatch.it(my_obj.moo, new="moooo")

        assert Foo("s").moo == "cow"
        assert my_obj.moo == "moooo"

    def test_patching_module_level_object(self) -> None:
        MegaPatch.it(foo_instance.moo, new="moooo")

        assert Foo("s").moo == "cow"
        assert foo_instance.moo == "moooo"
