"""Symbol table and scope management for the Helen language.

Provides hierarchical symbol resolution across nested scopes (global,
agent, function, block) with agent-boundary isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from helen.core.ast import TypeNode


@dataclass
class Symbol:
    """A named entity in the symbol table.

    Attributes:
        name: The identifier name.
        kind: The symbol kind ('variable', 'function', 'agent', 'param', 'import').
        type_node: Optional type annotation from the source.
        is_const: Whether the symbol is immutable (const declaration).
    """

    name: str
    kind: str
    type_node: "TypeNode | None" = None
    is_const: bool = False

    def __repr__(self) -> str:
        const_flag = "const " if self.is_const else ""
        type_str = f": {self.type_node.name}" if self.type_node else ""
        return f"Symbol({const_flag}{self.name}{type_str}, kind={self.kind})"


@dataclass
class Scope:
    """A single scope level in the symbol table hierarchy.

    Attributes:
        parent: The enclosing scope (None for global).
        name: A descriptive name for this scope.
        scope_type: The type of scope ('global', 'agent', 'function', 'block').
        symbols: The symbols defined in this scope.
    """

    parent: "Scope | None"
    name: str
    scope_type: str = "block"
    symbols: dict[str, Symbol] = field(default_factory=dict)

    def define(self, name: str, symbol: Symbol) -> Symbol | None:
        """Define a symbol in this scope.

        Returns the existing symbol if already defined (duplicate), else None.
        """
        if name in self.symbols:
            return self.symbols[name]
        self.symbols[name] = symbol
        return None

    def resolve(self, name: str) -> Symbol | None:
        """Resolve a name in this scope, searching upward.

        Returns the first matching symbol found, or None if not found.
        """
        if name in self.symbols:
            return self.symbols[name]
        if self.parent is not None:
            return self.parent.resolve(name)
        return None

    def resolve_local(self, name: str) -> Symbol | None:
        """Resolve a name only in this scope (no upward search)."""
        return self.symbols.get(name)


@dataclass
class SymbolTable:
    """Hierarchical symbol table supporting nested scopes.

    Manages a stack of scopes starting with a global scope. Provides
    methods to enter/exit scopes and define/resolve symbols.

    Attributes:
        global_scope: The root scope shared by all code.
        current_scope: The innermost active scope.
    """

    global_scope: Scope = field(default=None)  # type: ignore
    current_scope: Scope = field(default=None)  # type: ignore

    def __post_init__(self) -> None:
        if self.global_scope is None:
            object.__setattr__(self, "global_scope", Scope(parent=None, name="global", scope_type="global"))
        if self.current_scope is None:
            object.__setattr__(self, "current_scope", self.global_scope)

    def enter_scope(self, name: str, scope_type: str = "block") -> Scope:
        """Push a new nested scope.

        Args:
            name: Descriptive name for the scope.
            scope_type: One of 'global', 'agent', 'function', 'block'.

        Returns:
            The newly created scope.
        """
        new_scope = Scope(parent=self.current_scope, name=name, scope_type=scope_type)
        object.__setattr__(self, "current_scope", new_scope)
        return new_scope

    def exit_scope(self) -> Scope | None:
        """Pop the current scope and return to the parent.

        Returns:
            The parent scope, or None if already at global scope.
        """
        parent = self.current_scope.parent
        if parent is not None:
            object.__setattr__(self, "current_scope", parent)
        return parent

    def define(self, name: str, symbol: Symbol) -> Symbol | None:
        """Define a symbol in the current scope.

        Returns the existing symbol if already defined (duplicate), else None.
        """
        return self.current_scope.define(name, symbol)

    def resolve(self, name: str) -> Symbol | None:
        """Resolve a name by searching the scope chain upward."""
        return self.current_scope.resolve(name)

    def resolve_local(self, name: str) -> Symbol | None:
        """Resolve a name only in the current scope."""
        return self.current_scope.resolve_local(name)

    @property
    def depth(self) -> int:
        """Return the current scope nesting depth (global = 0)."""
        d = 0
        scope = self.current_scope
        while scope is not None and scope.parent is not None:
            d += 1
            scope = scope.parent
        return d

    @property
    def in_global_scope(self) -> bool:
        """Check if we are currently at the global scope level."""
        return self.current_scope is self.global_scope

    @property
    def current_scope_type(self) -> str:
        """Return the type of the current scope."""
        return self.current_scope.scope_type
