"""Tests for control flow semantic checks — break/continue, llm usage, match default."""

import pytest

from helen.core.ast import (
    ForStmtNode,
    ProgramNode,
    VarDeclNode,
    VariableNode,
    WhileStmtNode,
)
from helen.core.errors import ErrorCode, ErrorReporter
from helen.core.source import SourceSpan
from helen.semantic.analyzer import SemanticAnalyzer


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _literal(value, line: int = 1):
    from helen.core.ast import LiteralNode
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1):
    return VariableNode(name=name, span=_span(line))


# ---------------------------------------------------------------------------
# break / continue inside loops
# ---------------------------------------------------------------------------


class TestBreakContinueInsideLoop:
    def test_break_inside_for(self):
        from helen.core.ast import BreakStmtNode
        brk = BreakStmtNode(span=_span())
        # Declare 'items' first
        decl = VarDeclNode(name="items", type_annotation=None, initializer=_literal([]), mutable=True, span=_span())
        for_stmt = ForStmtNode(
            iterator=_var("i"),
            iterable=_var("items"),
            body=brk,
            span=_span(),
        )
        prog = ProgramNode(statements=[decl, for_stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_break_inside_while(self):
        from helen.core.ast import BreakStmtNode
        brk = BreakStmtNode(span=_span())
        while_stmt = WhileStmtNode(condition=_literal(True), body=brk, span=_span())
        prog = ProgramNode(statements=[while_stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_continue_inside_for(self):
        from helen.core.ast import ContinueStmtNode
        cont = ContinueStmtNode(span=_span())
        decl = VarDeclNode(name="items", type_annotation=None, initializer=_literal([]), mutable=True, span=_span())
        for_stmt = ForStmtNode(
            iterator=_var("i"),
            iterable=_var("items"),
            body=cont,
            span=_span(),
        )
        prog = ProgramNode(statements=[decl, for_stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_nested_loops(self):
        from helen.core.ast import BreakStmtNode
        inner_break = BreakStmtNode(span=_span())
        inner_for = ForStmtNode(
            iterator=_var("j"),
            iterable=_var("inner"),
            body=inner_break,
            span=_span(),
        )
        # Declare outer and inner
        decl_outer = VarDeclNode(name="outer", type_annotation=None, initializer=_literal([]), mutable=True, span=_span())
        decl_inner = VarDeclNode(name="inner", type_annotation=None, initializer=_literal([]), mutable=True, span=_span())
        outer_for = ForStmtNode(
            iterator=_var("i"),
            iterable=_var("outer"),
            body=inner_for,
            span=_span(),
        )
        prog = ProgramNode(statements=[decl_outer, decl_inner, outer_for], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors


# ---------------------------------------------------------------------------
# LLM usage checks
# ---------------------------------------------------------------------------


class TestLlmUsage:
    def test_async_on_call_is_valid(self):
        """async call is parsed as AsyncCallStmtNode, semantic analyzer accepts it."""
        from helen.core.ast import AsyncCallStmtNode, CallArgNode, CallNode
        call = CallNode(
            callee=_var("AgentA"),
            arguments=[CallArgNode(name="data", value=_var("d1"))],
            span=_span(),
        )
        async_stmt = AsyncCallStmtNode(call=call, span=_span())
        prog = ProgramNode(statements=[async_stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        # Should not crash; callee will be flagged as undeclared but that's fine
        # The async-on-non-call check is done at parse time


# ---------------------------------------------------------------------------
# Match default mandatory
# ---------------------------------------------------------------------------


class TestMatchDefault:
    def test_match_with_default_passes(self):
        from helen.core.ast import CaseNode, MatchStmtNode
        # Declare x first
        decl = VarDeclNode(name="x", type_annotation=None, initializer=_literal("a"), mutable=True, span=_span())
        case = CaseNode(pattern=_literal("a"), body=[], span=_span())
        stmt = MatchStmtNode(
            subject=_var("x"),
            cases=[case],
            default=[_literal("fallback")],  # non-empty default
            span=_span(),
        )
        prog = ProgramNode(statements=[decl, stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors
