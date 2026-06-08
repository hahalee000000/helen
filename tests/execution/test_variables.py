"""Tests for helen.interpreter — variable declaration, const protection."""

import pytest

from helen.core.ast import (
    BinaryOpNode,
    ExprStmtNode,
    LiteralNode,
    ProgramNode,
    VarDeclNode,
    VariableNode,
)
from helen.core.errors import ErrorReporter
from helen.core.source import SourceSpan
from helen.core.tokens import Token, TokenType
from helen.interpreter.exceptions import ConstAssignmentError
from helen.interpreter.interpreter import Interpreter


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1) -> VariableNode:
    return VariableNode(name=name, span=_span(line))


def _assign(name: str, value, line: int = 2) -> BinaryOpNode:
    op_tok = Token(TokenType.ASSIGN, "=", None, line, 1, line, 2)
    return BinaryOpNode(
        left=_var(name, line),
        operator=op_tok,
        right=_lit(value, line),
        span=_span(line),
    )


def _run(*stmts) -> tuple:
    prog = ProgramNode(statements=list(stmts), span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors)
    result = interp.interpret(prog)
    return result, errors


class TestLetDeclaration:
    def test_let_declare_and_read(self):
        decl = VarDeclNode(name="x", type_annotation=None, initializer=_lit(42), mutable=True, span=_span())
        use = ExprStmtNode(expression=_var("x"), span=_span())
        result, errors = _run(decl, use)
        assert result == 42
        assert not errors.has_errors

    def test_let_reassign(self):
        decl = VarDeclNode(name="x", type_annotation=None, initializer=_lit(1), mutable=True, span=_span())
        reassign = ExprStmtNode(expression=_assign("x", 2), span=_span())
        use = ExprStmtNode(expression=_var("x"), span=_span(3))
        result, errors = _run(decl, reassign, use)
        assert result == 2
        assert not errors.has_errors


class TestConstDeclaration:
    def test_const_declare_and_read(self):
        decl = VarDeclNode(name="MAX", type_annotation=None, initializer=_lit(100), mutable=False, span=_span())
        use = ExprStmtNode(expression=_var("MAX"), span=_span())
        result, errors = _run(decl, use)
        assert result == 100
        assert not errors.has_errors

    def test_const_assignment_raises(self):
        decl = VarDeclNode(name="MAX", type_annotation=None, initializer=_lit(100), mutable=False, span=_span())
        reassign = ExprStmtNode(expression=_assign("MAX", 200), span=_span(2))
        with pytest.raises(ConstAssignmentError):
            _run(decl, reassign)


class TestVariableScope:
    def test_shadow_in_nested_scope(self):
        """Variable in inner scope shadows outer, but outer is unchanged."""
        from helen.core.ast import IfStmtNode, MainBlockNode

        # let x = 1
        outer_decl = VarDeclNode(name="x", type_annotation=None, initializer=_lit(1), mutable=True, span=_span())
        # if (true) { let x = 2; x }
        inner_decl = VarDeclNode(name="x", type_annotation=None, initializer=_lit(2), mutable=True, span=_span(2))
        inner_use = ExprStmtNode(expression=_var("x"), span=_span(3))
        then_block = MainBlockNode(body=[inner_decl, inner_use], span=_span())
        if_stmt = IfStmtNode(condition=_lit(True), then_branch=then_block, else_branch=None, span=_span())
        # use x (should be 1 from outer scope)
        final_use = ExprStmtNode(expression=_var("x"), span=_span(4))

        prog = ProgramNode(statements=[outer_decl, if_stmt, final_use], span=_span())
        errors = ErrorReporter()
        interp = Interpreter(errors)
        result = interp.interpret(prog)
        assert result == 1
        assert not errors.has_errors
