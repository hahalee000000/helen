"""Tests for helen.runtime.structured — StructuredOutput schema generation and parsing."""

from helen.runtime.structured import StructuredOutput


class TestRouteSchema:
    def test_build_route_schema_has_enum(self):
        schema = StructuredOutput.build_route_schema(["query", "command", "chat"])
        branch_enum = schema["function"]["parameters"]["properties"]["branch"]["enum"]
        assert branch_enum == ["query", "command", "chat"]

    def test_build_route_schema_required_branch(self):
        schema = StructuredOutput.build_route_schema(["a", "b"])
        assert schema["function"]["parameters"]["required"] == ["branch"]

    def test_build_route_schema_function_name(self):
        schema = StructuredOutput.build_route_schema(["a"])
        assert schema["function"]["name"] == "classify"


class TestRouteParsing:
    def test_parse_valid_branch(self):
        response = {"branch": "query"}
        result = StructuredOutput.parse_route_response(response, ["query", "command"])
        assert result == "query"

    def test_parse_invalid_branch(self):
        response = {"branch": "unknown"}
        result = StructuredOutput.parse_route_response(response, ["query", "command"])
        assert result is None

    def test_parse_none_response(self):
        result = StructuredOutput.parse_route_response(None, ["query"])
        assert result is None

    def test_parse_nested_arguments(self):
        response = {"arguments": {"branch": "command", "confidence": 0.9}}
        result = StructuredOutput.parse_route_response(response, ["query", "command"])
        assert result == "command"

    def test_parse_missing_branch_key(self):
        response = {"confidence": 0.9}
        result = StructuredOutput.parse_route_response(response, ["query"])
        assert result is None


class TestPromptBuilding:
    def test_build_route_prompt(self):
        prompt = StructuredOutput.build_route_prompt("classify this", ["a", "b"])
        assert "classify this" in prompt
        assert "a" in prompt
        assert "b" in prompt
        assert "classify" in prompt.lower()

    def test_build_route_prompt_with_context(self):
        prompt = StructuredOutput.build_route_prompt("desc", ["a"], context="user asked X")
        assert "user asked X" in prompt
