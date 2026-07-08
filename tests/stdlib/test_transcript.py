"""Tests for transcript stdlib functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helen.stdlib.transcript import (
    export_transcript,
    get_compression_audit,
    get_session_id,
    list_sessions,
    replay_transcript,
)


class TestTranscriptStdlib:
    """Test transcript stdlib functions."""

    def test_get_session_id_no_interpreter(self):
        """Test get_session_id with no active interpreter."""
        # Should return empty string when no interpreter
        result = get_session_id()
        assert result == ""

    def test_list_sessions_empty(self, tmp_path):
        """Test list_sessions with no sessions."""
        # This will use the default session directory
        # We can't easily test this without mocking, so just verify it doesn't crash
        sessions = list_sessions()
        assert isinstance(sessions, list)

    def test_replay_transcript_no_interpreter(self):
        """Test replay_transcript with no active interpreter."""
        # Should return empty list when no interpreter
        result = replay_transcript()
        assert result == []

    def test_get_compression_audit_no_interpreter(self):
        """Test get_compression_audit with no active interpreter."""
        # Should return empty list when no interpreter
        result = get_compression_audit()
        assert result == []

    def test_export_transcript_empty(self, tmp_path):
        """Test export_transcript with no messages."""
        output_path = tmp_path / "export.json"
        result = export_transcript(str(output_path), format="json")
        # Should return empty string when no messages
        assert result == ""

    def test_export_transcript_json_format(self, tmp_path):
        """Test export_transcript in JSON format."""
        output_path = tmp_path / "export.json"

        # Create some mock data by directly writing to the export function
        # (In real usage, this would come from the interpreter)
        messages = [
            {"type": "message", "role": "user", "content": "Hello", "uuid": "msg1"},
            {"type": "message", "role": "assistant", "content": "Hi", "uuid": "msg2"},
        ]

        # Mock the replay_transcript function to return our test data
        import helen.stdlib.transcript as transcript_module
        original_replay = transcript_module.replay_transcript

        def mock_replay(*args, **kwargs):
            return messages

        transcript_module.replay_transcript = mock_replay

        try:
            result = export_transcript(str(output_path), format="json")
            assert result == str(output_path)
            assert output_path.exists()

            # Verify JSON content
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) == 2
            assert data[0]["role"] == "user"
            assert data[1]["role"] == "assistant"
        finally:
            # Restore original function
            transcript_module.replay_transcript = original_replay

    def test_export_transcript_markdown_format(self, tmp_path):
        """Test export_transcript in Markdown format."""
        output_path = tmp_path / "export.md"

        messages = [
            {"type": "message", "role": "user", "content": "Hello", "uuid": "msg1"},
            {"type": "message", "role": "assistant", "content": "Hi there", "uuid": "msg2"},
        ]

        import helen.stdlib.transcript as transcript_module
        original_replay = transcript_module.replay_transcript

        def mock_replay(*args, **kwargs):
            return messages

        transcript_module.replay_transcript = mock_replay

        try:
            result = export_transcript(str(output_path), format="markdown")
            assert result == str(output_path)
            assert output_path.exists()

            # Verify Markdown content
            content = output_path.read_text(encoding="utf-8")
            assert "# Transcript Export" in content
            assert "## User" in content
            assert "## Assistant" in content
            assert "Hello" in content
            assert "Hi there" in content
        finally:
            transcript_module.replay_transcript = original_replay

    def test_export_transcript_text_format(self, tmp_path):
        """Test export_transcript in plain text format."""
        output_path = tmp_path / "export.txt"

        messages = [
            {"type": "message", "role": "user", "content": "Hello", "uuid": "msg1"},
            {"type": "message", "role": "assistant", "content": "Hi", "uuid": "msg2"},
        ]

        import helen.stdlib.transcript as transcript_module
        original_replay = transcript_module.replay_transcript

        def mock_replay(*args, **kwargs):
            return messages

        transcript_module.replay_transcript = mock_replay

        try:
            result = export_transcript(str(output_path), format="text")
            assert result == str(output_path)
            assert output_path.exists()

            # Verify text content
            content = output_path.read_text(encoding="utf-8")
            assert "[user] Hello" in content
            assert "[assistant] Hi" in content
        finally:
            transcript_module.replay_transcript = original_replay

    def test_export_transcript_invalid_format(self, tmp_path):
        """Test export_transcript with invalid format."""
        output_path = tmp_path / "export.xyz"

        messages = [
            {"type": "message", "role": "user", "content": "Hello", "uuid": "msg1"},
        ]

        import helen.stdlib.transcript as transcript_module
        original_replay = transcript_module.replay_transcript

        def mock_replay(*args, **kwargs):
            return messages

        transcript_module.replay_transcript = mock_replay

        try:
            result = export_transcript(str(output_path), format="invalid")
            assert result == ""  # Should return empty string on error
        finally:
            transcript_module.replay_transcript = original_replay
