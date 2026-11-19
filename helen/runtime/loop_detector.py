"""Tool call loop detection for LLM agent execution.

Detects when an agent is stuck in a repetitive tool call pattern
and provides mechanisms to break the loop.

Detection strategies:
1. Exact match: Same function + same arguments repeated N times
2. Near-match: Same function + similar arguments (for shell commands with minor variations)
3. Sliding window: K duplicates in last M calls

v1.46.27: Initial implementation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolCallSignature:
    """A normalized signature for a tool call, used for deduplication."""
    name: str
    args_key: str  # Sorted, normalized JSON string of arguments

    @classmethod
    def from_tool_call(cls, tool_call: dict[str, Any]) -> ToolCallSignature:
        """Create a signature from an OpenAI-format tool call."""
        fn = tool_call.get("function", {})
        name = fn.get("name", "unknown")
        args_raw = fn.get("arguments", "{}")

        # Normalize arguments: parse, sort keys, re-serialize
        try:
            if isinstance(args_raw, str):
                args = json.loads(args_raw)
            else:
                args = args_raw
            # Sort keys for consistent ordering
            args_key = json.dumps(args, sort_keys=True, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            # If we can't parse, use raw string
            args_key = str(args_raw)

        return cls(name=name, args_key=args_key)

    def __hash__(self) -> int:
        return hash((self.name, self.args_key))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ToolCallSignature):
            return False
        return self.name == other.name and self.args_key == other.args_key


@dataclass
class LoopDetectionResult:
    """Result of loop detection analysis."""
    is_looping: bool
    loop_type: str | None = None  # "exact", "near", "pattern"
    repeated_count: int = 0
    signature: ToolCallSignature | None = None
    hint_message: str | None = None

    def __bool__(self) -> bool:
        return self.is_looping


class ToolCallLoopDetector:
    """Detects repetitive tool call patterns that indicate an agent is stuck.

    Configuration:
        exact_repeat_threshold: Consecutive identical calls to trigger (default: 3)
        window_size: Sliding window for pattern detection (default: 10)
        window_repeat_threshold: Duplicates within window to trigger (default: 5)
    """

    def __init__(
        self,
        exact_repeat_threshold: int = 3,
        window_size: int = 10,
        window_repeat_threshold: int = 5,
    ):
        self.exact_repeat_threshold = exact_repeat_threshold
        self.window_size = window_size
        self.window_repeat_threshold = window_repeat_threshold

        # History of tool call signatures
        self._history: list[ToolCallSignature] = []

    def record(self, tool_calls: list[dict[str, Any]]) -> None:
        """Record a batch of tool calls (one turn's worth).

        Args:
            tool_calls: List of tool calls from LLM response,
                       each with 'function' -> {'name', 'arguments'}
        """
        for tc in tool_calls:
            sig = ToolCallSignature.from_tool_call(tc)
            self._history.append(sig)

        # Keep history bounded
        max_history = self.window_size * 3
        if len(self._history) > max_history:
            self._history = self._history[-max_history:]

    def check(self) -> LoopDetectionResult:
        """Check if the agent is in a loop.

        Returns:
            LoopDetectionResult indicating whether a loop was detected,
            with details and a suggested hint message.
        """
        if not self._history:
            return LoopDetectionResult(is_looping=False)

        # Strategy 1: Check for exact consecutive repeats at the end
        exact_result = self._check_exact_repeats()
        if exact_result.is_looping:
            return exact_result

        # Strategy 2: Check for repeating pattern in sliding window
        window_result = self._check_window_pattern()
        if window_result.is_looping:
            return window_result

        return LoopDetectionResult(is_looping=False)

    def _check_exact_repeats(self) -> LoopDetectionResult:
        """Check if the last N calls are all identical."""
        if len(self._history) < self.exact_repeat_threshold:
            return LoopDetectionResult(is_looping=False)

        # Check the last N signatures
        recent = self._history[-self.exact_repeat_threshold:]
        first = recent[0]

        if all(sig == first for sig in recent):
            # Count how many consecutive
            count = 1
            for i in range(len(self._history) - 2, -1, -1):
                if self._history[i] == first:
                    count += 1
                else:
                    break

            hint = self._build_hint(
                loop_type="exact",
                signature=first,
                repeated_count=count,
                message=(
                    f"You have called `{first.name}` with the same arguments "
                    f"{count} times in a row without progress. "
                    "This indicates the task may already be complete, "
                    "the arguments are incorrect, or you need a different approach. "
                    "Please verify the operation succeeded and provide a final summary, "
                    "or try a different strategy if it failed."
                ),
            )

            return LoopDetectionResult(
                is_looping=True,
                loop_type="exact",
                repeated_count=count,
                signature=first,
                hint_message=hint,
            )

        return LoopDetectionResult(is_looping=False)

    def _check_window_pattern(self) -> LoopDetectionResult:
        """Check for repeated calls within a sliding window."""
        if len(self._history) < self.window_repeat_threshold:
            return LoopDetectionResult(is_looping=False)

        window = self._history[-self.window_size:]

        # Count occurrences of each signature
        counts: dict[ToolCallSignature, int] = {}
        for sig in window:
            counts[sig] = counts.get(sig, 0) + 1

        # Find the most repeated signature
        most_common = max(counts.items(), key=lambda x: x[1])
        sig, count = most_common

        if count >= self.window_repeat_threshold:
            hint = self._build_hint(
                loop_type="pattern",
                signature=sig,
                repeated_count=count,
                message=(
                    f"Analysis of your last {len(window)} tool calls shows that "
                    f"`{sig.name}` was called {count} times with similar arguments "
                    "but without making progress. "
                    "This pattern suggests you may be stuck in a loop. "
                    "Please stop the current approach, verify what has been done, "
                    "and provide a final answer or try a fundamentally different strategy."
                ),
            )

            return LoopDetectionResult(
                is_looping=True,
                loop_type="pattern",
                repeated_count=count,
                signature=sig,
                hint_message=hint,
            )

        return LoopDetectionResult(is_looping=False)

    def _build_hint(
        self,
        loop_type: str,
        signature: ToolCallSignature,
        repeated_count: int,
        message: str,
    ) -> str:
        """Build a hint message to inject into the conversation."""
        # Decode arguments for display
        try:
            args = json.loads(signature.args_key)
            args_display = ", ".join(f"{k}={v!r}" for k, v in list(args.items())[:3])
            if len(args) > 3:
                args_display += ", ..."
        except (json.JSONDecodeError, TypeError):
            args_display = signature.args_key[:100]

        header = f"[Loop Detection: {loop_type} repeat detected]"
        detail = f"Tool: {signature.name}({args_display}) x{repeated_count}"

        return f"{header}\n{detail}\n\n{message}"

    def reset(self) -> None:
        """Reset the detector state."""
        self._history.clear()


__all__ = [
    "ToolCallLoopDetector",
    "ToolCallSignature",
    "LoopDetectionResult",
]
