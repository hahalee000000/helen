"""Tests for hellen.runtime.memory — MemoryProvider (HLD 3.8.2).

Covers:
- FileMemoryProvider: JSON persistence, directory creation, get/set
- InMemoryProvider: dict storage for testing
- search fallback: text containment matching
- Path not found handling
"""

import os
import tempfile
import json

from hellen.runtime.memory import FileMemoryProvider, InMemoryProvider


class TestFileMemoryProvider:
    """Test JSON file-based memory storage."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "memory.json")
        self.provider = FileMemoryProvider()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_set_and_get(self):
        """set() stores and get() retrieves a value."""
        self.provider.set(self.path, "key1", "value1")
        assert self.provider.get(self.path, "key1") == "value1"

    def test_get_nonexistent_key(self):
        """get() returns None for missing key."""
        result = self.provider.get(self.path, "missing")
        assert result is None

    def test_save_and_load(self):
        """save() persists and load() retrieves all data."""
        data = {"a": "1", "b": "2"}
        self.provider.save(self.path, data)
        loaded = self.provider.load(self.path)
        assert loaded == data

    def test_load_nonexistent_file(self):
        """load() returns empty dict for non-existent file."""
        result = self.provider.load(self.path)
        assert result == {}

    def test_creates_parent_directory(self):
        """save() creates parent directories automatically."""
        nested = os.path.join(self.tmpdir, "sub", "dir", "mem.json")
        self.provider.save(nested, {"x": "y"})
        assert os.path.exists(nested)

    def test_persistence_across_instances(self):
        """Data persists: new instance loads same file."""
        self.provider.save(self.path, {"persisted": "yes"})
        new_provider = FileMemoryProvider()
        assert new_provider.get(self.path, "persisted") == "yes"


class TestInMemoryProvider:
    """Test in-memory dict storage."""

    def setup_method(self):
        self.provider = InMemoryProvider()
        self.path = "test"

    def test_set_and_get(self):
        self.provider.set(self.path, "k", "v")
        assert self.provider.get(self.path, "k") == "v"

    def test_get_nonexistent(self):
        assert self.provider.get(self.path, "missing") is None

    def test_save_and_load(self):
        self.provider.save(self.path, {"a": "1"})
        assert self.provider.load(self.path) == {"a": "1"}

    def test_does_not_persist(self):
        """InMemoryProvider does not persist to disk."""
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "mem.json")
        self.provider.save(path, {"x": "y"})
        # File should not exist on disk
        assert not os.path.exists(path)
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestMemorySearch:
    """Test search fallback behavior."""

    def test_file_provider_search(self):
        """search() finds entries containing query text."""
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "mem.json")
        provider = FileMemoryProvider()
        provider.set(path, "note1", "Python is great for ML")
        provider.set(path, "note2", "JavaScript for web")
        provider.set(path, "note3", "Python web frameworks")

        results = provider.search(path, "Python", top_k=5)
        assert len(results) == 2
        assert all("Python" in r["value"] for r in results)
        assert all(r["score"] == 1.0 for r in results)

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_inmemory_provider_search(self):
        """InMemoryProvider search works the same way."""
        provider = InMemoryProvider()
        provider.set("test", "a", "hello world")
        provider.set("test", "b", "goodbye world")
        provider.set("test", "c", "foo bar")

        results = provider.search("test", "world", top_k=5)
        assert len(results) == 2

    def test_search_respects_top_k(self):
        """search() limits results to top_k."""
        provider = InMemoryProvider()
        for i in range(10):
            provider.set("test", f"k{i}", "match text")

        results = provider.search("test", "match", top_k=3)
        assert len(results) == 3
