"""Tests for helen.interpreter — collections (list, map, index, access)."""

from helen.core.ast import (
    AccessNode,
    ExprStmtNode,
    IndexNode,
    ListLiteralNode,
    LiteralNode,
    MapEntryNode,
    MapLiteralNode,
    ProgramNode,
    VarDeclNode,
    VariableNode,
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
    from helen.interpreter.exceptions import RuntimeError as HelenRuntimeError
    prog = ProgramNode(statements=list(stmts), span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors)
    try:
        result = interp.interpret(prog)
    except HelenRuntimeError:
        result = None
    return result, errors


class TestListLiteral:
    def test_empty_list(self):
        lst = ListLiteralNode(elements=[], span=_span())
        result, _ = _run(ExprStmtNode(expression=lst, span=_span()))
        assert result == []

    def test_list_of_ints(self):
        lst = ListLiteralNode(elements=[_lit(1), _lit(2), _lit(3)], span=_span())
        result, _ = _run(ExprStmtNode(expression=lst, span=_span()))
        assert result == [1, 2, 3]

    def test_list_of_strings(self):
        lst = ListLiteralNode(elements=[_lit("a"), _lit("b")], span=_span())
        result, _ = _run(ExprStmtNode(expression=lst, span=_span()))
        assert result == ["a", "b"]


class TestMapLiteral:
    def test_empty_map(self):
        mp = MapLiteralNode(entries=[], span=_span())
        result, _ = _run(ExprStmtNode(expression=mp, span=_span()))
        assert result == {}

    def test_map_with_entries(self):
        e1 = MapEntryNode(key=_lit("name"), value=_lit("helen"), span=_span())
        e2 = MapEntryNode(key=_lit("version"), value=_lit(1), span=_span())
        mp = MapLiteralNode(entries=[e1, e2], span=_span())
        result, _ = _run(ExprStmtNode(expression=mp, span=_span()))
        assert result == {"name": "helen", "version": 1}


class TestIndexAccess:
    def test_index_list_by_int(self):
        lst = ListLiteralNode(elements=[_lit(10), _lit(20), _lit(30)], span=_span())
        idx = IndexNode(target=lst, index=_lit(0), span=_span())
        result, _ = _run(ExprStmtNode(expression=idx, span=_span()))
        assert result == 10

    def test_index_map_by_string(self):
        e = MapEntryNode(key=_lit("key"), value=_lit(42), span=_span())
        mp = MapLiteralNode(entries=[e], span=_span())
        idx = IndexNode(target=mp, index=_lit("key"), span=_span())
        result, _ = _run(ExprStmtNode(expression=idx, span=_span()))
        assert result == 42

    def test_index_out_of_bounds(self):
        lst = ListLiteralNode(elements=[_lit(1)], span=_span())
        idx = IndexNode(target=lst, index=_lit(5), span=_span())
        result, errors = _run(ExprStmtNode(expression=idx, span=_span()))
        assert errors.has_errors


class TestMemberAccess:
    def test_access_dict_property(self):
        e = MapEntryNode(key=_lit("x"), value=_lit(99), span=_span())
        mp = MapLiteralNode(entries=[e], span=_span())
        acc = AccessNode(target=mp, property="x", span=_span())
        result, _ = _run(ExprStmtNode(expression=acc, span=_span()))
        assert result == 99

    def test_access_missing_property(self):
        mp = MapLiteralNode(entries=[], span=_span())
        acc = AccessNode(target=mp, property="missing", span=_span())
        result, errors = _run(ExprStmtNode(expression=acc, span=_span()))
        assert errors.has_errors


class TestVariableCollections:
    def test_list_in_variable(self):
        """let xs = [1, 2, 3]; xs[1]"""
        lst = ListLiteralNode(elements=[_lit(1), _lit(2), _lit(3)], span=_span())
        decl = VarDeclNode(name="xs", type_annotation=None, initializer=lst, mutable=True, span=_span())
        idx = IndexNode(target=_var("xs", 2), index=_lit(1, 2), span=_span(2))
        result, errors = _run(decl, ExprStmtNode(expression=idx, span=_span(2)))
        assert result == 2
        assert not errors.has_errors

    def test_map_in_variable(self):
        """let m = {"k": 42}; m["k"]"""
        e = MapEntryNode(key=_lit("k"), value=_lit(42), span=_span())
        mp = MapLiteralNode(entries=[e], span=_span())
        decl = VarDeclNode(name="m", type_annotation=None, initializer=mp, mutable=True, span=_span())
        idx = IndexNode(target=_var("m", 2), index=_lit("k", 2), span=_span(2))
        result, errors = _run(decl, ExprStmtNode(expression=idx, span=_span(2)))
        assert result == 42
        assert not errors.has_errors
