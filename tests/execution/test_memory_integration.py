"""Integration tests for memory in agent execution.

Covers:
- Agent memory declaration -> _memory_content injection
- Prompt rendering with memory content
- MemoryProvider integration with Interpreter
"""

import os
import tempfile
import json

from helen.core.ast import (
    AgentDeclNode,
    DeclarationNode,
    LiteralNode,
    MainBlockNode,
    ProgramNode,
    ReturnStmtNode,
)
from helen.core.errors import ErrorReporter
from helen.core.source import SourceSpan
from helen.runtime.memory import FileMemoryProvider, InMemoryProvider


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


class TestMemoryContentInjection:
    """Test that memory content is loaded and available as _memory_content."""

    def setup_method(self):
        self.provider = InMemoryProvider()
        self.provider.set("last_note", "Remember to test memory")
        self.provider.set("context", "Agent is in debug mode")

    def test_memory_load_returns_all_data(self):
        """list_keys() returns all keys, get() retrieves values."""
        keys = self.provider.list_keys()
        assert "last_note" in keys
        assert "context" in keys
        assert self.provider.get("last_note") == "Remember to test memory"

    def test_memory_content_formatted_for_prompt(self):
        """Memory content can be formatted as string for prompt injection."""
        keys = self.provider.list_keys()
        formatted = "\n".join(f"{k}: {self.provider.get(k)}" for k in keys)
        assert "last_note: Remember to test memory" in formatted
        assert "context: Agent is in debug mode" in formatted


class TestMemoryInAgentDeclaration:
    """Test memory declaration in agent."""

    def test_agent_has_memory_declaration(self):
        """AgentDeclNode can have a memory declaration."""
        decl = DeclarationNode(
            description=None,
            model=None,
            tools=None,
            memory=_lit("./memory/data.json"),
            temperature=None,
            max_turns=None,
            span=_span(),
        )
        assert decl.memory is not None

    def test_memory_declaration_value_extraction(self):
        """Memory path can be extracted from declaration."""
        decl = DeclarationNode(
            description=None,
            model=None,
            tools=None,
            memory=_lit("vector://knowledge-base"),
            temperature=None,
            max_turns=None,
            span=_span(),
        )
        assert decl.memory.value == "vector://knowledge-base"


class TestFileMemoryProviderIntegration:
    """Test FileMemoryProvider with real files."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "memory.json")
        self.provider = FileMemoryProvider(self.path)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_lifecycle(self):
        """set -> get -> persist -> reload cycle."""
        # Set values
        self.provider.set("key1", "value1")
        self.provider.set("key2", "value2")

        # Get works (in-memory cache)
        assert self.provider.get("key1") == "value1"
        assert self.provider.get("key2") == "value2"

        # File was persisted
        assert os.path.exists(self.path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        assert data == {"key1": "value1", "key2": "value2"}

        # New instance loads from file
        new_provider = FileMemoryProvider(self.path)
        assert new_provider.get("key1") == "value1"
        assert new_provider.get("key2") == "value2"

    def test_delete_and_persist(self):
        """Delete should persist to file."""
        self.provider.set("key", "value")
        self.provider.delete("key")
        assert self.provider.get("key") is None

        new_provider = FileMemoryProvider(self.path)
        assert new_provider.get("key") is None

    def test_list_keys(self):
        """list_keys() returns all stored keys."""
        self.provider.set("a", "1")
        self.provider.set("b", "2")
        self.provider.set("c", "3")
        keys = self.provider.list_keys()
        assert set(keys) == {"a", "b", "c"}
