import pytest
from megamock import MegaPatch
from megamock.megapatching import MegaMock
from tests.simple_app.foo import Foo, bar
from tests.simple_app import foo
from tests.simple_app.helpful_manager import HelpfulManager


class TestMegaPatchPatching:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        MegaPatch.stop_all()

    def test_patch_class_object(self) -> None:
        mocked = MegaPatch.it(Foo)
        mocked.z = "arrr"

        assert Foo.z == "arrr"

    def test_patch_klass_argument(self) -> None:
        mocked = MegaPatch.it(klass=Foo)
        mocked.zzz = "arrr"

        assert Foo("").zzz == "arrr"

    def test_patch_global_module_variable(self) -> None:
        mocked = MegaPatch.it(bar, new="sooo")

        assert foo.bar == "sooo"

    def test_patch_class_attribute(self) -> None:
        MegaPatch.it(Foo.moo, new="dog")

        assert Foo.moo == "dog"

    def test_patch_megamock_object(self) -> None:
        MegaPatch.it(Foo)
        MegaPatch.it(Foo.moo, new="dog")

    def test_patch_megamock_klass_object(self) -> None:
        mocked_foo = MegaPatch.it(klass=Foo)
        mocked_foo.moo = "dog"

        assert Foo("").moo == "dog"

    def test_patch_property(self) -> None:
        expected = "dog"
        MegaPatch.it(Foo.moo, new=expected)

        assert Foo("").moo == expected

    def test_patch_cached_property(self) -> None:
        expected = MegaMock(spec=HelpfulManager)
        MegaPatch.it(Foo.helpful_manager, new=expected)

        assert Foo("").helpful_manager == expected


class TestMegaPatchAutoStart:
    def test_enabled_by_default(self) -> None:
        MegaPatch.it(Foo.helpful_manager, new="something")

        assert Foo("").helpful_manager == "something"

    def test_can_be_disabled(self) -> None:
        MegaPatch.it(Foo.helpful_manager, new="something", autostart=False)

        assert isinstance(Foo("").helpful_manager, HelpfulManager)


class TestMegaPatchSpec:
    def test_uses_autospec(self) -> None:
        pass

    def test_can_override_autospec(self) -> None:
        pass

    def test_can_provide_spec(self) -> None:
        pass
