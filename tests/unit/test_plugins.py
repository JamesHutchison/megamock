from tests.unit.simple_app.for_autouse_1 import get_value


class TestPytestPlugin:
    def test_import_invoked_early_enough(self) -> None:
        assert get_value() == "modified"
