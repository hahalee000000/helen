"""Tests for expression parsing: index, member access, list/map literals, template refs, await."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.ast import (
    IndexNode, AccessNode, ListLiteralNode, MapLiteralNode, MapEntryNode,
    TemplateRefNode, UnaryOpNode, CallNode, VariableNode, BinaryOpNode,
    LiteralNode, ProgramNode, ExprStmtNode,
)
from helen.core.tokens import TokenType


def _parse(source: str) -> Parser:
    scanner = Scanner(source, file="<test>")
    tokens = scanner.scan_all()
    errors = scanner.errors
    parser = Parser(tokens, errors)
    return parser


def _first_stmt(parser: Parser):
    prog = parser.parse()
    assert isinstance(prog, ProgramNode)
    assert len(prog.statements) >= 1
    stmt = prog.statements[0]
    if isinstance(stmt, ExprStmtNode):
        return stmt.expression
    return stmt


class TestIndexAccess:
    def test_index_access(self):
        p = _parse("x[0]")
        expr = _first_stmt(p)
        assert isinstance(expr, IndexNode)
        assert isinstance(expr.target, VariableNode)
        assert expr.target.name == "x"
        assert isinstance(expr.index, LiteralNode)

    def test_nested_index(self):
        p = _parse("arr[i][j]")
        expr = _first_stmt(p)
        assert isinstance(expr, IndexNode)
        # outer index is [j]
        assert isinstance(expr.index, VariableNode)
        assert expr.index.name == "j"
        # target is arr[i]
        assert isinstance(expr.target, IndexNode)


class TestMemberAccess:
    def test_member_access(self):
        p = _parse("obj.field")
        expr = _first_stmt(p)
        assert isinstance(expr, AccessNode)
        assert expr.property == "field"
        assert isinstance(expr.target, VariableNode)
        assert expr.target.name == "obj"

    def test_chained_access(self):
        p = _parse("obj.field.method")
        expr = _first_stmt(p)
        assert isinstance(expr, AccessNode)
        assert expr.property == "method"
        assert isinstance(expr.target, AccessNode)
        assert expr.target.property == "field"


class TestListLiteral:
    def test_list_literal_empty(self):
        p = _parse("[]")
        expr = _first_stmt(p)
        assert isinstance(expr, ListLiteralNode)
        assert len(expr.elements) == 0

    def test_list_literal_items(self):
        p = _parse("[1, 2, 3]")
        expr = _first_stmt(p)
        assert isinstance(expr, ListLiteralNode)
        assert len(expr.elements) == 3
        assert all(isinstance(e, LiteralNode) for e in expr.elements)

    def test_list_literal_mixed(self):
        p = _parse("[x, 1, \"hello\"]")
        expr = _first_stmt(p)
        assert isinstance(expr, ListLiteralNode)
        assert len(expr.elements) == 3


class TestMapLiteral:
    def test_map_literal_empty(self):
        p = _parse("{}")
        expr = _first_stmt(p)
        assert isinstance(expr, MapLiteralNode)
        assert len(expr.entries) == 0

    def test_map_literal_entries(self):
        p = _parse('{"a": 1, "b": 2}')
        expr = _first_stmt(p)
        assert isinstance(expr, MapLiteralNode)
        assert len(expr.entries) == 2
        entry = expr.entries[0]
        assert isinstance(entry, MapEntryNode)
        assert isinstance(entry.key, LiteralNode)
        assert isinstance(entry.value, LiteralNode)


class TestTemplateRef:
    def test_template_ref(self):
        p = _parse("{{x}}")
        expr = _first_stmt(p)
        assert isinstance(expr, TemplateRefNode)
        assert isinstance(expr.expression, VariableNode)
        assert expr.expression.name == "x"

    def test_template_ref_expression(self):
        p = _parse("{{a + b}}")
        expr = _first_stmt(p)
        assert isinstance(expr, TemplateRefNode)
        assert isinstance(expr.expression, BinaryOpNode)


class TestAwaitPrefix:
    def test_await_prefix_call(self):
        p = _parse("await fetchData()")
        expr = _first_stmt(p)
        assert isinstance(expr, UnaryOpNode)
        assert expr.operator.type == TokenType.AWAIT
        assert isinstance(expr.operand, CallNode)


class TestComplexExpressions:
    def test_index_plus_list(self):
        p = _parse("a[0].b + [1, 2]")
        expr = _first_stmt(p)
        assert isinstance(expr, BinaryOpNode)
        assert isinstance(expr.left, AccessNode)
        assert isinstance(expr.right, ListLiteralNode)

    def test_map_in_list(self):
        p = _parse('[{"k": v}]')
        expr = _first_stmt(p)
        assert isinstance(expr, ListLiteralNode)
        assert len(expr.elements) == 1
        assert isinstance(expr.elements[0], MapLiteralNode)
