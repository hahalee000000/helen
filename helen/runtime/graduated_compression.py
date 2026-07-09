"""Graduated compression pipeline for Helen context management.

Phase 2: Five-layer graduated compression pipeline.

Design Philosophy: "Cheapest Move First"
- Layer 1-4: Zero inference cost (no LLM calls)
- Layer 5: High cost (LLM summarization) - last resort

Thresholds:
- 60%: Layer 1 - Budget Reduction
- 70%: Layer 2 - Snip
- 80%: Layer 3 - Microcompact
- 90%: Layer 4 - Context Collapse
- 95%: Layer 5 - LLM Semantic Summarization

v1.17: Supports multimodal content (Message.content can be str or list[dict]).
       All content accesses use _message_text() helper for safe string extraction.
"""

from __future__ import annotations

import logging
from typing import Callable

from helen.runtime.history import Message, _message_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 2: Compression thresholds and constants
# ---------------------------------------------------------------------------

COMPRESSION_THRESHOLDS = {
    "budget_reduction": 0.60,   # 60% - Replace large tool outputs
    "snip": 0.70,               # 70% - Drop stale turns
    "microcompact": 0.80,       # 80% - Clear old tool results
    "context_collapse": 0.90,   # 90% - Archive and collapse
    "auto_compact": 0.95,       # 95% - LLM semantic compression
}

# Layer names
LAYER_NONE = "none"
LAYER_BUDGET_REDUCTION = "budget_reduction"
LAYER_SNIP = "snip"
LAYER_MICROCOMPACT = "microcompact"
LAYER_CONTEXT_COLLAPSE = "context_collapse"
LAYER_AUTO_COMPACT = "auto_compact"

# Phase 2: Configuration constants
BUDGET_REDUCTION_MAX_CHARS = 4000  # Max chars for tool output before replacement
SNIP_KEEP_RECENT = 8               # Number of recent turns to keep in snip
MICROCOMPACT_KEEP_RECENT = 5       # Number of recent tool results to keep
CONTEXT_COLLAPSE_THRESHOLD = 20    # Number of turns before collapse


