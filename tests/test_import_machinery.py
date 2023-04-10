import inspect
import linecache

import pytest

from megamock.import_machinery import _reconstruct_full_line
from megamock.megamocks import MegaMock
from megamock.megas import Mega
from megamock.type_util import call


class TestReconstructFullLine:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self._mock_frame = MegaMock.it(inspect.FrameInfo)

    def test_no_code_context(self) -> None:
        self._mock_frame.code_context = None
        assert _reconstruct_full_line(self._mock_frame) == ""

    def test_one_line_of_code(self) -> None:
        self._mock_frame.code_context = ["from foo import bar\n"]
        assert _reconstruct_full_line(self._mock_frame) == "from foo import bar\n"

    def test_multiline_parenthesis_code(self) -> None:
        self._mock_frame.code_context = ["from foo import (\n"]
        self._mock_frame.filename = "a_file.py"
        self._mock_frame.lineno = 2
        getline = MegaMock.it(
            linecache.getline, side_effect=["    bar,\n", "    baz,\n", ")\n"]
        )
        result = _reconstruct_full_line(self._mock_frame, getline=getline)
        assert result == "from foo import (\n    bar,\n    baz,\n)\n"
        assert Mega(getline).has_calls(
            [call("a_file.py", 3), call("a_file.py", 4), call("a_file.py", 5)]
        )

    def test_multiline_backslash_code(self) -> None:
        self._mock_frame.code_context = ["from foo import \\\n"]
        self._mock_frame.filename = "a_file.py"
        self._mock_frame.lineno = 2
        getline = MegaMock.it(
            linecache.getline,
            side_effect=["    bar,\\\n", "    baz\n", "dont be here\n"],
        )
        result = _reconstruct_full_line(self._mock_frame, getline=getline)
        assert result == "from foo import \\\n    bar,\\\n    baz\n"
        assert Mega(getline).has_calls([call("a_file.py", 3), call("a_file.py", 4)])
