"""Tests for new dict functions added in v1.33."""

import pytest


class TestRemoveKey:
    """Test remove_key function."""

    def test_remove_existing_key(self):
        """Test removing an existing key."""
        from helen.stdlib.collection import _remove_key

        data = {"a": 1, "b": 2, "c": 3}
        result = _remove_key(data, "b")

        assert result == {"a": 1, "c": 3}
        assert "b" not in result

    def test_remove_nonexistent_key(self):
        """Test removing a non-existent key (should return same dict)."""
        from helen.stdlib.collection import _remove_key

        data = {"a": 1, "b": 2}
        result = _remove_key(data, "x")

        assert result == {"a": 1, "b": 2}

    def test_remove_from_empty_dict(self):
        """Test removing from empty dict."""
        from helen.stdlib.collection import _remove_key

        data = {}
        result = _remove_key(data, "key")

        assert result == {}


class TestGet:
    """Test get function."""

    def test_get_existing_key(self):
        """Test getting an existing key."""
        from helen.stdlib.collection import _get

        data = {"name": "Alice", "age": 30}

        assert _get(data, "name") == "Alice"
        assert _get(data, "age") == 30

    def test_get_nonexistent_key_default(self):
        """Test getting non-existent key with default."""
        from helen.stdlib.collection import _get

        data = {"name": "Alice"}

        assert _get(data, "email", "N/A") == "N/A"
        assert _get(data, "missing") is None

    def test_get_with_none_default(self):
        """Test get with None as default."""
        from helen.stdlib.collection import _get

        data = {"a": 1}

        assert _get(data, "b", None) is None
        assert _get(data, "b", 0) == 0


class TestSetKey:
    """Test set_key function."""

    def test_set_new_key(self):
        """Test setting a new key."""
        from helen.stdlib.collection import _set_key

        data = {"a": 1, "b": 2}
        result = _set_key(data, "c", 3)

        assert result == {"a": 1, "b": 2, "c": 3}
        assert data == {"a": 1, "b": 2}  # Original unchanged

    def test_set_existing_key(self):
        """Test updating an existing key."""
        from helen.stdlib.collection import _set_key

        data = {"a": 1, "b": 2}
        result = _set_key(data, "a", 10)

        assert result == {"a": 10, "b": 2}
        assert data == {"a": 1, "b": 2}  # Original unchanged

    def test_set_key_empty_dict(self):
        """Test setting key in empty dict."""
        from helen.stdlib.collection import _set_key

        data = {}
        result = _set_key(data, "key", "value")

        assert result == {"key": "value"}


class TestHasKey:
    """Test has_key function."""

    def test_has_existing_key(self):
        """Test checking existing key."""
        from helen.stdlib.collection import _has_key

        data = {"name": "Alice", "age": 30}

        assert _has_key(data, "name") is True
        assert _has_key(data, "age") is True

    def test_has_nonexistent_key(self):
        """Test checking non-existent key."""
        from helen.stdlib.collection import _has_key

        data = {"name": "Alice"}

        assert _has_key(data, "email") is False
        assert _has_key(data, "missing") is False

    def test_has_key_empty_dict(self):
        """Test checking key in empty dict."""
        from helen.stdlib.collection import _has_key

        data = {}

        assert _has_key(data, "anything") is False


class TestChineseAliases:
    """Test Chinese aliases for new dict functions."""

    def test_chinese_aliases_registered(self):
        """Test that Chinese aliases are registered."""
        from helen.stdlib import stdlib

        # Check that aliases exist and map to correct canonical names
        assert stdlib.canonical_name("删除键") == "remove_key"
        assert stdlib.canonical_name("获取") == "get"
        assert stdlib.canonical_name("设置键") == "set_key"
        assert stdlib.canonical_name("包含键") == "has_key"

    def test_chinese_aliases_work(self):
        """Test that Chinese aliases work in practice."""
        from helen.stdlib import stdlib

        # Get functions via Chinese aliases using lookup
        remove_key_fn = stdlib.lookup("删除键")
        get_fn = stdlib.lookup("获取")
        set_key_fn = stdlib.lookup("设置键")
        has_key_fn = stdlib.lookup("包含键")

        assert remove_key_fn is not None
        assert get_fn is not None
        assert set_key_fn is not None
        assert has_key_fn is not None

        # Test they work (use .fn attribute)
        data = {"a": 1, "b": 2}
        assert remove_key_fn.fn(data, "a") == {"b": 2}
        assert get_fn.fn(data, "a") == 1
        assert set_key_fn.fn(data, "c", 3) == {"a": 1, "b": 2, "c": 3}
        assert has_key_fn.fn(data, "a") is True
