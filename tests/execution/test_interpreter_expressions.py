"""Tests for hellen.interpreter — expression evaluation."""

import pytest

from hellen.core.ast import (
    AccessNode,
    BinaryOpNode,
    CallArgNode,
    CallNode,
    ExprStmtNode,
    FnBlockNode,
    FunctionDeclNode,
    GroupingNode,
    IndexNode,
    ListLiteralNode,
    LiteralNode,
    MapEntryNode,
    MapLiteralNode,
    ProgramNode,
    UnaryOpNode,
    VariableNode,
)
from hellen.core.errors import ErrorReporter
from hellen.core.source import SourceSpan
from hellen.core.tokens import Token, TokenType
from hellen.interpreter.interpreter import Interpreter


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _tok(tt: TokenType = TokenType.IDENTIFIER, lexeme: str = "x") -> Token:
    return Token(tt, lexeme, None, 1, 1, 1, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1) -> VariableNode:
    return VariableNode(name=name, span=_span(line))


def _binary(op: TokenType, left, right, line: int = 1) -> BinaryOpNode:
    op_tok = Token(op, op.name, None, line, 1, line, 2)
    return BinaryOpNode(left=left, operator=op_tok, right=right, span=_span(line))


def _unary(op: TokenType, operand, line: int = 1) -> UnaryOpNode:
    op_tok = Token(op, op.name, None, line, 1, line, 2)
    return UnaryOpNode(operator=op_tok, operand=operand, span=_span(line))


def _run(expr) -> tuple:
    """Run an expression in a program and return (result, errors)."""
    from hellen.core.ast import ExprStmtNode, ProgramNode

    stmt = ExprStmtNode(expression=expr, span=_span())
    prog = ProgramNode(statements=[stmt], span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors)
    result = interp.interpret(prog)
    return result, errors


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------


class TestLiteralEvaluation:
    def test_int(self):
        result, _ = _run(_lit(42))
        assert result == 42

    def test_float(self):
        result, _ = _run(_lit(3.14))
        assert result == 3.14

    def test_string(self):
        result, _ = _run(_lit("hello"))
        assert result == "hello"

    def test_true(self):
        result, _ = _run(_lit(True))
        assert result is True

    def test_false(self):
        result, _ = _run(_lit(False))
        assert result is False

    def test_null(self):
        result, _ = _run(_lit(None))
        assert result is None


# ---------------------------------------------------------------------------
# Binary operations
# ---------------------------------------------------------------------------


class TestBinaryOps:
    def test_add(self):
        result, _ = _run(_binary(TokenType.PLUS, _lit(1), _lit(2)))
        assert result == 3

    def test_subtract(self):
        result, _ = _run(_binary(TokenType.MINUS, _lit(5), _lit(3)))
        assert result == 2

    def test_multiply(self):
        result, _ = _run(_binary(TokenType.STAR, _lit(3), _lit(4)))
        assert result == 12

    def test_divide(self):
        result, _ = _run(_binary(TokenType.SLASH, _lit(10), _lit(2)))
        assert result == 5.0

    def test_modulo(self):
        result, _ = _run(_binary(TokenType.PERCENT, _lit(10), _lit(3)))
        assert result == 1

    def test_string_concat(self):
        result, _ = _run(_binary(TokenType.PLUS, _lit("hello"), _lit(" world")))
        assert result == "hello world"

    def test_string_number_concat(self):
        result, _ = _run(_binary(TokenType.PLUS, _lit("x="), _lit(42)))
        assert result == "x=42"

    def test_equal(self):
        result, _ = _run(_binary(TokenType.EQUAL_EQUAL, _lit(1), _lit(1)))
        assert result is True
        result, _ = _run(_binary(TokenType.EQUAL_EQUAL, _lit(1), _lit(2)))
        assert result is False

    def test_not_equal(self):
        result, _ = _run(_binary(TokenType.BANG_EQUAL, _lit(1), _lit(2)))
        assert result is True

    def test_greater(self):
        result, _ = _run(_binary(TokenType.GREATER, _lit(5), _lit(3)))
        assert result is True

    def test_greater_equal(self):
        result, _ = _run(_binary(TokenType.GREATER_EQUAL, _lit(5), _lit(5)))
        assert result is True

    def test_less(self):
        result, _ = _run(_binary(TokenType.LESS, _lit(3), _lit(5)))
        assert result is True

    def test_less_equal(self):
        result, _ = _run(_binary(TokenType.LESS_EQUAL, _lit(5), _lit(5)))
        assert result is True

    def test_and(self):
        result, _ = _run(_binary(TokenType.AND, _lit(True), _lit(True)))
        assert result is True
        result, _ = _run(_binary(TokenType.AND, _lit(True), _lit(False)))
        assert result is False

    def test_or(self):
        result, _ = _run(_binary(TokenType.OR, _lit(False), _lit(True)))
        assert result is True
        result, _ = _run(_binary(TokenType.OR, _lit(False), _lit(False)))
        assert result is False


