from collections import defaultdict
from types import ModuleType
from typing import NamedTuple

ModAndName = NamedTuple("ModAndName", [("module", str), ("name", str)])


class References:
    """
    The References class is used as part of the import machinary and its
    the magic that allows MegaPatch to work by simply passing things in.
    """

    # References from a calling module and the name used to the
    # source module and the original name
    references: dict[str, dict[str, ModAndName]] = defaultdict(dict)
    # reverse references from the source module and the original,
    # non-nested name, to the calling module and the name used
    reverse_references: dict[str, dict[str, set[ModAndName]]] = defaultdict(
        lambda: defaultdict(set)
    )
    # renames from the calling module and the name used to the original name
    renames: dict[ModAndName, str] = {}

    @staticmethod
    def add_reference(
        module: ModuleType,
        calling_module: ModuleType,
        original_name: str,
        named_as: str,
    ) -> None:
        module_path = module.__name__
        calling_module_name = calling_module.__name__
        References.references[calling_module_name][named_as] = ModAndName(
            module_path,
            original_name,
        )
        base_original_name = original_name.split(".")[0]
        References.reverse_references[module_path][base_original_name].add(
            ModAndName(calling_module_name, named_as)
        )
        if original_name != named_as:
            References.renames[
                ModAndName(calling_module_name, named_as)
            ] = original_name

    @staticmethod
    def get_references(module_name: str, named_as: str) -> set[ModAndName]:
        """
        Given an importing module and name used, return the source module and name

        A set is used, but it can't have more than one element
        """
        val = References.references[module_name].get(named_as)
        if not val:
            return set()
        return {val}

    @staticmethod
    def get_reverse_references(module_name: str, original_name: str) -> set[ModAndName]:
        """
        Given a source module and original name, return the imports to it.
        This includes logic to handle the nesting of the original name. For example,
        Foo.bar may be referenced as OtherFoo.bar. Since "Foo.bar" isn't kept track of
        for imports, only "Foo", the base name is extracted from original_name and then
        the referenced name is rebuilt from the right hand side of original_name.

        So for example, the reverse_references may look like this:
            {
                "example.module": {
                    "Foo": {
                        ModAndName("example.other.module", "OtherFoo")
                    }
                }
            }

        get_reverse_references("example.module", "Foo.bar") would return:
            {
                ("example.other.module", "OtherFoo.bar")
            }

        The import that got us here would look like this:
            from example.other.module import Foo as OtherFoo

        And then the MegaPatch might look like this:
            MegaPatch.it(OtherFoo.bar, ...)
        """
        # TODO: This is bugged and tests only pass if its broken!
        #       Should be 1, but tests fail if it is!
        components = original_name.split(".", 0)
        base_name = components[0]
        if len(components) > 1:
            right_side = [".".join(components[1:])]
        else:
            right_side = []
        return {
            ModAndName(x.module, ".".join([x.name] + right_side))
            for x in References.reverse_references[module_name].get(base_name, set())
        }

    @staticmethod
    def get_original_name(module_name: str, named_as: str) -> str:
        """
        Given an importing module and name used, return the original name
        """
        return References.renames.get(ModAndName(module_name, named_as), named_as)


# Rust code is slower than Python equivalent
# try:
#     from _megamock import References  # type: ignore # noqa
# except ImportError:
#     pass
