"""Tests for helen.interpreter — control flow execution."""

import pytest

from helen.core.ast import (
    BreakStmtNode,
    CaseNode,
    ContinueStmtNode,
    ExprStmtNode,
    ForStmtNode,
    IfStmtNode,
    LiteralNode,
    MainBlockNode,
    MatchStmtNode,
    ProgramNode,
    VarDeclNode,
    VariableNode,
    WhileStmtNode,
)
from helen.core.errors import ErrorReporter
from helen.core.source import SourceSpan
from helen.interpreter.interpreter import Interpreter


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1) -> VariableNode:
    return VariableNode(name=name, span=_span(line))


def _run(*stmts) -> tuple:
    prog = ProgramNode(statements=list(stmts), span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors)
    result = interp.interpret(prog)
    return result, errors


class TestIfStatement:
    def test_if_true_branch(self):
        from helen.core.ast import ExprStmtNode

        then_block = MainBlockNode(body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span())
        stmt = IfStmtNode(condition=_lit(True), then_branch=then_block, else_branch=None, span=_span())
        result, errors = _run(stmt)
        assert result == 1
        assert not errors.has_errors

    def test_if_false_then_else(self):
        from helen.core.ast import ExprStmtNode

        then_block = MainBlockNode(body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span())
        else_block = MainBlockNode(body=[ExprStmtNode(expression=_lit(2), span=_span())], span=_span())
        stmt = IfStmtNode(condition=_lit(False), then_branch=then_block, else_branch=else_block, span=_span())
        result, errors = _run(stmt)
        assert result == 2
        assert not errors.has_errors

    def test_if_false_no_else(self):
        then_block = MainBlockNode(body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span())
        stmt = IfStmtNode(condition=_lit(False), then_branch=then_block, else_branch=None, span=_span())
        result, errors = _run(stmt)
        assert result is None
        assert not errors.has_errors


class TestForLoop:
    def test_for_iteration(self):
        """for x in [1, 2, 3] { x }"""
        # We need to build the AST manually since we don't have a list variable
        # Use a list literal directly
        from helen.core.ast import ExprStmtNode, ListLiteralNode

        lst = ListLiteralNode(elements=[_lit(1), _lit(2), _lit(3)], span=_span())
        body = ExprStmtNode(expression=_var("x"), span=_span())
        stmt = ForStmtNode(iterator=_var("x"), iterable=lst, body=body, span=_span())
        result, errors = _run(stmt)
        # Last iteration result
        assert result == 3
        assert not errors.has_errors

    def test_break_in_for(self):
        """for x in [1, 2, 3, 4, 5] { if (x == 3) break; x }"""
        from helen.core.ast import BinaryOpNode, ExprStmtNode, IfStmtNode, ListLiteralNode, MainBlockNode

        lst = ListLiteralNode(elements=[_lit(1), _lit(2), _lit(3), _lit(4), _lit(5)], span=_span())

        # if (x == 3) break
        eq = BinaryOpNode(left=_var("x"), operator=_make_tok(), right=_lit(3), span=_span())
        break_stmt = BreakStmtNode(span=_span())
        if_then = MainBlockNode(body=[break_stmt], span=_span())
        if_stmt = IfStmtNode(condition=eq, then_branch=if_then, else_branch=None, span=_span())

        # x (expression statement)
        expr = ExprStmtNode(expression=_var("x"), span=_span())

        body = MainBlockNode(body=[if_stmt, expr], span=_span())
        stmt = ForStmtNode(iterator=_var("x"), iterable=lst, body=body, span=_span())
        result, errors = _run(stmt)
        # BreakSentinel is consumed by the loop; top-level returns None
        assert result is None
        assert not errors.has_errors

    def test_continue_in_for(self):
        """for x in [1, 2, 3] { if (x == 2) continue; x }"""
        from helen.core.ast import BinaryOpNode, ExprStmtNode, IfStmtNode, ListLiteralNode, MainBlockNode

        lst = ListLiteralNode(elements=[_lit(1), _lit(2), _lit(3)], span=_span())

        eq = BinaryOpNode(left=_var("x"), operator=_make_tok(), right=_lit(2), span=_span())
        cont_stmt = ContinueStmtNode(span=_span())
        if_then = MainBlockNode(body=[cont_stmt], span=_span())
        if_stmt = IfStmtNode(condition=eq, then_branch=if_then, else_branch=None, span=_span())

        expr = ExprStmtNode(expression=_var("x"), span=_span())
        body = MainBlockNode(body=[if_stmt, expr], span=_span())
        stmt = ForStmtNode(iterator=_var("x"), iterable=lst, body=body, span=_span())
        result, errors = _run(stmt)
        assert result == 3  # 1, then skip 2, then 3
        assert not errors.has_errors


