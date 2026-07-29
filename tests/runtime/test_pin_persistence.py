"""Tests for v1.30.1: pin state persistence to transcript.

Verifies that:
- JSONLBackend.update_pinned() rewrites the file with updated pinned state
- SQLiteBackend.update_pinned() updates the record in place
- TranscriptStore.update_pinned() updates both memory and disk
- Pin state survives reload from backend (simulates process restart)
"""

import tempfile
import os

import pytest

from helen.runtime.transcript_store import (
    TranscriptStore,
    JSONLBackend,
    SQLiteBackend,
)
from helen.runtime.history import Message


class TestJSONLBackendUpdatePinned:
    """Test JSONLBackend.update_pinned() persists to disk."""

    def test_update_pinned_true(self, tmp_path):
        jsonl_path = tmp_path / "transcript.jsonl"
        backend = JSONLBackend(jsonl_path)

        msg = Message(role="user", content="hello", uuid="msg-1")
        backend.append(msg)

        # Pin the message
        backend.update_pinned("msg-1", True)

        # Reload and verify
        items = backend.load_all()
        assert len(items) == 1
        assert items[0].uuid == "msg-1"
        assert items[0].pinned is True

    def test_update_pinned_false(self, tmp_path):
        jsonl_path = tmp_path / "transcript.jsonl"
        backend = JSONLBackend(jsonl_path)

        msg = Message(role="user", content="hello", uuid="msg-1", pinned=True)
        backend.append(msg)

        # Unpin the message
        backend.update_pinned("msg-1", False)

        # Reload and verify
        items = backend.load_all()
        assert len(items) == 1
        assert items[0].pinned is False

    def test_update_pinned_nonexistent_uuid(self, tmp_path):
        """update_pinned on a non-existent UUID is a no-op (no crash)."""
        jsonl_path = tmp_path / "transcript.jsonl"
        backend = JSONLBackend(jsonl_path)

        msg = Message(role="user", content="hello", uuid="msg-1")
        backend.append(msg)

        # Pin a non-existent UUID - should not raise
        backend.update_pinned("non-existent", True)

        # Original message unchanged
        items = backend.load_all()
        assert len(items) == 1
        assert items[0].pinned is False

    def test_update_pinned_preserves_other_messages(self, tmp_path):
        """Updating one message doesn't affect others."""
        jsonl_path = tmp_path / "transcript.jsonl"
        backend = JSONLBackend(jsonl_path)

        msg1 = Message(role="user", content="one", uuid="msg-1")
        msg2 = Message(role="assistant", content="two", uuid="msg-2")
        msg3 = Message(role="user", content="three", uuid="msg-3")
        backend.append(msg1)
        backend.append(msg2)
        backend.append(msg3)

        backend.update_pinned("msg-2", True)

        items = backend.load_all()
        assert len(items) == 3
        assert items[0].pinned is False
        assert items[1].pinned is True
        assert items[2].pinned is False

    def test_update_pinned_no_file(self, tmp_path):
        """update_pinned on non-existent file is a no-op."""
        backend = JSONLBackend(tmp_path / "nonexistent.jsonl")
        backend.update_pinned("any-uuid", True)  # should not raise


class TestSQLiteBackendUpdatePinned:
    """Test SQLiteBackend.update_pinned() persists to DB."""

    def test_update_pinned_true(self, tmp_path):
        db_path = tmp_path / "transcript.db"
        backend = SQLiteBackend(db_path)

        msg = Message(role="user", content="hello", uuid="msg-1")
        backend.append(msg)

        backend.update_pinned("msg-1", True)

        items = backend.load_all()
        assert len(items) == 1
        assert items[0].pinned is True

        backend.close()

    def test_update_pinned_false(self, tmp_path):
        db_path = tmp_path / "transcript.db"
        backend = SQLiteBackend(db_path)

        msg = Message(role="user", content="hello", uuid="msg-1", pinned=True)
        backend.append(msg)

        backend.update_pinned("msg-1", False)

        items = backend.load_all()
        assert len(items) == 1
        assert items[0].pinned is False

        backend.close()

    def test_update_pinned_no_duplicates(self, tmp_path):
        """SQLite uses INSERT OR REPLACE — no duplicate rows."""
        db_path = tmp_path / "transcript.db"
        backend = SQLiteBackend(db_path)

        msg = Message(role="user", content="hello", uuid="msg-1")
        backend.append(msg)
        backend.update_pinned("msg-1", True)
        backend.update_pinned("msg-1", False)

        items = backend.load_all()
        assert len(items) == 1
        assert items[0].pinned is False

        backend.close()


class TestTranscriptStoreUpdatePinned:
    """Test TranscriptStore.update_pinned() updates memory + disk."""

    def test_update_pinned_memory_and_disk(self, tmp_path):
        """update_pinned updates both in-memory message and disk."""
        db_path = tmp_path / "transcript.db"
        backend = SQLiteBackend(db_path)
        store = TranscriptStore(backend=backend)

        msg = store.append(Message(role="user", content="hello"))
        uuid = msg.uuid

        # Pin
        result = store.update_pinned(uuid, True)
        assert result is True
        assert store.get(uuid).pinned is True

        # Unpin
        result = store.update_pinned(uuid, False)
        assert result is True
        assert store.get(uuid).pinned is False

        store.close()

    def test_update_pinned_survives_reload(self, tmp_path):
        """Pin state survives store reload (simulates process restart)."""
        db_path = tmp_path / "transcript.db"

        # Session 1: create and pin
        backend1 = SQLiteBackend(db_path)
        store1 = TranscriptStore(backend=backend1)
        msg = store1.append(Message(role="user", content="important"))
        uuid = msg.uuid
        store1.update_pinned(uuid, True)
        store1.close()

        # Session 2: reload from disk
        backend2 = SQLiteBackend(db_path)
        store2 = TranscriptStore.load_from_backend(backend2)
        reloaded = store2.get(uuid)
        assert reloaded is not None
        assert reloaded.pinned is True

        store2.close()

    def test_update_pinned_nonexistent(self, tmp_path):
        db_path = tmp_path / "transcript.db"
        backend = SQLiteBackend(db_path)
        store = TranscriptStore(backend=backend)

        result = store.update_pinned("non-existent", True)
        assert result is False

        store.close()

    def test_update_pinned_jsonl_backend(self, tmp_path):
        """Pin persistence works with JSONL backend too."""
        jsonl_path = tmp_path / "transcript.jsonl"

        backend1 = JSONLBackend(jsonl_path)
        store1 = TranscriptStore(backend=backend1)
        msg = store1.append(Message(role="user", content="pinned note"))
        uuid = msg.uuid
        store1.update_pinned(uuid, True)
        store1.close()

        backend2 = JSONLBackend(jsonl_path)
        store2 = TranscriptStore.load_from_backend(backend2)
        reloaded = store2.get(uuid)
        assert reloaded is not None
        assert reloaded.pinned is True

        store2.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
