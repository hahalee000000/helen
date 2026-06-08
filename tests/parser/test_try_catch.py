"""Tests for try/catch/finally parsing."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.ast import (
    TryStmtNode, CatchClauseNode, CatchAllNode, FinallyBlockNode, ProgramNode,
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


class TestTryCatch:
    def test_try_catch_typed(self):
        p = _parse('try { x = 1 } catch Error e { y = 2 }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, TryStmtNode)
        assert len(stmt.catch_clauses) == 1
        assert isinstance(stmt.catch_clauses[0], CatchClauseNode)
        assert stmt.catch_clauses[0].error_name == "e"

    def test_try_catch_all(self):
        p = _parse('try { x = 1 } catch { y = 2 }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, TryStmtNode)
        assert isinstance(stmt.catch_all, CatchAllNode)

    def test_try_finally(self):
        p = _parse('try { x = 1 } finally { cleanup() }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, TryStmtNode)
        assert isinstance(stmt.finally_block, FinallyBlockNode)

    def test_try_catch_finally(self):
        p = _parse('try { x = 1 } catch Error e { handle(e) } finally { cleanup() }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, TryStmtNode)
        assert len(stmt.catch_clauses) == 1
        assert isinstance(stmt.finally_block, FinallyBlockNode)

    def test_try_multiple_catches(self):
        p = _parse('try { x = 1 } catch IOError e { handle(e) } catch Exception e { log(e) } catch { fallback() }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, TryStmtNode)
        assert len(stmt.catch_clauses) == 2
        assert isinstance(stmt.catch_all, CatchAllNode)

    def test_try_no_catch_or_finally_error(self):
        p = _parse('try { x = 1 }')
        parser = p
        parser.parse()
        assert parser.errors.has_errors
