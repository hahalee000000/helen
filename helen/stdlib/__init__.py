"""Helen Standard Library (HLD M15).

Built-in functions and tools available to all Helen programs.
Registered in the global scope before any user code executes.
"""

from __future__ import annotations

import math as _math
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

# Import network functions
from helen.stdlib.network import (
    _http_get, _http_post, _http_put, _http_delete, _http_download,
    _url_parse, _url_build, _url_encode, _url_decode
)

# Import string functions
from helen.stdlib.string import (
    # Regex
    _regex_match, _regex_search, _regex_test, _regex_replace, _regex_split, _regex_findall,
    # Text analysis
    _tokenize, _word_count, _levenshtein, _similarity,
    _remove_punctuation, _normalize_whitespace, _extract_urls, _extract_emails,
    # Encoding
    _base64_encode, _base64_decode, _html_escape, _html_unescape,
    # String ops
    _repeat, _reverse, _pad_left, _pad_right, _center, _count, _index, _contains,
    # Float formatting
    _format_float,
)

# Import data functions
from helen.stdlib.data import (
    _json_parse, _json_stringify, _json_load, _json_save,
    _html_parse, _html_text, _html_links, _html_select,
    _markdown_to_html, _markdown_extract_headings, _markdown_parse,
    _csv_parse, _csv_stringify, _csv_load, _csv_save,
)

# Import collection functions
from helen.stdlib.collection import (
    # List ops
    _map, _filter, _reduce, _find as _find_if, _every, _some,
    _sort, _unique, _flatten, _chunk, _zip,
    # Dict ops
    _keys, _values, _entries, _merge, _pick, _omit,
    # Set ops
    _make_set, _set_union, _set_intersection, _set_difference, _set_has,
)

# Import time functions
from helen.stdlib.time import (
    # Time
    _now, _time_func, _sleep,
    # Date
    _date, _datetime, _date_format, _date_parse,
    _date_add, _date_diff, _date_year, _date_month, _date_day, _date_weekday,
)

# Import math stats functions
from helen.stdlib.math_stats import (
    _mean, _median, _mode, _variance, _stddev,
    _correlation, _percentile, _sum, _product,
    _min as _stats_min, _max as _stats_max,
)

# Import file advanced functions
from helen.stdlib.file_advanced import (
    # File info
    _file_size, _file_modified, _list_dir, _walk_dir,
    # File ops
    _copy_file, _move_file, _delete_file, _delete_dir,
    # Temp files
    _temp_file, _temp_dir,
    # File search
    _glob_files, _grep_files,
)

# Import system functions
from helen.stdlib.system import (
    # Env
    _env_get, _env_set, _env_list, _env_delete,
    # CLI args
    _get_cli_args, _parse_cli_args,
    # Process
    _exec, _exec_async, _pid, _exit, _kill,
    # Log
    _log_debug, _log_info, _log_warn, _log_error, _log_critical,
    _log_set_level, _log_to_file,
)

# Import crypto functions
from helen.stdlib.crypto import (
    # Hash
    _md5, _sha1, _sha256, _sha512, _hmac_sha256, _hash_file,
    # Random
    _random, _randint, _choice, _shuffle, _sample,
)

# Import data formats functions
from helen.stdlib.data_formats import (
    # YAML
    _yaml_parse, _yaml_stringify, _yaml_load, _yaml_save,
    # TOML
    _toml_parse, _toml_stringify, _toml_load, _toml_save,
    # XML
    _xml_parse, _xml_stringify, _xml_load, _xml_save,
)

# Import test framework functions
from helen.stdlib.test import (
    _describe, _it, _it_skip,
    _assert_true, _assert_equal, _assert_not_equal, _assert_contains, _assert_throws,
    _expect, _before_each, _after_each, _before_all, _after_all,
    _run_tests, _run_tests_json, _test_reset, _test_count,
    _test_suite, _test_case, _test_case_skip, _test_end_suite,
    _fail, _set_test_timeout,
)

# Import quality assessment functions
from helen.stdlib.quality import (
    _analyze_code, _check_security, _quality_score, _quality_report,
)

# Import tool wrapper functions
from helen.stdlib.tools import (
    # Tool wrappers
    _web_search, _web_fetch,
    _shell_exec, _calculate, _patch_file, _load_skill,
)

# Import context management functions
from helen.stdlib.context import (
    _clear_context, _compress_context, _set_interpreter_context,  # noqa: F401 — re-exported
    _classify_message, _compress_context_target,  # Phase 1: Message classification
)

# Import transcript functions (Phase 1 SSOT)
from helen.stdlib.transcript import (
    get_session_id as _get_session_id,
    list_sessions as _list_sessions,
    replay_transcript as _replay_transcript,
    export_transcript as _export_transcript,
    get_compression_audit as _get_compression_audit,
    resume_session as _resume_session,
)

# Import media functions (multimodal support)
from helen.stdlib.media import (
    _media, _media_base64, _is_media, _media_type_fn,
    _to_openai_parts, _to_claude_parts, _to_gemini_parts,
    _media_to_base64, _save_media,
    _is_image, _is_video, _is_audio,
)


@dataclass
class BuiltinFunction:
    """A built-in function available in Helen programs."""

    name: str
    description: str
    signature: str
    fn: Callable[..., Any]
    category: str = "core"  # core, io, math, string


