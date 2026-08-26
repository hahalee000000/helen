"""Working memory management for long-running agents.

Phase 4: Maintains a compact, high-priority context buffer that tracks:
- Current task description
- Active files (recently read/modified)
- Recent decisions (key choices made)
- Pending TODOs
- Error history (recent errors and fixes)

This provides the model with essential context without consuming
the full conversation history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from helen.runtime.history import _message_text
from helen.runtime.token_utils import estimate_tokens_simple, is_cjk

logger = logging.getLogger(__name__)

# Three-channel budget allocation (fractions of effective max tokens)
# Effective max = max_tokens * (1 - RESPONSE_BUFFER_RATIO)
RESPONSE_BUFFER_RATIO = 0.10
THREE_CHANNEL_BUDGET = {"system": 0.10, "working": 0.45, "history": 0.35}


def _tokens_to_chars(text: str, token_budget: int) -> int:
    """Convert token budget to character budget (CJK-aware).

    Uses the actual character composition of the text to estimate
    how many characters fit within the token budget.

    Args:
        text: Reference text for character composition analysis
        token_budget: Target number of tokens

    Returns:
        Estimated number of characters that fit within token_budget
    """
    if not text:
        return 0
    cjk_count = sum(1 for c in text if is_cjk(c))
    total_len = len(text)
    if total_len == 0:
        return 0
    # Weighted chars-per-token ratio based on actual composition
    ratio = (cjk_count * 1.2 + (total_len - cjk_count) * 4.0) / total_len
    return int(token_budget * ratio)


def _truncate_to_token_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within token budget (CJK-aware).

    Args:
        text: Text to truncate
        max_tokens: Maximum number of tokens allowed

    Returns:
        Truncated text that fits within max_tokens
    """
    if estimate_tokens_simple(text) <= max_tokens:
        return text
    char_budget = _tokens_to_chars(text, max_tokens)
    return text[:max(0, char_budget)]


