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

logger = logging.getLogger(__name__)


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

    def to_context(self, budget_chars: int | None = None) -> str:
        """Format working memory as context for the LLM.

        Args:
            budget_chars: Optional character budget. When provided, sections
                are progressively dropped (lowest-priority first) to fit
                within the budget. Priority order (highest first):
                Current Task > Recent Errors > Active Files >
                Recent Decisions > Pending TODOs.
                If None, max_tokens * 4 is used as the hard upper bound.

        Returns:
            Formatted string representation of working memory
        """
        # max_tokens acts as a hard upper bound on output size.
        # When no explicit budget is given, use max_tokens as the limit.
        effective_budget = budget_chars
        if self.max_tokens > 0:
            max_chars = self.max_tokens * 4  # Rough 4 chars/token estimate
            if effective_budget is None:
                effective_budget = max_chars
            else:
                effective_budget = min(effective_budget, max_chars)

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
        total_chars = sum(
            len("\n".join(sections[i][0] + sections[i][1])) + 1
            for i in included
        ) if included else 0

        while total_chars > effective_budget and len(included) > 1:
            # Drop the lowest-priority section still included
            # Keep at least one section — body truncation handles the rest
            dropped = included.pop()
            total_chars -= (
                len("\n".join(sections[dropped][0] + sections[dropped][1])) + 1
            )

        # If even the highest-priority section alone exceeds budget,
        # truncate its body content to fit.
        parts = []
        remaining_chars = effective_budget
        for idx in included:
            header, body = sections[idx]
            header_str = "\n".join(header)
            body_str = "\n".join(body)
            section_str = f"{header_str}\n{body_str}"

            if len(section_str) <= remaining_chars:
                parts.append(section_str)
                remaining_chars -= len(section_str) + 1  # +1 for trailing \n
            elif remaining_chars > len(header_str) + 4:
                # Can fit header + partial body; truncate body
                body_budget = remaining_chars - len(header_str) - 2
                truncated_body = body_str[:body_budget]
                # Cut at last complete line to avoid mid-character break
                last_newline = truncated_body.rfind("\n")
                if last_newline > 0:
                    truncated_body = truncated_body[:last_newline]
                parts.append(f"{header_str}\n{truncated_body}")
                remaining_chars = 0
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

    Channel 1 (15%): System instructions
    Channel 2 (50%): Working memory
    Channel 3 (35%): Long-term memory (compressed history)

    Args:
        system_prompt: System prompt text
        working_memory: Working memory instance
        history: Conversation history (may be compressed)
        budget: Token budget allocation (default: 15/50/35 split)
        max_tokens: Maximum context window tokens (for budget enforcement)

    Returns:
        List of messages ready for LLM submission
    """
    from helen.runtime.token_utils import DEFAULT_CONTEXT_WINDOW
    if max_tokens is None:
        max_tokens = DEFAULT_CONTEXT_WINDOW

    if budget is None:
        budget = {
            "system": 0.15,
            "working": 0.50,
            "history": 0.35,
        }

    messages = []

    # Channel 1: System instructions (budget: 15% of max_tokens)
    system_budget = int(max_tokens * budget.get("system", 0.15))
    if system_prompt:
        # Truncate system prompt if it exceeds budget (rough: 4 chars/token)
        max_chars = system_budget * 4
        truncated_prompt = system_prompt[:max_chars] if len(system_prompt) > max_chars else system_prompt
        messages.append({
            "role": "system",
            "content": truncated_prompt,
        })

    # Channel 2: Working memory (budget: 50% of max_tokens, capped by working_memory.max_tokens)
    working_budget = int(max_tokens * budget.get("working", 0.50))
    working_budget = min(working_budget, working_memory.max_tokens)
    working_budget_chars = working_budget * 4  # Rough conversion

    working_context = working_memory.to_context(budget_chars=working_budget_chars)
    if working_context:
        messages.append({
            "role": "system",
            "content": f"[Working Memory]\n{working_context}",
        })

    # Channel 3: Conversation history (budget: 35% of max_tokens)
    history_budget = int(max_tokens * budget.get("history", 0.35))
    history_budget_chars = history_budget * 4  # Rough conversion

    # Truncate history to fit within budget
    selected_history = []
    used_chars = 0
    # Iterate from most recent to oldest, keep until budget exhausted
    for msg in reversed(history):
        # v1.17: Use _message_text for multimodal content length calculation
        msg_chars = len(_message_text(msg.content))
        if used_chars + msg_chars <= history_budget_chars:
            selected_history.insert(0, msg)
            used_chars += msg_chars
        else:
            break  # Budget exhausted

    for msg in selected_history:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    return messages
