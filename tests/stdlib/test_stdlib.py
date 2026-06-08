"""Tests for Helen Standard Library (HLD M15)."""

from helen.stdlib import stdlib, BuiltinFunction, StdlibRegistry


class TestStdlibRegistry:
    """Test the stdlib registry."""

    def test_register_and_lookup(self):
        """Register a function and look it up."""
        def dummy() -> str:
            return "test"

        func = BuiltinFunction("dummy", "Test function", "dummy()", dummy, "core")
        reg = StdlibRegistry()
        reg.register(func)

        result = reg.lookup("dummy")
        assert result is not None
        assert result.name == "dummy"
        assert result.description == "Test function"

    def test_lookup_nonexistent(self):
        """Lookup nonexistent function returns None."""
        reg = StdlibRegistry()
        assert reg.lookup("nonexistent") is None

    def test_list_by_category(self):
        """List functions by category."""
        reg = StdlibRegistry()
        reg.register(
            BuiltinFunction("core_fn", "Core", "core_fn()", lambda: None, "core")
        )
        reg.register(
            BuiltinFunction("string_fn", "String", "string_fn()", lambda: None, "string")
        )

        core_fns = reg.list_by_category("core")
        assert len(core_fns) == 1
        assert core_fns[0].name == "core_fn"

        string_fns = reg.list_by_category("string")
        assert len(string_fns) == 1
        assert string_fns[0].name == "string_fn"

    def test_list_all(self):
        """List all registered functions."""
        reg = StdlibRegistry()
        reg.register(
            BuiltinFunction("a", "A", "a()", lambda: None, "core")
        )
        reg.register(
            BuiltinFunction("b", "B", "b()", lambda: None, "core")
        )

        all_fns = reg.list_all()
        assert len(all_fns) == 2

    def test_names_property(self):
        """Names property returns all registered names."""
        reg = StdlibRegistry()
        reg.register(
            BuiltinFunction("x", "X", "x()", lambda: None, "core")
        )
        reg.register(
            BuiltinFunction("y", "Y", "y()", lambda: None, "core")
        )

        assert set(reg.names) == {"x", "y"}


class TestCoreBuiltins:
    """Test core built-in functions."""

    def test_print_returns_string(self):
        """print() returns the formatted string."""
        from helen.stdlib import _print
        result = _print("hello", "world")
        assert result == "hello world"

    def test_len_string(self):
        """len() works on strings."""
        from helen.stdlib import _len
        assert _len("hello") == 5

    def test_len_list(self):
        """len() works on lists."""
        from helen.stdlib import _len
        assert _len([1, 2, 3]) == 3

    def test_len_dict(self):
        """len() works on dicts."""
        from helen.stdlib import _len
        assert _len({"a": 1, "b": 2}) == 2

    def test_len_invalid_type(self):
        """len() raises TypeError for invalid types."""
        from helen.stdlib import _len
        try:
            _len(42)
            assert False, "Should have raised TypeError"
        except TypeError:
            pass

    def test_str_conversion(self):
        """str() converts values to string."""
        from helen.stdlib import _str
        assert _str(42) == "42"
        assert _str(3.14) == "3.14"
        assert _str(True) == "True"

    def test_int_conversion(self):
        """int() converts values to integer."""
        from helen.stdlib import _int
        assert _int("42") == 42
        assert _int(3.14) == 3

    def test_float_conversion(self):
        """float() converts values to float."""
        from helen.stdlib import _float
        assert _float("3.14") == 3.14
        assert _float(42) == 42.0

    def test_abs(self):
        """abs() returns absolute value."""
        from helen.stdlib import _abs
        assert _abs(-5) == 5
        assert _abs(5) == 5

    def test_min(self):
        """min() returns minimum value."""
        from helen.stdlib import _min
        assert _min(1, 2, 3) == 1
        assert _min([3, 1, 2]) == 1

    def test_max(self):
        """max() returns maximum value."""
        from helen.stdlib import _max
        assert _max(1, 2, 3) == 3
        assert _max([3, 1, 2]) == 3

    def test_range(self):
        """range() generates integer ranges."""
        from helen.stdlib import _range
        assert _range(3) == [0, 1, 2]
        assert _range(1, 4) == [1, 2, 3]
        assert _range(0, 6, 2) == [0, 2, 4]

    def test_type(self):
        """type() returns type name."""
        from helen.stdlib import _type
        assert _type(42) == "int"
        assert _type("hello") == "str"
        assert _type([1, 2]) == "list"

    def test_isinstance(self):
        """isinstance() checks type."""
        from helen.stdlib import _isinstance
        assert _isinstance(42, "int")
        assert _isinstance("hello", "str")
        assert not _isinstance(42, "str")
        assert not _isinstance("hello", "int")


