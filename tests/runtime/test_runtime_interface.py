"""Tests for helen.runtime — Runtime ABC interface completeness (HLD 3.8.1).

Covers:
- Runtime ABC has all required abstract methods
- Mock Runtime implementation works
- Method signatures match HLD spec
"""

from abc import ABC
from helen.runtime import Runtime, Message, SkillMeta, ToolSchema


class TestRuntimeABC:
    """Test Runtime abstract base class completeness."""

    def test_runtime_is_abstract(self):
        """Runtime is an abstract base class."""
        assert issubclass(Runtime, ABC)

    def test_cannot_instantiate_runtime(self):
        """Runtime cannot be instantiated directly."""
        try:
            Runtime()
            assert False, "Should not be able to instantiate ABC"
        except TypeError:
            pass

    def test_has_required_abstract_methods(self):
        """Runtime defines all required abstract methods (HLD 3.8.1)."""
        required = [
            "load_tool",
            "list_skills",
            "load_skill",
            "call_llm",
            "cancel_llm_call",
            "get_memory",
            "set_memory",
            "resolve_import",
            "get_token_count",
            "get_conversation_history",
            "set_conversation_history",
            "register_memory_provider",
        ]
        for method_name in required:
            assert hasattr(Runtime, method_name), f"Missing: {method_name}"
            method = getattr(Runtime, method_name)
            assert getattr(method, "__isabstractmethod__", False), (
                f"{method_name} should be abstract"
            )


class TestRuntimeDataclasses:
    """Test Runtime dataclass types."""

    def test_message_fields(self):
        """Message has role, content, tool_calls, tool_call_id."""
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.tool_calls == []
        assert msg.tool_call_id is None

    def test_skill_meta_fields(self):
        """SkillMeta has name, description, category."""
        skill = SkillMeta(name="test", description="desc")
        assert skill.name == "test"
        assert skill.description == "desc"
        assert skill.category == ""

    def test_tool_schema_fields(self):
        """ToolSchema has name, description, parameters."""
        tool = ToolSchema(
            name="search",
            description="Search the web",
            parameters={"type": "object"},
        )
        assert tool.name == "search"
        assert tool.description == "Search the web"
        assert tool.parameters == {"type": "object"}


class TestMockRuntime:
    """Test that a concrete implementation of Runtime works."""

    def test_mock_runtime_implements_all(self):
        """A mock implementation satisfies the ABC."""
        from helen.runtime import Runtime

        class MockRuntime(Runtime):
            def load_tool(self, name): return None
            def list_skills(self): return []
            def load_skill(self, name): return ""
            def call_llm(self, messages, tools=None, model=None, temperature=1.0, max_turns=1): return None
            def cancel_llm_call(self, call_id): return False
            def get_memory(self, key): return None
            def set_memory(self, key, value): pass
            def resolve_import(self, path, from_file): return None
            def get_token_count(self, text): return 0
            def get_conversation_history(self): return []
            def set_conversation_history(self, history): pass
            def register_memory_provider(self, protocol, provider): pass

        # Should not raise
        runtime = MockRuntime()
        assert runtime is not None
        assert isinstance(runtime, Runtime)
