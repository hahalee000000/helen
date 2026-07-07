"""Reactive Compaction for Helen context management.

Phase 9B: Mid-turn reactive compression that triggers during tool execution
loops when context approaches capacity. Unlike the graduated compression
pipeline (which runs between turns), this module compresses within a turn
to prevent context overflow.

Design Philosophy: "Hybrid Stratified"
- 90% threshold: Structural compaction (zero-cost, zero-latency)
  Reuses _context_collapse logic: file refs, tool usage, user intents
- 95% threshold: LLM semantic compaction (higher quality, higher cost)
  Reuses LLMSummarizer for intelligent summaries
- Each turn: max 1 structural + 1 semantic trigger (avoid loops)

Integration point: http_llm.py tool execution loop
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Thresholds for reactive compaction
STRUCTURAL_THRESHOLD = 0.90   # 90%: trigger structural (zero-cost) compaction
SEMANTIC_THRESHOLD = 0.95     # 95%: trigger LLM semantic compaction

# Number of recent messages to always preserve
PRESERVE_RECENT = 4

# Block size for structural summarization (messages per block)
STRUCTURAL_BLOCK_SIZE = 10


class ReactiveCompactor:
    """Mid-turn reactive compression using hybrid stratified strategy.

    Usage:
        compactor = ReactiveCompactor()

        # In tool loop, after each tool result:
        messages, layer = compactor.check_and_compact(messages, max_tokens)
        if layer:
            logger.info(f"Reactive compaction triggered: {layer}")

        # At start of each new turn:
        compactor.reset_turn()
    """

    def __init__(
        self,
        structural_threshold: float = STRUCTURAL_THRESHOLD,
        semantic_threshold: float = SEMANTIC_THRESHOLD,
        llm_client: Callable | None = None,
        preserve_recent: int = PRESERVE_RECENT,
    ):
        """Initialize reactive compactor.

        Args:
            structural_threshold: Usage ratio to trigger structural compaction
            semantic_threshold: Usage ratio to trigger LLM semantic compaction
            llm_client: Optional LLM client for semantic compaction.
                        Signature: llm_client(messages) -> str
            preserve_recent: Number of recent messages to always preserve
        """
        self.structural_threshold = structural_threshold
        self.semantic_threshold = semantic_threshold
        self.llm_client = llm_client
        self.preserve_recent = preserve_recent

        # Per-turn state
        self._structural_triggered = False
        self._semantic_triggered = False

    def reset_turn(self) -> None:
        """Reset per-turn state at the start of a new turn."""
        self._structural_triggered = False
        self._semantic_triggered = False

    def check_and_compact(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Check usage and compact if threshold exceeded.

        Hybrid strategy:
        1. If usage > structural_threshold (90%): zero-cost structural compaction
        2. If usage > semantic_threshold (95%): LLM semantic compaction
        3. Each strategy triggers at most once per turn

        Args:
            messages: Current messages list (dict format for LLM API)
            max_tokens: Maximum context window tokens

        Returns:
            Tuple of (messages, layer_name).
            layer_name is None if no compaction was triggered.
        """
        if not messages or max_tokens <= 0:
            return messages, None

        # Calculate current usage
        usage_ratio = self._calculate_usage_ratio(messages, max_tokens)

        # Check semantic threshold first (higher priority)
        if (
            usage_ratio >= self.semantic_threshold
            and not self._semantic_triggered
            and self.llm_client is not None
            and len(messages) > self.preserve_recent + 2
        ):
            self._semantic_triggered = True
            logger.info(
                "Reactive compaction: semantic at %.1f%% usage (threshold: %.0f%%)",
                usage_ratio * 100, self.semantic_threshold * 100,
            )
            messages = self._semantic_compact(messages)
            return messages, "reactive_semantic"

        # Check structural threshold
        if (
            usage_ratio >= self.structural_threshold
            and not self._structural_triggered
            and len(messages) > self.preserve_recent + 2
        ):
            self._structural_triggered = True
            logger.info(
                "Reactive compaction: structural at %.1f%% usage (threshold: %.0f%%)",
                usage_ratio * 100, self.structural_threshold * 100,
            )
            messages = self._structural_compact(messages)
            return messages, "reactive_structural"

        return messages, None

    # -----------------------------------------------------------------------
    # Internal methods
    # -----------------------------------------------------------------------

    def _get_default_max_tokens(self) -> int:
        """Get the default max tokens from token_utils."""
        from helen.runtime.token_utils import DEFAULT_CONTEXT_WINDOW
        return DEFAULT_CONTEXT_WINDOW

    def _calculate_usage_ratio(self, messages: list[dict[str, Any]], max_tokens: int = 0) -> float:
        """Calculate current token usage ratio.

        Uses character-based estimation (same as history.estimate_tokens).
        """
        if not messages:
            return 0.0

        effective_max = max_tokens if max_tokens > 0 else self._get_default_max_tokens()

        total_tokens = 0
        for msg in messages:
            content = msg.get("content", "")
            if content:
                total_tokens += _estimate_tokens(content)
                total_tokens += 4  # per-message overhead

        return total_tokens / effective_max if effective_max > 0 else 0.0

    def _structural_compact(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Zero-cost structural compaction.

        Reuses _context_collapse logic:
        1. Separate system messages from conversation
        2. Split old messages into blocks
        3. Extract file refs, tool usage, user intents per block
        4. Replace old messages with timeline summary + keep recent

        Args:
            messages: Current messages list

        Returns:
            Compacted messages list
        """
        import re

        # Separate system and conversation messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        conv_msgs = [m for m in messages if m.get("role") != "system"]

        if len(conv_msgs) <= self.preserve_recent + 2:
            return messages  # Nothing to compact

        # Split into old and recent
        old_msgs = conv_msgs[:-self.preserve_recent]
        recent_msgs = conv_msgs[-self.preserve_recent:]

        # Build timeline summary
        timeline_parts = [f"[Reactive Compaction: {len(old_msgs)} turns archived as timeline]"]

        # Segment into blocks
        for i in range(0, len(old_msgs), STRUCTURAL_BLOCK_SIZE):
            block = old_msgs[i:i + STRUCTURAL_BLOCK_SIZE]
            start_idx = i
            end_idx = i + len(block)

            block_parts = [f"  [{start_idx}-{end_idx}]"]

            # Extract file references
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

            # Extract tool usage from tool_calls
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

            # Extract user intents
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

        # Global stats
        stats_parts = ["[Global]"]
        user_turns = sum(1 for m in old_msgs if m.get("role") == "user")
        assistant_turns = sum(1 for m in old_msgs if m.get("role") == "assistant")
        stats_parts.append(f"Turns: {user_turns}u/{assistant_turns}a")

        total_tool_calls = sum(
            len(m.get("tool_calls", []))
            for m in old_msgs
            if m.get("role") == "assistant"
        )
        if total_tool_calls > 0:
            stats_parts.append(f"Tool calls: {total_tool_calls}")

        errors = sum(
            1 for m in old_msgs
            if m.get("role") == "tool" and "error" in m.get("content", "").lower()
        )
        if errors > 0:
            stats_parts.append(f"Errors: {errors}")

        if len(stats_parts) > 1:
            timeline_parts.append(" ".join(stats_parts))

        timeline_parts.append(f"[Preserved: last {len(recent_msgs)} turns for continuity]")

        summary_text = "\n".join(timeline_parts)

        # Build result
        summary_msg = {"role": "system", "content": summary_text}
        result = system_msgs + [summary_msg] + recent_msgs

        logger.debug(
            "Reactive structural compaction: %d -> %d messages",
            len(messages), len(result),
        )
        return result

    def _semantic_compact(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """LLM-based semantic compaction.

        Uses LLMSummarizer to generate intelligent summary of old messages.
        Preserves task objectives, key decisions, and important context.

        Args:
            messages: Current messages list

        Returns:
            Compacted messages list
        """
        if self.llm_client is None:
            # Fall back to structural if no LLM client
            return self._structural_compact(messages)

        # Separate system and conversation messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        conv_msgs = [m for m in messages if m.get("role") != "system"]

        if len(conv_msgs) <= self.preserve_recent + 2:
            return messages

        # Split into old and recent
        old_msgs = conv_msgs[:-self.preserve_recent]
        recent_msgs = conv_msgs[-self.preserve_recent:]

        try:
            from helen.runtime.llm_summarizer import LLMSummarizer

            # Convert dict messages to a format LLMSummarizer can handle
            # LLMSummarizer expects objects with .role, .content, .tool_calls, etc.
            class _MsgAdapter:
                def __init__(self, d: dict):
                    self.role = d.get("role", "user")
                    self.content = d.get("content", "")
                    self.tool_calls = d.get("tool_calls", [])
                    self.tool_call_id = d.get("tool_call_id")
                    self.compressed = False

            adapted_old = [_MsgAdapter(m) for m in old_msgs]

            summarizer = LLMSummarizer(self.llm_client)
            summary_text = summarizer.summarize(adapted_old, target_tokens=2000)

            summary_msg = {
                "role": "system",
                "content": f"[Previous conversation summary - LLM generated]\n\n{summary_text}",
            }

            result = system_msgs + [summary_msg] + recent_msgs

            logger.debug(
                "Reactive semantic compaction: %d -> %d messages",
                len(messages), len(result),
            )
            return result

        except Exception as e:
            logger.warning("Reactive semantic compaction failed: %s — falling back to structural", e)
            return self._structural_compact(messages)


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