def graduated_compress(
    history: list[Message],
    usage_ratio: float,
    max_tokens: int | None = None,
    llm_client: Callable | None = None,
) -> tuple[list[Message], str]:
    """Graduated compression pipeline - cheapest move first.

    Phase 2: Implements five-layer graduated compression.

    Args:
        history: Conversation history
        usage_ratio: Current usage ratio (0.0-1.0)
        max_tokens: Maximum context window tokens. Defaults to DEFAULT_CONTEXT_WINDOW.
        llm_client: Optional LLM client for Layer 5 semantic summarization.
                    If None, Layer 5 falls back to structural summarization.
                    Expected signature: llm_client(messages) -> str

    Returns:
        (compressed_history, layer_used)
        - compressed_history: Compressed history
        - layer_used: Which compression layer was used
          "none" | "budget_reduction" | "snip" | "microcompact" |
          "context_collapse" | "auto_compact"

    Guarantees:
        - Each layer only triggers when cheaper layers are insufficient
        - Zero-cost layers (Layer 1-4) never call LLM
        - Layer 5 only triggers when all previous layers are insufficient
        - Layer 5 uses LLM when llm_client is provided, otherwise structural
    """
    from helen.runtime.token_utils import DEFAULT_CONTEXT_WINDOW
    if max_tokens is None:
        max_tokens = DEFAULT_CONTEXT_WINDOW

    if not history:
        return history, LAYER_NONE

    current_history = history
    current_ratio = usage_ratio
    last_layer = LAYER_NONE

    # Layer 1: Budget Reduction (60%)
    if current_ratio >= COMPRESSION_THRESHOLDS["budget_reduction"]:
        new_history = _budget_reduction(current_history)
        new_ratio = _calculate_usage_ratio(new_history, max_tokens)
        # Only mark as applied if it actually compressed something
        if new_ratio < current_ratio:
            current_history = new_history
            current_ratio = new_ratio
            last_layer = LAYER_BUDGET_REDUCTION

    # Layer 2: Snip (70%)
    if current_ratio >= COMPRESSION_THRESHOLDS["snip"]:
        new_history = _snip(current_history, keep_recent=SNIP_KEEP_RECENT)
        new_ratio = _calculate_usage_ratio(new_history, max_tokens)
        if new_ratio < current_ratio:
            current_history = new_history
            current_ratio = new_ratio
            last_layer = LAYER_SNIP

    # Layer 3: Microcompact (80%)
    if current_ratio >= COMPRESSION_THRESHOLDS["microcompact"]:
        new_history = _microcompact(current_history, keep_recent=MICROCOMPACT_KEEP_RECENT)
        new_ratio = _calculate_usage_ratio(new_history, max_tokens)
        if new_ratio < current_ratio:
            current_history = new_history
            current_ratio = new_ratio
            last_layer = LAYER_MICROCOMPACT

    # Layer 4: Context Collapse (90%)
    if current_ratio >= COMPRESSION_THRESHOLDS["context_collapse"]:
        new_history = _context_collapse(current_history)
        new_ratio = _calculate_usage_ratio(new_history, max_tokens)
        if new_ratio < current_ratio:
            current_history = new_history
            current_ratio = new_ratio
            last_layer = LAYER_CONTEXT_COLLAPSE

    # Layer 5: Auto-Compact (95%) - LLM semantic summarization (or structural fallback)
    if current_ratio >= COMPRESSION_THRESHOLDS["auto_compact"]:
        # Use LLM summarization if client is available, otherwise structural
        new_history = _auto_compact(current_history, llm_client=llm_client, target_tokens=max_tokens // 10)
        new_ratio = _calculate_usage_ratio(new_history, max_tokens)
        if new_ratio < current_ratio:
            current_history = new_history
            current_ratio = new_ratio
            last_layer = LAYER_AUTO_COMPACT
        else:
            # Last resort: aggressive snip keeping only last 4 messages
            if len(current_history) > 4:
                system_msgs = [m for m in current_history if m.role == "system"]
                recent = [m for m in current_history if m.role != "system"][-4:]
                current_history = system_msgs + recent
                last_layer = LAYER_AUTO_COMPACT
                logger.warning("Auto-Compact: aggressive snip (last resort)")

    # Return the last layer that actually compressed something
    return current_history, last_layer


# ---------------------------------------------------------------------------
# Phase 2: Layer 1 - Budget Reduction
# ---------------------------------------------------------------------------

def _budget_reduction(history: list[Message]) -> list[Message]:
    """Layer 1: Replace large tool outputs with reference pointers.

    Zero-cost operation (no LLM calls).

    For each tool result message:
    - If content > BUDGET_REDUCTION_MAX_CHARS → replace with pointer
    - Otherwise → keep as-is

    Returns:
        History with large tool outputs replaced
    """
    result = []
    for msg in history:
        # v1.17: Use _message_text to handle both str and list[dict] content
        content_text = _message_text(msg.content)
        if msg.role == "tool" and len(content_text) > BUDGET_REDUCTION_MAX_CHARS:
            # Replace large output with pointer
            tool_id = msg.tool_call_id or "unknown"
            preview = content_text[:200]
            msg_copy = Message(
                role=msg.role,
                content=f"[Tool result cleared: {tool_id}, {len(content_text)} chars]\nPreview: {preview}...",
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
                _token_count=0,  # Will be recalculated
                _model=msg._model,
                message_type=msg.message_type,
                priority=msg.priority,
                compressed=True,
            )
            result.append(msg_copy)
            logger.debug("Budget reduction: Replaced tool result %s (%d chars)",
                        tool_id, len(content_text))
        else:
            result.append(msg)

    return result


# ---------------------------------------------------------------------------
# Phase 2: Layer 2 - Snip
# ---------------------------------------------------------------------------

def _snip(history: list[Message], keep_recent: int = 8) -> list[Message]:
    """Layer 2: Drop stale conversation turns.

    Zero-cost operation (no LLM calls).

    Identifies "stale" turns (older than keep_recent) and drops them.
    Always preserves system messages.

    Returns:
        History with stale turns removed
    """
    if len(history) <= keep_recent:
        return history  # Not enough messages to snip

    # Separate system messages and conversation turns
    system_msgs = [msg for msg in history if msg.role == "system"]
    conversation_msgs = [msg for msg in history if msg.role != "system"]

    if len(conversation_msgs) <= keep_recent:
        return history  # Not enough conversation to snip

    # Keep only the most recent conversation turns
    recent = conversation_msgs[-keep_recent:]

    # Reconstruct: system messages + recent conversation
    result = system_msgs + recent

    logger.debug("Snip: Dropped %d stale turns, kept %d recent",
                len(conversation_msgs) - keep_recent, keep_recent)

    return result


# ---------------------------------------------------------------------------
# Phase 2: Layer 3 - Microcompact
# ---------------------------------------------------------------------------

def _microcompact(history: list[Message], keep_recent: int = 5) -> list[Message]:
    """Layer 3: Clear old tool results, preserve tool_use decisions.

    Zero-cost operation (no LLM calls).

    Core innovation: Preserves "actions" (tool_use blocks) but clears "data" (tool_result content).

    For each tool result message:
    - If it's one of the keep_recent most recent → preserve
    - Otherwise → replace content with placeholder

    Returns:
        History with old tool results cleared
    """
    # Find all tool result messages
    tool_result_indices = []
    for i, msg in enumerate(history):
        if msg.role == "tool":
            tool_result_indices.append(i)

    if len(tool_result_indices) <= keep_recent:
        return history  # Not enough tool results to microcompact

    # Determine which tool results to clear (keep recent ones)
    indices_to_clear = tool_result_indices[:-keep_recent]

    result = list(history)  # Copy
    for idx in indices_to_clear:
        msg = result[idx]
        if not msg.compressed:  # Only clear if not already compressed
            tool_id = msg.tool_call_id or "unknown"
            msg_copy = Message(
                role=msg.role,
                content=f"[Tool result cleared: {tool_id}]",
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
                _token_count=0,  # Will be recalculated
                _model=msg._model,
                message_type=msg.message_type,
                priority=msg.priority,
                compressed=True,
            )
            result[idx] = msg_copy
            logger.debug("Microcompact: Cleared tool result %s", tool_id)

    return result


# ---------------------------------------------------------------------------
# Phase 2: Layer 4 - Context Collapse (with temporal preservation)
# ---------------------------------------------------------------------------

def _context_collapse(history: list[Message]) -> list[Message]:
    """Layer 4: Archive and project collapsed view with temporal preservation.

    Zero-cost operation (no LLM calls).

    Inspired by RCC (Recurrent Context Compression) and CogCanvas:
    - Preserves temporal structure via timeline view
    - Extracts key decision points and task state changes
    - Segments old messages into time blocks with per-block summaries
    - Maintains continuity with recent conversation

    Algorithm:
    1. Segment old messages into time blocks (every ~10 messages)
    2. For each block, extract:
       - Time marker (message index range)
       - File references
       - Tool usage
       - User intents / task state
    3. Generate timeline summary preserving progression
    4. Return: system + timeline summary + recent messages

    Returns:
        History with collapsed view projected (temporal-aware)
    """
    if len(history) <= CONTEXT_COLLAPSE_THRESHOLD:
        return history  # Not enough messages to collapse

    # Separate system messages and conversation
    system_msgs = [msg for msg in history if msg.role == "system"]
    conversation_msgs = [msg for msg in history if msg.role != "system"]

    if len(conversation_msgs) <= CONTEXT_COLLAPSE_THRESHOLD:
        return history

    # Split into old and recent
    old_msgs = conversation_msgs[:-CONTEXT_COLLAPSE_THRESHOLD]
    recent_msgs = conversation_msgs[-CONTEXT_COLLAPSE_THRESHOLD:]

    # Generate temporal timeline summary
    timeline_parts = [f"[Context Collapse: {len(old_msgs)} turns archived as timeline]"]

    # Segment into time blocks (every ~10 messages)
    block_size = 10
    blocks = []
    for i in range(0, len(old_msgs), block_size):
        block = old_msgs[i:i + block_size]
        blocks.append((i, i + len(block), block))

    # Process each block
    for block_idx, (start, end, block) in enumerate(blocks):
        block_summary = _summarize_block(block, start, end)
        if block_summary:
            timeline_parts.append(block_summary)

    # Add global statistics
    global_stats = _extract_global_stats(old_msgs)
    if global_stats:
        timeline_parts.append(global_stats)

    timeline_parts.append(f"[Preserved: last {len(recent_msgs)} turns for continuity]")

    summary_text = "\n".join(timeline_parts)

    # Create summary message
    summary_msg = Message(
        role="system",
        content=summary_text,
        tool_calls=[],
        tool_call_id=None,
        _token_count=0,
        _model=history[0]._model if history else None,
        message_type="system",
        priority=100,
        compressed=False,  # Summary itself is not compressed
    )

    # Return: system messages + timeline summary + recent conversation
    result = system_msgs + [summary_msg] + recent_msgs

    logger.debug(
        "Context collapse (temporal): Archived %d turns in %d blocks, kept %d recent",
        len(old_msgs), len(blocks), len(recent_msgs)
    )

    return result


def _summarize_block(block: list[Message], start_idx: int, end_idx: int) -> str | None:
    """Summarize a block of messages with temporal markers.

    Extracts:
    - Message range (time marker)
    - File references
    - Tool usage
    - User intents / decisions

    Args:
        block: Messages in this block
        start_idx: Start index in original conversation
        end_idx: End index in original conversation

    Returns:
        Block summary string or None if empty
    """
    import re

    parts = [f"  [{start_idx}-{end_idx}]"]

    # Extract file references
    file_refs = set()
    for msg in block:
        # v1.17: Use _message_text for multimodal content support
        content_text = _message_text(msg.content)
        matches = re.finditer(
            r'[\w./-]+\.(?:py|js|ts|json|yaml|yml|md|txt|helen|rs|go|java|c|cpp|h|hpp)',
            content_text
        )
        for m in matches:
            file_refs.add(m.group())
    if file_refs:
        parts.append(f"Files: {', '.join(sorted(file_refs)[:3])}")

    # Extract tool usage
    tool_counts = {}
    for msg in block:
        if msg.role == "assistant" and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "unknown")
                tool_counts[name] = tool_counts.get(name, 0) + 1
    if tool_counts:
        top_tools = sorted(tool_counts.items(), key=lambda x: -x[1])[:3]
        tool_str = ", ".join(f"{name}({count})" for name, count in top_tools)
        parts.append(f"Tools: {tool_str}")

    # Extract user intents (first line of user messages)
    user_intents = []
    for msg in block:
        if msg.role == "user" and msg.content:
            # v1.17: Use _message_text for multimodal content support
            content_text = _message_text(msg.content)
            first_line = content_text.split('\n')[0][:60].strip()
            if first_line and first_line not in user_intents:
                user_intents.append(first_line)
    if user_intents:
        parts.append(f"Tasks: {'; '.join(user_intents[:2])}")

    # Only return if we have meaningful content
    if len(parts) > 1:
        return " | ".join(parts)
    return None