# ---------------------------------------------------------------------------
# Unary operations
# ---------------------------------------------------------------------------


class TestUnaryOps:
    def test_negate_bool(self):
        result, _ = _run(_unary(TokenType.BANG, _lit(True)))
        assert result is False
        result, _ = _run(_unary(TokenType.BANG, _lit(False)))
        assert result is True

    def test_negate_number(self):
        result, _ = _run(_unary(TokenType.MINUS, _lit(5)))
        assert result == -5


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


class TestGrouping:
    def test_grouped_expr(self):
        inner = _binary(TokenType.PLUS, _lit(1), _lit(2))
        grouped = GroupingNode(expression=inner, span=_span())
        result, _ = _run(grouped)
        assert result == 3


# ---------------------------------------------------------------------------
# Variable evaluation
# ---------------------------------------------------------------------------


class TestVariableEval:
    def test_lookup_undefined(self):
        result, errors = _run(_var("unknown"))
        assert errors.has_errors


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------


class TestCollections:
    def test_list_literal(self):
        node = ListLiteralNode(elements=[_lit(1), _lit(2), _lit(3)], span=_span())
        result, _ = _run(node)
        assert result == [1, 2, 3]

    def test_map_literal(self):
        entry = MapEntryNode(key=_lit("a"), value=_lit(1), span=_span())
        node = MapLiteralNode(entries=[entry], span=_span())
        result, _ = _run(node)
        assert result == {"a": 1}

    def test_index_list(self):
        lst = ListLiteralNode(elements=[_lit(10), _lit(20), _lit(30)], span=_span())
        node = IndexNode(target=lst, index=_lit(1), span=_span())
        result, _ = _run(node)
        assert result == 20

    def test_index_map(self):
        entry = MapEntryNode(key=_lit("x"), value=_lit(42), span=_span())
        mp = MapLiteralNode(entries=[entry], span=_span())
        node = IndexNode(target=mp, index=_lit("x"), span=_span())
        result, _ = _run(node)
        assert result == 42

    def test_access_dict_property(self):
        entry = MapEntryNode(key=_lit("name"), value=_lit("hellen"), span=_span())
        mp = MapLiteralNode(entries=[entry], span=_span())
        node = AccessNode(target=mp, property="name", span=_span())
        result, _ = _run(node)
        assert result == "hellen"


# ---------------------------------------------------------------------------
# Function call (basic)
# ---------------------------------------------------------------------------


class TestFunctionCall:
    def test_call_undefined(self):
        call = CallNode(callee=_var("unknown"), arguments=[], span=_span())
        result, errors = _run(call)
        assert errors.has_errors

    def test_call_defined_function(self):
        fn = FunctionDeclNode(
            name="add",
            params=[],
            return_type=None,
            body=FnBlockNode(body=[_lit(42)], span=_span()),
            span=_span(),
        )
        call = CallNode(callee=_var("add"), arguments=[], span=_span())
        prog = ProgramNode(statements=[fn, ExprStmtNode(expression=call, span=_span())], span=_span())
        errors = ErrorReporter()
        interp = Interpreter(errors)
        result = interp.interpret(prog)
        assert result == 42
        assert not errors.has_errors
