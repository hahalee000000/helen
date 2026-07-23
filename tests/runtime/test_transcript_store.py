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


# ═══════════════════════════════════════════════════════════════════════
# v1.23.3 SessionMeta tests
# ═══════════════════════════════════════════════════════════════════════


class TestSessionMeta:
    """v1.23.3: Session metadata (argv, timestamp, version, etc.)."""

    def test_session_meta_roundtrip(self):
        """SessionMeta can be serialized and deserialized."""
        from helen.runtime.transcript_store import SessionMeta
        meta = SessionMeta(
            argv=["helen", "test.helen"],
            timestamp=1720435200.123,
            helen_version="1.23.3",
            python_version="3.12.13",
            platform="linux-aarch64",
            cwd="/home/test",
            session_id="session_1720435200_abc123",
            session_scope="project",
        )
        d = meta.to_dict()
        assert d["type"] == "session_meta"
        assert d["argv"] == ["helen", "test.helen"]
        assert d["helen_version"] == "1.23.3"

        restored = SessionMeta.from_dict(d)
        assert restored.argv == meta.argv
        assert restored.timestamp == meta.timestamp
        assert restored.helen_version == meta.helen_version
        assert restored.session_scope == meta.session_scope

    def test_session_meta_from_current_context(self):
        """from_current_context captures sys.argv and versions."""
        from helen.runtime.transcript_store import SessionMeta
        meta = SessionMeta.from_current_context(
            session_id="test_session",
            session_scope="global",
        )
        assert len(meta.argv) > 0  # at least python executable
        assert meta.timestamp > 0
        assert meta.helen_version != ""
        assert meta.python_version != ""
        assert meta.platform != ""
        assert meta.cwd != ""
        assert meta.session_id == "test_session"
        assert meta.session_scope == "global"

    def test_jsonl_backend_write_read_meta(self, tmp_path):
        """JSONL backend can write and read session metadata."""
        from helen.runtime.transcript_store import (
            JSONLBackend, SessionMeta, Message,
        )
        path = tmp_path / "transcript.jsonl"
        backend = JSONLBackend(path)

        meta = SessionMeta(
            argv=["helen", "test.helen"],
            timestamp=1720435200.0,
            helen_version="1.23.3",
            python_version="3.12.13",
            platform="linux-aarch64",
            cwd="/home/test",
            session_id="test_session",
            session_scope="project",
        )
        backend.write_meta(meta)

        # Verify meta is the first line
        assert path.exists()
        first_line = path.read_text().split("\n")[0]
        assert '"type": "session_meta"' in first_line or '"type":"session_meta"' in first_line

        # Read meta back
        restored = backend.read_meta()
        assert restored is not None
        assert restored.argv == ["helen", "test.helen"]
        assert restored.helen_version == "1.23.3"

        # load_all should NOT include meta as a message
        items = backend.load_all()
        assert len(items) == 0  # no messages, meta is filtered out

        # Append a real message, meta should still be there
        backend.append(Message(role="user", content="hello"))
        items = backend.load_all()
        assert len(items) == 1
        assert items[0].role == "user"

        # Meta still readable
        restored2 = backend.read_meta()
        assert restored2 is not None
        assert restored2.argv == ["helen", "test.helen"]

        backend.close()

    def test_jsonl_backend_read_meta_old_transcript(self, tmp_path):
        """Old transcripts without meta return None gracefully."""
        from helen.runtime.transcript_store import JSONLBackend, Message
        path = tmp_path / "old_transcript.jsonl"
        # Write an old-style transcript (no meta)
        with open(path, "w") as f:
            f.write('{"type": "message", "role": "user", "content": "hi"}\n')

        backend = JSONLBackend(path)
        assert backend.read_meta() is None

        # load_all still works
        items = backend.load_all()
        assert len(items) == 1
        backend.close()

    def test_transcript_store_meta_roundtrip(self, tmp_path):
        """TranscriptStore exposes write_meta and read_meta."""
        from helen.runtime.transcript_store import (
            TranscriptStore, JSONLBackend, SessionMeta, Message,
        )
        path = tmp_path / "transcript.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend)

        meta = SessionMeta.from_current_context(
            session_id="test_session",
            session_scope="project",
        )
        store.write_meta(meta)

        # Append a message
        store.append(Message(role="user", content="hello"))

        # Read back
        restored = store.read_meta()
        assert restored is not None
        assert restored.session_id == "test_session"
        assert len(store.read_view()) == 1  # message list unaffected

    def test_session_meta_in_transcript_file(self, tmp_path):
        """End-to-end: transcript file has meta as first line."""
        from helen.runtime.transcript_store import (
            TranscriptStore, JSONLBackend, SessionMeta, Message,
        )
        import json
        path = tmp_path / "transcript.jsonl"
        backend = JSONLBackend(path)
        store = TranscriptStore(backend=backend)

        meta = SessionMeta(argv=["helen", "app.helen", "--mode", "test"])
        store.write_meta(meta)
        store.append(Message(role="user", content="hello"))

        # Read raw file and verify first line
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["type"] == "session_meta"
        assert first["argv"] == ["helen", "app.helen", "--mode", "test"]

        second = json.loads(lines[1])
        assert second["type"] == "message"
        assert second["role"] == "user"


class TestRestoreMediaPreservesFields:
    """Regression test for issue #19.

    _restore_media_in_messages() must preserve ALL Message fields
    (pinned, invocation_id, parent_invocation_id, agent_name,
    visible_to_invocation_ids) when reconstructing multimodal messages.
    Otherwise agent-internal llm act with media() silently loses context.
    """

    def test_restore_preserves_invocation_tree_fields(self, tmp_path):
        from helen.runtime.transcript_store import TranscriptStore
        from helen.runtime.media_storage import MediaStorage

        store = TranscriptStore()
        store._media_storage = MediaStorage(tmp_path, threshold_mb=0.0)  # always externalize

        msg = Message(
            role="user",
            content=[
                {"type": "text", "text": "look at this"},
                {"type": "media_ref", "media_ref": "does_not_exist",
                 "mime": "image/png", "media_type": "image"},
            ],
            agent_name="TestAgent",
            invocation_id="inv_abc",
            parent_invocation_id="inv_parent",
            visible_to_invocation_ids=["inv_other"],
            pinned=True,
        )

        # Direct call to the private method under test
        restored = store._restore_media_in_messages([msg])

        assert len(restored) == 1
        out = restored[0]
        # v1.19 pinned
        assert out.pinned is True
        # v1.22 invocation tree
        assert out.agent_name == "TestAgent"
        assert out.invocation_id == "inv_abc"
        assert out.parent_invocation_id == "inv_parent"
        # v1.24 visibility
        assert out.visible_to_invocation_ids == ["inv_other"]
        # mutation safety: list field must be a copy, not shared
        out.visible_to_invocation_ids.append("mutated")
        assert msg.visible_to_invocation_ids == ["inv_other"]

    def test_plain_text_messages_pass_through_unchanged(self, tmp_path):
        """Non-multimodal messages should not be touched (existing behaviour)."""
        from helen.runtime.transcript_store import TranscriptStore
        from helen.runtime.media_storage import MediaStorage

        store = TranscriptStore()
        store._media_storage = MediaStorage(tmp_path, threshold_mb=0.0)

        msg = Message(
            role="user",
            content="plain text",
            invocation_id="inv_xyz",
        )
        restored = store._restore_media_in_messages([msg])
        assert len(restored) == 1
        assert restored[0] is msg  # same instance, not a copy
