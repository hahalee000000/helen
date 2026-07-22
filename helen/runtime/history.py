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

# P3: Compression modes (can be set per-agent via history-compression setting)
COMPRESSION_MODE_SUMMARIZE = "summarize"  # Default: summarize old messages
COMPRESSION_MODE_TRUNCATE = "truncate"    # Drop old messages without summary
COMPRESSION_MODE_NONE = "none"            # No compression (may hit context limit)

# P3: Minimum recent messages to always keep (never compressed/dropped)
MIN_RECENT_MESSAGES = 5


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
    """Check if a character is CJK (Chinese/Japanese/Korean).

    Delegates to shared token_utils module for consistency.
    """
    from helen.runtime.token_utils import is_cjk
    return is_cjk(char)


def estimate_tokens(text: str, model: str | None = None) -> int:
    """Estimate token count for a text string.

    P3: Uses tiktoken when available for exact counting (model-aware).
    Falls back to character-type-aware heuristics (~15% accuracy) when
    tiktoken is not installed or for unknown models.

    Heuristic uses different chars-per-token ratios for CJK vs Latin characters.
    Much more accurate than naive len(text)//4 for multilingual content.

    Args:
        text: Input text.
        model: Optional model name for tiktoken encoding selection.

    Returns:
        Estimated or exact token count.
    """
    if not text:
        return 0

    # P3: Try tiktoken for exact counting when available
    tiktoken_count = _try_tiktoken_count(text, model)
    if tiktoken_count is not None:
        return tiktoken_count

    # Fallback: character-type-aware heuristic
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


# ---------------------------------------------------------------------------
# P3: tiktoken integration (optional, exact counting)
# ---------------------------------------------------------------------------

# Cache of tiktoken encoders by model/encoding name
_tiktoken_cache: dict[str, Any] = {}
_tiktoken_import_attempted = False
_tiktoken_available = False


def _try_tiktoken_init() -> bool:
    """Try to import tiktoken (once per process)."""
    global _tiktoken_import_attempted, _tiktoken_available
    if _tiktoken_import_attempted:
        return _tiktoken_available
    _tiktoken_import_attempted = True
    try:
        import tiktoken as _tt  # noqa: F401
        _tiktoken_available = True
    except ImportError:
        _tiktoken_available = False
    return _tiktoken_available


def _get_tiktoken_encoding(model: str | None) -> Any:
    """Get tiktoken encoding for a model (cached).

    Args:
        model: Model name (e.g., "gpt-4", "qwen3.7-plus").

    Returns:
        tiktoken.Encoding instance, or None if unavailable.
    """
    if not _try_tiktoken_init():
        return None

    import tiktoken

    cache_key = model or "__default__"
    if cache_key in _tiktoken_cache:
        return _tiktoken_cache[cache_key]

    enc = None
    try:
        # Try to get encoding for specific model
        if model:
            try:
                enc = tiktoken.encoding_for_model(model)
            except KeyError:
                pass

        # Fallback: try common encodings
        if enc is None:
            # Check if model is GPT-4/GPT-3.5 family
            if model and any(m in model.lower() for m in ("gpt-4", "gpt-3.5", "o1", "o3")):
                enc = tiktoken.get_encoding("cl100k_base")
            else:
                # Default to cl100k_base (works for most modern models)
                enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        enc = None

    _tiktoken_cache[cache_key] = enc
    return enc


def _try_tiktoken_count(text: str, model: str | None) -> int | None:
    """Try to count tokens using tiktoken. Returns None if unavailable.

    Args:
        text: Input text.
        model: Optional model name for encoding selection.

    Returns:
        Exact token count if tiktoken is available, None otherwise.
    """
    enc = _get_tiktoken_encoding(model)
    if enc is None:
        return None
    try:
        return len(enc.encode(text))
    except Exception:
        return None


