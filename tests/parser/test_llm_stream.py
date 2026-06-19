"""Tests for llm stream statement parsing (Phase 2)."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.core.ast import LlmStreamStmtNode, VariableNode


def _format_errors(errors: ErrorReporter) -> str:
    """格式化错误报告用于测试断言。"""
    return "\n".join(str(e) for e in errors.errors)


class TestLlmStreamParsing:
    """Tests for parsing llm stream statements."""
    
    def test_llm_stream_basic(self):
        """llm stream "prompt" should parse to LlmStreamStmtNode."""
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
    
    def test_llm_stream_with_callback(self):
        """llm stream "prompt" on_chunk callback should parse with callback."""
        source = 'llm stream "Hello" on_chunk my_callback'
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
        assert isinstance(stmt.on_chunk, VariableNode)
        assert stmt.on_chunk.name == "my_callback"
    
    def test_llm_stream_with_expression(self):
        """llm stream should accept expression as prompt."""
        source = 'llm stream "Hello " + "World"'
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1
        
        stmt = program.statements[0]
        assert isinstance(stmt, LlmStreamStmtNode)
    
    def test_llm_stream_bare_form(self):
        """llm stream without prompt should parse as bare form (for agent context)."""
        source = 'llm stream'
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Bare form should parse OK: {_format_errors(errors)}"
        assert len(program.statements) == 1
        
        stmt = program.statements[0]
        assert isinstance(stmt, LlmStreamStmtNode)
        assert stmt.prompt is None  # Bare form has no prompt
        assert stmt.on_chunk is None
    
    def test_llm_if_still_works(self):
        """llm if should still work after adding stream."""
        source = '''
        llm if "test" {
            branch "yes" {
                print("yes")
            }
            default {
                print("no")
            }
        }
        '''
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
    
    def test_llm_act_still_works(self):
        """llm act should still work after adding stream."""
        source = 'llm act "test prompt"'
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
