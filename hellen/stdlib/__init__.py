"""Hellen Standard Library (HLD M15).

Built-in functions and tools available to all Hellen programs.
Registered in the global scope before any user code executes.
"""

from __future__ import annotations

import math as _math
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class BuiltinFunction:
    """A built-in function available in Hellen programs."""

    name: str
    description: str
    signature: str
    fn: Callable[..., Any]
    category: str = "core"  # core, io, math, string


@dataclass
class StdlibRegistry:
    """Registry of all built-in functions.

    Provides lookup by name and listing by category.
    """

    _builtins: dict[str, BuiltinFunction] = field(default_factory=dict)

    def register(self, func: BuiltinFunction) -> None:
        """Register a built-in function."""
        self._builtins[func.name] = func

    def lookup(self, name: str) -> BuiltinFunction | None:
        """Look up a built-in function by name."""
        return self._builtins.get(name)

    def list_by_category(self, category: str) -> list[BuiltinFunction]:
        """List all builtins in a category."""
        return [f for f in self._builtins.values() if f.category == category]

    def list_all(self) -> list[BuiltinFunction]:
        """List all built-in functions."""
        return list(self._builtins.values())

    @property
    def names(self) -> list[str]:
        """All registered builtin names."""
        return list(self._builtins.keys())


# Global stdlib instance
stdlib = StdlibRegistry()


# ── Core builtins ──────────────────────────────────────────────

def _print(*args: Any) -> str:
    """Print values to stdout."""
    parts = [str(a) for a in args]
    result = " ".join(parts)
    print(result)
    return result


def _len(value: Any) -> int:
    """Return the length of a string, list, or dict."""
    if isinstance(value, (str, list, dict, tuple)):
        return len(value)
    raise TypeError(f"object of type '{type(value).__name__}' has no len()")


def _str(value: Any) -> str:
    """Convert a value to string."""
    return str(value)


def _int(value: Any) -> int:
    """Convert a value to integer."""
    return int(value)


def _float(value: Any) -> float:
    """Convert a value to float."""
    return float(value)


def _abs(value: Any) -> float:
    """Return the absolute value."""
    return abs(value)


def _min(*args: Any) -> Any:
    """Return the minimum value."""
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        return min(args[0])
    return min(args)


def _max(*args: Any) -> Any:
    """Return the maximum value."""
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        return max(args[0])
    return max(args)


def _range(start: int, stop: int | None = None, step: int = 1) -> list[int]:
    """Return a list of integers from start to stop (exclusive)."""
    if stop is None:
        stop = start
        start = 0
    return list(range(start, stop, step))


def _type(value: Any) -> str:
    """Return the type name of a value."""
    return type(value).__name__


def _isinstance(value: Any, type_name: str) -> bool:
    """Check if a value is an instance of a type."""
    type_map = {
        "int": int, "float": float, "str": str, "bool": bool,
        "list": list, "dict": dict, "tuple": tuple, "NoneType": type(None),
    }
    py_type = type_map.get(type_name)
    if py_type is None:
        return False
    return isinstance(value, py_type)


# ── String builtins ────────────────────────────────────────────

def _upper(s: str) -> str:
    """Convert string to uppercase."""
    return s.upper()


def _lower(s: str) -> str:
    """Convert string to lowercase."""
    return s.lower()


def _strip(s: str) -> str:
    """Remove leading and trailing whitespace."""
    return s.strip()


def _split(s: str, sep: str = " ") -> list[str]:
    """Split string by separator."""
    return s.split(sep)


def _join(sep: str, items: list[str]) -> str:
    """Join list of strings with separator."""
    return sep.join(str(item) for item in items)


def _startswith(s: str, prefix: str) -> bool:
    """Check if string starts with prefix."""
    return s.startswith(prefix)


def _endswith(s: str, suffix: str) -> bool:
    """Check if string ends with suffix."""
    return s.endswith(suffix)


def _replace(s: str, old: str, new: str) -> str:
    """Replace all occurrences of old with new."""
    return s.replace(old, new)


def _find(s: str, sub: str) -> int:
    """Find the index of a substring. Returns -1 if not found."""
    return s.find(sub)


# ── Math builtins ──────────────────────────────────────────────


def _round(value: float, ndigits: int = 0) -> float:
    """Round a number to ndigits decimal places."""
    return round(value, ndigits)


def _sqrt(value: float) -> float:
    """Return the square root."""
    return _math.sqrt(value)


def _floor(value: float) -> int:
    """Return the floor of a number."""
    return _math.floor(value)


def _ceil(value: float) -> int:
    """Return the ceiling of a number."""
    return _math.ceil(value)


def _input(prompt: str = "") -> str:
    """Read a line of input from the user."""
    return __builtins__["input"](prompt) if hasattr(__builtins__, "get") else input(prompt)


def _read_file(path: str) -> str:
    """Read the entire content of a text file."""
    import pathlib  # noqa: PLC0415
    return pathlib.Path(path).read_text(encoding="utf-8")


# ── Registration ───────────────────────────────────────────────

def _register_builtins() -> None:
    """Register all built-in functions."""
    builtins = [
        # Core
        BuiltinFunction("print", "Print values to stdout", "print(*args)", _print, "core"),
        BuiltinFunction("len", "Return length of string/list/dict", "len(value)", _len, "core"),
        BuiltinFunction("str", "Convert to string", "str(value)", _str, "core"),
        BuiltinFunction("int", "Convert to integer", "int(value)", _int, "core"),
        BuiltinFunction("float", "Convert to float", "float(value)", _float, "core"),
        BuiltinFunction("abs", "Absolute value", "abs(value)", _abs, "core"),
        BuiltinFunction("min", "Minimum value", "min(*args)", _min, "core"),
        BuiltinFunction("max", "Maximum value", "max(*args)", _max, "core"),
        BuiltinFunction("range", "Integer range", "range(start, stop?, step?)", _range, "core"),
        BuiltinFunction("type", "Type name", "type(value)", _type, "core"),
        BuiltinFunction("isinstance", "Type check", "isinstance(value, type_name)", _isinstance, "core"),

        # String
        BuiltinFunction("upper", "Uppercase string", "upper(s)", _upper, "string"),
        BuiltinFunction("lower", "Lowercase string", "lower(s)", _lower, "string"),
        BuiltinFunction("strip", "Trim whitespace", "strip(s)", _strip, "string"),
        BuiltinFunction("split", "Split string", "split(s, sep?)", _split, "string"),
        BuiltinFunction("join", "Join strings", "join(sep, items)", _join, "string"),
        BuiltinFunction("startswith", "Check prefix", "startswith(s, prefix)", _startswith, "string"),
        BuiltinFunction("endswith", "Check suffix", "endswith(s, suffix)", _endswith, "string"),
        BuiltinFunction("replace", "Replace substring", "replace(s, old, new)", _replace, "string"),
        BuiltinFunction("find", "Find substring index", "find(s, sub)", _find, "string"),

        # Math
        BuiltinFunction("round", "Round number", "round(value, ndigits?)", _round, "math"),
        BuiltinFunction("sqrt", "Square root", "sqrt(value)", _sqrt, "math"),
        BuiltinFunction("floor", "Floor value", "floor(value)", _floor, "math"),
        BuiltinFunction("ceil", "Ceiling value", "ceil(value)", _ceil, "math"),
        BuiltinFunction("input", "Read line from stdin", "input(prompt?)", _input, "core"),
        BuiltinFunction("read_file", "Read file content", "read_file(path)", _read_file, "core"),
    ]

    for func in builtins:
        stdlib.register(func)


# Auto-register on import
_register_builtins()
