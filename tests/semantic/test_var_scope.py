"""Tests for variable scoping — block, function, global, const protection."""

import pytest

from helen.core.ast import (
    FnBlockNode,
    FunctionDeclNode,
    MainBlockNode,
    ProgramNode,
    VarDeclNode,
    VariableNode,
)
from helen.core.errors import ErrorCode, ErrorReporter
from helen.core.source import SourceSpan
from helen.semantic.analyzer import SemanticAnalyzer


def _span(line: int = 1, col: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, col, line, col + 4)


def _literal(value, line: int = 1):
    from helen.core.ast import LiteralNode
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1):
    return VariableNode(name=name, span=_span(line))


class TestBlockScope:
    """Block-scoped variables (let) are only visible within the block."""

    def test_let_visible_in_same_block(self):
        decl = VarDeclNode(name="x", type_annotation=None, initializer=_literal(42), mutable=True, span=_span())
        use = _var("x")
        prog = ProgramNode(statements=[decl, use], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_block_scope_isolation_via_if(self):
        """Variable declared inside if-then should not be visible outside."""
        from helen.core.ast import IfStmtNode

        # let x = 1 inside the then-branch
        inner_decl = VarDeclNode(name="x", type_annotation=None, initializer=_literal(1), mutable=True, span=_span())
        then_block = inner_decl  # then_branch is a StatementNode
        if_stmt = IfStmtNode(condition=_literal(True), then_branch=then_block, else_branch=None, span=_span())
        # try to use x outside the if
        use_outside = _var("x")
        prog = ProgramNode(statements=[if_stmt, use_outside], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        # x is NOT visible outside the if block
        assert errors.has_errors
        assert any(e.code == ErrorCode.UNDECLARED_VARIABLE for e in errors.errors)


class TestFunctionScope:
    """Function parameters are visible in the function body."""

    def test_param_visible_in_body(self):
        param_decl = _make_param("data")
        fn_body = FnBlockNode(body=[_var("data")], span=_span())
        fn = FunctionDeclNode(name="process", params=[param_decl], return_type=None, body=fn_body, span=_span())
        prog = ProgramNode(statements=[fn], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_param_not_visible_outside(self):
        param_decl = _make_param("data")
        fn_body = FnBlockNode(body=[], span=_span())
        fn = FunctionDeclNode(name="process", params=[param_decl], return_type=None, body=fn_body, span=_span())
        use_outside = _var("data")
        prog = ProgramNode(statements=[fn, use_outside], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.UNDECLARED_VARIABLE for e in errors.errors)


class TestGlobalScope:
    """Global declarations are visible everywhere."""

    def test_global_visible_in_fn(self):
        global_decl = VarDeclNode(name="g", type_annotation=None, initializer=_literal(42), mutable=True, span=_span())
        fn_body = FnBlockNode(body=[_var("g")], span=_span())
        fn = FunctionDeclNode(name="f", params=[], return_type=None, body=fn_body, span=_span())
        prog = ProgramNode(statements=[global_decl, fn], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors


class TestConstProtection:
    """Const variables are marked in the symbol table."""

    def test_const_marked_immutable(self):
        from helen.semantic.symbols import Symbol, SymbolTable

        st = SymbolTable()
        sym = Symbol(name="MAX", kind="variable", is_const=True)
        st.define("MAX", sym)
        resolved = st.resolve("MAX")
        assert resolved is not None
        assert resolved.is_const is True

    def test_let_not_const(self):
        from helen.semantic.symbols import Symbol, SymbolTable

        st = SymbolTable()
        sym = Symbol(name="x", kind="variable", is_const=False)
        st.define("x", sym)
        resolved = st.resolve("x")
        assert resolved is not None
        assert resolved.is_const is False


def _make_param(name: str):
    from helen.core.ast import AgentParamNode
    return AgentParamNode(name=name, type_annotation=None, default_value=None, span=_span())
