from typing import Any, Callable, Sequence, cast

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

    def __init__(self, func: Callable) -> None:
        self._func = func

    def called_once_with(self, *args, **kwargs) -> bool:
        """
        Return true if the mock was called exactly once and with the specified
        arguments
        """
        try:
            cast(MegaMock, self._func).assert_called_once_with(*args, **kwargs)
        except AssertionError:
            return False
        return True

    def called_once(self) -> bool:
        """
        Return true if the mock was called exactly once
        """
        try:
            cast(MegaMock, self._func).assert_called_once()
        except AssertionError:
            return False
        return True

    def called(self) -> bool:
        """
        Return true if the mock was called
        """
        return cast(MegaMock, self._func).called

    def not_called(self) -> bool:
        """
        Return true if the mock was not called
        """
        try:
            cast(MegaMock, self._func).assert_not_called()
        except AssertionError:
            return False
        return True

    def called_with(self, *args, **kwargs) -> bool:
        """
        Return true if the last call made to the mock was with the specified
        arguments
        """
        try:
            cast(MegaMock, self._func).assert_called_with(*args, **kwargs)
        except AssertionError:
            return False
        return True

    def any_call(self, *args, **kwargs) -> bool:
        """
        Return true if the mock was called with the specified arguments
        at any point in time
        """
        try:
            cast(MegaMock, self._func).assert_any_call(*args, **kwargs)
        except AssertionError:
            return False
        return True

    def has_calls(self, calls: Sequence[Call], any_order=False) -> bool:
        """
        Return true if all of the given calls were made.

        If any_order is true, the calls can be made in any order.

        Extra calls are ignored.
        """
        try:
            cast(MegaMock, self._func).assert_has_calls(calls, any_order)
        except AssertionError:
            return False
        return True

    @property
    def call_args(self) -> Call:
        """
        Return the last call made to the mock
        """
        return cast(MegaMock, self._func).call_args

    @property
    def call_args_list(self) -> list[Call]:
        """
        Return the list of all calls made to the mock
        """
        return cast(MegaMock, self._func).call_args_list

    @property
    def call_count(self) -> int:
        """
        Return the number of times the mock was called
        """
        return cast(MegaMock, self._func).call_count

    def use_real_logic(self) -> None:
        """
        Helper function to have a MegaMock object use the real logic
        """
        self.set_return_value(UseRealLogic)

    def set_return_value(self, value: Any) -> None:
        """
        Helper function to set the return value of a function, when it has
        already been cast to the actual function
        """
        cast(MegaMock, self._func).return_value = value
