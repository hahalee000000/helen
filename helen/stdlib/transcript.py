"""Transcript stdlib functions for Helen.

Provides access to transcript session management and replay capabilities:
- get_session_id(): Get current transcript session ID
- list_sessions(): List all transcript sessions
- replay_transcript(): Replay transcript messages
- export_transcript(): Export transcript to file
- get_compression_audit(): Get compression event history

These functions are registered as stdlib built-ins and can be called
from Helen programs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Global reference to interpreter's agent context (set by interpreter)
_interpreter_agent_context = None


def _set_transcript_context(agent_context: Any) -> None:
    """Set the interpreter's agent context for transcript management.

    Called by the interpreter during initialization to provide stdlib functions
    with access to the transcript store.

    Args:
        agent_context: The interpreter's AgentContextManager instance
    """
    global _interpreter_agent_context
    _interpreter_agent_context = agent_context


def get_session_id() -> str:
    """Get current transcript session ID.

    Returns:
        Current session ID, or empty string if TranscriptStore is not enabled.

    Example:
        let session = get_session_id()
        print("Session: {session}")
    """
    if _interpreter_agent_context is None:
        return ""

    session_id = getattr(_interpreter_agent_context, "session_id", None)
    if session_id is None:
        return ""

    return session_id


def list_sessions() -> list[dict[str, Any]]:
    """List all transcript sessions.

    Returns:
        List of session metadata dicts, sorted by modification time (newest first).
        Each dict contains:
        - session_id: Session identifier
        - created_at: Creation timestamp (Unix epoch)
        - modified_at: Last modification timestamp (Unix epoch)
        - size_bytes: Transcript file size in bytes
        - message_count: Number of messages (line count estimate)

    Example:
        let sessions = list_sessions()
        for session in sessions {
            print("{session.session_id}: {session.size_bytes} bytes")
        }
    """
    from helen.runtime.config import get_transcript_config
    from helen.runtime.session_manager import SessionManager

    config = get_transcript_config()
    session_dir = config.get("session_dir")
    manager = SessionManager(base_dir=session_dir)
    return manager.list_sessions()


def replay_transcript(
    session_id: str | None = None,
    include_compressed: bool = False,
) -> list[dict[str, Any]]:
    """Replay transcript messages.

    Args:
        session_id: Session to replay. If None, uses current session.
        include_compressed: If True, includes compressed messages.
                           If False, returns only the current effective view.

    Returns:
        List of message dicts with keys:
        - role: Message role (user/assistant/system/tool)
        - content: Message content
        - uuid: Message UUID
        - timestamp: When the message was added

    Example:
        // Get current session transcript
        let messages = replay_transcript()

        // Get specific session with compressed messages
        let full = replay_transcript("session_123", true)
    """
    from helen.runtime.transcript_store import BoundaryMarker, Message

    if _interpreter_agent_context is None:
        return []

    store = getattr(_interpreter_agent_context, "transcript_store", None)
    if store is None:
        return []

    # If session_id is specified and different from current, load that session
    current_session_id = getattr(_interpreter_agent_context, "session_id", None)
    if session_id is not None and session_id != current_session_id:
        from helen.runtime.config import get_transcript_config
        from helen.runtime.session_manager import SessionManager
        from helen.runtime.transcript_store import JSONLBackend, TranscriptStore

        config = get_transcript_config()
        session_dir = config.get("session_dir")
        manager = SessionManager(base_dir=session_dir)

        if not manager.session_exists(session_id):
            logger.warning("Session does not exist: %s", session_id)
            return []

        transcript_path = manager.get_session_path(session_id)
        backend = JSONLBackend(transcript_path)
        store = TranscriptStore.load_from_backend(backend)

    # Get messages
    if include_compressed:
        # Return all messages and boundaries from transcript
        items = []
        for item in store.transcript:
            if isinstance(item, Message):
                items.append({
                    "type": "message",
                    "role": item.role,
                    "content": item.content,
                    "uuid": item.uuid,
                    "message_type": item.message_type,
                })
            elif isinstance(item, BoundaryMarker):
                items.append({
                    "type": "boundary",
                    "uuid": item.uuid,
                    "layer": item.layer,
                    "summary": item.summary,
                    "head_uuid": item.head_uuid,
                    "tail_uuid": item.tail_uuid,
                })
        return items
    else:
        # Return current effective view (with compression applied)
        view = store.read_view()
        return [
            {
                "type": "message",
                "role": msg.role,
                "content": msg.content,
                "uuid": msg.uuid,
                "message_type": msg.message_type,
            }
            for msg in view
        ]


def export_transcript(
    output_path: str,
    format: str = "json",
    session_id: str | None = None,
) -> str:
    """Export transcript to file.

    Args:
        output_path: Path to output file
        format: Export format: "json", "markdown", or "text"
        session_id: Session to export. If None, uses current session.

    Returns:
        The output_path on success, empty string on failure.

    Example:
        export_transcript("transcript.json", "json")
        export_transcript("transcript.md", "markdown")
    """
    messages = replay_transcript(session_id=session_id, include_compressed=False)

    if not messages:
        logger.warning("No messages to export")
        return ""

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)

        elif format == "markdown":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("# Transcript Export\n\n")
                for msg in messages:
                    if msg.get("type") == "message":
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        f.write(f"## {role.title()}\n\n")
                        f.write(f"{content}\n\n")
                        f.write("---\n\n")

        elif format == "text":
            with open(output_file, "w", encoding="utf-8") as f:
                for msg in messages:
                    if msg.get("type") == "message":
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        f.write(f"[{role}] {content}\n")

        else:
            logger.error("Unknown export format: %s", format)
            return ""

        logger.info("Exported transcript to %s", output_path)
        return str(output_file)

    except OSError as e:
        logger.error("Failed to export transcript to %s: %s", output_path, e)
        return ""


def get_compression_audit() -> list[dict[str, Any]]:
    """Get audit trail of all compression events.

    Returns:
        List of compression event dicts with keys:
        - uuid: Boundary marker UUID
        - layer: Compression layer name
        - head_uuid: First compressed message UUID
        - tail_uuid: Last compressed message UUID
        - anchor_uuid: Anchor message UUID
        - summary: Compression summary text
        - original_token_count: Tokens before compression
        - compressed_token_count: Tokens after compression
        - timestamp: When compression occurred

    Example:
        let audit = get_compression_audit()
        for event in audit {
            print("{event.layer}: {event.original_token_count} -> {event.compressed_token_count}")
        }
    """
    if _interpreter_agent_context is None:
        return []

    store = getattr(_interpreter_agent_context, "transcript_store", None)
    if store is None:
        return []

    return store.get_compression_audit()


# Register stdlib functions
def register_transcript_functions(register_func):
    """Register transcript stdlib functions.

    Args:
        register_func: Function to register a stdlib function
    """
    register_func("get_session_id", get_session_id)
    register_func("list_sessions", list_sessions)
    register_func("replay_transcript", replay_transcript)
    register_func("export_transcript", export_transcript)
    register_func("get_compression_audit", get_compression_audit)
