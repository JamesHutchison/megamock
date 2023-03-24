import asyncio
import inspect
from typing import cast
from unittest import mock

import pytest

from megamock import MegaMock
from megamock.megamocks import (
    AsyncMegaMock,
    AttributeTrackingBase,
    NonCallableMegaMock,
    UseRealLogic,
    set_return_value,
)
from megamock.megapatches import MegaPatch
from tests.conftest import SomeClass
from tests.simple_app.bar import Bar
from tests.simple_app.foo import Foo


class TestAttributeTrackingBase:
    class Sample(AttributeTrackingBase):
        def __init__(self) -> None:
            import traceback

            self.stacktrace = traceback.extract_stack()[::-1]

    def test_top_of_stacktrace_breaks_up_lines(self) -> None:
        obj = TestAttributeTrackingBase.Sample()
        assert len(obj.top_of_stacktrace) == 10

    def test_top_of_stacktrace_shortens_path(self) -> None:
        obj = TestAttributeTrackingBase.Sample()
        assert obj.top_of_stacktrace[0].startswith("...")

    def test_top_of_stacktrace_root_folder(self) -> None:
        obj = TestAttributeTrackingBase.Sample()

        MegaPatch.it(
            AttributeTrackingBase.format_stacktrace,
            return_value=['"file_in_root.py", line 1,  something something'],
        )
        assert obj.top_of_stacktrace[0].startswith('"file_in_root.py')


