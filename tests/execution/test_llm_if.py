"""Tests for helen.interpreter — llm if statement execution with MockLLMRuntime."""

from helen.core.ast import (
    ExprStmtNode,
    LlmBranchNode,
    LlmIfStmtNode,
    LiteralNode,
    ProgramNode,
)
from helen.core.errors import ErrorReporter
from helen.core.source import SourceSpan
from helen.interpreter.exceptions import TimeoutError
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _run(stmt, llm_runtime=None) -> tuple:
    prog = ProgramNode(statements=[stmt], span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors, llm_runtime=llm_runtime)
    result = interp.interpret(prog)
    return result, errors


class TestLlmIfExecution:
    def test_route_to_correct_branch(self):
        """llm if "desc" { branch "query" { return 1 } default { return 0 } }"""
        runtime = MockLLMRuntime(route_return="query")
        branch_q = LlmBranchNode(
            condition=_lit("query"),
            body=[ExprStmtNode(expression=_lit(1), span=_span())],
            span=_span(),
        )
        branch_default = LlmBranchNode(
            condition=None,
            body=[ExprStmtNode(expression=_lit(0), span=_span())],
            span=_span(),
        )
        stmt = LlmIfStmtNode(
            description="classify input",
            branches=[branch_q, branch_default],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result == 1
        assert not errors.has_errors
        assert len(runtime.route_history) == 1

    def test_route_to_default_on_unknown(self):
        """LLM returns unknown branch → execute default."""
        runtime = MockLLMRuntime(route_return="unknown_branch")
        branch_q = LlmBranchNode(
            condition=_lit("query"),
            body=[ExprStmtNode(expression=_lit(1), span=_span())],
            span=_span(),
        )
        branch_default = LlmBranchNode(
            condition=None,
            body=[ExprStmtNode(expression=_lit(0), span=_span())],
            span=_span(),
        )
        stmt = LlmIfStmtNode(
            description="classify",
            branches=[branch_q, branch_default],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result == 0  # default branch
        assert not errors.has_errors

    def test_route_to_default_on_parse_failure(self):
        """LLM returns None → execute default."""
        runtime = MockLLMRuntime(route_return=None)
        branch_q = LlmBranchNode(
            condition=_lit("query"),
            body=[ExprStmtNode(expression=_lit(1), span=_span())],
            span=_span(),
        )
        branch_default = LlmBranchNode(
            condition=None,
            body=[ExprStmtNode(expression=_lit(99), span=_span())],
            span=_span(),
        )
        stmt = LlmIfStmtNode(
            description="classify",
            branches=[branch_q, branch_default],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result == 99  # default branch
        assert not errors.has_errors

    def test_route_on_llm_exception(self):
        """LLM raises exception → execute default."""
        runtime = MockLLMRuntime(route_fail=TimeoutError("timeout"))
        branch_q = LlmBranchNode(
            condition=_lit("query"),
            body=[ExprStmtNode(expression=_lit(1), span=_span())],
            span=_span(),
        )
        branch_default = LlmBranchNode(
            condition=None,
            body=[ExprStmtNode(expression=_lit(42), span=_span())],
            span=_span(),
        )
        stmt = LlmIfStmtNode(
            description="classify",
            branches=[branch_q, branch_default],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result == 42  # default branch
        assert not errors.has_errors

    def test_multiple_branches(self):
        """LLM can route to any of multiple branches."""
        runtime = MockLLMRuntime(route_return="command")
        branch_q = LlmBranchNode(
            condition=_lit("query"),
            body=[ExprStmtNode(expression=_lit(1), span=_span())],
            span=_span(),
        )
        branch_c = LlmBranchNode(
            condition=_lit("command"),
            body=[ExprStmtNode(expression=_lit(2), span=_span())],
            span=_span(),
        )
        branch_default = LlmBranchNode(
            condition=None,
            body=[ExprStmtNode(expression=_lit(0), span=_span())],
            span=_span(),
        )
        stmt = LlmIfStmtNode(
            description="classify",
            branches=[branch_q, branch_c, branch_default],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result == 2
        assert not errors.has_errors

    def test_enum_validation_rejects_invalid_branch(self):
        """Runtime returns branch not in enum → treated as None → default (HLD 3.6.6)."""
        runtime = MockLLMRuntime(route_return="query")  # valid but...
        # ...the llm_if node only has "other" as named branch, so "query" is not in enum
        branch_other = LlmBranchNode(
            condition=_lit("other"),
            body=[ExprStmtNode(expression=_lit(1), span=_span())],
            span=_span(),
        )
        branch_default = LlmBranchNode(
            condition=None,
            body=[ExprStmtNode(expression=_lit(99), span=_span())],
            span=_span(),
        )
        stmt = LlmIfStmtNode(
            description="classify",
            branches=[branch_other, branch_default],
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        # "query" is not in ["other", "default"], so enum validation rejects it → default
        assert result == 99
        assert not errors.has_errors
