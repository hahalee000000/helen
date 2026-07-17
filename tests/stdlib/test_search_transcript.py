"""Tests for search_transcript stdlib function.

search_transcript(query, ...) searches persistent transcripts by content.
Unlike search_context() which only searches the current active context,
search_transcript() can search across sessions and supports regex, role
filtering, and limits.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from helen.runtime.history import Message
from helen.runtime.transcript_store import TranscriptStore, JSONLBackend
from helen.stdlib.transcript import search_transcript
import helen.stdlib.transcript as transcript_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_msg(role="user", content="hello", uuid=""):
    return Message(role=role, content=content, uuid=uuid)


def _build_session(tmp_path: Path, messages: list[Message], session_id: str) -> Path:
    """Create a fake session directory with a transcript file."""
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = session_dir / "transcript.jsonl"

    store = TranscriptStore()
    for msg in messages:
        store.append(msg)

    backend = JSONLBackend(transcript_path)
    for item in store.transcript:
        backend.append(item)

    return transcript_path


def _mock_agent_context_with_messages(messages: list[Message], session_id: str = "session_test"):
    """Build a mock agent_context with an in-memory transcript_store."""
    store = TranscriptStore()
    for msg in messages:
        store.append(msg)

    agent_context = MagicMock()
    agent_context.transcript_store = store
    agent_context.session_id = session_id
    return agent_context


# ---------------------------------------------------------------------------
# Tests: basic behavior
# ---------------------------------------------------------------------------

class TestSearchTranscriptBasic:
    """Basic search behavior."""

    def teardown_method(self):
        transcript_module._interpreter_agent_context = None

    def test_empty_query_returns_empty(self):
        """Empty query should return no results."""
        result = search_transcript("")
        assert result == []

    def test_no_interpreter_returns_empty(self):
        """Without interpreter, current session search returns empty."""
        transcript_module._interpreter_agent_context = None
        result = search_transcript("anything")
        assert result == []

    def test_substring_match(self):
        """Substring search finds matching messages."""
        messages = [
            _make_msg(role="user", content="Hello world", uuid="u1"),
            _make_msg(role="assistant", content="Hi there", uuid="a1"),
            _make_msg(role="user", content="How are you today?", uuid="u2"),
        ]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("Hello")
        assert len(results) == 1
        assert results[0]["role"] == "user"
        assert results[0]["message_uuid"] == "u1"
        assert "Hello world" in results[0]["content"]
        assert results[0]["match_position"] == 0

    def test_substring_multiple_matches(self):
        """Multiple messages match the same query."""
        messages = [
            _make_msg(role="user", content="Hello world", uuid="u1"),
            _make_msg(role="assistant", content="Hello back", uuid="a1"),
            _make_msg(role="user", content="Goodbye", uuid="u2"),
        ]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("Hello")
        assert len(results) == 2
        uuids = {r["message_uuid"] for r in results}
        assert uuids == {"u1", "a1"}

    def test_case_sensitive(self):
        """Substring match is case sensitive."""
        messages = [
            _make_msg(role="user", content="Hello World", uuid="u1"),
            _make_msg(role="assistant", content="hello world", uuid="a1"),
        ]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("Hello")
        assert len(results) == 1
        assert results[0]["message_uuid"] == "u1"

    def test_no_match(self):
        """No matches returns empty list."""
        messages = [
            _make_msg(role="user", content="Hello", uuid="u1"),
        ]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("xyz")
        assert results == []


# ---------------------------------------------------------------------------
# Tests: regex
# ---------------------------------------------------------------------------

class TestSearchTranscriptRegex:
    """Regex search behavior."""

    def teardown_method(self):
        transcript_module._interpreter_agent_context = None

    def test_regex_match(self):
        """Regex search works."""
        messages = [
            _make_msg(role="user", content="fix bug 123", uuid="u1"),
            _make_msg(role="user", content="fix feature xyz", uuid="u2"),
            _make_msg(role="user", content="no changes here", uuid="u3"),
        ]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("fix.*\\d+", regex=True)
        assert len(results) == 1
        assert results[0]["message_uuid"] == "u1"

    def test_invalid_regex_returns_empty(self):
        """Invalid regex pattern returns empty results (no crash)."""
        messages = [_make_msg(role="user", content="Hello", uuid="u1")]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("[invalid", regex=True)
        assert results == []


# ---------------------------------------------------------------------------
# Tests: role filtering
# ---------------------------------------------------------------------------

class TestSearchTranscriptRole:
    """Role filtering."""

    def teardown_method(self):
        transcript_module._interpreter_agent_context = None

    def test_filter_by_role(self):
        """Role filter restricts to matching messages."""
        messages = [
            _make_msg(role="user", content="TODO fix auth", uuid="u1"),
            _make_msg(role="assistant", content="TODO noted", uuid="a1"),
            _make_msg(role="user", content="TODO write tests", uuid="u2"),
        ]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("TODO", role="user")
        assert len(results) == 2
        assert all(r["role"] == "user" for r in results)

    def test_role_filter_no_match(self):
        """Role filter with no matches returns empty."""
        messages = [
            _make_msg(role="assistant", content="TODO", uuid="a1"),
        ]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("TODO", role="user")
        assert results == []


# ---------------------------------------------------------------------------
# Tests: limit
# ---------------------------------------------------------------------------

class TestSearchTranscriptLimit:
    """Limit behavior."""

    def teardown_method(self):
        transcript_module._interpreter_agent_context = None

    def test_limit_respected(self):
        """Limit parameter caps results."""
        messages = [_make_msg(role="user", content=f"TODO item {i}", uuid=f"u{i}")
                    for i in range(20)]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("TODO", limit=5)
        assert len(results) == 5


# ---------------------------------------------------------------------------
# Tests: snippet generation
# ---------------------------------------------------------------------------

class TestSearchTranscriptSnippet:
    """Snippet generation."""

    def teardown_method(self):
        transcript_module._interpreter_agent_context = None

    def test_snippet_contains_match(self):
        """Snippet should contain the matched content."""
        messages = [
            _make_msg(role="user", content="A " * 100 + "TARGET" + " B " * 100, uuid="u1"),
        ]
        transcript_module._interpreter_agent_context = _mock_agent_context_with_messages(messages)

        results = search_transcript("TARGET")
        assert len(results) == 1
        assert "TARGET" in results[0]["snippet"]
        assert results[0]["match_position"] > 0


# ---------------------------------------------------------------------------
# Tests: cross-session (scope="all")
# ---------------------------------------------------------------------------

class TestSearchTranscriptCrossSession:
    """Cross-session search (scope='all')."""

    def teardown_method(self):
        transcript_module._interpreter_agent_context = None

    def test_scope_all_searches_multiple_sessions(self, tmp_path, monkeypatch):
        """scope='all' searches across multiple session directories."""
        # Create two sessions with different content
        messages1 = [
            _make_msg(role="user", content="auth bug in module A", uuid="u1"),
        ]
        messages2 = [
            _make_msg(role="user", content="auth bug in module B", uuid="u2"),
        ]
        _build_session(tmp_path, messages1, "session_1")
        _build_session(tmp_path, messages2, "session_2")

        def fake_resolve(scope=""):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )
        # Remove in-memory interpreter context to force disk search
        transcript_module._interpreter_agent_context = None

        results = search_transcript("auth bug", scope="all")
        assert len(results) == 2
        session_ids = {r["session_id"] for r in results}
        assert session_ids == {"session_1", "session_2"}

    def test_specific_session_id(self, tmp_path, monkeypatch):
        """Specifying session_id restricts search to that session."""
        messages1 = [_make_msg(role="user", content="auth bug", uuid="u1")]
        messages2 = [_make_msg(role="user", content="auth bug", uuid="u2")]
        _build_session(tmp_path, messages1, "session_A")
        _build_session(tmp_path, messages2, "session_B")

        def fake_resolve(scope=""):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )
        transcript_module._interpreter_agent_context = None

        results = search_transcript("auth bug", session_id="session_A", scope="all")
        assert len(results) == 1
        assert results[0]["session_id"] == "session_A"


# ---------------------------------------------------------------------------
# Tests: multimodal content
# ---------------------------------------------------------------------------

class TestSearchTranscriptMultimodal:
    """Multimodal content handling."""

    def teardown_method(self):
        transcript_module._interpreter_agent_context = None

    def test_multimodal_content_flattened(self):
        """Multimodal content (list) is flattened to text for search."""
        msg = Message(
            role="user",
            content=[
                {"type": "text", "text": "Hello world"},
                {"type": "image", "data": "..."},
            ],
            uuid="u1",
        )
        store = TranscriptStore()
        store.append(msg)

        agent_context = MagicMock()
        agent_context.transcript_store = store
        agent_context.session_id = "session_test"
        transcript_module._interpreter_agent_context = agent_context

        results = search_transcript("Hello")
        assert len(results) == 1
        assert "Hello world" in results[0]["content"]