@dataclass
class WorkingMemory:
    """Compact working memory for tracking essential context.

    Maintains a small, high-priority context buffer that the model
    can reference for current task state.
    """

    task_description: str = ""
    active_files: list[str] = field(default_factory=list)
    recent_decisions: list[str] = field(default_factory=list)
    pending_todos: list[str] = field(default_factory=list)
    error_history: list[dict] = field(default_factory=list)

    # Token budget for working memory
    max_tokens: int = 5000

    def to_context(self, budget_tokens: int | None = None) -> str:
        """Format working memory as context for the LLM.

        Args:
            budget_tokens: Optional token budget. When provided, sections
                are progressively dropped (lowest-priority first) to fit
                within the budget. Priority order (highest first):
                Current Task > Recent Errors > Active Files >
                Recent Decisions > Pending TODOs.
                If None, max_tokens is used as the hard upper bound.

        Returns:
            Formatted string representation of working memory
        """
        # max_tokens acts as a hard upper bound on output size (in tokens).
        # When no explicit budget is given, use max_tokens as the limit.
        effective_budget = budget_tokens
        if self.max_tokens > 0:
            if effective_budget is None:
                effective_budget = self.max_tokens
            else:
                effective_budget = min(effective_budget, self.max_tokens)

        # Build sections in priority order (highest priority first).
        # When over budget, sections are dropped from the END first.
        # Each entry: (section_header_lines, section_body_lines)
        sections: list[tuple[list[str], list[str]]] = []

        if self.task_description:
            sections.append(
                (["## Current Task"], [self.task_description, ""])
            )

        if self.error_history:
            body: list[str] = []
            for e in self.error_history[-3:]:
                cmd = e.get("command", "unknown")
                err = e.get("error", "unknown")[:100]
                body.append(f"- Command: {cmd}")
                body.append(f"  Error: {err}")
            body.append("")
            sections.append((["## Recent Errors"], body))

        if self.active_files:
            body = [f"- {f}" for f in self.active_files[-5:]]
            body.append("")
            sections.append((["## Active Files"], body))

        if self.recent_decisions:
            body = [f"- {d}" for d in self.recent_decisions[-5:]]
            body.append("")
            sections.append((["## Recent Decisions"], body))

        if self.pending_todos:
            body = [f"- [ ] {t}" for t in self.pending_todos[:10]]
            body.append("")
            sections.append((["## Pending TODOs"], body))

        if effective_budget is None:
            # No budget — include everything
            parts: list[str] = []
            for header, body in sections:
                parts.extend(header)
                parts.extend(body)
            return "\n".join(parts)

        # With budget: drop lowest-priority sections until we fit.
        # Iterate from lowest priority (end of list) to highest.
        included = list(range(len(sections)))
        total_tokens = sum(
            estimate_tokens_simple("\n".join(sections[i][0] + sections[i][1]))
            for i in included
        ) if included else 0

        while total_tokens > effective_budget and len(included) > 1:
            # Drop the lowest-priority section still included
            # Keep at least one section — body truncation handles the rest
            dropped = included.pop()
            total_tokens -= estimate_tokens_simple(
                "\n".join(sections[dropped][0] + sections[dropped][1])
            )

        # If even the highest-priority section alone exceeds budget,
        # truncate its body content to fit.
        parts = []
        remaining_tokens = effective_budget
        for idx in included:
            header, body = sections[idx]
            header_str = "\n".join(header)
            body_str = "\n".join(body)
            section_str = f"{header_str}\n{body_str}"
            section_tokens = estimate_tokens_simple(section_str)

            if section_tokens <= remaining_tokens:
                parts.append(section_str)
                remaining_tokens -= section_tokens
            else:
                header_tokens = estimate_tokens_simple(header_str)
                if remaining_tokens > header_tokens + 2:
                    # Can fit header + partial body; truncate body
                    # Estimate chars/token ratio (CJK-aware) for truncation
                    body_budget_tokens = remaining_tokens - header_tokens - 1
                    char_budget = _tokens_to_chars(body_str, body_budget_tokens)
                    truncated_body = body_str[:char_budget]
                    # Cut at last complete line to avoid mid-character break
                    last_newline = truncated_body.rfind("\n")
                    if last_newline > 0:
                        truncated_body = truncated_body[:last_newline]
                    parts.append(f"{header_str}\n{truncated_body}")
                    remaining_tokens = 0
                    break
                else:
                    break

        return "\n".join(parts)

    def update_from_tool_call(self, tool_call: dict, tool_result: Any) -> None:
        """Update working memory based on a tool call and its result.

        Args:
            tool_call: Tool call information (name, args)
            tool_result: Tool execution result
        """
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        if tool_name == "read_file":
            # Track file access
            file_path = tool_args.get("path", "")
            if file_path:
                self._add_active_file(file_path)

        elif tool_name in ("write_file", "patch_file"):
            # Track file modifications
            file_path = tool_args.get("path", "")
            if file_path:
                self._add_active_file(file_path)
                self._add_decision(f"Modified file: {file_path}")

        elif tool_name == "shell_exec":
            # Track shell commands and errors
            command = tool_args.get("command", "")

            # Check if command failed
            if hasattr(tool_result, "returncode") and tool_result.returncode != 0:
                error_msg = tool_result.stderr or tool_result.stdout or "Unknown error"
                self._add_error(command, error_msg)
            elif isinstance(tool_result, dict) and tool_result.get("exit_code", 0) != 0:
                error_msg = tool_result.get("error", "Unknown error")
                self._add_error(command, error_msg)

    def _add_active_file(self, file_path: str) -> None:
        """Add a file to active files list, maintaining token budget.

        Token-level eviction: when total tokens exceed max_tokens,
        oldest entries are removed first.

        Args:
            file_path: Path to the file
        """
        if file_path not in self.active_files:
            self.active_files.append(file_path)
            # Token-level eviction: remove oldest until under budget
            self._evict_to_budget()

    def _add_decision(self, decision: str) -> None:
        """Add a decision to recent decisions list, maintaining token budget.

        Token-level eviction: when total tokens exceed max_tokens,
        oldest entries are removed first.

        Args:
            decision: Decision description
        """
        self.recent_decisions.append(decision)
        # Token-level eviction: remove oldest until under budget
        self._evict_to_budget()

    def _add_error(self, command: str, error: str) -> None:
        """Add an error to error history, maintaining token budget.

        Token-level eviction: when total tokens exceed max_tokens,
        oldest entries are removed first.

        Args:
            command: Command that failed
            error: Error message
        """
        self.error_history.append({
            "command": command,
            "error": error,
        })
        # Token-level eviction: remove oldest until under budget
        self._evict_to_budget()

    def _add_todo(self, todo: str) -> None:
        """Add a TODO item to pending todos list, maintaining token budget.

        Token-level eviction: when total tokens exceed max_tokens,
        oldest entries are removed first.

        Args:
            todo: TODO description
        """
        # Avoid duplicates
        if todo not in self.pending_todos:
            self.pending_todos.append(todo)
            # Token-level eviction: remove oldest until under budget
            self._evict_to_budget()

    def _complete_todo(self, todo: str) -> None:
        """Remove a TODO item when completed.

        Args:
            todo: TODO description to remove
        """
        if todo in self.pending_todos:
            self.pending_todos.remove(todo)

    def _evict_to_budget(self) -> None:
        """Evict oldest entries to stay within token budget.

        Token-level eviction strategy:
        1. Estimate total tokens across all lists
        2. If over max_tokens, remove oldest entries from lowest-priority lists first
        3. Priority (highest first): task_description > error_history > active_files >
           recent_decisions > pending_todos

        This ensures the most important information is preserved even when
        individual entries vary greatly in size.
        """
        if self.max_tokens <= 0:
            return  # No budget constraint

        # Estimate current total tokens
        # Rough estimate: 4 chars per token for English, but we use a conservative
        # multiplier for mixed content
        def estimate_list_tokens(items: list) -> int:
            total_chars = sum(len(str(item)) for item in items)
            return total_chars // 4

        # Task description is always preserved (highest priority)
        task_tokens = len(self.task_description) // 4 if self.task_description else 0

        # Calculate tokens for each list
        error_tokens = estimate_list_tokens(
            [f"{e.get('command', '')}{e.get('error', '')}" for e in self.error_history]
        )
        file_tokens = estimate_list_tokens(self.active_files)
        decision_tokens = estimate_list_tokens(self.recent_decisions)
        todo_tokens = estimate_list_tokens(self.pending_todos)

        total_tokens = task_tokens + error_tokens + file_tokens + decision_tokens + todo_tokens

        # If under budget, nothing to do
        if total_tokens <= self.max_tokens:
            return

        # Evict from lowest-priority lists first
        # Priority order (evict first): pending_todos > recent_decisions > active_files > error_history
        # task_description is never evicted

        # Phase 1: Evict pending_todos (lowest priority)
        while todo_tokens > 0 and total_tokens > self.max_tokens and self.pending_todos:
            removed = self.pending_todos.pop(0)
            todo_tokens -= len(removed) // 4
            total_tokens -= len(removed) // 4

        # Phase 2: Evict recent_decisions
        while decision_tokens > 0 and total_tokens > self.max_tokens and self.recent_decisions:
            removed = self.recent_decisions.pop(0)
            decision_tokens -= len(removed) // 4
            total_tokens -= len(removed) // 4

        # Phase 3: Evict active_files
        while file_tokens > 0 and total_tokens > self.max_tokens and self.active_files:
            removed = self.active_files.pop(0)
            file_tokens -= len(removed) // 4
            total_tokens -= len(removed) // 4

        # Phase 4: Evict error_history (highest priority list, evict last)
        while error_tokens > 0 and total_tokens > self.max_tokens and self.error_history:
            removed = self.error_history.pop(0)
            error_tokens -= (len(removed.get('command', '')) + len(removed.get('error', ''))) // 4
            total_tokens -= (len(removed.get('command', '')) + len(removed.get('error', ''))) // 4

    def estimate_tokens(self) -> int:
        """Estimate token count for working memory context.

        Returns:
            Estimated token count
        """
        context = self.to_context()
        # Rough estimate: 4 chars per token
        return len(context) // 4

    def clear(self) -> None:
        """Clear all working memory."""
        self.task_description = ""
        self.active_files.clear()
        self.recent_decisions.clear()
        self.pending_todos.clear()
        self.error_history.clear()


