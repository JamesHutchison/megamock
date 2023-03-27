from typing import Any
import pytest

from megamock.megapatches import MegaPatch


def pytest_sessionstart(*args, **kwargs) -> None:
    import megamock

    megamock.start_import_mod()


def pytest_addoption(parser: Any) -> None:
    parser.addoption(
        "--do_not_autostop_megapatches",
        help="Disable autostopping MegaPatches after every test",
        action="store",
        default=False,
    )


@pytest.fixture(autouse=True)
def stop_all_megapatches(request) -> None:
    if not request.config.getoption("--do_not_autostop_megapatches"):
        MegaPatch.stop_all()


# swap out default mocker if pytest-mock is installed
try:
    from pytest_mock import MockerFixture  # type: ignore  # noqa  # test for install

    @pytest.fixture(autouse=True, scope="session")
    def use_pytest_mocker(session_mocker: MockerFixture) -> None:
        MegaPatch.default_mocker = session_mocker

except ImportError:
    pass  # not installed
