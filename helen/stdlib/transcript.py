"""Transcript stdlib functions for Helen.

Provides access to transcript session management and replay capabilities:
- get_session_id(): Get current transcript session ID
- list_sessions(): List all transcript sessions
- replay_transcript(): Replay transcript messages
- export_transcript(): Export transcript to file
- search_transcript(): Search transcript messages by content
- get_compression_audit(): Get compression event history

These functions are registered as stdlib built-ins and can be called
from Helen programs.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Thread-local storage for the interpreter's agent context.
#
# v1.23.4 fix: Previously this was a module-level global, which meant that
# spawning a child Interpreter (in a daemon thread) would overwrite the
# main thread's agent context via _set_transcript_context(). This caused
# the main thread to see the spawned session's ID (or None) after spawn.
#
# With thread-local storage, each thread has its own agent context:
#   - Main thread: set during Interpreter.__init__ / _register_stdlib
#   - Spawned thread: set when spawned_interp._register_stdlib runs
# The two never interfere, preserving Helen's runtime isolation design.
_agent_context_local = threading.local()


def _set_transcript_context(agent_context: Any) -> None:
    """Set the interpreter's agent context for transcript management.

    Called by the interpreter during initialization to provide stdlib functions
    with access to the transcript store.

    v1.23.4: Stores in thread-local storage so concurrent Interpreters
    (e.g. spawn) don't clobber each other's context.

    Args:
        agent_context: The interpreter's AgentContextManager instance
    """
    _agent_context_local.ctx = agent_context


def _get_agent_context() -> Any:
    """Get the current thread's agent context.

    Returns:
        The AgentContextManager for the current thread, or None if not set.
    """
    return getattr(_agent_context_local, "ctx", None)


def get_session_id() -> str:
    """Get current transcript session ID.

    Returns:
        Current session ID, or empty string if TranscriptStore is not enabled.

    Example:
        let session = get_session_id()
        print("Session: {session}")
    """
    if _get_agent_context() is None:
        return ""

    session_id = getattr(_get_agent_context(), "session_id", None)
    if session_id is None:
        return ""

    return session_id


def get_session_meta(session_id: str = "") -> dict[str, Any]:
    """Get session metadata (argv, timestamp, helen version, etc.).

    v1.23.3: Returns metadata recorded at session creation. Useful for
    identifying sessions, debugging, and building audit trails.

    Args:
        session_id: Optional session ID. If empty, uses the current session.

    Returns:
        dict with session metadata, or empty dict if not available:
        {
            "status": "ok",
            "data": {
                "argv": ["helen", "program.helen"],
                "timestamp": 1720435200.123,
                "helen_version": "1.23.3",
                "python_version": "3.12.13",
                "platform": "linux-aarch64",
                "cwd": "/home/user/project",
                "session_id": "session_1720435200_a1b2c3d4",
                "session_scope": "project"
            }
        }
        Or on error/not-available: {"status": "error", "error": "..."}

    Example:
        let meta = get_session_meta()
        if meta["status"] == "ok" {
            print("Started: " + str(meta["data"]["argv"]))
            print("Helen version: " + meta["data"]["helen_version"])
        }
    """
    if _get_agent_context() is None:
        return {"status": "error", "error": "TranscriptStore not enabled"}

    store = getattr(_get_agent_context(), "transcript_store", None)
    if store is None:
        return {"status": "error", "error": "TranscriptStore not available"}

    try:
        meta = store.read_meta()
        if meta is None:
            return {"status": "error", "error": "No session metadata available (old transcript?)"}

        return {
            "status": "ok",
            "data": {
                "argv": meta.argv,
                "timestamp": meta.timestamp,
                "helen_version": meta.helen_version,
                "python_version": meta.python_version,
                "platform": meta.platform,
                "cwd": meta.cwd,
                "session_id": meta.session_id,
                "session_scope": meta.session_scope,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def list_sessions(scope: str = "") -> list[dict[str, Any]]:
    """List all transcript sessions.

    Args:
        scope: Optional scope filter — "global", "project", or "" (both).
            When empty, lists sessions from the currently resolved scope only.
            This matches the behavior of :sessions REPL command.

    Returns:
        List of session metadata dicts, sorted by modification time (newest first).
        Each dict contains:
        - session_id: Session identifier
        - created_at: Creation timestamp (Unix epoch)
        - modified_at: Last modification timestamp (Unix epoch)
        - size_bytes: Transcript file size in bytes
        - message_count: Number of messages (line count estimate)
        - scope: "global" | "project" (added in v1.20)

    Example:
        let sessions = list_sessions()
        for session in sessions {
            print("{session.session_id}: {session.size_bytes} bytes")
        }

        // List from a specific scope
        let global_sessions = list_sessions("global")
        let project_sessions = list_sessions("project")
    """
    from helen.runtime.config import resolve_session_dir, HELEN_HOME

    results = []

    if scope == "global" or scope == "":
        global_dir = resolve_session_dir(scope="global")[0]
        from helen.runtime.session_manager import SessionManager
        manager = SessionManager(base_dir=global_dir)
        for s in manager.list_sessions():
            s["scope"] = "global"
            results.append(s)

    if scope == "project":
        project_dir = resolve_session_dir(scope="project")[0]
        from helen.runtime.session_manager import SessionManager
        manager = SessionManager(base_dir=project_dir)
        for s in manager.list_sessions():
            s["scope"] = "project"
            results.append(s)

    # Default (no scope specified): only current scope, not both
    if scope == "":
        current_dir, current_scope = resolve_session_dir()
        # Filter to just current scope if we got both
        results = [s for s in results if s["scope"] == current_scope]

    # Sort by modification time (newest first)
    results.sort(key=lambda s: s.get("modified_at", 0), reverse=True)
    return results


def get_spawned_sessions(session_id: str = "") -> list[dict[str, Any]]:
    """Get all sessions spawned by the given session (v1.23.7+).

    Returns direct children (sessions whose parent_session_id matches).
    For the full tree including nested spawns, use get_invocation_tree().

    Args:
        session_id: Parent session ID. If empty, uses current session.

    Returns:
        List of spawned session metadata dicts, each containing:
        - session_id: The spawned session's ID
        - agent_name: Agent name (if available)
        - timestamp: Spawn time
        - scope: "global" | "project"

    Example:
        let children = get_spawned_sessions()
        for child in children {
            print("Spawned: {child.session_id}")
        }

        // Get full tree (including nested spawns)
        let tree = get_invocation_tree()
    """
    from helen.runtime.config import resolve_session_dir
    from helen.runtime.session_manager import SessionManager
    from helen.runtime.transcript_store import SessionMeta

    # Determine target session
    if not session_id:
        agent_ctx = _get_agent_context()
        if agent_ctx is None:
            return []
        session_id = agent_ctx.session_id
        if not session_id:
            return []

    # Search in both global and project scopes
    results = []
    for scope in ["global", "project"]:
        try:
            session_dir, _ = resolve_session_dir(scope=scope)
            manager = SessionManager(base_dir=session_dir)

            # Check all sessions for matching parent_session_id
            for session_info in manager.list_sessions():
                child_sid = session_info.get("session_id", "")
                if not child_sid:
                    continue

                # Read session meta to get parent_session_id
                try:
                    transcript_path = manager.get_session_path(child_sid)
                    if transcript_path.exists():
                        from helen.runtime.transcript_store import JSONLBackend
                        backend = JSONLBackend(transcript_path)
                        store = TranscriptStore.load_from_backend(backend)
                        meta = store.read_meta()
                        if meta and meta.parent_session_id == session_id:
                            results.append({
                                "session_id": child_sid,
                                "parent_session_id": session_id,
                                "timestamp": meta.timestamp,
                                "scope": scope,
                                "argv": meta.argv,
                            })
                except Exception:
                    # Skip sessions that can't be read
                    pass
        except Exception:
            continue

    # Sort by timestamp
    results.sort(key=lambda s: s.get("timestamp", 0))
    return results


def get_spawn_tree(session_id: str = "") -> dict[str, Any]:
    """Get the full session spawn tree including nested spawns (v1.23.7+).

    Recursively builds a tree structure showing the complete spawn hierarchy
    across different sessions. This is different from get_invocation_tree()
    which shows agent calls within a single session.

    Args:
        session_id: Root session ID. If empty, uses current session.

    Returns:
        Tree dict with structure:
        {
            "session_id": "session_abc",
            "children": [
                {
                    "session_id": "session_def",
                    "children": [...]
                },
                ...
            ]
        }

    Example:
        let tree = get_spawn_tree()
        print("Root: {tree.session_id}")
        for child in tree.children {
            print("  Spawned: {child.session_id}")
        }
    """
    from helen.runtime.config import resolve_session_dir
    from helen.runtime.session_manager import SessionManager
    from helen.runtime.transcript_store import SessionMeta, TranscriptStore

    # Determine target session
    if not session_id:
        agent_ctx = _get_agent_context()
        if agent_ctx is None:
            return {"session_id": "", "children": []}
        session_id = agent_ctx.session_id
        if not session_id:
            return {"session_id": "", "children": []}

    def build_tree(sid: str) -> dict[str, Any]:
        """Recursively build tree for session and its children."""
        node = {"session_id": sid, "children": []}

        # Find direct children
        children = get_spawned_sessions(sid)
        for child in children:
            child_tree = build_tree(child["session_id"])
            node["children"].append(child_tree)

        return node

    return build_tree(session_id)


def replay_transcript(
    session_id: str | None = None,
    include_compressed: bool = False,
    # v1.22: Invocation tree filtering
    agent: str | None = None,
    invocation_id: str | None = None,
    last_only: bool = False,
    include_subtree: bool = False,
) -> list[dict[str, Any]]:
    """Replay transcript messages, with optional filtering.

    Args:
        session_id: Session to replay. If None, uses current session.
        include_compressed: If True, includes compressed messages.
                           If False, returns only the current effective view.
        agent: Filter by agent name. None returns all agents.
        invocation_id: Filter by invocation UUID. When include_subtree=True,
                       also includes all descendant invocations.
        last_only: When agent is set, only return the agent's most recent
                   invocation (not all invocations).
        include_subtree: When invocation_id is set, also return messages from
                         all descendant invocations.

    Returns:
        List of message dicts with keys:
        - type: "message" or "boundary"
        - role: Message role (user/assistant/system/tool)
        - content: Message content
        - uuid: Message UUID
        - message_type: Auto-inferred message type
        - agent_name: Agent that produced this message (v1.22+)
        - invocation_id: Invocation UUID (v1.22+)

    Example:
        // Get current session transcript
        let messages = replay_transcript()

        // Get specific session with compressed messages
        let full = replay_transcript("session_123", true)

        // v1.22: Filter by agent
        let a_msgs = replay_transcript(agent="Researcher")

        // v1.22: Get only the agent's last run
        let last_run = replay_transcript(agent="Researcher", last_only=true)

        // v1.22: Get specific invocation (and its subtree)
        let subtree = replay_transcript(invocation_id="inv_xxx", include_subtree=true)
    """
    from helen.runtime.transcript_store import BoundaryMarker, Message

    if _get_agent_context() is None:
        return []

    store = getattr(_get_agent_context(), "transcript_store", None)
    if store is None:
        return []

    # If session_id is specified and different from current, load that session
    current_session_id = getattr(_get_agent_context(), "session_id", None)
    if session_id is not None and session_id != current_session_id:
        from helen.runtime.config import resolve_session_dir
        from helen.runtime.session_manager import SessionManager
        from helen.runtime.transcript_store import JSONLBackend, TranscriptStore

        session_dir, _scope = resolve_session_dir()
        manager = SessionManager(base_dir=session_dir)

        if not manager.session_exists(session_id):
            logger.warning("Session does not exist: %s", session_id)
            return []

        transcript_path = manager.get_session_path(session_id)
        backend = JSONLBackend(transcript_path)
        store = TranscriptStore.load_from_backend(backend)

    # v1.22: Determine the set of allowed invocation IDs based on filters
    allowed_invocations: set[str] | None = None

    if invocation_id is not None or agent is not None:
        index = _build_invocation_index(store)

        if invocation_id is not None:
            # Start with this invocation
            allowed = {invocation_id}
            if include_subtree:
                # Add all descendants
                def _add_descendants(parent_id: str) -> None:
                    if parent_id in index:
                        for child_id in index[parent_id].get("children", []):
                            allowed.add(child_id)
                            _add_descendants(child_id)
                _add_descendants(invocation_id)
            allowed_invocations = allowed

        elif agent is not None:
            # Filter by agent name
            agent_invs = [inv_id for inv_id, entry in index.items()
                          if entry.get("agent_name") == agent]
            if last_only and agent_invs:
                # Pick the most recent by first_message_time, with order as tiebreaker
                agent_invs.sort(
                    key=lambda i: (
                        index[i]["first_message_time"] if index[i]["first_message_time"] is not None else 0,
                        index[i].get("order", 0),
                    ),
                    reverse=True,
                )
                agent_invs = [agent_invs[0]]
            allowed_invocations = set(agent_invs)

    # Helper to build message dict (includes v1.22 fields)
    def _msg_dict(msg: Message) -> dict[str, Any]:
        d = {
            "type": "message",
            "role": msg.role,
            "content": msg.content,
            "uuid": msg.uuid,
            "message_type": msg.message_type,
        }
        # v1.22: Include invocation tree fields if set
        if getattr(msg, "agent_name", None) is not None:
            d["agent_name"] = msg.agent_name
        if getattr(msg, "invocation_id", ""):
            d["invocation_id"] = msg.invocation_id
        return d

    # Get messages
    if include_compressed:
        items = []
        for item in store.transcript:
            if isinstance(item, Message):
                # Apply invocation filter
                if allowed_invocations is not None:
                    inv_id = getattr(item, "invocation_id", "") or ""
                    if inv_id not in allowed_invocations:
                        continue
                items.append(_msg_dict(item))
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
        view = store.read_view()
        result = []
        for msg in view:
            if allowed_invocations is not None:
                inv_id = getattr(msg, "invocation_id", "") or ""
                if inv_id not in allowed_invocations:
                    continue
            result.append(_msg_dict(msg))
        return result


def replay_full_session(session_id: str = "") -> list[dict[str, Any]]:
    """Replay transcript from session and all spawned sessions, sorted by time (v1.23.7+).

    Aggregates messages from the root session and all its spawn children
    (recursively), returning a unified view sorted by timestamp. This provides
    a complete picture of the execution flow across all related sessions.

    Unlike replay_transcript() which only shows a single session, this function
    shows the full execution tree including spawn relationships.

    Args:
        session_id: Root session ID. If empty, uses current session.

    Returns:
        List of message dicts from all sessions, sorted by timestamp.
        Each message includes a "session_id" field indicating its origin.

    Example:
        // View complete execution flow (main + all spawns)
        let messages = replay_full_session()
        for msg in messages {
            print("[{msg.session_id}] {msg.role}: {msg.content[:50]}")
        }

        // Count messages per session
        let counts = {}
        for msg in messages {
            counts[msg.session_id] = (counts[msg.session_id] or 0) + 1
        }
    """
    # Get root session ID
    if not session_id:
        agent_ctx = _get_agent_context()
        if agent_ctx is None:
            return []
        session_id = agent_ctx.session_id
        if not session_id:
            return []

    # Collect all session IDs (root + all spawns recursively)
    all_session_ids = [session_id]

    def collect_spawns(sid):
        """Recursively collect all spawned sessions."""
        spawned = get_spawned_sessions(sid)
        for spawn_info in spawned:
            child_sid = spawn_info.get("session_id", "")
            if child_sid and child_sid not in all_session_ids:
                all_session_ids.append(child_sid)
                collect_spawns(child_sid)

    collect_spawns(session_id)

    # Aggregate messages from all sessions
    all_messages = []
    for sid in all_session_ids:
        try:
            messages = replay_transcript(session_id=sid)
            # Tag each message with its session ID
            for msg in messages:
                msg["session_id"] = sid
                all_messages.append(msg)
        except Exception as e:
            # Skip sessions that can't be read
            logger.debug("Failed to replay session %s: %s", sid, e)
            continue

    # Sort by timestamp (if available)
    def get_timestamp(msg):
        return msg.get("timestamp", 0)

    all_messages.sort(key=get_timestamp)
    return all_messages


def export_transcript(
    output_path: str,
    format: str = "json",
    session_id: str | None = None,
    include_spawned: bool = False,  # v1.23.7: Export spawn tree
) -> str:
    """Export transcript to file.

    Args:
        output_path: Path to output file
        format: Export format: "json", "markdown", or "text"
        session_id: Session to export. If None, uses current session.
        include_spawned: v1.23.7+ If True, export all spawned sessions
                        (recursively). Messages include session_id field.
                        Default False.

    Returns:
        The output_path on success, empty string on failure.

    Example:
        // Export current session
        export_transcript("transcript.json", "json")
        export_transcript("transcript.md", "markdown")

        // Export with all spawned sessions
        export_transcript("full_transcript.json", "json", include_spawned=true)
    """
    # v1.23.7: Use replay_full_session if include_spawned
    if include_spawned:
        messages = replay_full_session(session_id=session_id)
    else:
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


def search_transcript(
    query: str,
    session_id: str | None = None,
    scope: str = "current",
    role: str = "",
    regex: bool = False,
    limit: int = 50,
    include_spawned: bool = False,  # v1.23.7: Search across spawn sessions
) -> list[dict[str, Any]]:
    """Search transcript messages by content.

    Finds messages whose content matches the query. Unlike search_context()
    which only searches the current active context (discarded when main {}
    exits), search_transcript() searches the persistent TranscriptStore.

    Args:
        query: Text pattern to search for. Substring by default; regex if
               regex=True.
        session_id: Specific session to search. Ignored when scope="all".
                    When None and scope="current", searches the current session.
        scope: Search scope — "current" (default session), "all" (every
               session on disk), "global", or "project".
        role: Filter by message role (e.g., "user", "assistant", "tool").
              Empty string matches all roles.
        regex: If True, treat query as a regex pattern; otherwise substring.
        limit: Maximum number of matches to return (default 50).
        include_spawned: v1.23.7+ If True, also search all spawned sessions
                        (recursively). Results include session_id field to
                        identify the origin session. Default False.

    Returns:
        List of match dicts, ordered by recency (newest first):
        [
            {
                "session_id": str,
                "message_uuid": str,
                "role": str,
                "content": str,             # full content
                "snippet": str,             # matched region with context
                "match_position": int,      # start index of match in content
            },
            ...
        ]

    Examples:
        // Search current session for messages about "认证 bug"
        let matches = search_transcript("认证 bug")

        // Search ALL sessions (cross-session discovery)
        let matches = search_transcript("数据库 schema", scope="all")

        // Regex search
        let matches = search_transcript("fix.*bug", regex=true)

        // Only user messages
        let matches = search_transcript("TODO", role="user")
    """
    import re

    if not query:
        return []

    # Compile regex pattern once
    try:
        pattern = re.compile(query) if regex else None
    except re.error as e:
        logger.error("Invalid regex pattern: %s", e)
        return []

    def _matches(content: str) -> int:
        """Return match position if content matches, else -1."""
        if pattern is not None:
            m = pattern.search(content)
            return m.start() if m else -1
        idx = content.find(query)
        return idx

    def _make_snippet(content: str, pos: int, context_chars: int = 60) -> str:
        """Build a snippet around the match position."""
        if not content:
            return ""
        start = max(0, pos - context_chars)
        end = min(len(content), pos + len(query) + context_chars)
        snippet = content[start:end].replace("\n", " ")
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(content) else ""
        return f"{prefix}{snippet}{suffix}"

    def _match_message(msg_dict: dict, sid: str) -> dict | None:
        """Check if a message dict matches; return match record or None."""
        content = msg_dict.get("content", "")
        if isinstance(content, list):
            # Multimodal: flatten text parts
            content = "\n".join(
                p.get("text", "")
                for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        if not content:
            return None

        # Role filter
        msg_role = msg_dict.get("role", "")
        if role and msg_role != role:
            return None

        pos = _matches(content)
        if pos < 0:
            return None

        return {
            "session_id": sid,
            "message_uuid": msg_dict.get("uuid", ""),
            "role": msg_role,
            "content": content,
            "snippet": _make_snippet(content, pos),
            "match_position": pos,
        }

    results: list[dict[str, Any]] = []

    # --- Scope 1: current session (in-memory, fast path) ---
    # "current" means the active interpreter's in-memory transcript. If there's
    # no interpreter, there's no "current" session - return empty (don't fall
    # through to disk, which would search unrelated historical sessions).
    if scope == "current":
        if _get_agent_context() is None:
            return []
        store = getattr(_get_agent_context(), "transcript_store", None)
        current_sid = get_session_id()

        # If session_id is specified and differs from current, fall through to disk
        if store is not None and (session_id is None or session_id == current_sid):
            from helen.runtime.transcript_store import BoundaryMarker, Message
            for item in store.transcript:
                if isinstance(item, BoundaryMarker):
                    continue
                if not isinstance(item, Message):
                    continue
                msg_dict = {
                    "uuid": item.uuid,
                    "role": item.role,
                    "content": item.content,
                }
                match = _match_message(msg_dict, current_sid)
                if match is not None:
                    results.append(match)
                    if len(results) >= limit:
                        break
            # Newest first
            results.reverse()
            return results[:limit]
        # session_id specified but not current -> fall through to disk search below

    elif scope in ("", "global", "project") and session_id is None and _get_agent_context() is not None:
        # Implicit "current": interpreter exists, no explicit scope/session_id
        store = getattr(_get_agent_context(), "transcript_store", None)
        current_sid = get_session_id()
        if store is not None:
            from helen.runtime.transcript_store import BoundaryMarker, Message
            for item in store.transcript:
                if isinstance(item, BoundaryMarker):
                    continue
                if not isinstance(item, Message):
                    continue
                msg_dict = {
                    "uuid": item.uuid,
                    "role": item.role,
                    "content": item.content,
                }
                match = _match_message(msg_dict, current_sid)
                if match is not None:
                    results.append(match)
                    if len(results) >= limit:
                        break
            results.reverse()
            return results[:limit]

    # --- Scope 2: disk-based search (specific session or all sessions) ---
    from helen.runtime.config import resolve_session_dir
    from helen.runtime.session_manager import SessionManager
    from helen.runtime.transcript_store import JSONLBackend, Message, TranscriptStore

    # Determine which session dirs to search
    search_dirs: list[tuple[Path, str]] = []
    seen_dirs: set[str] = set()
    if scope == "all":
        # Search both global and project dirs (dedupe by path)
        for sc in ("global", "project"):
            try:
                d, _ = resolve_session_dir(scope=sc)
                d_str = str(d)
                if d_str not in seen_dirs:
                    search_dirs.append((Path(d), sc))
                    seen_dirs.add(d_str)
            except Exception:
                pass
    else:
        # Single scope (current/global/project)
        try:
            d, _ = resolve_session_dir(scope=scope or "")
            search_dirs.append((Path(d), scope or "current"))
        except Exception as e:
            logger.error("Failed to resolve session dir for scope %r: %s", scope, e)
            return []

    # Collect session IDs to search (dedupe)
    target_sids: list[str] = []
    seen_sids: set[str] = set()
    for base_dir, _sc in search_dirs:
        try:
            manager = SessionManager(base_dir=str(base_dir))
            for s in manager.list_sessions():
                sid = s["session_id"]
                if sid in seen_sids:
                    continue
                if session_id is not None and sid != session_id:
                    continue
                target_sids.append(sid)
                seen_sids.add(sid)
        except Exception as e:
            logger.error("Failed to list sessions in %s: %s", base_dir, e)

    # Read each session's transcript and search
    for sid in target_sids:
        if len(results) >= limit:
            break
        # Find the session dir
        transcript_path = None
        for base_dir, _sc in search_dirs:
            try:
                manager = SessionManager(base_dir=str(base_dir))
                if manager.session_exists(sid):
                    transcript_path = manager.get_session_path(sid)
                    break
            except Exception:
                continue
        if transcript_path is None or not transcript_path.exists():
            continue

        try:
            backend = JSONLBackend(transcript_path)
            loaded = TranscriptStore.load_from_backend(backend, max_memory_items=100_000)
        except Exception as e:
            logger.warning("Failed to load transcript %s: %s", sid, e)
            continue

        for item in loaded.transcript:
            if len(results) >= limit:
                break
            if not isinstance(item, Message):
                continue
            msg_dict = {
                "uuid": item.uuid,
                "role": item.role,
                "content": item.content,
            }
            match = _match_message(msg_dict, sid)
            if match is not None:
                results.append(match)

    # Newest first (within each session the list is chronological; across
    # sessions we just append, so final reverse gives newest-first overall)
    results.reverse()

    # v1.23.7: If include_spawned, also search all spawned sessions
    if include_spawned and results:
        # Get the root session ID (from first result or parameter)
        root_sid = session_id or get_session_id()
        if root_sid:
            # Collect all spawned session IDs
            spawned_sids = []
            def collect_spawns(sid):
                spawned = get_spawned_sessions(sid)
                for spawn_info in spawned:
                    child_sid = spawn_info.get("session_id", "")
                    if child_sid and child_sid not in spawned_sids:
                        spawned_sids.append(child_sid)
                        collect_spawns(child_sid)
            collect_spawns(root_sid)

            # Search each spawned session
            for child_sid in spawned_sids:
                if len(results) >= limit:
                    break
                child_results = search_transcript(
                    query=query,
                    session_id=child_sid,
                    scope="current",  # Will fall through to disk
                    role=role,
                    regex=regex,
                    limit=limit - len(results),
                    include_spawned=False,  # Don't recurse infinitely
                )
                results.extend(child_results)

    return results[:limit]


# ---------------------------------------------------------------------------
# v1.22: Invocation tree queries
# ---------------------------------------------------------------------------
# An invocation is one execution of an agent's main {} block (or top-level
# main). Messages are tagged with invocation_id / agent_name / parent
# invocation_id. These functions query the invocation tree.


def _build_invocation_index(
    store: Any,
) -> dict[str, dict[str, Any]]:
    """Rebuild the invocation index from a TranscriptStore.

    Scans all messages in the store and builds a mapping from invocation_id
    to invocation metadata. Used by list_invocations / get_invocation_tree
    when the interpreter's in-memory index is unavailable (e.g., after
    process restart, or for historical sessions).

    Returns:
        dict mapping invocation_id -> {
            "invocation_id": str,
            "agent_name": str | None,
            "parent_invocation_id": str,
            "message_count": int,
            "first_message_time": float | None,
            "last_message_time": float | None,
            "order": int,  # Index of first message in transcript (tiebreaker)
        }
    """
    from helen.runtime.transcript_store import BoundaryMarker, Message

    index: dict[str, dict[str, Any]] = {}
    message_idx = 0

    for item in store.transcript:
        if isinstance(item, BoundaryMarker) or not isinstance(item, Message):
            message_idx += 1
            continue
        inv_id = getattr(item, "invocation_id", "") or ""
        if not inv_id:
            message_idx += 1
            continue  # Skip messages without invocation_id (pre-v1.22)

        if inv_id not in index:
            index[inv_id] = {
                "invocation_id": inv_id,
                "agent_name": getattr(item, "agent_name", None),
                "parent_invocation_id": getattr(item, "parent_invocation_id", "") or "",
                "message_count": 0,
                "first_message_time": None,
                "last_message_time": None,
                "order": message_idx,  # Position of first message
            }
        entry = index[inv_id]
        entry["message_count"] += 1
        ts = getattr(item, "timestamp", None)
        if ts is not None:
            if entry["first_message_time"] is None or ts < entry["first_message_time"]:
                entry["first_message_time"] = ts
            if entry["last_message_time"] is None or ts > entry["last_message_time"]:
                entry["last_message_time"] = ts
        message_idx += 1

    # Add children lists
    for entry in index.values():
        entry["children"] = []
    for entry in index.values():
        parent = entry["parent_invocation_id"]
        if parent and parent in index:
            index[parent]["children"].append(entry["invocation_id"])

    return index


def _load_session_store(session_id: str) -> Any | None:
    """Load a TranscriptStore for a specific session. Returns None on failure."""
    from helen.runtime.config import resolve_session_dir
    from helen.runtime.session_manager import SessionManager
    from helen.runtime.transcript_store import JSONLBackend, SQLiteBackend, TranscriptStore
    from helen.runtime.config import get_transcript_config

    try:
        session_dir, _ = resolve_session_dir()
        manager = SessionManager(base_dir=session_dir)
        if not manager.session_exists(session_id):
            return None
        transcript_path = manager.get_session_path(session_id)
        config = get_transcript_config()
        backend_type = config.get("backend", "jsonl")
        if backend_type == "sqlite":
            sqlite_path = transcript_path.with_suffix(".db")
            backend = SQLiteBackend(sqlite_path)
        else:
            backend = JSONLBackend(transcript_path)
        return TranscriptStore.load_from_backend(backend, max_memory_items=100_000)
    except Exception as e:
        logger.error("Failed to load session %s: %s", session_id, e)
        return None


def list_invocations(
    session_id: str | None = None,
    agent: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List invocations, with optional filtering and pagination.

    Args:
        session_id: Session to query. If None, uses current session.
        agent: Filter by agent name. None returns all agents.
        limit: Maximum results (default 100).
        offset: Skip first N results (default 0).

    Returns:
        List of invocation metadata dicts, ordered by first_message_time (newest first).
        Each dict contains:
        - invocation_id: UUID of the invocation
        - agent_name: Agent name (None for top-level main)
        - parent_invocation_id: Parent invocation UUID
        - message_count: Number of messages in this invocation
        - first_message_time: Timestamp of first message (or None)
        - last_message_time: Timestamp of last message (or None)
        - children: List of child invocation IDs

    Example:
        let invs = list_invocations()
        for inv in invs {
            print("{inv.agent_name}: {inv.message_count} msgs")
        }

        // Filter by agent
        let a_runs = list_invocations(agent="Researcher")

        // Pagination
        let page2 = list_invocations(limit=10, offset=10)
    """
    sid = session_id or get_session_id()
    if not sid:
        return []

    store = _load_session_store(sid)
    if store is None:
        return []

    index = _build_invocation_index(store)

    # Filter by agent if specified
    if agent is not None:
        results = [e for e in index.values() if e["agent_name"] == agent]
    else:
        results = list(index.values())

    # Sort by first_message_time, newest first (None times fall back to order)
    results.sort(
        key=lambda e: (
            e["first_message_time"] if e["first_message_time"] is not None else 0,
            e.get("order", 0),  # Tiebreaker: later invocations first
        ),
        reverse=True,
    )

    return results[offset : offset + limit]


