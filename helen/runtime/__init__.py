"""Runtime API interface and default Hermes implementation (HLD 3.8.1).

Runtime provides the abstraction layer between Helen Core and external
services (LLM APIs, Memory, Skills, Tools). Core code never imports
Hermes directly — it only uses this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import os
import threading
import uuid

# Import Message from history module to avoid duplication
from helen.runtime.history import Message


@dataclass
class ToolSchema:
    """Schema for a tool available to the LLM."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillMeta:
    """Lightweight skill metadata for Tier 1 Skill Index."""

    name: str
    description: str
    category: str = ""
    tags: list[str] = field(default_factory=list)


class Runtime(ABC):
    """Helen Runtime abstract interface (HLD 3.8.1).

    This interface defines all operations that Helen Core needs from
    the runtime layer. The default implementation (HelenHermesRuntime)
    provides concrete adapters for the Hermes Agent infrastructure.
    """

    # --- Tool & Skill Management ---

    @abstractmethod
    def load_tool(self, name: str) -> Any:
        """Load a tool implementation by name."""
        ...

    @abstractmethod
    def list_skills(self) -> list[SkillMeta]:
        """Return lightweight Skill Index (Tier 1: name + description + category).

        Used by PromptBuilder to build <available_skills> section
        in System Prompt without loading full SKILL.md content.
        """
        ...

    @abstractmethod
    def load_skill(self, name: str) -> str:
        """Load a skill's full content (Tier 2: SKILL.md + linked files).

        Returns the complete SKILL.md text for injection into conversation
        history as a tool result.
        """
        ...

    # --- LLM Operations ---

    @abstractmethod
    def call_llm(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 1.0,
        max_turns: int = 1,
    ) -> Any:
        """Call the LLM API with messages and optional tool schemas.

        Args:
            messages: Conversation messages (system + history + current).
            tools: Function calling schemas.
            model: Model override (uses agent's model if None).
            temperature: Sampling temperature.
            max_turns: Maximum interaction turns.

        Returns:
            LLM response object (text, tool_calls, model).
        """
        ...

    @abstractmethod
    def cancel_llm_call(self, call_id: str) -> bool:
        """Cancel an in-progress LLM call."""
        ...

    # --- Memory Operations ---

    @abstractmethod
    def get_memory(self, key: str) -> str | None:
        """Get a memory value by exact key."""
        ...

    @abstractmethod
    def set_memory(self, key: str, value: str) -> None:
        """Set a memory value by exact key."""
        ...

    # --- Import Resolution ---

    @abstractmethod
    def resolve_import(self, path: str, from_file: str) -> Any:
        """Resolve and load an import (code, text, or data).

        Args:
            path: Import path string.
            from_file: Path of the importing file (for relative resolution).

        Returns:
            Parsed content (AST for .helen, str for text, dict/list for data).
        """
        ...

    # --- Token & History Management ---

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Estimate the token count of text."""
        ...

    @abstractmethod
    def get_conversation_history(self) -> list[Message]:
        """Get the current conversation history."""
        ...

    @abstractmethod
    def set_conversation_history(self, history: list[Message]) -> None:
        """Set/replace the conversation history."""
        ...

    # --- Memory Provider Registration (HLD 3.8.2) ---

    @abstractmethod
    def register_memory_provider(self, protocol: str, provider: Any) -> None:
        """Register a custom MemoryProvider for a URI protocol.

        Args:
            protocol: URI scheme (e.g., "file", "vector", "markdown").
            provider: A MemoryProvider instance.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete Implementation: HelenHermesRuntime (HLD 3.8.3)
# ---------------------------------------------------------------------------


class _CallHandle:
    """Tracks an in-flight LLM call for cancellation."""

    def __init__(self) -> None:
        self.cancelled = threading.Event()
        self.result: Any = None
        self.exception: Exception | None = None
        self.done = threading.Event()


