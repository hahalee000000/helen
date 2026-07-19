"""SharedStore and SharedStoreMethod: thread-safe shared mutable state.

Extracted from interpreter.py to improve code organization.
"""

from __future__ import annotations

import threading

from helen.interpreter.exceptions import ReturnSentinel


class SharedStore:
    """Shared store instance for controlled shared mutable state.

    v1.12: Provides a structured way to share mutable state across agents.
    Fields are private, methods provide the public interface.

    Thread safety: All field access is protected by a reentrant lock (RLock).
    This allows concurrent agents to safely read/write shared state.

    Security: Internal attributes (_name, _fields, _methods, _lock) cannot be
    accessed or modified from Helen code — __getattr__/__setattr__ block
    underscore-prefixed names.

    Example:
        shared store Counter {
            count: int = 0
            fn increment() { count += 1 }
            fn get(): int { return count }
        }
    """
    # Internal attribute names — set in __init__ via object.__setattr__
    _INTERNAL_ATTRS = frozenset({'_name', '_fields', '_methods', '_lock'})

    def __init__(self, name: str, fields: dict[str, object], methods: dict[str, object]):
        """Initialize a shared store.

        Args:
            name: The store's name.
            fields: Initial field values (private state).
            methods: Method implementations (callable closures).
        """
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_fields', dict(fields))  # defensive copy
        object.__setattr__(self, '_methods', dict(methods))  # defensive copy
        object.__setattr__(self, '_lock', threading.RLock())

    def __getattr__(self, name: str) -> object:
        """Access a field or method by name. Private attrs (_prefix) are blocked."""
        if name.startswith('_'):
            raise AttributeError(f"Cannot access private attribute '{name}'")
        fields = object.__getattribute__(self, '_fields')
        methods = object.__getattribute__(self, '_methods')
        store_name = object.__getattribute__(self, '_name')
        if name in methods:
            return methods[name]
        if name in fields:
            return fields[name]
        raise AttributeError(f"Shared store '{store_name}' has no field or method '{name}'")

    def __setattr__(self, name: str, value: object) -> None:
        """Set a field value. Only public fields can be modified, not methods or internals."""
        # Block ALL underscore-prefixed names — including after __init__
        if name.startswith('_'):
            store_name = object.__getattribute__(self, '_name')
            raise AttributeError(
                f"Cannot set private attribute '{name}' on shared store '{store_name}'. "
                f"Internal attributes are not accessible from Helen code."
            )
        methods = object.__getattribute__(self, '_methods')
        fields = object.__getattribute__(self, '_fields')
        store_name = object.__getattribute__(self, '_name')
        if name in methods:
            raise AttributeError(f"Cannot overwrite method '{name}' in shared store '{store_name}'")
        if name in fields:
            lock = object.__getattribute__(self, '_lock')
            with lock:
                fields[name] = value
            return
        raise AttributeError(f"Shared store '{store_name}' has no field '{name}'")

    def __repr__(self) -> str:
        name = object.__getattribute__(self, '_name')
        fields = object.__getattribute__(self, '_fields')
        methods = object.__getattribute__(self, '_methods')
        return f"<SharedStore {name} with {len(fields)} fields, {len(methods)} methods>"

    def get_field(self, name: str) -> object:
        """Get a field value (thread-safe)."""
        fields = object.__getattribute__(self, '_fields')
        store_name = object.__getattribute__(self, '_name')
        if name not in fields:
            raise AttributeError(f"Shared store '{store_name}' has no field '{name}'")
        lock = object.__getattribute__(self, '_lock')
        with lock:
            return fields[name]

    def set_field(self, name: str, value: object) -> None:
        """Set a field value (thread-safe)."""
        fields = object.__getattribute__(self, '_fields')
        store_name = object.__getattribute__(self, '_name')
        if name not in fields:
            raise AttributeError(f"Shared store '{store_name}' has no field '{name}'")
        lock = object.__getattribute__(self, '_lock')
        with lock:
            fields[name] = value

    def __deepcopy__(self, memo: dict) -> "SharedStore":
        """Deep copy creates an independent SharedStore with copied fields.

        Methods are NOT copied — they reference closures bound to the original
        interpreter environment. The copy has empty methods and shares no state
        with the original (except through explicitly passed references).

        The lock is recreated (locks cannot be pickled/deep-copied).
        """
        import copy
        name = object.__getattribute__(self, '_name')
        fields = object.__getattribute__(self, '_fields')
        new_fields = copy.deepcopy(fields, memo)
        new_store = SharedStore(name, new_fields, {})
        memo[id(self)] = new_store
        return new_store


class SharedStoreMethod:
    """A callable wrapper for a shared store method.

    When accessed via store.method, returns this callable.
    When called, executes the method with access to the store's fields.

    v1.12 fix: Method execution is serialized via the store's lock to prevent
    concurrent field corruption.
    """
    def __init__(self, method_node, store: SharedStore, interpreter):
        object.__setattr__(self, '_method_node', method_node)
        object.__setattr__(self, '_store', store)
        object.__setattr__(self, '_interpreter', interpreter)

    def __call__(self, *args):
        """Call the method with the given arguments (serialized via store lock)."""
        interp = self._interpreter
        m_node = object.__getattribute__(self, '_method_node')
        store_inst = object.__getattribute__(self, '_store')
        lock = object.__getattribute__(store_inst, '_lock')
        fields = object.__getattribute__(store_inst, '_fields')

        # Serialize method execution to prevent concurrent field corruption
        with lock:
            # Create execution environment with store fields as variables
            old_env = interp.environment
            method_env = old_env.enter_scope()
            # Bind store fields as local variables
            for fname, fvalue in fields.items():
                method_env.define(fname, fvalue)
            # Bind method parameters
            for i, param in enumerate(m_node.params):
                if i < len(args):
                    method_env.define(param.name, args[i])
            interp.environment = method_env
            try:
                result = interp._execute_stmts(m_node.body.body)
                # Write back any field modifications
                for fname in fields:
                    try:
                        fields[fname] = method_env.lookup(fname)
                    except NameError:
                        pass
                if isinstance(result, ReturnSentinel):
                    return result.value
                return result
            finally:
                interp.environment = old_env


def _is_mutable_type(value: object) -> bool:
    """Check if a value is a mutable reference type."""
    return isinstance(value, (list, dict))