def get_invocation(invocation_id: str, session_id: str | None = None) -> dict[str, Any]:
    """Get metadata for a specific invocation.

    Args:
        invocation_id: The invocation UUID to look up.
        session_id: Session to query. If None, uses current session.

    Returns:
        Invocation metadata dict (same shape as list_invocations entries),
        or empty dict if not found.

    Example:
        let info = get_invocation("inv_1784272795_a61bcdaf")
        print("Agent: " + str(info["agent_name"]))
        print("Messages: " + str(info["message_count"]))
    """
    if not invocation_id:
        return {}

    sid = session_id or get_session_id()
    if not sid:
        return {}

    store = _load_session_store(sid)
    if store is None:
        return {}

    index = _build_invocation_index(store)
    return index.get(invocation_id, {})


def get_invocation_tree(session_id: str | None = None) -> dict[str, Any]:
    """Get the full invocation tree for a session.

    Returns the root invocation (top-level main) with nested children.
    If there's no top-level main (unusual), returns the forest as a
    virtual root with multiple children.

    Args:
        session_id: Session to query. If None, uses current session.

    Returns:
        Nested dict representing the invocation tree:
        {
            "invocation_id": str,
            "agent_name": str | None,
            "message_count": int,
            "children": [<nested trees>],
            ...
        }

    Example:
        let tree = get_invocation_tree()
        // Print tree shape:
        // inv_0 (top)
        // ├── inv_1 (agent A)
        // └── inv_2 (agent B)
        //     └── inv_3 (agent C, nested in B)
    """
    sid = session_id or get_session_id()
    if not sid:
        return {}

    store = _load_session_store(sid)
    if store is None:
        return {}

    index = _build_invocation_index(store)
    if not index:
        return {}

    # Find roots: invocations whose parent is not in the index
    roots = [e for e in index.values() if e["parent_invocation_id"] not in index]

    def _build_tree(entry: dict) -> dict:
        node = dict(entry)
        node["children"] = [
            _build_tree(index[child_id])
            for child_id in entry.get("children", [])
            if child_id in index
        ]
        return node

    if len(roots) == 1:
        return _build_tree(roots[0])

    # Multiple roots: wrap in virtual root
    return {
        "invocation_id": "",
        "agent_name": None,
        "message_count": 0,
        "parent_invocation_id": "",
        "children": [_build_tree(r) for r in roots],
    }


