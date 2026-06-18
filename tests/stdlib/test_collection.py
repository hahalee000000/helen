"""Tests for Collection stdlib module.

Tests list, dict, and set operations.
"""

import pytest
from helen.stdlib.collection import (
    # List ops
    _map, _filter, _reduce, _find, _every, _some,
    _sort, _reverse, _unique, _flatten, _chunk, _zip,
    # Dict ops
    _keys, _values, _entries, _merge, _pick, _omit,
    # Set ops
    _make_set, _set_union, _set_intersection, _set_difference, _set_has,
)


# ── List Operations Tests ──────────────────────────────────────


class TestMap:
    """Tests for map."""

    def test_basic(self):
        result = _map([1, 2, 3], lambda x: x * 2)
        assert result == [2, 4, 6]

    def test_transform(self):
        result = _map(["a", "b", "c"], str.upper)
        assert result == ["A", "B", "C"]

    def test_empty(self):
        result = _map([], lambda x: x)
        assert result == []


class TestFilter:
    """Tests for filter."""

    def test_basic(self):
        result = _filter([1, 2, 3, 4, 5], lambda x: x > 2)
        assert result == [3, 4, 5]

    def test_even(self):
        result = _filter([1, 2, 3, 4], lambda x: x % 2 == 0)
        assert result == [2, 4]

    def test_empty(self):
        result = _filter([], lambda x: True)
        assert result == []


class TestReduce:
    """Tests for reduce."""

    def test_sum(self):
        result = _reduce([1, 2, 3, 4], lambda acc, x: acc + x, 0)
        assert result == 10

    def test_product(self):
        result = _reduce([1, 2, 3, 4], lambda acc, x: acc * x, 1)
        assert result == 24

    def test_no_initial(self):
        result = _reduce([1, 2, 3], lambda acc, x: acc + x)
        assert result == 6

    def test_empty_with_initial(self):
        result = _reduce([], lambda acc, x: acc + x, 0)
        assert result == 0


class TestFind:
    """Tests for find."""

    def test_found(self):
        result = _find([1, 2, 3, 4], lambda x: x > 2)
        assert result == 3

    def test_not_found(self):
        result = _find([1, 2, 3], lambda x: x > 10)
        assert result is None

    def test_first_match(self):
        result = _find([1, 2, 3, 4], lambda x: x % 2 == 0)
        assert result == 2


class TestEvery:
    """Tests for every."""

    def test_all_true(self):
        result = _every([2, 4, 6], lambda x: x % 2 == 0)
        assert result is True

    def test_some_false(self):
        result = _every([2, 3, 4], lambda x: x % 2 == 0)
        assert result is False

    def test_empty(self):
        result = _every([], lambda x: False)
        assert result is True


class TestSome:
    """Tests for some."""

    def test_some_true(self):
        result = _some([1, 2, 3], lambda x: x > 2)
        assert result is True

    def test_none_true(self):
        result = _some([1, 2, 3], lambda x: x > 10)
        assert result is False

    def test_empty(self):
        result = _some([], lambda x: True)
        assert result is False


class TestSort:
    """Tests for sort."""

    def test_basic(self):
        result = _sort([3, 1, 4, 1, 5])
        assert result == [1, 1, 3, 4, 5]

    def test_reverse(self):
        result = _sort([3, 1, 4], lambda a, b: b - a)
        assert result == [4, 3, 1]

    def test_strings(self):
        result = _sort(["banana", "apple", "cherry"])
        assert result == ["apple", "banana", "cherry"]


class TestReverse:
    """Tests for reverse."""

    def test_basic(self):
        result = _reverse([1, 2, 3])
        assert result == [3, 2, 1]

    def test_empty(self):
        result = _reverse([])
        assert result == []


class TestUnique:
    """Tests for unique."""

    def test_basic(self):
        result = _unique([1, 2, 2, 3, 3, 3])
        assert sorted(result) == [1, 2, 3]

    def test_strings(self):
        result = _unique(["a", "b", "a", "c"])
        assert sorted(result) == ["a", "b", "c"]


