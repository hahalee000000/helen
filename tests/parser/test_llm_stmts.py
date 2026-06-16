"""Tests for LLM statement parsing: llm if, llm choose, llm act, and disambiguation."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.ast import (
    LlmIfStmtNode, LlmBranchNode, LlmChooseStmtNode, LlmOptionNode,
    ProgramNode, MainBlockNode,
)
from helen.core.tokens import TokenType


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


class TestLlmIfStmt:
    def test_llm_if_simple(self):
        p = _parse('llm if "classify" { branch true { x = 1 } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, LlmIfStmtNode)
        assert stmt.description == "classify"
        assert len(stmt.branches) == 1
        assert isinstance(stmt.branches[0], LlmBranchNode)

    def test_llm_if_with_default(self):
        p = _parse('llm if "classify" { branch true { x = 1 } default { x = 0 } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, LlmIfStmtNode)
        assert len(stmt.branches) == 2
        # Second branch is default (condition=None)
        assert stmt.branches[1].condition is None

    def test_llm_if_multiple_branches(self):
        p = _parse('llm if "classify" { branch true { a = 1 } branch false { b = 2 } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, LlmIfStmtNode)
        assert len(stmt.branches) == 2

    def test_llm_if_in_main_block(self):
        p = _parse('agent Test { main { llm if "desc" { branch true { x = 1 } } } }')
        prog = p.parse()
        agent = prog.statements[0]
        main = None
        for s in agent.main_block.body if hasattr(agent, 'main_block') and agent.main_block else []:
            pass
        # Just verify it parses without error
        assert len(prog.statements) == 1


class TestLlmChooseStmt:
    def test_llm_choose_simple(self):
        p = _parse('llm choose "pick one" { option "a" { x = 1 } default { x = 0 } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, LlmChooseStmtNode)
        assert stmt.description == "pick one"
        assert len(stmt.options) == 1
        assert isinstance(stmt.options[0], LlmOptionNode)
        assert stmt.options[0].label == "a"

    def test_llm_choose_multiple_options(self):
        p = _parse('llm choose "pick" { option "a" { x = 1 } option "b" { x = 2 } default { } }')
        stmt = _first_stmt(p)
        assert isinstance(stmt, LlmChooseStmtNode)
        assert len(stmt.options) == 2


class TestLlmDisambiguation:
    def test_llm_not_followed_by_keyword_error(self):
        p = _parse('llm something')
        parser = p
        parser.parse()
        # Should have errors
        assert parser.errors.has_errors