def _extract_global_stats(old_msgs: list[Message]) -> str | None:
    """Extract global statistics across all old messages.

    Args:
        old_msgs: All archived messages

    Returns:
        Global stats string or None if empty
    """
    stats_parts = ["[Global]"]

    # Total turns
    user_turns = sum(1 for m in old_msgs if m.role == "user")
    assistant_turns = sum(1 for m in old_msgs if m.role == "assistant")
    stats_parts.append(f"Turns: {user_turns}u/{assistant_turns}a")

    # Total tool calls
    total_tools = sum(
        len(m.tool_calls) for m in old_msgs
        if m.role == "assistant" and m.tool_calls
    )
    if total_tools > 0:
        stats_parts.append(f"Tool calls: {total_tools}")

    # Error count
    # v1.17: Use _message_text for multimodal content support
    errors = sum(
        1 for m in old_msgs
        if m.role == "tool" and "error" in _message_text(m.content).lower()
    )
    if errors > 0:
        stats_parts.append(f"Errors: {errors}")

    return " ".join(stats_parts) if len(stats_parts) > 1 else None


# ---------------------------------------------------------------------------
# Phase 2: Layer 5 - Auto-Compact (LLM Semantic Summarization)
# ---------------------------------------------------------------------------

def _auto_compact(
    history: list[Message],
    keep_recent: int = 4,
    llm_client: Callable | None = None,
    target_tokens: int = 2000,
) -> list[Message]:
    """Layer 5: LLM semantic summarization (or structural fallback).

    When llm_client is provided, uses LLMSummarizer for high-quality semantic
    compression that preserves task objectives, key decisions, and context.

    When llm_client is None, falls back to zero-cost structural summarization:
    - Archives more messages (all but keep_recent)
    - Generates rich structural summary with file refs, tool usage, etc.
    - Preserves recent conversation for continuity

    Args:
        history: Conversation history to compress
        keep_recent: Number of recent messages to preserve (default: 4)
        llm_client: Optional LLM client for semantic summarization.
                    Expected signature: llm_client(messages) -> str
        target_tokens: Target token count for the summary (default: 2000)

    Returns:
        History with summarization applied
    """
    if len(history) <= keep_recent + 2:
        return history  # Not enough to compact

    # Separate system messages and conversation
    system_msgs = [msg for msg in history if msg.role == "system"]
    conversation_msgs = [msg for msg in history if msg.role != "system"]

    if len(conversation_msgs) <= keep_recent:
        return history

    # Split into old and recent
    old_msgs = conversation_msgs[:-keep_recent]
    recent_msgs = conversation_msgs[-keep_recent:]

    # Use LLM summarization if client is available
    if llm_client is not None:
        try:
            from helen.runtime.llm_summarizer import LLMSummarizer
            summarizer = LLMSummarizer(llm_client)
            summary_text = summarizer.summarize(old_msgs, target_tokens=target_tokens)

            summary_msg = Message(
                role="system",
                content=f"[Previous conversation summary - LLM generated]\n\n{summary_text}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=0,
                _model=history[0]._model if history else None,
                message_type="system",
                priority=100,
                compressed=False,
            )

            result = system_msgs + [summary_msg] + recent_msgs
            logger.debug(
                "Auto-Compact (LLM): Archived %d turns into semantic summary, kept %d recent",
                len(old_msgs), len(recent_msgs)
            )
            return result

        except Exception as e:
            logger.warning(f"LLM summarization failed, falling back to structural: {e}")
            # Fall through to structural summarization

    # Fallback: Zero-cost structural summarization
    return _structural_auto_compact(system_msgs, old_msgs, recent_msgs, history)


