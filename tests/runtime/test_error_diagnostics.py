"""Tests for error diagnostics module.

Tests the structured error classification, suggestion generation,
and data flow tracing functionality.
"""

import pytest
from helen.runtime.error_diagnostics import (
    ERROR_SUGGESTION_REGISTRY,
    generate_suggestion,
    build_data_flow,
)


class TestErrorSuggestionRegistry:
    """Test the error suggestion registry."""

    def test_all_exception_types_registered(self):
        """All 10 Helen exception types should have suggestions."""
        expected_types = {
            "AnyError",
            "LLMError",
            "TimeoutError",
            "ModelError",
            "PromptTooLongError",
            "AgentError",
            "LLMOutputContractError",  # v1.40
            "ToolError",
            "RuntimeError",
            "AssertionError",
            "AggregateError",
        }
        assert set(ERROR_SUGGESTION_REGISTRY.keys()) == expected_types

    def test_all_entries_have_required_fields(self):
        """Each registry entry must have category and template."""
        for error_type, entry in ERROR_SUGGESTION_REGISTRY.items():
            assert "category" in entry, f"{error_type} missing 'category'"
            assert "template" in entry, f"{error_type} missing 'template'"
            assert isinstance(entry["category"], str)
            assert isinstance(entry["template"], str)
            assert len(entry["category"]) > 0
            assert len(entry["template"]) > 0


class TestGenerateSuggestion:
    """Test suggestion generation."""

    def test_runtime_error_basic(self):
        """Basic RuntimeError should get generic suggestion."""
        category, suggestion = generate_suggestion("RuntimeError", "something went wrong", {})
        assert category == "RuntimeGenericError"
        assert "something went wrong" in suggestion
        assert "变量类型" in suggestion or "边界条件" in suggestion

    def test_runtime_error_division_by_zero(self):
        """Division by zero should trigger specific rule."""
        category, suggestion = generate_suggestion("RuntimeError", "division by zero", {})
        assert category == "RuntimeGenericError"
        assert "除零" in suggestion
        assert "分母" in suggestion

    def test_runtime_error_type_mismatch(self):
        """Type mismatch should trigger specific rule."""
        category, suggestion = generate_suggestion("RuntimeError", "expected int, got str", {})
        assert category == "RuntimeGenericError"
        assert "类型不匹配" in suggestion

    def test_runtime_error_undefined_variable(self):
        """Undefined variable should trigger specific rule."""
        category, suggestion = generate_suggestion("RuntimeError", "undefined variable 'foo'", {})
        assert category == "RuntimeGenericError"
        assert "未定义变量" in suggestion

    def test_timeout_error(self):
        """TimeoutError should suggest timeout-related fixes."""
        category, suggestion = generate_suggestion("TimeoutError", "LLM call timed out", {})
        assert category == "LLMTimeout"
        assert "timeout" in suggestion.lower() or "超时" in suggestion

    def test_prompt_too_long_with_context(self):
        """PromptTooLongError should use tokens_used and tokens_limit."""
        context = {"tokens_used": 5000, "tokens_limit": 4096}
        category, suggestion = generate_suggestion("PromptTooLongError", "prompt too long", context)
        assert category == "LLMContextOverflow"
        assert "5000" in suggestion or "4096" in suggestion
        assert "compress_context" in suggestion or "clear_context" in suggestion

    def test_agent_error_with_context(self):
        """AgentError should include agent_name and cause."""
        context = {"agent_name": "Reviewer", "cause": "LLM timeout"}
        category, suggestion = generate_suggestion("AgentError", "Agent failed", context)
        assert category == "AgentCallFailed"
        assert "Reviewer" in suggestion
        assert "LLM timeout" in suggestion

    def test_unknown_error_type(self):
        """Unknown error type should get fallback suggestion."""
        category, suggestion = generate_suggestion("UnknownError", "something", {})
        assert category == "UnknownError"
        assert "UnknownError" in suggestion

    def test_runtime_error_case_insensitive(self):
        """Rule matching should be case-insensitive."""
        category, suggestion = generate_suggestion("RuntimeError", "DIVISION BY ZERO", {})
        assert category == "RuntimeGenericError"
        assert "除零" in suggestion


