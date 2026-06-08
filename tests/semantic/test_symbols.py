"""Tests for hellen.semantic.symbols — Symbol, Scope, SymbolTable."""

import pytest

from hellen.semantic.symbols import Scope, Symbol, SymbolTable


# ---------------------------------------------------------------------------
# Symbol
# ---------------------------------------------------------------------------


class TestSymbol:
    def test_create_variable(self):
        s = Symbol(name="x", kind="variable")
        assert s.name == "x"
        assert s.kind == "variable"
        assert s.is_const is False
        assert s.type_node is None

    def test_create_const(self):
        s = Symbol(name="MAX", kind="variable", is_const=True)
        assert s.is_const is True

    def test_create_with_type(self):
        from hellen.core.ast import TypeNode
        from hellen.core.source import SourceSpan

        span = SourceSpan("<test>", 1, 1, 1, 5)
        tn = TypeNode(name="int", span=span)
        s = Symbol(name="x", kind="variable", type_node=tn)
        assert s.type_node.name == "int"

    def test_repr(self):
        s = Symbol(name="x", kind="variable")
        assert "x" in repr(s)
        assert "variable" in repr(s)


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


class TestScope:
    def test_define_and_resolve(self):
        scope = Scope(parent=None, name="test")
        s = Symbol(name="x", kind="variable")
        assert scope.define("x", s) is None
        assert scope.resolve("x") is s

    def test_define_duplicate(self):
        scope = Scope(parent=None, name="test")
        s1 = Symbol(name="x", kind="variable")
        s2 = Symbol(name="x", kind="param")
        assert scope.define("x", s1) is None
        assert scope.define("x", s2) is s1

    def test_resolve_not_found(self):
        scope = Scope(parent=None, name="test")
        assert scope.resolve("missing") is None

    def test_resolve_parent_chain(self):
        parent = Scope(parent=None, name="parent")
        child = Scope(parent=parent, name="child")
        s = Symbol(name="x", kind="variable")
        parent.define("x", s)
        assert child.resolve("x") is s

    def test_resolve_local_only(self):
        parent = Scope(parent=None, name="parent")
        child = Scope(parent=parent, name="child")
        parent.define("x", Symbol(name="x", kind="variable"))
        assert child.resolve_local("x") is None
        assert child.resolve("x") is not None


# ---------------------------------------------------------------------------
# SymbolTable
# ---------------------------------------------------------------------------


class TestSymbolTable:
    def test_initial_global_scope(self):
        st = SymbolTable()
        assert st.global_scope is not None
        assert st.current_scope is st.global_scope
        assert st.global_scope.scope_type == "global"

    def test_enter_exit_scope(self):
        st = SymbolTable()
        st.enter_scope("fn:test", "function")
        assert st.depth == 1
        assert st.current_scope.scope_type == "function"
        st.exit_scope()
        assert st.depth == 0
        assert st.current_scope is st.global_scope

    def test_nested_scopes(self):
        st = SymbolTable()
        st.enter_scope("outer", "block")
        st.enter_scope("inner", "block")
        assert st.depth == 2
        st.exit_scope()
        assert st.depth == 1
        st.exit_scope()
        assert st.depth == 0

    def test_define_and_resolve(self):
        st = SymbolTable()
        sym = Symbol(name="x", kind="variable")
        st.define("x", sym)
        assert st.resolve("x") is sym

    def test_resolve_across_scopes(self):
        st = SymbolTable()
        sym = Symbol(name="x", kind="variable")
        st.define("x", sym)
        st.enter_scope("inner", "block")
        assert st.resolve("x") is sym

    def test_shadowing(self):
        st = SymbolTable()
        outer = Symbol(name="x", kind="variable")
        st.define("x", outer)
        st.enter_scope("inner", "block")
        inner = Symbol(name="x", kind="variable")
        st.define("x", inner)
        resolved = st.resolve("x")
        assert resolved is inner
        st.exit_scope()
        assert st.resolve("x") is outer

    def test_duplicate_detection(self):
        st = SymbolTable()
        s1 = Symbol(name="x", kind="variable")
        s2 = Symbol(name="x", kind="variable")
        assert st.define("x", s1) is None
        assert st.define("x", s2) is s1  # returns existing

    def test_exit_at_global_returns_none(self):
        st = SymbolTable()
        assert st.exit_scope() is None

    def test_in_global_scope(self):
        st = SymbolTable()
        assert st.in_global_scope is True
        st.enter_scope("inner", "block")
        assert st.in_global_scope is False

    def test_current_scope_type(self):
        st = SymbolTable()
        assert st.current_scope_type == "global"
        st.enter_scope("fn", "function")
        assert st.current_scope_type == "function"

    def test_agent_scope(self):
        st = SymbolTable()
        st.enter_scope("agent:MyAgent", "agent")
        assert st.current_scope.scope_type == "agent"

    def test_scope_depth_zero_at_start(self):
        st = SymbolTable()
        assert st.depth == 0
