"""Tests for type parsing: optional, union, and literal types."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.ast import (
    OptionalTypeNode, UnionTypeNode, VarDeclNode, ProgramNode,
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


class TestOptionalType:
    def test_optional_type_annotation(self):
        p = _parse('let x: str? = null')
        stmt = _first_stmt(p)
        assert isinstance(stmt, VarDeclNode)
        assert stmt.type_annotation is not None
        assert isinstance(stmt.type_annotation, OptionalTypeNode)

    def test_optional_in_function_param(self):
        p = _parse('fn f(x: int?) { }')
        prog = p.parse()
        fn = prog.statements[0]
        assert isinstance(fn.params[0].type_annotation, OptionalTypeNode)


class TestUnionType:
    def test_union_type_annotation(self):
        p = _parse('let x: int|str = 1')
        stmt = _first_stmt(p)
        assert isinstance(stmt, VarDeclNode)
        assert stmt.type_annotation is not None
        assert isinstance(stmt.type_annotation, UnionTypeNode)
        assert len(stmt.type_annotation.members) == 2

    def test_union_type_three_members(self):
        p = _parse('let x: int|str|bool = true')
        stmt = _first_stmt(p)
        assert isinstance(stmt, VarDeclNode)
        assert isinstance(stmt.type_annotation, UnionTypeNode)
        assert len(stmt.type_annotation.members) == 3


class TestTypeInFunctionReturn:
    def test_optional_return_type(self):
        p = _parse('fn f(): str? { return null }')
        prog = p.parse()
        fn = prog.statements[0]
        assert isinstance(fn.return_type, OptionalTypeNode)

    def test_union_return_type(self):
        p = _parse('fn f(): int|str { return 1 }')
        prog = p.parse()
        fn = prog.statements[0]
        assert isinstance(fn.return_type, UnionTypeNode)