class TestBuildDataFlow:
    """Test data flow tracing."""

    def test_empty_context(self):
        """Empty scope and call_stack should return empty flow."""
        flow = build_data_flow({}, [])
        assert flow == []

    def test_message_in_scope(self):
        """Message objects in scope should be traced."""
        class MockMessage:
            def __init__(self):
                self.uuid = "msg-123"
                self.role = "assistant"
                self.content = "test"
                self.agent_name = "Reviewer"

        scope = {"result": MockMessage()}
        flow = build_data_flow(scope, [])

        assert len(flow) == 1
        assert flow[0]["variable"] == "result"
        assert flow[0]["source"] == "msg-123"
        assert flow[0]["via"] == "Reviewer"

    def test_agent_in_call_stack(self):
        """Agent calls in call_stack should be traced."""
        call_stack = [
            {"function": "agent:Coder", "location": "test.helen:10"},
            {"function": "main", "location": "test.helen:1"},
        ]
        flow = build_data_flow({}, call_stack)

        assert len(flow) == 1
        assert flow[0]["source"] == "agent_output"
        assert flow[0]["via"] == "agent:Coder"
        assert flow[0]["origin"] == "test.helen:10"

    def test_multiple_messages_and_agents(self):
        """Should trace multiple messages and agent calls."""
        class MockMessage:
            def __init__(self, uuid, agent):
                self.uuid = uuid
                self.role = "assistant"
                self.content = "test"
                self.agent_name = agent

        scope = {
            "msg1": MockMessage("msg-1", "Coder"),
            "msg2": MockMessage("msg-2", "Reviewer"),
        }
        call_stack = [
            {"function": "agent:Analyzer", "location": "test.helen:20"},
        ]

        flow = build_data_flow(scope, call_stack)

        assert len(flow) == 3  # 2 messages + 1 agent
        # Check that all expected entries are present
        variables = {f.get("variable") for f in flow}
        assert "msg1" in variables
        assert "msg2" in variables
        assert any(f.get("via") == "agent:Analyzer" for f in flow)


class TestDataFlowEdgeCases:
    """Test edge cases in data flow tracing."""

    def test_message_without_uuid(self):
        """Message without uuid should not be traced."""
        class MockMessage:
            def __init__(self):
                self.role = "assistant"
                self.content = "test"
                # No uuid attribute

        scope = {"result": MockMessage()}
        flow = build_data_flow(scope, [])

        # Should not trace messages without uuid
        assert len(flow) == 0

    def test_non_message_objects(self):
        """Non-message objects should not be traced."""
        scope = {"x": 42, "name": "test", "data": [1, 2, 3]}
        flow = build_data_flow(scope, [])

        assert len(flow) == 0

    def test_call_stack_without_agents(self):
        """Call stack without agent calls should not add agent flows."""
        call_stack = [
            {"function": "main", "location": "test.helen:1"},
            {"function": "helper", "location": "test.helen:5"},
        ]
        flow = build_data_flow({}, call_stack)

        assert len(flow) == 0


class TestIntegration:
    """Integration tests for error diagnostics."""

    def test_full_diagnostic_flow(self):
        """Test complete diagnostic generation flow."""
        from helen.runtime.error_diagnostics import generate_diagnostics

        # Simulate a RuntimeError with context
        diagnostics = generate_diagnostics(
            error_type="RuntimeError",
            message="division by zero",
            scope={},
            call_stack=[],
            exception_context={}
        )

        assert "diagnostic_category" in diagnostics
        assert "suggestion" in diagnostics
        assert "data_flow" in diagnostics
        assert diagnostics["diagnostic_category"] == "RuntimeGenericError"
        assert "除零" in diagnostics["suggestion"]

    def test_diagnostic_with_data_flow(self):
        """Test diagnostic generation with data flow."""
        from helen.runtime.error_diagnostics import generate_diagnostics

        class MockMessage:
            def __init__(self):
                self.uuid = "msg-abc"
                self.role = "assistant"
                self.content = "test"
                self.agent_name = "Coder"

        diagnostics = generate_diagnostics(
            error_type="LLMError",
            message="LLM call failed",
            scope={"result": MockMessage()},
            call_stack=[{"function": "agent:Reviewer", "location": "test.helen:10"}],
            exception_context={}
        )

        assert len(diagnostics["data_flow"]) == 2  # 1 message + 1 agent
        assert any(f.get("source") == "msg-abc" for f in diagnostics["data_flow"])
        assert any(f.get("via") == "agent:Reviewer" for f in diagnostics["data_flow"])
