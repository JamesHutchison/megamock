from megamock.megamocks import MegaMock
from megamock.megas import Mega
from megamock.type_util import call


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

    class TestCalledOnce:
        def test_return_true(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)

            assert Mega(mock).called_once()

        def test_return_false(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)
            mock(1, 2, 3)

            assert Mega(mock).called_once() is False

    class TestCalled:
        def test_return_true(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)

            assert Mega(mock).called()

        def test_return_false(self) -> None:
            mock = MegaMock()

            assert Mega(mock).called() is False

    class TestNotCalled:
        def test_return_true(self) -> None:
            mock = MegaMock()

            assert Mega(mock).not_called()

        def test_return_false(self) -> None:
            mock = MegaMock()
            mock()

            assert Mega(mock).not_called() is False

    class TestCalledWith:
        def test_return_true(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)

            assert Mega(mock).called_with(1, 2, 3)

        def test_return_false(self) -> None:
            mock = MegaMock()
            mock(4, 5, 6)

            assert Mega(mock).called_with(1, 2, 3) is False

    class TestAnyCall:
        def test_return_true(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)
            mock(4, 5, 6)

            assert Mega(mock).any_call(4, 5, 6)

        def test_return_false(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)

            assert Mega(mock).any_call(4, 5, 6) is False

    class TestHasCalls:
        def test_return_true(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)
            mock(4, 5, 6)

            assert Mega(mock).has_calls([call(4, 5, 6), call(1, 2, 3)], any_order=True)

        def test_return_false(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)

            assert Mega(mock).has_calls([call(4, 5, 6)], any_order=True) is False

    class TestCallArgs:
        def test_call_args(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)
            mock(4, 5, 6)

            assert Mega(mock).call_args == call(4, 5, 6)

    class TestCallArgsList:
        def test_call_args_list(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)
            mock(4, 5, 6)

            assert Mega(mock).call_args_list == [call(1, 2, 3), call(4, 5, 6)]

    class TestCallCount:
        def test_call_count(self) -> None:
            mock = MegaMock()
            mock(1, 2, 3)
            mock(4, 5, 6)

            assert Mega(mock).call_count == 2