class TestMegaMock:
    def test_allows_no_args(self) -> None:
        MegaMock()

    def test_return_value_when_no_args(self) -> None:
        assert isinstance(MegaMock()(), MegaMock)

    def test_side_effect_value(self) -> None:
        mega_mock = MegaMock(side_effect=lambda: 5)

        assert mega_mock() == 5

    def test_function_spec_with_return_value(self) -> None:
        def some_func(val: str) -> str:
            return val

        mega_mock = MegaMock(some_func, return_value="foo")
        assert mega_mock("input val") == "foo"

        with pytest.raises(TypeError):
            mega_mock()

    def test_call_args_update(self) -> None:
        mega_mock = MegaMock()
        mega_mock()

        assert mega_mock.call_count == 1
        assert mega_mock.call_args_list == [mock.call()]

    def test_not_awaitable(self) -> None:
        assert asyncio.iscoroutinefunction(MegaMock()) is False
        assert inspect.isawaitable(MegaMock()) is False

    async def test_when_async_function_is_spec_then_awaitable(self) -> None:
        async def some_func() -> str:
            return "s"

        mega_mock = MegaMock(some_func)
        assert asyncio.iscoroutinefunction(mega_mock) is True
        assert inspect.isawaitable(mega_mock()) is True

    def test_assigning_return_value(self) -> None:
        mega_mock = MegaMock(Foo)
        set_return_value(mega_mock.megacast.some_method, "foo")

        assert mega_mock.some_method() == "foo"
        assert mega_mock.megacast.some_method() == "foo"

    def test_allows_for_setting_different_type(self) -> None:
        mega_mock: Foo = MegaMock(Foo)  # mypy should not care

        assert mega_mock.z

    def test_assert_called_once_with(self) -> None:
        mega_mock = MegaMock(Foo, instance=False)

        mega_mock("s")

        mega_mock.assert_called_once_with("s")

        with pytest.raises(AssertionError):
            mega_mock.assert_called_once_with("t")

    def test_return_value_equality_set_in_params(self) -> None:
        result = MegaMock()
        callable = MegaMock(return_value=result)
        callable.return_value = result

        assert callable("foo", "bar") is result

    def test_return_value_equality_set_via_attribute(self) -> None:
        result = MegaMock()
        callable = MegaMock()
        callable.return_value = result

        assert callable("foo", "bar") is result

    class TestMockingAClass:
        def test_classes_default_to_instance(self) -> None:
            mock_instance: SomeClass = MegaMock(SomeClass)

            with pytest.raises(AttributeError):
                mock_instance.does_not_exist  # type: ignore

            mock_instance.b()

        def test_can_create_mock_for_class_itself(self) -> None:
            mock_class: type[SomeClass] = MegaMock(SomeClass, instance=False)

            mock_class.c

        def test_mock_classes_do_not_have_undefined_attributes(self) -> None:
            mock_class: type[SomeClass] = MegaMock(SomeClass, instance=False)

            with pytest.raises(AttributeError):
                mock_class.a

        def test_delimited_attributes_are_allowed_if_spec_set_is_true(self) -> None:
            mock_instance: SomeClass = MegaMock(SomeClass, spec_set=True)

            mock_instance.a = "some str"

        def test_spec_set_with_annotations_enforces_type(self) -> None:
            mock_instance: SomeClass = MegaMock(SomeClass, spec_set=True)

            with pytest.raises(TypeError) as exc:
                mock_instance.a = 12345  # type: ignore

            assert str(exc.value) == "12345 is not an instance of str | None"

        def test_spec_set_with_annotations_allows_mock_objects(self) -> None:
            mock_instance: SomeClass = MegaMock(SomeClass, spec_set=True)

            mock_instance.a = MegaMock(str)

        def test_spec_set_defaults_to_true(self) -> None:
            mock_instance: SomeClass = MegaMock(SomeClass, spec_set=True, instance=True)

            with pytest.raises(AttributeError):
                mock_instance.does_not_exist = 5  # type: ignore

        def test_callable_classes_are_callable(self) -> None:
            mock_instance = MegaMock(Bar)

            mock_instance()

        # The return type for callable is not inspected, so a generic MegaMock
        # is always used. To support this, the annotated return type for __call__
        # would need to be inspected
        # Issue https://github.com/JamesHutchison/megamock/issues/14
        @pytest.mark.xfail
        def test_callable_result_has_same_callable_property(self) -> None:
            mock_instance = MegaMock(Bar)

            with pytest.raises(TypeError):
                mock_instance()()

        def test_noncallable_classes_are_not_callable(self) -> None:
            mock_instance = MegaMock(Foo)

            with pytest.raises(TypeError):
                mock_instance()

    class TestFromLegacyMock:
        def test_when_autospec_used_on_class(self) -> None:
            legacy_mock = mock.create_autospec(SomeClass)
            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock.megamock.spec is SomeClass
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

            assert isinstance(mega_mock.return_value, NonCallableMegaMock)

        def test_when_regular_mock(self) -> None:

            legacy_mock = mock.Mock()
            legacy_mock.b = mock.Mock()
            legacy_mock.c = mock.NonCallableMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock.megamock.spec is SomeClass
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

        def test_when_magic_mock(self) -> None:
            legacy_mock = mock.MagicMock()
            legacy_mock.b = mock.MagicMock()
            legacy_mock.c = mock.NonCallableMagicMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock.megamock.spec is SomeClass
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

        def test_when_non_callable_mock(self) -> None:
            legacy_mock = mock.NonCallableMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec="a")

            assert isinstance(mega_mock, NonCallableMegaMock)

        def test_when_non_callable_magic_mock(self) -> None:
            legacy_mock = mock.NonCallableMagicMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec="a")

            assert isinstance(mega_mock, NonCallableMegaMock)

    class TestMegaMockAttributeAssignment:
        def test_grabs_expected_stacktrace(self) -> None:
            mega_mock: MegaMock = MegaMock()

            mega_mock.foo = "bar"

            assert "foo" in mega_mock.megamock.attr_assignments
            stacktrace = mega_mock.megamock.attr_assignments["foo"][0].stacktrace
            assert len(stacktrace) > 5
            for frame in stacktrace:
                assert "/megamocks.py" not in frame.filename

        def test_multiple_assignments(self) -> None:
            mega_mock: MegaMock = MegaMock()
            mega_mock.foo = "foo"
            mega_mock.bar = "bar"

            mega_mock.foo = "second"

            assert len(mega_mock.megamock.attr_assignments["foo"]) == 2
            assert len(mega_mock.megamock.attr_assignments["bar"]) == 1

            assert mega_mock.megamock.attr_assignments["foo"][0].attr_value == "foo"
            assert mega_mock.megamock.attr_assignments["foo"][1].attr_value == "second"

    class TestWraps:
        def test_wraps_object(self) -> None:
            obj = Foo("s")
            mega_mock = MegaMock(wraps=obj)

            assert mega_mock.some_method() == "value"
            assert len(mega_mock.some_method.call_args_list) == 1

        def test_wraps_has_same_warts_as_magicmock(self) -> None:
            obj = Foo("s")
            mega_mock = MegaMock(wraps=obj)

            assert isinstance(mega_mock.s, MegaMock)

    class TestSpy:
        @pytest.fixture(autouse=True)
        def setup(self) -> None:
            self.obj = Foo("s")
            self.mega_mock = MegaMock(spy=self.obj)

        def test_equivalent_to_wraps_for_methods(self) -> None:
            assert self.mega_mock.some_method() == "value"
            assert len(self.mega_mock.some_method.call_args_list) == 1

        def test_supports_properties(self) -> None:
            self.mega_mock._s = "str"
            assert self.mega_mock.s == "str"

        def test_supports_attributes(self) -> None:
            assert self.mega_mock._s == "s"

        def test_spies_on_attribute_access(self) -> None:
            mega_mock = self.mega_mock
            mega_mock.z
            mega_mock.moo
            mega_mock.helpful_manager

            assert len(mega_mock.megamock.spied_access) == 3
            assert (
                mega_mock.megamock.spied_access["z"][0]
                .stacktrace[0]
                .filename.endswith("test_megamocks.py")
            )

        def test_supports_megacast(self) -> None:
            assert self.mega_mock.megacast.some_method() == "value"

    class TestAsyncMock:
        async def test_async_mock_basics(self) -> None:
            mega_mock: AsyncMegaMock = AsyncMegaMock()
            assert asyncio.iscoroutinefunction(mega_mock) is True
            assert inspect.isawaitable(mega_mock()) is True

            await mega_mock()
            assert mega_mock.await_count == 1

        async def test_function_side_effect(self) -> None:
            mega_mock: AsyncMegaMock = AsyncMegaMock(side_effect=lambda: 5)

            result = await mega_mock()
            assert result == 5
            assert mega_mock.call_count == 1

        async def test_exception_side_effect(self) -> None:
            mega_mock: AsyncMegaMock = AsyncMegaMock(side_effect=Exception("whoops!"))

            with pytest.raises(Exception) as exc:
                await mega_mock()

            assert str(exc.value) == "whoops!"

        async def test_iterable_side_effect(self) -> None:
            mega_mock: AsyncMegaMock = AsyncMegaMock(side_effect=[1, 2, 3])

            first = await mega_mock()
            second = await mega_mock()
            third = await mega_mock()

            assert [first, second, third] == [1, 2, 3]

        async def test_return_value_provided(self) -> None:
            mega_mock: AsyncMegaMock = AsyncMegaMock(return_value=25)

            assert await mega_mock() == 25

        async def test_defaults_to_async_mega_mock_return(self) -> None:
            assert isinstance(AsyncMegaMock(), AsyncMegaMock)

            await AsyncMegaMock()()

        async def test_altering_return_value(self) -> None:
            mega_mock: AsyncMegaMock = AsyncMegaMock()
            mega_mock.return_value.return_value = 5

            result = await mega_mock()
            assert await result() == 5

        async def test_async_spec(self) -> None:
            async def some_func(val: str) -> str:
                return val

            mega_mock: AsyncMegaMock = AsyncMegaMock(
                some_func, return_value="actual return"
            )
            assert await mega_mock("input val") == "actual return"

            with pytest.raises(TypeError):
                await mega_mock()

        async def test_await_args(self) -> None:
            mega_mock: AsyncMegaMock = AsyncMegaMock()

            await mega_mock("foo", keyword_arg="bar")
            assert mega_mock.await_args == mock.call("foo", keyword_arg="bar")

        async def test_await_args_list(self) -> None:
            mega_mock: AsyncMegaMock = AsyncMegaMock()

            await mega_mock("first")
            await mega_mock("second", keyword_arg="kwsecond")

            expected_await_args_list = [
                mock.call("first"),
                mock.call("second", keyword_arg="kwsecond"),
            ]
            assert mega_mock.await_args_list == expected_await_args_list

    class TestUseRealLogic:
        def test_will_use_real_method_values(self) -> None:
            mega_mock = MegaMock(Foo("s"), spec_set=False)

            # check preconditions
            assert isinstance(mega_mock.some_method(), MegaMock)

            mega_mock.some_method.return_value = UseRealLogic

            assert mega_mock.some_method() == "value"

        def test_real_logic_uses_mock_object_values(self) -> None:
            mega_mock = MegaMock(Foo("s"))
            mega_mock.moo = "fox"
            mega_mock.what_moos.return_value = UseRealLogic

            assert mega_mock.what_moos() == "The fox moos"

        def test_real_logic_with_class_instance_shortcut(self) -> None:
            mega_mock = MegaMock(Foo)
            mega_mock.moo = "fox"
            mega_mock.what_moos.return_value = UseRealLogic

            assert mega_mock.what_moos() == "The fox moos"

        def test_function_call_on_mock_object(self) -> None:
            mega_mock = MegaMock(Foo("s"))
            mega_mock.moo = "fox"
            UseRealLogic(mega_mock.what_moos)

            assert mega_mock.what_moos() == "The fox moos"

        def test_function_call_on_cast_object(self) -> None:
            mega_mock = MegaMock(Foo("s"))
            mega_mock.moo = "fox"
            UseRealLogic(mega_mock.megacast.what_moos)

            assert mega_mock.megacast.what_moos() == "The fox moos"

    class TestMegaCast:
        def test_cast_types_to_the_spec_with_type(self) -> None:
            mega_mock = MegaMock(Foo)
            mega_mock.z = "z"

            assert mega_mock.megacast.z == "z"

        def test_cast_types_to_the_spec_with_instance(self) -> None:
            mega_mock = MegaMock(Foo("s"))
            mega_mock.z = "z"

            assert mega_mock.megacast.z == "z"

        def test_using_function(self) -> None:
            def some_func(val: str) -> str:
                return val

            mega_mock = MegaMock(some_func)
            mega_mock.megacast.__module__  # should have no mypy errors

    class TestMegaInstance:
        def test_using_class(self) -> None:
            mega_mock = MegaMock(Foo, instance=False)

            mega_mock.megainstance.s  # should have no mypy errors
            mega_mock.megainstance.moo = "fox"

            # check preconditions
            assert cast(Foo, mega_mock("s")).moo == "fox"  # should not error

            mega_mock.megainstance is Foo("s")

        def test_errors_if_not_a_class(self) -> None:
            mega_mock = MegaMock(Foo, instance=True)

            with pytest.raises(Exception) as exc:
                mega_mock.megainstance

            assert (
                str(exc.value)
                == "The megainstance property was intended for class mocks"
            )

        def test_calling_method_from_mega_instance(self) -> None:
            mega_mock = MegaMock(Foo, instance=False)

            mega_mock.megainstance.some_method()
