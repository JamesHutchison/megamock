from unittest import mock

from megamock import MegaMock
from megamock.megamocks import NonCallableMegaMock


class TestMegaMock:
    class TestFromLegacyMock:
        def test_when_autospec_used_on_class(self, some_object: type) -> None:
            legacy_mock = mock.create_autospec(some_object)
            mega_mock: MegaMock = MegaMock.from_legacy_mock(
                legacy_mock, spec=some_object
            )

            assert mega_mock._megamock_spec is some_object
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

        def test_when_regular_mock(self, some_object: type) -> None:

            legacy_mock = mock.Mock()
            legacy_mock.b = mock.Mock()
            legacy_mock.c = mock.NonCallableMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=some_object)

            assert mega_mock._megamock_spec is some_object
            assert hasattr(mega_mock, "b")

            assert isinstance(mega_mock.b, MegaMock)
            assert isinstance(mega_mock.c, NonCallableMegaMock)

        def test_when_magic_mock(self, some_object: type) -> None:
            legacy_mock = mock.MagicMock()
            legacy_mock.b = mock.MagicMock()
            legacy_mock.c = mock.NonCallableMagicMock()

            mega_mock = MegaMock.from_legacy_mock(legacy_mock, spec=some_object)

            assert mega_mock._megamock_spec is some_object
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
