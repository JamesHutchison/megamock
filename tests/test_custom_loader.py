import megamock


class TestCustomLoader:
    def test_classes_is_instance_of_class(self) -> None:
        import megamock
        from tests.simple_app.foo import Foo

        import tests.simple_app.foo

        assert isinstance(Foo(""), Foo)

    def test_primitives_is_instance_of_primitive(self) -> None:
        pass

    def test_class_name_is_the_same(self) -> None:
        pass

    def test_repr_is_the_same(self) -> None:
        pass

    def test_str_is_the_same(self) -> None:
        pass
