from tests.unit.simple_app.for_autouse_1 import get_value
from tests.unit.simple_app.for_autouse_2 import session_modified_function


class TestPytestPlugin:
    def test_import_invoked_early_enough(self) -> None:
        assert get_value() == "modified"

    def test_session_modified_fixture(self) -> None:
        assert session_modified_function() == "session_modified"
