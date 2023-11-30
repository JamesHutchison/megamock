from typing import Iterable

import pytest

from megamock.megapatches import MegaPatch


def pytest_load_initial_conftests(*args, **kwargs) -> None:
    import megamock

    megamock.start_import_mod()


@pytest.fixture(autouse=True)
def megapatch_contexts() -> Iterable:
    with MegaPatch.new_context():
        yield


@pytest.fixture(scope="session", autouse=True)
def megapatch_session_contexts() -> Iterable:
    with MegaPatch.new_context():
        yield


# swap out default mocker if pytest-mock is installed
try:
    from pytest_mock import MockerFixture  # type: ignore  # noqa  # test for install

    @pytest.fixture(autouse=True, scope="session")
    def use_pytest_mocker(session_mocker: MockerFixture) -> None:
        MegaPatch.default_mocker = session_mocker

except ImportError:
    pass  # not installed
