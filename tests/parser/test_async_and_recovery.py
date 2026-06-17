"""Tests for async statement modifier, async expression, and error recovery."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.ast import (
    AsyncCallStmtNode, AsyncCallExprNode, CallNode, ProgramNode, ExprStmtNode,
    VarDeclNode,
)


def _parse(source: str) -> Parser:
    scanner = Scanner(source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, scanner.errors)
    return parser


def _first_stmt(parser: Parser):
    prog = parser.parse()
    assert isinstance(prog, ProgramNode)
    assert len(prog.statements) >= 1
    return prog.statements[0]


class TestAsyncCall:
    def test_async_call(self):
        p = _parse('async fetchData()')
        stmt = _first_stmt(p)
        assert isinstance(stmt, AsyncCallStmtNode)
        assert isinstance(stmt.call, CallNode)

    def test_async_call_with_args(self):
        p = _parse('async fetch(url, timeout=30)')
        stmt = _first_stmt(p)
        assert isinstance(stmt, AsyncCallStmtNode)
        assert len(stmt.call.arguments) >= 1

    def test_async_in_main_block(self):
        p = _parse('agent Test { main { async load() } }')
        prog = p.parse()
        assert len(prog.statements) == 1

    def test_async_on_non_call_error(self):
        p = _parse('async x')
        parser = p
        parser.parse()
        # Should report error about async on non-call
        assert parser.errors.has_errors


class TestAsyncExpression:
    """Test async as expression (let task = async Agent(...))."""

    def test_async_expr_in_let(self):
        """let task = async Worker() parses as VarDeclNode with AsyncCallExprNode initializer."""
        p = _parse('let task = async Worker()')
        prog = p.parse()
        stmt = prog.statements[0]
        assert isinstance(stmt, VarDeclNode)
        assert isinstance(stmt.initializer, AsyncCallExprNode)
        assert isinstance(stmt.initializer.call, CallNode)

    def test_async_expr_with_args(self):
        """let task = async Worker("input") parses correctly."""
        p = _parse('let task = async Worker("input")')
        prog = p.parse()
        stmt = prog.statements[0]
        assert isinstance(stmt, VarDeclNode)
        assert isinstance(stmt.initializer, AsyncCallExprNode)
        assert len(stmt.initializer.call.arguments) == 1

    def test_async_expr_in_main_block(self):
        """async expression works inside main block."""
        p = _parse('agent Test { main { let t = async load() } }')
        prog = p.parse()
        assert not p.errors.has_errors

    def test_async_stmt_still_works(self):
        """Bare async Agent() still parses as statement."""
        p = _parse('async fetchData()')
        stmt = _first_stmt(p)
        assert isinstance(stmt, AsyncCallStmtNode)
        assert isinstance(stmt.call, CallNode)


class TestErrorRecovery:
    def test_multiple_errors_no_crash(self):
        p = _parse('agent A { prompt "hi" let x = main { break } }')
        parser = p
        result = parser.parse()
        # Should not crash, produce some AST
        assert isinstance(result, ProgramNode)

    def test_missing_parenthesis_recovers(self):
        p = _parse('fn test( { }')
        parser = p
        result = parser.parse()
        assert isinstance(result, ProgramNode)

    def test_unterminated_string_in_program(self):
        p = _parse('let x = "unterminated')
        parser = p
        result = parser.parse()
        assert isinstance(result, ProgramNode)
