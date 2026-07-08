"""Tests for TranscriptStore JSONL backend persistence."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from helen.runtime.history import Message
from helen.runtime.transcript_store import (
    BoundaryMarker,
    JSONLBackend,
    TranscriptStore,
)


class TestJSONLBackend:
    """Test JSONL persistence backend."""

    def test_create_backend(self, tmp_path):
        """Test creating a JSONL backend."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)
        assert backend.path == path
        assert path.parent.exists()

    def test_append_message(self, tmp_path):
        """Test appending a message to backend."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)

        msg = Message(role="user", content="Hello", uuid="abc123")
        backend.append(msg)
        backend.close()

        # Verify file was written
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        # Verify content
        data = json.loads(lines[0])
        assert data["type"] == "message"
        assert data["role"] == "user"
        assert data["content"] == "Hello"
        assert data["uuid"] == "abc123"

    def test_append_boundary_marker(self, tmp_path):
        """Test appending a boundary marker to backend."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)

        marker = BoundaryMarker(
            uuid="marker123",
            head_uuid="head456",
            tail_uuid="tail789",
            anchor_uuid="anchor000",
            summary="Compressed",
            layer="layer1",
        )
        backend.append(marker)
        backend.close()

        # Verify file was written
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        # Verify content
        data = json.loads(lines[0])
        assert data["type"] == "boundary_marker"
        assert data["uuid"] == "marker123"
        assert data["layer"] == "layer1"

    def test_load_all(self, tmp_path):
        """Test loading all items from backend."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)

        # Append some items
        msg1 = Message(role="user", content="Hello", uuid="msg1")
        msg2 = Message(role="assistant", content="Hi", uuid="msg2")
        marker = BoundaryMarker(uuid="marker1", layer="test")

        backend.append(msg1)
        backend.append(msg2)
        backend.append(marker)
        backend.close()

        # Load all items
        backend2 = JSONLBackend(path)
        items = backend2.load_all()
        backend2.close()

        assert len(items) == 3
        assert isinstance(items[0], Message)
        assert items[0].uuid == "msg1"
        assert isinstance(items[1], Message)
        assert items[1].uuid == "msg2"
        assert isinstance(items[2], BoundaryMarker)
        assert items[2].uuid == "marker1"

    def test_load_empty_file(self, tmp_path):
        """Test loading from non-existent file."""
        path = tmp_path / "nonexistent.jsonl"
        backend = JSONLBackend(path)
        items = backend.load_all()
        assert items == []

    def test_load_corrupted_line(self, tmp_path):
        """Test loading with corrupted line (should skip and continue)."""
        path = tmp_path / "test.jsonl"

        # Write valid, corrupted, and valid lines
        msg1 = Message(role="user", content="Valid 1", uuid="msg1")
        msg2 = Message(role="user", content="Valid 2", uuid="msg2")

        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "message",
                "role": "user",
                "content": "Valid 1",
                "uuid": "msg1",
            }) + "\n")
            f.write("CORRUPTED LINE\n")
            f.write(json.dumps({
                "type": "message",
                "role": "user",
                "content": "Valid 2",
                "uuid": "msg2",
            }) + "\n")

        backend = JSONLBackend(path)
        items = backend.load_all()
        backend.close()

        # Should load valid lines and skip corrupted one
        assert len(items) == 2
        assert items[0].uuid == "msg1"
        assert items[1].uuid == "msg2"


class TestTranscriptStoreWithBackend:
    """Test TranscriptStore with persistence backend."""

    def test_store_with_backend(self, tmp_path):
        """Test TranscriptStore with JSONL backend."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend)

        # Append messages
        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="assistant", content="Hi")

        store.append(msg1)
        store.append(msg2)
        store.close()

        # Verify file was written
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_load_from_backend(self, tmp_path):
        """Test loading TranscriptStore from backend."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)

        # Create and populate a store
        store1 = TranscriptStore(backend=backend)
        msg1 = Message(role="user", content="Hello", uuid="msg1")
        msg2 = Message(role="assistant", content="Hi", uuid="msg2")
        store1.append(msg1)
        store1.append(msg2)
        store1.close()

        # Load into a new store
        backend2 = JSONLBackend(path)
        store2 = TranscriptStore.load_from_backend(backend2)

        assert store2.get_message_count() == 2
        view = store2.read_view()
        assert len(view) == 2
        assert view[0].uuid == "msg1"
        assert view[1].uuid == "msg2"

        store2.close()

    def test_view_cache_invalidation(self, tmp_path):
        """Test that view cache is invalidated on append."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend)

        # Append first message
        msg1 = Message(role="user", content="Hello")
        store.append(msg1)

        # Get view (caches it)
        view1 = store.read_view()
        assert len(view1) == 1

        # Append second message (should invalidate cache)
        msg2 = Message(role="assistant", content="Hi")
        store.append(msg2)

        # Get view again (should be updated)
        view2 = store.read_view()
        assert len(view2) == 2

        store.close()

    def test_record_compression_with_backend(self, tmp_path):
        """Test recording compression with backend persistence."""
        path = tmp_path / "test.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend)

        # Append messages
        msg1 = Message(role="user", content="Message 1")
        msg2 = Message(role="assistant", content="Message 2")
        msg3 = Message(role="user", content="Message 3")

        store.append(msg1)
        store.append(msg2)
        store.append(msg3)

        # Record compression
        marker = store.record_compression(
            head_uuid=msg1.uuid,
            tail_uuid=msg2.uuid,
            anchor_uuid=msg3.uuid,
            summary="Compressed messages 1-2",
            layer="test_layer",
            original_token_count=100,
            compressed_token_count=20,
        )

        store.close()

        # Verify both messages and boundary marker were persisted
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 4  # 3 messages + 1 boundary marker

        # Verify boundary marker content
        marker_data = json.loads(lines[3])
        assert marker_data["type"] == "boundary_marker"
        assert marker_data["uuid"] == marker.uuid
        assert marker_data["layer"] == "test_layer"