@dataclass
class Message:
    """A single message in a conversation.

    P3: Supports model-aware token counting via optional model field.
    Phase 1: Supports message classification for selective compression.
    Phase 10: Optional UUID for mostly-append transcript storage.
    v1.17: content can be str (plain text) or list[dict] (multimodal content parts).
    """

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
    # Cached token count (lazily computed)
    _token_count: int = field(default=0, repr=False)
    # P3: Optional model name for accurate token counting
    _model: str | None = field(default=None, repr=False)

    # Phase 1: Message classification for selective compression
    message_type: str | None = field(default=None, repr=False)  # Auto-inferred type
    priority: int = field(default=50, repr=False)               # Priority (1-100, higher = more important)
    compressed: bool = field(default=False, repr=False)         # Whether message has been compressed
    pinned: bool = field(default=False, repr=False)             # Pinned messages are immune to compression

    # Phase 10: Mostly-append transcript storage
    # UUID is assigned on first append; preserved across compression.
    # Empty string means no UUID (backward compatible with existing messages).
    uuid: str = field(default="", repr=False)

    # v1.22: Invocation tree tracking
    # agent_name: Name of the agent that produced this message (None for top-level).
    # invocation_id: UUID of the agent main{} invocation that produced this message.
    # parent_invocation_id: UUID of the parent invocation (for nested agent calls).
    # Together these form the invocation tree — see reports/v1.22-invocation-tree-proposal.md.
    agent_name: str | None = field(default=None, repr=False)
    invocation_id: str = field(default="", repr=False)
    parent_invocation_id: str = field(default="", repr=False)

    # v1.24: Visibility tracking for cross-invocation context sharing
    # visible_to_invocation_ids: List of invocation IDs that can see this message
    # in addition to the original invocation_id. Used by resume_session() and
    # restore_context() to ensure restored messages are visible to the current
    # caller while preserving the original invocation_id for call tree integrity.
    visible_to_invocation_ids: list[str] = field(default_factory=list, repr=False)

    @property
    def token_count(self) -> int:
        """Lazily computed token count (model-aware when tiktoken available)."""
        if self._token_count == 0 and self.content:
            # For multimodal content (list), estimate tokens from text parts only
            if isinstance(self.content, list):
                text_parts = []
                for part in self.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                text = "\n".join(text_parts)
                # Add token estimate for non-text media parts (images ~85 tokens avg)
                media_parts = [p for p in self.content
                               if isinstance(p, dict) and p.get("type") != "text"]
                self._token_count = estimate_tokens(text, self._model) or 0
                self._token_count += len(media_parts) * 85
            else:
                self._token_count = estimate_tokens(self.content, self._model) or 0
            # Add overhead for message structure (role, tool_calls, etc.)
            # OpenAI counts ~4 tokens per message overhead
            self._token_count += 4
        return self._token_count

    def infer_message_type(self) -> str:
        """Infer the message type based on role and content.

        Returns one of:
        - "system": System prompt
        - "user": User message
        - "assistant": Assistant text response
        - "assistant_tool_call": Assistant tool call decision
        - "tool": Tool execution result

        Phase 1: Used for selective compression (preserve actions, clear data).
        """
        if self.role == "system":
            return "system"
        elif self.role == "user":
            return "user"
        elif self.role == "assistant":
            # Check if this is a tool call decision or text response
            if self.tool_calls and len(self.tool_calls) > 0:
                return "assistant_tool_call"
            else:
                return "assistant"
        elif self.role == "tool":
            return "tool"
        else:
            # Unknown role, treat as assistant
            return "assistant"

    def assign_priority(self) -> int:
        """Assign priority based on message type.

        Priority scale (1-100, higher = more important):
        - 100: System prompt, user requests (critical)
        - 80: Assistant text responses (high)
        - 70: Assistant tool call decisions (high - preserve actions)
        - 20: Tool results (low - can be cleared)

        Phase 1: Used for selective compression.
        """
        msg_type = self.message_type or self.infer_message_type()

        if msg_type == "system":
            return 100
        elif msg_type == "user":
            return 90
        elif msg_type == "assistant":
            return 80
        elif msg_type == "assistant_tool_call":
            return 70
        elif msg_type == "tool":
            return 20
        else:
            return 50