def invocation_path(invocation_id: str, session_id: str | None = None) -> str:
    """Get a human-readable path string for an invocation.

    Args:
        invocation_id: The invocation UUID.
        session_id: Session to query. If None, uses current session.

    Returns:
        Path string like "inv_0 (top) → inv_1 (agent A) → inv_3 (agent C)"
        or empty string if not found.

    Example:
        print(invocation_path("inv_3"))
        // "top → A → C"
    """
    if not invocation_id:
        return ""

    sid = session_id or get_session_id()
    if not sid:
        return ""

    store = _load_session_store(sid)
    if store is None:
        return ""

    index = _build_invocation_index(store)
    if invocation_id not in index:
        return ""

    # Walk up the parent chain
    path_parts: list[str] = []
    current_id: str | None = invocation_id
    seen: set[str] = set()
    while current_id and current_id in index and current_id not in seen:
        entry = index[current_id]
        name = entry["agent_name"] or "top"
        path_parts.append(f"{name}")
        seen.add(current_id)
        current_id = entry.get("parent_invocation_id") or None

    path_parts.reverse()
    return " → ".join(path_parts)


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
    if _get_agent_context() is None:
        return []

    store = getattr(_get_agent_context(), "transcript_store", None)
    if store is None:
        return []

    return store.get_compression_audit()


