from unittest import mock

import pytest

from megamock import MegaMock
from megamock.megamocks import NonCallableMegaMock
from tests.conftest import SomeClass


class TestMegaMock:
    def test_allows_no_args(self) -> None:
        MegaMock()

    class TestMockingAClass:
        def test_classes_default_to_instance(self) -> None:
            mock_instance: SomeClass = MegaMock(SomeClass)

            with pytest.raises(AttributeError):
                mock_instance.does_not_exist  # type: ignore

            mock_instance.b()

        def test_annotated_attributes_are_allowed_if_spec_set_is_true(self) -> None:
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

    class TestFromLegacyMock:
        def test_when_autospec_used_on_class(self) -> None:
            legacy_mock = mock.create_autospec(SomeClass)
            mega_mock: MegaMock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock._megamock_spec is SomeClass
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

        def test_when_regular_mock(self) -> None:

            legacy_mock = mock.Mock()
            legacy_mock.b = mock.Mock()
            legacy_mock.c = mock.NonCallableMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock._megamock_spec is SomeClass
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

        def test_when_magic_mock(self) -> None:
            legacy_mock = mock.MagicMock()
            legacy_mock.b = mock.MagicMock()
            legacy_mock.c = mock.NonCallableMagicMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=SomeClass)

            assert mega_mock._megamock_spec is SomeClass
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