class TestWhileLoop:
    def test_while_iteration(self):
        """let i = 0; while (i < 3) { i = i + 1 }"""
        from helen.core.ast import BinaryOpNode, ExprStmtNode, MainBlockNode

        i_decl = VarDeclNode(name="i", type_annotation=None, initializer=_lit(0), mutable=True, span=_span())

        cond = BinaryOpNode(left=_var("i"), operator=_make_tok(name="LESS", lexeme="<"), right=_lit(3), span=_span(2))

        # i = i + 1
        add = BinaryOpNode(left=_var("i", 3), operator=_make_tok(name="PLUS", lexeme="+"), right=_lit(1), span=_span(3))
        assign = BinaryOpNode(left=_var("i", 3), operator=_make_tok(name="ASSIGN", lexeme="="), right=add, span=_span(3))

        body = MainBlockNode(body=[ExprStmtNode(expression=assign, span=_span(3))], span=_span())
        while_stmt = WhileStmtNode(condition=cond, body=body, span=_span(2))
        final_use = ExprStmtNode(expression=_var("i"), span=_span(4))

        result, errors = _run(i_decl, while_stmt, final_use)
        assert result == 3
        assert not errors.has_errors

    def test_while_break(self):
        """let i = 0; while (true) { i = i + 1; if (i == 2) break }"""
        from helen.core.ast import BinaryOpNode, ExprStmtNode, IfStmtNode, MainBlockNode

        i_decl = VarDeclNode(name="i", type_annotation=None, initializer=_lit(0), mutable=True, span=_span())

        # while (true)
        cond = _lit(True)

        # i = i + 1
        add = BinaryOpNode(left=_var("i", 2), operator=_make_tok(name="PLUS", lexeme="+"), right=_lit(1), span=_span(2))
        assign = BinaryOpNode(left=_var("i", 2), operator=_make_tok(name="ASSIGN", lexeme="="), right=add, span=_span(2))

        # if (i == 2) break
        eq = BinaryOpNode(left=_var("i", 3), operator=_make_tok(name="EQUAL_EQUAL", lexeme="=="), right=_lit(2), span=_span(3))
        break_stmt = BreakStmtNode(span=_span(3))
        if_then = MainBlockNode(body=[break_stmt], span=_span())
        if_stmt = IfStmtNode(condition=eq, then_branch=if_then, else_branch=None, span=_span(3))

        body = MainBlockNode(body=[ExprStmtNode(expression=assign, span=_span(2)), if_stmt], span=_span())
        while_stmt = WhileStmtNode(condition=cond, body=body, span=_span(2))
        final_use = ExprStmtNode(expression=_var("i"), span=_span(4))

        result, errors = _run(i_decl, while_stmt, final_use)
        assert result == 2
        assert not errors.has_errors


class TestMatchStatement:
    def test_match_first_case(self):
        stmt = MatchStmtNode(
            subject=_lit("a"),
            cases=[
                CaseNode(pattern=_lit("a"), body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span()),
                CaseNode(pattern=_lit("b"), body=[ExprStmtNode(expression=_lit(2), span=_span())], span=_span()),
            ],
            default=[ExprStmtNode(expression=_lit(0), span=_span())],
            span=_span(),
        )
        result, errors = _run(stmt)
        assert result == 1
        assert not errors.has_errors

    def test_match_second_case(self):
        stmt = MatchStmtNode(
            subject=_lit("b"),
            cases=[
                CaseNode(pattern=_lit("a"), body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span()),
                CaseNode(pattern=_lit("b"), body=[ExprStmtNode(expression=_lit(2), span=_span())], span=_span()),
            ],
            default=[ExprStmtNode(expression=_lit(0), span=_span())],
            span=_span(),
        )
        result, errors = _run(stmt)
        assert result == 2
        assert not errors.has_errors

    def test_match_default(self):
        stmt = MatchStmtNode(
            subject=_lit("c"),
            cases=[
                CaseNode(pattern=_lit("a"), body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span()),
                CaseNode(pattern=_lit("b"), body=[ExprStmtNode(expression=_lit(2), span=_span())], span=_span()),
            ],
            default=[ExprStmtNode(expression=_lit(0), span=_span())],
            span=_span(),
        )
        result, errors = _run(stmt)
        assert result == 0
        assert not errors.has_errors


def _make_tok(name: str = "EQUAL_EQUAL", lexeme: str = "==") -> "Token":
    from helen.core.tokens import Token, TokenType

    tt = getattr(TokenType, name, TokenType.EQUAL_EQUAL)
    return Token(tt, lexeme, None, 1, 1, 1, len(lexeme) + 1)
