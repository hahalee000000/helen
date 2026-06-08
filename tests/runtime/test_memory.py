"""Tests for Helen memory providers (HLD §3.8.2).

Tests cover:
- InMemoryProvider: basic CRUD, isolation
- FileMemoryProvider: persistence, file creation, corruption recovery
- MemoryProvider ABC: interface contract enforcement
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from helen.runtime.memory import (
    FileMemoryProvider,
    InMemoryProvider,
    MemoryProvider,
)


# ── InMemoryProvider Tests ─────────────────────────────────────


class TestInMemoryProvider:
    """In-memory provider: basic CRUD operations."""

    def setup_method(self) -> None:
        self.provider = InMemoryProvider()

    def test_get_returns_none_for_missing_key(self) -> None:
        assert self.provider.get("nonexistent") is None

    def test_set_and_get(self) -> None:
        self.provider.set("name", "Alice")
        assert self.provider.get("name") == "Alice"

    def test_overwrite_existing_key(self) -> None:
        self.provider.set("name", "Alice")
        self.provider.set("name", "Bob")
        assert self.provider.get("name") == "Bob"

    def test_delete_existing_key(self) -> None:
        self.provider.set("name", "Alice")
        self.provider.delete("name")
        assert self.provider.get("name") is None

    def test_delete_nonexistent_key_is_noop(self) -> None:
        self.provider.delete("nonexistent")  # Should not raise

    def test_list_keys_empty(self) -> None:
        assert self.provider.list_keys() == []

    def test_list_keys_with_data(self) -> None:
        self.provider.set("a", "1")
        self.provider.set("b", "2")
        self.provider.set("c", "3")
        keys = self.provider.list_keys()
        assert set(keys) == {"a", "b", "c"}

    def test_data_isolation(self) -> None:
        """Two providers should not share data."""
        p1 = InMemoryProvider()
        p2 = InMemoryProvider()
        p1.set("key", "value")
        assert p2.get("key") is None

    def test_multiple_keys(self) -> None:
        """Store and retrieve multiple keys."""
        for i in range(100):
            self.provider.set(f"key_{i}", f"value_{i}")
        for i in range(100):
            assert self.provider.get(f"key_{i}") == f"value_{i}"


# ── FileMemoryProvider Tests ──────────────────────────────────


class TestFileMemoryProvider:
    """File-backed provider: persistence and file operations."""

    def setup_method(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.filepath = os.path.join(self.tmpdir, "memory.json")

    def _create_provider(self) -> FileMemoryProvider:
        return FileMemoryProvider(self.filepath)

    def test_get_returns_none_for_missing_key(self) -> None:
        provider = self._create_provider()
        assert provider.get("nonexistent") is None

    def test_set_and_get(self) -> None:
        provider = self._create_provider()
        provider.set("name", "Alice")
        assert provider.get("name") == "Alice"

    def test_persistence_across_instances(self) -> None:
        """Data should survive creating a new provider instance."""
        p1 = self._create_provider()
        p1.set("name", "Alice")
        p1.set("age", "30")

        p2 = self._create_provider()
        assert p2.get("name") == "Alice"
        assert p2.get("age") == "30"

    def test_file_is_created_on_first_write(self) -> None:
        provider = self._create_provider()
        assert not os.path.exists(self.filepath)
        provider.set("key", "value")
        assert os.path.exists(self.filepath)

    def test_file_contains_valid_json(self) -> None:
        provider = self._create_provider()
        provider.set("a", "1")
        provider.set("b", "2")
        with open(self.filepath, encoding="utf-8") as f:
            data = json.load(f)
        assert data == {"a": "1", "b": "2"}

    def test_overwrite_existing_key(self) -> None:
        provider = self._create_provider()
        provider.set("name", "Alice")
        provider.set("name", "Bob")
        assert provider.get("name") == "Bob"

        # Verify persistence sees the overwrite
        p2 = self._create_provider()
        assert p2.get("name") == "Bob"

    def test_delete_existing_key(self) -> None:
        provider = self._create_provider()
        provider.set("name", "Alice")
        provider.delete("name")
        assert provider.get("name") is None

        # Verify persistence sees the deletion
        p2 = self._create_provider()
        assert p2.get("name") is None

    def test_delete_nonexistent_key_is_noop(self) -> None:
        provider = self._create_provider()
        provider.delete("nonexistent")  # Should not raise

    def test_list_keys_empty(self) -> None:
        provider = self._create_provider()
        assert provider.list_keys() == []

    def test_list_keys_with_data(self) -> None:
        provider = self._create_provider()
        provider.set("a", "1")
        provider.set("b", "2")
        keys = provider.list_keys()
        assert set(keys) == {"a", "b"}

    def test_creates_parent_directories(self) -> None:
        """Provider should create parent directories if missing."""
        deep_path = os.path.join(self.tmpdir, "a", "b", "c", "mem.json")
        provider = FileMemoryProvider(deep_path)
        provider.set("key", "value")
        assert os.path.exists(deep_path)

    def test_load_existing_file(self) -> None:
        """Provider should load data from an existing file."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump({"preloaded": "data"}, f)

        provider = self._create_provider()
        assert provider.get("preloaded") == "data"

    def test_clear_removes_all_data(self) -> None:
        provider = self._create_provider()
        provider.set("a", "1")
        provider.set("b", "2")
        provider.clear()
        assert provider.list_keys() == []
        assert provider.get("a") is None

    def test_clear_persists(self) -> None:
        provider = self._create_provider()
        provider.set("a", "1")
        provider.clear()

        p2 = self._create_provider()
        assert p2.list_keys() == []

    def test_size(self) -> None:
        provider = self._create_provider()
        assert provider.size() == 0
        provider.set("a", "1")
        provider.set("b", "2")
        assert provider.size() == 2

    def test_path_property(self) -> None:
        provider = self._create_provider()
        assert provider.path == self.filepath

    def test_unicode_values(self) -> None:
        """Provider should handle unicode strings."""
        provider = self._create_provider()
        provider.set("greeting", "你好世界")
        assert provider.get("greeting") == "你好世界"

        p2 = self._create_provider()
        assert p2.get("greeting") == "你好世界"

    def test_corrupted_json_file(self) -> None:
        """Provider should handle corrupted JSON gracefully."""
        with open(self.filepath, "w") as f:
            f.write("not valid json {{{")

        # Should not crash; treats as empty
        provider = self._create_provider()
        assert provider.list_keys() == []


# ── MemoryProvider ABC Contract Tests ─────────────────────────


class TestMemoryProviderContract:
    """Verify that all providers implement the MemoryProvider contract."""

    def test_inmemory_is_subclass(self) -> None:
        assert issubclass(InMemoryProvider, MemoryProvider)

    def test_filememory_is_subclass(self) -> None:
        assert issubclass(FileMemoryProvider, MemoryProvider)

    def test_inmemory_implements_all_methods(self) -> None:
        provider = InMemoryProvider()
        assert hasattr(provider, "get")
        assert hasattr(provider, "set")
        assert hasattr(provider, "delete")
        assert hasattr(provider, "list_keys")

    def test_filememory_implements_all_methods(self) -> None:
        provider = FileMemoryProvider("/tmp/test.json")
        assert hasattr(provider, "get")
        assert hasattr(provider, "set")
        assert hasattr(provider, "delete")
        assert hasattr(provider, "list_keys")

    def test_cannot_instantiate_abc_directly(self) -> None:
        with pytest.raises(TypeError):
            MemoryProvider()  # type: ignore[abstract]
