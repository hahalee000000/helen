"""Agent context manager for Helen interpreter.

Provides automatic integration of:
- WorkingMemory: Track active files, decisions, todos, errors
- Unified compression: "none" | "graduated" | "traditional"
- Cache-aware wrapping: Preserves stable prefix for prompt cache
- Three-channel context: Build system + working memory + history

Compression architecture:

    prepare_context()
        └─> _compress_history()
              ├─ strategy="none"       → no compression
              ├─ strategy="traditional" → HistoryManager.enforce_limit()
              └─ strategy="graduated"   → graduated_compress() (5-layer pipeline)
              Then, if cache_aware_enabled:
                  └─ _apply_cache_aware_wrap()
                       preserves first N messages (cache zone)
                       re-applies base strategy to compressible zone only

Usage:
    agent_context = AgentContextManager(
        working_memory_tokens=5000,
        compression_strategy="graduated",
        cache_aware_enabled=True,
    )

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
from helen.runtime.cache_aware_compression import (
    CacheStats,
    DEFAULT_CACHE_ZONE_RATIO,
    MIN_CACHE_ZONE_MESSAGES,
)
from helen.runtime.history import Message

logger = logging.getLogger(__name__)

# Valid compression strategies
COMPRESSION_STRATEGIES = frozenset({"none", "graduated", "traditional"})


class AgentContextManager:
    """Manages agent context: working memory and compression.

    Automatically tracks:
    - Active files (from read_file, write_file, patch_file)
    - Recent decisions (from file modifications)
    - Pending todos (extracted from comments)
    - Error history (from shell_exec failures)

    Compression architecture (unified entry point):
    - compression_strategy controls the base algorithm:
        "none"       → no compression
        "graduated"  → 5-layer graduated pipeline (default)
        "traditional" → HistoryManager single-layer compress
    - cache_aware_enabled optionally wraps the base algorithm
      to preserve the first N messages (cache-friendly zone)
    """

    def __init__(
        self,
        working_memory_tokens: int = 5000,
        compression_strategy: str = "graduated",
        working_memory_enabled: bool = True,
        cache_aware_enabled: bool = True,
        llm_client: Any | None = None,
        *,
        compression_enabled: bool | None = None,
    ):
        """Initialize agent context manager.

        Args:
            working_memory_tokens: Token budget for working memory
            compression_strategy: Compression strategy
                "none" | "graduated" | "traditional"
            working_memory_enabled: Enable working memory tracking
            cache_aware_enabled: Enable cache-aware prefix preservation
            llm_client: Optional LLM client for Layer 5 semantic summarization.
                        Expected signature: llm_client(messages) -> str
                        When provided, graduated compression uses LLM for
                        high-quality semantic compression at Layer 5.
            compression_enabled: (deprecated) Backward compat shim.
                True → "graduated", False → "none".
                Only used when compression_strategy is not explicitly set.
        """
        # Backward compatibility: compression_enabled → compression_strategy
        if compression_enabled is not None:
            compression_strategy = "graduated" if compression_enabled else "none"

        if compression_strategy not in COMPRESSION_STRATEGIES:
            logger.warning(
                f"Unknown compression strategy {compression_strategy!r}, "
                f"falling back to 'graduated'"
            )
            compression_strategy = "graduated"

        self.working_memory = WorkingMemory(max_tokens=working_memory_tokens)
        self._compression_strategy = compression_strategy
        self.working_memory_enabled = working_memory_enabled
        self.cache_aware_enabled = cache_aware_enabled
        self.llm_client = llm_client
        self._last_usage_ratio = 0.0
        self._last_cache_stats: CacheStats | None = None

    # -- Backward compatibility property for compression_enabled --

    @property
    def compression_enabled(self) -> bool:
        """Whether any compression is enabled (strategy != 'none')."""
        return self._compression_strategy != "none"

    @compression_enabled.setter
    def compression_enabled(self, value: bool) -> None:
        """Set compression via boolean (backward compat)."""
        self._compression_strategy = "graduated" if value else "none"

    @property
    def compression_strategy(self) -> str:
        """Current compression strategy: 'none' | 'graduated' | 'traditional'."""
        return self._compression_strategy

    @compression_strategy.setter
    def compression_strategy(self, value: str) -> None:
        if value not in COMPRESSION_STRATEGIES:
            logger.warning(
                f"Unknown compression strategy {value!r}, "
                f"falling back to 'graduated'"
            )
            value = "graduated"
        self._compression_strategy = value

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
        1. Compression to history (via unified _compress_history)
        2. Three-channel context building (if working memory enabled)

        Args:
            system_prompt: System prompt text
            history: Conversation history
            max_tokens: Maximum context window tokens
            current_prompt: Current user prompt (for budget calculation)

        Returns:
            List of message dicts ready for LLM API
        """
        # Apply compression via unified entry point
        compressed_history = self._compress_history(history, max_tokens)

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

    def _compress_history(
        self,
        history: list[Message],
        max_tokens: int,
    ) -> list[Message]:
        """Unified compression entry point.

        Composition logic:
        1. Skip if strategy="none" or usage is below first threshold.
        2. If cache_aware_enabled: preserve first N messages (cache zone),
           apply base strategy only to the compressible suffix.
        3. Otherwise: apply base strategy to full history.

        Args:
            history: Conversation history
            max_tokens: Maximum context window tokens

        Returns:
            Compressed history
        """
        strategy = self._compression_strategy

        if strategy == "none" or len(history) <= 1:
            return history

        usage_ratio = _calculate_usage_ratio(history, max_tokens)

        # Skip graduated compression when below the first layer threshold —
        # graduated_compress would return the history unchanged anyway.
        # For traditional, check against budget (80% of max_tokens).
        if strategy == "graduated" and usage_ratio < 0.60:
            return history
        if strategy == "traditional":
            total_tokens = sum(m.token_count for m in history)
            if total_tokens <= int(max_tokens * 0.8):
                return history

        # Branch: cache_aware wraps the base strategy; otherwise run it directly.
        # When cache_aware is on, we skip the global base compression and let
        # _apply_cache_aware_wrap run the base strategy only on the suffix,
        # avoiding wasted work (the global result would be discarded).
        if self.cache_aware_enabled:
            return self._apply_cache_aware_wrap(history, max_tokens)

        # No cache-aware: run base compression on full history
        if strategy == "traditional":
            return self._apply_traditional(history, max_tokens)

        # graduated
        compressed, layer = graduated_compress(
            history, usage_ratio, max_tokens, llm_client=self.llm_client
        )
        if layer != "none":
            logger.debug(f"Applied graduated compression: {layer}")
            self._last_usage_ratio = _calculate_usage_ratio(compressed, max_tokens)
        return compressed

    def _apply_traditional(
        self,
        history: list[Message],
        max_tokens: int,
    ) -> list[Message]:
        """Traditional single-layer compression via HistoryManager.

        Uses HistoryManager.enforce_limit() which applies summarize or
        truncate based on its configured compression_mode. When the
        interpreter's HistoryManager is available, its compression_mode
        is respected; otherwise defaults to "summarize".

        Args:
            history: Conversation history
            max_tokens: Maximum context window tokens

        Returns:
            Compressed history
        """
        from helen.runtime.history import HistoryManager

        # Try to read the interpreter's configured compression_mode
        mode = "summarize"
        try:
            from helen.stdlib.context import _interpreter_history_manager
            if _interpreter_history_manager is not None:
                mode = getattr(_interpreter_history_manager, "compression_mode", "summarize")
        except ImportError:
            pass

        manager = HistoryManager(context_window=max_tokens, compression_mode=mode)
        return manager.enforce_limit(list(history))

    def _apply_cache_aware_wrap(
        self,
        history: list[Message],
        max_tokens: int,
    ) -> list[Message]:
        """Cache-aware wrapping: preserve prefix, compress suffix.

        Splits history at the cache zone boundary:
        - Cache zone (first N messages): kept unchanged, ensuring
          prompt cache hits.
        - Compressible zone (remaining messages): apply the base
          compression strategy with adjusted budget.

        This composes cache-awareness with ANY base strategy, instead
        of being a separate mutually-exclusive path.

        Args:
            history: The uncompressed original history
            max_tokens: Maximum context window tokens

        Returns:
            History with cache zone preserved and suffix compressed
        """
        cache_zone_end = self._identify_cache_zone(len(history))

        if cache_zone_end >= len(history):
            # Entire history is cache zone — nothing to compress
            return history

        # Cache zone: untouched prefix
        cache_zone = history[:cache_zone_end]
        cache_tokens = sum(m.token_count for m in cache_zone)

        # Compressible zone: suffix
        compressible = history[cache_zone_end:]
        remaining_budget = max(1, max_tokens - cache_tokens)

        # Apply base strategy to compressible zone only
        if self._compression_strategy == "traditional":
            compressed_zone = self._apply_traditional(
                compressible, remaining_budget
            )
        else:  # "graduated"
            zone_ratio = _calculate_usage_ratio(compressible, remaining_budget)
            compressed_zone, layer = graduated_compress(
                compressible, zone_ratio, remaining_budget, llm_client=self.llm_client
            )
            if layer != "none":
                logger.debug(
                    f"Cache-aware + graduated: applied {layer} to compressible zone"
                )

        # Track cache stats for reporting
        messages_modified = sum(
            1 for m in compressed_zone
            if getattr(m, "compressed", False)
        )
        self._last_cache_stats = CacheStats(
            cache_zone_size=len(cache_zone),
            compressible_zone_size=len(compressible),
            messages_modified=messages_modified,
            cache_zone_preserved=True,
            compression_strategy=f"cache_aware+{self._compression_strategy}",
        )

        return cache_zone + compressed_zone

    def _identify_cache_zone(self, history_length: int) -> int:
        """Calculate cache zone size (number of messages to preserve).

        Mirrors CacheAwareCompressor._identify_cache_zone logic.

        Args:
            history_length: Total number of messages in history

        Returns:
            Number of messages in the cache zone
        """
        if history_length == 0:
            return 0

        ratio_based = int(history_length * DEFAULT_CACHE_ZONE_RATIO)
        cache_zone_size = max(ratio_based, MIN_CACHE_ZONE_MESSAGES)
        cache_zone_size = min(cache_zone_size, history_length)

        # Leave room for at least 2 messages in compressible zone
        if history_length - cache_zone_size < 2:
            cache_zone_size = max(0, history_length - 2)

        return cache_zone_size

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
            "compression_strategy": self._compression_strategy,
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
