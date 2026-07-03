"""Collection module for Helen stdlib.

Provides list, dict, and set operations.
"""

from __future__ import annotations

from functools import reduce as _reduce_builtin
from typing import Any, Callable


# ── List operations ────────────────────────────────────────────


def _map(lst: list[Any], fn: Callable[[Any], Any]) -> list[Any]:
    """Apply function to each element.

    Args:
        lst: Input list
        fn: Function to apply

    Returns:
        New list with transformed elements
    """
    from helen.interpreter.exceptions import HelenRuntimeError, RuntimeError as HelenRuntimeErrorClass, RuntimeError as HelenRuntimeErrorClass

    result = []
    for i, item in enumerate(lst):
        try:
            result.append(fn(item))
        except Exception as e:
            # 提供更详细的错误上下文
            error_msg = f"map operation failed at index {i}"
            if hasattr(e, 'message'):
                error_msg += f": {e.message}"
            else:
                error_msg += f": {str(e)}"

            # 尝试获取元素的字符串表示（避免过长的输出）
            item_repr = repr(item)
            if len(item_repr) > 100:
                item_repr = item_repr[:100] + "...(truncated)"
            error_msg += f" (element: {item_repr})"

            # 如果是HelenRuntimeError，保留span信息；否则创建新的RuntimeError
            if isinstance(e, HelenRuntimeError):
                raise HelenRuntimeErrorClass(error_msg, e.span)
            else:
                # 使用Helen的RuntimeError而不是Python的RuntimeError
                raise HelenRuntimeErrorClass(error_msg)
    return result


def _filter(lst: list[Any], fn: Callable[[Any], bool]) -> list[Any]:
    """Filter elements by predicate.

    Args:
        lst: Input list
        fn: Predicate function

    Returns:
        New list with elements that satisfy predicate
    """
    from helen.interpreter.exceptions import HelenRuntimeError, RuntimeError as HelenRuntimeErrorClass

    result = []
    for i, item in enumerate(lst):
        try:
            if fn(item):
                result.append(item)
        except Exception as e:
            error_msg = f"filter operation failed at index {i}"
            if hasattr(e, 'message'):
                error_msg += f": {e.message}"
            else:
                error_msg += f": {str(e)}"

            item_repr = repr(item)
            if len(item_repr) > 100:
                item_repr = item_repr[:100] + "...(truncated)"
            error_msg += f" (element: {item_repr})"

            if isinstance(e, HelenRuntimeError):
                raise HelenRuntimeErrorClass(error_msg, e.span)
            else:
                raise HelenRuntimeErrorClass(error_msg)
    return result


def _reduce(lst: list[Any], fn: Callable[[Any, Any], Any], initial: Any = None) -> Any:
    """Reduce list to single value.

    Args:
        lst: Input list
        fn: Reducer function (accumulator, element) -> new_accumulator
        initial: Initial accumulator value

    Returns:
        Reduced value
    """
    from helen.interpreter.exceptions import HelenRuntimeError, RuntimeError as HelenRuntimeErrorClass

    try:
        if initial is None:
            return _reduce_builtin(fn, lst)
        return _reduce_builtin(fn, lst, initial)
    except Exception as e:
        error_msg = f"reduce operation failed"
        if hasattr(e, 'message'):
            error_msg += f": {e.message}"
        else:
            error_msg += f": {str(e)}"

        if isinstance(e, HelenRuntimeError):
            raise HelenRuntimeErrorClass(error_msg, e.span)
        else:
            raise HelenRuntimeErrorClass(error_msg)


def _find(lst: list[Any], fn: Callable[[Any], bool]) -> Any | None:
    """Find first element satisfying predicate.

    Args:
        lst: Input list
        fn: Predicate function

    Returns:
        First matching element or None
    """
    from helen.interpreter.exceptions import HelenRuntimeError, RuntimeError as HelenRuntimeErrorClass

    for i, item in enumerate(lst):
        try:
            if fn(item):
                return item
        except Exception as e:
            error_msg = f"find operation failed at index {i}"
            if hasattr(e, 'message'):
                error_msg += f": {e.message}"
            else:
                error_msg += f": {str(e)}"

            item_repr = repr(item)
            if len(item_repr) > 100:
                item_repr = item_repr[:100] + "...(truncated)"
            error_msg += f" (element: {item_repr})"

            if isinstance(e, HelenRuntimeError):
                raise HelenRuntimeErrorClass(error_msg, e.span)
            else:
                raise HelenRuntimeErrorClass(error_msg)
    return None


def _every(lst: list[Any], fn: Callable[[Any], bool]) -> bool:
    """Check if all elements satisfy predicate.

    Args:
        lst: Input list
        fn: Predicate function

    Returns:
        True if all elements satisfy predicate
    """
    from helen.interpreter.exceptions import HelenRuntimeError, RuntimeError as HelenRuntimeErrorClass

    for i, item in enumerate(lst):
        try:
            if not fn(item):
                return False
        except Exception as e:
            error_msg = f"every operation failed at index {i}"
            if hasattr(e, 'message'):
                error_msg += f": {e.message}"
            else:
                error_msg += f": {str(e)}"

            item_repr = repr(item)
            if len(item_repr) > 100:
                item_repr = item_repr[:100] + "...(truncated)"
            error_msg += f" (element: {item_repr})"

            if isinstance(e, HelenRuntimeError):
                raise HelenRuntimeErrorClass(error_msg, e.span)
            else:
                raise HelenRuntimeErrorClass(error_msg)
    return True


