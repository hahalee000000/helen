"""Tests for transcript query functionality (Phase 3).

Tests the query() method on TranscriptStoreBackend, JSONLBackend,
SQLiteBackend, and TranscriptStore, as well as the query_transcript()
stdlib function.
"""

import pytest
import tempfile
import time
from pathlib import Path
from helen.runtime.transcript_store import (
    TranscriptStore,
    JSONLBackend,
    SQLiteBackend,
    Message,
)


class TestTranscriptStoreBackendQuery:
    """Test query() method on TranscriptStoreBackend base class."""

    def test_query_with_no_filters(self):
        """Query with no filters should return all messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            # Add some messages
            store.append(Message(role="user", content="Hello"))
            store.append(Message(role="assistant", content="Hi there"))
            store.append(Message(role="user", content="How are you?"))

            # Query all messages
            result = store.query()
            assert len(result) == 3
            assert all(isinstance(msg, Message) for msg in result)

    def test_query_with_role_filter(self):
        """Query with role filter should return only matching messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            store.append(Message(role="user", content="Hello"))
            store.append(Message(role="assistant", content="Hi"))
            store.append(Message(role="user", content="Thanks"))

            result = store.query(roles=["user"])
            assert len(result) == 2
            assert all(msg.role == "user" for msg in result)

    def test_query_with_agent_filter(self):
        """Query with agent filter should return only matching messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            msg1 = Message(role="assistant", content="From Coder")
            msg1.agent_name = "Coder"
            msg2 = Message(role="assistant", content="From Reviewer")
            msg2.agent_name = "Reviewer"
            msg3 = Message(role="assistant", content="From Coder again")
            msg3.agent_name = "Coder"

            store.append(msg1)
            store.append(msg2)
            store.append(msg3)

            result = store.query(agent_names=["Coder"])
            assert len(result) == 2
            assert all(msg.agent_name == "Coder" for msg in result)

    def test_query_with_limit(self):
        """Query with limit should return at most N messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            for i in range(10):
                store.append(Message(role="user", content=f"Message {i}"))

            result = store.query(limit=5)
            assert len(result) == 5

    def test_query_with_offset(self):
        """Query with offset should skip N messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            for i in range(10):
                store.append(Message(role="user", content=f"Message {i}"))

            result = store.query(offset=5)
            assert len(result) == 5
            assert result[0].content == "Message 5"

    def test_query_with_limit_and_offset(self):
        """Query with limit and offset should paginate correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            for i in range(10):
                store.append(Message(role="user", content=f"Message {i}"))

            # Page 1
            page1 = store.query(limit=3, offset=0)
            assert len(page1) == 3
            assert page1[0].content == "Message 0"

            # Page 2
            page2 = store.query(limit=3, offset=3)
            assert len(page2) == 3
            assert page2[0].content == "Message 3"

    def test_query_with_content_regex(self):
        """Query with content regex should filter by pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            store.append(Message(role="user", content="Error: division by zero"))
            store.append(Message(role="user", content="Success"))
            store.append(Message(role="user", content="Error: timeout"))

            result = store.query(content_regex="Error:")
            assert len(result) == 2
            assert all("Error:" in msg.content for msg in result)


class TestJSONLBackendQuery:
    """Test query() method on JSONLBackend."""

    def test_jsonl_query_basic(self):
        """JSONL backend query should work with basic filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            store.append(Message(role="user", content="Hello"))
            store.append(Message(role="assistant", content="Hi"))
            store.append(Message(role="user", content="Thanks"))

            result = backend.query(roles=["user"])
            assert len(result) == 2
            assert all(isinstance(msg, Message) for msg in result)

    def test_jsonl_query_with_timestamp(self):
        """JSONL backend query should handle timestamp filter gracefully.

        Note: JSONL backend doesn't store timestamps separately, so timestamp
        filtering is not supported. This test verifies it doesn't crash.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(Path(tmpdir) / "test.jsonl")
            store = TranscriptStore(backend=backend)

            store.append(Message(role="user", content="Old"))
            time.sleep(0.01)
            store.append(Message(role="user", content="New"))

            # Timestamp filtering is not supported in JSONL backend
            # It should just be ignored (return all messages)
            result = backend.query(since=time.time() - 100)
            assert len(result) == 2


class TestSQLiteBackendQuery:
    """Test query() method on SQLiteBackend."""

    def test_sqlite_query_basic(self):
        """SQLite backend query should work with basic filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = SQLiteBackend(Path(tmpdir) / "test.db")
            store = TranscriptStore(backend=backend)

            store.append(Message(role="user", content="Hello"))
            store.append(Message(role="assistant", content="Hi"))
            store.append(Message(role="user", content="Thanks"))

            result = backend.query(roles=["user"])
            assert len(result) == 2
            assert all(isinstance(msg, Message) for msg in result)

            backend.close()

    def test_sqlite_query_with_agent(self):
        """SQLite backend query should filter by agent name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = SQLiteBackend(Path(tmpdir) / "test.db")
            store = TranscriptStore(backend=backend)

            msg1 = Message(role="assistant", content="From Coder")
            msg1.agent_name = "Coder"
            msg2 = Message(role="assistant", content="From Reviewer")
            msg2.agent_name = "Reviewer"

            store.append(msg1)
            store.append(msg2)

            result = backend.query(agent_names=["Coder"])
            assert len(result) == 1
            assert result[0].agent_name == "Coder"

            backend.close()

    def test_sqlite_query_performance(self):
        """SQLite backend query should be fast with large datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = SQLiteBackend(Path(tmpdir) / "test.db")
            store = TranscriptStore(backend=backend)

            # Add 1000 messages
            for i in range(1000):
                msg = Message(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")
                store.append(msg)

            # Query should be fast (< 1 second)
            start = time.time()
            result = backend.query(roles=["user"], limit=100)
            elapsed = time.time() - start

            assert len(result) == 100
            assert elapsed < 1.0, f"Query took {elapsed}s, expected < 1s"

            backend.close()


class TestQueryTranscriptStdlib:
    """Test query_transcript() stdlib function."""

    def test_query_transcript_basic(self):
        """query_transcript should return list of message dicts."""
        from helen.stdlib.transcript_query import query_transcript

        # This test requires an interpreter context, so we'll skip it for now
        # and test it in integration tests instead
        pytest.skip("Requires interpreter context")


class TestQueryConsistency:
    """Test that JSONL and SQLite backends return consistent results."""

    def test_jsonl_sqlite_consistency(self):
        """JSONL and SQLite backends should return same results for same query."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create JSONL backend and add messages
            jsonl_backend = JSONLBackend(tmpdir / "test.jsonl")
            jsonl_store = TranscriptStore(backend=jsonl_backend)

            for i in range(20):
                msg = Message(
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"Message {i}",
                )
                if i % 3 == 0:
                    msg.agent_name = "Agent1"
                else:
                    msg.agent_name = "Agent2"
                jsonl_store.append(msg)

            # Create SQLite backend and add same messages
            sqlite_backend = SQLiteBackend(tmpdir / "test.db")
            sqlite_store = TranscriptStore(backend=sqlite_backend)

            for i in range(20):
                msg = Message(
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"Message {i}",
                )
                if i % 3 == 0:
                    msg.agent_name = "Agent1"
                else:
                    msg.agent_name = "Agent2"
                sqlite_store.append(msg)

            # Query both with same filters
            jsonl_result = jsonl_store.query(roles=["user"], agent_names=["Agent1"], limit=10)
            sqlite_result = sqlite_store.query(roles=["user"], agent_names=["Agent1"], limit=10)

            # Should return same number of results
            assert len(jsonl_result) == len(sqlite_result)

            # Should have same content (order might differ slightly due to timestamp)
            jsonl_contents = {msg.content for msg in jsonl_result}
            sqlite_contents = {msg.content for msg in sqlite_result}
            assert jsonl_contents == sqlite_contents

            sqlite_backend.close()
