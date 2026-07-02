"""Tests for CLI argument support — argv variable, get_cli_args(), parse_cli_args().

Tests cover:
1. argv pre-defined const variable access
2. get_cli_args() stdlib function
3. parse_cli_args() structured parsing (auto and spec-driven modes)
4. CLI argument passing from run_command → Interpreter
5. argv propagation into agent scopes (const auto-sharing)
6. Semantic analysis: argv is recognized (no UNDECLARED_VARIABLE)
7. const protection: argv cannot be reassigned
8. Edge cases: empty args, args with special characters
"""

import os
import tempfile

import pytest

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime
from helen.cli.__main__ import run_command, main


# ─── Helpers ────────────────────────────────────────────────────────────────────


def parse_and_run(source: str, program_args: list[str] | None = None,
                  filename: str = "<test>") -> tuple:
    """Parse and execute Helen source code end-to-end with optional CLI args."""
    errors = ErrorReporter()
    interpreter = Interpreter(
        errors=errors,
        llm_runtime=MockLLMRuntime(),
        program_args=program_args,
    )
    analyzer = SemanticAnalyzer(errors, base_dir=".")
    scanner = Scanner(source=source, file=filename)
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    if errors.has_errors:
        raise RuntimeError(f"Parse errors: {[e.message for e in errors.errors]}")
    analyzer.analyze(program)
    if errors.has_errors:
        raise RuntimeError(f"Semantic errors: {[e.message for e in errors.errors]}")
    result = interpreter.interpret(program)
    return result, interpreter


# ─── argv Variable Tests ────────────────────────────────────────────────────────


class TestArgvVariable:
    """Tests for the pre-defined `argv` const variable."""

    def test_argv_empty_by_default(self):
        """argv is an empty list when no program args are passed."""
        result, interp = parse_and_run("argv")
        assert result == []

    def test_argv_with_args(self):
        """argv contains the CLI arguments passed to the program."""
        result, interp = parse_and_run("argv", program_args=["--verbose", "--output=json"])
        assert result == ["--verbose", "--output=json"]

    def test_argv_is_list(self):
        """argv is a list type."""
        result, interp = parse_and_run("type(argv)")
        assert result == "list"

    def test_argv_length(self):
        """len(argv) returns the number of arguments."""
        result, interp = parse_and_run("len(argv)", program_args=["a", "b", "c"])
        assert result == 3

    def test_argv_indexing(self):
        """Individual argv elements can be accessed by index."""
        result, interp = parse_and_run("argv[0]", program_args=["hello", "world"])
        assert result == "hello"

    def test_argv_last_element(self):
        """Last element of argv can be accessed."""
        result, interp = parse_and_run("argv[len(argv) - 1]",
                                       program_args=["first", "middle", "last"])
        assert result == "last"

    def test_argv_contains(self):
        """contains(argv, flag) works for checking if a flag is present."""
        result, interp = parse_and_run(
            'contains(argv, "--verbose")',
            program_args=["--verbose", "--output=json"],
        )
        assert result is True

    def test_argv_contains_missing(self):
        """contains(argv, flag) returns false when flag is absent."""
        result, interp = parse_and_run(
            'contains(argv, "--quiet")',
            program_args=["--verbose"],
        )
        assert result is False

    def test_argv_in_expression(self):
        """argv can be used in expressions."""
        result, interp = parse_and_run(
            'len(argv) > 0',
            program_args=["--verbose"],
        )
        assert result is True

    def test_argv_iteration(self):
        """argv can be iterated with for-in."""
        source = """
        let result = ""
        for arg in argv {
            result = result + arg + " "
        }
        result
        """
        result, interp = parse_and_run(source, program_args=["a", "b", "c"])
        assert result == "a b c "

    def test_argv_const_protection(self):
        """argv cannot be reassigned (it's a const)."""
        source = 'argv = ["hacked"]'
        # The semantic analyzer catches const assignment before runtime.
        with pytest.raises(RuntimeError, match="cannot assign to const"):
            parse_and_run(source, program_args=["--test"])

    def test_argv_special_characters(self):
        """argv handles arguments with special characters."""
        args = ["--path=/tmp/foo bar", "--quote=it's", "--emoji=🎉"]
        result, interp = parse_and_run("argv", program_args=args)
        assert result == args


# ─── argv Semantic Analysis Tests ───────────────────────────────────────────────


