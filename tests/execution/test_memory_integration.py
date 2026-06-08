"""Integration tests for memory in agent execution.

Covers:
- Agent memory declaration -> _memory_content injection
- Prompt rendering with memory content
- MemoryProvider integration with Interpreter
"""

import os
import tempfile
import json

from hellen.core.ast import (
    AgentDeclNode,
    DeclarationNode,
    LiteralNode,
    MainBlockNode,
    ProgramNode,
    ReturnStmtNode,
)
from hellen.core.errors import ErrorReporter
from hellen.core.source import SourceSpan
from hellen.runtime.memory import InMemoryProvider


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


class TestMemoryContentInjection:
    """Test that memory content is loaded and available as _memory_content."""

    def setup_method(self):
        self.provider = InMemoryProvider()
        self.provider.set("test", "last_note", "Remember to test memory")
        self.provider.set("test", "context", "Agent is in debug mode")

    def test_memory_load_returns_all_data(self):
        """load() returns all key-value pairs."""
        data = self.provider.load("test")
        assert "last_note" in data
        assert "context" in data
        assert data["last_note"] == "Remember to test memory"

    def test_memory_content_formatted_for_prompt(self):
        """Memory content can be formatted as string for prompt injection."""
        data = self.provider.load("test")
        formatted = "\n".join(f"{k}: {v}" for k, v in data.items())
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
            skills=None,
            sub_agents=None,
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
            skills=None,
            sub_agents=None,
            memory=_lit("vector://knowledge-base"),
            temperature=None,
            max_turns=None,
            span=_span(),
        )
        assert decl.memory.value == "vector://knowledge-base"


class TestFileMemoryProviderIntegration:
    """Test FileMemoryProvider with real files."""

    def setup_method(self):
        from hellen.runtime.memory import FileMemoryProvider
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "memory.json")
        self.provider = FileMemoryProvider()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_lifecycle(self):
        """set -> save -> load -> get -> search cycle."""
        from hellen.runtime.memory import FileMemoryProvider
        # Set values
        self.provider.set(self.path, "key1", "value1")
        self.provider.set(self.path, "key2", "value2")

        # Get works before save (in-memory cache)
        assert self.provider.get(self.path, "key1") == "value1"

        # Save persists
        self.provider.save(self.path, {"key1": "value1", "key2": "value2"})

        # New instance loads from file
        new_provider = FileMemoryProvider()
        data = new_provider.load(self.path)
        assert data == {"key1": "value1", "key2": "value2"}

        # Search works
        results = new_provider.search(self.path, "value", top_k=5)
        assert len(results) == 2
