"""Tests for function declaration: params, return type, async fn."""

import pytest
from hellen.core.lexer import Scanner
from hellen.core.parser import Parser
from hellen.core.ast import (
    FunctionDeclNode, FnBlockNode, AgentParamNode, ProgramNode,
    TypeNode, OptionalTypeNode,
)


def _parse(source: str) -> Parser:
    scanner = Scanner(source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, scanner.errors)
    return parser


def _first_fn(parser: Parser) -> FunctionDeclNode:
    prog = parser.parse()
    assert isinstance(prog, ProgramNode)
    assert len(prog.statements) >= 1
    return prog.statements[0]


class TestFunctionDecl:
    def test_fn_simple(self):
        p = _parse('fn greet() { }')
        fn = _first_fn(p)
        assert isinstance(fn, FunctionDeclNode)
        assert fn.name == "greet"
        assert len(fn.params) == 0
        assert isinstance(fn.body, FnBlockNode)

    def test_fn_with_params(self):
        p = _parse('fn add(a: int, b: int) -> int { return a + b }')
        fn = _first_fn(p)
        assert isinstance(fn, FunctionDeclNode)
        assert len(fn.params) == 2
        assert fn.params[0].name == "a"
        assert fn.params[0].type_annotation is not None
        assert fn.params[0].type_annotation.name == "int"

    def test_fn_param_with_default(self):
        p = _parse('fn greet(name: str = "world") { }')
        fn = _first_fn(p)
        assert isinstance(fn, FunctionDeclNode)
        assert fn.params[0].name == "name"
        assert fn.params[0].default_value is not None

    def test_fn_optional_return_type(self):
        p = _parse('fn find() -> str? { return null }')
        fn = _first_fn(p)
        assert isinstance(fn, FunctionDeclNode)
        assert fn.return_type is not None
        assert isinstance(fn.return_type, OptionalTypeNode)

    def test_fn_no_return_type(self):
        p = _parse('fn noop() { }')
        fn = _first_fn(p)
        assert isinstance(fn, FunctionDeclNode)
        assert fn.return_type is None

    def test_fn_union_return_type(self):
        p = _parse('fn parse() -> int|str { return 1 }')
        fn = _first_fn(p)
        assert isinstance(fn, FunctionDeclNode)
        assert fn.return_type is not None