@dataclass
class StdlibRegistry:
    """Registry of all built-in functions.

    Provides lookup by name and listing by category.

    Supports multi-language aliases: each alias is an additional name
    pointing to the same canonical BuiltinFunction. All aliases are
    loaded at startup regardless of user locale (locale only affects
    presentation in docs/LSP/error messages).

    Attributes:
        _builtins: Canonical name → BuiltinFunction mapping.
        _aliases: Alias name → canonical name mapping.
        _canonical_names: Set of all canonical names (for tooling/docs).
    """

    _builtins: dict[str, BuiltinFunction] = field(default_factory=dict)
    _aliases: dict[str, str] = field(default_factory=dict)
    _canonical_names: set[str] = field(default_factory=set)

    def register(self, func: BuiltinFunction) -> None:
        """Register a built-in function under its canonical name."""
        self._builtins[func.name] = func
        self._canonical_names.add(func.name)

    def register_alias(self, alias: str, canonical: str) -> bool:
        """Register a localized alias for a canonical builtin name.

        Args:
            alias: The alias name (e.g. "长度" for "len").
            canonical: The canonical function name (e.g. "len").

        Returns:
            True if registered, False if canonical name not found
            or alias already registered to a different canonical.
        """
        if canonical not in self._canonical_names:
            return False
        if alias in self._aliases and self._aliases[alias] != canonical:
            return False
        self._aliases[alias] = canonical
        return True

    def lookup(self, name: str) -> BuiltinFunction | None:
        """Look up a built-in function by name or alias."""
        func = self._builtins.get(name)
        if func is not None:
            return func
        # Fall back to alias lookup
        canonical = self._aliases.get(name)
        if canonical is not None:
            return self._builtins.get(canonical)
        return None

    def is_alias(self, name: str) -> bool:
        """Check if a name is an alias (not canonical)."""
        return name in self._aliases

    def canonical_name(self, name: str) -> str:
        """Return the canonical name for a name or alias.

        Returns the input unchanged if it's already canonical or unknown.
        """
        return self._aliases.get(name, name)

    def list_by_category(self, category: str) -> list[BuiltinFunction]:
        """List all builtins in a category."""
        return [f for f in self._builtins.values() if f.category == category]

    def list_all(self) -> list[BuiltinFunction]:
        """List all built-in functions (canonical only, no aliases)."""
        return list(self._builtins.values())

    @property
    def names(self) -> list[str]:
        """All registered names (canonical + aliases)."""
        return list(self._builtins.keys()) + list(self._aliases.keys())

    @property
    def canonical_names(self) -> set[str]:
        """All canonical (non-alias) names."""
        return set(self._canonical_names)

    @property
    def aliases(self) -> dict[str, str]:
        """All registered aliases (alias → canonical)."""
        return dict(self._aliases)


# Global stdlib instance
stdlib = StdlibRegistry()


# ── Core builtins ──────────────────────────────────────────────

def _print(*args: Any) -> str:
    """Print values to stdout."""
    parts = []
    for a in args:
        # Convert booleans to lowercase to match Helen syntax
        if isinstance(a, bool):
            parts.append("true" if a else "false")
        else:
            parts.append(str(a))
    result = " ".join(parts)
    print(result)
    return result


def _len(value: Any) -> int:
    """Return the length of a string, list, dict, or read-only view."""
    if isinstance(value, (str, list, dict, tuple)):
        return len(value)
    # v1.12: ReadOnlyView and other objects with __len__
    if hasattr(value, '__len__'):
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


# ── Debug/Observability builtins (AI-native) ──────────────────

# Global reference to interpreter's observability manager (set by interpreter)
_interpreter_observability = None


def _set_interpreter_observability(obs):
    """Set the interpreter's observability manager for debug builtins."""
    global _interpreter_observability
    _interpreter_observability = obs


# ── Context Management builtins (v1.15) ──────────────────────

# Global reference to interpreter's history (set by interpreter)
_interpreter_history = None
_interpreter_history_manager = None


def _debug(message: str, data: Any = None) -> str:
    """Output structured debug information for AI consumption.

    Args:
        message: Debug message describing what's being logged.
        data: Optional data to include (any value).

    Returns:
        The formatted debug string.
    """
    import json
    import sys

    if data is not None:
        try:
            data_str = json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            data_str = repr(data)
        output = f"[DEBUG] {message} {data_str}"
    else:
        output = f"[DEBUG] {message}"

    print(output, file=sys.stderr)
    return output


def _trace_on() -> str:
    """Enable execution tracing.

    Returns:
        Confirmation message.
    """
    if _interpreter_observability is not None:
        _interpreter_observability.tracer.enabled = True
        _interpreter_observability.call_stack.enabled = True
        return "Execution tracing enabled"
    return "Warning: No interpreter context available"


def _trace_off() -> str:
    """Disable execution tracing.

    Returns:
        Confirmation message.
    """
    if _interpreter_observability is not None:
        _interpreter_observability.tracer.enabled = False
        return "Execution tracing disabled"
    return "Warning: No interpreter context available"


def _get_trace(n: int = 50) -> str:
    """Get recent execution trace entries.

    Args:
        n: Number of recent entries to return (default 50).

    Returns:
        Formatted trace string.
    """
    if _interpreter_observability is not None:
        return _interpreter_observability.tracer.format_trace(last_n=n)
    return "(no interpreter context)"


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


def _join(items: list[str], sep: str) -> str:
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