class TestStringBuiltins:
    """Test string built-in functions."""

    def test_upper(self):
        """upper() converts to uppercase."""
        from helen.stdlib import _upper
        assert _upper("hello") == "HELLO"

    def test_lower(self):
        """lower() converts to lowercase."""
        from helen.stdlib import _lower
        assert _lower("HELLO") == "hello"

    def test_strip(self):
        """strip() removes whitespace."""
        from helen.stdlib import _strip
        assert _strip("  hello  ") == "hello"

    def test_split(self):
        """split() splits string."""
        from helen.stdlib import _split
        assert _split("a b c") == ["a", "b", "c"]
        assert _split("a,b,c", ",") == ["a", "b", "c"]

    def test_join(self):
        """join() joins list."""
        from helen.stdlib import _join
        assert _join("-", ["a", "b", "c"]) == "a-b-c"

    def test_startswith(self):
        """startswith() checks prefix."""
        from helen.stdlib import _startswith
        assert _startswith("hello", "hel")
        assert not _startswith("hello", "xyz")

    def test_endswith(self):
        """endswith() checks suffix."""
        from helen.stdlib import _endswith
        assert _endswith("hello", "llo")
        assert not _endswith("hello", "xyz")

    def test_replace(self):
        """replace() replaces substring."""
        from helen.stdlib import _replace
        assert _replace("hello world", "world", "there") == "hello there"

    def test_find(self):
        """find() returns index."""
        from helen.stdlib import _find
        assert _find("hello", "ll") == 2
        assert _find("hello", "xyz") == -1


class TestMathBuiltins:
    """Test math built-in functions."""

    def test_round(self):
        """round() rounds numbers."""
        from helen.stdlib import _round
        assert _round(3.14159, 2) == 3.14
        assert _round(3.5) == 4.0

    def test_sqrt(self):
        """sqrt() returns square root."""
        from helen.stdlib import _sqrt
        assert _sqrt(4) == 2.0
        assert _sqrt(9) == 3.0

    def test_floor(self):
        """floor() returns floor."""
        from helen.stdlib import _floor
        assert _floor(3.9) == 3
        assert _floor(-3.1) == -4

    def test_ceil(self):
        """ceil() returns ceiling."""
        from helen.stdlib import _ceil
        assert _ceil(3.1) == 4
        assert _ceil(-3.9) == -3


class TestGlobalStdlib:
    """Test the globally registered stdlib."""

    def test_stdlib_has_core_builtins(self):
        """Global stdlib has core builtins."""
        assert stdlib.lookup("print") is not None
        assert stdlib.lookup("len") is not None
        assert stdlib.lookup("str") is not None

    def test_stdlib_has_string_builtins(self):
        """Global stdlib has string builtins."""
        assert stdlib.lookup("upper") is not None
        assert stdlib.lookup("lower") is not None
        assert stdlib.lookup("split") is not None

    def test_stdlib_has_math_builtins(self):
        """Global stdlib has math builtins."""
        assert stdlib.lookup("round") is not None
        assert stdlib.lookup("sqrt") is not None

    def test_stdlib_categories(self):
        """Builtins are organized by category."""
        core = stdlib.list_by_category("core")
        string = stdlib.list_by_category("string")
        math_builtins = stdlib.list_by_category("math")

        assert len(core) > 0
        assert len(string) > 0
        assert len(math_builtins) > 0

    def test_stdlib_total_count(self):
        """Total builtin count is reasonable."""
        all_fns = stdlib.list_all()
        assert len(all_fns) >= 20  # At least 20 builtins
