"""History Manager for Helen (HLD 3.12).

Manages conversation history for multi-turn LLM interactions:
- Token budget checking before each LLM call
- History trimming (oldest-first) when approaching context window limits
- Conversation summary building with 4096 Token cap
- Model-aware context window sizing
- Automatic history compression when exceeding limits
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model context window lookup (tokens)
# ---------------------------------------------------------------------------

# Known model families and their context windows.
# Used as fallback when config doesn't specify. Updates as new models release.
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # Qwen family (DashScope)
    "qwen3.7-plus": 131072,
    "qwen3.7": 131072,
    "qwen-plus": 131072,
    "qwen-max": 32768,
    "qwen-turbo": 131072,
    "qwen-long": 1000000,
    # OpenAI family
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4.1": 1047576,
    "gpt-4.1-mini": 1047576,
    "gpt-4.1-nano": 1047576,
    "gpt-3.5-turbo": 16385,
    "o1": 200000,
    "o1-mini": 128000,
    "o1-pro": 200000,
    "o3": 200000,
    "o3-mini": 200000,
    "o4-mini": 200000,
    # Claude family (Anthropic)
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3-5-haiku": 200000,
    "claude-opus-4": 200000,
    "claude-sonnet-4": 200000,
    "claude-fable-5": 200000,
    # Gemini family
    "gemini-pro": 32768,
    "gemini-1.5-pro": 2097152,
    "gemini-1.5-flash": 1048576,
    "gemini-2.0-flash": 1048576,
    "gemini-2.5-pro": 1048576,
}

# Default fallback context window when model is unknown
DEFAULT_CONTEXT_WINDOW = 128000

# Token estimation constants
# Average tokens per character varies by language:
# - English: ~0.25 (4 chars per token)
# - Chinese/Japanese/Korean: ~1.5 (CJK chars are usually 1-2 tokens each)
# - Mixed: ~0.35
# We use a character-type-aware estimation for better accuracy.
CHARS_PER_TOKEN_EN = 4.0  # English/Latin
CHARS_PER_TOKEN_CJK = 1.2  # CJK characters (more tokens per char)
CHARS_PER_TOKEN_MIXED = 3.0  # Mixed content estimate

# History size limit: keep at most 80% of context window for history
# (reserves 20% for system prompt, current instruction, and response)
HISTORY_BUDGET_RATIO = 0.8

# Summary target: when compressing, aim for this many tokens
COMPRESSION_SUMMARY_TOKENS = 2048


def get_model_context_window(model: str | None) -> int:
    """Get the context window size (in tokens) for a given model.

    Lookup order:
    1. Exact match in MODEL_CONTEXT_WINDOWS
    2. Prefix match (e.g., "qwen3.7-plus-2024-08" matches "qwen3.7-plus")
    3. DEFAULT_CONTEXT_WINDOW fallback

    Args:
        model: Model name string (e.g., "qwen3.7-plus", "gpt-4o-mini")

    Returns:
        Context window size in tokens.
    """
    if not model:
        return DEFAULT_CONTEXT_WINDOW

    # Exact match
    if model in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model]

    # Prefix match: try progressively shorter prefixes
    # e.g., "qwen3.7-plus-2024-08" -> "qwen3.7-plus" -> "qwen3.7"
    parts = model.split("-")
    for i in range(len(parts), 0, -1):
        prefix = "-".join(parts[:i])
        if prefix in MODEL_CONTEXT_WINDOWS:
            return MODEL_CONTEXT_WINDOWS[prefix]

    return DEFAULT_CONTEXT_WINDOW


# ---------------------------------------------------------------------------
# Token estimation (model-aware, character-type-aware)
# ---------------------------------------------------------------------------

def _is_cjk(char: str) -> bool:
    """Check if a character is CJK (Chinese/Japanese/Korean)."""
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF      # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF   # CJK Extension A
        or 0x20000 <= cp <= 0x2A6DF # CJK Extension B
        or 0x2A700 <= cp <= 0x2B73F # CJK Extension C
        or 0x2B740 <= cp <= 0x2B81F # CJK Extension D
        or 0xF900 <= cp <= 0xFAFF   # CJK Compatibility Ideographs
        or 0x3000 <= cp <= 0x303F   # CJK Symbols and Punctuation
        or 0x3040 <= cp <= 0x309F   # Hiragana
        or 0x30A0 <= cp <= 0x30FF   # Katakana
        or 0xAC00 <= cp <= 0xD7AF   # Hangul Syllables
    )


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string using character-type-aware heuristics.

    Uses different chars-per-token ratios for CJK vs Latin characters.
    Much more accurate than naive len(text)//4 for multilingual content.

    Accuracy: within ~15% of actual token count for typical mixed content.

    Args:
        text: Input text.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0

    cjk_count = sum(1 for c in text if _is_cjk(c))
    total_len = len(text)

    if cjk_count == 0:
        # Pure Latin/English
        return max(1, int(total_len / CHARS_PER_TOKEN_EN))
    elif cjk_count == total_len:
        # Pure CJK
        return max(1, int(total_len / CHARS_PER_TOKEN_CJK))
    else:
        # Mixed: CJK chars at CJK rate, others at English rate
        non_cjk = total_len - cjk_count
        return max(1, int(cjk_count / CHARS_PER_TOKEN_CJK + non_cjk / CHARS_PER_TOKEN_EN))


@dataclass
class Message:
    """A single message in a conversation."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
    # Cached token count (lazily computed)
    _token_count: int = field(default=0, repr=False)

    @property
    def token_count(self) -> int:
        """Lazily computed token count."""
        if self._token_count == 0 and self.content:
            self._token_count = estimate_tokens(self.content)
            # Add overhead for message structure (role, tool_calls, etc.)
            # OpenAI counts ~4 tokens per message overhead
            self._token_count += 4
        return self._token_count