class TestArgvSemanticAnalysis:
    """Tests for semantic analysis of argv."""

    def test_argv_recognized_by_analyzer(self):
        """argv does not trigger UNDECLARED_VARIABLE error."""
        errors = ErrorReporter()
        source = "let x = argv"
        analyzer = SemanticAnalyzer(errors, base_dir=".")
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        analyzer.analyze(program)
        # No UNDECLARED_VARIABLE error for argv
        undeclared = [e for e in errors.errors if "undeclared" in e.message.lower()]
        assert len(undeclared) == 0

    def test_argv_cannot_be_shadowed(self):
        """argv cannot be re-declared with let (it's a pre-defined const)."""
        source = 'let argv = ["custom"]'
        with pytest.raises(RuntimeError, match="duplicate declaration"):
            parse_and_run(source, program_args=["original"])


# ─── Agent Scope Propagation Tests ──────────────────────────────────────────────


class TestArgvAgentPropagation:
    """Tests for argv propagation into agent scopes."""

    def test_argv_visible_in_agent(self):
        """argv (const) is visible inside agent main blocks."""
        source = """
        agent my_agent {
            main {
                argv
            }
        }
        my_agent()
        """
        result, interp = parse_and_run(source, program_args=["--agent-test"])
        assert result == ["--agent-test"]

    def test_argv_visible_in_function(self):
        """argv is visible inside function bodies."""
        source = """
        fn get_args() {
            argv
        }
        get_args()
        """
        result, interp = parse_and_run(source, program_args=["a", "b"])
        assert result == ["a", "b"]


# ─── get_cli_args() Tests ───────────────────────────────────────────────────────


class TestGetCliArgs:
    """Tests for the get_cli_args() stdlib function."""

    def test_get_cli_args_empty(self):
        """get_cli_args() returns empty list when no args."""
        result, interp = parse_and_run("get_cli_args()")
        assert result == []

    def test_get_cli_args_with_args(self):
        """get_cli_args() returns the CLI arguments."""
        result, interp = parse_and_run(
            "get_cli_args()",
            program_args=["--verbose", "--output=json"],
        )
        assert result == ["--verbose", "--output=json"]

    def test_get_cli_args_matches_argv(self):
        """get_cli_args() returns the same value as argv."""
        result, interp = parse_and_run(
            "get_cli_args() == argv",
            program_args=["--test"],
        )
        assert result is True

    def test_get_cli_args_returns_copy(self):
        """get_cli_args() returns a copy (modifying it doesn't affect argv)."""
        source = """
        let args = get_cli_args()
        args == argv
        """
        result, interp = parse_and_run(source, program_args=["a"])
        assert result is True


# ─── parse_cli_args() Tests ─────────────────────────────────────────────────────


class TestParseCliArgsAutoMode:
    """Tests for parse_cli_args() in auto-parse mode (no spec)."""

    def test_parse_empty(self):
        """parse_cli_args() with no args returns {_positional: []}."""
        result, interp = parse_and_run("parse_cli_args()")
        assert result == {"_positional": []}

    def test_parse_flags(self):
        """parse_cli_args() recognizes --verbose as a flag."""
        result, interp = parse_and_run(
            "parse_cli_args()",
            program_args=["--verbose", "--quiet"],
        )
        assert result["verbose"] is True
        assert result["quiet"] is True

    def test_parse_key_value_equals(self):
        """parse_cli_args() recognizes --key=value."""
        result, interp = parse_and_run(
            "parse_cli_args()",
            program_args=["--output=json", "--port=8080"],
        )
        assert result["output"] == "json"
        assert result["port"] == "8080"

    def test_parse_key_value_space(self):
        """parse_cli_args() recognizes --key value (space separated)."""
        result, interp = parse_and_run(
            "parse_cli_args()",
            program_args=["--output", "json"],
        )
        assert result["output"] == "json"

    def test_parse_positional(self):
        """parse_cli_args() collects positional arguments."""
        result, interp = parse_and_run(
            "parse_cli_args()",
            program_args=["file1.txt", "file2.txt"],
        )
        assert result["_positional"] == ["file1.txt", "file2.txt"]

    def test_parse_short_flags(self):
        """parse_cli_args() recognizes -v as a short flag."""
        result, interp = parse_and_run(
            "parse_cli_args()",
            program_args=["-v", "-q"],
        )
        assert result["v"] is True
        assert result["q"] is True

    def test_parse_mixed(self):
        """parse_cli_args() handles mixed flags, key-value, and positional."""
        result, interp = parse_and_run(
            "parse_cli_args()",
            program_args=["--verbose", "--output=json", "input.txt"],
        )
        assert result["verbose"] is True
        assert result["output"] == "json"
        assert result["_positional"] == ["input.txt"]


