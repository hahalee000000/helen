"""Tests for llm act with on_chunk/on_complete callback parsing."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.core.ast import LlmActExprNode, ExprStmtNode, VariableNode


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


class TestLlmActCallbacks:
    """Tests for parsing llm act with on_chunk/on_complete callbacks."""

    def test_llm_act_basic(self):
        """llm act "prompt" should parse to LlmActExprNode without callbacks."""
        source = 'llm act "Hello"'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.on_chunk is None
        assert node.on_complete is None

    def test_llm_act_with_on_chunk(self):
        """llm act "prompt" on_chunk callback should parse with callback."""
        source = 'llm act "Hello" on_chunk my_callback'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        assert len(program.statements) == 1

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.on_chunk is not None
        assert isinstance(node.on_chunk, VariableNode)
        assert node.on_chunk.name == "my_callback"
        assert node.on_complete is None

    def test_llm_act_with_on_complete(self):
        """llm act "prompt" on_complete callback should parse."""
        source = 'llm act "Hello" on_complete done_fn'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.on_chunk is None
        assert node.on_complete is not None
        assert isinstance(node.on_complete, VariableNode)
        assert node.on_complete.name == "done_fn"

    def test_llm_act_with_both_callbacks(self):
        """llm act with both on_chunk and on_complete."""
        source = 'llm act "Hello" on_chunk cb1 on_complete cb2'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.on_chunk is not None
        assert node.on_chunk.name == "cb1"
        assert node.on_complete is not None
        assert node.on_complete.name == "cb2"

    def test_llm_act_expression_with_callback(self):
        """let result = llm act "prompt" on_chunk cb should work as expression."""
        source = 'let result = llm act "Hello" on_chunk my_cb'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"

        # The statement is a VarDeclNode; its initializer is LlmActExprNode
        stmt = program.statements[0]
        assert stmt.initializer is not None
        assert isinstance(stmt.initializer, LlmActExprNode)
        assert stmt.initializer.on_chunk is not None
        assert stmt.initializer.on_chunk.name == "my_cb"

    def test_llm_act_bare_form(self):
        """llm act without prompt should parse as bare form (for agent context)."""
        source = 'llm act'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Bare form should parse OK: {_format_errors(errors)}"
        assert len(program.statements) == 1

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.prompt is None
        assert node.on_chunk is None
        assert node.on_complete is None

    def test_llm_act_bare_form_with_on_chunk(self):
        """llm act on_chunk callback should work in bare form."""
        source = 'llm act on_chunk my_callback'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.prompt is None  # Bare form
        assert node.on_chunk is not None
        assert isinstance(node.on_chunk, VariableNode)
        assert node.on_chunk.name == "my_callback"

    def test_llm_act_bare_form_with_on_complete(self):
        """llm act on_complete callback should work in bare form."""
        source = 'llm act on_complete on_done'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.prompt is None  # Bare form
        assert node.on_complete is not None

    def test_llm_act_bare_form_with_both_callbacks(self):
        """llm act with both callbacks should work in bare form."""
        source = 'llm act on_chunk cb1 on_complete cb2'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.prompt is None  # Bare form
        assert node.on_chunk is not None
        assert node.on_chunk.name == "cb1"
        assert node.on_complete is not None
        assert node.on_complete.name == "cb2"

    def test_llm_act_with_lambda_callback(self):
        """llm act "prompt" on_chunk fn(chunk) { print(chunk) } should work."""
        source = 'llm act "Hello" on_chunk fn(chunk) { print(chunk) }'
        program, errors = _parse(source)

        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"

        node = _get_expr_stmt(program)
        assert isinstance(node, LlmActExprNode)
        assert node.on_chunk is not None

    def test_llm_if_still_works(self):
        """llm if should still work after refactoring."""
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
        program, errors = _parse(source)
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
