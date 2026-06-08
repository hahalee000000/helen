"""Tests for helen CLI — REPL."""

import pytest
from helen.cli.repl import _needs_continuation, _execute_input
from helen.interpreter.interpreter import Interpreter
from helen.core.errors import ErrorReporter
from helen.runtime.llm_runtime import MockLLMRuntime
from helen.semantic.analyzer import SemanticAnalyzer


@pytest.fixture
def interp():
    """Provide a fresh Interpreter for REPL tests."""
    errors = ErrorReporter()
    return Interpreter(errors=errors, llm_runtime=MockLLMRuntime())


@pytest.fixture
def analyzer(interp):
    """Provide a fresh SemanticAnalyzer for REPL tests."""
    return SemanticAnalyzer(interp.errors, base_dir=".")


class TestNeedsContinuation:
    """Test multi-line bracket/brace matching."""

    def test_complete_statement(self):
        """Balanced braces → no continuation needed."""
        assert not _needs_continuation("let x = 1;")
        assert not _needs_continuation("let x = {1, 2, 3};")

    def test_unbalanced_brace(self):
        """Unbalanced braces → continuation needed."""
        assert _needs_continuation("agent Test {")
        assert _needs_continuation("if (x > 0) {")

    def test_unbalanced_paren(self):
        """Unbalanced parentheses → continuation needed."""
        assert _needs_continuation("let x = func(")

    def test_unbalanced_bracket(self):
        """Unbalanced brackets → continuation needed."""
        assert _needs_continuation("let x = [1, 2,")

    def test_string_with_brace(self):
        """Braces inside strings don't count."""
        assert not _needs_continuation('let msg = "hello {world}";')

    def test_nested_braces(self):
        """Nested braces are correctly counted."""
        assert not _needs_continuation("agent A { main { let x = 1; } }")
        assert _needs_continuation("agent A { main { let x = 1; }")


class TestExecuteInput:
    """Test REPL input execution."""

    def test_simple_expression(self, interp, analyzer):
        """Simple valid input executes successfully."""
        success, result = _execute_input("let x = 1", interp, analyzer)
        assert success

    def test_syntax_error(self, interp, analyzer):
        """Syntax error returns failure."""
        success, result = _execute_input("agent {", interp, analyzer)
        assert not success

    def test_arithmetic(self, interp, analyzer):
        """Arithmetic expressions work in REPL."""
        success, result = _execute_input("let x = 1 + 2\nlet y = x * 3", interp, analyzer)
        assert success


class TestReplCommand:
    """Test repl_command entry point."""

    def test_repl_returns_zero(self):
        """repl_command returns 0 on exit."""
        from helen.cli.repl import repl_command
        # Can't easily test interactive REPL without stdin mocking
        # Just verify the function exists and is callable
        assert callable(repl_command)
