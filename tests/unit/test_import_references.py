from megamock.import_references import References
from megamock.megamocks import MegaMock
from megamock.megapatches import MegaPatch
from megamock.megas import Mega


class TestReferences:
    class TestAddReference:
        def test_when_package_is_missing_do_not_add(self) -> None:
            patch = MegaPatch.it(References._add_reference)

            calling_module = MegaMock()
            calling_module.__package__ = ""
            References.add_reference(MegaMock(), calling_module, "orig", "named_as")

            assert Mega(patch.mock).not_called()
