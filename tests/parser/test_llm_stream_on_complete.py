"""Test llm stream on_complete callback."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.core.ast import ProgramNode, LlmStreamStmtNode, MainBlockNode


def _format_errors(errors: ErrorReporter) -> str:
    """格式化错误报告用于测试断言。"""
    return "\n".join(str(e) for e in errors.errors)


class TestLlmStreamOnComplete:
    """Test llm stream on_complete callback parsing."""

    def test_llm_stream_with_on_complete(self):
        """Test parsing llm stream with on_complete callback."""
        source = 'llm stream "Hello" on_complete on_done'
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1
        
        stmt = program.statements[0]
        assert isinstance(stmt, LlmStreamStmtNode)
        assert stmt.on_complete is not None

    def test_llm_stream_with_both_callbacks(self):
        """Test parsing llm stream with both on_chunk and on_complete."""
        source = 'llm stream "Hello" on_chunk on_chunk on_complete on_done'
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1
        
        stmt = program.statements[0]
        assert isinstance(stmt, LlmStreamStmtNode)
        assert stmt.on_chunk is not None
        assert stmt.on_complete is not None

    def test_llm_stream_without_callbacks(self):
        """Test parsing llm stream without any callbacks."""
        source = 'llm stream "Hello"'
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1
        
        stmt = program.statements[0]
        assert isinstance(stmt, LlmStreamStmtNode)
        assert stmt.on_chunk is None
        assert stmt.on_complete is None
