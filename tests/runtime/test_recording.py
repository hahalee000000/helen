"""Tests for LLM recording and replay functionality (Phase 4).

Tests the CassetteWriter, CassetteReader, ReplayLLMRuntime, and
RecordingLLMRuntimeWrapper classes.
"""

import pytest
import tempfile
import json
from pathlib import Path
from helen.runtime.recording import (
    CassetteWriter,
    CassetteReader,
    CassetteEntry,
    ReplayLLMRuntime,
)
from helen.runtime.llm_runtime import LLMResponse


class TestCassetteEntry:
    """Test CassetteEntry dataclass."""

    def test_cassette_entry_to_dict(self):
        """Test CassetteEntry serialization."""
        entry = CassetteEntry(
            seq=0,
            timestamp=1234567890.0,
            agent_name="TestAgent",
            model="test-model",
            request={"prompt": "test"},
            response={"content": "response"},
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            duration_ms=100.0,
        )
        d = entry.to_dict()
        assert d["type"] == "llm_call"
        assert d["seq"] == 0
        assert d["agent_name"] == "TestAgent"
        assert d["model"] == "test-model"

    def test_cassette_entry_from_dict(self):
        """Test CassetteEntry deserialization."""
        d = {
            "type": "llm_call",
            "seq": 1,
            "timestamp": 1234567890.0,
            "agent_name": "TestAgent",
            "model": "test-model",
            "request": {"prompt": "test"},
            "response": {"content": "response"},
            "usage": {"prompt_tokens": 10},
            "duration_ms": 100.0,
        }
        entry = CassetteEntry.from_dict(d)
        assert entry.seq == 1
        assert entry.agent_name == "TestAgent"
        assert entry.model == "test-model"


class TestCassetteWriter:
    """Test CassetteWriter."""

    def test_write_single_entry(self):
        """Test writing a single entry to cassette."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"
            writer = CassetteWriter(cassette_path)

            writer.write_entry(
                messages=[{"role": "user", "content": "test"}],
                payload={"prompt": "test"},
                response={"content": "response"},
                usage={"prompt_tokens": 10},
                duration_ms=100.0,
                agent_name="TestAgent",
                model="test-model",
            )

            # Verify file was created
            assert cassette_path.exists()

            # Verify content
            with open(cassette_path) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["type"] == "llm_call"
                assert data["seq"] == 0
                assert data["agent_name"] == "TestAgent"

    def test_write_multiple_entries(self):
        """Test writing multiple entries to cassette."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"
            writer = CassetteWriter(cassette_path)

            for i in range(3):
                writer.write_entry(
                    messages=[{"role": "user", "content": f"test{i}"}],
                    payload={"prompt": f"test{i}"},
                    response={"content": f"response{i}"},
                    usage={},
                    duration_ms=100.0,
                )

            # Verify 3 lines were written
            with open(cassette_path) as f:
                lines = f.readlines()
                assert len(lines) == 3

    def test_context_manager(self):
        """Test using CassetteWriter as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"

            with CassetteWriter(cassette_path) as writer:
                writer.write_entry(
                    messages=[],
                    payload={},
                    response={},
                    usage={},
                    duration_ms=100.0,
                )

            # File should be closed after context manager exits
            assert cassette_path.exists()


class TestCassetteReader:
    """Test CassetteReader."""

    def test_read_empty_cassette(self):
        """Test reading from non-existent cassette."""
        reader = CassetteReader("/nonexistent/path.jsonl")
        assert len(reader) == 0

    def test_read_single_entry(self):
        """Test reading a single entry from cassette."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"

            # Write an entry
            writer = CassetteWriter(cassette_path)
            writer.write_entry(
                messages=[{"role": "user", "content": "test"}],
                payload={"prompt": "test"},
                response={"content": "response"},
                usage={"prompt_tokens": 10},
                duration_ms=100.0,
                agent_name="TestAgent",
                model="test-model",
            )

            # Read it back
            reader = CassetteReader(cassette_path)
            assert len(reader) == 1

            entry = reader.get_entry(0)
            assert entry is not None
            assert entry.agent_name == "TestAgent"
            assert entry.model == "test-model"

    def test_read_multiple_entries(self):
        """Test reading multiple entries from cassette."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"

            # Write 3 entries
            writer = CassetteWriter(cassette_path)
            for i in range(3):
                writer.write_entry(
                    messages=[],
                    payload={"prompt": f"test{i}"},
                    response={"content": f"response{i}"},
                    usage={},
                    duration_ms=100.0,
                )

            # Read them back
            reader = CassetteReader(cassette_path)
            assert len(reader) == 3

            # Test get_next_entry
            entry = reader.get_next_entry(-1)
            assert entry.seq == 0

            entry = reader.get_next_entry(0)
            assert entry.seq == 1

            entry = reader.get_next_entry(1)
            assert entry.seq == 2

            entry = reader.get_next_entry(2)
            assert entry is None

    def test_iterate_entries(self):
        """Test iterating over cassette entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"

            # Write 3 entries
            writer = CassetteWriter(cassette_path)
            for i in range(3):
                writer.write_entry(
                    messages=[],
                    payload={"prompt": f"test{i}"},
                    response={"content": f"response{i}"},
                    usage={},
                    duration_ms=100.0,
                )

            # Iterate
            reader = CassetteReader(cassette_path)
            entries = list(reader)
            assert len(entries) == 3
            assert entries[0].seq == 0
            assert entries[2].seq == 2


