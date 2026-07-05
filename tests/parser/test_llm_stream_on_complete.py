"""Test llm act on_complete callback."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.core.ast import LlmActExprNode, ExprStmtNode


def _format_errors(errors: ErrorReporter) -> str:
    """格式化错误报告用于测试断言。"""
    return "\n".join(str(e) for e in errors.errors)


def _parse(source: str):
    """Parse source and return (program, errors)."""
    errors = ErrorReporter()
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    return program, errors


def _get_expr_stmt(program):
    """Extract the expression from the first statement (ExprStmtNode wrapping)."""
    stmt = program.statements[0]
    if isinstance(stmt, ExprStmtNode):
        return stmt.expression
    return stmt


class TestLlmActOnComplete:
    """Test llm act on_complete callback parsing."""

    def test_llm_act_with_on_complete(self):
        """Test parsing llm act with on_complete callback."""
        source = 'llm act "Hello" on_complete on_done'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.on_complete is not None

    def test_llm_act_with_both_callbacks(self):
        """Test parsing llm act with both on_chunk and on_complete."""
        source = 'llm act "Hello" on_chunk on_chunk on_complete on_done'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.on_chunk is not None
        assert node.on_complete is not None

    def test_llm_act_without_callbacks(self):
        """Test parsing llm act without any callbacks."""
        source = 'llm act "Hello"'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.on_chunk is None
        assert node.on_complete is None