def _some(lst: list[Any], fn: Callable[[Any], bool]) -> bool:
    """Check if any element satisfies predicate.

    Args:
        lst: Input list
        fn: Predicate function

    Returns:
        True if at least one element satisfies predicate
    """
    from helen.interpreter.exceptions import HelenRuntimeError, RuntimeError as HelenRuntimeErrorClass

    for i, item in enumerate(lst):
        try:
            if fn(item):
                return True
        except Exception as e:
            error_msg = f"some operation failed at index {i}"
            if hasattr(e, 'message'):
                error_msg += f": {e.message}"
            else:
                error_msg += f": {str(e)}"

            item_repr = repr(item)
            if len(item_repr) > 100:
                item_repr = item_repr[:100] + "...(truncated)"
            error_msg += f" (element: {item_repr})"

            if isinstance(e, HelenRuntimeError):
                raise HelenRuntimeErrorClass(error_msg, e.span)
            else:
                raise HelenRuntimeErrorClass(error_msg)
    return False


def _sort(lst: list[Any], compare: Callable[[Any, Any], int] | None = None) -> list[Any]:
    """Sort list.

    Args:
        lst: Input list
        compare: Optional comparison function

    Returns:
        New sorted list
    """
    if compare is None:
        return sorted(lst)

    from functools import cmp_to_key
    return sorted(lst, key=cmp_to_key(compare))


def _reverse(lst: list[Any]) -> list[Any]:
    """Reverse list.

    Args:
        lst: Input list

    Returns:
        New reversed list
    """
    return lst[::-1]


def _unique(lst: list[Any]) -> list[Any]:
    """Remove duplicates while preserving order.

    Args:
        lst: Input list

    Returns:
        New list with unique elements
    """
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _flatten(lst: list[Any]) -> list[Any]:
    """Flatten nested lists recursively.

    Args:
        lst: Input list (may contain nested lists)

    Returns:
        Flattened list
    """
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(_flatten(item))
        else:
            result.append(item)
    return result


def _chunk(lst: list[Any], size: int) -> list[list[Any]]:
    """Split list into chunks.

    Args:
        lst: Input list
        size: Chunk size

    Returns:
        List of chunks
    """
    if size <= 0:
        raise ValueError("Chunk size must be positive")

    return [lst[i:i + size] for i in range(0, len(lst), size)]


def _zip(*lists: list[Any]) -> list[tuple[Any, ...]]:
    """Zip multiple lists.

    Args:
        *lists: Lists to zip

    Returns:
        List of tuples
    """
    if not lists:
        return []
    return list(zip(*lists))


# ── Dict operations ────────────────────────────────────────────


def _keys(d: dict[Any, Any]) -> list[Any]:
    """Get all keys.

    Args:
        d: Input dict

    Returns:
        List of keys
    """
    return list(d.keys())


def _values(d: dict[Any, Any]) -> list[Any]:
    """Get all values.

    Args:
        d: Input dict

    Returns:
        List of values
    """
    return list(d.values())


def _entries(d: dict[Any, Any]) -> list[tuple[Any, Any]]:
    """Get all key-value pairs.

    Args:
        d: Input dict

    Returns:
        List of (key, value) tuples
    """
    return list(d.items())


def _merge(*dicts: dict[Any, Any]) -> dict[Any, Any]:
    """Merge multiple dicts.

    Args:
        *dicts: Dicts to merge

    Returns:
        Merged dict (later dicts override earlier ones)
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def _pick(d: dict[Any, Any], keys: list[Any]) -> dict[Any, Any]:
    """Select specific keys.

    Args:
        d: Input dict
        keys: Keys to keep

    Returns:
        New dict with only specified keys
    """
    return {k: v for k, v in d.items() if k in keys}


def _omit(d: dict[Any, Any], keys: list[Any]) -> dict[Any, Any]:
    """Exclude specific keys.

    Args:
        d: Input dict
        keys: Keys to exclude

    Returns:
        New dict without specified keys
    """
    return {k: v for k, v in d.items() if k not in keys}


# ── Set operations ─────────────────────────────────────────────


def _make_set(items: list[Any]) -> set[Any]:
    """Create set from list.

    Args:
        items: Input list

    Returns:
        Set
    """
    return set(items)


def _set_union(s1: set[Any], s2: set[Any]) -> set[Any]:
    """Union of two sets.

    Args:
        s1: First set
        s2: Second set

    Returns:
        Union set
    """
    return s1 | s2


def _set_intersection(s1: set[Any], s2: set[Any]) -> set[Any]:
    """Intersection of two sets.

    Args:
        s1: First set
        s2: Second set

    Returns:
        Intersection set
    """
    return s1 & s2


def _set_difference(s1: set[Any], s2: set[Any]) -> set[Any]:
    """Difference of two sets (s1 - s2).

    Args:
        s1: First set
        s2: Second set

    Returns:
        Difference set
    """
    return s1 - s2


def _set_has(s: set[Any], item: Any) -> bool:
    """Check if set contains item.

    Args:
        s: Input set
        item: Item to check

    Returns:
        True if item is in set
    """
    return item in s
