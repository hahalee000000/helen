"""Collection module contracts for Helen stdlib.

Defines interfaces for list, dict, and set operations.
"""

from typing import Any, Callable


class ListOpsContract:
    """Contract for list operations."""

    @staticmethod
    def map(lst: list[Any], fn: Callable[[Any], Any]) -> list[Any]:
        """Apply function to each element.

        Args:
            lst: Input list
            fn: Function to apply

        Returns:
            New list with transformed elements
        """
        ...

    @staticmethod
    def filter(lst: list[Any], fn: Callable[[Any], bool]) -> list[Any]:
        """Filter elements by predicate.

        Args:
            lst: Input list
            fn: Predicate function

        Returns:
            New list with elements that satisfy predicate
        """
        ...

    @staticmethod
    def reduce(lst: list[Any], fn: Callable[[Any, Any], Any], initial: Any = None) -> Any:
        """Reduce list to single value.

        Args:
            lst: Input list
            fn: Reducer function (accumulator, element) -> new_accumulator
            initial: Initial accumulator value

        Returns:
            Reduced value
        """
        ...

    @staticmethod
    def find(lst: list[Any], fn: Callable[[Any], bool]) -> Any | None:
        """Find first element satisfying predicate.

        Args:
            lst: Input list
            fn: Predicate function

        Returns:
            First matching element or None
        """
        ...

    @staticmethod
    def every(lst: list[Any], fn: Callable[[Any], bool]) -> bool:
        """Check if all elements satisfy predicate.

        Args:
            lst: Input list
            fn: Predicate function

        Returns:
            True if all elements satisfy predicate
        """
        ...

    @staticmethod
    def some(lst: list[Any], fn: Callable[[Any], bool]) -> bool:
        """Check if any element satisfies predicate.

        Args:
            lst: Input list
            fn: Predicate function

        Returns:
            True if at least one element satisfies predicate
        """
        ...

    @staticmethod
    def sort(lst: list[Any], compare: Callable[[Any, Any], int] | None = None) -> list[Any]:
        """Sort list.

        Args:
            lst: Input list
            compare: Optional comparison function

        Returns:
            New sorted list
        """
        ...

    @staticmethod
    def reverse(lst: list[Any]) -> list[Any]:
        """Reverse list.

        Args:
            lst: Input list

        Returns:
            New reversed list
        """
        ...

    @staticmethod
    def unique(lst: list[Any]) -> list[Any]:
        """Remove duplicates.

        Args:
            lst: Input list

        Returns:
            New list with unique elements
        """
        ...

    @staticmethod
    def flatten(lst: list[Any]) -> list[Any]:
        """Flatten nested lists.

        Args:
            lst: Input list (may contain nested lists)

        Returns:
            Flattened list
        """
        ...

    @staticmethod
    def chunk(lst: list[Any], size: int) -> list[list[Any]]:
        """Split list into chunks.

        Args:
            lst: Input list
            size: Chunk size

        Returns:
            List of chunks
        """
        ...

    @staticmethod
    def zip(*lists: list[Any]) -> list[tuple[Any, ...]]:
        """Zip multiple lists.

        Args:
            *lists: Lists to zip

        Returns:
            List of tuples
        """
        ...


class DictOpsContract:
    """Contract for dict operations."""

    @staticmethod
    def keys(d: dict[Any, Any]) -> list[Any]:
        """Get all keys.

        Args:
            d: Input dict

        Returns:
            List of keys
        """
        ...

    @staticmethod
    def values(d: dict[Any, Any]) -> list[Any]:
        """Get all values.

        Args:
            d: Input dict

        Returns:
            List of values
        """
        ...

    @staticmethod
    def entries(d: dict[Any, Any]) -> list[tuple[Any, Any]]:
        """Get all key-value pairs.

        Args:
            d: Input dict

        Returns:
            List of (key, value) tuples
        """
        ...

    @staticmethod
    def merge(*dicts: dict[Any, Any]) -> dict[Any, Any]:
        """Merge multiple dicts.

        Args:
            *dicts: Dicts to merge

        Returns:
            Merged dict (later dicts override earlier ones)
        """
        ...

    @staticmethod
    def pick(d: dict[Any, Any], keys: list[Any]) -> dict[Any, Any]:
        """Select specific keys.

        Args:
            d: Input dict
            keys: Keys to keep

        Returns:
            New dict with only specified keys
        """
        ...

    @staticmethod
    def omit(d: dict[Any, Any], keys: list[Any]) -> dict[Any, Any]:
        """Exclude specific keys.

        Args:
            d: Input dict
            keys: Keys to exclude

        Returns:
            New dict without specified keys
        """
        ...


class SetOpsContract:
    """Contract for set operations."""

    @staticmethod
    def make_set(items: list[Any]) -> Any:  # Returns Python set
        """Create set from list.

        Args:
            items: Input list

        Returns:
            Set
        """
        ...

    @staticmethod
    def set_union(s1: Any, s2: Any) -> Any:
        """Union of two sets.

        Args:
            s1: First set
            s2: Second set

        Returns:
            Union set
        """
        ...

    @staticmethod
    def set_intersection(s1: Any, s2: Any) -> Any:
        """Intersection of two sets.

        Args:
            s1: First set
            s2: Second set

        Returns:
            Intersection set
        """
        ...

    @staticmethod
    def set_difference(s1: Any, s2: Any) -> Any:
        """Difference of two sets (s1 - s2).

        Args:
            s1: First set
            s2: Second set

        Returns:
            Difference set
        """
        ...

    @staticmethod
    def set_has(s: Any, item: Any) -> bool:
        """Check if set contains item.

        Args:
            s: Input set
            item: Item to check

        Returns:
            True if item is in set
        """
        ...
