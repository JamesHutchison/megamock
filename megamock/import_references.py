from collections import defaultdict
import inspect


class References:
    references: dict = defaultdict(dict)
    reverse_references: dict = defaultdict(lambda: defaultdict(set))

    @staticmethod
    def add_reference(module, calling_module, key) -> None:
        module_path = module.__name__
        References.references[calling_module.__name__][key] = (module_path, key)
        References.reverse_references[module_path][key].add(calling_module.__name__)

    def get_references(module_name, key) -> set:
        val = References.references[module_name].get(key)
        if not val:
            return set()
        return {val[0]}
