"""Type conversion utilities for the Helen language.

Shared functions for converting AST type nodes to semantic types.
Used by both the semantic analyzer and the interpreter.
"""

from __future__ import annotations

from helen.core.ast import (
    LiteralTypeNode,
    OptionalTypeNode,
    TypeNode,
    UnionTypeNode,
)
from helen.semantic.types import (
    AnyType,
    BoolType,
    FloatType,
    IntType,
    ListType,
    LiteralType,
    MapType,
    NullType,
    OptionalType,
    StringType,
    Type,
    UnionType,
)


def type_from_typenode(type_node: TypeNode | None) -> Type:
    """Convert an AST TypeNode to a semantic Type.

    This is a shared utility used by both the semantic analyzer and
    the interpreter to avoid code duplication.

    Args:
        type_node: The AST type node to convert, or None.

    Returns:
        The corresponding semantic Type instance.
    """
    if type_node is None:
        return AnyType()

    # Handle composite type nodes
    if isinstance(type_node, OptionalTypeNode):
        return OptionalType(type_from_typenode(type_node.inner))
    if isinstance(type_node, UnionTypeNode):
        return UnionType([type_from_typenode(m) for m in type_node.members])
    if isinstance(type_node, LiteralTypeNode):
        return LiteralType(type_node.values)

    name = type_node.name.lower()
    if name in ("int", "integer"):
        return IntType()
    if name in ("float", "double"):
        return FloatType()
    if name in ("str", "string"):
        return StringType()
    if name in ("bool", "boolean"):
        return BoolType()
    if name == "null":
        return NullType()
    if name == "any":
        return AnyType()
    if name == "list":
        return ListType(AnyType())
    if name == "map":
        return MapType(AnyType(), AnyType())
    # Unknown type names → AnyType (v1 lenient)
    return AnyType()
