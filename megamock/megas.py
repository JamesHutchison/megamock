from typing import Callable, Sequence, cast

from megamock.megamocks import MegaMock, UseRealLogic
from megamock.type_util import Call


class Mega:
    """
    Wrapper class around callable MegaMock objects. This provides
    a convenience to the developer via autocomplete, a more
    standard interface, and tools for values against cast'ed objects.

    Instead of (does not autocomplete "assert_called_with"):
        mock.my_method.assert_called_with(1, 2, 3)

    Use (autocompletes "assert_called_with"):
        assert Mega(mock.my_method).called_with(1, 2, 3)
    """

    last_assertion_error: AssertionError | None = None

    def __init__(self, func: Callable) -> None:
        self._func = func

    def _check_mock_assertion(self, func: Callable) -> bool:
        try:
            func()
        except AssertionError as err:
            Mega.last_assertion_error = err
            return False
        return True

    @property
    def _mm(self) -> MegaMock:
        """
        Property to shorthand the cast to MegaMock
        """
        return cast(MegaMock, self._func)

    def called_once_with(self, *args, **kwargs) -> bool:
        """
        Return true if the mock was called exactly once and with the specified
        arguments
        """
        return self._check_mock_assertion(
            lambda: self._mm.assert_called_once_with(*args, **kwargs)
        )

    def called_once(self) -> bool:
        """
        Return true if the mock was called exactly once
        """
        return self._check_mock_assertion(lambda: self._mm.assert_called_once())

    def called(self) -> bool:
        """
        Return true if the mock was called
        """
        return self._mm.called

    def not_called(self) -> bool:
        """
        Return true if the mock was not called
        """
        return self._check_mock_assertion(lambda: self._mm.assert_not_called())

    def called_with(self, *args, **kwargs) -> bool:
        """
        Return true if the last call made to the mock was with the specified
        arguments
        """
        return self._check_mock_assertion(
            lambda: self._mm.assert_called_with(*args, **kwargs)
        )

    def any_call(self, *args, **kwargs) -> bool:
        """
        Return true if the mock was called with the specified arguments
        at any point in time
        """
        return self._check_mock_assertion(
            lambda: self._mm.assert_any_call(*args, **kwargs)
        )

    def has_calls(self, calls: Sequence[Call], any_order=False) -> bool:
        """
        Return true if all of the given calls were made.

        If any_order is true, the calls can be made in any order.

        Extra calls are ignored.
        """
        return self._check_mock_assertion(
            lambda: self._mm.assert_has_calls(calls, any_order)
        )

    @property
    def call_args(self) -> Call:
        """
        Return the last call made to the mock
        """
        return self._mm.call_args

    @property
    def call_args_list(self) -> list[Call]:
        """
        Return the list of all calls made to the mock
        """
        return self._mm.call_args_list

    @property
    def call_count(self) -> int:
        """
        Return the number of times the mock was called
        """
        return self._mm.call_count

    def use_real_logic(self) -> None:
        """
        Helper function to have a MegaMock object use the real logic
        """
        self._mm.return_value = UseRealLogic
