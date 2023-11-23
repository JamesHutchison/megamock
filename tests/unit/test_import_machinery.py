import linecache
from types import FrameType

import pytest

from megamock.import_machinery import _get_code_lines, _reconstruct_full_line
from megamock.megamocks import MegaMock
from megamock.megapatches import MegaPatch
from megamock.megas import Mega
from megamock.type_util import call


class TestReconstructFullLine:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self._mock_frame = MegaMock.it(FrameType)

        self._code_lines_patch = MegaPatch.it(_get_code_lines)

    def test_no_code_context(self) -> None:
        self._code_lines_patch.mock.return_value = [], 1
        assert _reconstruct_full_line(self._mock_frame) == ""

    def test_one_line_of_code(self) -> None:
        self._code_lines_patch.mock.return_value = ["from foo import bar\n"], 1
        assert _reconstruct_full_line(self._mock_frame) == "from foo import bar\n"

    def test_multiline_parenthesis_code(self) -> None:
        self._code_lines_patch.mock.return_value = ["from foo import (\n"], 2
        self._mock_frame.f_code.co_filename = "a_file.py"
        getline = MegaMock.this(
            linecache.getline, side_effect=["    bar,\n", "    baz,\n", ")\n"]
        )
        result = _reconstruct_full_line(self._mock_frame, getline=getline)
        assert result == "from foo import (\n    bar,\n    baz,\n)\n"
        assert Mega(getline).has_calls(
            [call("a_file.py", 3), call("a_file.py", 4), call("a_file.py", 5)]
        )

    def test_multiline_backslash_code(self) -> None:
        self._code_lines_patch.mock.return_value = ["from foo import \\\r\n"], 2
        self._mock_frame.f_code.co_filename = "a_file.py"
        getline = MegaMock.this(
            linecache.getline,
            side_effect=["    bar,\\\r\n", "    baz\r\n", "dont be here\r\n"],
        )
        result = _reconstruct_full_line(self._mock_frame, getline=getline)
        assert result == "from foo import \\\r\n    bar,\\\r\n    baz\r\n"
        assert Mega(getline).has_calls([call("a_file.py", 3), call("a_file.py", 4)])