class TestReplayLLMRuntime:
    """Test ReplayLLMRuntime."""

    def test_replay_single_interaction(self):
        """Test replaying a single LLM interaction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"

            # Create cassette with one interaction
            writer = CassetteWriter(cassette_path)
            writer.write_entry(
                messages=[{"role": "user", "content": "test"}],
                payload={"prompt": "test"},
                response={"content": "recorded response"},
                usage={"prompt_tokens": 10, "completion_tokens": 20},
                duration_ms=100.0,
            )

            # Replay
            runtime = ReplayLLMRuntime(cassette_path)
            response = runtime.act("different prompt")

            assert isinstance(response, LLMResponse)
            assert response.text == "recorded response"

    def test_replay_multiple_interactions(self):
        """Test replaying multiple LLM interactions in sequence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"

            # Create cassette with 3 interactions
            writer = CassetteWriter(cassette_path)
            for i in range(3):
                writer.write_entry(
                    messages=[],
                    payload={},
                    response={"content": f"response{i}"},
                    usage={},
                    duration_ms=100.0,
                )

            # Replay in sequence
            runtime = ReplayLLMRuntime(cassette_path)

            response0 = runtime.act("prompt0")
            assert response0.text == "response0"

            response1 = runtime.act("prompt1")
            assert response1.text == "response1"

            response2 = runtime.act("prompt2")
            assert response2.text == "response2"

    def test_replay_exhausted(self):
        """Test error when trying to replay more interactions than recorded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"

            # Create cassette with one interaction
            writer = CassetteWriter(cassette_path)
            writer.write_entry(
                messages=[],
                payload={},
                response={"content": "response"},
                usage={},
                duration_ms=100.0,
            )

            # Replay
            runtime = ReplayLLMRuntime(cassette_path)
            runtime.act("prompt")

            # Try to replay again - should raise error
            with pytest.raises(RuntimeError, match="No more recorded interactions"):
                runtime.act("another prompt")

    def test_replay_route_not_supported(self):
        """Test that route() is not supported in replay mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cassette_path = Path(tmpdir) / "test.jsonl"

            # Create empty cassette
            writer = CassetteWriter(cassette_path)

            runtime = ReplayLLMRuntime(cassette_path)

            with pytest.raises(NotImplementedError, match="does not support route"):
                runtime.route("prompt", ["option1", "option2"])
