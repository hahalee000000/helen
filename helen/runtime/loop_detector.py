"""Tool call loop detection for LLM agent execution.

Detects when an agent is stuck in a repetitive tool call pattern
and provides mechanisms to break the loop.

Detection strategies:
1. Exact match: Same function + same arguments repeated N times
2. Near-match: Same function + similar arguments (for shell commands with minor variations)
3. Sliding window: K duplicates in last M calls

v1.46.27: Initial implementation.
v1.46.35: Mixed approach — per-tool thresholds + informative hints (not yes/no judgment).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# Per-tool thresholds: different tools have different repeat tolerance
# Read/execution tools are more tolerant, write/modification tools are stricter
DEFAULT_TOOL_THRESHOLDS: dict[str, int] = {
    # Read/execution tools — high tolerance (legitimate repeated use)
    "shell_exec": 25,      # Shell commands often need many iterations
    "read_file": 20,       # Reading large files in chunks
    "list_directory": 20,  # Browsing directory structure
    "search_files": 15,    # Search operations
    "find_files": 15,      # Find operations
    "web_search": 15,      # Web searches
    "web_fetch": 15,       # Web fetches

    # Write/modification tools — strict (repeated writes are suspicious)
    "write_file": 5,       # Writing same file repeatedly is usually a bug
    "edit_file": 5,        # Editing same file repeatedly
    "patch_file": 5,       # Patching same file repeatedly

    # Default for unknown tools
    "default": 10,
}


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
            # If we can't parse, fall back to raw string
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
    loop_type: str | None = None  # "exact", "near", "pattern", "tool-name-repeat"
    repeated_count: int = 0
    signature: ToolCallSignature | None = None
    hint_message: str | None = None
    threshold_used: int = 0  # The threshold that triggered this detection

    def __bool__(self) -> bool:
        return self.is_looping


class ToolCallLoopDetector:
    """Detects repetitive tool call patterns that indicate an agent is stuck.

    v1.46.35: Mixed approach — per-tool thresholds + informative hints.
    - Different tools have different repeat tolerance
    - Hints provide information and suggestions, not yes/no judgment
    - LLM can continue if making legitimate progress

    Configuration:
        exact_repeat_threshold: Base threshold for exact repeats (used if tool not in per-tool map)
        window_size: Sliding window for pattern detection (default: 10)
        window_repeat_threshold: Duplicates within window to trigger (default: 5)
        tool_only_repeat_threshold: Base threshold for tool-name repeat (multiplied by tool factor)
        tool_thresholds: Per-tool threshold overrides
    """

    def __init__(
        self,
        exact_repeat_threshold: int = 3,
        window_size: int = 10,
        window_repeat_threshold: int = 5,
        tool_only_repeat_threshold: int = 15,
        tool_thresholds: dict[str, int] | None = None,
    ):
        self.exact_repeat_threshold = exact_repeat_threshold
        self.window_size = window_size
        self.window_repeat_threshold = window_repeat_threshold
        self.tool_only_repeat_threshold = tool_only_repeat_threshold

        # Merge custom thresholds with defaults
        self.tool_thresholds = DEFAULT_TOOL_THRESHOLDS.copy()
        if tool_thresholds:
            self.tool_thresholds.update(tool_thresholds)

        # History of tool call signatures
        self._history: list[ToolCallSignature] = []

    def _get_tool_threshold(self, tool_name: str) -> int:
        """Get the repeat threshold for a specific tool."""
        return self.tool_thresholds.get(tool_name, self.tool_thresholds.get("default", 10))

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

        # Strategy 3 (v1.46.30): Check for consecutive calls to same tool (any args)
        # This catches cases like agent repeatedly calling shell_exec with different
        # sed commands to read different parts of a file without making progress
        tool_only_result = self._check_tool_name_repeat()
        if tool_only_result.is_looping:
            return tool_only_result

        return LoopDetectionResult(is_looping=False)

    def _check_exact_repeats(self) -> LoopDetectionResult:
        """Check if the last N calls are all identical.

        Uses per-tool threshold: tools like shell_exec have higher tolerance.
        """
        if not self._history:
            return LoopDetectionResult(is_looping=False)

        # Get the most recent tool name to determine threshold
        last_tool_name = self._history[-1].name
        threshold = self._get_tool_threshold(last_tool_name)

        if len(self._history) < threshold:
            return LoopDetectionResult(is_looping=False)

        # Check the last N signatures
        recent = self._history[-threshold:]
        first = recent[0]

        if all(sig == first for sig in recent):
            # Count how many consecutive
            count = 1
            for i in range(len(self._history) - 2, -1, -1):
                if self._history[i] == first:
                    count += 1
                else:
                    break

            hint = self._build_informative_hint(
                loop_type="exact",
                signature=first,
                repeated_count=count,
                threshold=threshold,
            )

            return LoopDetectionResult(
                is_looping=True,
                loop_type="exact",
                repeated_count=count,
                signature=first,
                hint_message=hint,
                threshold_used=threshold,
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

        # Use the configured window_repeat_threshold directly
        # (not derived from per-tool threshold)
        if count >= self.window_repeat_threshold:
            hint = self._build_informative_hint(
                loop_type="pattern",
                signature=sig,
                repeated_count=count,
                threshold=self.window_repeat_threshold,
            )

            return LoopDetectionResult(
                is_looping=True,
                loop_type="pattern",
                repeated_count=count,
                signature=sig,
                hint_message=hint,
                threshold_used=self.window_repeat_threshold,
            )

        return LoopDetectionResult(is_looping=False)

    def _check_tool_name_repeat(self) -> LoopDetectionResult:
        """Check if the last N calls all use the same tool (any arguments).

        This catches patterns like agent repeatedly calling shell_exec with
        different sed/grep/cat commands but not making progress.

        Uses per-tool threshold for more accurate detection.
        """
        if not self._history:
            return LoopDetectionResult(is_looping=False)

        # Get the most recent tool name
        last_tool_name = self._history[-1].name
        threshold = self._get_tool_threshold(last_tool_name)

        if len(self._history) < threshold:
            return LoopDetectionResult(is_looping=False)

        # Check the last N tool names
        recent = self._history[-threshold:]

        # All must be the same tool name
        if all(sig.name == last_tool_name for sig in recent):
            # Count how many consecutive (go back further)
            count = threshold
            for i in range(len(self._history) - threshold - 1, -1, -1):
                if self._history[i].name == last_tool_name:
                    count += 1
                else:
                    break

            # Create a synthetic signature for the hint
            synthetic_sig = ToolCallSignature(
                name=last_tool_name,
                args_key="(various arguments)"
            )

            hint = self._build_tool_name_hint(
                tool_name=last_tool_name,
                repeated_count=count,
                threshold=threshold,
            )

            return LoopDetectionResult(
                is_looping=True,
                loop_type="tool-name-repeat",
                repeated_count=count,
                signature=synthetic_sig,
                hint_message=hint,
                threshold_used=threshold,
            )

        return LoopDetectionResult(is_looping=False)

    def _build_informative_hint(
        self,
        loop_type: str,
        signature: ToolCallSignature,
        repeated_count: int,
        threshold: int,
    ) -> str:
        """Build an informative hint that provides information and suggestions.

        v1.46.35: Instead of asking LLM to judge yes/no, we:
        1. Provide factual information about the pattern
        2. List common reasons (both OK and not OK)
        3. Suggest actions without forcing a choice
        """
        # Decode arguments for display
        try:
            args = json.loads(signature.args_key)
            args_display = ", ".join(f"{k}={v!r}" for k, v in list(args.items())[:3])
            if len(args) > 3:
                args_display += ", ..."
        except (json.JSONDecodeError, TypeError):
            args_display = signature.args_key[:100]

        header = f"[Loop Detection Notice: {loop_type} pattern]"
        detail = f"Tool: {signature.name}({args_display}) called {repeated_count} times"

        # Provide informative message with common scenarios
        message = f"""You have called `{signature.name}` {repeated_count} times with this pattern.