def build_three_channel_context(
    system_prompt: str,
    working_memory: WorkingMemory,
    history: list,
    budget: dict[str, float] | None = None,
    max_tokens: int | None = None,
) -> list[dict]:
    """Build three-channel context for LLM submission.

    Channel 1 (10%): System instructions
    Channel 2 (45%): Working memory (capped by working_memory.max_tokens)
    Channel 3 (35%): Long-term memory (compressed history)
    Response buffer (10%): Reserved for model response

    Budgets are token-based (not character-based) for accuracy with
    CJK and multimodal content.

    Args:
        system_prompt: System prompt text
        working_memory: Working memory instance
        history: Conversation history (may be compressed)
        budget: Token budget allocation (default: 10/45/35 + 10% response)
        max_tokens: Maximum context window tokens (for budget enforcement)

    Returns:
        List of messages ready for LLM submission
    """
    from helen.runtime.token_utils import DEFAULT_CONTEXT_WINDOW
    if max_tokens is None:
        max_tokens = DEFAULT_CONTEXT_WINDOW

    if budget is None:
        budget = THREE_CHANNEL_BUDGET

    # Reserve response buffer before distributing to channels
    effective_max = int(max_tokens * (1.0 - RESPONSE_BUFFER_RATIO))

    messages = []

    # Channel 1: System instructions (token-based budget)
    system_budget = int(effective_max * budget.get("system", 0.10))
    if system_prompt:
        truncated_prompt = _truncate_to_token_budget(system_prompt, system_budget)
        messages.append({
            "role": "system",
            "content": truncated_prompt,
        })

    # Channel 2: Working memory (token-based, capped by working_memory.max_tokens)
    working_budget = int(effective_max * budget.get("working", 0.45))
    working_budget = min(working_budget, working_memory.max_tokens)

    working_context = working_memory.to_context(budget_tokens=working_budget)
    if working_context:
        messages.append({
            "role": "system",
            "content": f"[Working Memory]\n{working_context}",
        })

    # Channel 3: Conversation history (token-based, uses msg.token_count
    # which correctly handles multimodal content including image token estimate)
    history_budget = int(effective_max * budget.get("history", 0.35))

    # Select history messages from most recent to oldest within token budget
    selected_history = []
    used_tokens = 0
    for msg in reversed(history):
        msg_tokens = msg.token_count  # Handles multimodal correctly
        if used_tokens + msg_tokens <= history_budget:
            selected_history.insert(0, msg)
            used_tokens += msg_tokens
        else:
            break  # Budget exhausted

    for msg in selected_history:
        api_msg = {
            "role": msg.role,
            "content": msg.content,
        }
        # v1.46.3: Include tool fields to avoid API 400 errors
        if msg.tool_calls:
            api_msg["tool_calls"] = msg.tool_calls
        if msg.tool_call_id:
            api_msg["tool_call_id"] = msg.tool_call_id
        messages.append(api_msg)

    return messages
