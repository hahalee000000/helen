"""Context management functions for Helen stdlib.

Provides functions to manage LLM conversation context:
- clear_context(): Clear conversation history
- compress_context(): Trigger context compression
- compress_context_target(): Phase 1 - Targeted compression by message type

These functions allow applications to control context growth in long-running agents.
"""

from __future__ import annotations

from typing import Any

# Global reference to interpreter's history manager (set by interpreter)
_interpreter_history_manager = None
_interpreter_history = None


def _set_interpreter_context(history: list, history_manager: Any) -> None:
    """Set the interpreter's history and history manager for context management.

    Called by the interpreter during initialization to provide stdlib functions
    with access to the conversation history.

    Args:
        history: The interpreter's _history list
        history_manager: The interpreter's HistoryManager instance
    """
    global _interpreter_history, _interpreter_history_manager
    _interpreter_history = history
    _interpreter_history_manager = history_manager


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
    initial_tokens = sum(msg._token_count for msg in _interpreter_history if hasattr(msg, '_token_count'))

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
                    original_tokens = msg._token_count
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
                    original_tokens = msg._token_count
                    if msg.role == "user":
                        msg.content = f"[Earlier user message cleared]"
                    elif msg.role == "assistant":
                        if msg.tool_calls:
                            msg.content = f"[Earlier assistant tool call cleared]"
                        else:
                            msg.content = f"[Earlier assistant response cleared]"
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
    final_tokens = sum(msg._token_count for msg in _interpreter_history if hasattr(msg, '_token_count'))
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

    # Calculate total tokens using Message.token_count attribute
    # Each message has a cached _token_count that is lazily computed
    estimated_tokens = sum(msg._token_count for msg in _interpreter_history if hasattr(msg, '_token_count'))

    cleared_count = len(_interpreter_history)
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

    Args:
        strategy: Compression strategy to use:
            - "auto": Let HistoryManager decide (default, based on token threshold)
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
        // Auto-compress when context is large
        let result = compress_context("auto")
        if result["status"] == "ok" {
            print("Compressed from " + str(result["original_tokens"]) +
                  " to " + str(result["compressed_tokens"]) + " tokens")
        }

        // Force summarize compression
        compress_context("summarize")

    Note:
        - "auto" strategy only compresses if token count exceeds threshold
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

    if strategy == "none":
        # Calculate tokens using Message._token_count
        total_tokens = sum(msg._token_count for msg in _interpreter_history if hasattr(msg, '_token_count'))
        return {
            "status": "ok",
            "original_messages": len(_interpreter_history),
            "compressed_messages": len(_interpreter_history),
            "original_tokens": total_tokens,
            "compressed_tokens": total_tokens,
            "strategy": "none",
        }

    # Get stats before compression (using Message._token_count)
    original_count = len(_interpreter_history)
    original_tokens = sum(msg._token_count for msg in _interpreter_history if hasattr(msg, '_token_count'))

    # Perform compression
    if strategy == "auto":
        # Use HistoryManager's enforce_limit (respects compression_mode setting)
        _interpreter_history_manager.enforce_limit(_interpreter_history)
    elif strategy == "summarize":
        # Force summarize compression with default budget
        from helen.runtime.history import HISTORY_BUDGET_RATIO
        budget = int(_interpreter_history_manager.MAX_TOKENS * HISTORY_BUDGET_RATIO)
        _interpreter_history_manager._summarize_compress(_interpreter_history, budget)
    elif strategy == "truncate":
        # Force truncate compression with default budget
        from helen.runtime.history import HISTORY_BUDGET_RATIO
        budget = int(_interpreter_history_manager.MAX_TOKENS * HISTORY_BUDGET_RATIO)
        _interpreter_history_manager._truncate_compress(_interpreter_history, budget)
    else:
        return {
            "status": "error",
            "error": f"Unknown compression strategy: {strategy}",
            "original_messages": original_count,
            "compressed_messages": original_count,
            "strategy": strategy,
        }

    # Get stats after compression (using Message._token_count)
    compressed_count = len(_interpreter_history)
    compressed_tokens = sum(msg._token_count for msg in _interpreter_history if hasattr(msg, '_token_count'))

    return {
        "status": "ok",
        "original_messages": original_count,
        "compressed_messages": compressed_count,
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "strategy": strategy,
    }
