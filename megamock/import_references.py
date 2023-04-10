from collections import defaultdict
from types import ModuleType


class References:
    # (module_path, original_name, named_as)
    references: dict[str, dict[str, tuple]] = defaultdict(dict)
    # (module_path, original_name)
    reverse_references: dict = defaultdict(lambda: defaultdict(set))
    # renames
    renames: dict[tuple[str, str], str] = {}

    @staticmethod
    def add_reference(
        module: ModuleType,
        calling_module: ModuleType,
        original_name: str,
        named_as: str,
    ) -> None:
        module_path = module.__name__
        References.references[calling_module.__name__][named_as] = (
            module_path,
            original_name,
            # named_as,
        )
        base_original_name = original_name.split(".")[0]
        References.reverse_references[module_path][base_original_name].add(
            (calling_module.__name__, named_as)
        )
        if original_name != named_as:
            References.renames[(calling_module.__name__, named_as)] = original_name

    @staticmethod
    def get_references(module_name: str, original_name: str) -> set:
        val = References.references[module_name].get(original_name)
        if not val:
            return set()
        return {(val[0], val[1])}

    @staticmethod
    def get_reverse_references(module_name: str, original_name: str) -> set:
        components = original_name.split(".", 0)
        if len(components) > 1:
            base_name, right_side = components[0], [".".join(components[1:])]
        else:
            base_name = components[0]
            right_side = []
        return {
            (x[0], ".".join([x[1]] + right_side))
            for x in References.reverse_references[module_name].get(base_name, set())
        }

    @staticmethod
    def get_original_name(module_name: str, named_as: str) -> str:
        return References.renames.get((module_name, named_as), named_as)
