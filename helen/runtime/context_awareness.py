"""Context Awareness for Helen LLM interactions.

Phase 9A: Inject token budget awareness into LLM context.

Two injection points:
1. System prompt: <budget:token_budget>N</budget:token_budget>
   - LLM knows its context window limit from the start
2. After tool calls: <system_warning>Token usage: X%; N remaining</system_warning>
   - Triggered at warning (50%), critical (75%), and emergency (90%) thresholds
   - Injected as a system message after the last tool result

This makes the LLM context-aware, enabling it to:
- Avoid generating overly long responses when context is tight
- Proactively summarize its own work when approaching limits
- Make smarter decisions about what to include/exclude
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Usage levels
# ---------------------------------------------------------------------------

USAGE_NORMAL = "normal"        # < 50%
USAGE_WARNING = "warning"      # 50-75%
USAGE_CRITICAL = "critical"    # 75-90%
USAGE_EMERGENCY = "emergency"  # > 90%

# Thresholds for usage warnings
WARNING_THRESHOLD = 0.50
CRITICAL_THRESHOLD = 0.75
EMERGENCY_THRESHOLD = 0.90


class ContextAwareness:
    """Inject token budget awareness into LLM context.

    Usage:
        awareness = ContextAwareness()  # Uses DEFAULT_CONTEXT_WINDOW

        # 1. Inject budget tag into system prompt
        system_prompt = awareness.inject_budget_tag(system_prompt)

        # 2. After tool results, build usage warning if needed
        warning = awareness.build_usage_warning(current_messages)
        if warning:
            messages.append({"role": "system", "content": warning})
    """

    def __init__(self, max_tokens: int | None = None):
        """Initialize context awareness.

        Args:
            max_tokens: Maximum context window tokens.
                       Defaults to DEFAULT_CONTEXT_WINDOW if None.
        """
        from helen.runtime.token_utils import DEFAULT_CONTEXT_WINDOW
        self.max_tokens = max_tokens if max_tokens is not None else DEFAULT_CONTEXT_WINDOW

    def build_usage_warning(
        self,
        messages: list[dict[str, Any]],
    ) -> str | None:
        """Build usage warning if context is getting tight.

        Only returns a warning if usage exceeds WARNING_THRESHOLD (50%).
        Returns None if usage is normal (no warning needed).

        Args:
            messages: Current messages list

        Returns:
            Warning message string, or None if usage is normal
        """
        current_tokens = self._calculate_tokens(messages)
        ratio = current_tokens / self.max_tokens if self.max_tokens > 0 else 0
        level = self.get_usage_level(ratio)

        if level == USAGE_NORMAL:
            return None

        remaining = self.max_tokens - current_tokens
        remaining = max(0, remaining)

        if level == USAGE_WARNING:
            return (
                f"<system_warning>Token usage: {current_tokens}/{self.max_tokens}; "
                f"{int(ratio * 100)}% used; {remaining} remaining</system_warning>"
            )
        elif level == USAGE_CRITICAL:
            return (
                f"<system_warning>Token usage: {current_tokens}/{self.max_tokens}; "
                f"{int(ratio * 100)}% used; {remaining} remaining. "
                f"Consider summarizing previous work before continuing.</system_warning>"
            )
        elif level == USAGE_EMERGENCY:
            return (
                f"<system_warning>CRITICAL: Token usage at {int(ratio * 100)}% "
                f"({current_tokens}/{self.max_tokens}); only {remaining} tokens remaining. "
                f"You MUST be concise. Avoid redundant explanations.</system_warning>"
            )

        return None

    def get_usage_level(self, ratio: float) -> str:
        """Classify usage ratio into a level.

        Args:
            ratio: Usage ratio (0.0 - 1.0+)

        Returns:
            Usage level: "normal", "warning", "critical", or "emergency"
        """
        if ratio >= EMERGENCY_THRESHOLD:
            return USAGE_EMERGENCY
        elif ratio >= CRITICAL_THRESHOLD:
            return USAGE_CRITICAL
        elif ratio >= WARNING_THRESHOLD:
            return USAGE_WARNING
        return USAGE_NORMAL

    def _calculate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Calculate total token count in messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if content:
                total += _estimate_tokens(content)
                total += 4  # per-message overhead
        return total


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Estimate token count from text (character-type-aware).

    Delegates to shared token_utils module.
    """
    from helen.runtime.token_utils import estimate_tokens_simple
    return estimate_tokens_simple(text)


def _is_cjk(char: str) -> bool:
    """Check if a character is CJK.

    Delegates to shared token_utils module.
    """
    from helen.runtime.token_utils import is_cjk
    return is_cjk(char)
