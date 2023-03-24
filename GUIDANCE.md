# MegaMock Guidance
## About
This guidance section is to help clarify the role of MegaMock, why, and how you would use it. If you're already convinced you want to
try MegaMock and want to just jump in, there's no need to read this document at this time. See [General Guidance](#general-guidance) to jump straight
to the guidance section.

## Why Mock?
There's various camps of developers who have grown their careers via different backgrounds. Some languages
have historically made mocking a pain in the butt, so developers have learned to work around it by following
certain design patterns. This
usually means writing code in a more verbose, complex pattern, that works around the ability to
simply swap something out on demand. In many cases, attempting to not mock ends up muddying up the clarity
of the interface for the developer who uses it, unless extra effort is spent creating a facade to hide
the complexity.

For example, consider a situation where you have one class, which makes 3rd party API calls. Which
interface would you rather use?

Interface A
```python
class A:
    def some_func(self) -> ClientApiResponse:
        api_client = get_api_client_from_pool()
        response = api_client.make_api_call()
        # ... do something with response ...
```

Interface B
```python
class A:
    def __init__(self, client_pool: BaseApiClientPool):
        self.client_pool = client_pool

    def some_func(self) -> BaseApiResponse:
        api_client = self.client_pool.get_client()
        response = api_client.make_api_call()
        # ... do something with response ...
```

Interface C
```python
class A:
    def some_func(
        self,
        client_pool: BaseApiClientPool,
        api_call_maker: BaseApiCallMaker,
        _connect_timeout: int = 5,
        _read_timeout: int = 10,
        _retries: int = 3,
        _retry_strategy: BaseRetryStrategy = ExponentialRetryBackoffStrategy(),
    ) -> BaseApiResponse:
        api_client = client_pool.get_client(_connect_timeout, _read_timeout)
        response = api_call_maker(api_client).make_api_call(_retries, _retry_strategy)
        # ... do something with response ...
```

Trying to swap everything out with a replaceable part will start to snowball pretty quickly.
This adds cognitive load to the developer. They need to tease out the actual purpose of the function,
the actual classes that are being used in production, and decipher how the business domain maps
to the classes presented. When a developer looks at the types passed in, they will find themselves
landing on the base class when they "go to definition". They then need to navigate to the actual class,
and hopefully not accidentally land on the test class. References to the actual class will be minimal,
if they want to find the usages, they have to go back to the base class and find the usages there.
This kind of navigation makes conceptually simple situations seem difficult to understand and navigate.

It's better to have a simple interface that mirrors the business domain as much possible, and only
introduce complexities where it is necessary.

Mocking also saves you time by allowing more leeway when writing code. You can quickly write code
as you find it intuitive, like writing a rough draft of a document, and cheaply write unit tests
against it. You can then refactor the code later if needed.

## Why MegaMock?

Even seasoned Python developers are frequently bit by the built-in mock framework. One very nasty
gotcha is found in the `patch` function. It's very easy to accidentally patch in the wrong location.
This stems from the nature that code is often written. A common programming technique to import
an object is to type
out the name of the class or function that you want, then press a keyboard shortcut to pull up
the quick action menu and have it generate the import. The import is usually, but not always,
a local import. This can create a divergence when patching an object. In some modules,
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
should also include the `autospec=True` argument, which is probably not enabled by default for
legacy reasons. Finally, `patch`es need to be remembered to be started and stopped.

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

The correct way to do this is to use `create_autospec`:

```python
mock = mock.create_autospec(SomeClass, spec_set=True, instance=True)
```

Now the mock object will have the same interface as `SomeClass`, will error if an attribute is assigned
that isn't part of the definition, and it also is mock instance of SomeClass instead of a mock type.
Likewise, attributes are only callable if they are actually callable.

With MegaMock, doing this is as simple as:

```python
mock = MegaMock(SomeClass)
```

Another example where MegaMock can be helpful is when you want to _mostly_ mock out a class.
This may be a common case in pytest fixtures where the fixture just mocks out the whole class,
and then you want to selectively enable logic as needed. Using the built-in mock library, you may
end up with something like this (highly simplified):

