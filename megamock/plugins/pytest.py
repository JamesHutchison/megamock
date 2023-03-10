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
