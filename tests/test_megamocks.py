from unittest import mock

import pytest

from megamock import MegaMock
from megamock.megamocks import NonCallableMegaMock
from tests.conftest import SomeClass
from tests.simple_app.bar import Bar
from tests.simple_app.foo import Foo


class TestMegaMock:
    def test_allows_no_args(self) -> None:
        MegaMock()

    def test_return_value_when_no_args(self) -> None:
        assert isinstance(MegaMock()(), MegaMock)

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
            mega_mock: MegaMock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock.megamock_spec is SomeClass
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

            assert isinstance(mega_mock.return_value, NonCallableMegaMock)

        def test_when_regular_mock(self) -> None:

            legacy_mock = mock.Mock()
            legacy_mock.b = mock.Mock()
            legacy_mock.c = mock.NonCallableMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock.megamock_spec is SomeClass
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

        def test_when_magic_mock(self) -> None:
            legacy_mock = mock.MagicMock()
            legacy_mock.b = mock.MagicMock()
            legacy_mock.c = mock.NonCallableMagicMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock.megamock_spec is SomeClass
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
            mega_mock = MegaMock()

            mega_mock.foo = "bar"

            assert "foo" in mega_mock.megamock_attr_assignments
            stacktrace = mega_mock.megamock_attr_assignments["foo"][0].stacktrace
            assert len(stacktrace) > 5
            for frame in stacktrace:
                assert "/megamocks.py" not in frame.filename

        def test_multiple_assignments(self) -> None:
            mega_mock = MegaMock()
            mega_mock.foo = "foo"
            mega_mock.bar = "bar"

            mega_mock.foo = "second"

            assert len(mega_mock.megamock_attr_assignments["foo"]) == 2
            assert len(mega_mock.megamock_attr_assignments["bar"]) == 1

            assert mega_mock.megamock_attr_assignments["foo"][0].attr_value == "foo"
            assert mega_mock.megamock_attr_assignments["foo"][1].attr_value == "second"

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
