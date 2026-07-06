"""Agent context manager for Helen interpreter.

Provides automatic integration of:
- WorkingMemory: Track active files, decisions, todos, errors
- Graduated compression: Apply progressive compression strategies
- Three-channel context: Build system + working memory + history

Usage:
    agent_context = AgentContextManager(working_memory_tokens=5000)

    # After each history addition
    agent_context.update_working_memory(message, role)

    # Before LLM call
    messages = agent_context.prepare_context(
        system_prompt="...",
        history=history,
        max_tokens=131072
    )
"""

from __future__ import annotations

import logging
from typing import Any

from helen.runtime.working_memory import WorkingMemory, build_three_channel_context
from helen.runtime.graduated_compression import graduated_compress, _calculate_usage_ratio
from helen.runtime.cache_aware_compression import CacheAwareCompressor, CacheStats
from helen.runtime.history import Message

logger = logging.getLogger(__name__)


class AgentContextManager:
    """Manages agent context: working memory and compression.

    Automatically tracks:
    - Active files (from read_file, write_file, patch_file)
    - Recent decisions (from file modifications)
    - Pending todos (extracted from comments)
    - Error history (from shell_exec failures)

    Automatically applies:
    - Graduated compression when history grows
    - Three-channel context building for LLM calls
    """

    def __init__(
        self,
        working_memory_tokens: int = 5000,
        compression_enabled: bool = True,
        working_memory_enabled: bool = True,
        cache_aware_enabled: bool = True,
    ):
        """Initialize agent context manager.

        Args:
            working_memory_tokens: Token budget for working memory
            compression_enabled: Enable graduated compression
            working_memory_enabled: Enable working memory tracking
            cache_aware_enabled: Enable cache-aware compression (Phase 6)
        """
        self.working_memory = WorkingMemory(max_tokens=working_memory_tokens)
        self.compression_enabled = compression_enabled
        self.working_memory_enabled = working_memory_enabled
        self.cache_aware_enabled = cache_aware_enabled
        self._last_usage_ratio = 0.0
        self._last_cache_stats: CacheStats | None = None
        self._cache_compressor = CacheAwareCompressor() if cache_aware_enabled else None

    def update_from_message(self, content: str, role: str) -> None:
        """Update working memory from a message.

        Extracts:
        - File references from content
        - TODOs from comments
        - Decisions from assistant responses

        Args:
            content: Message content
            role: Message role (user/assistant/tool)
        """
        if not self.working_memory_enabled:
            return

        # Extract file references
        files = self._extract_file_references(content)
        for file in files:
            self.working_memory._add_active_file(file)

        # Extract TODOs
        todos = self._extract_todos(content)
        for todo in todos:
            self.working_memory._add_todo(todo)

        # Extract decisions from assistant
        if role == "assistant":
            decisions = self._extract_decisions(content)
            for decision in decisions:
                self.working_memory._add_decision(decision)

    def update_from_tool_call(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: Any,
        exit_code: int | None = None,
    ) -> None:
        """Update working memory from a tool call.

        Tracks:
        - File operations (read/write/patch)
        - Shell command results and errors
        - Search results

        Args:
            tool_name: Name of the tool (e.g., "read_file")
            tool_args: Tool arguments
            tool_result: Tool result (string or dict)
            exit_code: Exit code for shell commands (if available)
        """
        if not self.working_memory_enabled:
            return

        if tool_name == "read_file":
            file_path = tool_args.get("file_path", "")
            if file_path:
                self.working_memory._add_active_file(file_path)

        elif tool_name == "write_file":
            file_path = tool_args.get("file_path", "")
            if file_path:
                self.working_memory._add_active_file(file_path)
                self.working_memory._add_decision(f"Modified {file_path}")

        elif tool_name == "patch_file":
            file_path = tool_args.get("file_path", "")
            if file_path:
                self.working_memory._add_active_file(file_path)
                self.working_memory._add_decision(f"Patched {file_path}")

        elif tool_name == "shell_exec":
            command = tool_args.get("command", "")
            if exit_code is not None and exit_code != 0:
                error_msg = str(tool_result)[:200] if tool_result else "Unknown error"
                self.working_memory._add_error(command, error_msg)
            elif isinstance(tool_result, str) and "error" in tool_result.lower():
                error_msg = tool_result[:200]
                self.working_memory._add_error(command, error_msg)

        elif tool_name in ("glob_files", "grep_files"):
            # Track search patterns
            pattern = tool_args.get("pattern", "")
            if pattern:
                self.working_memory._add_decision(f"Searched for: {pattern}")

    def prepare_context(
        self,
        system_prompt: str | None,
        history: list[Message],
        max_tokens: int,
        current_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """Prepare three-channel context for LLM call.

        Applies:
        1. Graduated compression to history (if enabled)
        2. Three-channel context building (if working memory enabled)

        Args:
            system_prompt: System prompt text
            history: Conversation history
            max_tokens: Maximum context window tokens
            current_prompt: Current user prompt (for budget calculation)

        Returns:
            List of message dicts ready for LLM API
        """
        # Apply graduated compression if enabled
        if self.compression_enabled and len(history) > 10:
            # Calculate actual usage_ratio (0.0-1.0) before passing to graduated_compress
            total_tokens = sum(msg.token_count for msg in history)
            usage_ratio = total_tokens / max_tokens if max_tokens > 0 else 0.0

            # Phase 6: Use cache-aware compression if enabled (replaces graduated compression)
            if self.cache_aware_enabled and self._cache_compressor is not None:
                compressed_history, cache_stats = self._cache_compressor.compress(
                    history, max_tokens, usage_ratio
                )
                self._last_cache_stats = cache_stats
                if cache_stats.messages_modified > 0:
                    logger.debug(
                        f"Applied cache-aware compression: "
                        f"strategy={cache_stats.compression_strategy}, "
                        f"cache_hit={cache_stats.estimated_cache_hit}, "
                        f"tokens_saved={cache_stats.tokens_saved}"
                    )
            else:
                compressed_history, layer = graduated_compress(history, usage_ratio, max_tokens)
                if layer != "none":
                    logger.debug(f"Applied graduated compression: {layer}")
                    self._last_usage_ratio = sum(
                        msg.token_count for msg in compressed_history
                    ) / max_tokens if max_tokens > 0 else 0.0
        else:
            compressed_history = history

        # Build three-channel context if working memory enabled
        if self.working_memory_enabled:
            messages = build_three_channel_context(
                system_prompt=system_prompt or "",
                working_memory=self.working_memory,
                history=compressed_history,
                max_tokens=max_tokens,
            )
        else:
            # Fallback: just system + history
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            for msg in compressed_history:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        return messages

    def _extract_file_references(self, content: str) -> list[str]:
        """Extract file references from content.

        Looks for patterns like:
        - path/to/file.py
        - ./file.txt
        - src/main.helen

        Args:
            content: Text content

        Returns:
            List of file paths found
        """
        import re

        # Match common file path patterns
        patterns = [
            r'(?:^|\s|["\'(])([\w./-]+\.(?:py|js|ts|json|yaml|yml|md|txt|helen|rs|go|java|c|cpp|h|hpp))\b',
            r'(?:^|\s|["\'(])([\w./-]+/(?:[\w.-]+/)*[\w.-]+)\b',
        ]

        files = []
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                file_path = match.group(1)
                # Filter out common false positives
                if file_path not in ("http://", "https://", "ftp://", "git://"):
                    files.append(file_path)

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        return unique_files

    def _extract_todos(self, content: str) -> list[str]:
        """Extract TODO items from content.

        Looks for patterns like:
        - TODO: ...
        - FIXME: ...
        - [ ] ...

        Args:
            content: Text content

        Returns:
            List of TODO items found
        """
        import re

        patterns = [
            r'TODO[:\s]+(.+?)(?:\n|$)',
            r'FIXME[:\s]+(.+?)(?:\n|$)',
            r'\[\s\]\s+(.+?)(?:\n|$)',
        ]

        todos = []
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                todo = match.group(1).strip()
                if len(todo) > 5 and len(todo) < 200:  # Filter out noise
                    todos.append(todo)

        return todos

    def _extract_decisions(self, content: str) -> list[str]:
        """Extract recent decisions from assistant content.

        Looks for patterns like:
        - I'll use ...
        - Let me try ...
        - Decided to ...
        - Approach: ...

        Args:
            content: Assistant message content

        Returns:
            List of decisions found
        """
        import re

        patterns = [
            r'(?:I\'ll|I will|Let me|I\'m going to|Decided to|Approach:)\s+(.+?)(?:\.|\n|$)',
            r'(?:using|chose|selected|opted for)\s+(.+?)(?:\.|\n|$)',
        ]

        decisions = []
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                decision = match.group(1).strip()
                if len(decision) > 10 and len(decision) < 150:  # Filter out noise
                    decisions.append(decision)

        return decisions

    def get_stats(self) -> dict[str, Any]:
        """Get current context manager statistics.

        Returns:
            Dict with stats about working memory and compression
        """
        stats = {
            "working_memory_enabled": self.working_memory_enabled,
            "compression_enabled": self.compression_enabled,
            "cache_aware_enabled": self.cache_aware_enabled,
            "active_files": len(self.working_memory.active_files),
            "recent_decisions": len(self.working_memory.recent_decisions),
            "pending_todos": len(self.working_memory.pending_todos),
            "error_history": len(self.working_memory.error_history),
        }
        if self._last_cache_stats is not None:
            stats["cache_stats"] = self._last_cache_stats.to_dict()
        return stats
