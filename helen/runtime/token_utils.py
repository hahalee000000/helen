"""Shared token estimation utilities for Helen runtime.

Centralizes token estimation and CJK character detection to avoid
duplication across multiple modules (history, context_recovery,
reactive_compaction, context_awareness).

Design notes:
- Pure functions with no circular import risk
- Used by all modules that need token estimation
- Character-type-aware heuristic (~15% accuracy without tiktoken)
- Falls back gracefully when tiktoken is unavailable
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token estimation constants
# ---------------------------------------------------------------------------

CHARS_PER_TOKEN_EN = 4.0     # English/Latin
CHARS_PER_TOKEN_CJK = 1.2    # CJK characters
CHARS_PER_TOKEN_MIXED = 3.0  # Mixed content estimate
PER_MESSAGE_OVERHEAD = 4     # Per-message overhead (role, structure)

# Default context window for unknown models (tokens)
DEFAULT_CONTEXT_WINDOW = 131072


# ---------------------------------------------------------------------------
# CJK character detection
# ---------------------------------------------------------------------------

def is_cjk(char: str) -> bool:
    """Check if a character is CJK (Chinese/Japanese/Korean).

    Comprehensive Unicode range check covering:
    - CJK Unified Ideographs (0x4E00-0x9FFF)
    - CJK Extensions A-E
    - CJK Compatibility Ideographs
    - CJK Symbols and Punctuation
    - Hiragana, Katakana
    - Hangul Syllables

    Args:
        char: Single character to check

    Returns:
        True if character is CJK
    """
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF)       # CJK Unified Ideographs
        or (0x3400 <= cp <= 0x4DBF)    # CJK Extension A
        or (0x20000 <= cp <= 0x2A6DF)  # CJK Extension B
        or (0x2A700 <= cp <= 0x2B73F)  # CJK Extension C
        or (0x2B740 <= cp <= 0x2B81F)  # CJK Extension D
        or (0xF900 <= cp <= 0xFAFF)    # CJK Compatibility Ideographs
        or (0x3000 <= cp <= 0x303F)    # CJK Symbols and Punctuation
        or (0x3040 <= cp <= 0x309F)    # Hiragana
        or (0x30A0 <= cp <= 0x30FF)    # Katakana
        or (0xAC00 <= cp <= 0xD7AF)    # Hangul Syllables
    )


def is_cjk_codepoint(codepoint: int) -> bool:
    """Check if a Unicode codepoint is CJK.

    Integer version for use in lexers/parsers that work with codepoints.

    Args:
        codepoint: Unicode codepoint (integer)

    Returns:
        True if codepoint is CJK
    """
    return (
        (0x4E00 <= codepoint <= 0x9FFF)
        or (0x3400 <= codepoint <= 0x4DBF)
        or (0x20000 <= codepoint <= 0x2A6DF)
        or (0x2A700 <= codepoint <= 0x2B73F)
        or (0x2B740 <= codepoint <= 0x2B81F)
        or (0xF900 <= codepoint <= 0xFAFF)
        or (0x3000 <= codepoint <= 0x303F)
        or (0x3040 <= codepoint <= 0x309F)
        or (0x30A0 <= codepoint <= 0x30FF)
        or (0xAC00 <= codepoint <= 0xD7AF)
    )


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def estimate_tokens_simple(text: str) -> int:
    """Estimate token count using character-type-aware heuristic.

    No external dependencies (no tiktoken). ~15% accuracy.

    Different ratios for:
    - Pure Latin/English: ~4 chars per token
    - Pure CJK: ~1.2 chars per token
    - Mixed: weighted average

    Args:
        text: Input text to estimate

    Returns:
        Estimated token count (>= 1 for non-empty text)
    """
    if not text:
        return 0

    cjk_count = sum(1 for c in text if is_cjk(c))
    total_len = len(text)

    if cjk_count == 0:
        # Pure Latin/English
        return max(1, int(total_len / CHARS_PER_TOKEN_EN))
    elif cjk_count == total_len:
        # Pure CJK
        return max(1, int(total_len / CHARS_PER_TOKEN_CJK))
    else:
        # Mixed content
        non_cjk = total_len - cjk_count
        return max(1, int(cjk_count / CHARS_PER_TOKEN_CJK + non_cjk / CHARS_PER_TOKEN_EN))


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate total tokens in a list of message dicts.

    Includes per-message overhead (4 tokens per message).

    Args:
        messages: List of message dicts with 'content' key

    Returns:
        Estimated total token count
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if content:
            total += estimate_tokens_simple(content)
            total += PER_MESSAGE_OVERHEAD
    return total


def estimate_messages_tokens_from_message(messages: list[Any]) -> int:
    """Estimate total tokens in a list of Message objects.

    Uses Message.token_count property when available.

    Args:
        messages: List of Message objects with token_count property

    Returns:
        Estimated total token count
    """
    return sum(getattr(m, 'token_count', 0) for m in messages)


# ---------------------------------------------------------------------------
# Usage ratio calculation
# ---------------------------------------------------------------------------

def calculate_usage_ratio_from_dicts(
    messages: list[dict[str, Any]],
    max_tokens: int,
) -> float:
    """Calculate usage ratio from dict-format messages.

    Args:
        messages: List of message dicts
        max_tokens: Maximum context window tokens

    Returns:
        Usage ratio (0.0 - 1.0+)
    """
    if not messages or max_tokens <= 0:
        return 0.0
    return estimate_messages_tokens(messages) / max_tokens


def calculate_usage_ratio_from_messages(
    messages: list[Any],
    max_tokens: int,
) -> float:
    """Calculate usage ratio from Message objects.

    Args:
        messages: List of Message objects
        max_tokens: Maximum context window tokens

    Returns:
        Usage ratio (0.0 - 1.0+)
    """
    if not messages or max_tokens <= 0:
        return 0.0
    return estimate_messages_tokens_from_message(messages) / max_tokens


# ---------------------------------------------------------------------------
# File extension regex (shared)
# ---------------------------------------------------------------------------

# Common file extensions for extraction in timeline summaries
FILE_EXTENSION_PATTERN = (
    r'[\w./-]+\.(?:py|js|ts|json|yaml|yml|md|txt|helen|rs|go|java|c|cpp|h|hpp)'
)


# ---------------------------------------------------------------------------
# Timeline summary block extraction (shared)
# ---------------------------------------------------------------------------

def summarize_message_block(
    block: list,
    start_idx: int,
    end_idx: int,
    content_getter=None,
    role_getter=None,
    tool_calls_getter=None,
) -> str | None:
    """Summarize a block of messages with temporal markers.

    Extracts:
    - Message range (time marker)
    - File references (via regex)
    - Tool usage (name + count)
    - User intents (first line of user messages)

    Supports both Message objects and dict messages via getter functions.

    Args:
        block: Messages in this block
        start_idx: Start index in original conversation
        end_idx: End index in original conversation
        content_getter: Function to get content from a message.
                       Defaults to getattr(msg, 'content', '') or msg.get('content', '')
        role_getter: Function to get role from a message.
                    Defaults to getattr(msg, 'role', '') or msg.get('role', '')
        tool_calls_getter: Function to get tool_calls from a message.
                          Defaults to getattr(msg, 'tool_calls', []) or msg.get('tool_calls', [])

    Returns:
        Block summary string or None if empty
    """
    import re

    # Default getters support both Message objects and dicts
    if content_getter is None:
        def content_getter(msg):
            return getattr(msg, 'content', '') if hasattr(msg, 'content') else msg.get('content', '')
    if role_getter is None:
        def role_getter(msg):
            return getattr(msg, 'role', '') if hasattr(msg, 'role') else msg.get('role', '')
    if tool_calls_getter is None:
        def tool_calls_getter(msg):
            return getattr(msg, 'tool_calls', []) if hasattr(msg, 'tool_calls') else msg.get('tool_calls', [])

    parts = [f"  [{start_idx}-{end_idx}]"]

    # Extract file references
    file_refs = set()
    for msg in block:
        content = content_getter(msg)
        if content:
            matches = re.finditer(FILE_EXTENSION_PATTERN, content)
            for m in matches:
                file_refs.add(m.group())
    if file_refs:
        parts.append(f"Files: {', '.join(sorted(file_refs)[:3])}")

    # Extract tool usage
    tool_counts = {}
    for msg in block:
        if role_getter(msg) == "assistant":
            tool_calls = tool_calls_getter(msg)
            if tool_calls:
                for tc in tool_calls:
                    # Support both OpenAI format (nested) and flat format
                    if isinstance(tc, dict):
                        name = tc.get("function", {}).get("name") or tc.get("name", "unknown")
                    else:
                        name = getattr(tc, 'name', 'unknown')
                    tool_counts[name] = tool_counts.get(name, 0) + 1
    if tool_counts:
        top_tools = sorted(tool_counts.items(), key=lambda x: -x[1])[:3]
        tool_str = ", ".join(f"{name}({count})" for name, count in top_tools)
        parts.append(f"Tools: {tool_str}")

    # Extract user intents (first line of user messages)
    user_intents = []
    for msg in block:
        if role_getter(msg) == "user":
            content = content_getter(msg)
            if content:
                first_line = content.split('\n')[0][:60].strip()
                if first_line and first_line not in user_intents:
                    user_intents.append(first_line)
    if user_intents:
        parts.append(f"Tasks: {'; '.join(user_intents[:2])}")

    # Only return if we have meaningful content
    if len(parts) > 1:
        return " | ".join(parts)
    return None


def extract_global_stats(
    messages: list,
    role_getter=None,
    tool_calls_getter=None,
    content_getter=None,
) -> str | None:
    """Extract global statistics across messages.

    Extracts:
    - Total user/assistant turns
    - Total tool calls
    - Error count

    Args:
        messages: List of messages
        role_getter: Function to get role from a message
        tool_calls_getter: Function to get tool_calls from a message
        content_getter: Function to get content from a message

    Returns:
        Global stats string or None if empty
    """
    # Default getters
    if role_getter is None:
        def role_getter(msg):
            return getattr(msg, 'role', '') if hasattr(msg, 'role') else msg.get('role', '')
    if tool_calls_getter is None:
        def tool_calls_getter(msg):
            return getattr(msg, 'tool_calls', []) if hasattr(msg, 'tool_calls') else msg.get('tool_calls', [])
    if content_getter is None:
        def content_getter(msg):
            return getattr(msg, 'content', '') if hasattr(msg, 'content') else msg.get('content', '')

    stats_parts = ["[Global]"]

    # Total turns
    user_turns = sum(1 for m in messages if role_getter(m) == "user")
    assistant_turns = sum(1 for m in messages if role_getter(m) == "assistant")
    stats_parts.append(f"Turns: {user_turns}u/{assistant_turns}a")

    # Total tool calls
    total_tools = 0
    for m in messages:
        if role_getter(m) == "assistant":
            tcs = tool_calls_getter(m)
            if tcs:
                total_tools += len(tcs)
    if total_tools > 0:
        stats_parts.append(f"Tool calls: {total_tools}")

    # Error count
    errors = 0
    for m in messages:
        if role_getter(m) == "tool":
            content = content_getter(m)
            if content and "error" in content.lower():
                errors += 1
    if errors > 0:
        stats_parts.append(f"Errors: {errors}")

    return " ".join(stats_parts) if len(stats_parts) > 1 else None
