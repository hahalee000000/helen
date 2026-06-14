"""Tests for helen.semantic.types — Type hierarchy and compatibility."""

import pytest

from helen.semantic.types import (
    AnyType,
    BoolType,
    FloatType,
    IntType,
    ListType,
    LiteralType,
    MapType,
    NullType,
    NumberType,
    OptionalType,
    StringType,
    UnionType,
    type_compatible,
    type_of_literal,
)


# ---------------------------------------------------------------------------
# Type creation
# ---------------------------------------------------------------------------


class TestTypeCreation:
    def test_bool_type(self):
        t = BoolType()
        assert t.name == "BoolType"

    def test_number_type(self):
        t = NumberType()
        assert t.name == "NumberType"

    def test_int_type_is_number_subtype(self):
        assert isinstance(IntType(), NumberType)

    def test_float_type_is_number_subtype(self):
        assert isinstance(FloatType(), NumberType)

    def test_string_type(self):
        t = StringType()
        assert t.name == "StringType"

    def test_null_type(self):
        t = NullType()
        assert t.name == "NullType"

    def test_any_type(self):
        t = AnyType()
        assert t.name == "AnyType"

    def test_optional_type_name(self):
        t = OptionalType(StringType())
        assert t.name == "StringType?"

    def test_list_type_name(self):
        t = ListType(IntType())
        assert t.name == "List[IntType]"

    def test_map_type_name(self):
        t = MapType(StringType(), IntType())
        assert t.name == "Map[StringType, IntType]"

    def test_union_type_name(self):
        t = UnionType([StringType(), NullType()])
        assert t.name == "StringType | NullType"

    def test_literal_type_name(self):
        t = LiteralType([42, "hello"])
        assert "Literal" in t.name


# ---------------------------------------------------------------------------
# Type equality
# ---------------------------------------------------------------------------


class TestTypeEquality:
    def test_same_type_equal(self):
        assert BoolType() == BoolType()
        assert NumberType() == NumberType()

    def test_different_types_not_equal(self):
        assert BoolType() != NumberType()

    def test_optional_equality(self):
        assert OptionalType(StringType()) == OptionalType(StringType())
        assert OptionalType(StringType()) != OptionalType(IntType())

    def test_union_equality_order_independent(self):
        u1 = UnionType([StringType(), IntType()])
        u2 = UnionType([IntType(), StringType()])
        assert u1 == u2

    def test_literal_equality(self):
        l1 = LiteralType([42, "hello"])
        l2 = LiteralType(["hello", 42])
        assert l1 == l2


# ---------------------------------------------------------------------------
# type_of_literal
# ---------------------------------------------------------------------------


class TestTypeOfLiteral:
    def test_int(self):
        assert type_of_literal(42) == IntType()

    def test_float(self):
        assert type_of_literal(3.14) == FloatType()

    def test_string(self):
        assert type_of_literal("hello") == StringType()

    def test_bool_true(self):
        assert type_of_literal(True) == BoolType()

    def test_bool_false(self):
        assert type_of_literal(False) == BoolType()

    def test_none(self):
        assert type_of_literal(None) == NullType()

    def test_list(self):
        assert type_of_literal([1, 2]) == AnyType()

    def test_dict(self):
        assert type_of_literal({"a": 1}) == AnyType()


# ---------------------------------------------------------------------------
# type_compatible
# ---------------------------------------------------------------------------


class TestTypeCompatible:
    def test_same_type(self):
        assert type_compatible(StringType(), StringType()) is True
        assert type_compatible(BoolType(), BoolType()) is True
        assert type_compatible(NumberType(), NumberType()) is True

    def test_any_accepts_all(self):
        assert type_compatible(StringType(), AnyType()) is True
        assert type_compatible(NumberType(), AnyType()) is True
        assert type_compatible(BoolType(), AnyType()) is True

    def test_int_to_number(self):
        assert type_compatible(IntType(), NumberType()) is True

    def test_float_to_number(self):
        assert type_compatible(FloatType(), NumberType()) is True

    def test_string_to_number_incompatible(self):
        assert type_compatible(StringType(), NumberType()) is False

    def test_bool_to_string_incompatible(self):
        assert type_compatible(BoolType(), StringType()) is False

    def test_literal_int_to_number(self):
        lit = LiteralType([42])
        assert type_compatible(lit, NumberType()) is True

    def test_literal_string_to_string(self):
        lit = LiteralType(["hello"])
        assert type_compatible(lit, StringType()) is True

    def test_literal_mixed_to_number(self):
        lit = LiteralType([42, "oops"])
        assert type_compatible(lit, NumberType()) is False

    def test_null_to_optional(self):
        assert type_compatible(NullType(), OptionalType(StringType())) is True

    def test_string_to_optional_string(self):
        assert type_compatible(StringType(), OptionalType(StringType())) is True

    def test_int_to_optional_number(self):
        assert type_compatible(IntType(), OptionalType(NumberType())) is True

    def test_string_to_union(self):
        u = UnionType([StringType(), IntType()])
        assert type_compatible(StringType(), u) is True
        assert type_compatible(IntType(), u) is True
        assert type_compatible(BoolType(), u) is False

    def test_number_to_string(self):
        assert type_compatible(NumberType(), StringType()) is False

    def test_empty_literal_compatible(self):
        lit = LiteralType([])
        assert type_compatible(lit, StringType()) is True
