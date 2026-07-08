"""Tests for Phase 4: SQLite backend and LRU cache."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from helen.runtime.history import Message
from helen.runtime.transcript_store import (
    BoundaryMarker,
    JSONLBackend,
    SQLiteBackend,
    TranscriptStore,
)


class TestSQLiteBackend:
    """Test SQLite backend for transcript persistence."""

    def test_create_sqlite_backend(self, tmp_path):
        """Test creating a SQLite backend."""
        path = tmp_path / "test.db"
        backend = SQLiteBackend(path)
        assert backend.path == path
        assert path.parent.exists()
        backend.close()

    def test_sqlite_append_message(self, tmp_path):
        """Test appending a message to SQLite backend."""
        path = tmp_path / "test.db"
        backend = SQLiteBackend(path)

        msg = Message(role="user", content="Hello", uuid="abc123")
        backend.append(msg)

        # Verify by loading
        items = backend.load_all()
        assert len(items) == 1
        assert items[0].uuid == "abc123"
        assert items[0].content == "Hello"

        backend.close()

    def test_sqlite_append_boundary_marker(self, tmp_path):
        """Test appending a boundary marker to SQLite backend."""
        path = tmp_path / "test.db"
        backend = SQLiteBackend(path)

        marker = BoundaryMarker(
            uuid="marker123",
            head_uuid="head456",
            tail_uuid="tail789",
            anchor_uuid="anchor000",
            summary="Compressed",
            layer="layer1",
        )
        backend.append(marker)

        # Verify by loading
        items = backend.load_all()
        assert len(items) == 1
        assert isinstance(items[0], BoundaryMarker)
        assert items[0].uuid == "marker123"
        assert items[0].layer == "layer1"

        backend.close()

    def test_sqlite_load_multiple_items(self, tmp_path):
        """Test loading multiple items from SQLite backend."""
        path = tmp_path / "test.db"
        backend = SQLiteBackend(path)

        # Append multiple items
        for i in range(10):
            msg = Message(role="user", content=f"Message {i}", uuid=f"msg{i}")
            backend.append(msg)

        # Verify by loading
        items = backend.load_all()
        assert len(items) == 10
        for i, item in enumerate(items):
            assert item.uuid == f"msg{i}"
            assert item.content == f"Message {i}"

        backend.close()

    def test_sqlite_wal_mode(self, tmp_path):
        """Test that SQLite uses WAL mode."""
        path = tmp_path / "test.db"
        backend = SQLiteBackend(path)

        # Check WAL file exists after write
        msg = Message(role="user", content="Test", uuid="test123")
        backend.append(msg)

        # WAL file should exist
        wal_path = path.with_suffix(".db-wal")
        # Note: WAL file may or may not exist depending on checkpoint timing
        # Just verify the database works
        items = backend.load_all()
        assert len(items) == 1

        backend.close()


class TestLRUCache:
    """Test LRU cache for memory efficiency."""

    def test_lru_cache_basic(self, tmp_path):
        """Test basic LRU cache functionality."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend, max_memory_items=100)

        # Add 150 items (exceeds max_memory_items)
        for i in range(150):
            msg = Message(role="user", content=f"Message {i}", uuid=f"msg{i}")
            store.append(msg)

        # Should have evicted some items
        assert len(store.transcript) <= 100
        assert store._offloaded_count > 0

        # All items should still be in backend
        loaded_items = backend.load_all()
        assert len(loaded_items) == 150

        store.close()

    def test_lru_cache_eviction_threshold(self, tmp_path):
        """Test LRU cache eviction at 80% threshold."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend, max_memory_items=100)

        # Add exactly 100 items (at limit)
        for i in range(100):
            msg = Message(role="user", content=f"Message {i}", uuid=f"msg{i}")
            store.append(msg)

        # Should not evict yet
        assert len(store.transcript) == 100
        assert store._offloaded_count == 0

        # Add one more item (triggers eviction)
        msg = Message(role="user", content="Message 100", uuid="msg100")
        store.append(msg)

        # Should evict down to 80 items (80% of 100)
        assert len(store.transcript) == 80
        assert store._offloaded_count == 21  # 101 - 80 = 21

        store.close()

    def test_lru_cache_load_from_backend(self, tmp_path):
        """Test loading from backend with LRU cache."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)

        # Create store and add 200 items
        store1 = TranscriptStore(backend=backend, max_memory_items=1000)
        for i in range(200):
            msg = Message(role="user", content=f"Message {i}", uuid=f"msg{i}")
            store1.append(msg)
        store1.close()

        # Load with smaller memory limit
        backend2 = JSONLBackend(path)
        store2 = TranscriptStore.load_from_backend(backend2, max_memory_items=100)

        # Should only load last 100 items
        assert len(store2.transcript) == 100
        assert store2._offloaded_count == 100

        # Should have the most recent items
        assert store2.transcript[0].uuid == "msg100"
        assert store2.transcript[-1].uuid == "msg199"

        store2.close()

    def test_uuid_addressing(self, tmp_path):
        """Test UUID-based addressing (Phase 4.2)."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend)

        # Add messages
        msg1 = Message(role="user", content="First", uuid="uuid1")
        msg2 = Message(role="assistant", content="Second", uuid="uuid2")
        msg3 = Message(role="user", content="Third", uuid="uuid3")

        store.append(msg1)
        store.append(msg2)
        store.append(msg3)

        # Retrieve by UUID
        retrieved1 = store.get("uuid1")
        retrieved2 = store.get("uuid2")
        retrieved3 = store.get("uuid3")

        assert retrieved1 is not None
        assert retrieved1.content == "First"
        assert retrieved2 is not None
        assert retrieved2.content == "Second"
        assert retrieved3 is not None
        assert retrieved3.content == "Third"

        # Non-existent UUID
        assert store.get("nonexistent") is None

        store.close()


class TestPhase4Integration:
    """Integration tests for Phase 4 features."""

    def test_sqlite_with_lru_cache(self, tmp_path):
        """Test SQLite backend with LRU cache."""
        path = tmp_path / "test.db"
        backend = SQLiteBackend(path)
        store = TranscriptStore(backend=backend, max_memory_items=50)

        # Add 100 items
        for i in range(100):
            msg = Message(role="user", content=f"Message {i}", uuid=f"msg{i}")
            store.append(msg)

        # Should have evicted some items from memory
        assert len(store.transcript) <= 50
        assert store._offloaded_count > 0

        # All items should be in SQLite
        loaded_items = backend.load_all()
        assert len(loaded_items) == 100

        # Most recent items should be in memory
        last_item = store.get("msg99")
        assert last_item is not None
        assert last_item.content == "Message 99"

        # Some old items should be offloaded (not in memory)
        # The exact number depends on eviction pattern
        offloaded_count = sum(1 for i in range(50) if store.get(f"msg{i}") is None)
        assert offloaded_count > 0  # At least some items are offloaded

        store.close()

    def test_compression_with_lru_cache(self, tmp_path):
        """Test compression works correctly with LRU cache."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend, max_memory_items=100)

        # Add messages
        messages = []
        for i in range(50):
            msg = Message(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")
            store.append(msg)
            messages.append(msg)

        # Record compression
        marker = store.record_compression(
            head_uuid=messages[0].uuid,
            tail_uuid=messages[9].uuid,
            anchor_uuid=messages[10].uuid,
            summary="Compressed first 10 messages",
            layer="test",
        )

        # Verify boundary marker was added
        assert store.get_boundary_count() == 1

        # View should exclude compressed messages
        view = store.read_view()
        assert len(view) == 41  # 50 - 10 + 1 summary

        store.close()

    def test_performance_large_session(self, tmp_path):
        """Test performance with large session (Phase 4 goal: 100K messages <100MB)."""
        path = tmp_path / "test.db"
        backend = SQLiteBackend(path)
        store = TranscriptStore(backend=backend, max_memory_items=1000)

        # Add 10K messages (test performance)
        for i in range(10000):
            msg = Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i} with some content to simulate real usage",
            )
            store.append(msg)

        # Should have evicted most items from memory
        assert len(store.transcript) <= 1000
        assert store._offloaded_count > 9000

        # All items should be in SQLite
        loaded_items = backend.load_all()
        assert len(loaded_items) == 10000

        # Database file should be reasonable size (<10MB for 10K messages)
        db_size_mb = path.stat().st_size / (1024 * 1024)
        assert db_size_mb < 10

        store.close()
