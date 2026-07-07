"""Tests for Phase 10: Mostly-append Transcript Store."""

import pytest
from helen.runtime.transcript_store import TranscriptStore, BoundaryMarker, _generate_uuid
from helen.runtime.history import Message


class TestBoundaryMarker:
    """Test BoundaryMarker dataclass."""

    def test_auto_uuid(self):
        marker = BoundaryMarker()
        assert marker.uuid != ""
        assert len(marker.uuid) == 12

    def test_custom_uuid(self):
        marker = BoundaryMarker(uuid="custom_id")
        assert marker.uuid == "custom_id"

    def test_to_dict(self):
        marker = BoundaryMarker(
            head_uuid="h1", tail_uuid="t1", anchor_uuid="a1",
            summary="test summary", layer="test_layer",
        )
        d = marker.to_dict()

        assert d["type"] == "boundary_marker"
        assert d["head_uuid"] == "h1"
        assert d["summary"] == "test summary"
        assert d["layer"] == "test_layer"

    def test_from_dict(self):
        d = {
            "uuid": "abc123",
            "head_uuid": "h1", "tail_uuid": "t1", "anchor_uuid": "a1",
            "summary": "test", "layer": "l1",
            "timestamp": 1234567890.0,
            "original_token_count": 1000,
            "compressed_token_count": 500,
        }
        marker = BoundaryMarker.from_dict(d)

        assert marker.uuid == "abc123"
        assert marker.head_uuid == "h1"
        assert marker.original_token_count == 1000


class TestTranscriptStore:
    """Test TranscriptStore class."""

    def test_append_assigns_uuid(self):
        store = TranscriptStore()
        msg = Message(role="user", content="Hello")

        result = store.append(msg)

        assert result.uuid != ""
        assert len(result.uuid) == 12

    def test_append_preserves_existing_uuid(self):
        store = TranscriptStore()
        msg = Message(role="user", content="Hello", uuid="existing_uuid")

        result = store.append(msg)

        assert result.uuid == "existing_uuid"

    def test_append_many(self):
        store = TranscriptStore()
        msgs = [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello"),
        ]

        result = store.append_many(msgs)

        assert len(result) == 2
        assert all(m.uuid != "" for m in result)
        assert store.get_message_count() == 2

    def test_record_compression(self):
        store = TranscriptStore()

        # Append some messages
        msg1 = store.append(Message(role="user", content="Q1"))
        msg2 = store.append(Message(role="assistant", content="A1"))
        msg3 = store.append(Message(role="user", content="Q2"))
        store.append(Message(role="assistant", content="A2"))

        # Record compression
        marker = store.record_compression(
            head_uuid=msg1.uuid,
            tail_uuid=msg2.uuid,
            anchor_uuid=msg3.uuid,
            summary="Earlier conversation",
            layer="test",
            original_token_count=100,
            compressed_token_count=50,
        )

        assert marker.uuid != ""
        assert store.get_boundary_count() == 1
        assert store.get_transcript_size() == 5  # 4 msgs + 1 marker

    def test_read_view_without_compression(self):
        store = TranscriptStore()
        store.append(Message(role="user", content="Hi"))
        store.append(Message(role="assistant", content="Hello"))

        view = store.read_view()

        assert len(view) == 2
        assert view[0].content == "Hi"
        assert view[1].content == "Hello"

    def test_read_view_with_compression(self):
        store = TranscriptStore()
        msg1 = store.append(Message(role="user", content="Q1"))
        msg2 = store.append(Message(role="assistant", content="A1"))
        msg3 = store.append(Message(role="user", content="Q2"))
        msg4 = store.append(Message(role="assistant", content="A2"))

        # Compress first two messages
        store.record_compression(
            head_uuid=msg1.uuid,
            tail_uuid=msg2.uuid,
            anchor_uuid=msg3.uuid,
            summary="Compressed: Q1/A1",
            layer="test",
        )

        view = store.read_view()

        # Should have summary + remaining messages
        assert len(view) == 3  # summary + Q2 + A2
        # First should be summary
        assert "Compressed" in view[0].content
        assert view[1].content == "Q2"
        assert view[2].content == "A2"

    def test_get_compression_audit(self):
        store = TranscriptStore()
        msg1 = store.append(Message(role="user", content="Q1"))
        msg2 = store.append(Message(role="assistant", content="A1"))
        msg3 = store.append(Message(role="user", content="Q2"))

        store.record_compression(
            head_uuid=msg1.uuid,
            tail_uuid=msg2.uuid,
            anchor_uuid=msg3.uuid,
            summary="Test summary",
            layer="test_layer",
        )

        audit = store.get_compression_audit()

        assert len(audit) == 1
        assert audit[0]["summary"] == "Test summary"
        assert audit[0]["layer"] == "test_layer"

    def test_serialization_roundtrip(self):
        store = TranscriptStore()
        msg1 = store.append(Message(role="user", content="Hello"))
        msg2 = store.append(Message(role="assistant", content="Hi"))

        # Serialize
        data = store.to_dict()
        assert data["version"] == 1
        assert len(data["items"]) == 2

        # Deserialize
        restored = TranscriptStore.from_dict(data)
        assert restored.get_message_count() == 2
        view = restored.read_view()
        assert view[0].content == "Hello"
        assert view[1].content == "Hi"

    def test_serialization_with_boundaries(self):
        store = TranscriptStore()
        msg1 = store.append(Message(role="user", content="Q1"))
        msg2 = store.append(Message(role="assistant", content="A1"))
        msg3 = store.append(Message(role="user", content="Q2"))

        store.record_compression(
            head_uuid=msg1.uuid,
            tail_uuid=msg2.uuid,
            anchor_uuid=msg3.uuid,
            summary="Summary",
            layer="test",
        )

        data = store.to_dict()
        assert len(data["items"]) == 4  # 3 msgs + 1 boundary

        restored = TranscriptStore.from_dict(data)
        assert restored.get_message_count() == 3
        assert restored.get_boundary_count() == 1


class TestMessageUUID:
    """Test Message UUID field (Phase 10)."""

    def test_default_empty_uuid(self):
        msg = Message(role="user", content="Hello")
        assert msg.uuid == ""

    def test_custom_uuid(self):
        msg = Message(role="user", content="Hello", uuid="test123")
        assert msg.uuid == "test123"

    def test_uuid_backward_compatible(self):
        """Existing code that doesn't pass uuid still works."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"


class TestGenerateUuid:
    """Test UUID generation helper."""

    def test_generates_string(self):
        uid = _generate_uuid()
        assert isinstance(uid, str)
        assert len(uid) == 12

    def test_unique(self):
        uids = {_generate_uuid() for _ in range(100)}
        assert len(uids) == 100  # All unique