def _message_text(content: str | list[dict[str, Any]]) -> str:
    """Extract plain text from message content (handles multimodal lists).

    For multimodal content (list of content parts), concatenates all text parts.
    For plain text content, returns as-is.

    v1.17: Supports multimodal content for MediaPart handling.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        return "\n".join(text_parts)
    return str(content) if content else ""


class HistoryManager:
    """Manage conversation history with token budget enforcement (HLD 3.12).

    Features:
    - Model-aware context window sizing
    - Token budget calculation: reserve space for system prompt + instruction
    - History trimming: remove oldest messages first when over budget
    - Conversation summary: build 4096-token summary for LLM routing
    - P3: Configurable compression modes (summarize/truncate/none)
    - P3: Three-tier compression (recent → keep, middle → summarize, oldest → drop)
    """

    # Class-level defaults (overridden per-instance via model)
    MAX_TOKENS: int = DEFAULT_CONTEXT_WINDOW
    SUMMARY_MAX_TOKENS: int = 4096

    def __init__(
        self,
        model: str | None = None,
        context_window: int | None = None,
        compression_mode: str = COMPRESSION_MODE_SUMMARIZE,
    ):
        """Initialize history manager.

        Args:
            model: Model name for context window lookup.
            context_window: Explicit context window override (takes precedence over model).
            compression_mode: How to handle history overflow.
                - "summarize" (default): Summarize old messages into a compact summary
                - "truncate": Drop old messages without summary
                - "none": No compression (may hit context window limit)
        """
        if context_window is not None:
            self.MAX_TOKENS = context_window
        elif model is not None:
            self.MAX_TOKENS = get_model_context_window(model)
        self._model = model
        self.compression_mode = compression_mode

    def set_model(self, model: str | None) -> None:
        """Update the model and recalculate context window.

        P3: Invalidates cached token counts so they will be recomputed
        with the new model's encoding on next access.
        """
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
        """Enforce history size limit using the configured compression mode.

        P3: Three-tier compression strategy:
        1. Recent messages (newest MIN_RECENT_MESSAGES): always kept complete
        2. Middle messages: compressed per mode (summarize/truncate/none)
        3. Oldest messages beyond budget: dropped

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

        # P3: Apply compression based on mode
        if self.compression_mode == COMPRESSION_MODE_NONE:
            return history  # No compression requested (may hit API limit)

        if self.compression_mode == COMPRESSION_MODE_TRUNCATE:
            return self._truncate_compress(history, budget)

        # Default: summarize mode
        return self._summarize_compress(history, budget)

    def _truncate_compress(
        self,
        history: list[Message],
        budget: int,
    ) -> list[Message]:
        """P3: Truncate compression — drop oldest messages, keep recent ones.

        Always keeps at least MIN_RECENT_MESSAGES messages.
        Never drops system messages.
        """
        if len(history) <= MIN_RECENT_MESSAGES:
            return history  # Can't drop more

        # Calculate tokens for each message
        msg_tokens = [(msg, msg.token_count) for msg in history]

        # Identify system messages (must keep)
        system_indices = {i for i, (msg, _) in enumerate(msg_tokens) if msg.role == "system"}

        # Walk from newest, accumulating until we'd exceed budget
        recent: list[Message] = []
        recent_tokens = 0
        min_recent_start = max(0, len(history) - MIN_RECENT_MESSAGES)

        for i in range(len(history) - 1, -1, -1):
            if i in system_indices:
                continue
            msg, tokens = msg_tokens[i]
            # Must keep at least MIN_RECENT_MESSAGES non-system messages
            non_system_kept = len([m for m in recent if m.role != "system"])
            if recent_tokens + tokens > budget and i >= min_recent_start and non_system_kept >= MIN_RECENT_MESSAGES:
                break
            recent.insert(0, msg)
            recent_tokens += tokens

        # Prepend system messages at the start
        for i in sorted(system_indices):
            msg, _ = msg_tokens[i]
            if msg not in recent:
                recent.insert(0, msg)

        return recent

    def _summarize_compress(
        self,
        history: list[Message],
        budget: int,
    ) -> list[Message]:
        """P3: Three-tier summarize compression.

        Tier 1 (recent): Keep complete — newest MIN_RECENT_MESSAGES
        Tier 2 (middle): Summarize into [Previous conversation summary]
        Tier 3 (oldest): Drop if even summary would exceed budget
        """
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

        # Ensure at least MIN_RECENT_MESSAGES are kept
        if len(recent) < MIN_RECENT_MESSAGES and split_idx > 0:
            # Pull more messages from old to meet minimum
            needed = MIN_RECENT_MESSAGES - len(recent)
            for i in range(split_idx - 1, max(-1, split_idx - 1 - needed - 5), -1):
                if i < 0:
                    break
                msg = history[i]
                if msg.role != "system":  # Don't count system messages
                    recent.insert(0, msg)
                    split_idx = i
                    if len(recent) >= MIN_RECENT_MESSAGES:
                        break

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
            text = _message_text(msg.content)
            line = f"[{msg.role}] {text}"
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
                text = _message_text(newest.content)
                if len(text) > approx_chars:
                    return f"[{newest.role}] {text[:approx_chars]}... [truncated]"
                return f"[{newest.role}] {text}"
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
            text = _message_text(msg.content)
            line = f"[{msg.role}] {text}"
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

    # ------------------------------------------------------------------
    # P4: History Persistence (save/load to JSON)
    # ------------------------------------------------------------------

    def save_to_file(self, history: list[Message], filepath: str) -> None:
        """Save conversation history to a JSON file.

        P4: Enables cross-session history persistence. Saved format:
        {
            "version": 1,
            "model": "qwen3.7-plus",
            "saved_at": "2026-07-04T12:00:00Z",
            "messages": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }

        Args:
            history: List of messages to save.
            filepath: Path to the output JSON file.
        """
        import json
        from datetime import datetime

        data = {
            "version": 2,
            "model": self._model,
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls,
                    "tool_call_id": msg.tool_call_id,
                    "uuid": msg.uuid,
                }
                for msg in history
            ],
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("History saved to %s (%d messages)", filepath, len(history))
        except Exception as e:
            logger.warning("Failed to save history to %s: %s", filepath, e)

    def load_from_file(self, filepath: str) -> list[Message]:
        """Load conversation history from a JSON file.

        P4: Restores history from a previously saved file.

        Args:
            filepath: Path to the input JSON file.

        Returns:
            List of Message objects loaded from file.
        """
        import json

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            messages = []
            for msg_data in data.get("messages", []):
                msg = Message(
                    role=msg_data.get("role", "user"),
                    content=msg_data.get("content", ""),
                    tool_calls=msg_data.get("tool_calls", []),
                    tool_call_id=msg_data.get("tool_call_id"),
                    _model=self._model,
                    uuid=msg_data.get("uuid", ""),
                )
                messages.append(msg)

            logger.info("History loaded from %s (%d messages)", filepath, len(messages))
            return messages
        except FileNotFoundError:
            logger.info("History file not found: %s", filepath)
            return []
        except Exception as e:
            logger.warning("Failed to load history from %s: %s", filepath, e)
            return []

    # ------------------------------------------------------------------
    # P4: History Search / Retrieval
    # ------------------------------------------------------------------

    def search(
        self,
        history: list[Message],
        query: str | None = None,
        role: str | None = None,
        tool_name: str | None = None,
        limit: int = 20,
    ) -> list[Message]:
        """Search history for messages matching criteria.

        P4: Enables agents to query historical context for specific
        information, tool calls, or message types.

        Args:
            history: List of messages to search.
            query: Optional text to search for in message content (case-insensitive).
            role: Optional role filter ("user", "assistant", "system", "tool").
            tool_name: Optional tool name filter (searches in tool_calls).
            limit: Maximum number of results to return (default 20).

        Returns:
            List of matching messages (newest first, up to limit).
        """
        results: list[Message] = []

        for msg in reversed(history):  # Newest first
            if len(results) >= limit:
                break

            # Role filter
            if role and msg.role != role:
                continue

            # Text search (case-insensitive)
            if query and query.lower() not in _message_text(msg.content).lower():
                # Also check tool results
                if not any(query.lower() in tc.get("result", "").lower()
                          for tc in getattr(msg, 'tool_calls', [])):
                    continue

            # Tool name filter
            if tool_name:
                if not any(tool_name.lower() in tc.get("name", "").lower()
                          for tc in getattr(msg, 'tool_calls', [])):
                    # Also check content for tool summaries
                    if tool_name.lower() not in _message_text(msg.content).lower():
                        continue

            results.append(msg)

        return results

    # ------------------------------------------------------------------
    # P4: Context Usage Visualization
    # ------------------------------------------------------------------

    def get_usage_stats(
        self,
        history: list[Message],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Get context usage statistics for visualization.

        P4: Returns a dict with detailed context window usage information,
        suitable for display in REPL or debug output.

        Args:
            history: List of messages to analyze.
            system_prompt: Optional system prompt (for token counting).

        Returns:
            Dict with keys:
            - total_tokens: Total tokens used
            - context_window: Model's context window size
            - usage_percent: Percentage of context window used
            - message_count: Number of messages
            - by_role: Token count breakdown by role
            - compressed: Whether history has been compressed
            - summary_count: Number of summary messages
        """
        # Calculate tokens
        msg_tokens = sum(msg.token_count for msg in history)
        system_tokens = estimate_tokens(system_prompt, self._model) if system_prompt else 0
        total_tokens = msg_tokens + system_tokens

        # Breakdown by role
        by_role: dict[str, int] = {}
        for msg in history:
            by_role[msg.role] = by_role.get(msg.role, 0) + msg.token_count
        if system_tokens:
            by_role["system_prompt"] = system_tokens

        # Check for compression
        # v1.17: Use _message_text for multimodal content safety
        summary_count = sum(1 for msg in history
                          if msg.role == "system" and _message_text(msg.content).startswith("[Previous conversation summary]"))

        usage_percent = (total_tokens / self.MAX_TOKENS * 100) if self.MAX_TOKENS > 0 else 0

        return {
            "total_tokens": total_tokens,
            "context_window": self.MAX_TOKENS,
            "usage_percent": round(usage_percent, 1),
            "message_count": len(history),
            "by_role": by_role,
            "compressed": summary_count > 0,
            "summary_count": summary_count,
            "model": self._model,
            "compression_mode": self.compression_mode,
        }

    def format_usage_stats(self, stats: dict[str, Any]) -> str:
        """Format usage stats as human-readable string for REPL display.

        P4: Produces a concise, aligned text output.

        Args:
            stats: Dict from get_usage_stats().

        Returns:
            Multi-line string with formatted stats.
        """
        lines = [
            "╔══════════════════════════════════════╗",
            "║       Context Usage Statistics        ║",
            "╠══════════════════════════════════════╣",
        ]

        total = stats["total_tokens"]
        window = stats["context_window"]
        percent = stats["usage_percent"]
        model = stats.get("model", "unknown")

        # Progress bar (40 chars wide)
        bar_width = 40
        filled = int(bar_width * percent / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        status = "⚠️ " if percent > 80 else "✅ "

        lines.append(f"║ {status} {bar} {percent:5.1f}%            ║")
        lines.append(f"║ Tokens: {total:>8,} / {window:>8,}              ║")
        lines.append(f"║ Model:  {model:<30} ║")
        lines.append(f"║ Messages: {stats['message_count']:<27} ║")

        # By-role breakdown
        by_role = stats["by_role"]
        if by_role:
            lines.append("╠──────────────────────────────────────╣")
            for role, tokens in sorted(by_role.items()):
                role_label = role.capitalize()[:15]
                lines.append(f"║  {role_label:<16} {tokens:>8,} tokens        ║")

        # Compression info
        if stats["compressed"]:
            lines.append("╠──────────────────────────────────────╣")
            lines.append(f"║  📦 Compressed: {stats['summary_count']} summary message(s)   ║")
            lines.append(f"║  Mode: {stats['compression_mode']:<31} ║")

        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)
