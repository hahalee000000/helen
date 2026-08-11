"""Transcript query stdlib functions for Helen.

Provides incremental transcript querying capabilities with filtering
and pagination. Designed for AI-native debugging (Phase 3).

Usage in Helen:
    import std.debug.*

    # Query messages by role
    let msgs = query_transcript(role="assistant")

    # Query by agent name
    let agent_msgs = query_transcript(agent="Reviewer")

    # Query with multiple filters
    let filtered = query_transcript(
        role="assistant",
        agent="Coder",
        limit=100
    )

    # Query with pagination
    let page1 = query_transcript(limit=50, offset=0)
    let page2 = query_transcript(limit=50, offset=50)
"""

from __future__ import annotations

from typing import Any


def query_transcript(
    session_id: str = "",
    role: str = "",
    agent: str = "",
    invocation_id: str = "",
    since: float = 0.0,
    until: float = 0.0,
    content_regex: str = "",
    message_type: str = "",
    limit: int = 1000,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query transcript messages with filtering and pagination.

    v1.40: Added for incremental transcript queries (Phase 3).

    Returns a list of message dictionaries matching the filters.
    Each message dict contains: uuid, role, content, agent_name,
    invocation_id, timestamp, and other message fields.

    Args:
        session_id: Session ID to query (empty = current session)
        role: Filter by message role (e.g., "user", "assistant", "tool")
        agent: Filter by agent name
        invocation_id: Filter by invocation ID
        since: Filter by timestamp >= since (Unix timestamp)
        until: Filter by timestamp <= until (Unix timestamp)
        content_regex: Filter by content matching regex pattern
        message_type: Filter by message type
        limit: Maximum number of results to return (default: 1000)
        offset: Number of results to skip for pagination (default: 0)

    Returns:
        List of message dictionaries matching the filters.
        Returns empty list if no messages match or if session not found.

    Example:
        # Get last 10 assistant messages
        let recent = query_transcript(role="assistant", limit=10)

        # Get messages from specific agent
        let coder_msgs = query_transcript(agent="Coder")

        # Paginate through all messages
        let page1 = query_transcript(limit=100, offset=0)
        let page2 = query_transcript(limit=100, offset=100)
    """
    from helen.stdlib.context_helpers import get_interpreter
    from helen.runtime.session_manager import SessionManager
    from helen.runtime.transcript_store import JSONLBackend, SQLiteBackend
    from pathlib import Path
    import os

    interp = get_interpreter()

    # Determine which session to query
    if session_id:
        # Query a specific session (may not be current)
        # Try to load from disk
        session_manager = SessionManager()
        session_path = session_manager.get_session_path(session_id)

        if not session_path.exists():
            return []

        # Try SQLite first, then JSONL
        sqlite_path = Path(str(session_path) + ".db")
        if sqlite_path.exists():
            backend = SQLiteBackend(sqlite_path)
        else:
            backend = JSONLBackend(session_path)

        try:
            from helen.runtime.transcript_store import TranscriptStore
            store = TranscriptStore.load_from_backend(backend, max_memory_items=100_000)
        except Exception:
            return []

    elif interp and hasattr(interp, 'agent_context') and interp.agent_context:
        # Query current session
        store = interp.agent_context.transcript_store
        if store is None:
            return []
    else:
        return []

    # Build filter lists
    roles = [role] if role else None
    agent_names = [agent] if agent else None
    invocation_ids = [invocation_id] if invocation_id else None
    message_types = [message_type] if message_type else None

    # Convert 0.0 to None for since/until
    since_val = since if since > 0 else None
    until_val = until if until > 0 else None

    # Execute query
    messages = store.query(
        roles=roles,
        agent_names=agent_names,
        invocation_ids=invocation_ids,
        since=since_val,
        until=until_val,
        content_regex=content_regex if content_regex else None,
        message_types=message_types,
        limit=limit,
        offset=offset,
    )

    # Convert Message objects to dicts
    result = []
    for msg in messages:
        msg_dict = {
            "uuid": msg.uuid,
            "role": msg.role,
            "content": msg.content if isinstance(msg.content, str) else str(msg.content),
            "timestamp": msg.timestamp,
            "agent_name": msg.agent_name or "",
            "invocation_id": msg.invocation_id or "",
            "parent_invocation_id": msg.parent_invocation_id or "",
            "message_type": msg.message_type or "",
            "tool_calls": msg.tool_calls or [],
            "tool_call_id": msg.tool_call_id or "",
            "pinned": msg.pinned,
            "compressed": msg.compressed,
        }
        result.append(msg_dict)

    # Clean up backend if we created one
    if session_id:
        try:
            backend.close()
        except Exception:
            pass

    return result
