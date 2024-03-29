from unittest import mock

import pytest

from megamock import MegaPatch
from megamock.megamocks import NonCallableMegaMock, UseRealLogic
from megamock.megapatches import MegaMock, MegaPatchContext
from megamock.megas import Mega
from tests.unit.simple_app import bar as other_bar
from tests.unit.simple_app import foo, nested_classes
from tests.unit.simple_app.async_portion import (
    SomeClassWithAsyncMethods,
    an_async_function,
)
from tests.unit.simple_app.bar import Bar, some_context_manager, some_func
from tests.unit.simple_app.bar import some_func as some_other_func
from tests.unit.simple_app.does_rename import func_that_uses_foo as func_uses_foo
from tests.unit.simple_app.foo import Foo, bar, foo_instance
from tests.unit.simple_app.foo import Foo as OtherFoo
from tests.unit.simple_app.foo import bar as other_bar_constant
from tests.unit.simple_app.helpful_manager import HelpfulManager
from tests.unit.simple_app.locks import SomeLock
from tests.unit.simple_app.nested_classes import NestedParent
from tests.unit.simple_app.uses_nested_classes import (
    get_nested_class_attribute_value,
    get_nested_class_function_value,
)
from tests.unit.simple_app.uses_nested_classes import (
    get_nested_class_attribute_value as another_nested_class_attr,
)


class TestMegaPatchContext:
    def test_active_patches(self) -> None:
        megapatch_context = MegaPatchContext()
        megapatch = MegaMock.it(MegaPatch)
        megapatch_context.add(megapatch)
        assert megapatch in megapatch_context.active_patches()

    def test_add_remove(self) -> None:
        megapatch_context = MegaPatchContext()
        megapatch = MegaMock.it(MegaPatch)
        megapatch_context.add(megapatch)
        assert megapatch in megapatch_context.active_patches()
        megapatch_context.remove(megapatch)
        assert megapatch not in megapatch_context.active_patches()

    def test_stop_all(self) -> None:
        megapatch_context = MegaPatchContext()
        megapatch1 = MegaMock.it(MegaPatch)
        megapatch2 = MegaMock.it(MegaPatch)
        megapatch_context.add(megapatch1)
        megapatch_context.add(megapatch2)
        megapatch_context.stop_all()
        assert Mega(megapatch1.stop).called_once()
        assert Mega(megapatch2.stop).called_once()

    def test_context_manager(self) -> None:
        context_stack_length = len(MegaPatch.context_stack)
        with MegaPatchContext() as context:
            assert MegaPatch.context_stack[-1] is context
            assert len(MegaPatch.context_stack) == context_stack_length + 1
        assert MegaPatch.context_stack[-1] is not context
        assert len(MegaPatch.context_stack) == context_stack_length

    def test_delete(self) -> None:
        megapatch_context = MegaPatchContext()
        megapatch = MegaMock.it(MegaPatch)
        megapatch_context.add(megapatch)
        del megapatch_context
        assert Mega(megapatch.stop).called_once()


