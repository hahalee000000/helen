"""Context management functions for Helen stdlib.

Provides functions to manage LLM conversation context:
- clear_context(): Clear conversation history
- compress_context(): Trigger context compression

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

    # Estimate tokens before clearing (rough estimate: 4 chars per token)
    total_chars = sum(len(msg.get("content", "")) for msg in _interpreter_history if isinstance(msg, dict))
    estimated_tokens = total_chars // 4

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
        return {
            "status": "ok",
            "original_messages": len(_interpreter_history),
            "compressed_messages": len(_interpreter_history),
            "original_tokens": 0,
            "compressed_tokens": 0,
            "strategy": "none",
        }

    # Get stats before compression
    original_count = len(_interpreter_history)
    original_tokens = _interpreter_history_manager.estimate_tokens(_interpreter_history)

    # Perform compression
    if strategy == "auto":
        # Use HistoryManager's default compression (threshold-based)
        _interpreter_history_manager.compress_if_needed(_interpreter_history)
    elif strategy == "summarize":
        # Force summarize compression
        _interpreter_history_manager._compress_summarize(_interpreter_history)
    elif strategy == "truncate":
        # Force truncate compression (keep last 10 messages)
        _interpreter_history_manager._compress_truncate(_interpreter_history, keep_last=10)
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
    compressed_tokens = _interpreter_history_manager.estimate_tokens(_interpreter_history)

    return {
        "status": "ok",
        "original_messages": original_count,
        "compressed_messages": compressed_count,
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "strategy": strategy,
    }
