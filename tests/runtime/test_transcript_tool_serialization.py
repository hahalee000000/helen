"""Tests for v1.46.2 tool_calls/tool_call_id serialization fix.

Verifies that user messages don't include empty tool_calls or null tool_call_id
in the serialized JSONL format, which would cause OpenAI API 400 errors.
"""

import json
import tempfile
from pathlib import Path

from helen.runtime.transcript_store import TranscriptStore, JSONLBackend, Message


def test_user_message_serialization():
    """User messages should not include tool_calls or tool_call_id fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_path = Path(tmpdir) / "test_session"
        session_path.mkdir()
        backend = JSONLBackend(session_path / "transcript.jsonl")
        store = TranscriptStore(backend=backend)

        # Create a user message (no tool_calls)
        user_msg = Message(
            role="user",
            content="Hello",
            tool_calls=[],
            tool_call_id=None,
        )

        # Append to transcript
        store.append(user_msg)

        # Read the JSONL file
        jsonl_path = session_path / "transcript.jsonl"
        with open(jsonl_path) as f:
            lines = f.readlines()

        # Parse the message line (skip metadata line)
        msg_line = [l for l in lines if l.strip() and '"type"' in l and '"message"' in l][0]
        msg_data = json.loads(msg_line)

        # User message should NOT have tool_calls or tool_call_id fields
        assert "tool_calls" not in msg_data, \
            f"User message should not have tool_calls field, got: {msg_data}"
        assert "tool_call_id" not in msg_data, \
            f"User message should not have tool_call_id field, got: {msg_data}"


def test_assistant_message_with_tool_calls():
    """Assistant messages with tool_calls should include the field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_path = Path(tmpdir) / "test_session"
        session_path.mkdir()
        backend = JSONLBackend(session_path / "transcript.jsonl")
        store = TranscriptStore(backend=backend)

        # Create an assistant message with tool_calls
        assistant_msg = Message(
            role="assistant",
            content="",
            tool_calls=[{
                "id": "call_123",
                "type": "function",
                "function": {"name": "read_file", "arguments": "{}"}
            }],
            tool_call_id=None,
        )

        store.append(assistant_msg)

        # Read the JSONL file
        jsonl_path = session_path / "transcript.jsonl"
        with open(jsonl_path) as f:
            lines = f.readlines()

        msg_line = [l for l in lines if l.strip() and '"type"' in l and '"message"' in l][0]
        msg_data = json.loads(msg_line)

        # Assistant message with tool_calls SHOULD have the field
        assert "tool_calls" in msg_data, \
            f"Assistant message with tool_calls should have tool_calls field"
        assert len(msg_data["tool_calls"]) == 1
        assert msg_data["tool_calls"][0]["id"] == "call_123"

        # But should NOT have tool_call_id (it's None)
        assert "tool_call_id" not in msg_data, \
            f"Assistant message should not have tool_call_id when it's None"


def test_tool_result_message():
    """Tool result messages should include tool_call_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_path = Path(tmpdir) / "test_session"
        session_path.mkdir()
        backend = JSONLBackend(session_path / "transcript.jsonl")
        store = TranscriptStore(backend=backend)

        # Create a tool result message
        tool_msg = Message(
            role="tool",
            content="File content here",
            tool_calls=[],
            tool_call_id="call_123",
        )

        store.append(tool_msg)

        # Read the JSONL file
        jsonl_path = session_path / "transcript.jsonl"
        with open(jsonl_path) as f:
            lines = f.readlines()

        msg_line = [l for l in lines if l.strip() and '"type"' in l and '"message"' in l][0]
        msg_data = json.loads(msg_line)

        # Tool message SHOULD have tool_call_id
        assert "tool_call_id" in msg_data, \
            f"Tool message should have tool_call_id field"
        assert msg_data["tool_call_id"] == "call_123"

        # But should NOT have tool_calls (it's empty)
        assert "tool_calls" not in msg_data, \
            f"Tool message should not have tool_calls when it's empty"


def test_api_format_conversion():
    """Verify API format conversion handles all message types correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_path = Path(tmpdir) / "test_session"
        session_path.mkdir()
        backend = JSONLBackend(session_path / "transcript.jsonl")
        store = TranscriptStore(backend=backend)

        # Add various message types
        store.append(Message(role="user", content="Hello", tool_calls=[], tool_call_id=None))
        store.append(Message(
            role="assistant",
            content="",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "test", "arguments": "{}"}}],
            tool_call_id=None,
        ))
        store.append(Message(role="tool", content="Result", tool_calls=[], tool_call_id="call_1"))
        store.append(Message(role="assistant", content="Done", tool_calls=[], tool_call_id=None))

        # Get all messages and convert to API format
        messages = [m for m in store.transcript if isinstance(m, Message)]
        api_messages = []
        for msg in messages:
            api_msg = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                api_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                api_msg["tool_call_id"] = msg.tool_call_id
            api_messages.append(api_msg)

        # Verify each message
        assert len(api_messages) == 4

        # User message: no tool fields
        assert api_messages[0]["role"] == "user"
        assert "tool_calls" not in api_messages[0]
        assert "tool_call_id" not in api_messages[0]

        # Assistant with tool_calls: has tool_calls, no tool_call_id
        assert api_messages[1]["role"] == "assistant"
        assert "tool_calls" in api_messages[1]
        assert "tool_call_id" not in api_messages[1]

        # Tool result: has tool_call_id, no tool_calls
        assert api_messages[2]["role"] == "tool"
        assert "tool_call_id" in api_messages[2]
        assert "tool_calls" not in api_messages[2]

        # Final assistant: no tool fields
        assert api_messages[3]["role"] == "assistant"
        assert "tool_calls" not in api_messages[3]
        assert "tool_call_id" not in api_messages[3]