class TestMegaPatchPatching:
    def test_patch_class_itself(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.new_value.z = "a"

        assert Foo.z == "a"
        Foo("s")  # should work

        # sanity check, instance should NOT work because it doesn't support calling
        with pytest.raises(TypeError):
            Foo("s")()  # type: ignore

    def test_patch_class_instance_from_type(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.return_value.z = "b"

        assert Foo("").z == "b"

    def test_patch_from_module_reference(self) -> None:
        patch = MegaPatch.it(foo.Foo)
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

    def test_patch_class_method_from_module_reference(self) -> None:
        MegaPatch.it(foo.Foo.some_method, return_value="foo")
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
        MegaPatch.it(Foo.zzz, new=expected)

        assert Foo("").zzz == expected

    def test_patch_cached_property(self) -> None:
        expected = MegaMock.it(spec=HelpfulManager)
        MegaPatch.it(Foo.helpful_manager, new=expected)

        assert Foo("").helpful_manager is expected

    @pytest.mark.xfail
    def test_set_property_side_effect_after_setting_patch(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.megainstance.zzz.side_effect = Exception("raised!")  # type: ignore

        # this doesn't work because properties are replaced with a mock object,
        # so the implicit call is eliminated
        with pytest.raises(Exception):
            Foo("").zzz

    def test_patch_nested_class_function(self) -> None:
        MegaPatch.it(NestedParent.NestedChild.AnotherNestedChild.z, return_value="a")

        assert get_nested_class_function_value() == "a"

    def test_patch_nested_class_attribute(self) -> None:
        MegaPatch.it(NestedParent.NestedChild.AnotherNestedChild.a, new="z")

        assert get_nested_class_attribute_value() == "z"

    def test_patch_renamed_class_method(self) -> None:
        MegaPatch.it(OtherFoo.some_method, return_value="sm")

        assert Foo("s").some_method() == "sm"

    def test_patch_renamed_class(self) -> None:
        MegaPatch.it(OtherFoo)

        assert isinstance(Foo("s"), NonCallableMegaMock)

    def test_patch_renamed_function(self) -> None:
        MegaPatch.it(some_other_func, return_value="r")

        assert other_bar.some_func("v") == "r"
        assert some_other_func("v") == "r"

    def test_patch_renamed_nested_class(self) -> None:
        MegaPatch.it(NestedParent.NestedChild.AnotherNestedChild.a, new="b")

        assert NestedParent.NestedChild.AnotherNestedChild().a == "b"
        assert nested_classes.NestedParent.NestedChild.AnotherNestedChild().a == "b"

    def test_patch_renamed_parent_module(self) -> None:
        MegaPatch.it(other_bar.some_func, return_value="r")

        assert other_bar.some_func("v") == "r"
        assert some_other_func("v") == "r"

    def test_patch_renamed_constant_primitive(self) -> None:
        MegaPatch.it(other_bar_constant, new="new_val")

        assert other_bar_constant == "new_val"
        assert foo.bar == "new_val"

    def test_patch_that_is_renamed_in_non_test_module_1(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.megainstance.some_method.return_value = "it worked"

        assert func_uses_foo() == "it worked"

    def test_patch_that_is_renamed_in_non_test_module_2(self) -> None:
        from tests.unit.simple_app.does_rename import MyFoo

        patch = MegaPatch.it(MyFoo)
        patch.megainstance.some_method.return_value = "it worked"

        assert func_uses_foo() == "it worked"

    def test_renamed_multiline(self) -> None:
        patch = MegaPatch.it(get_nested_class_attribute_value)
        patch.mock.return_value = "foo"

        assert another_nested_class_attr() == "foo"

    @pytest.mark.xfail
    def test_patch_with_real_logic(self) -> None:
        # this currently fails because the object created by autospec
        # isn't using the MegaMock code path
        MegaPatch.it(Foo.some_method, return_value=UseRealLogic)

        assert Foo("s").some_method() == "a"

    def test_patch_class_and_enable_real_logic(self) -> None:
        megapatch = MegaPatch.it(Foo)

        Mega(megapatch.megainstance.some_method).use_real_logic()

        assert Foo("s").some_method() == "value"

    def test_setting_side_effect(self) -> None:
        MegaPatch.it(Foo.some_method, side_effect=Exception("Error!"))

        with pytest.raises(Exception) as exc:
            Foo("s").some_method()

        assert str(exc.value) == "Error!"

    def test_setting_side_effect_to_a_property(self) -> None:
        MegaPatch.it(Foo.zzz, side_effect=Exception("Error!"))

        with pytest.raises(Exception) as exc:
            Foo("s").zzz

        assert str(exc.value) == "Error!"

    def test_setting_side_effect_to_a_cached_property(self) -> None:
        MegaPatch.it(Foo.helpful_manager, side_effect=Exception("Error!"))

        with pytest.raises(Exception) as exc:
            Foo("s").helpful_manager

        assert str(exc.value) == "Error!"

    def test_stacked_patching_return_value(self) -> None:
        MegaPatch.it(Foo)
        MegaPatch.it(Foo.some_method, return_value="new val")

        assert Foo("s").some_method() == "new val"

    def test_stacked_patching_side_effect(self) -> None:
        MegaPatch.it(Foo)
        MegaPatch.it(Foo.some_method, side_effect=Exception("Error!"))

        with pytest.raises(Exception) as exc:
            Foo("s").some_method()

        assert str(exc.value) == "Error!"

    @pytest.mark.xfail
    def test_assigning_return_value_later_on_class_mock_reflected_in_instance(
        self,
    ) -> None:
        # there's no magic that allows this to work
        patch = MegaPatch.it(Foo)
        patch.mock.some_method.return_value = "new val"

        assert Foo("s").some_method() == "new val"


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

    def test_megainstance_for_class_is_the_instance_object(self) -> None:
        patch = MegaPatch.it(Foo)

        assert patch.megainstance is Foo("s")

    def test_provided_return_value_is_the_return_value(self) -> None:
        ret_val: MegaMock = MegaMock()
        patch = MegaPatch.it(some_func, return_value=ret_val)

        assert patch.return_value is ret_val

    def test_assigning_patch_return_value_directly(self) -> None:
        patch = MegaPatch.it(Foo)

        patch.return_value = 5

        assert Foo("s") == 5
        assert patch.return_value == 5

    def test_assigning_patch_return_value_directly_on_method(self) -> None:
        patch = MegaPatch.it(Foo.some_method)

        patch.return_value = 5

        assert Foo("s").some_method() == 5
        assert patch.return_value == 5

    def test_return_value_has_changable_return_value(self) -> None:
        patch = MegaPatch.it(Bar)

        patch.return_value.return_value = "something"

        assert Bar()() == "something"

    def test_can_enable_real_logic_on_mock(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.return_value.some_method.return_value = UseRealLogic

        assert Foo("s").some_method() == "value"

    def test_enable_real_logic_mega(self) -> None:
        patch = MegaPatch.it(Foo)
        Mega(patch.return_value.some_method).use_real_logic()

        assert Foo("s").some_method() == "value"

    # https://github.com/JamesHutchison/megamock/issues/75
    @pytest.mark.xfail
    def test_using_actual_thing_to_enable_real_logic(self) -> None:
        # must use the mock to assign real logic
        MegaPatch.it(Foo)
        Mega(Foo.some_method).use_real_logic()

        assert Foo("s").some_method() == "value"


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


class TestAsyncPatching:
    async def test_patching_async_function(self) -> None:
        MegaPatch.it(an_async_function, return_value="val")

        assert await an_async_function("s") == "val"

    async def test_patching_async_method(self) -> None:
        MegaPatch.it(SomeClassWithAsyncMethods.some_method, return_value="val")

        assert await SomeClassWithAsyncMethods().some_method("s") == "val"


class TestGotchaCheck:
    def test_raises_value_error_if_autospec_and_use_real_logic(self) -> None:
        with pytest.raises(ValueError):
            MegaPatch.it(Foo, autospec=True, return_value=UseRealLogic)


class TestNewCallable:
    def test_new_callable(self) -> None:
        def foo() -> str:
            return "foo"

        MegaPatch.it(Foo, new_callable=foo)

        assert Foo == "foo"

    def test_combining_new_and_new_callable(self) -> None:
        with pytest.raises(ValueError) as exc:
            MegaPatch.it(Foo, new="hi", new_callable=mock.Mock)

        assert str(exc.value) == "Cannot use 'new' and 'new_callable' together"

    def test_combining_return_value_and_new_callable(self) -> None:
        # return_value is passed in as an argument to the new callable
        mega_patch = MegaPatch.it(Foo, return_value="val", new_callable=mock.Mock)

        # wart from unittest.mock - new_callable can't be combined with autospec
        assert Foo() == "val"  # type: ignore

        assert mega_patch.return_value == "val"

    def test_combining_autospec_and_new_callable(self) -> None:
        with pytest.raises(ValueError) as exc:
            MegaPatch.it(Foo, autospec=True, new_callable=mock.Mock)

        assert str(exc.value) == "Cannot use 'autospec' and 'new_callable' together"


class TestMegaPatchContextManager:
    def test_patch_context_manager(self) -> None:
        MegaPatch.it(some_context_manager)

        with some_context_manager():
            pass

    def test_set_return_value(self) -> None:
        megapatch = MegaPatch.it(some_context_manager)
        megapatch.set_context_manager_return_value("foo")

        with some_context_manager() as val:
            assert val == "foo"

    def test_set_side_effect_exception(self) -> None:
        megapatch = MegaPatch.it(some_context_manager)
        megapatch.set_context_manager_side_effect(Exception())

        with pytest.raises(Exception):
            with some_context_manager():
                pass

    def test_set_side_effect_iterable(self) -> None:
        megapatch = MegaPatch.it(some_context_manager)
        megapatch.set_context_manager_side_effect([1, 2])

        with some_context_manager() as first_val:
            pass
        with some_context_manager() as second_val:
            pass

        assert [first_val, second_val] == [1, 2]

    def test_set_exit_side_effect(self) -> None:
        megapatch = MegaPatch.it(some_context_manager)
        megapatch.set_context_manager_exit_side_effect(Exception("Error on file close"))

        with pytest.raises(Exception) as exc:
            with some_context_manager():
                pass

        assert str(exc.value) == "Error on file close"

    def test_using_class(self) -> None:
        lock = SomeLock()

        # check precondition, should raise exception
        with pytest.raises(Exception):
            with lock:
                with lock:
                    pass

        MegaPatch.it(SomeLock)

        lock = SomeLock()

        # since logic is mocked out, should not raise
        with lock:
            with lock:
                pass

    def test_setting_return_value_for_non_context_manager(self) -> None:
        with pytest.raises(ValueError):
            MegaPatch.it(Foo).set_context_manager_return_value("foo")

    def test_setting_side_effect_for_non_context_manager(self) -> None:
        with pytest.raises(ValueError):
            MegaPatch.it(Foo).set_context_manager_side_effect(Exception())

    def test_setting_exit_side_effect_for_non_context_manager(self) -> None:
        with pytest.raises(ValueError):
            MegaPatch.it(Foo).set_context_manager_exit_side_effect(Exception())


class TestMegaPatchAsContextManager:
    def test_when_autostart_left_to_default(self) -> None:
        with MegaPatch.it(Foo.some_method, return_value="val"):
            assert Foo("s").some_method() == "val"

        assert Foo("s").some_method() == "value"

    def test_when_autostart_is_false(self) -> None:
        patch = MegaPatch.it(Foo.some_method, return_value="val", autostart=False)
        with patch:
            assert Foo("s").some_method() == "val"

        assert Foo("s").some_method() == "value"


class TestMegaPatchAsFunctionDecorator:
    def test_when_autostart_left_to_default(self) -> None:
        @MegaPatch.it(Foo.some_method, return_value="val")
        def test() -> None:
            assert Foo("s").some_method() == "val"

        test()

        assert Foo("s").some_method() == "value"

    def test_when_autostart_is_false(self) -> None:
        patch = MegaPatch.it(Foo.some_method, return_value="val")

        @patch
        def test() -> None:
            assert Foo("s").some_method() == "val"

        test()

        assert Foo("s").some_method() == "value"

    def test_when_exception_thrown(self) -> None:
        @MegaPatch.it(Foo.some_method, return_value="val")
        def test() -> None:
            raise Exception("Err")

        with pytest.raises(Exception):
            test()

        assert Foo("s").some_method() == "value"


class TestMegaPatchNames:
    def test_megapatch_class(self) -> None:
        patch = MegaPatch.it(Foo)

        assert "name='Foo'" in str(patch.mock)

    def test_megapatch_class_instance(self) -> None:
        patch = MegaPatch.it(Foo)

        assert "name='Foo()'" in str(patch.return_value)

    @pytest.mark.xfail
    def test_megapatch_method(self) -> None:
        # this doesn't work as expected because autospec creates a function
        # that bypasses MegaMock logic and returns MagicMock
        patch = MegaPatch.it(Foo.some_method)
        assert "name='Foo.some_method'" in str(patch.return_value)


class TestMegaPatchNewContext:
    def test_new_context_with_context_manager(self) -> None:
        context = MegaPatch.new_context()
        with context:
            assert len([x for x in MegaPatch.context_stack if x is context]) == 1