def resume_session(session_id: str) -> dict:
    """Resume a previous transcript session (idempotent, preserves call tree).

    Imports messages from a previous session into the current TranscriptStore,
    allowing continuation of a past conversation.

    v1.24 improvements:
    1. Preserves original invocation_id (maintains call tree integrity)
    2. Adds current invocation_id to visible_to_invocation_ids (ensures visibility)
    3. Uses UUID deduplication (idempotent — safe to call multiple times)
    4. Returns detailed status with imported/skipped counts

    Use restore_context() for finer-grained control (filter by agent, invocation,
    or restore only the most recent invocation).

    Args:
        session_id: The session ID to resume

    Returns:
        dict:
        {
            "status": "ok" | "error",
            "imported_messages": int,        # Number of messages imported
            "skipped_duplicates": int,       # Number of messages skipped (already exist)
            "session_id": str,               # The session ID that was resumed
        }

    Example:
        let result = resume_session("session_1783492628_d9d9c0aa")
        if result.status == "ok" {
            print("Imported {result.imported_messages} messages")
            print("Skipped {result.skipped_duplicates} duplicates")
        } else {
            print("Failed: {result.error}")
        }
    """
    if _get_agent_context() is None:
        return {"status": "error", "error": "No interpreter agent context",
                "imported_messages": 0, "skipped_duplicates": 0}

    store = getattr(_get_agent_context(), "transcript_store", None)
    if store is None:
        return {"status": "error", "error": "No transcript store",
                "imported_messages": 0, "skipped_duplicates": 0}

    # Import required modules
    from helen.runtime.config import get_transcript_config
    from helen.runtime.session_manager import SessionManager
    from helen.runtime.transcript_store import (
        BoundaryMarker, JSONLBackend, SQLiteBackend, TranscriptStore,
    )

    try:
        from helen.runtime.config import resolve_session_dir
        from helen.runtime.session_manager import SessionManager
        from helen.runtime.transcript_store import (
            BoundaryMarker, JSONLBackend, SQLiteBackend, TranscriptStore,
        )

        session_dir, _scope = resolve_session_dir()
        config = get_transcript_config()
        backend_type = config.get("backend", "jsonl")

        manager = SessionManager(base_dir=session_dir)

        # Check if session exists
        if not manager.session_exists(session_id):
            return {"status": "error", "error": f"Session not found: {session_id}",
                    "imported_messages": 0, "skipped_duplicates": 0}

        # Get transcript path
        transcript_path = manager.get_session_path(session_id)

        # Create backend based on config
        if backend_type == "sqlite":
            sqlite_path = transcript_path.with_suffix(".db")
            backend = SQLiteBackend(sqlite_path)
        else:
            backend = JSONLBackend(transcript_path)

        # Load transcript from backend
        max_memory_items = config.get("max_memory_items", 1000)
        loaded_store = TranscriptStore.load_from_backend(backend, max_memory_items)

        # v1.24: Get current invocation_id for visibility tracking
        current_invocation_id = ""
        try:
            from helen.stdlib.llm_control import _interpreter_ref
            if _interpreter_ref is not None:
                current_invocation_id = getattr(
                    _interpreter_ref, '_current_invocation_id', ''
                ) or ''
        except Exception:
            pass

        # v1.24: Build UUID index for deduplication (idempotency)
        existing_uuids = set(store._uuid_index.keys())

        imported = 0
        skipped = 0

        for item in loaded_store.transcript:
            if isinstance(item, BoundaryMarker):
                continue

            # v1.24: Idempotency check — skip if UUID already exists
            if item.uuid in existing_uuids:
                skipped += 1
                continue

            # v1.24: Preserve original invocation_id (call tree integrity)
            # and add current invocation_id to visible_to_invocation_ids (visibility)
            from helen.runtime.history import Message
            visible_to = list(getattr(item, 'visible_to_invocation_ids', []) or [])
            if current_invocation_id and current_invocation_id not in visible_to:
                visible_to.append(current_invocation_id)

            msg = Message(
                role=item.role,
                content=item.content,
                tool_calls=list(item.tool_calls) if item.tool_calls else [],
                tool_call_id=item.tool_call_id,
                uuid=item.uuid,                      # v1.24: Preserve original UUID
                compressed=item.compressed,
                pinned=item.pinned,
                invocation_id=item.invocation_id,    # v1.24: Preserve original (call tree)
                parent_invocation_id=item.parent_invocation_id,  # v1.24: Preserve
                agent_name=item.agent_name,          # v1.24: Preserve
                visible_to_invocation_ids=visible_to,  # v1.24: Add visibility
            )
            store.append(msg)
            existing_uuids.add(msg.uuid)
            imported += 1

        return {
            "status": "ok",
            "imported_messages": imported,
            "skipped_duplicates": skipped,
            "session_id": session_id,
        }

    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Failed to resume session %s: %s", session_id, e)
        return {"status": "error", "error": str(e),
                "imported_messages": 0, "skipped_duplicates": 0}