```python
real_func = MyClass.some_func

...

with mock.patch("tiring.path.to.the.class.to.mock.out.MyClass", autospec=True) as mock_class:
    mock_class.some_func = real_func

    do_test_logic(...)
```

With MegaMock, you can do this instead:

```python
MegaPatch.it(MyClass)
UseRealLogic(MyClass.megainstance.some_func)

do_test_logic(...)
```

## General Guidance

MegaMock is intended to _replace_ the built in `unittest.mock` library. In many cases it can be
a drop in replacement, although in the current alpha state that is not guaranteed. Currently,
all "naked" MegaMock objects require a type annotation if a spec object is not passed in, due to
a limitation in the Python static typing system. This limitation only affects you if you use static
type checking.

Do not write "Fake" and "Real" classes if you can avoid it. Instead of write real classes and use mocking
when fake behavior is needed.

Keep static typing in mind when writing code, even if you are writing a simple script that you are not
type checking. While it may be tempting to do something like this, where "value to pass around" is
actually a complex object:

```python
mock = MegaMock(outgoing_function)

func_under_test("value to pass around")

mock.assert_called_once_with("value to pass around")
```

It's better to use mock objects instead, which won't fail when put under the scrutiny of mypy.

```python
value_to_pass_around = MegaMock(the_type)

func_under_test(value_to_pass_around)

mock.assert_called_once_with(value_to_pass_around)
```

When creating a test with a single mock, prefer using the name `mock` for the variable if it
does not shadow another variable. Prefer `patch` for MegaPatch, under the same circumstances.

You should almost always use `MegaPatch.it` instead of `MegaPatch` directly.

Avoid testing the implementation. When you test the implementation, you create a brittle test
that easily breaks when the implementation changes. It can be very tempting to liberally
create mocks of almost everything and validate that one slice of the code is properly calling
another slice, but this should _generally_ be avoided.

```python
def ive_got_the_power(x):
    return pow(x, SOME_CONSTANT)


def test_ive_got_the_power():
    MegaPatch.it("my_module.SOME_CONSTANT", new=2)

    # bad, if the implementation was changed to use ** instead, this test would fail
    patch = MegaPatch.it(pow, return_value=4)

    ive_got_the_power(2)
    assert patch.mock.called_once_with(2, 2)

    # good
    assert ive_got_the_power(2) == 4
```

There are some exceptions. For example, a function may invoke complex inner logic with
a defined interface contract, and you want to verify that it is interacting correctly.
You don't want your test to care about the implementation of that inner logic.
In this case, you may want to mock out the inner logic and verify that the outer logic is calling it correctly.

```python
def get_super_complex_thing_for_today(data_blob):
    today = datetime.date.today()

    return get_super_complex_thing_for_date(data_blob, date=today)


def test_that(self) -> None:
    data_blob = MegaMock(DataBlob)
    today = MegaMock(datetime.date)
    expected_return = MegaMock[None]()

    patch = MegaPatch.it(datetime.date.today, return_value=today)
    patch = MegaPatch.it(get_super_complex_thing_for_date)

    assert get_super_complex_thing_for_today(data_blob) == get_super_complex_thing_for_date.return_value
    assert patch.mock.called_once_with(data_blob, date=today)
```

In that same line of thought, don't write tests with a long set-up and tear-down if it could be as equally
well tested using a mock, or is hitting an already well-tested code path.

`MegaMock` objects keep track of attribute assignments using the `mock.attr_assignments` attribute. This
is usually not needed, but in some uncommon cases, can be a helpful debugging tool when a mock goes through
a complex logic path that mutates it and the end result is not what was expected.

Similarly, spied objects have `mock.spied_access` which tracks the name and value of spied members, and their
access times. If you're not hitting the expected logic paths, this, combined with attr_assignments, can be helpful.

Prefer casting functions to their types, using `megacast` and `megainstance`. This allows the static type checkers
to infer the actual type of the object and lets you leverage your IDE's autocompletion.