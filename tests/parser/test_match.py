"""Tests for match statement parsing."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.ast import (
    MatchStmtNode, CaseNode, ProgramNode,
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


class TestMatchStmt:
    def test_match_simple(self):
        p = _parse('match x { case 1 { a = 1 } default { b = 2 } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, MatchStmtNode)
        assert len(stmt.cases) == 1
        assert isinstance(stmt.cases[0], CaseNode)
        assert len(stmt.default) >= 1

    def test_match_multiple_cases(self):
        p = _parse('match x { case 1 { a = 1 } case 2 { b = 2 } default { } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, MatchStmtNode)
        assert len(stmt.cases) == 2

    def test_match_with_default_only(self):
        p = _parse('match x { default { y = 0 } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, MatchStmtNode)
        assert len(stmt.cases) == 0
        assert len(stmt.default) >= 1

    def test_match_no_default(self):
        p = _parse('match x { case 1 { a = 1 } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, MatchStmtNode)
        assert len(stmt.cases) == 1
        assert len(stmt.default) == 0

    def test_match_in_main_block(self):
        p = _parse('agent Test { main { match status { case "ok" { x = 1 } default { x = 0 } } } }')
        prog = p.parse()
        assert len(prog.statements) == 1
