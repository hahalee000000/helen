"""Runtime environment for the Hellen interpreter.

Provides a chain of scopes for variable storage, supporting nested
block scoping and const protection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Environment:
    """A single scope in the environment chain.

    Each Environment holds its own symbol table and a reference to a
    parent scope. Variable lookup walks up the chain (LEGB-like).
    Variable definition always targets the innermost scope.

    Attributes:
        parent: The enclosing environment (None for global).
        _store: Key-value store for this scope.
        _consts: Set of variable names that are immutable.
    """

    parent: "Environment | None" = None
    _store: dict[str, Any] = field(default_factory=dict, repr=False)
    _consts: set[str] = field(default_factory=set, repr=False)

    def define(self, name: str, value: Any, is_const: bool = False) -> None:
        """Define a variable in the current scope.

        Args:
            name: Variable name.
            value: The value to bind.
            is_const: If True, the variable cannot be reassigned.
        """
        self._store[name] = value
        if is_const:
            self._consts.add(name)

    def lookup(self, name: str) -> Any:
        """Look up a variable by name, searching up the scope chain.

        Args:
            name: Variable name to resolve.

        Returns:
            The bound value.

        Raises:
            NameError: If the variable is not found in any scope.
        """
        if name in self._store:
            return self._store[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise NameError(f"Undefined variable '{name}'")

    def assign(self, name: str, value: Any) -> None:
        """Assign a new value to an existing variable.

        Walks up the scope chain to find the variable, then updates it
        in the scope where it was originally defined.

        Args:
            name: Variable name to update.
            value: New value to bind.

        Raises:
            NameError: If the variable is not found.
            ConstAssignmentError: If the variable is const.
        """
        if name in self._store:
            if name in self._consts:
                from hellen.interpreter.exceptions import ConstAssignmentError

                raise ConstAssignmentError(name)
            self._store[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise NameError(f"Undefined variable '{name}'")

    def is_const(self, name: str) -> bool:
        """Check if a variable is marked const in its defining scope.

        Args:
            name: Variable name.

        Returns:
            True if the variable exists and is const.
        """
        if name in self._store:
            return name in self._consts
        if self.parent is not None:
            return self.parent.is_const(name)
        return False

    def enter_scope(self) -> "Environment":
        """Create and return a new nested child scope.

        Returns:
            The new child Environment.
        """
        child = Environment(parent=self)
        return child

    def exit_scope(self) -> "Environment | None":
        """Return the parent scope.

        Returns:
            The parent environment, or None if this is the global scope.
        """
        return self.parent

    def __contains__(self, name: str) -> bool:
        """Check if a variable is defined in this scope chain."""
        if name in self._store:
            return True
        if self.parent is not None:
            return name in self.parent
        return False

    def __repr__(self) -> str:
        return f"Environment(vars={list(self._store.keys())}, consts={list(self._consts)})"