def _structural_auto_compact(
    system_msgs: list[Message],
    old_msgs: list[Message],
    recent_msgs: list[Message],
    original_history: list[Message],
) -> list[Message]:
    """Zero-cost structural summarization (fallback for Layer 5).

    Extracts structural information without calling LLM:
    - File references
    - Tool usage statistics
    - User intents
    - Error history

    Args:
        system_msgs: System messages to preserve
        old_msgs: Old messages to summarize
        recent_msgs: Recent messages to preserve
        original_history: Original history for metadata

    Returns:
        History with structural summary applied
    """
    # Build rich structural summary
    summary_parts = [f"[Auto-Compact: {len(old_msgs)} turns archived]"]

    # Extract file references
    file_refs = set()
    import re
    for msg in old_msgs:
        # Find file paths in content (v1.17: use _message_text for multimodal)
        content_text = _message_text(msg.content)
        matches = re.finditer(
            r'[\w./-]+\.(?:py|js|ts|json|yaml|yml|md|txt|helen|rs|go|java|c|cpp|h|hpp)',
            content_text
        )
        for m in matches:
            file_refs.add(m.group())

    if file_refs:
        summary_parts.append(f"Files: {', '.join(sorted(file_refs)[:8])}")

    # Extract tool usage
    tool_counts = {}
    for msg in old_msgs:
        if msg.role == "assistant" and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "unknown")
                tool_counts[name] = tool_counts.get(name, 0) + 1

    if tool_counts:
        top_tools = sorted(tool_counts.items(), key=lambda x: -x[1])[:5]
        tool_str = ", ".join(f"{name}({count})" for name, count in top_tools)
        summary_parts.append(f"Tools: {tool_str}")

    # Extract user intents (first line of user messages)
    user_intents = []
    for msg in old_msgs:
        if msg.role == "user" and msg.content:
            # v1.17: Use _message_text for multimodal content support
            content_text = _message_text(msg.content)
            first_line = content_text.split('\n')[0][:100].strip()
            if first_line and first_line not in user_intents:
                user_intents.append(first_line)
    if user_intents:
        summary_parts.append(f"Tasks: {'; '.join(user_intents[:3])}")

    # Extract errors
    errors = []
    for msg in old_msgs:
        # v1.17: Use _message_text for multimodal content support
        content_text = _message_text(msg.content)
        if msg.role == "tool" and "error" in content_text.lower():
            preview = content_text[:80].strip()
            if preview:
                errors.append(preview)
    if errors:
        summary_parts.append(f"Errors encountered: {len(errors)}")

    summary_text = "\n".join(summary_parts)
    summary_text += f"\n[Preserved: last {len(recent_msgs)} turns]"

    # Create summary message
    summary_msg = Message(
        role="system",
        content=summary_text,
        tool_calls=[],
        tool_call_id=None,
        _token_count=0,
        _model=original_history[0]._model if original_history else None,
        message_type="system",
        priority=100,
        compressed=False,
    )

    result = system_msgs + [summary_msg] + recent_msgs

    logger.debug(
        "Auto-Compact (structural): Archived %d turns into summary, kept %d recent",
        len(old_msgs), len(recent_msgs)
    )

    return result


# ---------------------------------------------------------------------------
# Phase 2: Helper functions
# ---------------------------------------------------------------------------

def _calculate_usage_ratio(history: list[Message], max_tokens: int) -> float:
    """Calculate current usage ratio.

    Args:
        history: Conversation history
        max_tokens: Maximum context window tokens

    Returns:
        Usage ratio (0.0 - 1.0)
    """
    if not history or max_tokens == 0:
        return 0.0

    total_tokens = sum(msg.token_count for msg in history)
    return total_tokens / max_tokens