# ---------------------------------------------------------------------------
# Session directory access (v1.20)
# ---------------------------------------------------------------------------

def get_session_dir() -> dict:
    """Get the resolved transcript session directory.

    Returns the actual directory path where transcripts are stored for the
    current session, taking into account:
    - `session_scope` config ("global" | "project" | "auto")
    - `HELEN_SESSION_DIR` environment variable override
    - Project detection (when scope is "auto" or "project")

    Returns:
        dict:
        {
            "status": "ok",
            "session_dir": str,           # Absolute path to session directory
            "scope": str,                 # "global" | "project" | "env_override"
            "project_dir": str | None,    # Detected project dir (if scope=project)
        }

    Example:
        let info = get_session_dir()
        print("Transcripts are stored in: " + info["session_dir"])
        print("Scope: " + info["scope"])
    """
    from helen.runtime.config import resolve_session_dir, detect_project_dir
    import os

    path, scope = resolve_session_dir()
    project_dir = detect_project_dir(os.getcwd()) if scope == "project" else None

    return {
        "status": "ok",
        "session_dir": path,
        "scope": scope,
        "project_dir": project_dir,
    }


def set_session_dir(path: str) -> dict:
    """Set the transcript session directory at runtime.

    This overrides the session directory for the current interpreter session
    only. It does NOT modify ``~/.helen/config.yaml`` — use that file for
    persistent configuration.

    The new directory will be created if it doesn't exist. Existing transcripts
    in the old directory are NOT migrated — they remain where they are.

    Args:
        path: Absolute or relative path to the new session directory.
              Relative paths are resolved against cwd.

    Returns:
        dict:
        {
            "status": "ok",
            "session_dir": str,    # Absolute path of the new directory
            "previous": str,       # Previous session directory
        }
        Or on error: {"status": "error", "error": "..."}

    Example:
        let r = set_session_dir("./my_sessions")
        if r["status"] == "ok" {
            print("Now storing transcripts in: " + r["session_dir"])
        }

    Note:
        This only affects future sessions created after the call. The current
        session's transcript remains in its original location until the next
        session starts.
    """
    import os
    from pathlib import Path

    if not path:
        return {"status": "error", "error": "path is required"}

    try:
        new_path = Path(path).expanduser().resolve()
        # Get previous path for the response
        from helen.runtime.config import resolve_session_dir
        previous_path, _ = resolve_session_dir()

        # Set the env var so subsequent resolve_session_dir() calls return this path
        os.environ["HELEN_SESSION_DIR"] = str(new_path)

        # Create directory if needed
        new_path.mkdir(parents=True, exist_ok=True)

        return {
            "status": "ok",
            "session_dir": str(new_path),
            "previous": previous_path,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Session deletion (v1.21)
# ---------------------------------------------------------------------------

def delete_session(session_id: str, cascade: bool = True) -> dict:
    """Permanently delete a session and its transcript data.

    This removes all data for the specified session from disk, including
    transcript files, compression history, and indexes. This operation
    cannot be undone.

    v1.23.7: Added cascade parameter. When True (default), also deletes all
    sessions spawned by this session (recursively). This prevents orphaned
    transcripts from accumulating.

    Args:
        session_id: The session ID to delete
        cascade: If True (default), also delete all spawned sessions.
                 If False, only delete the specified session (spawned
                 sessions become orphans).

    Returns:
        dict:
        {
            "status": "ok" | "error",
            "session_id": str,
            "message": str,
            "freed_bytes": int,  # Only on success
            "deleted_sessions": list[str],  # v1.23.7: List of deleted session IDs
        }

    Example:
        // Delete session and all its spawns (default)
        let r = delete_session("session_1720435200_a1b2c3d4")
        print("Deleted {len(r['deleted_sessions'])} sessions")

        // Delete only the specified session (keep spawns)
        let r = delete_session("session_1720435200_a1b2c3d4", cascade=false)

    Warning:
        This permanently deletes all session data and cannot be undone.
        The current session cannot be deleted using this function — use
        delete_current_session() for that (with extra confirmation).
    """
    import os
    from pathlib import Path

    if not session_id:
        return {"status": "error", "message": "session_id is required"}

    # Prevent deleting the current session
    current_session_id = get_session_id()
    if session_id == current_session_id:
        return {
            "status": "error",
            "message": "Cannot delete current session. Use delete_current_session() instead.",
            "session_id": session_id,
        }

    try:
        from helen.runtime.config import resolve_session_dir
        from helen.runtime.session_manager import SessionManager

        # Resolve session directory
        session_dir, _ = resolve_session_dir()
        manager = SessionManager(base_dir=session_dir)

        # Check if session exists
        if not manager.session_exists(session_id):
            return {
                "status": "error",
                "message": f"Session not found: {session_id}",
                "session_id": session_id,
            }

        # v1.23.7: Collect all sessions to delete (cascade)
        sessions_to_delete = [session_id]
        if cascade:
            spawned = get_spawned_sessions(session_id)
            for spawn_info in spawned:
                child_sid = spawn_info.get("session_id", "")
                if child_sid and child_sid != current_session_id:
                    # Recursively collect nested spawns
                    nested_result = delete_session(child_sid, cascade=True)
                    if nested_result.get("status") == "ok":
                        sessions_to_delete.extend(nested_result.get("deleted_sessions", []))

        # Delete all collected sessions
        total_freed_bytes = 0
        deleted_sessions = []

        for sid in sessions_to_delete:
            # Calculate size before deletion
            session_path = manager.get_session_dir(sid)
            freed_bytes = 0
            if session_path.exists():
                freed_bytes = sum(
                    f.stat().st_size
                    for f in session_path.rglob("*")
                    if f.is_file()
                )

            # Delete the session
            success = manager.delete_session(sid)

            if success:
                total_freed_bytes += freed_bytes
                deleted_sessions.append(sid)
                logger.info("Deleted session %s, freed %d bytes", sid, freed_bytes)
            else:
                logger.warning("Failed to delete session %s", sid)

        if deleted_sessions:
            return {
                "status": "ok",
                "session_id": session_id,
                "message": f"Deleted {len(deleted_sessions)} session(s) successfully",
                "freed_bytes": total_freed_bytes,
                "deleted_sessions": deleted_sessions,
            }
        else:
            return {
                "status": "error",
                "message": "Failed to delete session(s)",
                "session_id": session_id,
            }

    except Exception as e:
        logger.error("Failed to delete session %s: %s", session_id, e)
        return {"status": "error", "message": str(e), "session_id": session_id}


def delete_current_session(confirm: bool = False, cascade: bool = True) -> dict:
    """Permanently delete the current session and its transcript data.

    This is a dangerous operation that deletes all data for the current
    session. Requires explicit confirmation via the `confirm` parameter.

    Args:
        confirm: Must be True to proceed with deletion

    Returns:
        dict:
        {
            "status": "ok" | "error",
            "session_id": str,
            "message": str,
            "freed_bytes": int,  # Only on success
        }

    Example:
        // First call without confirm to see what would be deleted
        let r = delete_current_session()
        print(r["message"])  # "Set confirm=true to delete current session"

        // Then call with confirm to actually delete
        if should_delete {
            let r = delete_current_session(confirm=true)
        }

    Warning:
        This permanently deletes ALL data for the current session and cannot
        be undone. The interpreter will continue running, but a new session
        will be started automatically.
    """
    if not confirm:
        return {
            "status": "error",
            "message": "Set confirm=true to delete current session",
            "session_id": get_session_id(),
        }

    session_id = get_session_id()
    if not session_id:
        return {
            "status": "error",
            "message": "No current session to delete",
        }

    try:
        from helen.runtime.config import resolve_session_dir
        from helen.runtime.session_manager import SessionManager

        # Resolve session directory
        session_dir, _ = resolve_session_dir()
        manager = SessionManager(base_dir=session_dir)

        # Check if session exists
        if not manager.session_exists(session_id):
            return {
                "status": "error",
                "message": f"Current session not found: {session_id}",
                "session_id": session_id,
            }

        # v1.23.7: Collect all sessions to delete (cascade)
        sessions_to_delete = [session_id]
        if cascade:
            def collect_spawns(sid):
                """Recursively collect all spawned sessions."""
                spawned = get_spawned_sessions(sid)
                for spawn_info in spawned:
                    child_sid = spawn_info.get("session_id", "")
                    if child_sid and child_sid not in sessions_to_delete:
                        sessions_to_delete.append(child_sid)
                        collect_spawns(child_sid)
            collect_spawns(session_id)

        # v1.23.7: Delete all collected sessions (batch delete)
        total_freed_bytes = 0
        deleted_sessions = []

        for sid in sessions_to_delete:
            # Calculate size before deletion
            session_path = manager.get_session_dir(sid)
            freed_bytes = 0
            if session_path.exists():
                freed_bytes = sum(
                    f.stat().st_size
                    for f in session_path.rglob("*")
                    if f.is_file()
                )

            # Delete the session
            success = manager.delete_session(sid)

            if success:
                total_freed_bytes += freed_bytes
                deleted_sessions.append(sid)
                logger.warning("Deleted session %s, freed %d bytes", sid, freed_bytes)
            else:
                logger.warning("Failed to delete session %s", sid)

        if deleted_sessions:
            # Clear the current transcript store
            if _get_agent_context() is not None:
                store = getattr(_get_agent_context(), "transcript_store", None)
                if store is not None:
                    store.transcript.clear()
                    store._uuid_index.clear()
                    store._dirty = True

            return {
                "status": "ok",
                "session_id": session_id,
                "message": f"Deleted {len(deleted_sessions)} session(s) successfully. A new session will be started.",
                "freed_bytes": total_freed_bytes,
                "deleted_sessions": deleted_sessions,
            }
        else:
            return {
                "status": "error",
                "message": "Failed to delete session(s)",
                "session_id": session_id,
            }

    except Exception as e:
        logger.error("Failed to delete current session: %s", e)
        return {"status": "error", "message": str(e), "session_id": session_id}


def cleanup_sessions(keep_count: int = 100, older_than_days: int | None = None, cascade: bool = True) -> dict:
    """Clean up old sessions to free disk space.

    Permanently deletes old session data from disk. This operation cannot be undone.

    v1.23.7: Added cascade parameter. When True (default), also deletes all
    sessions spawned by the deleted sessions (recursively). This prevents
    orphaned transcripts from accumulating.

    Args:
        keep_count: Keep only the N most recent sessions (default: 100)
        older_than_days: Delete sessions older than N days (optional)
        cascade: If True (default), also delete spawned sessions. If False,
                 only delete matching sessions (spawned sessions become orphans).

    Returns:
        dict:
        {
            "status": "ok",
            "deleted_count": int,
            "freed_bytes": int,
            "message": str,
            "deleted_sessions": list[str],  # v1.23.7: List of deleted session IDs
        }

    Examples:
        // Keep only 50 most recent sessions (cascade by default)
        let r = cleanup_sessions(50)
        print("Deleted " + str(r["deleted_count"]) + " sessions")

        // Delete sessions older than 30 days
        let r = cleanup_sessions(older_than_days=30)
        print("Freed " + str(r["freed_bytes"]) + " bytes")

        // Combine both criteria
        let r = cleanup_sessions(keep_count=50, older_than_days=30)

        // Don't cascade (keep spawned sessions)
        let r = cleanup_sessions(50, cascade=false)

    Warning:
        This permanently deletes session data and cannot be undone.
        Use with caution in production environments.
    """
    import time

    try:
        from helen.runtime.config import resolve_session_dir
        from helen.runtime.session_manager import SessionManager

        # Resolve session directory
        session_dir, _ = resolve_session_dir()
        manager = SessionManager(base_dir=session_dir)

        if older_than_days is not None:
            # Delete sessions older than N days
            cutoff_time = time.time() - (older_than_days * 86400)
            sessions = manager.list_sessions()

            deleted_count = 0
            freed_bytes = 0
            deleted_sessions = []

            for session in sessions:
                # Don't delete the current session
                current_session_id = get_session_id()
                if session["session_id"] == current_session_id:
                    continue

                if session.get("modified_at", 0) < cutoff_time:
                    # v1.23.7: Use delete_session with cascade support
                    result = delete_session(session["session_id"], cascade=cascade)
                    if result.get("status") == "ok":
                        deleted_count += 1
                        freed_bytes += result.get("freed_bytes", 0)
                        deleted_sessions.extend(result.get("deleted_sessions", []))

            logger.info(
                "Cleaned up %d sessions older than %d days, freed %d bytes",
                deleted_count,
                older_than_days,
                freed_bytes,
            )

            return {
                "status": "ok",
                "deleted_count": deleted_count,
                "freed_bytes": freed_bytes,
                "message": f"Deleted {deleted_count} sessions older than {older_than_days} days",
                "deleted_sessions": deleted_sessions,
            }

        else:
            # Keep only N most recent sessions
            sessions = manager.list_sessions()
            current_session_id = get_session_id()

            # Don't count current session in keep_count
            other_sessions = [s for s in sessions if s["session_id"] != current_session_id]

            if len(other_sessions) <= keep_count:
                return {
                    "status": "ok",
                    "deleted_count": 0,
                    "freed_bytes": 0,
                    "message": f"No cleanup needed, only {len(other_sessions)} sessions (keeping {keep_count})",
                }

            # Sessions are sorted by modified_at (newest first)
            to_delete = other_sessions[keep_count:]
            deleted_count = 0
            freed_bytes = 0
            deleted_sessions = []

            for session in to_delete:
                # v1.23.7: Use delete_session with cascade support
                result = delete_session(session["session_id"], cascade=cascade)
                if result.get("status") == "ok":
                    deleted_count += 1
                    freed_bytes += result.get("freed_bytes", 0)
                    deleted_sessions.extend(result.get("deleted_sessions", []))

            logger.info(
                "Cleaned up %d old sessions, freed %d bytes (keeping %d)",
                deleted_count,
                freed_bytes,
                keep_count,
            )

            return {
                "status": "ok",
                "deleted_count": deleted_count,
                "freed_bytes": freed_bytes,
                "message": f"Deleted {deleted_count} old sessions, keeping {keep_count} most recent",
                "deleted_sessions": deleted_sessions,
            }

    except Exception as e:
        logger.error("Failed to cleanup sessions: %s", e)
        return {"status": "error", "message": str(e), "deleted_count": 0, "freed_bytes": 0}

