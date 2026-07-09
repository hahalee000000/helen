"""Context overflow recovery cascade for Helen.

Phase 8: Multi-step recovery when LLM API returns prompt-too-long errors.

Recovery cascade (3 steps):
  Step 1: Context Collapse overflow recovery (zero-cost)
    - Archive old messages as timeline summary
    - Preserves file refs, tool usage, user intents
  Step 2: Reactive Compaction (structural then semantic)
    - Structural: zero-cost compression of older blocks
    - Semantic: LLM-based summary (if llm_client available)
  Step 3: Raise PromptTooLongError
    - All recovery attempts exhausted

Integration: http_llm.py _chat_with_messages_retry() and act_stream()
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Recovery result
# ---------------------------------------------------------------------------

@dataclass
class RecoveryResult:
    """Result of a recovery attempt.

    Attributes:
        messages: Recovered messages list (may be shorter than input)
        strategy: Name of the recovery strategy that succeeded
        success: Whether recovery succeeded
        tokens_reduced: Estimated number of tokens reduced
    """

    messages: list[dict[str, Any]] = field(default_factory=list)
    strategy: str = "none"
    success: bool = False
    tokens_reduced: int = 0


# ---------------------------------------------------------------------------
# Recovery cascade
# ---------------------------------------------------------------------------

class PromptTooLongRecovery:
    """Multi-step recovery cascade for context overflow.

    Usage:
        recovery = PromptTooLongRecovery()  # Uses DEFAULT_CONTEXT_WINDOW
        result = recovery.recover(messages)

        if result.success:
            # Use result.messages for retry
            messages = result.messages
        else:
            raise PromptTooLongError(...)
    """

    def __init__(
        self,
        max_tokens: int | None = None,
        llm_client: Any = None,
        max_recovery_attempts: int = 3,
    ):
        """Initialize recovery cascade.

        Args:
            max_tokens: Maximum context window tokens.
                       Defaults to DEFAULT_CONTEXT_WINDOW if None.
            llm_client: Optional LLM client for semantic recovery
            max_recovery_attempts: Maximum number of recovery steps to try
        """
        from helen.runtime.token_utils import DEFAULT_CONTEXT_WINDOW
        self.max_tokens = max_tokens if max_tokens is not None else DEFAULT_CONTEXT_WINDOW
        self.llm_client = llm_client
        self.max_recovery_attempts = max_recovery_attempts

    def recover(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
    ) -> RecoveryResult:
        """Execute recovery cascade.

        Steps:
        1. Context Collapse recovery (zero-cost)
        2. Reactive Compaction — structural (zero-cost)
        3. Reactive Compaction — semantic (if llm_client available)

        Args:
            messages: Current messages that caused context overflow
            max_tokens: Override max_tokens (uses instance default if None)

        Returns:
            RecoveryResult with success status and recovered messages
        """

        # Calculate initial token estimate
        initial_tokens = self._estimate_total_tokens(messages)

        # Step 1: Context Collapse recovery
        logger.info("Recovery step 1: context collapse overflow recovery")
        result = self._context_collapse_recovery(messages)
        if result.success and self._is_smaller(result.messages, messages):
            result.tokens_reduced = initial_tokens - self._estimate_total_tokens(result.messages)
            logger.info(
                "Recovery succeeded via context collapse: reduced ~%d tokens",
                result.tokens_reduced,
            )
            return result

        # Step 2: Reactive structural compaction
        logger.info("Recovery step 2: reactive structural compaction")
        result = self._reactive_structural_recovery(messages)
        if result.success and self._is_smaller(result.messages, messages):
            result.tokens_reduced = initial_tokens - self._estimate_total_tokens(result.messages)
            logger.info(
                "Recovery succeeded via reactive structural: reduced ~%d tokens",
                result.tokens_reduced,
            )
            return result

        # Step 3: Reactive semantic compaction (if LLM available)
        if self.llm_client is not None:
            logger.info("Recovery step 3: reactive semantic compaction (LLM)")
            result = self._reactive_semantic_recovery(messages)
            if result.success and self._is_smaller(result.messages, messages):
                result.tokens_reduced = initial_tokens - self._estimate_total_tokens(result.messages)
                logger.info(
                    "Recovery succeeded via reactive semantic: reduced ~%d tokens",
                    result.tokens_reduced,
                )
                return result

        # Step 4: Aggressive trim (last resort before giving up)
        logger.info("Recovery step 4: aggressive trim (last resort)")
        result = self._aggressive_trim(messages)
        if result.success and self._is_smaller(result.messages, messages):
            result.tokens_reduced = initial_tokens - self._estimate_total_tokens(result.messages)
            logger.info(
                "Recovery succeeded via aggressive trim: reduced ~%d tokens",
                result.tokens_reduced,
            )
            return result

        # All recovery attempts exhausted
        logger.error("All recovery attempts exhausted — cannot reduce context")
        return RecoveryResult(
            messages=messages,
            strategy="exhausted",
            success=False,
            tokens_reduced=0,
        )

    # -----------------------------------------------------------------------
    # Recovery strategies
    # -----------------------------------------------------------------------

    def _context_collapse_recovery(
        self,
        messages: list[dict[str, Any]],
    ) -> RecoveryResult:
        """Step 1: Context Collapse overflow recovery.

        Archive old messages as a timeline summary, preserving recent
        conversation for continuity.

        Strategy:
        - Keep system messages unchanged
        - Keep last N recent messages (default: 4)
        - Summarize everything in between as timeline
        """
        preserve_recent = 4

        system_msgs = [m for m in messages if m.get("role") == "system"]
        conv_msgs = [m for m in messages if m.get("role") != "system"]

        if len(conv_msgs) <= preserve_recent + 2:
            # Not enough messages to collapse further
            return RecoveryResult(messages=messages, strategy="context_collapse", success=False)

        old_msgs = conv_msgs[:-preserve_recent]
        recent_msgs = conv_msgs[-preserve_recent:]

        # Build timeline summary (same logic as graduated_compression._context_collapse)
        timeline_parts = [f"[Context Collapse Recovery: {len(old_msgs)} turns archived]"]

        block_size = 10
        for i in range(0, len(old_msgs), block_size):
            block = old_msgs[i:i + block_size]
            start_idx = i
            end_idx = i + len(block)

            block_parts = [f"  [{start_idx}-{end_idx}]"]

            # File references
            file_refs = set()
            for msg in block:
                content = msg.get("content", "")
                matches = re.finditer(
                    r'[\w./-]+\.(?:py|js|ts|json|yaml|yml|md|txt|helen|rs|go|java|c|cpp|h|hpp)',
                    content,
                )
                for m in matches:
                    file_refs.add(m.group())
            if file_refs:
                block_parts.append(f"Files: {', '.join(sorted(file_refs)[:3])}")

            # Tool usage
            tool_counts: dict[str, int] = {}
            for msg in block:
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        name = tc.get("function", {}).get("name", "unknown")
                        tool_counts[name] = tool_counts.get(name, 0) + 1
            if tool_counts:
                top_tools = sorted(tool_counts.items(), key=lambda x: -x[1])[:3]
                tool_str = ", ".join(f"{name}({count})" for name, count in top_tools)
                block_parts.append(f"Tools: {tool_str}")

            # User intents
            user_intents = []
            for msg in block:
                if msg.get("role") == "user" and msg.get("content"):
                    first_line = msg["content"].split('\n')[0][:60].strip()
                    if first_line and first_line not in user_intents:
                        user_intents.append(first_line)
            if user_intents:
                block_parts.append(f"Tasks: {'; '.join(user_intents[:2])}")

            if len(block_parts) > 1:
                timeline_parts.append(" | ".join(block_parts))

        timeline_parts.append(f"[Preserved: last {len(recent_msgs)} turns]")
        summary_text = "\n".join(timeline_parts)

        summary_msg = {"role": "system", "content": summary_text}
        result = system_msgs + [summary_msg] + recent_msgs

        return RecoveryResult(
            messages=result,
            strategy="context_collapse",
            success=True,
        )

    def _reactive_structural_recovery(
        self,
        messages: list[dict[str, Any]],
    ) -> RecoveryResult:
        """Step 2: Reactive structural compaction.

        Uses ReactiveCompactor's structural method (zero-cost).
        More aggressive than context collapse: drops more old messages.
        """
        from helen.runtime.reactive_compaction import ReactiveCompactor

        compactor = ReactiveCompactor(
            structural_threshold=0.0,  # Always trigger
            preserve_recent=2,          # Keep fewer messages
        )

        result_msgs, layer = compactor.check_and_compact(messages, self.max_tokens)

        if layer is not None:
            return RecoveryResult(
                messages=result_msgs,
                strategy="reactive_structural",
                success=True,
            )

        return RecoveryResult(messages=messages, strategy="reactive_structural", success=False)

    def _reactive_semantic_recovery(
        self,
        messages: list[dict[str, Any]],
    ) -> RecoveryResult:
        """Step 3: Reactive semantic compaction (LLM-based).

        Uses LLMSummarizer for high-quality summaries.
        """
        from helen.runtime.reactive_compaction import ReactiveCompactor

        compactor = ReactiveCompactor(
            semantic_threshold=0.0,     # Always trigger
            llm_client=self.llm_client,
            preserve_recent=2,
        )

        result_msgs, layer = compactor.check_and_compact(messages, self.max_tokens)

        if layer is not None:
            return RecoveryResult(
                messages=result_msgs,
                strategy="reactive_semantic",
                success=True,
            )

        return RecoveryResult(messages=messages, strategy="reactive_semantic", success=False)

    def _aggressive_trim(
        self,
        messages: list[dict[str, Any]],
    ) -> RecoveryResult:
        """Step 4: Aggressive trim — last resort.

        Keeps only system messages + last 2 conversation messages.
        Drops everything else.
        """
        system_msgs = [m for m in messages if m.get("role") == "system"]
        conv_msgs = [m for m in messages if m.get("role") != "system"]

        if len(conv_msgs) <= 2:
            return RecoveryResult(messages=messages, strategy="aggressive_trim", success=False)

        # Keep only the last 2 conversation messages
        recent = conv_msgs[-2:]
        result = system_msgs + recent

        return RecoveryResult(
            messages=result,
            strategy="aggressive_trim",
            success=True,
        )

    # -----------------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------------

    def _is_smaller(
        self,
        new_messages: list[dict[str, Any]],
        old_messages: list[dict[str, Any]],
    ) -> bool:
        """Check if new messages are smaller than old messages."""
        new_tokens = self._estimate_total_tokens(new_messages)
        old_tokens = self._estimate_total_tokens(old_messages)
        return new_tokens < old_tokens

    def _estimate_total_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate total tokens in messages list."""
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