def _interpolate(template: str, vars: dict) -> str:
    """Interpolate a template string with variables.
    
    Replaces {{var}} placeholders with values from the vars dict.
    Supports nested attribute access like {{user.name}}.
    
    Args:
        template: String with {{var}} placeholders
        vars: Dictionary of variable names to values
    
    Returns:
        Interpolated string
    
    Example:
        let result = interpolate("Hello, {{name}}!", {"name": "Alice"})
        // result = "Hello, Alice!"
    """
    import re
    
    def replace_var(match):
        var_path = match.group(1).strip()
        parts = var_path.split(".")
        try:
            value = vars.get(parts[0])
        except (AttributeError, TypeError):
            return match.group(0)  # Keep original if not found
        
        for part in parts[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        
        if value is None:
            return match.group(0)  # Keep original if not found
        return str(value)
    
    return re.sub(r"\{\{(.+?)\}\}", replace_var, template)


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
    """Read a line of input from the user with readline support."""
    try:
        import readline  # noqa: F401  # enables cursor movement, history, etc.
    except ImportError:
        pass  # Windows may not have readline
    return __builtins__["input"](prompt) if hasattr(__builtins__, "get") else input(prompt)


def _multiline_input(prompt: str = "") -> str:
    """Read multiple lines of input. Empty line terminates.

    First line uses *prompt*, continuation lines use '... '.
    Returns all lines joined by newlines (trailing empty line excluded).
    """
    try:
        import readline  # noqa: F401
    except ImportError:
        pass
    _read = __builtins__["input"] if hasattr(__builtins__, "get") else input
    lines = []
    current_prompt = prompt
    while True:
        try:
            line = _read(current_prompt)
        except EOFError:
            break
        if line == "":
            break
        lines.append(line)
        current_prompt = "... "
    return "\n".join(lines)


def _read_file(path: str) -> str:
    """Read the entire content of a text file."""
    import pathlib  # noqa: PLC0415
    return pathlib.Path(path).read_text(encoding="utf-8")


def _write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed."""
    import pathlib  # noqa: PLC0415
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


def _append_file(path: str, content: str) -> str:
    """Append content to a file. Creates file and parent dirs if needed."""
    import pathlib  # noqa: PLC0415
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended {len(content)} bytes to {path}"


def _mkdir(path: str) -> str:
    """Create a directory. Parent directories must exist."""
    import pathlib  # noqa: PLC0415
    pathlib.Path(path).mkdir(parents=False, exist_ok=True)
    return f"Created directory: {path}"


def _mkdir_p(path: str) -> str:
    """Create a directory and all parent directories."""
    import pathlib  # noqa: PLC0415
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    return f"Created directory tree: {path}"


# ── Path operations ───────────────────────────────────────────


def _path_join(*parts: str) -> str:
    """Join path components."""
    import os.path  # noqa: PLC0415
    return os.path.join(*parts)


def _path_dirname(path: str) -> str:
    """Return directory name."""
    import os.path  # noqa: PLC0415
    return os.path.dirname(path)


def _path_basename(path: str) -> str:
    """Return base name."""
    import os.path  # noqa: PLC0415
    return os.path.basename(path)


def _path_exists(path: str) -> bool:
    """Check if path exists."""
    import os.path  # noqa: PLC0415
    return os.path.exists(path)


def _path_is_file(path: str) -> bool:
    """Check if path is a file."""
    import os.path  # noqa: PLC0415
    return os.path.isfile(path)


def _path_is_dir(path: str) -> bool:
    """Check if path is a directory."""
    import os.path  # noqa: PLC0415
    return os.path.isdir(path)


# ── String operations ─────────────────────────────────────────


def _substring(s: str, start: int, end: int | None = None) -> str:
    """Extract substring. If end is None, extracts from start to end of string."""
    if end is None:
        return s[start:]
    return s[start:end]


def _trim_prefix(s: str, prefix: str) -> str:
    """Remove prefix from string if it exists."""
    if s.startswith(prefix):
        return s[len(prefix):]
    return s


def _trim_suffix(s: str, suffix: str) -> str:
    """Remove suffix from string if it exists."""
    if s.endswith(suffix):
        return s[:-len(suffix)]
    return s


# ── Stream output builtins ────────────────────────────────────


def _stream_print(text: str) -> str:
    """Print text without newline (for streaming output)."""
    sys.stdout.write(text)
    sys.stdout.flush()
    return text


def _stream_clear() -> str:
    """Clear current line using ANSI escape codes."""
    sys.stdout.write("\r\x1b[2K")
    sys.stdout.flush()
    return ""


def _progress_bar(current: int, total: int, width: int = 40) -> str:
    """Display a progress bar with percentage.

    Args:
        current: Current progress value
        total: Total value (100% = total)
        width: Width of progress bar in characters (default 40)

    Returns:
        The progress bar string
    """
    if total == 0:
        percentage = 0.0
    else:
        percentage = min(100.0, (current / total) * 100)

    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)
    result = f"\r[{bar}] {percentage:.0f}%"
    sys.stdout.write(result)
    sys.stdout.flush()
    return result


def _stream_cursor_up(n: int = 1) -> str:
    """Move cursor up n lines using ANSI escape codes."""
    sys.stdout.write(f"\x1b[{n}A")
    sys.stdout.flush()
    return ""


def _stream_cursor_down(n: int = 1) -> str:
    """Move cursor down n lines using ANSI escape codes."""
    sys.stdout.write(f"\x1b[{n}B")
    sys.stdout.flush()
    return ""


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
        BuiltinFunction("join", "Join strings", "join(items, sep)", _join, "string"),
        BuiltinFunction("startswith", "Check prefix", "startswith(s, prefix)", _startswith, "string"),
        BuiltinFunction("endswith", "Check suffix", "endswith(s, suffix)", _endswith, "string"),
        BuiltinFunction("replace", "Replace substring", "replace(s, old, new)", _replace, "string"),
        BuiltinFunction("find", "Find substring index", "find(s, sub)", _find, "string"),
        BuiltinFunction("contains", "Check if contains substring", "contains(s, sub)", _contains, "string"),
        BuiltinFunction("substring", "Extract substring", "substring(s, start, end?)", _substring, "string"),
        BuiltinFunction("trim_prefix", "Remove prefix", "trim_prefix(s, prefix)", _trim_prefix, "string"),
        BuiltinFunction("trim_suffix", "Remove suffix", "trim_suffix(s, suffix)", _trim_suffix, "string"),
        BuiltinFunction("interpolate", "Template string interpolation", "interpolate(template, vars)", _interpolate, "string"),

        # Math
        BuiltinFunction("round", "Round number", "round(value, ndigits?)", _round, "math"),
        BuiltinFunction("sqrt", "Square root", "sqrt(value)", _sqrt, "math"),
        BuiltinFunction("floor", "Floor value", "floor(value)", _floor, "math"),
        BuiltinFunction("ceil", "Ceiling value", "ceil(value)", _ceil, "math"),
        BuiltinFunction("input", "Read line from stdin", "input(prompt?)", _input, "core"),
        BuiltinFunction("multiline_input", "Read multiple lines (empty line ends)", "multiline_input(prompt?)", _multiline_input, "core"),
        BuiltinFunction("read_file", "Read file content", "read_file(path)", _read_file, "core"),
        BuiltinFunction("write_file", "Write to file", "write_file(path, content)", _write_file, "io"),
        BuiltinFunction("append_file", "Append to file", "append_file(path, content)", _append_file, "io"),
        BuiltinFunction("mkdir", "Create directory", "mkdir(path)", _mkdir, "io"),
        BuiltinFunction("mkdir_p", "Create directory tree", "mkdir_p(path)", _mkdir_p, "io"),

        # Path operations
        BuiltinFunction("path_join", "Join path components", "path_join(*parts)", _path_join, "path"),
        BuiltinFunction("path_dirname", "Directory name", "path_dirname(path)", _path_dirname, "path"),
        BuiltinFunction("path_basename", "Base name", "path_basename(path)", _path_basename, "path"),
        BuiltinFunction("path_exists", "Check if path exists", "path_exists(path)", _path_exists, "path"),
        BuiltinFunction("path_is_file", "Check if path is file", "path_is_file(path)", _path_is_file, "path"),
        BuiltinFunction("path_is_dir", "Check if path is directory", "path_is_dir(path)", _path_is_dir, "path"),

        # Network operations (imported from network module)
        BuiltinFunction("http_get", "HTTP GET request", "http_get(url, headers?)", _http_get, "network"),
        BuiltinFunction("http_post", "HTTP POST request", "http_post(url, data?, headers?)", _http_post, "network"),
        BuiltinFunction("http_put", "HTTP PUT request", "http_put(url, data?, headers?)", _http_put, "network"),
        BuiltinFunction("http_delete", "HTTP DELETE request", "http_delete(url, headers?)", _http_delete, "network"),
        BuiltinFunction("http_download", "Download file from URL", "http_download(url, path)", _http_download, "network"),
        BuiltinFunction("url_parse", "Parse URL", "url_parse(url)", _url_parse, "network"),
        BuiltinFunction("url_build", "Build URL", "url_build(scheme, host, path?, query?)", _url_build, "network"),
        BuiltinFunction("url_encode", "URL encode", "url_encode(s)", _url_encode, "network"),
        BuiltinFunction("url_decode", "URL decode", "url_decode(s)", _url_decode, "network"),

        # String regex Operations
        BuiltinFunction("regex_match", "Regex match at start", "regex_match(pattern, s)", _regex_match, "string"),
        BuiltinFunction("regex_search", "Regex search anywhere", "regex_search(pattern, s)", _regex_search, "string"),
        BuiltinFunction("regex_test", "Regex test returns bool", "regex_test(pattern, s)", _regex_test, "string"),
        BuiltinFunction("regex_replace", "Regex replace", "regex_replace(pattern, s, replacement)", _regex_replace, "string"),
        BuiltinFunction("regex_split", "Regex split", "regex_split(pattern, s)", _regex_split, "string"),
        BuiltinFunction("regex_findall", "Regex find all", "regex_findall(pattern, s)", _regex_findall, "string"),

        # String text analysis
        BuiltinFunction("tokenize", "Tokenize text", "tokenize(text)", _tokenize, "string"),
        BuiltinFunction("word_count", "Count word frequencies", "word_count(text)", _word_count, "string"),
        BuiltinFunction("levenshtein", "Edit distance", "levenshtein(s1, s2)", _levenshtein, "string"),
        BuiltinFunction("similarity", "String similarity", "similarity(s1, s2)", _similarity, "string"),
        BuiltinFunction("remove_punctuation", "Remove punctuation", "remove_punctuation(text)", _remove_punctuation, "string"),
        BuiltinFunction("normalize_whitespace", "Normalize whitespace", "normalize_whitespace(text)", _normalize_whitespace, "string"),
        BuiltinFunction("extract_urls", "Extract URLs", "extract_urls(text)", _extract_urls, "string"),
        BuiltinFunction("extract_emails", "Extract emails", "extract_emails(text)", _extract_emails, "string"),

        # String encoding
        BuiltinFunction("base64_encode", "Base64 encode", "base64_encode(s)", _base64_encode, "string"),
        BuiltinFunction("base64_decode", "Base64 decode", "base64_decode(s)", _base64_decode, "string"),
        BuiltinFunction("html_escape", "HTML escape", "html_escape(s)", _html_escape, "string"),
        BuiltinFunction("html_unescape", "HTML unescape", "html_unescape(s)", _html_unescape, "string"),

        # String operations
        BuiltinFunction("repeat", "Repeat string", "repeat(s, n)", _repeat, "string"),
        BuiltinFunction("reverse", "Reverse string", "reverse(s)", _reverse, "string"),
        BuiltinFunction("pad_left", "Pad left", "pad_left(s, width, char?)", _pad_left, "string"),
        BuiltinFunction("pad_right", "Pad right", "pad_right(s, width, char?)", _pad_right, "string"),
        BuiltinFunction("center", "Center string", "center(s, width, char?)", _center, "string"),
        BuiltinFunction("count", "Count substring", "count(s, sub)", _count, "string"),
        BuiltinFunction("index", "Find substring index", "index(s, sub)", _index, "string"),

        # Float formatting
        BuiltinFunction("format_float", "Format float with decimals", "format_float(value, decimals)", _format_float, "string"),

        # Data JSON operations
        BuiltinFunction("json_parse", "Parse JSON", "json_parse(text)", _json_parse, "data"),
        BuiltinFunction("json_stringify", "Stringify to JSON", "json_stringify(value, indent?)", _json_stringify, "data"),
        BuiltinFunction("json_load", "Load JSON from file", "json_load(path)", _json_load, "data"),
        BuiltinFunction("json_save", "Save JSON to file", "json_save(path, value, indent?)", _json_save, "data"),

        # Data HTML operations
        BuiltinFunction("html_parse", "Parse HTML", "html_parse(text)", _html_parse, "data"),
        BuiltinFunction("html_text", "Extract HTML text", "html_text(html)", _html_text, "data"),
        BuiltinFunction("html_links", "Extract HTML links", "html_links(html)", _html_links, "data"),
        BuiltinFunction("html_select", "CSS select elements", "html_select(html, selector)", _html_select, "data"),

        # Data Markdown operations
        BuiltinFunction("markdown_to_html", "Convert Markdown to HTML", "markdown_to_html(text)", _markdown_to_html, "data"),
        BuiltinFunction("markdown_extract_headings", "Extract Markdown headings", "markdown_extract_headings(text)", _markdown_extract_headings, "data"),
        BuiltinFunction("markdown_parse", "Parse Markdown to blocks", "markdown_parse(text)", _markdown_parse, "data"),

        # Data CSV operations
        BuiltinFunction("csv_parse", "Parse CSV", "csv_parse(text, delimiter?)", _csv_parse, "data"),
        BuiltinFunction("csv_stringify", "Stringify to CSV", "csv_stringify(rows, delimiter?)", _csv_stringify, "data"),
        BuiltinFunction("csv_load", "Load CSV from file", "csv_load(path, delimiter?)", _csv_load, "data"),
        BuiltinFunction("csv_save", "Save CSV to file", "csv_save(path, rows, delimiter?)", _csv_save, "data"),

        # Collection list operations
        BuiltinFunction("map", "Map function over list", "map(lst, fn)", _map, "collection"),
        BuiltinFunction("filter", "Filter list by predicate", "filter(lst, fn)", _filter, "collection"),
        BuiltinFunction("reduce", "Reduce list to value", "reduce(lst, fn, initial?)", _reduce, "collection"),
        BuiltinFunction("find_if", "Find element by predicate", "find_if(lst, fn)", _find_if, "collection"),
        BuiltinFunction("every", "Check all elements", "every(lst, fn)", _every, "collection"),
        BuiltinFunction("some", "Check any element", "some(lst, fn)", _some, "collection"),
        BuiltinFunction("sort", "Sort list", "sort(lst, compare?)", _sort, "collection"),
        BuiltinFunction("unique", "Remove duplicates", "unique(lst)", _unique, "collection"),
        BuiltinFunction("flatten", "Flatten nested lists", "flatten(lst)", _flatten, "collection"),
        BuiltinFunction("chunk", "Split into chunks", "chunk(lst, size)", _chunk, "collection"),
        BuiltinFunction("zip", "Zip lists", "zip(*lists)", _zip, "collection"),

        # Collection dict operations
        BuiltinFunction("keys", "Get dict keys", "keys(dict)", _keys, "collection"),
        BuiltinFunction("values", "Get dict values", "values(dict)", _values, "collection"),
        BuiltinFunction("entries", "Get dict entries", "entries(dict)", _entries, "collection"),
        BuiltinFunction("merge", "Merge dicts", "merge(*dicts)", _merge, "collection"),
        BuiltinFunction("pick", "Pick dict keys", "pick(dict, keys)", _pick, "collection"),
        BuiltinFunction("omit", "Omit dict keys", "omit(dict, keys)", _omit, "collection"),

        # Collection set operations
        BuiltinFunction("make_set", "Create set", "make_set(items)", _make_set, "collection"),
        BuiltinFunction("set_union", "Set union", "set_union(s1, s2)", _set_union, "collection"),
        BuiltinFunction("set_intersection", "Set intersection", "set_intersection(s1, s2)", _set_intersection, "collection"),
        BuiltinFunction("set_difference", "Set difference", "set_difference(s1, s2)", _set_difference, "collection"),
        BuiltinFunction("set_has", "Check set membership", "set_has(set, item)", _set_has, "collection"),

        # Time operations
        BuiltinFunction("now", "Current datetime", "now()", _now, "time"),
        BuiltinFunction("time", "Unix timestamp", "time()", _time_func, "time"),
        BuiltinFunction("sleep", "Pause execution", "sleep(seconds)", _sleep, "time"),
        BuiltinFunction("date", "Create/get date", "date(year?, month?, day?)", _date, "time"),
        BuiltinFunction("datetime", "Create/get datetime", "datetime(year?, month?, day?, hour?, minute?, second?)", _datetime, "time"),
        BuiltinFunction("date_format", "Format date", "date_format(date_str, format_str)", _date_format, "time"),
        BuiltinFunction("date_parse", "Parse date", "date_parse(date_str, format_str)", _date_parse, "time"),
        BuiltinFunction("date_add", "Add to date", "date_add(date_str, days?, hours?, minutes?, seconds?)", _date_add, "time"),
        BuiltinFunction("date_diff", "Date difference", "date_diff(date1, date2, unit?)", _date_diff, "time"),
        BuiltinFunction("date_year", "Extract year", "date_year(date_str)", _date_year, "time"),
        BuiltinFunction("date_month", "Extract month", "date_month(date_str)", _date_month, "time"),
        BuiltinFunction("date_day", "Extract day", "date_day(date_str)", _date_day, "time"),
        BuiltinFunction("date_weekday", "Day of week", "date_weekday(date_str)", _date_weekday, "time"),

        # Math statistics operations
        BuiltinFunction("mean", "Arithmetic mean", "mean(numbers)", _mean, "math"),
        BuiltinFunction("median", "Median value", "median(numbers)", _median, "math"),
        BuiltinFunction("mode", "Most frequent values", "mode(numbers)", _mode, "math"),
        BuiltinFunction("variance", "Variance", "variance(numbers, population?)", _variance, "math"),
        BuiltinFunction("stddev", "Standard deviation", "stddev(numbers, population?)", _stddev, "math"),
        BuiltinFunction("correlation", "Pearson correlation", "correlation(x, y)", _correlation, "math"),
        BuiltinFunction("percentile", "Percentile value", "percentile(numbers, p)", _percentile, "math"),
        BuiltinFunction("sum", "Sum of numbers", "sum(numbers)", _sum, "math"),
        BuiltinFunction("product", "Product of numbers", "product(numbers)", _product, "math"),
        BuiltinFunction("stats_min", "Minimum value (stats)", "stats_min(numbers)", _stats_min, "math"),
        BuiltinFunction("stats_max", "Maximum value (stats)", "stats_max(numbers)", _stats_max, "math"),

        # File advanced operations
        BuiltinFunction("file_size", "File size in bytes", "file_size(path)", _file_size, "file"),
        BuiltinFunction("file_modified", "File modification time", "file_modified(path)", _file_modified, "file"),
        BuiltinFunction("list_dir", "List directory", "list_dir(path, pattern?)", _list_dir, "file"),
        BuiltinFunction("walk_dir", "Walk directory tree", "walk_dir(path)", _walk_dir, "file"),
        BuiltinFunction("copy_file", "Copy file", "copy_file(src, dst)", _copy_file, "file"),
        BuiltinFunction("move_file", "Move file", "move_file(src, dst)", _move_file, "file"),
        BuiltinFunction("delete_file", "Delete file", "delete_file(path)", _delete_file, "file"),
        BuiltinFunction("delete_dir", "Delete directory", "delete_dir(path, recursive?)", _delete_dir, "file"),
        BuiltinFunction("temp_file", "Create temp file", "temp_file(suffix?, prefix?, dir?)", _temp_file, "file"),
        BuiltinFunction("temp_dir", "Create temp directory", "temp_dir(suffix?, prefix?, dir?)", _temp_dir, "file"),
        BuiltinFunction("glob_files", "Recursively find files matching glob pattern", "glob_files(path, pattern?)", _glob_files, "file"),
        BuiltinFunction("grep_files", "Search file contents for a pattern", "grep_files(path, pattern, regex?, case_sensitive?, max_results?)", _grep_files, "file"),

        # System environment operations
        BuiltinFunction("env_get", "Get environment variable", "env_get(key, default?)", _env_get, "system"),
        BuiltinFunction("env_set", "Set environment variable", "env_set(key, value)", _env_set, "system"),
        BuiltinFunction("env_list", "List all environment variables", "env_list()", _env_list, "system"),
        BuiltinFunction("env_delete", "Delete environment variable", "env_delete(key)", _env_delete, "system"),

        # System CLI argument operations
        BuiltinFunction("get_cli_args", "Get CLI arguments", "get_cli_args()", _get_cli_args, "system"),
        BuiltinFunction("parse_cli_args", "Parse CLI arguments", "parse_cli_args(spec?)", _parse_cli_args, "system"),

        # System process operations
        BuiltinFunction("exec", "Execute command", "exec(command, shell?, timeout?)", _exec, "system"),
        BuiltinFunction("exec_async", "Execute command asynchronously", "exec_async(command, shell?)", _exec_async, "system"),
        BuiltinFunction("pid", "Get current process ID", "pid()", _pid, "system"),
        BuiltinFunction("exit", "Exit program", "exit(code?)", _exit, "system"),
        BuiltinFunction("kill", "Send signal to process", "kill(pid, signal?)", _kill, "system"),

        # System logging operations
        BuiltinFunction("log_debug", "Log debug message", "log_debug(message)", _log_debug, "system"),
        BuiltinFunction("log_info", "Log info message", "log_info(message)", _log_info, "system"),
        BuiltinFunction("log_warn", "Log warning message", "log_warn(message)", _log_warn, "system"),
        BuiltinFunction("log_error", "Log error message", "log_error(message)", _log_error, "system"),
        BuiltinFunction("log_critical", "Log critical message", "log_critical(message)", _log_critical, "system"),
        BuiltinFunction("log_set_level", "Set logging level", "log_set_level(level)", _log_set_level, "system"),
        BuiltinFunction("log_to_file", "Set log output to file", "log_to_file(path)", _log_to_file, "system"),

        # Crypto hash operations
        BuiltinFunction("md5", "Calculate MD5 hash", "md5(text)", _md5, "crypto"),
        BuiltinFunction("sha1", "Calculate SHA1 hash", "sha1(text)", _sha1, "crypto"),
        BuiltinFunction("sha256", "Calculate SHA256 hash", "sha256(text)", _sha256, "crypto"),
        BuiltinFunction("sha512", "Calculate SHA512 hash", "sha512(text)", _sha512, "crypto"),
        BuiltinFunction("hmac_sha256", "Calculate HMAC-SHA256", "hmac_sha256(key, message)", _hmac_sha256, "crypto"),
        BuiltinFunction("hash_file", "Calculate hash of file", "hash_file(path, algorithm?)", _hash_file, "crypto"),

        # Crypto random operations
        BuiltinFunction("random", "Generate random float", "random()", _random, "crypto"),
        BuiltinFunction("randint", "Generate random integer", "randint(min, max)", _randint, "crypto"),
        BuiltinFunction("choice", "Choose random item", "choice(items)", _choice, "crypto"),
        BuiltinFunction("shuffle", "Shuffle list randomly", "shuffle(items)", _shuffle, "crypto"),
        BuiltinFunction("sample", "Sample items randomly", "sample(items, k)", _sample, "crypto"),

        # Data formats YAML operations
        BuiltinFunction("yaml_parse", "Parse YAML", "yaml_parse(text)", _yaml_parse, "data"),
        BuiltinFunction("yaml_stringify", "Stringify to YAML", "yaml_stringify(value)", _yaml_stringify, "data"),
        BuiltinFunction("yaml_load", "Load YAML from file", "yaml_load(path)", _yaml_load, "data"),
        BuiltinFunction("yaml_save", "Save YAML to file", "yaml_save(path, value)", _yaml_save, "data"),

        # Data formats TOML operations
        BuiltinFunction("toml_parse", "Parse TOML", "toml_parse(text)", _toml_parse, "data"),
        BuiltinFunction("toml_stringify", "Stringify to TOML", "toml_stringify(value)", _toml_stringify, "data"),
        BuiltinFunction("toml_load", "Load TOML from file", "toml_load(path)", _toml_load, "data"),
        BuiltinFunction("toml_save", "Save TOML to file", "toml_save(path, value)", _toml_save, "data"),

        # Data formats XML operations
        BuiltinFunction("xml_parse", "Parse XML", "xml_parse(text)", _xml_parse, "data"),
        BuiltinFunction("xml_stringify", "Stringify to XML", "xml_stringify(value, root?)", _xml_stringify, "data"),
        BuiltinFunction("xml_load", "Load XML from file", "xml_load(path)", _xml_load, "data"),
        BuiltinFunction("xml_save", "Save XML to file", "xml_save(path, value, root?)", _xml_save, "data"),

        # Stream output
        BuiltinFunction("stream_print", "Print without newline", "stream_print(text)", _stream_print, "io"),
        BuiltinFunction("stream_clear", "Clear current line", "stream_clear()", _stream_clear, "io"),
        BuiltinFunction("progress_bar", "Display progress bar", "progress_bar(current, total, width?)", _progress_bar, "io"),
        BuiltinFunction("stream_cursor_up", "Move cursor up", "stream_cursor_up(n?)", _stream_cursor_up, "io"),
        BuiltinFunction("stream_cursor_down", "Move cursor down", "stream_cursor_down(n?)", _stream_cursor_down, "io"),

        # Debug/observability (AI-native)
        BuiltinFunction("debug", "Output structured debug info", "debug(message, data?)", _debug, "debug"),
        BuiltinFunction("trace_on", "Enable execution tracing", "trace_on()", _trace_on, "debug"),
        BuiltinFunction("trace_off", "Disable execution tracing", "trace_off()", _trace_off, "debug"),
        BuiltinFunction("get_trace", "Get recent execution trace", "get_trace(n?)", _get_trace, "debug"),

        # Test framework (TDD support)
        BuiltinFunction("describe", "Define a test suite", "describe(name, fn)", _describe, "test"),
        BuiltinFunction("it", "Define a test case", "it(name, fn)", _it, "test"),
        BuiltinFunction("it_skip", "Define a skipped test case", "it_skip(name, fn?)", _it_skip, "test"),
        BuiltinFunction("assert_true", "Assert condition is truthy", "assert_true(condition, message?)", _assert_true, "test"),
        BuiltinFunction("assert_equal", "Assert equality", "assert_equal(actual, expected, message?)", _assert_equal, "test"),
        BuiltinFunction("assert_not_equal", "Assert inequality", "assert_not_equal(actual, expected, message?)", _assert_not_equal, "test"),
        BuiltinFunction("assert_contains", "Assert container contains item", "assert_contains(container, item, message?)", _assert_contains, "test"),
        BuiltinFunction("assert_throws", "Assert function throws", "assert_throws(fn, error_type?)", _assert_throws, "test"),
        BuiltinFunction("expect", "Create chainable expectation", "expect(value)", _expect, "test"),
        BuiltinFunction("before_each", "Register before-each hook", "before_each(fn)", _before_each, "test"),
        BuiltinFunction("after_each", "Register after-each hook", "after_each(fn)", _after_each, "test"),
        BuiltinFunction("before_all", "Register before-all hook", "before_all(fn)", _before_all, "test"),
        BuiltinFunction("after_all", "Register after-all hook", "after_all(fn)", _after_all, "test"),
        BuiltinFunction("run_tests", "Execute all tests and print report", "run_tests(only?, suite?, filter?)", _run_tests, "test"),
        BuiltinFunction("run_tests_json", "Execute tests and return JSON", "run_tests_json(only?, suite?, filter?)", _run_tests_json, "test"),
        BuiltinFunction("test_reset", "Clear all registered tests", "test_reset()", _test_reset, "test"),
        BuiltinFunction("test_count", "Count registered tests", "test_count()", _test_count, "test"),
        BuiltinFunction("test_suite", "Start a test suite", "test_suite(name)", _test_suite, "test"),
        BuiltinFunction("test_case", "Register a test case", "test_case(name, fn)", _test_case, "test"),
        BuiltinFunction("test_case_skip", "Register a skipped test", "test_case_skip(name, fn?)", _test_case_skip, "test"),
        BuiltinFunction("test_end_suite", "End current test suite", "test_end_suite()", _test_end_suite, "test"),
        BuiltinFunction("fail", "Explicitly fail a test", "fail(message?)", _fail, "test"),
        BuiltinFunction("set_test_timeout", "Set per-test timeout", "set_test_timeout(seconds)", _set_test_timeout, "test"),

        # Quality assessment (7-dimension evaluation)
        BuiltinFunction("analyze_code", "Analyze code metrics", "analyze_code(source, filename?)", _analyze_code, "quality"),
        BuiltinFunction("check_security", "Check security issues", "check_security(source)", _check_security, "quality"),
        BuiltinFunction("quality_score", "Calculate quality score", "quality_score(source, file_path?)", _quality_score, "quality"),
        BuiltinFunction("quality_report", "Generate quality report", "quality_report(source, filename?)", _quality_report, "quality"),

        # Tool wrappers (from helen.stdlib.tools)
        BuiltinFunction("web_search", "Search the web", "web_search(query, limit?)", _web_search, "tools"),
        BuiltinFunction("web_fetch", "Fetch web page content", "web_fetch(url)", _web_fetch, "tools"),
        BuiltinFunction("shell_exec", "Execute shell command", "shell_exec(command, timeout?, shell?)", _shell_exec, "tools"),
        BuiltinFunction("calculate", "Evaluate math expression", "calculate(expression)", _calculate, "tools"),
        BuiltinFunction("patch_file", "Patch a file", "patch_file(path, old_string, new_string, replace_all?)", _patch_file, "tools"),
        BuiltinFunction("load_skill", "Load a skill by name", "load_skill(name)", _load_skill, "tools"),

        # Context management (v1.15)
        BuiltinFunction("clear_context", "Clear conversation context", "clear_context()", _clear_context, "context"),
        BuiltinFunction("compress_context", "Compress conversation context", "compress_context(strategy?)", _compress_context, "context"),
        # Phase 1: Message classification and selective compression
        BuiltinFunction("classify_message", "Classify message type and priority", "classify_message(message)", _classify_message, "context"),
        BuiltinFunction("compress_context_target", "Compress context by target type", "compress_context_target(target, keep_recent?)", _compress_context_target, "context"),

        # Transcript management (Phase 1 SSOT)
        BuiltinFunction("get_session_id", "Get current transcript session ID", "get_session_id()", _get_session_id, "transcript"),
        BuiltinFunction("list_sessions", "List all transcript sessions", "list_sessions()", _list_sessions, "transcript"),
        BuiltinFunction("replay_transcript", "Replay transcript messages", "replay_transcript(session_id?, include_compressed?)", _replay_transcript, "transcript"),
        BuiltinFunction("export_transcript", "Export transcript to file", "export_transcript(output_path, format?, session_id?)", _export_transcript, "transcript"),
        BuiltinFunction("get_compression_audit", "Get compression event history", "get_compression_audit()", _get_compression_audit, "transcript"),
        BuiltinFunction("resume_session", "Resume a previous transcript session", "resume_session(session_id)", _resume_session, "transcript"),

        # Media/multimodal functions (v1.17)
        BuiltinFunction("media", "Create media from file/URL", "media(source, type?)", _media, "media"),
        BuiltinFunction("media_base64", "Create media from base64 data", "media_base64(data, mime, type?)", _media_base64, "media"),
        BuiltinFunction("is_media", "Check if value is MediaPart", "is_media(value)", _is_media, "media"),
        BuiltinFunction("media_type", "Get media type", "media_type(value)", _media_type_fn, "media"),

        # Media format adapters (v1.17)
        BuiltinFunction("to_openai_parts", "Convert MediaParts to OpenAI content format", "to_openai_parts(parts)", _to_openai_parts, "media"),
        BuiltinFunction("to_claude_parts", "Convert MediaParts to Claude content format", "to_claude_parts(parts)", _to_claude_parts, "media"),
        BuiltinFunction("to_gemini_parts", "Convert MediaParts to Gemini content format", "to_gemini_parts(parts)", _to_gemini_parts, "media"),

        # Media utilities (v1.17)
        BuiltinFunction("media_to_base64", "Convert MediaPart content to base64 string", "media_to_base64(part)", _media_to_base64, "media"),
        BuiltinFunction("save_media", "Save MediaPart to file", "save_media(part, path?)", _save_media, "media"),

        # Media type predicates (v1.17)
        BuiltinFunction("is_image", "Check if MediaPart is an image", "is_image(value)", _is_image, "media"),
        BuiltinFunction("is_video", "Check if MediaPart is a video", "is_video(value)", _is_video, "media"),
        BuiltinFunction("is_audio", "Check if MediaPart is audio", "is_audio(value)", _is_audio, "media"),
    ]

    for func in builtins:
        stdlib.register(func)


# Auto-register on import
_register_builtins()

# Register locale aliases (all locales, unconditionally).
# Must run after _register_builtins() so canonical names exist.
from helen.stdlib.locales import register_all_aliases as _register_all_aliases
_register_all_aliases()
