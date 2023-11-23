# MegaMock Guidance
## About
This guide explains the role and usage of MegaMock. If you're ready to use MegaMock, skip to the [General Guidance](#general-guidance) section.

## Why Mock?
Consider a situation where you have one class, which makes 3rd party API calls. Which
interface would you rather use?

Interface A
```python
class A:
    def some_func(self, args) -> ClientApiResponse:
        api_client = get_api_client_from_pool()
        response = api_client.make_api_call(some, args)
        # ... do something with response ...
```

Interface B
```python
class A:
    def __init__(self, client_pool: BaseApiClientPool):
        self.client_pool = client_pool

    def some_func(self, args) -> BaseApiResponse:
        api_client = self.client_pool.get_client()
        response = api_client.make_api_call(some, args)
        # ... do something with response ...
```

Interface C
```python
class A:
    def some_func(
        self,
        client_pool: BaseApiClientPool,
        api_call_maker: BaseApiCallMaker,
        args,
        _connect_timeout: int = 5,
        _read_timeout: int = 10,
        _retries: int = 3,
        _retry_strategy: BaseRetryStrategy = ExponentialRetryBackoffStrategy(),
    ) -> BaseApiResponse:
        api_client = client_pool.get_client(_connect_timeout, _read_timeout)
        response = api_call_maker(api_client).make_api_call(args, retries=_retries, retry_strategy=_retry_strategy)
        # ... do something with response ...
```

The alternative to mocking and patching objects is to create a more complex class structure, where
the real implementation and the fake implementation are subclasses of a common base class.

Swapping everything with replaceable parts can lead to complexity, increasing cognitive load for
developers. They must understand the function's purpose, identify production classes, and map
the business domain to presented classes. Developers may struggle with code navigation, as they need
to identify actual classes among base and test classes. This complexity can make simple situations
harder to understand and navigate. Would you rather cmd / ctrl + click on a function and see the
actual implementation, or a placeholder implementation?

It's better to have a simple interface that mirrors the business domain as much possible, and only
introduce complexities where it is necessary.

Mocking and using the patch functionality also saves you time by allowing more leeway when writing
code. You can quickly write code as you find it intuitive, like writing a rough draft of a document,
and cheaply write unit tests against it. You can then refactor the code later if needed.

## Why MegaMock?

Even seasoned Python developers are frequently bit by the built-in mock framework. One very nasty
gotcha is found in the `patch` function. It's very easy to accidentally patch in the wrong location.
This stems from the nature that code is often written. A common programming technique to import
an object is to type out the name of the class or function that you want, then press a keyboard shortcut to pull up
the quick action menu and have it generate the import. The import is usually, but not always,
a `from` import. This can create a divergence when patching an object. In some modules,
you may need to apply the patch on the module where the object was defined. In other modules,
you would need to apply the patch where it is being used.

Another issue with the `patch` function is that it requires a dot path to the thing you are patching.
Most IDEs don't easily provide this functionality, so often times the developer is manually typing
this out or at least copying a path reference and swapping the slashes for periods.

```
./path/to/my/file.py -> path.to.my.file
```

This is error prone,
and time consuming. The dot paths are not changed when things are renamed. The calls to patch
should also include the `autospec=True` argument, which isn't default behavior, when it should be.
Finally, `patch`es need to be remembered to be started and stopped.

```python
# many patch strings may extend so long they need to be split into multiple lines
patch = mock.patch("mod1.mod2.mod3.SomeClass.some_func", autospec=True, return_value="val")
patch.start()
```

An alternative is to patch an object using `patch.object`. This is closer to how MegaMock operates,
because you are importing something to patch. One downside is that the patching still takes in a
string argument, and its still sensitive to how things are imported.

```python
from mod1.mod2.mod3 import SomeClass

patch = mock.patch.object(SomeClass, "some_func", autospec=True, return_value="val")
patch.start()
```

The library `pytest-mock` provides a `mocker` fixture that can be used to patch objects. This fixture
automatically does the start and stop for you, among a few other improvements.

**In contrast, here is how MegaMock does it:**

```python
MegaPatch.it(SomeClass.some_func, return_value="val")
```

MegaMock will not automatically stop patches for you. You can stop them using:

```python
MegaPatch.stop_all()
```

However, it's better to the built-in pytest plugin, if you are using pytest, which will automatically
stop all patches every test.

--------------------

You may want to pass in a mock object to a function and test that. It's very easy to write
mock code that looks like this:

