"""Tests for helen.interpreter — llm act statement execution."""

from helen.core.ast import (
    LlmActStmtNode,
    LiteralNode,
    ProgramNode,
)
from helen.core.errors import ErrorReporter
from helen.core.source import SourceSpan
from helen.interpreter.exceptions import TimeoutError
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import LLMResponse, MockLLMRuntime


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _run(stmt, llm_runtime=None) -> tuple:
    prog = ProgramNode(statements=[stmt], span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors, llm_runtime=llm_runtime)
    result = interp.interpret(prog)
    return result, errors


class TestLlmActExecution:
    def test_act_returns_text(self):
        """llm act greet() "say hello" → returns LLM response text."""
        runtime = MockLLMRuntime(act_return="Hello, world!")
        stmt = LlmActStmtNode(
            target="greet",
            arguments={},
            description="say hello",
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result == "Hello, world!"
        assert not errors.has_errors

    def test_act_with_arguments(self):
        """llm act greet(name="Alice") "personalized greeting" → returns response."""
        from helen.core.ast import LiteralNode

        runtime = MockLLMRuntime(act_return="Hi Alice!")
        stmt = LlmActStmtNode(
            target="greet",
            arguments={"name": LiteralNode(value="Alice", span=_span())},
            description="personalized greeting",
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result == "Hi Alice!"
        assert not errors.has_errors
        # Check prompt was built correctly
        assert "greet" in runtime.act_history[0]["prompt"]
        assert "Alice" in runtime.act_history[0]["prompt"]

    def test_act_on_llm_exception(self):
        """LLM raises exception → returns None."""
        runtime = MockLLMRuntime(act_fail=TimeoutError("timeout"))
        stmt = LlmActStmtNode(
            target="greet",
            arguments={},
            description="say hello",
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        assert result is None
        assert not errors.has_errors

    def test_act_returns_tool_calls(self):
        """LLM act can return tool call requests."""
        tool_call = {"name": "search", "arguments": {"query": "hello"}}
        response = LLMResponse(text=None, tool_calls=[tool_call], model="gpt-4")
        runtime = MockLLMRuntime(act_return=response)
        stmt = LlmActStmtNode(
            target="search_web",
            arguments={},
            description="search",
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        # Result is text (None), but tool_calls are in the response
        assert result is None
        assert not errors.has_errors

    def test_act_empty_response_on_none(self):
        """act_return=None returns empty string (MockLLMRuntime behavior)."""
        runtime = MockLLMRuntime(act_return=None)
        stmt = LlmActStmtNode(
            target="test",
            arguments={},
            description="test",
            span=_span(),
        )
        result, errors = _run(stmt, llm_runtime=runtime)
        # MockLLMRuntime returns LLMResponse(text="") for None
        assert result == ""
        assert not errors.has_errors

    def test_act_passes_load_skill_tool(self):
        """act() is called with tools containing load_skill schema (HLD 3.6.5)."""
        runtime = MockLLMRuntime(act_return="ok")
        stmt = LlmActStmtNode(
            target="test",
            arguments={},
            description="test",
            span=_span(),
        )
        _run(stmt, llm_runtime=runtime)
        tools = runtime.act_history[0]["tools"]
        assert len(tools) >= 1
        # Find load_skill in tools list (it may not be first)
        load_skill_tool = next((t for t in tools if t["function"]["name"] == "load_skill"), None)
        assert load_skill_tool is not None, "load_skill tool not found in tools list"
        assert load_skill_tool["function"]["parameters"]["required"] == ["name"]

    def test_act_passes_default_settings(self):
        """act() uses default temperature=1.0, max_turns=2 when tools are present."""
        runtime = MockLLMRuntime(act_return="ok")
        stmt = LlmActStmtNode(
            target="test",
            arguments={},
            description="test",
            span=_span(),
        )
        _run(stmt, llm_runtime=runtime)
        history = runtime.act_history[0]
        assert history["temperature"] == 1.0
        assert history["max_turns"] == 3  # Bumped from 1 to 3 when tools are present
        assert history["model"] is None  # No agent context

    def test_get_agent_setting_defaults_without_agent(self):
        """_get_agent_setting returns defaults when _current_agent is None."""
        from helen.interpreter.interpreter import Interpreter
        interp = Interpreter()
        assert interp._get_agent_setting("model") is None
        assert interp._get_agent_setting("temperature", 1.0) == 1.0
        assert interp._get_agent_setting("max-turns", 1) == 1

    def test_load_skill_tool_schema(self):
        """_load_skill_tool_schema returns correct function calling schema."""
        schema = Interpreter._load_skill_tool_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "load_skill"
        assert schema["function"]["parameters"]["required"] == ["name"]
        props = schema["function"]["parameters"]["properties"]
        assert "name" in props
        assert props["name"]["type"] == "string"
