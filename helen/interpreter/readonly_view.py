"""ReadOnlyView: immutable wrapper for mutable types passed to agents.

Extracted from interpreter.py to improve code organization.
"""

from __future__ import annotations


class ReadOnlyView:
    """Read-only wrapper for mutable types (list, dict) passed to agents.

    v1.12: Agent isolation improvement. When a reference type (list, dict)
    is passed as a parameter to an agent, it is wrapped in a ReadOnlyView
    to prevent the agent from modifying the caller's data.

    The wrapper supports read operations (iteration, indexing, len) but
    raises ScopeViolationError on mutation attempts.

    Security notes:
    - __iter__ wraps each yielded item in ReadOnlyView to prevent escape
      through iteration (e.g. `for item in param { item.append(1) }`)
    - unwrap is renamed to _unwrap and is inaccessible from Helen code
      (__getattr__ blocks _-prefixed names)
    """
    def __init__(self, data):
        object.__setattr__(self, '_data', data)

    def __getitem__(self, key):
        value = self._data[key]
        # Wrap nested mutable types (list, dict) as well
        # Also wrap tuples that may contain mutable items
        if isinstance(value, (list, dict)):
            return ReadOnlyView(value)
        if isinstance(value, tuple) and any(isinstance(v, (list, dict)) for v in value):
            return ReadOnlyView(value)
        return value

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        """Iterate with each item wrapped in ReadOnlyView if mutable."""
        for item in self._data:
            if isinstance(item, (list, dict)):
                yield ReadOnlyView(item)
            elif isinstance(item, tuple) and any(isinstance(v, (list, dict)) for v in item):
                yield ReadOnlyView(item)
            else:
                yield item

    def __contains__(self, item):
        return item in self._data

    def __bool__(self):
        return bool(self._data)

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        return f"ReadOnly({self._data!r})"

    def __eq__(self, other):
        if isinstance(other, ReadOnlyView):
            return self._data == other._data
        return self._data == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        return self._data < other_data

    def __le__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        return self._data <= other_data

    def __gt__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        return self._data > other_data

    def __ge__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        return self._data >= other_data

    def __add__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        result = self._data + other_data
        if isinstance(result, (list, dict)):
            return ReadOnlyView(result)
        return result

    def __radd__(self, other):
        """Support [1, 2] + ReadOnlyView([3, 4])."""
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        result = other_data + self._data
        if isinstance(result, (list, dict)):
            return ReadOnlyView(result)
        return result

    def __hash__(self):
        return hash(self._data) if not isinstance(self._data, (list, dict)) else id(self)

    def keys(self):
        """Dict-like keys() method."""
        if hasattr(self._data, 'keys'):
            return self._data.keys()
        raise AttributeError("ReadOnly list has no keys() method")

    def values(self):
        """Dict-like values() method — returns ReadOnlyView for mutable values."""
        if hasattr(self._data, 'values'):
            return [ReadOnlyView(v) if isinstance(v, (list, dict)) else v
                    for v in self._data.values()]
        raise AttributeError("ReadOnly list has no values() method")

    def items(self):
        """Dict-like items() method — values wrapped in ReadOnlyView if mutable."""
        if hasattr(self._data, 'items'):
            result = []
            for k, v in self._data.items():
                if isinstance(v, (list, dict)):
                    result.append((k, ReadOnlyView(v)))
                else:
                    result.append((k, v))
            return result
        raise AttributeError("ReadOnly list has no items() method")

    def get(self, key, default=None):
        """Dict-like get() method."""
        if hasattr(self._data, 'get'):
            value = self._data.get(key, default)
            if isinstance(value, (list, dict)):
                return ReadOnlyView(value)
            return value
        raise AttributeError("ReadOnly list has no get() method")

    def _mutate_error(self, *args, **kwargs):
        """Raise error for any mutation attempt."""
        from helen.interpreter.exceptions import ScopeViolationError
        raise ScopeViolationError(
            "cannot modify read-only parameter in agent scope. "
            "Parameters are passed as read-only views to prevent "
            "accidental modification of caller's data. "
            "Create a local copy with `let copy = list(param)` if you need to modify."
        )

    # Block all mutation methods
    __setitem__ = _mutate_error
    __delitem__ = _mutate_error
    append = _mutate_error
    extend = _mutate_error
    insert = _mutate_error
    remove = _mutate_error
    pop = _mutate_error
    clear = _mutate_error
    sort = _mutate_error
    reverse = _mutate_error
    update = _mutate_error
    setdefault = _mutate_error
    popitem = _mutate_error
