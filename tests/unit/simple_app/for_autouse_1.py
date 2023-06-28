from tests.unit.simple_app.for_autouse_2 import modified_function


def get_value() -> str:
    return modified_function()
