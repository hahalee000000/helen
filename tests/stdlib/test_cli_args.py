"""Tests for CLI argument stdlib functions — get_cli_args() and parse_cli_args().

Direct unit tests for the Python implementations in helen.stdlib.system.
"""

import pytest

from helen.stdlib.system import (
    _get_cli_args,
    _parse_cli_args,
    _set_cli_args,
    _cli_args,
)


class TestSetCliArgs:
    """Tests for _set_cli_args() internal function."""

    def test_set_empty(self):
        _set_cli_args([])
        assert _get_cli_args() == []

    def test_set_args(self):
        _set_cli_args(["--verbose", "--output=json"])
        result = _get_cli_args()
        assert result == ["--verbose", "--output=json"]

    def test_set_replaces_previous(self):
        _set_cli_args(["first"])
        _set_cli_args(["second"])
        assert _get_cli_args() == ["second"]

    def test_set_copies_input(self):
        """Modifying the input list doesn't affect stored args."""
        original = ["--test"]
        _set_cli_args(original)
        original.append("--extra")
        assert _get_cli_args() == ["--test"]


class TestGetCliArgs:
    """Tests for _get_cli_args()."""

    def test_returns_copy(self):
        """get_cli_args returns a copy, not the internal list."""
        _set_cli_args(["--test"])
        result = _get_cli_args()
        result.append("--hacked")
        assert _get_cli_args() == ["--test"]

    def test_returns_list(self):
        _set_cli_args([])
        assert isinstance(_get_cli_args(), list)


class TestParseCliArgsAutoMode:
    """Tests for _parse_cli_args() in auto-parse mode (no spec)."""

    def test_empty(self):
        _set_cli_args([])
        result = _parse_cli_args()
        assert result == {"_positional": []}

    def test_long_flag(self):
        _set_cli_args(["--verbose"])
        result = _parse_cli_args()
        assert result["verbose"] is True

    def test_long_flag_with_equals(self):
        _set_cli_args(["--output=json"])
        result = _parse_cli_args()
        assert result["output"] == "json"

    def test_long_flag_with_space(self):
        _set_cli_args(["--output", "json"])
        result = _parse_cli_args()
        assert result["output"] == "json"

    def test_short_flag(self):
        _set_cli_args(["-v"])
        result = _parse_cli_args()
        assert result["v"] is True

    def test_positional(self):
        _set_cli_args(["file.txt"])
        result = _parse_cli_args()
        assert result["_positional"] == ["file.txt"]

    def test_mixed(self):
        _set_cli_args(["--verbose", "--output=json", "input.txt", "-q"])
        result = _parse_cli_args()
        assert result["verbose"] is True
        assert result["output"] == "json"
        assert result["_positional"] == ["input.txt"]
        assert result["q"] is True

    def test_flag_followed_by_flag(self):
        """Two flags in a row — both become True."""
        _set_cli_args(["--verbose", "--quiet"])
        result = _parse_cli_args()
        assert result["verbose"] is True
        assert result["quiet"] is True

    def test_value_with_equals(self):
        """Value containing = is preserved (split on first = only)."""
        _set_cli_args(["--expr=a=b"])
        result = _parse_cli_args()
        assert result["expr"] == "a=b"

    def test_negative_number_positional(self):
        """Negative numbers with len > 2 (e.g., -50) are positional."""
        _set_cli_args(["-50"])
        result = _parse_cli_args()
        # -50 has len 3, so it's not a single-char short flag.
        assert result["_positional"] == ["-50"]


class TestParseCliArgsSpecMode:
    """Tests for _parse_cli_args() with spec dict."""

    def test_flag_default(self):
        _set_cli_args([])
        result = _parse_cli_args({"verbose": {"type": "flag", "default": False}})
        assert result["verbose"] is False

    def test_flag_present(self):
        _set_cli_args(["--verbose"])
        result = _parse_cli_args({"verbose": {"type": "flag", "default": False}})
        assert result["verbose"] is True

    def test_string_default(self):
        _set_cli_args([])
        result = _parse_cli_args({"output": {"type": "string", "default": "text"}})
        assert result["output"] == "text"

    def test_string_equals(self):
        _set_cli_args(["--output=json"])
        result = _parse_cli_args({"output": {"type": "string", "default": "text"}})
        assert result["output"] == "json"

    def test_string_space(self):
        _set_cli_args(["--output", "json"])
        result = _parse_cli_args({"output": {"type": "string", "default": "text"}})
        assert result["output"] == "json"

    def test_int_type(self):
        _set_cli_args(["--port=8080"])
        result = _parse_cli_args({"port": {"type": "int", "default": 3000}})
        assert result["port"] == 8080
        assert isinstance(result["port"], int)

    def test_int_space(self):
        _set_cli_args(["--port", "8080"])
        result = _parse_cli_args({"port": {"type": "int", "default": 3000}})
        assert result["port"] == 8080

    def test_float_type(self):
        _set_cli_args(["--rate=0.5"])
        result = _parse_cli_args({"rate": {"type": "float", "default": 1.0}})
        assert result["rate"] == 0.5

    def test_positional_in_spec(self):
        _set_cli_args(["--verbose", "file.txt"])
        result = _parse_cli_args({"verbose": {"type": "flag", "default": False}})
        assert result["_positional"] == ["file.txt"]

    def test_unknown_flag_in_spec(self):
        """Unknown flags still get captured as True."""
        _set_cli_args(["--unknown"])
        result = _parse_cli_args({"known": {"type": "flag", "default": False}})
        assert result["unknown"] is True
        assert result["known"] is False

    def test_short_flag_in_spec(self):
        _set_cli_args(["-v"])
        result = _parse_cli_args({"v": {"type": "flag", "default": False}})
        assert result["v"] is True

    def test_multiple_specs(self):
        _set_cli_args(["--verbose", "--output=json", "--port=8080", "file.txt"])
        spec = {
            "verbose": {"type": "flag", "default": False},
            "output": {"type": "string", "default": "text"},
            "port": {"type": "int", "default": 3000},
        }
        result = _parse_cli_args(spec)
        assert result["verbose"] is True
        assert result["output"] == "json"
        assert result["port"] == 8080
        assert result["_positional"] == ["file.txt"]

    def test_int_invalid_value(self):
        """Invalid int value keeps the string."""
        _set_cli_args(["--port=abc"])
        result = _parse_cli_args({"port": {"type": "int", "default": 3000}})
        assert result["port"] == "abc"

    def test_positional_always_present(self):
        """_positional is always present, even if empty."""
        _set_cli_args(["--verbose"])
        result = _parse_cli_args({"verbose": {"type": "flag", "default": False}})
        assert "_positional" in result
        assert result["_positional"] == []
