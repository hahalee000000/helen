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

    def to_context(self) -> str:
        """Format working memory as context for the LLM.

        Returns:
            Formatted string representation of working memory
        """
        parts = []

        if self.task_description:
            parts.append("## Current Task")
            parts.append(self.task_description)
            parts.append("")

        if self.active_files:
            parts.append("## Active Files")
            for f in self.active_files[-5:]:  # Last 5 files
                parts.append(f"- {f}")
            parts.append("")

        if self.recent_decisions:
            parts.append("## Recent Decisions")
            for d in self.recent_decisions[-5:]:  # Last 5 decisions
                parts.append(f"- {d}")
            parts.append("")

        if self.pending_todos:
            parts.append("## Pending TODOs")
            for t in self.pending_todos[:10]:  # First 10 TODOs
                parts.append(f"- [ ] {t}")
            parts.append("")

        if self.error_history:
            parts.append("## Recent Errors")
            for e in self.error_history[-3:]:  # Last 3 errors
                cmd = e.get("command", "unknown")
                err = e.get("error", "unknown")[:100]  # Truncate
                parts.append(f"- Command: {cmd}")
                parts.append(f"  Error: {err}")
            parts.append("")

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
        """Add a file to active files list, maintaining limit.

        Args:
            file_path: Path to the file
        """
        if file_path not in self.active_files:
            self.active_files.append(file_path)
            # Keep only last 10 files
            if len(self.active_files) > 10:
                self.active_files = self.active_files[-10:]

    def _add_decision(self, decision: str) -> None:
        """Add a decision to recent decisions list.

        Args:
            decision: Decision description
        """
        self.recent_decisions.append(decision)
        # Keep only last 10 decisions
        if len(self.recent_decisions) > 10:
            self.recent_decisions = self.recent_decisions[-10:]

    def _add_error(self, command: str, error: str) -> None:
        """Add an error to error history.

        Args:
            command: Command that failed
            error: Error message
        """
        self.error_history.append({
            "command": command,
            "error": error,
        })
        # Keep only last 5 errors
        if len(self.error_history) > 5:
            self.error_history = self.error_history[-5:]

    def _add_todo(self, todo: str) -> None:
        """Add a TODO item to pending todos list.

        Args:
            todo: TODO description
        """
        # Avoid duplicates
        if todo not in self.pending_todos:
            self.pending_todos.append(todo)
            # Keep only last 20 TODOs
            if len(self.pending_todos) > 20:
                self.pending_todos = self.pending_todos[-20:]

    def _complete_todo(self, todo: str) -> None:
        """Remove a TODO item when completed.

        Args:
            todo: TODO description to remove
        """
        if todo in self.pending_todos:
            self.pending_todos.remove(todo)

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
    max_tokens: int = 131072,
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
    working_context = working_memory.to_context()
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
        msg_chars = len(msg.content)
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
