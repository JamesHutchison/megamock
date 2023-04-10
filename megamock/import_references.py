from collections import defaultdict
from types import ModuleType


class References:
    # (module_path, named_as, original_name)
    references: dict[str, dict[str, tuple]] = defaultdict(dict)
    # (module_path, original_name)
    reverse_references: dict = defaultdict(lambda: defaultdict(set))

    @staticmethod
    def add_reference(
        module: ModuleType,
        calling_module: ModuleType,
        original_name: str,
        named_as: str,
    ) -> None:
        module_path = module.__name__
        References.references[calling_module.__name__][original_name] = (
            module_path,
            named_as,
            original_name,
        )
        References.reverse_references[module_path][original_name].add(
            (calling_module.__name__, named_as)
        )

    @staticmethod
    def get_references(module_name: str, original_name: str) -> set:
        val = References.references[module_name].get(original_name)
        if not val:
            return set()
        return {(val[0], val[1])}