class TestParseCliArgsSpecMode:
    """Tests for parse_cli_args() with a spec dict.

    Note: Helen's lexer tokenizes `}}` as TEMPLATE_CLOSE, so nested map
    literals must use `} }` (with a space) to close correctly.
    """

    def test_parse_spec_flag_default(self):
        """Spec with flag type applies default when flag absent."""
        source = """
        let spec = {"verbose": {"type": "flag", "default": false} }
        let result = parse_cli_args(spec)
        result["verbose"]
        """
        result, interp = parse_and_run(source, program_args=[])
        assert result is False

    def test_parse_spec_flag_present(self):
        """Spec with flag type sets true when flag present."""
        source = """
        let spec = {"verbose": {"type": "flag", "default": false} }
        let result = parse_cli_args(spec)
        result["verbose"]
        """
        result, interp = parse_and_run(source, program_args=["--verbose"])
        assert result is True

    def test_parse_spec_string_default(self):
        """Spec with string type applies default when arg absent."""
        source = """
        let spec = {"output": {"type": "string", "default": "text"} }
        let result = parse_cli_args(spec)
        result["output"]
        """
        result, interp = parse_and_run(source, program_args=[])
        assert result == "text"

    def test_parse_spec_string_present(self):
        """Spec with string type captures value."""
        source = """
        let spec = {"output": {"type": "string", "default": "text"} }
        let result = parse_cli_args(spec)
        result["output"]
        """
        result, interp = parse_and_run(source, program_args=["--output=json"])
        assert result == "json"

    def test_parse_spec_int_type(self):
        """Spec with int type converts string to int."""
        source = """
        let spec = {"port": {"type": "int", "default": 3000} }
        let result = parse_cli_args(spec)
        result["port"]
        """
        result, interp = parse_and_run(source, program_args=["--port=8080"])
        assert result == 8080

    def test_parse_spec_positional(self):
        """Spec mode still collects positional arguments."""
        source = """
        let spec = {"verbose": {"type": "flag", "default": false} }
        let result = parse_cli_args(spec)
        result["_positional"]
        """
        result, interp = parse_and_run(
            source,
            program_args=["--verbose", "file.txt"],
        )
        assert result == ["file.txt"]


# ─── CLI Integration Tests ──────────────────────────────────────────────────────


class TestCLIIntegration:
    """Tests for CLI argument passing from the command line."""

    def _write_temp_helen(self, code: str) -> str:
        """Write a temporary Helen file and return its path."""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False)
        f.write(code)
        f.flush()
        f.close()
        return f.name

    def test_run_command_passes_args(self):
        """run_command() passes program_args to the interpreter."""
        code = "let x = argv"
        path = self._write_temp_helen(code)
        try:
            result = run_command(path, program_args=["--test", "value"])
            assert result == 0
        finally:
            os.unlink(path)

    def test_run_command_empty_args(self):
        """run_command() with no program_args works (argv is empty)."""
        code = "let x = argv"
        path = self._write_temp_helen(code)
        try:
            result = run_command(path)
            assert result == 0
        finally:
            os.unlink(path)

    def test_main_passes_extra_args(self):
        """main() passes arguments after the filename to the program."""
        code = 'let x = argv'
        path = self._write_temp_helen(code)
        try:
            result = main([path, "--verbose", "--output=json"])
            assert result == 0
        finally:
            os.unlink(path)

    def test_main_no_extra_args(self):
        """main() with no extra args after filename still runs."""
        code = 'let x = argv'
        path = self._write_temp_helen(code)
        try:
            result = main([path])
            assert result == 0
        finally:
            os.unlink(path)


# ─── Edge Case Tests ────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge case tests for CLI argument handling."""

    def test_argv_with_equals_in_value(self):
        """argv handles --key=value where value contains =."""
        result, interp = parse_and_run("argv", program_args=["--expr=a=b"])
        assert result == ["--expr=a=b"]

    def test_parse_cli_args_equals_in_value(self):
        """parse_cli_args() handles --key=value where value has =."""
        result, interp = parse_and_run(
            "parse_cli_args()",
            program_args=["--expr=a=b"],
        )
        # With = syntax, splits on first = only
        assert result["expr"] == "a=b"

    def test_argv_negative_index(self):
        """argv supports negative indexing (last element)."""
        result, interp = parse_and_run("argv[-1]", program_args=["a", "b", "c"])
        assert result == "c"

    def test_multiple_interpreters_isolated(self):
        """Multiple interpreters have isolated CLI args."""
        _, interp1 = parse_and_run("argv", program_args=["--from-first"])
        _, interp2 = parse_and_run("argv", program_args=["--from-second"])
        assert interp1.environment.lookup("argv") == ["--from-first"]
        assert interp2.environment.lookup("argv") == ["--from-second"]