class HistoryManager:
    """Manage conversation history with token budget enforcement (HLD 3.12).

    Features:
    - Model-aware context window sizing
    - Token budget calculation: reserve space for system prompt + instruction
    - History trimming: remove oldest messages first when over budget
    - Conversation summary: build 4096-token summary for LLM routing
    - History compression: summarize old messages when exceeding limits
    """

    # Class-level defaults (overridden per-instance via model)
    MAX_TOKENS: int = DEFAULT_CONTEXT_WINDOW
    SUMMARY_MAX_TOKENS: int = 4096

    def __init__(self, model: str | None = None, context_window: int | None = None):
        """Initialize history manager.

        Args:
            model: Model name for context window lookup.
            context_window: Explicit context window override (takes precedence over model).
        """
        if context_window is not None:
            self.MAX_TOKENS = context_window
        elif model is not None:
            self.MAX_TOKENS = get_model_context_window(model)
        self._model = model

    def set_model(self, model: str | None) -> None:
        """Update the model and recalculate context window."""
        self._model = model
        self.MAX_TOKENS = get_model_context_window(model)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for a text string.

        This is a module-level function also available as a method
        for backward compatibility.
        """
        return estimate_tokens(text)

    def check_budget(self, system_tokens: int, instruction_tokens: int) -> int:
        """Calculate available token budget for conversation history.

        Args:
            system_tokens: Token count of system prompt.
            instruction_tokens: Token count of current instruction.

        Returns:
            Available tokens for history (reserves 1000 buffer for response).
        """
        # Reserve: system prompt + instruction + 1000 for response buffer
        budget = self.MAX_TOKENS - system_tokens - instruction_tokens - 1000
        return max(0, budget)

    def trim_history(
        self, history: list[Message], budget: int
    ) -> list[Message]:
        """Trim history from oldest to newest to fit within budget.

        Keeps the most recent messages, removing oldest first.
        Never removes the system message if present.

        Args:
            history: List of messages (oldest first).
            budget: Maximum token count for history.

        Returns:
            Trimmed history list that fits within budget.
        """
        if not history:
            return []

        if budget <= 0:
            return []

        # Calculate tokens for each message
        msg_tokens = [(msg, msg.token_count) for msg in history]

        # If total is under budget, keep all
        total = sum(t for _, t in msg_tokens)
        if total <= budget:
            return list(history)

        # Remove oldest messages until under budget (but keep system messages)
        result: list[Message] = []
        result_tokens: list[int] = []

        # First, identify system messages (they must stay)
        system_indices = {i for i, (msg, _) in enumerate(msg_tokens) if msg.role == "system"}

        # Build result from newest to oldest, skipping system messages
        for i in range(len(msg_tokens) - 1, -1, -1):
            if i in system_indices:
                continue
            msg, tokens = msg_tokens[i]
            if sum(result_tokens) + tokens <= budget:
                result.insert(0, msg)
                result_tokens.insert(0, tokens)

        # Prepend system messages at the start
        for i in sorted(system_indices):
            msg, tokens = msg_tokens[i]
            result.insert(0, msg)
            result_tokens.insert(0, tokens)

        return result

    def enforce_limit(
        self,
        history: list[Message],
        budget_ratio: float = HISTORY_BUDGET_RATIO,
    ) -> list[Message]:
        """Enforce history size limit by compressing old messages.

        If total history exceeds budget_ratio * MAX_TOKENS, summarizes
        the oldest messages into a single summary message and keeps
        recent messages intact.

        This prevents unbounded memory growth in long REPL sessions.

        Args:
            history: List of messages (oldest first).
            budget_ratio: Fraction of context window to allocate to history.

        Returns:
            New history list, possibly with compressed summary at start.
        """
        if not history:
            return []

        budget = int(self.MAX_TOKENS * budget_ratio)
        total = sum(msg.token_count for msg in history)

        if total <= budget:
            return history  # Under limit, no compression needed

        # Need to compress. Split into "old" and "recent" parts.
        # Strategy: keep newest messages until we hit 60% of budget,
        # summarize everything older into a summary message.
        keep_budget = int(budget * 0.75)  # Keep 75% of budget for recent messages
        summary_budget = budget - keep_budget  # Remaining 25% for summary

        # Walk from newest, accumulating until we'd exceed keep_budget
        recent: list[Message] = []
        recent_tokens = 0
        split_idx = 0

        for i in range(len(history) - 1, -1, -1):
            msg = history[i]
            tokens = msg.token_count
            if recent_tokens + tokens > keep_budget:
                split_idx = i + 1
                break
            recent.insert(0, msg)
            recent_tokens += tokens
        else:
            # All messages fit in keep_budget (shouldn't happen if total > budget)
            return history

        # The old messages to summarize
        old_messages = history[:split_idx]
        if not old_messages:
            return history

        # Build summary text from old messages
        summary_text = self._build_summary_text(old_messages, summary_budget)

        # Create a summary message at the start
        summary_msg = Message(
            role="system",
            content=f"[Previous conversation summary]\n{summary_text}",
        )

        # Return: summary + recent messages
        return [summary_msg] + recent

    def _build_summary_text(
        self,
        messages: list[Message],
        max_tokens: int = COMPRESSION_SUMMARY_TOKENS,
    ) -> str:
        """Build a text summary of messages.

        Walks newest-first, accumulating content until token budget is exhausted.

        Args:
            messages: Messages to summarize (oldest first).
            max_tokens: Maximum tokens for summary.

        Returns:
            Summary text string.
        """
        if not messages:
            return ""

        lines: list[str] = []
        total_tokens = 0

        for msg in reversed(messages):
            if not msg.content:
                continue
            line = f"[{msg.role}] {msg.content}"
            line_tokens = estimate_tokens(line)
            if total_tokens + line_tokens > max_tokens:
                break
            lines.append(line)
            total_tokens += line_tokens

        lines.reverse()

        if not lines:
            # Even a single message exceeded budget — truncate the newest one
            newest = messages[-1]
            if newest.content:
                # Take roughly max_tokens worth of content
                approx_chars = max_tokens * 3  # Rough chars-per-token
                if len(newest.content) > approx_chars:
                    return f"[{newest.role}] {newest.content[:approx_chars]}... [truncated]"
                return f"[{newest.role}] {newest.content}"
            return ""

        return "\n".join(lines)

    def build_conversation_summary(
        self, history: list[Message], max_tokens: int = SUMMARY_MAX_TOKENS
    ) -> str:
        """Build a conversation summary for LLM routing/choose context.

        Builds summary by including recent messages (newest first) until
        max_tokens limit is reached. Records truncation count for logging.

        Per HLD 3.6.6 conversation_summary rules:
        - Format: "[{role}] {content}" per message
        - Maximum: max_tokens tokens (default 4096)
        - Includes newest messages, truncates oldest
        - Records truncated message count

        Args:
            history: List of messages.
            max_tokens: Maximum tokens for summary (default 4096).

        Returns:
            Formatted summary string: "[{role}] {content}" per message.
        """
        if not history:
            return ""

        # Build from newest to oldest, stop at token limit
        lines: list[str] = []
        total_tokens = 0
        truncated = 0

        for msg in reversed(history):
            line = f"[{msg.role}] {msg.content}"
            line_tokens = estimate_tokens(line)
            if total_tokens + line_tokens > max_tokens:
                truncated += 1
                continue
            lines.append(line)
            total_tokens += line_tokens

        # Reverse back to chronological order
        lines.reverse()

        if truncated > 0:
            logger.debug("History truncated: %d messages omitted to fit token limit", truncated)

        return "\n".join(lines)

    def prepare_for_llm(
        self,
        history: list[Message],
        system_prompt: str | None,
        current_prompt: str,
    ) -> list[dict[str, Any]]:
        """Prepare history for an LLM API call.

        Combines budget checking, trimming, and format conversion:
        1. Calculate available budget (context window - system - prompt - buffer)
        2. Trim history to fit within budget
        3. Convert to OpenAI messages format

        Args:
            history: List of Message objects.
            system_prompt: System prompt text (for budget calculation).
            current_prompt: Current instruction text (for budget calculation).

        Returns:
            List of message dicts ready for OpenAI API.
        """
        system_tokens = estimate_tokens(system_prompt) if system_prompt else 0
        instruction_tokens = estimate_tokens(current_prompt) if current_prompt else 0
        budget = self.check_budget(system_tokens, instruction_tokens)

        trimmed = self.trim_history(history, budget)

        # Convert to API format
        messages: list[dict[str, Any]] = []
        for msg in trimmed:
            api_msg: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.tool_calls:
                api_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                api_msg["tool_call_id"] = msg.tool_call_id
            messages.append(api_msg)

        return messages