```python
mock = mock.MagicMock()

func_under_test(mock)
```

The drawback is that if func_under_test misuses the mock object relative to the actual type it is
supposed to represent, then the test will pass, but the code will fail in production.

Many people may instead do this:

```python
mock = mock.MagicMock(spec=SomeClass)
```

but actually, this is still wrong. There's still behaviors that are not properly reflected in the mock.
Nested attributes are too broad.

The correct way to do this is to use `create_autospec`:

```python
mock = mock.create_autospec(SomeClass, spec_set=True, instance=True)
```

Now the mock object will have the same interface as `SomeClass`, will error if an attribute is assigned
that isn't part of the definition, and it also is mock instance of SomeClass instead of a mock type.
Likewise, attributes are only callable if they are actually callable. This also has its own flaws,
and attempting to get it to do what you want in some cases are non-trivial due to it generating
callables that are missing attributes you normally expect on `MagicMock` objects.

With MegaMock, doing all this is as simple as:

```python
mock = MegaMock.it(SomeClass)
```

Another example where MegaMock can be helpful is when you want to _mostly_ mock out a class.
There is no simple way to do this in the built-in mock library.

With MegaMock, you can do this:

```python
MegaPatch.it(MyClass)
use_real_logic(MyClass.megainstance.some_func)

do_test_logic(...)
```

## General Guidance

MegaMock is intended to _replace_ the built in `unittest.mock` library. In many cases it can be
a drop in replacement where you simply change the patterns on how you do things.

As mentioned earlier in the guidance, do not write "Fake" and "Real" classes if you can avoid it.
Instead, write real classes and use mocking when fake behavior is needed.

Keep static typing in mind when writing code, even if you are writing a simple script that you are not
type checking. While it may be tempting to use strings when the "value to pass around" is a complex object:

```python
mock = MegaMock(outgoing_function)

func_under_test("value to pass around")

assert Mega(mock).called_once_with("value to pass around")
```

It's better to use mock objects instead, which won't fail when put under the scrutiny of mypy.

```python
mock = MegaMock(outgoing_function)
value_to_pass_around = MegaMock(the_type)

func_under_test(value_to_pass_around)

assert Mega(mock).called_once_with(value_to_pass_around)
```

When creating a test with a single mock, prefer using the name `mock` for the variable if it
does not shadow another variable. Prefer `patch` for MegaPatch, under the same circumstances.

You should almost always use `MegaPatch.it` instead of `MegaPatch` directly. When creating
a `MegaMock` object with a spec, use `MegaMock.it(...)` or `MegaMock.this(...)`

When writing tests, avoid testing the implementation. When you test the implementation,
you create a brittle test that easily breaks when the implementation changes.
It can be very tempting to liberally create mocks of almost everything and validate that one
slice of the code is properly calling another slice, but this should _generally_ be avoided,
and should never be the de facto way things are tested in your project.

```python
def ive_got_the_power(x):
    return pow(x, SOME_CONSTANT)


def test_ive_got_the_power():
    MegaPatch.it("my_module.SOME_CONSTANT", new=2)

    # good, test the public interface gives the desired result
    assert ive_got_the_power(2) == 4

    # bad, if the implementation was changed to use ** instead, this test would fail
    patch = MegaPatch.it(pow, return_value=4)

    ive_got_the_power(2)
    assert patch.mock.called_once_with(2, 2)
```

There are some exceptions. For example, a function may invoke complex inner logic with
a defined interface contract and you want to verify that it is interacting correctly.
It can be time saving and also create a faster performing test to treat that inner logic
as a black box interface you are simply feeding into and reading from.
In this case, you may want to mock out the inner logic and verify that the outer logic is
calling it correctly. This only makes sense if the inner logic is already well tested.
In this case, you are treating the inner logic like a defined interface contract, and testing
your interactions with that contract.

```python
def get_super_complex_thing_for_today(data_blob):
    today = datetime.date.today()

    return get_super_complex_thing_for_date(data_blob, date=today)


def test_that(self) -> None:
    data_blob = MegaMock(DataBlob)
    today = MegaMock(datetime.date)
    expected_return = MegaMock()

    datetime_patch = MegaPatch.it(datetime.date.today, return_value=today)
    logic_patch = MegaPatch.it(get_super_complex_thing_for_date)

    # validate returning the response from the complex logic
    assert get_super_complex_thing_for_today(data_blob) == get_super_complex_thing_for_date.return_value
    # validate that the current date and data was passed in
    assert Mega(logic_patch.mock).called_once_with(data_blob, date=today)
```