class HelenHermesRuntime(Runtime):
    """Default Hermes-based implementation of the Helen Runtime (HLD 3.8.3).

    Wraps an LLMRuntime (or similar provider) and adds:
    - Cancellable LLM calls via threading.Event
    - Memory key-value store
    - Import resolution delegation
    - Conversation history management
    """

    def __init__(
        self,
        llm_runtime: Any | None = None,
        import_resolver: Any | None = None,
    ) -> None:
        self._llm_runtime = llm_runtime
        self._import_resolver = import_resolver
        self._memory: dict[str, str] = {}
        self._conversation_history: list[Message] = []
        self._active_calls: dict[str, _CallHandle] = {}
        self._memory_providers: dict[str, Any] = {}
        self._lock = threading.Lock()

    # --- Tool & Skill Management ---

    def load_tool(self, name: str) -> Any:
        """Load a tool implementation by name.

        Delegates to the Helen built tool registry. Returns a ToolSchema
        with the tool's name, description, and parameter schema.
        """
        from helen.runtime.tools import get_tool
        tool = get_tool(name)
        if tool is not None:
            return ToolSchema(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
            )
        return ToolSchema(
            name=name,
            description=f"Tool '{name}' not found in Helen built-in registry",
            parameters={"type": "object", "properties": {}},
        )

    def list_skills(self) -> list[SkillMeta]:
        """Return lightweight Skill Index by scanning skill directories.

        Reads SKILL.md frontmatter from each skill directory to extract
        name, description, category, and tags without loading full content.
        """
        skills: list[SkillMeta] = []
        skill_dirs = self._find_skill_directories()
        for skill_dir in skill_dirs:
            skill_md = os.path.join(skill_dir, "SKILL.md")
            if os.path.exists(skill_md):
                meta = self._parse_skill_frontmatter(skill_md)
                if meta:
                    skills.append(SkillMeta(
                        name=meta.get("name", os.path.basename(skill_dir)),
                        description=meta.get("description", ""),
                        category=meta.get("category", ""),
                        tags=meta.get("tags", []),
                    ))
        return skills

    def load_skill(self, name: str) -> str:
        """Load a skill's full SKILL.md content.

        Searches known skill directories for a matching SKILL.md file.

        Args:
            name: The skill name (directory name or frontmatter name).

        Returns:
            The complete SKILL.md text.

        Raises:
            FileNotFoundError: If the skill is not found.
        """
        skill_dirs = self._find_skill_directories()
        for skill_dir in skill_dirs:
            # Match by directory name
            if os.path.basename(skill_dir) == name:
                skill_md = os.path.join(skill_dir, "SKILL.md")
                if os.path.exists(skill_md):
                    with open(skill_md, encoding="utf-8") as f:
                        return f.read()
            # Also check subdirectories (e.g. mlops/inference)
            for root, dirs, files in os.walk(skill_dir):
                if os.path.basename(root) == name and "SKILL.md" in files:
                    with open(os.path.join(root, "SKILL.md"), encoding="utf-8") as f:
                        return f.read()
        raise FileNotFoundError(f"Skill '{name}' not found in any skill directory")

    # --- Internal helpers ---

    @staticmethod
    def _find_skill_directories() -> list[str]:
        """Find all directories that contain SKILL.md files.

        Uses Helen config module to get skill directories in priority order:
        1. ~/.helen/skills/ (Helen native)
        2. ~/.hermes/skills/ (Hermes fallback)
        3. ~/.hermes/hermes-agent/skills/ (Hermes agent skills)

        Skills can be nested (e.g. mlops/inference/serving-llms-vllm/SKILL.md),
        so we recursively walk the skill base directories.
        """
        from helen.runtime.config import get_skill_dirs

        candidates: list[str] = []
        for base in get_skill_dirs():
            base_str = str(base)
            if os.path.exists(base_str):
                for root, dirs, files in os.walk(base_str):
                    if "SKILL.md" in files:
                        candidates.append(root)
        return candidates

    @staticmethod
    def _parse_skill_frontmatter(path: str) -> dict[str, Any]:
        """Parse YAML frontmatter from a SKILL.md file."""
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            if not content.startswith("---"):
                return {}
            end = content.find("---", 3)
            if end < 0:
                return {}
            yaml_text = content[3:end].strip()
            result: dict[str, Any] = {}
            
            current_key = None
            current_value_lines = []
            is_folded = False
            
            def save_current():
                nonlocal current_key, current_value_lines, is_folded
                if current_key:
                    if is_folded:
                        result[current_key] = " ".join(current_value_lines).strip()
                    else:
                        result[current_key] = "\n".join(current_value_lines).strip()
                current_key = None
                current_value_lines = []
                is_folded = False
            
            for line in yaml_text.split("\n"):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                
                # Continuation line
                if line.startswith(" ") or line.startswith("\t"):
                    if current_key:
                        current_value_lines.append(stripped)
                    continue
                
                # New field
                if ":" in stripped:
                    save_current()
                    key, _, value = stripped.partition(":")
                    current_key = key.strip()
                    value = value.strip()
                    
                    if value == ">" or value == ">-" or value == ">+":
                        is_folded = True
                        current_value_lines = []
                    elif value == "" or value == "|" or value == "|-" or value == "|+":
                        current_value_lines = []
                    else:
                        current_value_lines = [value.strip('"').strip("'")]
            
            save_current()
            
            # Parse tags specially
            if "tags" in result and isinstance(result["tags"], str):
                tags_str = result["tags"]
                if tags_str.startswith("[") and tags_str.endswith("]"):
                    tags_content = tags_str[1:-1]
                    result["tags"] = [t.strip().strip("'\"") for t in tags_content.split(",") if t.strip()]
                else:
                    result["tags"] = []
            
            return result
        except (OSError, ValueError):
            return {}

    # --- LLM Operations ---

    def call_llm(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 1.0,
        max_turns: int = 1,
    ) -> Any:
        """Call the LLM API with messages and optional tool schemas.

        Supports cancellation via cancel_llm_call().

        Args:
            messages: Conversation messages.
            tools: Function calling schemas.
            model: Model override.
            temperature: Sampling temperature.
            max_turns: Maximum interaction turns.

        Returns:
            LLM response object.

        Raises:
            CancelledError: If the call was cancelled.
        """
        call_id = str(uuid.uuid4())
        handle = _CallHandle()

        with self._lock:
            self._active_calls[call_id] = handle

        try:
            if self._llm_runtime is None:
                raise RuntimeError("No LLM runtime configured")

            # Build messages list for the LLM
            llm_messages = [
                {"role": m.role, "content": m.content, **({"tool_calls": m.tool_calls} if m.tool_calls else {})}
                for m in messages
            ]

            # Check cancellation before calling
            if handle.cancelled.is_set():
                raise CancelledError(call_id)

            # Call the underlying LLM runtime
            result = self._llm_runtime.act(
                prompt=llm_messages[-1]["content"] if llm_messages else "",
                tools=tools,
                model=model,
                temperature=temperature,
                max_turns=max_turns,
            )
            handle.result = result
            return result
        except CancelledError:
            raise
        except Exception as exc:
            handle.exception = exc
            raise
        finally:
            handle.done.set()
            with self._lock:
                self._active_calls.pop(call_id, None)

    def cancel_llm_call(self, call_id: str) -> bool:
        """Cancel an in-progress LLM call.

        Args:
            call_id: The UUID returned when the call was started.

        Returns:
            True if the call was found and cancelled, False if not found
            or already completed.
        """
        with self._lock:
            handle = self._active_calls.get(call_id)
        if handle is None:
            return False
        handle.cancelled.set()
        return True

    # --- Memory Operations ---

    def get_memory(self, key: str) -> str | None:
        """Get a memory value by exact key."""
        return self._memory.get(key)

    def set_memory(self, key: str, value: str) -> None:
        """Set a memory value by exact key."""
        self._memory[key] = value

    # --- Import Resolution ---

    def resolve_import(self, path: str, from_file: str) -> Any:
        """Resolve and load an import."""
        if self._import_resolver is None:
            raise RuntimeError("No import resolver configured")
        return self._import_resolver.resolve(path, from_file)

    # --- Token & History Management ---

    def get_token_count(self, text: str) -> int:
        """Estimate the token count of text."""
        return len(text) // 4

    def get_conversation_history(self) -> list[Message]:
        """Get the current conversation history."""
        return list(self._conversation_history)

    def set_conversation_history(self, history: list[Message]) -> None:
        """Set/replace the conversation history."""
        self._conversation_history = list(history)

    # --- Memory Provider Registration ---

    def register_memory_provider(self, protocol: str, provider: Any) -> None:
        """Register a custom MemoryProvider for a URI protocol."""
        self._memory_providers[protocol] = provider


class CancelledError(Exception):
    """Raised when an LLM call is cancelled."""

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id
        super().__init__(f"LLM call {call_id} was cancelled")
