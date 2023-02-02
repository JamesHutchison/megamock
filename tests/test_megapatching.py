from megamock import MegaPatch
from tests.simple_app.foo import Foo


class TestMegaPatchPatching:
    def test_patch_class(self) -> None:
        mocked = MegaPatch.it(Foo)
        mocked.return_value.s = "arrr"

        f = Foo("")
        assert f.s == "arrr"

    def test_patch_global_module_variable(self) -> None:
        pass

    def test_patch_class_attribute(self) -> None:
        pass


class TestMegaPatchAutoStart:
    def test_enabled_by_default(self) -> None:
        pass

    def test_can_be_disabled(self) -> None:
        pass


class TestMegaPatchSpec:
    def test_uses_autospec(self) -> None:
        pass

    def test_can_override_autospec(self) -> None:
        pass

    def test_can_provide_spec(self) -> None:
        pass
