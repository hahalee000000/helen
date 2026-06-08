"""Type system for the Hellen language.

Defines the type hierarchy and type compatibility checking for
progressive type analysis. V1 supports literal type inference and
basic type annotation validation.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Type hierarchy
# ---------------------------------------------------------------------------


class Type(ABC):
    """Abstract base class for all Hellen types."""

    @property
    def name(self) -> str:
        """Human-readable type name."""
        return type(self).__name__

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Type):
            return NotImplemented
        return type(self) is type(other)

    def __hash__(self) -> int:
        return hash(type(self))

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True)
class AnyType(Type):
    """Dynamic mode default type — accepts any value."""

    def __repr__(self) -> str:
        return "AnyType"


@dataclass(frozen=True)
class BoolType(Type):
    """Boolean type (true/false)."""

    def __repr__(self) -> str:
        return "BoolType"


@dataclass(frozen=True)
class NumberType(Type):
    """Numeric type (int or float)."""

    def __repr__(self) -> str:
        return "NumberType"


@dataclass(frozen=True)
class IntType(NumberType):
    """Integer subtype of NumberType."""

    def __repr__(self) -> str:
        return "IntType"


@dataclass(frozen=True)
class FloatType(NumberType):
    """Float subtype of NumberType."""

    def __repr__(self) -> str:
        return "FloatType"


@dataclass(frozen=True)
class StringType(Type):
    """String type."""

    def __repr__(self) -> str:
        return "StringType"


@dataclass(frozen=True)
class NullType(Type):
    """Null type."""

    def __repr__(self) -> str:
        return "NullType"


@dataclass(frozen=True)
class OptionalType(Type):
    """Optional type: T? (equivalent to T | null).

    Attributes:
        inner: The wrapped type.
    """

    inner: Type

    @property
    def name(self) -> str:
        return f"{self.inner.name}?"

    def __repr__(self) -> str:
        return f"OptionalType({self.inner!r})"


@dataclass(frozen=True)
class ListType(Type):
    """Generic list type: List[T].

    Attributes:
        element_type: The type of list elements.
    """

    element_type: Type

    @property
    def name(self) -> str:
        return f"List[{self.element_type.name}]"

    def __repr__(self) -> str:
        return f"ListType({self.element_type!r})"


@dataclass(frozen=True)
class MapType(Type):
    """Generic map type: Map[K, V].

    Attributes:
        key_type: The type of map keys.
        value_type: The type of map values.
    """

    key_type: Type
    value_type: Type

    @property
    def name(self) -> str:
        return f"Map[{self.key_type.name}, {self.value_type.name}]"

    def __repr__(self) -> str:
        return f"MapType({self.key_type!r}, {self.value_type!r})"


@dataclass(frozen=True)
class UnionType(Type):
    """Union type: A | B | C.

    Attributes:
        members: The constituent types.
    """

    members: list[Type]

    @property
    def name(self) -> str:
        return " | ".join(m.name for m in self.members)

    def __repr__(self) -> str:
        return f"UnionType({self.members!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UnionType):
            return NotImplemented
        return set(self.members) == set(other.members)

    def __hash__(self) -> int:
        return hash(frozenset(self.members))


@dataclass(frozen=True)
class LiteralType(Type):
    """Literal type: Literal["hello", 42].

    Attributes:
        values: The allowed literal values.
    """

    values: list[Any]

    @property
    def name(self) -> str:
        vals = ", ".join(repr(v) for v in self.values)
        return f"Literal[{vals}]"

    def __repr__(self) -> str:
        return f"LiteralType({self.values!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LiteralType):
            return NotImplemented
        return set(self.values) == set(other.values)

    def __hash__(self) -> int:
        return hash(frozenset(self.values))


@dataclass(frozen=True)
class AgentType(Type):
    """Agent reference type.

    Attributes:
        agent_name: The name of the referenced agent.
    """

    agent_name: str

    @property
    def name(self) -> str:
        return f"Agent({self.agent_name})"

    def __repr__(self) -> str:
        return f"AgentType({self.agent_name!r})"


# Singleton instances for common types
BOOL_TYPE = BoolType()
NUMBER_TYPE = NumberType()
INT_TYPE = IntType()
FLOAT_TYPE = FloatType()
STRING_TYPE = StringType()
NULL_TYPE = NullType()
ANY_TYPE = AnyType()


# ---------------------------------------------------------------------------
# Type compatibility
# ---------------------------------------------------------------------------


def type_compatible(actual: Type, expected: Type) -> bool:
    """Check if 'actual' type can be assigned to 'expected' type.

    Compatibility rules (v1):
    - AnyType is compatible with everything
    - IntType is compatible with NumberType (subtype)
    - FloatType is compatible with NumberType (subtype)
    - LiteralType is compatible with the type of its values
    - OptionalType[T] accepts T or NullType
    - UnionType accepts any of its member types
    - Same type is always compatible

    Args:
        actual: The type of the value being assigned.
        expected: The type annotation on the target.

    Returns:
        True if the assignment is type-safe.
    """
    # Anything is compatible with AnyType
    if isinstance(expected, AnyType):
        return True

    # Same type
    if type(actual) is type(expected):
        return True

    # IntType/FloatType → NumberType (subtype)
    if isinstance(expected, NumberType) and isinstance(actual, (IntType, FloatType, NumberType)):
        return True

    # LiteralType → underlying type
    if isinstance(actual, LiteralType):
        if not actual.values:
            return True
        # Check if all literal values are compatible with expected
        return all(type_compatible(type_of_literal(v), expected) for v in actual.values)

    # NullType → OptionalType[T]
    if isinstance(expected, OptionalType) and isinstance(actual, NullType):
        return True

    # T → OptionalType[T]
    if isinstance(expected, OptionalType) and type_compatible(actual, expected.inner):
        return True

    # T → UnionType if T is one of the members
    if isinstance(expected, UnionType):
        return any(type_compatible(actual, member) for member in expected.members)

    # NullType compatible check for OptionalType
    if isinstance(expected, OptionalType):
        return isinstance(actual, NullType) or type_compatible(actual, expected.inner)

    return False


def type_of_literal(value: Any) -> Type:
    """Infer the Hellen type from a Python literal value.

    Mapping:
    - bool → BoolType
    - int → NumberType (v1: no IntType distinction)
    - float → NumberType
    - str → StringType
    - None → NullType
    - list → AnyType (v1: no container inference)
    - dict → AnyType (v1: no container inference)

    Args:
        value: A Python literal value.

    Returns:
        The corresponding Hellen Type instance.
    """
    if value is None:
        return NULL_TYPE
    if isinstance(value, bool):
        return BOOL_TYPE
    if isinstance(value, int):
        return NUMBER_TYPE
    if isinstance(value, float):
        return NUMBER_TYPE
    if isinstance(value, str):
        return STRING_TYPE
    return ANY_TYPE
