"""Tests for type conversion utilities."""

import pytest
from helen.core.ast import (
    TypeNode,
    OptionalTypeNode,
    UnionTypeNode,
    LiteralTypeNode,
)
from helen.core.source import SourceSpan
from helen.semantic.type_utils import type_from_typenode
from helen.semantic.types import (
    AnyType,
    IntType,
    FloatType,
    StringType,
    BoolType,
    NullType,
    ListType,
    MapType,
    OptionalType,
    UnionType,
    LiteralType,
)


def make_span():
    """Create a dummy SourceSpan for testing."""
    return SourceSpan(file="test.helen", start_line=1, start_col=1, end_line=1, end_col=10)


class TestTypeFromTypenode:
    """Tests for type_from_typenode function."""

    def test_none_returns_any(self):
        """None type_node returns AnyType."""
        result = type_from_typenode(None)
        assert isinstance(result, AnyType)

    def test_int_type(self):
        """int type returns IntType."""
        node = TypeNode(name="int", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, IntType)

    def test_integer_alias(self):
        """integer alias returns IntType."""
        node = TypeNode(name="integer", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, IntType)

    def test_float_type(self):
        """float type returns FloatType."""
        node = TypeNode(name="float", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, FloatType)

    def test_double_alias(self):
        """double alias returns FloatType."""
        node = TypeNode(name="double", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, FloatType)

    def test_str_type(self):
        """str type returns StringType."""
        node = TypeNode(name="str", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, StringType)

    def test_string_alias(self):
        """string alias returns StringType."""
        node = TypeNode(name="string", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, StringType)

    def test_bool_type(self):
        """bool type returns BoolType."""
        node = TypeNode(name="bool", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, BoolType)

    def test_boolean_alias(self):
        """boolean alias returns BoolType."""
        node = TypeNode(name="boolean", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, BoolType)

    def test_null_type(self):
        """null type returns NullType."""
        node = TypeNode(name="null", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, NullType)

    def test_any_type(self):
        """any type returns AnyType."""
        node = TypeNode(name="any", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, AnyType)

    def test_list_type(self):
        """list type returns ListType(AnyType)."""
        node = TypeNode(name="list", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, ListType)
        assert isinstance(result.element_type, AnyType)

    def test_map_type(self):
        """map type returns MapType(AnyType, AnyType)."""
        node = TypeNode(name="map", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, MapType)
        assert isinstance(result.key_type, AnyType)
        assert isinstance(result.value_type, AnyType)

    def test_optional_type(self):
        """OptionalTypeNode returns OptionalType."""
        inner = TypeNode(name="int", span=make_span())
        node = OptionalTypeNode(inner=inner, span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, OptionalType)
        assert isinstance(result.inner, IntType)

    def test_union_type(self):
        """UnionTypeNode returns UnionType."""
        members = [
            TypeNode(name="int", span=make_span()),
            TypeNode(name="str", span=make_span()),
        ]
        node = UnionTypeNode(members=members, span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, UnionType)
        # UnionType stores types in members list
        assert len(result.members) == 2
        assert isinstance(result.members[0], IntType)
        assert isinstance(result.members[1], StringType)

    def test_literal_type(self):
        """LiteralTypeNode returns LiteralType."""
        from helen.core.ast import LiteralNode
        values = [
            LiteralNode(value=1, span=make_span()),
            LiteralNode(value=2, span=make_span()),
            LiteralNode(value=3, span=make_span()),
        ]
        node = LiteralTypeNode(values=values, span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, LiteralType)
        assert len(result.values) == 3

    def test_unknown_type_returns_any(self):
        """Unknown type name returns AnyType."""
        node = TypeNode(name="unknown", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, AnyType)

    def test_case_insensitive(self):
        """Type names are case-insensitive."""
        node = TypeNode(name="INT", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, IntType)