class TestFlatten:
    """Tests for flatten."""

    def test_basic(self):
        result = _flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_nested(self):
        result = _flatten([[1, [2, 3]], [4]])
        assert result == [1, 2, 3, 4]

    def test_already_flat(self):
        result = _flatten([1, 2, 3])
        assert result == [1, 2, 3]


class TestChunk:
    """Tests for chunk."""

    def test_basic(self):
        result = _chunk([1, 2, 3, 4, 5], 2)
        assert result == [[1, 2], [3, 4], [5]]

    def test_exact_division(self):
        result = _chunk([1, 2, 3, 4], 2)
        assert result == [[1, 2], [3, 4]]

    def test_larger_chunk(self):
        result = _chunk([1, 2, 3], 5)
        assert result == [[1, 2, 3]]


class TestZip:
    """Tests for zip."""

    def test_basic(self):
        result = _zip([1, 2, 3], ["a", "b", "c"])
        assert result == [(1, "a"), (2, "b"), (3, "c")]

    def test_different_lengths(self):
        result = _zip([1, 2], ["a", "b", "c"])
        assert result == [(1, "a"), (2, "b")]

    def test_single_list(self):
        result = _zip([1, 2, 3])
        assert result == [(1,), (2,), (3,)]


# ── Dict Operations Tests ──────────────────────────────────────


class TestKeys:
    """Tests for keys."""

    def test_basic(self):
        result = _keys({"a": 1, "b": 2})
        assert sorted(result) == ["a", "b"]

    def test_empty(self):
        result = _keys({})
        assert result == []


class TestValues:
    """Tests for values."""

    def test_basic(self):
        result = _values({"a": 1, "b": 2})
        assert sorted(result) == [1, 2]


class TestEntries:
    """Tests for entries."""

    def test_basic(self):
        result = _entries({"a": 1, "b": 2})
        assert sorted(result) == [("a", 1), ("b", 2)]


class TestMerge:
    """Tests for merge."""

    def test_basic(self):
        result = _merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_override(self):
        result = _merge({"a": 1}, {"a": 2})
        assert result == {"a": 2}

    def test_multiple(self):
        result = _merge({"a": 1}, {"b": 2}, {"c": 3})
        assert result == {"a": 1, "b": 2, "c": 3}


class TestPick:
    """Tests for pick."""

    def test_basic(self):
        result = _pick({"a": 1, "b": 2, "c": 3}, ["a", "c"])
        assert result == {"a": 1, "c": 3}

    def test_missing_key(self):
        result = _pick({"a": 1, "b": 2}, ["a", "x"])
        assert result == {"a": 1}


class TestOmit:
    """Tests for omit."""

    def test_basic(self):
        result = _omit({"a": 1, "b": 2, "c": 3}, ["b"])
        assert result == {"a": 1, "c": 3}

    def test_missing_key(self):
        result = _omit({"a": 1, "b": 2}, ["x"])
        assert result == {"a": 1, "b": 2}


# ── Set Operations Tests ───────────────────────────────────────


class TestMakeSet:
    """Tests for make_set."""

    def test_basic(self):
        result = _make_set([1, 2, 2, 3])
        assert result == {1, 2, 3}


class TestSetUnion:
    """Tests for set_union."""

    def test_basic(self):
        result = _set_union({1, 2}, {2, 3})
        assert result == {1, 2, 3}


class TestSetIntersection:
    """Tests for set_intersection."""

    def test_basic(self):
        result = _set_intersection({1, 2, 3}, {2, 3, 4})
        assert result == {2, 3}


class TestSetDifference:
    """Tests for set_difference."""

    def test_basic(self):
        result = _set_difference({1, 2, 3}, {2, 3, 4})
        assert result == {1}


class TestSetHas:
    """Tests for set_has."""

    def test_has(self):
        assert _set_has({1, 2, 3}, 2) is True

    def test_not_has(self):
        assert _set_has({1, 2, 3}, 5) is False
