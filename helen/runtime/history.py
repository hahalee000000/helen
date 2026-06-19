"""History Manager for Helen (HLD 3.12).

Manages conversation history for multi-turn LLM interactions:
- Token budget checking before each LLM call
- History trimming (oldest-first) when approaching context window limits
- Conversation summary building with 4096 Token cap
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """A single message in a conversation."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None


class HistoryManager:
    """Manage conversation history with token budget enforcement (HLD 3.12).

    Features:
    - MAX_TOKENS: 128000 (model context window)
    - Token budget calculation: reserve space for system prompt + instruction
    - History trimming: remove oldest messages first when over budget
    - Conversation summary: build 4096-token summary for LLM routing
    """

    MAX_TOKENS: int = 128000
    SUMMARY_MAX_TOKENS: int = 4096

    def check_budget(self, system_tokens: int, instruction_tokens: int) -> int:
        """Calculate available token budget for conversation history.

        Args:
            system_tokens: Token count of system prompt.
            instruction_tokens: Token count of current instruction.

        Returns:
            Available tokens for history (reserves 1000 buffer).
        """
        return self.MAX_TOKENS - system_tokens - instruction_tokens - 1000

    def trim_history(
        self, history: list[Message], budget: int
    ) -> list[Message]:
        """Trim history from oldest to newest to fit within budget.

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
        msg_tokens = []
        for msg in history:
            tokens = self.estimate_tokens(msg.content)
            msg_tokens.append(tokens)

        # If total is under budget, keep all
        total = sum(msg_tokens)
        if total <= budget:
            return list(history)

        # Remove oldest messages until under budget
        result = list(history)
        result_tokens = list(msg_tokens)
        while result and sum(result_tokens) > budget:
            result.pop(0)
            result_tokens.pop(0)

        return result

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
            line_tokens = self.estimate_tokens(line)
            if total_tokens + line_tokens > max_tokens:
                truncated += 1
                continue
            lines.append(line)
            total_tokens += line_tokens

        # Reverse back to chronological order
        lines.reverse()

        # Log truncation (in real impl, this would go to debug log)
        if truncated > 0:
            import logging
            logging.debug("History truncated: %d messages omitted to fit token limit", truncated)

        return "\n".join(lines)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for a text string.

        v1: Simple heuristic (chars / 4).
        Future: Use actual tokenizer from runtime.

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        return len(text) // 4
