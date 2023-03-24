from typing import Any, Callable, cast
from unittest.mock import _Call

from megamock.megamocks import MegaMock, UseRealLogic


class Mega:
    def __init__(self, func: Callable) -> None:
        self._func = func

    def called_once_with(self, *args, **kwargs) -> bool:
        try:
            cast(MegaMock, self._func).assert_called_once_with(*args, **kwargs)
        except AssertionError:
            return False
        return True

    def called_once(self) -> bool:
        try:
            cast(MegaMock, self._func).assert_called_once()
        except AssertionError:
            return False
        return True

    def called(self) -> bool:
        return cast(MegaMock, self._func).called

    def not_called(self) -> bool:
        try:
            cast(MegaMock, self._func).assert_not_called()
        except AssertionError:
            return False
        return True

    def called_with(self, *args, **kwargs) -> bool:
        try:
            cast(MegaMock, self._func).assert_called_with(*args, **kwargs)
        except AssertionError:
            return False
        return True

    def called_with_any(self, *args, **kwargs) -> bool:
        try:
            cast(MegaMock, self._func).assert_called_with(*args, **kwargs)
        except AssertionError:
            return False
        return True

    def any_call(self) -> bool:
        try:
            cast(MegaMock, self._func).assert_any_call()
        except AssertionError:
            return False
        return True

    def call_args(self) -> _Call:
        return cast(MegaMock, self._func).call_args

    def call_args_list(self) -> list[_Call]:
        return cast(MegaMock, self._func).call_args_list

    def call_count(self) -> int:
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