**Common scenarios:**
- ✅ OK: Reading different parts of a large file
- ✅ OK: Processing multiple items in a loop
- ✅ OK: Iterative refinement with visible progress
- ❌ Not OK: Repeating the same failed command
- ❌ Not OK: Calling with identical arguments expecting different results

**If you're making progress**, continue with your next step.

**If you're stuck**, consider:
1. Summarizing what you've learned so far
2. Trying a completely different approach
3. Asking the user for clarification

Note: If this pattern continues without progress, you may be asked to provide your final answer."""

        return f"{header}\n{detail}\n\n{message}"

    def _build_tool_name_hint(
        self,
        tool_name: str,
        repeated_count: int,
        threshold: int,
    ) -> str:
        """Build an informative hint for tool-name-only repeat detection.

        v1.46.35: Provides information and context-specific suggestions.
        """
        header = f"[Loop Detection Notice: repeated {tool_name} calls]"
        detail = f"Tool: {tool_name} called {repeated_count} times with varying arguments"

        # Context-specific suggestions based on tool type
        if tool_name in ("shell_exec", "read_file"):
            context_help = """This often happens when:
- Reading a large file chunk by chunk (consider reading the whole file or using grep)
- Running similar commands with small variations (consider a single comprehensive command)
- Checking the same condition repeatedly (the result won't change mid-task)"""
        elif tool_name in ("write_file", "edit_file", "patch_file"):
            context_help = """This often happens when:
- Trying to fix a file with multiple small edits (consider a single comprehensive edit)
- Writing intermediate results (consider accumulating changes before writing)
- Retry after write failure (check permissions and disk space)"""
        else:
            context_help = """This often happens when:
- Making incremental progress but not consolidating
- Repeating similar operations without a clear plan
- Not recognizing when enough information has been gathered"""

        message = f"""{context_help}

**If you're making progress**, continue but consider consolidating your approach.

**If you're stuck**, consider:
1. Summarizing what you've learned and providing your final answer
2. Taking a step back and planning a different approach
3. Asking the user for guidance

Note: If this pattern continues without progress, you may be asked to provide your final answer."""

        return f"{header}\n{detail}\n\n{message}"

    def reset(self) -> None:
        """Reset the detector state."""
        self._history.clear()


__all__ = [
    "ToolCallLoopDetector",
    "ToolCallSignature",
    "LoopDetectionResult",
    "DEFAULT_TOOL_THRESHOLDS",
]
