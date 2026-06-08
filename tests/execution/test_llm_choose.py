"""Tests for helen.interpreter — llm choose statement execution."""

from helen.core.ast import (
    ExprStmtNode,
    LlmChooseStmtNode,
    LlmOptionNode,
    ProgramNode,
)
from helen.core.errors import ErrorReporter
from helen.core.source import SourceSpan
from helen.interpreter.exceptions import ModelError
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _run(stmt, llm_runtime=None) -> tuple:
    prog = ProgramNode(statements=[stmt], span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors, llm_runtime=llm_runtime)
    result = interp.interpret(prog)
    return result, errors


class TestLlmChooseExecution:
    def test_choose_correct_option(self):
        """llm choose "pick" { option "A" { return 1 } option "B" { return 2 } }"""
        runtime = MockLLMRuntime(choose_return="A")
        opt_a = LlmOptionNode(label="A", body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span())
        opt_b = LlmOptionNode(label="B", body=[ExprStmtNode(expression=_lit(2), span=_span())], span=_span())
        stmt = LlmChooseStmtNode(
            description="pick one",
            options=[opt_a, opt_b],
            default=[],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result == "A"
        assert not errors.has_errors
        assert len(runtime.choose_history) == 1

    def test_choose_returns_none_on_unknown(self):
        """LLM returns unknown option → return None."""
        runtime = MockLLMRuntime(choose_return="C")
        opt_a = LlmOptionNode(label="A", body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span())
        opt_b = LlmOptionNode(label="B", body=[ExprStmtNode(expression=_lit(2), span=_span())], span=_span())
        stmt = LlmChooseStmtNode(
            description="pick",
            options=[opt_a, opt_b],
            default=[],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result is None
        assert not errors.has_errors

    def test_choose_on_llm_exception(self):
        """LLM raises exception → return None."""
        runtime = MockLLMRuntime(choose_fail=ModelError("quota"))
        opt_a = LlmOptionNode(label="A", body=[], span=_span())
        stmt = LlmChooseStmtNode(
            description="pick",
            options=[opt_a],
            default=[],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result is None
        assert not errors.has_errors

    def test_choose_records_options(self):
        """Verify options list is passed to runtime."""
        runtime = MockLLMRuntime(choose_return="X")
        opt_x = LlmOptionNode(label="X", body=[], span=_span())
        opt_y = LlmOptionNode(label="Y", body=[], span=_span())
        stmt = LlmChooseStmtNode(
            description="select",
            options=[opt_x, opt_y],
            default=[],
            span=_span(),
        )
        _run(stmt, llm_runtime=runtime)
        assert runtime.choose_history[0]["options"] == ["X", "Y"]


def _lit(value, line: int = 1):
    from helen.core.ast import LiteralNode
    return LiteralNode(value=value, span=_span(line))
