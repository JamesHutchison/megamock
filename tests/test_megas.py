from megamock.megamocks import MegaMock
from megamock.megas import Mega


class TestMega:
    class TestCalledOnceWith:
        def test_return_true(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)

            assert Mega(mock).called_once_with(1, 2, 3)

        def test_return_false(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)

            assert Mega(mock).called_once_with("foo") is False
