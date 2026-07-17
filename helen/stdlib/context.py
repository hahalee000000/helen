"""Context management functions for Helen stdlib.

Provides functions to manage LLM conversation context:
- clear_context(): Clear conversation history
- compress_context(): Trigger context compression
- compress_context_target(): Phase 1 - Targeted compression by message type
- context_stats(): Return detailed statistics about current context
- context_usage(): Return current context usage ratio (0.0-1.0)
- get_message(uuid): Retrieve a single message by UUID
- delete_message(uuid): Delete a message by UUID
- pin_message(uuid): Pin a message (immune to compression)
- unpin_message(uuid): Unpin a previously pinned message
- working_memory_get/set/remove/clear: Working memory access (P1)
- insert_message / replace_message: Fine-grained message mutation (P2)
- set_compression_strategy / set_context_window / set_working_memory_enabled /
  set_cache_aware / get_context_config: Runtime configuration (P2)
- search_context / context_slice: Query helpers (P3)
- export_context / import_context / fork_context: Multi-agent transfer (P2/P3)
- on_compression: Lifecycle hook (P1)

These functions allow applications to control context growth in long-running agents.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global reference to interpreter's history manager (set by interpreter)
_interpreter_history_manager = None
_interpreter_history = None
_interpreter_agent_context = None


def _set_interpreter_context(
    history: list, history_manager: Any, agent_context: Any = None
) -> None:
    """Set the interpreter's history and history manager for context management.

    Called by the interpreter during initialization to provide stdlib functions
    with access to the conversation history.

    Args:
        history: The interpreter's _history list
        history_manager: The interpreter's HistoryManager instance
        agent_context: The interpreter's AgentContextManager instance (optional)
    """
    global _interpreter_history, _interpreter_history_manager, _interpreter_agent_context
    _interpreter_history = history
    _interpreter_history_manager = history_manager
    _interpreter_agent_context = agent_context


def _get_effective_history() -> list | None:
    """Return the effective message list from TranscriptStore (SSOT) or fallback.

    Phase 2 SSOT: When TranscriptStore is enabled (the default since v1.16),
    ``llm act`` writes messages ONLY to TranscriptStore, bypassing the
    ``_interpreter_history`` list.  Stdlib read functions (``context_stats``,
    ``context_usage``, ``search_context``, …) must therefore consult
    TranscriptStore first to see the full conversation.

    Returns:
        List of Message objects, or None if no context is available at all.
    """
    if _interpreter_agent_context is not None:
        store = getattr(_interpreter_agent_context, 'transcript_store', None)
        if store is not None:
            return store.read_view()
    return _interpreter_history


def _classify_message(message: Any) -> dict:
    """Classify a message and assign priority.

    Phase 1: Enables selective compression by distinguishing "actions" (tool_use)
    from "data" (tool_result).

    Args:
        message: Message object to classify

    Returns:
        dict with classification info:
        {
            "message_type": str,      # "system"|"user"|"assistant"|"assistant_tool_call"|"tool"
            "priority": int,          # 1-100
            "compressed": bool        # Whether already compressed
        }
    """
    if not hasattr(message, 'infer_message_type'):
        return {
            "message_type": "unknown",
            "priority": 50,
            "compressed": False,
        }

    msg_type = message.infer_message_type()
    priority = message.assign_priority()
    compressed = getattr(message, 'compressed', False)

    return {
        "message_type": msg_type,
        "priority": priority,
        "compressed": compressed,
    }


def _compress_context_target(target: str, keep_recent: int = 5) -> dict:
    """Compress context by target type.

    Phase 1: Selective compression that distinguishes actions from data.

    Args:
        target: Compression target type
            - "tool_results": Clear old tool results, preserve tool_use decisions
            - "stale_turns": Discard stale conversation turns
        keep_recent: Number of recent messages to keep (default 5)

    Returns:
        dict with compression results:
        {
            "status": "ok" | "error",
            "target": str,
            "compressed": int,        # Number of messages compressed
            "saved_tokens": int,      # Tokens saved
            "kept_messages": int,     # Messages kept intact
        }
    """
    if _interpreter_history is None:
        return {
            "status": "error",
            "error": "No interpreter context available",
            "target": target,
            "compressed": 0,
            "saved_tokens": 0,
            "kept_messages": 0,
        }

    if target not in ["tool_results", "stale_turns"]:
        return {
            "status": "error",
            "error": f"Unknown compression target: {target}. Use 'tool_results' or 'stale_turns'.",
            "target": target,
            "compressed": 0,
            "saved_tokens": 0,
            "kept_messages": 0,
        }

    # Calculate initial token count
    initial_tokens = sum(msg.token_count for msg in _interpreter_history if hasattr(msg, 'token_count'))

    if target == "tool_results":
        # Compress old tool results, preserve tool_use decisions
        compressed_count = 0
        kept_count = 0

        # Keep the most recent 'keep_recent' tool results
        tool_result_indices = []
        for i, msg in enumerate(_interpreter_history):
            if hasattr(msg, 'message_type'):
                msg_type = msg.message_type or msg.infer_message_type()
                if msg_type == "tool":
                    tool_result_indices.append(i)

        # Mark old tool results for compression (keep recent ones)
        for i, idx in enumerate(tool_result_indices):
            if i < len(tool_result_indices) - keep_recent:
                msg = _interpreter_history[idx]
                if hasattr(msg, 'compressed') and not msg.compressed:
                    # Replace content with placeholder
                    msg.content = f"[Tool result cleared: {msg.tool_call_id}]"
                    msg.compressed = True
                    msg._token_count = 10  # Minimal tokens for placeholder
                    compressed_count += 1
                else:
                    kept_count += 1
            else:
                kept_count += 1

    elif target == "stale_turns":
        # Discard stale conversation turns (keep recent ones)
        compressed_count = 0
        kept_count = 0

        # Find turns to discard (older than keep_recent)
        if len(_interpreter_history) > keep_recent * 2:
            # Mark old messages as compressed
            for i in range(len(_interpreter_history) - keep_recent * 2):
                msg = _interpreter_history[i]
                if hasattr(msg, 'compressed') and not msg.compressed:
                    # Keep system messages
                    if msg.role == "system":
                        kept_count += 1
                        continue

                    # Mark as compressed and reduce content
                    if msg.role == "user":
                        msg.content = "[Earlier user message cleared]"
                    elif msg.role == "assistant":
                        if msg.tool_calls:
                            msg.content = "[Earlier assistant tool call cleared]"
                        else:
                            msg.content = "[Earlier assistant response cleared]"
                    elif msg.role == "tool":
                        msg.content = f"[Earlier tool result cleared: {msg.tool_call_id}]"

                    msg.compressed = True
                    msg._token_count = 10
                    compressed_count += 1
                else:
                    kept_count += 1
        else:
            kept_count = len(_interpreter_history)

    # Calculate final token count
    final_tokens = sum(msg.token_count for msg in _interpreter_history if hasattr(msg, 'token_count'))
    saved_tokens = initial_tokens - final_tokens

    return {
        "status": "ok",
        "target": target,
        "compressed": compressed_count,
        "saved_tokens": saved_tokens,
        "kept_messages": len(_interpreter_history),
    }


def _clear_context() -> dict:
    """Clear the current conversation context.

    Removes all messages from the LLM conversation history. This is useful for:
    - Starting a new conversation without restarting the program
    - Resetting context after an error
    - Managing memory in long-running agents

    Phase 11: Unified through AgentContextManager.

    Returns:
        dict with status and cleared message count:
        {
            "status": "ok",
            "cleared_messages": 5,
            "cleared_tokens": 1200,  # estimated
            "warning": "LLM will lose all previous context"
        }

    Example:
        let result = clear_context()
        print("Cleared " + str(result["cleared_messages"]) + " messages")

    Warning:
        This clears all conversation history. The LLM will lose all previous context.
        Use with caution in production applications.
    """
    if _interpreter_history is None:
        return {
            "status": "error",
            "error": "No interpreter context available",
            "cleared_messages": 0,
        }

    # Calculate tokens before clearing
    estimated_tokens = sum(msg.token_count for msg in _interpreter_history if hasattr(msg, 'token_count'))
    cleared_count = len(_interpreter_history)

    # Phase 11: Use AgentContextManager for unified clearing
    if _interpreter_agent_context is not None:
        result = _interpreter_agent_context.clear_context()
        # Also clear the history list itself
        _interpreter_history.clear()
        return {
            "status": "ok",
            "cleared_messages": cleared_count,
            "cleared_tokens": estimated_tokens,
            "cleared_items": result.get("cleared_items", []),
            "warning": "LLM will lose all previous context",
        }
    else:
        # Fallback: clear directly
        _interpreter_history.clear()
        return {
            "status": "ok",
            "cleared_messages": cleared_count,
            "cleared_tokens": estimated_tokens,
            "warning": "LLM will lose all previous context",
        }


def _compress_context(strategy: str = "auto") -> dict:
    """Compress the current conversation context.

    Triggers context compression using the specified strategy. This reduces
    token usage while preserving important context.

    Phase 11: When called without strategy (or "auto"), uses AgentContextManager
    to perform LLM-based compression (Layer 5 functionality).

    Args:
        strategy: Compression strategy to use:
            - "auto": Use AgentContextManager (Layer 5, LLM if available)
            - "summarize": Use LLM to summarize old messages
            - "truncate": Keep only the most recent N messages
            - "none": No compression (no-op)

    Returns:
        dict with compression results:
        {
            "status": "ok",
            "original_messages": 10,
            "compressed_messages": 5,
            "original_tokens": 2000,
            "compressed_tokens": 1000,
            "strategy": "auto"
        }

    Example:
        // Auto-compress (uses Layer 5 via AgentContextManager)
        let result = compress_context()
        if result["status"] == "ok" {
            print("Compressed from " + str(result["original_tokens"]) +
                  " to " + str(result["compressed_tokens"]) + " tokens")
        }

        // Force summarize compression (legacy)
        compress_context("summarize")

    Note:
        - "auto" uses AgentContextManager with LLM if available
        - "summarize" may call LLM (slow but preserves context)
        - "truncate" is fast but loses old messages
        - Returns original == compressed if no compression was needed
    """
    if _interpreter_history is None or _interpreter_history_manager is None:
        return {
            "status": "error",
            "error": "No interpreter context available",
            "original_messages": 0,
            "compressed_messages": 0,
            "strategy": strategy,
        }

    # Phase 2 SSOT: When TranscriptStore is enabled, delegate to AgentContextManager
    # which properly records BoundaryMarkers instead of doing destructive in-place replacement.
    if _interpreter_agent_context is not None and _interpreter_agent_context.transcript_store is not None:
        # Get the current view from TranscriptStore (this is the real history)
        current_history = _interpreter_agent_context.transcript_store.read_view()

        if len(current_history) <= 1:
            return {
                "status": "ok",
                "original_messages": len(current_history),
                "compressed_messages": len(current_history),
                "original_tokens": sum(getattr(msg, 'token_count', 0) for msg in current_history),
                "compressed_tokens": sum(getattr(msg, 'token_count', 0) for msg in current_history),
                "strategy": strategy,
            }

        # Get stats before compression
        original_count = len(current_history)
        original_tokens = sum(getattr(msg, 'token_count', 0) for msg in current_history)

        # Determine max_tokens (use DEFAULT_CONTEXT_WINDOW from token_utils)
        from helen.runtime.token_utils import DEFAULT_CONTEXT_WINDOW
        max_tokens = DEFAULT_CONTEXT_WINDOW

        # Handle explicit strategy overrides (summarize/truncate) in TranscriptStore path
        # These strategies should force compression regardless of usage ratio thresholds
        if strategy == "none":
            # No compression — return current state
            return {
                "status": "ok",
                "original_messages": original_count,
                "compressed_messages": original_count,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "strategy": "none",
            }
        elif strategy == "summarize":
            # Use _force_compact for explicit user request (no threshold check)
            from helen.runtime.graduated_compression import _force_compact
            compressed = _force_compact(
                list(current_history),
                llm_client=getattr(_interpreter_agent_context, 'llm_client', None),
                target_tokens=max_tokens // 10
            )
            # Record compression in TranscriptStore for audit trail (creates BoundaryMarker)
            if compressed != current_history and len(compressed) < len(current_history):
                _interpreter_agent_context._record_compression_ssot(
                    current_history, compressed, "force_compact"
                )
        elif strategy == "truncate":
            # Directly use Layer 4 (_context_collapse) for truncation
            from helen.runtime.graduated_compression import _context_collapse
            compressed = _context_collapse(list(current_history))
            # Record compression in TranscriptStore for audit trail
            if compressed != current_history and len(compressed) < len(current_history):
                _interpreter_agent_context._record_compression_ssot(
                    current_history, compressed, "context_collapse"
                )
        elif strategy == "auto":
            # Use AgentContextManager's _compress_history which respects thresholds
            compressed = _interpreter_agent_context._compress_history(current_history, max_tokens)
        else:
            return {
                "status": "error",
                "error": f"Unknown compression strategy: {strategy}",
                "original_messages": original_count,
                "compressed_messages": original_count,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "strategy": strategy,
            }

        # Get stats after compression
        compressed_count = len(compressed)
        compressed_tokens = sum(getattr(msg, 'token_count', 0) for msg in compressed)

        return {
            "status": "ok",
            "original_messages": original_count,
            "compressed_messages": compressed_count,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "strategy": strategy,
        }

    # Fallback: Legacy path for when TranscriptStore is not enabled.
    # This performs destructive in-place replacement on _interpreter_history.
    # Phase 11: Use AgentContextManager for "auto" strategy (Layer 5)
    if strategy == "auto" and _interpreter_agent_context is not None:
        original_count = len(_interpreter_history)
        result = _interpreter_agent_context.compress_context()

        return {
            "status": result.get("status", "ok"),
            "reason": result.get("reason", ""),
            "original_messages": original_count,
            "compressed_messages": len(_interpreter_history),
            "original_tokens": result.get("original_tokens", 0),
            "compressed_tokens": result.get("compressed_tokens", 0),
            "saved_tokens": result.get("saved_tokens", 0),
            "strategy": result.get("strategy", "llm_semantic"),
        }

    # Legacy strategies (for backward compatibility)
    if strategy == "none":
        # Calculate tokens using Message.token_count property
        total_tokens = sum(msg.token_count for msg in _interpreter_history if hasattr(msg, 'token_count'))
        return {
            "status": "ok",
            "original_messages": len(_interpreter_history),
            "compressed_messages": len(_interpreter_history),
            "original_tokens": total_tokens,
            "compressed_tokens": total_tokens,
            "strategy": "none",
        }

    # Get stats before compression
    original_count = len(_interpreter_history)
    original_tokens = sum(msg.token_count for msg in _interpreter_history if hasattr(msg, 'token_count'))

    # Perform compression
    if strategy == "auto":
        # Use HistoryManager's enforce_limit (respects compression_mode setting)
        _interpreter_history[:] = _interpreter_history_manager.enforce_limit(_interpreter_history)
    elif strategy == "summarize":
        # Use _force_compact for explicit user request (no threshold check)
        from helen.runtime.graduated_compression import _force_compact
        compressed = _force_compact(
            list(_interpreter_history),
            llm_client=getattr(_interpreter_agent_context, 'llm_client', None) if _interpreter_agent_context else None,
            target_tokens=_interpreter_history_manager.MAX_TOKENS // 10
        )
        if len(compressed) < len(_interpreter_history):
            _interpreter_history[:] = compressed
    elif strategy == "truncate":
        # Directly use Layer 4 (_context_collapse) for truncation
        from helen.runtime.graduated_compression import _context_collapse
        compressed = _context_collapse(list(_interpreter_history))
        if len(compressed) < len(_interpreter_history):
            _interpreter_history[:] = compressed
    else:
        return {
            "status": "error",
            "error": f"Unknown compression strategy: {strategy}",
            "original_messages": original_count,
            "compressed_messages": original_count,
            "strategy": strategy,
        }

    # Get stats after compression
    compressed_count = len(_interpreter_history)
    compressed_tokens = sum(msg.token_count for msg in _interpreter_history if hasattr(msg, 'token_count'))

    return {
        "status": "ok",
        "original_messages": original_count,
        "compressed_messages": compressed_count,
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "strategy": strategy,
    }


# ---------------------------------------------------------------------------
# Helpers for UUID-based message lookup
# ---------------------------------------------------------------------------

def _find_message_by_uuid(uuid: str) -> Any:
    """Find a message by UUID across interpreter history and TranscriptStore.

    Prefers TranscriptStore (SSOT) when available, falls back to linear scan
    of the interpreter's _history list.

    Args:
        uuid: The UUID to look up

    Returns:
        The Message object if found, else None.
    """
    if not uuid:
        return None

    # Prefer TranscriptStore's UUID index (O(1))
    if _interpreter_agent_context is not None:
        store = getattr(_interpreter_agent_context, 'transcript_store', None)
        if store is not None:
            item = store.get(uuid)
            if item is not None and hasattr(item, 'role'):  # It's a Message, not a BoundaryMarker
                return item

    # Fallback: linear scan of interpreter history
    if _interpreter_history is not None:
        for msg in _interpreter_history:
            if getattr(msg, 'uuid', '') == uuid:
                return msg

    return None


def _get_max_tokens() -> int:
    """Get the configured context window size (max tokens)."""
    if _interpreter_history_manager is not None:
        return getattr(_interpreter_history_manager, 'MAX_TOKENS', 0)
    return 0


# ---------------------------------------------------------------------------
# Inspection: context_stats, context_usage, get_message
# ---------------------------------------------------------------------------

def _context_stats() -> dict:
    """Return detailed statistics about the current conversation context.

    Provides a snapshot of context usage: message count, token count,
    usage ratio, breakdown by role, compression and pinning status.

    Returns:
        dict with statistics:
        {
            "status": "ok",
            "message_count": int,     # Total message count
            "total_tokens": int,      # Estimated total token count
            "usage_ratio": float,     # total_tokens / max_tokens (0.0-1.0+)
            "max_tokens": int,          # Configured context window size
            "by_role": {                # Message count per role
                "system": int,
                "user": int,
                "assistant": int,
                "tool": int,
            },
            "compressed_count": int,    # Number of already-compressed messages
            "pinned_count": int,        # Number of pinned messages
        }

    Example:
        let stats = context_stats()
        if stats["usage_ratio"] > 0.8 {
            compress_context("auto")
        }
    """
    messages = _get_effective_history()
    if messages is None:
        return {
            "status": "error",
            "error": "No interpreter context available",
            "message_count": 0,
            "total_tokens": 0,
            "usage_ratio": 0.0,
            "max_tokens": 0,
            "by_role": {"system": 0, "user": 0, "assistant": 0, "tool": 0},
            "compressed_count": 0,
            "pinned_count": 0,
        }

    by_role = {"system": 0, "user": 0, "assistant": 0, "tool": 0}
    total_tokens = 0
    compressed_count = 0
    pinned_count = 0

    for msg in messages:
        role = getattr(msg, 'role', 'unknown')
        if role in by_role:
            by_role[role] += 1
        total_tokens += getattr(msg, 'token_count', 0)
        if getattr(msg, 'compressed', False):
            compressed_count += 1
        if getattr(msg, 'pinned', False):
            pinned_count += 1

    max_tokens = _get_max_tokens()
    usage_ratio = (total_tokens / max_tokens) if max_tokens > 0 else 0.0

    return {
        "status": "ok",
        "message_count": len(messages),
        "total_tokens": total_tokens,
        "usage_ratio": usage_ratio,
        "max_tokens": max_tokens,
        "by_role": by_role,
        "compressed_count": compressed_count,
        "pinned_count": pinned_count,
    }


def _context_usage() -> float:
    """Return current context usage ratio (0.0 to 1.0+).

    A lightweight alternative to context_stats() when only the usage ratio
    is needed. Commonly used by agents to decide whether to compress.

    Returns:
        float: tokens / max_tokens. Returns 0.0 if context unavailable.

    Example:
        if context_usage() > 0.7 {
            compress_context("auto")
        }
    """
    messages = _get_effective_history()
    if messages is None:
        return 0.0
    max_tokens = _get_max_tokens()
    if max_tokens == 0:
        return 0.0
    total_tokens = sum(getattr(msg, 'token_count', 0) for msg in messages)
    return total_tokens / max_tokens


def _get_message(uuid: str) -> dict:
    """Retrieve a single message by UUID.

    Returns a dict snapshot of the message's key fields, or an error dict
    if not found.

    Args:
        uuid: The UUID of the message to retrieve.

    Returns:
        dict with message data:
        {
            "status": "ok",
            "uuid": str,
            "role": str,
            "content": str,          # Text content (multimodal parts joined)
            "tool_call_id": str?,
            "tool_calls_count": int,
            "token_count": int,
            "compressed": bool,
            "pinned": bool,
        }
        Or on error: {"status": "error", "error": "..."}

    Example:
        let msg = get_message("abc-123-...")
        if msg["status"] == "ok" {
            print("Got: " + msg["content"])
        }
    """
    if not uuid:
        return {"status": "error", "error": "uuid is required"}

    msg = _find_message_by_uuid(uuid)
    if msg is None:
        return {"status": "error", "error": f"Message not found: {uuid}"}

    # For multimodal content (list), extract text
    content = msg.content
    if isinstance(content, list):
        content = "\n".join(
            p.get("text", "") for p in content
            if isinstance(p, dict) and p.get("type") == "text"
        )

    return {
        "status": "ok",
        "uuid": getattr(msg, 'uuid', ''),
        "role": msg.role,
        "content": content,
        "tool_call_id": msg.tool_call_id,
        "tool_calls_count": len(msg.tool_calls) if msg.tool_calls else 0,
        "token_count": getattr(msg, 'token_count', 0),
        "compressed": getattr(msg, 'compressed', False),
        "pinned": getattr(msg, 'pinned', False),
    }


# ---------------------------------------------------------------------------
# Mutation: delete_message, pin_message, unpin_message
# ---------------------------------------------------------------------------

def _delete_message(uuid: str) -> dict:
    """Delete a message by UUID.

    Removes the message from both the interpreter's history and the
    TranscriptStore (SSOT). Pinned or not, deletion always succeeds if
    the UUID is found.

    Args:
        uuid: The UUID of the message to delete.

    Returns:
        dict:
        {
            "status": "ok",
            "uuid": str,
            "deleted_tokens": int,
        }
        Or on error: {"status": "error", "error": "..."}

    Example:
        let r = delete_message("abc-123-...")
        if r["status"] == "ok" {
            print("Freed ~" + str(r["deleted_tokens"]) + " tokens")
        }

    Note:
        Deleting a message does not record a BoundaryMarker (it's a true
        deletion, not compression). Use with care — prefer pinning or
        compressing when the audit trail matters.
    """
    if not uuid:
        return {"status": "error", "error": "uuid is required"}

    msg = _find_message_by_uuid(uuid)
    if msg is None:
        return {"status": "error", "error": f"Message not found: {uuid}"}

    deleted_tokens = getattr(msg, 'token_count', 0)

    # Remove from interpreter history (list scan, stable even if multiple refs)
    if _interpreter_history is not None:
        try:
            _interpreter_history.remove(msg)
        except ValueError:
            pass

    # Remove from TranscriptStore (both in-memory transcript and uuid index)
    if _interpreter_agent_context is not None:
        store = getattr(_interpreter_agent_context, 'transcript_store', None)
        if store is not None:
            # Remove from uuid index
            store._uuid_index.pop(uuid, None)
            # Remove from in-memory transcript list
            try:
                store.transcript.remove(msg)
                store._dirty = True  # Invalidate view cache
            except ValueError:
                pass
            # Note: we do NOT remove from the persistent backend (JSONL/SQLite);
            # deletion is logical only, preserving the audit trail. A future
            # "delete" BoundaryMarker could make this explicit.

    return {
        "status": "ok",
        "uuid": uuid,
        "deleted_tokens": deleted_tokens,
    }


def _pin_message(uuid: str) -> dict:
    """Pin a message by UUID, making it immune to compression.

    Pinned messages are preserved by all 5 layers of graduated compression
    (Budget Reduction, Snip, Microcompact, Context Collapse, Auto-Compact).
    Use this to protect critical context: system prompts, key decisions,
    few-shot examples, etc.

    Args:
        uuid: The UUID of the message to pin.

    Returns:
        dict:
        {
            "status": "ok",
            "uuid": str,
            "pinned": true,
        }
        Or on error: {"status": "error", "error": "..."}

    Example:
        let msg_uuid = last_user_message_uuid()  // hypothetical
        pin_message(msg_uuid)
    """
    if not uuid:
        return {"status": "error", "error": "uuid is required"}

    msg = _find_message_by_uuid(uuid)
    if msg is None:
        return {"status": "error", "error": f"Message not found: {uuid}"}

    msg.pinned = True

    # If TranscriptStore holds a different reference, update it too
    if _interpreter_agent_context is not None:
        store = getattr(_interpreter_agent_context, 'transcript_store', None)
        if store is not None:
            ts_msg = store.get(uuid)
            if ts_msg is not None and hasattr(ts_msg, 'pinned'):
                ts_msg.pinned = True

    return {
        "status": "ok",
        "uuid": uuid,
        "pinned": True,
    }


def _unpin_message(uuid: str) -> dict:
    """Unpin a previously pinned message by UUID.

    After unpinning, the message becomes subject to normal compression again.

    Args:
        uuid: The UUID of the message to unpin.

    Returns:
        dict:
        {
            "status": "ok",
            "uuid": str,
            "pinned": false,
        }
        Or on error: {"status": "error", "error": "..."}
    """
    if not uuid:
        return {"status": "error", "error": "uuid is required"}

    msg = _find_message_by_uuid(uuid)
    if msg is None:
        return {"status": "error", "error": f"Message not found: {uuid}"}

    msg.pinned = False

    if _interpreter_agent_context is not None:
        store = getattr(_interpreter_agent_context, 'transcript_store', None)
        if store is not None:
            ts_msg = store.get(uuid)
            if ts_msg is not None and hasattr(ts_msg, 'pinned'):
                ts_msg.pinned = False

    return {
        "status": "ok",
        "uuid": uuid,
        "pinned": False,
    }


# ---------------------------------------------------------------------------
# Working Memory access (P1)
# ---------------------------------------------------------------------------
# WorkingMemory has 5 fields: task_description, active_files, recent_decisions,
# pending_todos, error_history. Exposed via a key-based API:
#   "task"          -> str (task_description)
#   "active_files"  -> list[str]
#   "decisions"     -> list[str]
#   "todos"         -> list[str]
#   "errors"        -> list[dict]

_WORKING_MEMORY_KEYS = frozenset({"task", "active_files", "decisions", "todos", "errors"})


def _get_working_memory() -> Any:
    """Return the active WorkingMemory instance or None."""
    if _interpreter_agent_context is None:
        return None
    if not getattr(_interpreter_agent_context, 'working_memory_enabled', False):
        return None
    return getattr(_interpreter_agent_context, 'working_memory', None)


def _working_memory_get(key: str = "") -> dict:
    """Read working memory contents.

    If key is empty, returns the entire working memory snapshot.
    If key is provided, returns just that field.

    Args:
        key: One of "" (all), "task", "active_files", "decisions", "todos", "errors".

    Returns:
        dict with the requested data:
        {
            "status": "ok",
            "data": ...,  # the value (type depends on key)
        }
        Or on error: {"status": "error", "error": "..."}
    """
    wm = _get_working_memory()
    if wm is None:
        return {"status": "error", "error": "Working memory not available"}

    if not key:
        return {
            "status": "ok",
            "data": {
                "task": wm.task_description,
                "active_files": list(wm.active_files),
                "decisions": list(wm.recent_decisions),
                "todos": list(wm.pending_todos),
                "errors": list(wm.error_history),
            },
        }

    if key not in _WORKING_MEMORY_KEYS:
        return {
            "status": "error",
            "error": f"Unknown working memory key: {key}. "
                     f"Valid keys: {sorted(_WORKING_MEMORY_KEYS)}",
        }

    if key == "task":
        return {"status": "ok", "data": wm.task_description}
    if key == "active_files":
        return {"status": "ok", "data": list(wm.active_files)}
    if key == "decisions":
        return {"status": "ok", "data": list(wm.recent_decisions)}
    if key == "todos":
        return {"status": "ok", "data": list(wm.pending_todos)}
    if key == "errors":
        return {"status": "ok", "data": list(wm.error_history)}
    return {"status": "error", "error": "unreachable"}


def _working_memory_set(key: str, value: Any) -> dict:
    """Set a working memory field.

    For scalar keys ("task"): value replaces the current value.
    For list keys ("active_files", "decisions", "todos"): value is APPENDED
    (or replaces the list if value is itself a list).
    For "errors": value should be a dict with "command" and "error" keys;
    it is appended to error_history.

    Args:
        key: "task" | "active_files" | "decisions" | "todos" | "errors"
        value: The value to set or append.

    Returns:
        dict: {"status": "ok"} or {"status": "error", "error": "..."}
    """
    wm = _get_working_memory()
    if wm is None:
        return {"status": "error", "error": "Working memory not available"}

    if key not in _WORKING_MEMORY_KEYS:
        return {
            "status": "error",
            "error": f"Unknown working memory key: {key}. "
                     f"Valid keys: {sorted(_WORKING_MEMORY_KEYS)}",
        }

    if key == "task":
        wm.task_description = str(value) if value is not None else ""
    elif key == "active_files":
        if isinstance(value, list):
            wm.active_files = list(value)
        else:
            wm._add_active_file(str(value))
    elif key == "decisions":
        if isinstance(value, list):
            wm.recent_decisions = list(value)
        else:
            wm._add_decision(str(value))
    elif key == "todos":
        if isinstance(value, list):
            wm.pending_todos = list(value)
        else:
            wm._add_todo(str(value))
    elif key == "errors":
        if isinstance(value, list):
            wm.error_history = list(value)
        elif isinstance(value, dict):
            wm._add_error(value.get("command", ""), value.get("error", ""))
        else:
            return {"status": "error", "error": "errors value must be dict or list"}

    return {"status": "ok"}


def _working_memory_remove(key: str, item: Any = None) -> dict:
    """Remove a working memory entry.

    For "task": clears the task description.
    For list keys: if item is provided, removes that specific item;
                   if item is None, clears the entire list.
    For "errors": if item (a dict or index) is provided, removes it;
                  else clears all.

    Args:
        key: "task" | "active_files" | "decisions" | "todos" | "errors"
        item: Optional specific item to remove (for list keys).

    Returns:
        dict: {"status": "ok"} or {"status": "error", "error": "..."}
    """
    wm = _get_working_memory()
    if wm is None:
        return {"status": "error", "error": "Working memory not available"}

    if key not in _WORKING_MEMORY_KEYS:
        return {
            "status": "error",
            "error": f"Unknown working memory key: {key}. "
                     f"Valid keys: {sorted(_WORKING_MEMORY_KEYS)}",
        }

    if key == "task":
        wm.task_description = ""
    elif key == "active_files":
        if item is None:
            wm.active_files.clear()
        else:
            try:
                wm.active_files.remove(str(item))
            except ValueError:
                pass
    elif key == "decisions":
        if item is None:
            wm.recent_decisions.clear()
        else:
            try:
                wm.recent_decisions.remove(str(item))
            except ValueError:
                pass
    elif key == "todos":
        if item is None:
            wm.pending_todos.clear()
        else:
            try:
                wm.pending_todos.remove(str(item))
            except ValueError:
                pass
    elif key == "errors":
        if item is None:
            wm.error_history.clear()
        elif isinstance(item, int):
            if 0 <= item < len(wm.error_history):
                wm.error_history.pop(item)
        else:
            try:
                wm.error_history.remove(item)
            except ValueError:
                pass

    return {"status": "ok"}


def _working_memory_clear() -> dict:
    """Clear all working memory.

    Resets task_description, active_files, decisions, todos, and errors.
    Auto-populated fields will repopulate on subsequent tool calls/messages.

    Returns:
        dict: {"status": "ok"} or {"status": "error", "error": "..."}
    """
    wm = _get_working_memory()
    if wm is None:
        return {"status": "error", "error": "Working memory not available"}
    wm.clear()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Runtime configuration (P2)
# ---------------------------------------------------------------------------

def _set_compression_strategy(strategy: str) -> dict:
    """Set the compression strategy at runtime.

    Overrides the strategy declared in the agent's `context {}` block.

    Args:
        strategy: "graduated" | "traditional" | "none"

    Returns:
        dict: {"status": "ok", "strategy": str} or error
    """
    if _interpreter_agent_context is None:
        return {"status": "error", "error": "AgentContextManager not available"}
    if strategy not in ("none", "graduated", "traditional"):
        return {
            "status": "error",
            "error": f"Unknown strategy: {strategy}. Use 'graduated' | 'traditional' | 'none'",
        }
    _interpreter_agent_context.compression_strategy = strategy
    return {"status": "ok", "strategy": strategy}


def _set_context_window(tokens: int) -> dict:
    """Set the context window size (max tokens) at runtime.

    Args:
        tokens: Positive integer, new max_tokens.

    Returns:
        dict: {"status": "ok", "max_tokens": int} or error
    """
    if _interpreter_history_manager is None:
        return {"status": "error", "error": "HistoryManager not available"}
    if not isinstance(tokens, int) or tokens <= 0:
        return {"status": "error", "error": "tokens must be a positive integer"}
    _interpreter_history_manager.MAX_TOKENS = tokens
    return {"status": "ok", "max_tokens": tokens}


def _set_working_memory_enabled(enabled: bool) -> dict:
    """Enable or disable working memory at runtime.

    Args:
        enabled: True to enable, False to disable.

    Returns:
        dict: {"status": "ok", "enabled": bool} or error
    """
    if _interpreter_agent_context is None:
        return {"status": "error", "error": "AgentContextManager not available"}
    _interpreter_agent_context.working_memory_enabled = bool(enabled)
    return {"status": "ok", "enabled": bool(enabled)}


def _set_cache_aware(enabled: bool) -> dict:
    """Enable or disable cache-aware compression at runtime.

    Args:
        enabled: True to enable, False to disable.

    Returns:
        dict: {"status": "ok", "cache_aware": bool} or error
    """
    if _interpreter_agent_context is None:
        return {"status": "error", "error": "AgentContextManager not available"}
    _interpreter_agent_context.cache_aware_enabled = bool(enabled)
    return {"status": "ok", "cache_aware": bool(enabled)}


def _get_context_config() -> dict:
    """Return the current context management configuration.

    Returns:
        dict with current settings:
        {
            "status": "ok",
            "compression_strategy": str,
            "max_tokens": int,
            "working_memory_enabled": bool,
            "cache_aware_enabled": bool,
            "working_memory_max_tokens": int,
        }
    """
    if _interpreter_agent_context is None or _interpreter_history_manager is None:
        return {
            "status": "error",
            "error": "Context managers not available",
        }
    wm = getattr(_interpreter_agent_context, 'working_memory', None)
    return {
        "status": "ok",
        "compression_strategy": getattr(_interpreter_agent_context, 'compression_strategy', 'none'),
        "max_tokens": getattr(_interpreter_history_manager, 'MAX_TOKENS', 0),
        "working_memory_enabled": getattr(_interpreter_agent_context, 'working_memory_enabled', False),
        "cache_aware_enabled": getattr(_interpreter_agent_context, 'cache_aware_enabled', False),
        "working_memory_max_tokens": getattr(wm, 'max_tokens', 0) if wm else 0,
    }


# ---------------------------------------------------------------------------
# Fine-grained message mutation (P2)
# ---------------------------------------------------------------------------

def _insert_message(role: str, content: Any, position: str = "end") -> dict:
    """Insert a new message into the conversation context.

    Useful for seeding few-shot examples, injecting synthetic instructions,
    or backfilling context that wasn't part of the normal conversation flow.

    Args:
        role: "system" | "user" | "assistant" | "tool"
        content: Message content (str or list[dict] for multimodal)
        position: "end" (default), "start", or an integer index

    Returns:
        dict: {"status": "ok", "uuid": str, "index": int}
    """
    from helen.runtime.history import Message
    if _interpreter_history is None:
        return {"status": "error", "error": "No interpreter context"}
    if role not in ("system", "user", "assistant", "tool"):
        return {"status": "error", "error": f"Invalid role: {role}"}

    msg = Message(role=role, content=content)
    # Assign UUID via TranscriptStore if available (it will assign on append)
    if _interpreter_agent_context is not None:
        store = getattr(_interpreter_agent_context, 'transcript_store', None)
        if store is not None:
            store.append(msg)

    # Insert into interpreter history
    if position == "end" or position is None:
        _interpreter_history.append(msg)
        idx = len(_interpreter_history) - 1
    elif position == "start":
        _interpreter_history.insert(0, msg)
        idx = 0
    elif isinstance(position, int):
        idx = max(0, min(position, len(_interpreter_history)))
        _interpreter_history.insert(idx, msg)
    else:
        return {"status": "error", "error": f"Invalid position: {position}"}

    return {"status": "ok", "uuid": msg.uuid, "index": idx}


def _replace_message(uuid: str, new_content: Any) -> dict:
    """Replace the content of an existing message by UUID.

    Preserves role, tool_calls, tool_call_id, pinned, and other metadata.
    Clears cached token_count so it is recomputed.

    Args:
        uuid: UUID of the message to replace.
        new_content: New content (str or list[dict] for multimodal).

    Returns:
        dict: {"status": "ok", "uuid": str, "old_tokens": int, "new_tokens": int}
    """
    if not uuid:
        return {"status": "error", "error": "uuid is required"}
    msg = _find_message_by_uuid(uuid)
    if msg is None:
        return {"status": "error", "error": f"Message not found: {uuid}"}

    old_tokens = getattr(msg, 'token_count', 0)
    msg.content = new_content
    msg._token_count = 0  # Force recomputation
    new_tokens = msg.token_count

    return {
        "status": "ok",
        "uuid": uuid,
        "old_tokens": old_tokens,
        "new_tokens": new_tokens,
    }


# ---------------------------------------------------------------------------
# Query helpers (P3)
# ---------------------------------------------------------------------------

def _search_context(query: str, role: str = "", limit: int = 20) -> dict:
    """Search conversation history for messages containing query text.

    Case-insensitive substring search over message content. Returns matching
    messages with snippet context.

    Args:
        query: Text to search for (case-insensitive).
        role: Optional filter by role ("system"|"user"|"assistant"|"tool").
              Empty string means all roles.
        limit: Max number of results to return (default 20).

    Returns:
        dict:
        {
            "status": "ok",
            "matches": [
                {"uuid": str, "role": str, "snippet": str, "index": int},
                ...
            ],
            "total_matches": int,
        }
    """
    messages = _get_effective_history()
    if messages is None:
        return {"status": "error", "error": "No interpreter context", "matches": [], "total_matches": 0}
    if not query:
        return {"status": "error", "error": "query is required", "matches": [], "total_matches": 0}

    query_lower = query.lower()
    matches = []
    total = 0

    for i, msg in enumerate(messages):
        if role and msg.role != role:
            continue
        # Extract text from content
        content = msg.content
        if isinstance(content, list):
            content = "\n".join(
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        content_str = str(content)
        if query_lower in content_str.lower():
            total += 1
            if len(matches) < limit:
                # Generate a snippet around the match
                lower_content = content_str.lower()
                pos = lower_content.find(query_lower)
                start = max(0, pos - 40)
                end = min(len(content_str), pos + len(query) + 40)
                snippet = content_str[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content_str):
                    snippet = snippet + "..."
                matches.append({
                    "uuid": getattr(msg, 'uuid', ''),
                    "role": msg.role,
                    "snippet": snippet,
                    "index": i,
                })

    return {"status": "ok", "matches": matches, "total_matches": total}


def _context_slice(start: int = 0, end: int = -1, role: str = "") -> dict:
    """Extract a slice of the conversation history.

    Returns a list of message snapshots (dicts) within the given index range,
    optionally filtered by role.

    Args:
        start: Start index (inclusive, default 0).
        end: End index (exclusive, default -1 = end of history).
        role: Optional role filter (empty = all roles).

    Returns:
        dict:
        {
            "status": "ok",
            "messages": [
                {"uuid": str, "role": str, "content": str, "token_count": int, ...},
                ...
            ],
            "count": int,
        }
    """
    if _interpreter_history is None:
        return {"status": "error", "error": "No interpreter context", "messages": [], "count": 0}

    n = len(_interpreter_history)
    if end < 0:
        end = n
    start = max(0, min(start, n))
    end = max(start, min(end, n))

    messages = []
    for i in range(start, end):
        msg = _interpreter_history[i]
        if role and msg.role != role:
            continue
        content = msg.content
        if isinstance(content, list):
            content = "\n".join(
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        messages.append({
            "uuid": getattr(msg, 'uuid', ''),
            "role": msg.role,
            "content": str(content),
            "tool_call_id": msg.tool_call_id,
            "token_count": getattr(msg, 'token_count', 0),
            "compressed": getattr(msg, 'compressed', False),
            "pinned": getattr(msg, 'pinned', False),
            "index": i,
        })

    return {"status": "ok", "messages": messages, "count": len(messages)}


# ---------------------------------------------------------------------------
# Multi-agent context transfer (P2/P3)
# ---------------------------------------------------------------------------

def _export_context() -> dict:
    """Export the current conversation context as a serializable dict.

    Useful for:
    - Transferring context to another agent via Channel
    - Saving context to disk for later replay
    - Forking context for parallel exploration

    Returns:
        dict:
        {
            "status": "ok",
            "context": {
                "messages": [
                    {"role": str, "content": str, "uuid": str, ...},
                    ...
                ],
                "working_memory": {...} | None,
                "config": {...},
            },
        }
    """
    if _interpreter_history is None:
        return {"status": "error", "error": "No interpreter context"}

    messages = []
    for msg in _interpreter_history:
        content = msg.content
        if isinstance(content, list):
            content = "\n".join(
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        messages.append({
            "role": msg.role,
            "content": str(content),
            "tool_calls": msg.tool_calls,
            "tool_call_id": msg.tool_call_id,
            "uuid": getattr(msg, 'uuid', ''),
            "compressed": getattr(msg, 'compressed', False),
            "pinned": getattr(msg, 'pinned', False),
        })

    # Export working memory if available
    wm_data = None
    wm = _get_working_memory()
    if wm is not None:
        wm_data = {
            "task": wm.task_description,
            "active_files": list(wm.active_files),
            "decisions": list(wm.recent_decisions),
            "todos": list(wm.pending_todos),
            "errors": list(wm.error_history),
        }

    config = _get_context_config()

    return {
        "status": "ok",
        "context": {
            "messages": messages,
            "working_memory": wm_data,
            "config": config,
        },
    }


def _import_context(data: dict) -> dict:
    """Import a previously exported context into the current conversation.

    Replaces the current conversation history with the exported messages.
    Optionally restores working memory and config.

    Args:
        data: A dict as returned by export_context()["context"].

    Returns:
        dict:
        {
            "status": "ok",
            "imported_messages": int,
            "imported_working_memory": bool,
        }
    """
    from helen.runtime.history import Message
    if _interpreter_history is None:
        return {"status": "error", "error": "No interpreter context"}
    if not isinstance(data, dict):
        return {"status": "error", "error": "data must be a dict"}

    messages_data = data.get("messages", [])
    if not isinstance(messages_data, list):
        return {"status": "error", "error": "messages must be a list"}

    # Clear current history
    _interpreter_history.clear()

    # Import messages
    imported = 0
    for m in messages_data:
        msg = Message(
            role=m.get("role", "user"),
            content=m.get("content", ""),
            tool_calls=m.get("tool_calls", []),
            tool_call_id=m.get("tool_call_id"),
            uuid=m.get("uuid", ""),
            compressed=m.get("compressed", False),
            pinned=m.get("pinned", False),
        )
        _interpreter_history.append(msg)
        # Also register with TranscriptStore if available
        if _interpreter_agent_context is not None:
            store = getattr(_interpreter_agent_context, 'transcript_store', None)
            if store is not None and not msg.uuid:
                store.append(msg)  # assigns UUID
        imported += 1

    # Import working memory if present
    wm_imported = False
    wm_data = data.get("working_memory")
    if wm_data and _interpreter_agent_context is not None:
        wm = getattr(_interpreter_agent_context, 'working_memory', None)
        if wm is not None:
            wm.task_description = wm_data.get("task", "")
            wm.active_files = list(wm_data.get("active_files", []))
            wm.recent_decisions = list(wm_data.get("decisions", []))
            wm.pending_todos = list(wm_data.get("todos", []))
            wm.error_history = list(wm_data.get("errors", []))
            wm_imported = True

    return {
        "status": "ok",
        "imported_messages": imported,
        "imported_working_memory": wm_imported,
    }


def _fork_context() -> dict:
    """Create a deep-copy snapshot of the current context.

    Returns the same structure as export_context(), but explicitly meant for
    fork-on-write scenarios: the caller can modify the fork without affecting
    the original, then optionally merge back via import_context().

    Returns:
        dict: same as export_context()
    """
    return _export_context()


def _restore_context(session_id: str) -> dict:
    """Restore active context from a previous transcript session.

    This is a convenience function that bridges the gap between TranscriptStore
    (persistent audit trail) and active context (what the LLM actually sees).
    It:

    1. Reads the transcript of the specified session
    2. Converts Message objects to the format import_context() expects,
       preserving all fields (role, content, tool_calls, tool_call_id,
       compressed, pinned, uuid)
    3. Calls import_context() to populate the current active context

    Unlike ``resume_session()``, which only swaps the TranscriptStore reference,
    ``restore_context()`` populates ``_interpreter_history`` so the LLM actually
    sees the restored messages on the next call.

    Args:
        session_id: The session ID to restore from.

    Returns:
        dict:
        {
            "status": "ok" | "error",
            "restored_messages": int,        # Only on success
            "session_id": str,               # Only on success
            "boundary_markers": int,         # Skipped compression boundaries
            "note": str,                     # Hint about working_memory
        }

    Limitations:
        Only messages are restored. Working memory and context config are NOT
        persisted per-session in the transcript — they remain at their current
        values. Use ``working_memory_set()`` / ``set_compression_strategy()``
        etc. afterwards if you need to restore those manually.

    Example:
        // List past sessions
        let sessions = list_sessions()
        for s in sessions {
            print("{s.session_id}: {s.modified_at}")
        }

        // Restore a specific session into active context
        let r = restore_context("session_1783492628_d9d9c0aa")
        if r["status"] == "ok" {
            print("Restored " + str(r["restored_messages"]) + " messages")
        }
    """
    if not session_id:
        return {"status": "error", "error": "session_id is required"}

    if _interpreter_agent_context is None:
        return {"status": "error", "error": "No interpreter agent context"}

    # Import required modules
    from helen.runtime.config import resolve_session_dir
    from helen.runtime.session_manager import SessionManager
    from helen.runtime.transcript_store import (
        BoundaryMarker,
        JSONLBackend,
        SQLiteBackend,
        TranscriptStore,
    )
    from helen.runtime.config import get_transcript_config

    try:
        session_dir, _scope = resolve_session_dir()
        manager = SessionManager(base_dir=session_dir)

        # Check if session exists
        if not manager.session_exists(session_id):
            return {
                "status": "error",
                "error": f"Session not found: {session_id}",
            }

        # Get transcript path and load store
        transcript_path = manager.get_session_path(session_id)
        config = get_transcript_config()
        backend_type = config.get("backend", "jsonl")
        max_memory_items = config.get("max_memory_items", 1000)

        if backend_type == "sqlite":
            sqlite_path = transcript_path.with_suffix(".db")
            backend = SQLiteBackend(sqlite_path)
        else:
            backend = JSONLBackend(transcript_path)

        loaded_store = TranscriptStore.load_from_backend(backend, max_memory_items)

        # Convert Messages to import_context format, preserving all fields.
        # Skip BoundaryMarkers (they are compression audit trail, not content).
        messages = []
        boundary_count = 0
        for item in loaded_store.transcript:
            if isinstance(item, BoundaryMarker):
                boundary_count += 1
                continue
            # item is a Message (imported from helen.runtime.history)
            content = item.content
            if isinstance(content, list):
                # Multimodal content — flatten to text for active context
                content = "\n".join(
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            messages.append({
                "role": item.role,
                "content": str(content),
                "tool_calls": list(item.tool_calls) if item.tool_calls else [],
                "tool_call_id": item.tool_call_id,
                "uuid": item.uuid,
                "compressed": item.compressed,
                "pinned": item.pinned,
            })

        if not messages:
            return {
                "status": "error",
                "error": f"Session {session_id} has no messages",
            }

        # Delegate to import_context to populate _interpreter_history
        import_result = _import_context({"messages": messages})

        if import_result.get("status") != "ok":
            return {
                "status": "error",
                "error": f"import_context failed: {import_result.get('error')}",
            }

        logger.info(
            "Restored context from session %s: %d messages, %d boundary markers skipped",
            session_id,
            len(messages),
            boundary_count,
        )

        return {
            "status": "ok",
            "restored_messages": len(messages),
            "session_id": session_id,
            "boundary_markers": boundary_count,
            "note": (
                "Working memory and context config are not persisted per-session. "
                "Use working_memory_set() / set_compression_strategy() to restore manually."
            ),
        }

    except Exception as e:
        logger.error("Failed to restore context from session %s: %s", session_id, e)
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Lifecycle hooks (P1)
# ---------------------------------------------------------------------------
# Compression callback: called after each compression event.
# Stored as a callable that takes a dict of stats.

_compression_callback = None
_context_overflow_callback = None


def _on_compression(callback: Any = None) -> dict:
    """Register a callback to be invoked after each context compression.

    The callback receives a dict with compression stats:
    {
        "layer": str,              # e.g., "graduated_layer_1"
        "original_tokens": int,
        "compressed_tokens": int,
        "original_messages": int,
        "compressed_messages": int,
    }

    Pass None to clear the callback.

    Note: The callback is invoked from the Python runtime, not Helen code.
    In Helen programs, pass the name of a Helen function as a string — the
    runtime will resolve it via the interpreter environment at call time.

    Args:
        callback: Callable, Helen function name (str), or None.

    Returns:
        dict: {"status": "ok", "previous": <previous callback or None>}
    """
    global _compression_callback
    previous = _compression_callback
    _compression_callback = callback
    return {"status": "ok", "previous": previous}


def _on_context_overflow(callback: Any = None) -> dict:
    """Register a callback to be invoked when context usage exceeds a threshold.

    Currently a placeholder for future implementation — reserved for a hook
    that fires before Layer 5 is triggered, giving the user code a chance
    to intervene (e.g., by clearing non-essential context, pinning critical
    messages, or aborting the task).

    Args:
        callback: Callable, Helen function name (str), or None.

    Returns:
        dict: {"status": "ok", "previous": <previous callback or None>}
    """
    global _context_overflow_callback
    previous = _context_overflow_callback
    _context_overflow_callback = callback
    return {"status": "ok", "previous": previous}