Use `megainstance` to go from a mock class to the mock instance. This is typically used by `MegaPatch`.
`MegaMock` will automatically create a mock instance of a passed in class, but you can change
this behavior by setting `instance=False` when creating the mock.

This library was written with a leaning towards `pytest`, which is a popular testing library. See [usage](README.md#usage-pytest) in
the readme for more information about using the pytest plugin that comes with the library.

# Common hang-ups
Since MegaMock does the equivalent of setting `spec_set` to `True`, classes need to type hint their attributes.
Any attribute not type hinted will result in an attribute error if you attempt to set it for the purposes of doing a test.

```python
class MyClass:
    my_attr: str

    def __init__(self):
        self.my_attr = "foo"
```

```python
mock = MegaMock.it(MyClass)
mock.my_attr = "bar"
```

If you don't own the class, and it is missing the type annotations you can disable `spec_set`

```python
mock = MegaMock.it(ThirdPartyClass, spec_set=False)
```

# Advanced Use Cases
You can mock a context manager. This is typically done through `MegaPatch.it` rather than passing around context managers as args.
The preferred way of altering the context manager behavior is through the `set_context_manager...` `MegaPatch` methods.

Setting a return value:
```python
megapatch = MegaPatch.it(some_context_manager)
megapatch.set_context_manager_return_value("foo")

with some_context_manager() as val:
    assert val == "foo"
```

Setting a side-effect on entering:
```python
megapatch.set_context_manager_side_effect([1, 2])
```

Setting a side-effect on exiting:
```python
megapatch.set_context_manager_exit_side_effect(Exception("Error on file close"))
```

If for some reason you do want to deal with a `MegaMock` object directly, you will want to use the `return_value`
of the context manager and alter the `__enter__` or `__exit__` mock functions

```python
mock = MegaMock()
mock.return_value.__enter__.return_value = "some val"
mock.return_value.__exit__.side_effect = Exception("Error on file close!")

with pytest.raises(Exception) as exc:
    with mock() as val:
        assert val == "some val"

assert str(exc.value) == "Error on file close!"
```

One final note with context managers created from generators - they are not intended
to be used multiple times. This won't work:

```python

@contextlib.contextmanager
def my_context_manager():
    yield "something"

manager = my_context_manager()

with manager:
    pass

with manager:
    pass
```

# Behavior differences from `mock`
- Using `MegaMock` is like using the `mock.create_autospec()` function
  - This means a `MegaMock` object may support `async` functionality if the mocked object is async.
- Using `MegaPatch` is like setting `autospec=True`
- Mocking a class by default returns an instance of the class instead of a mocked type.
  This is like setting `instance=True` in the built-in library.
- As mentioned earlier in the readme, you don't need to care
  how you import something.
- Use `MegaMock.it(spec, ...)` and `MegaPatch.it(thing, ...)` instead
  of `MegaMock(spec=spec)` and `MegaPatch(thing=thing)`
- Mock lacks static type inference while MegaMock provides unions
  of the `MegaMock` object and the object used as a spec.

# Debugging tools
In addition to mocking capability, `MegaMock` objects can also help
you debug. The `attr_assignments` dictionary, found under the `megamock`
attribute in `MegaMock` objects, keep a record of what attributes
were assigned, when, and what the value was. This object is a dictionary
where the key is the attribute name, and the value is a list of
`AttributeAssignment` objects.

There is also `spied_access`, which is similar, but for
objects that are spied.

As mentioned earlier in the readme, `Mega.last_assertion_error` can
be used to access the assertion error thrown by mock.

If an attribute is coming out of a complex branch of logic with a value
you do not expect, you can check out these attributes in the debugger
and get an idea of where things are going wrong.

To easily view the stacktrace in the IDE, there's a special property,
`top_of_stacktrace`

![Top of Stack](docs/img/top-of-stack.png)

# Type Hinting
MegaMock leverages type hinting so that your IDE can autocomplete both
the `MegaMock` object and the object being mocked. This is done using
a hack that returns a union of two objects while doing it in a way
that bypasses mypy type checks. In the future, mypy may plug the hole
which would create an issue. If you get mypy issues, the current
recommendation is to just use `# type: ignore` and move on with your life.
Alternatively, you can cast an object to a type to fix a problem, but
this gets tedius.