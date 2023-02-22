from tests.simple_app.nested_classes import NestedParent


def get_nested_class_function_value() -> str:
    return NestedParent.NestedChild.AnotherNestedChild().z()


def get_nested_class_attribute_value() -> str:
    return NestedParent.NestedChild.AnotherNestedChild().a
