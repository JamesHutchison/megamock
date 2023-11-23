class NestedParent:
    class NestedChild:
        class AnotherNestedChild:
            a = "a"

            def z(self) -> str:
                return "z"

            @staticmethod
            def static_z() -> str:
                return "static_z"
