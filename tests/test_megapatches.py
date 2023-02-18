import pytest
from megamock import MegaPatch
from megamock.megapatches import MegaMock
from tests.simple_app.foo import Foo, bar
from tests.simple_app import foo
from tests.simple_app.helpful_manager import HelpfulManager
from tests.simple_app.nested_classes import NestedParent
from tests.simple_app.uses_nested_classes import (
    get_nested_class_function_value,
    get_nested_class_attribute_value,
)


class TestMegaPatchPatching:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        MegaPatch.stop_all()

    def test_patch_class_itself(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.new_value.z = "a"

        assert Foo.z == "a"

    def test_patch_class_instance(self) -> None:
        patch = MegaPatch.it(Foo)
        patch.return_value.z = "b"

        assert Foo("").z == "b"

    def test_patch_global_module_variable(self) -> None:
        MegaPatch.it(bar, new="a")

        assert foo.bar == "a"

    def test_patch_class_attribute(self) -> None:
        MegaPatch.it(Foo.moo, new="dog")

        assert Foo.moo == "dog"

    def test_patch_megamock_object(self) -> None:
        MegaPatch.it(Foo)
        MegaPatch.it(Foo.moo, new="dog")

    def test_patch_property(self) -> None:
        expected = "dog"
        MegaPatch.it(Foo.moo, new=expected)

        assert Foo("").moo == expected

    def test_patch_cached_property(self) -> None:
        expected = MegaMock(spec=HelpfulManager)
        MegaPatch.it(Foo.helpful_manager, new=expected)

        assert Foo("").helpful_manager is expected

    def test_patch_nested_class_function(self) -> None:
        MegaPatch.it(NestedParent.NestedChild.AnotherNestedChild.z, return_value="a")

        assert get_nested_class_function_value() == "a"

    def test_patch_nested_class_attribute(self) -> None:
        MegaPatch.it(NestedParent.NestedChild.AnotherNestedChild.a, new="z")

        assert get_nested_class_attribute_value() == "z"


class TestMegaPatchAutoStart:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        MegaPatch.stop_all()

    def test_enabled_by_default(self) -> None:
        MegaPatch.it(Foo.helpful_manager, new="something")

        assert Foo("").helpful_manager == "something"

    def test_can_be_disabled(self) -> None:
        MegaPatch.it(Foo.helpful_manager, new="something", autostart=False)

        assert isinstance(Foo("").helpful_manager, HelpfulManager)


class TestMegaPatchSpec:
    def test_uses_autospec(self) -> None:
        MegaPatch.it(Foo)

        with pytest.raises(TypeError):
            Foo()  # type: ignore

    def test_can_override_autospec(self) -> None:
        MegaPatch.it(Foo, autospec=False)

        Foo()  # type: ignore
