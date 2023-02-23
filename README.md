# MegaMock

Pew pew! Patch objects, variables, attributes, etc by passing in the thing in question, rather than passing in dot-annotated paths!
Also sane defaults for mocking behavior!

Supported Python Versions: 3.10+

# Why Use MegaMock?
MegaMock was created to address some shortcomings in the built-in Python library:
- Legacy code holds back "best practice" defaults, so many developers write sub-optimal mocks
  that allow things that should not be allowed. Likewise, writing better mocks are more work,
  so there's a tendency to write simpler code because, at that point in time, the developer
  felt that is all that was needed. MegaMock's simple interface provides sane defaults.
- `mock.patch` is very commonly used, and can work well when `autospec=True`, but has the drawback that
  you need to pass in a string to the thing that is being patched. Most (all?) IDEs do not properly
  recognize these strings as references to the objects that are being patched, and thus automated
  refactoring and reference finding skips them. Likewise, automatically getting a dot referenced path
  to an object is also commonly missing functionality. This all adds additional burden to the developer.
  With `MegaPatch`, you can import an object as you normally would into the test, then pass in thing
  itself you want to patch. This even works for methods, attributes, and nested classes!
- `mock.patch` has a gotcha where the string you provide must match where the reference lives.
  So, for example, if you have in `my_module.py`: `from other_module import Thing`, then doing
  `mock.patch("other_module.Thing")` won't actually work, because the reference in `my_module` still
  points to the original. You can work around this by doing `import other_module` and referencing `Thing`
  by `other_module.Thing`. MegaMock does not have this problem, and it doesn't matter how you import.

## Example Usage

### Production Code
```python
from module.submodule import MyClassToMock


def my_method(...):
    ...
    a_thing = MyClassToMock(...)
    do_something_with_a_thing(a_thing)
    ...


def do_something_with_a_thing(a_thing: MyClassToMock) -> None:
    result = a_thing.some_method(...)
    if result == "a value":
        ...
```

### Test Code
```python
from megamock import MegaPatch
from module.submodule import MyClassToMock


def test_something(...):
    patched = MegaPatch.it(MyClassToMock.some_method)
    patched.return_value = "a value"

    my_method(...)
```

## Documentation

### Installation

`pip install megamock`

### Usage

Import and execution order is important for MegaMock. When running tests, you will need to execute the `start_import_mod`
function prior to importing any production or test code. You will also want it so the loader is not used in production.

With `pytest`, this is easily done by adding a root level `conftest.py` file if it does not exist already, and executing
the function there.

```python
import megamock

megamock.start_import_mod()
```

In tests, the `MegaMock` class replaces the mock classes `MagicMock` and `Mock`. `MegaPatch.it(...)` replaces `patch(...)`.
Currently, there is no substitute for `patch.object` although `MegaPatch.it` should work on global instances (singletons).

```python

from megamock import MegaMock

def test_something(...):
    manager = MegaMock(MyManagerClass)
    service = SomeService(manager)
    ...
```

```python
from elsewhere import Service

from megamock import MegaPatch

def test_something(...):
    patched = MegaPatch.it(Service.make_external_call)
    patched.return_value = SomeValue(...)
    service = SomeService(...)

    code_under_test(service)
    ...
```

You can focus your production code on creating an intuitive, "batteries included" interface for developers
without making compromises for testability.
Please see the guidance section (TODO) for more information on how and when you would use MegaMock.

### Use Case Examples

All use cases below have the following import:

```python
from megamock import MegaMock, MegaPatch
```

Creating a mock instance of a class:

```python
from my_module import MyClass

mock_instance = MegaMock(MyClass)
```

Creating a mock class itself:

```python
from my_module import MyClass

mock_class = MegaMock(MyClass, instance=False)
```

Patching a class method:

```python
from my_module import MyClass

mega_patch = MegaPatch.it(MyClass.my_method, return_value=...)
```

Alternatively:
```python
mega_patch = MegaPatch.it(MyClass.my_method)
mega_patch.mock.return_value = ...
```

```python
mega_patch = MegaPatch.it(MyClass.my_method)
mega_patch.new_value.return_value = ...
```

You can also alter the return value of your mock without creating a separate mock object first.

```python
mega_patch.return_value.user = SomeUser()
```

Working with `MegaPatch` and classes:

`mega_patch.new_value` is the class _type_ itself

```python
mega_patch = MegaPatch.it(MyClass)

mega_patch.new_value.x is MyClass.x
```

`mega_patch.return_value` is the class _instance_ returned

```python
megaa_patch = MegaPatch.it(MyClass)

mega_patch.return_value is MyClass()
```

Patching a module attribute:

```python
import my_module

MegaPatch.it(my_module.some_attribute, new=...)
```

Patching a method of a nested class:

```python
import my_module

MegaPatch.it(
    my_module.MyClass.MyNestedClass.some_method,
    return_value=...
)
```

# Behavior differences from `mock`
- Using `MegaMock` is like using the `mock.create_autospec()` function
- Using `MegaPatch` is like setting `autospec=True`
- Mocking a class by default returns an instance of the class instead of a mocked type. This is like setting `instance=True`

# Art Gallery

![MegaMock](docs/img/megamock-cropped.png)
