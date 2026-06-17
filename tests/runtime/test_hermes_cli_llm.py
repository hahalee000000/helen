"""Tests for HermesCLI LLM Runtime (HLD §3.6.5, §3.8.1).

Tests cover:
- Route: classification prompt construction, branch matching
- Choose: option selection prompt, option matching
- Act: LLM action execution
- Error handling: timeout, missing CLI, parse errors
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from helen.runtime.hermes_cli_llm import HermesCLILLMRuntime
from helen.runtime.llm_runtime import LLMResponse


class TestHermesCLILLMRuntimeRoute:
    """Test route() method - LLM classification."""

    def setup_method(self) -> None:
        self.runtime = HermesCLILLMRuntime(hermes_path="hermes")

    def test_route_returns_matching_branch(self) -> None:
        with patch.object(self.runtime, "_ask", return_value="urgent"):
            result = self.runtime.route(
                "Classify this email",
                ["urgent", "meeting", "spam"],
            )
        assert result == "urgent"

    def test_route_case_insensitive_match(self) -> None:
        with patch.object(self.runtime, "_ask", return_value="URGENT"):
            result = self.runtime.route(
                "Classify this email",
                ["urgent", "meeting", "spam"],
            )
        assert result == "urgent"

    def test_route_returns_first_branch_on_no_match(self) -> None:
        with patch.object(self.runtime, "_ask", return_value="unknown"):
            result = self.runtime.route(
                "Classify this email",
                ["urgent", "meeting", "spam"],
            )
        assert result == "urgent"

    def test_route_returns_none_on_ask_failure(self) -> None:
        with patch.object(self.runtime, "_ask", return_value=None):
            result = self.runtime.route("Test", ["a", "b"])
        assert result is None

    def test_route_returns_none_for_empty_branches(self) -> None:
        with patch.object(self.runtime, "_ask", return_value="x"):
            result = self.runtime.route("Test", [])
        assert result is None

    def test_route_passes_context(self) -> None:
        captured: dict[str, str] = {}

        def capture_ask(prompt: str) -> str:
            captured["prompt"] = prompt
            return "a"

        with patch.object(self.runtime, "_ask", side_effect=capture_ask):
            self.runtime.route("Classify", ["a", "b"], context="Previous: urgent")

        assert "Previous: urgent" in captured["prompt"]

    def test_route_prompt_contains_branches(self) -> None:
        captured: dict[str, str] = {}

        def capture_ask(prompt: str) -> str:
            captured["prompt"] = prompt
            return "a"

        with patch.object(self.runtime, "_ask", side_effect=capture_ask):
            self.runtime.route("Sort tickets", ["bug", "feature", "docs"])

        assert "bug" in captured["prompt"]
        assert "feature" in captured["prompt"]
        assert "docs" in captured["prompt"]


class TestHermesCLILLMRuntimeAct:
    """Test act() method - LLM autonomous action."""

    def setup_method(self) -> None:
        self.runtime = HermesCLILLMRuntime(hermes_path="hermes")

    def test_act_returns_llm_response(self) -> None:
        with patch.object(self.runtime, "_ask", return_value="Hello world"):
            response = self.runtime.act("Say hello")
        assert isinstance(response, LLMResponse)
        assert response.text == "Hello world"

    def test_act_with_model_override(self) -> None:
        with patch.object(self.runtime, "_ask", return_value="Hi"):
            response = self.runtime.act("Hi", model="gpt-4")
        assert response.model == "gpt-4"

    def test_act_uses_default_model(self) -> None:
        runtime = HermesCLILLMRuntime(hermes_path="hermes", default_model="claude-3")
        with patch.object(runtime, "_ask", return_value="Hi"):
            response = runtime.act("Hi")
        assert response.model == "claude-3"

    def test_act_empty_response_on_ask_failure(self) -> None:
        with patch.object(self.runtime, "_ask", return_value=None):
            response = self.runtime.act("Test")
        assert response.text == ""

    def test_act_accepts_tools_param(self) -> None:
        """act() should not crash when tools are provided."""
        with patch.object(self.runtime, "_ask", return_value="OK"):
            response = self.runtime.act(
                "Search for something",
                tools=[{"name": "search", "description": "Search the web"}],
            )
        assert isinstance(response, LLMResponse)


class TestHermesCLILLMRuntimeAsk:
    """Test _ask() method - CLI interaction."""

    def test_ask_returns_text_on_success(self) -> None:
        runtime = HermesCLILLMRuntime(hermes_path="hermes")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Hello"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = runtime._ask("Say hello")

        assert result == "Hello"
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "hermes" in cmd[0]
        assert "-z" in cmd
        assert "Say hello" in cmd

    def test_ask_returns_none_on_cli_error(self) -> None:
        runtime = HermesCLILLMRuntime(hermes_path="hermes")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: something went wrong"

        with patch("subprocess.run", return_value=mock_result):
            result = runtime._ask("test")

        assert result is None
        assert runtime.last_error is not None

    def test_ask_returns_none_on_timeout(self) -> None:
        runtime = HermesCLILLMRuntime(hermes_path="hermes", timeout=1)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 1)):
            result = runtime._ask("test")

        assert result is None
        assert "timed out" in runtime.last_error

    def test_ask_returns_none_on_missing_cli(self) -> None:
        runtime = HermesCLILLMRuntime(hermes_path="/nonexistent/hermes")

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = runtime._ask("test")

        assert result is None
        assert "not found" in runtime.last_error

    def test_ask_passes_model_flag(self) -> None:
        runtime = HermesCLILLMRuntime(hermes_path="hermes")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "OK"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runtime._ask("test", model="gpt-4")

        cmd = mock_run.call_args[0][0]
        assert "-m" in cmd
        assert "gpt-4" in cmd

    def test_ask_returns_plain_text(self) -> None:
        """hermes -z returns plain text, not JSON."""
        runtime = HermesCLILLMRuntime(hermes_path="hermes")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Plain text response"

        with patch("subprocess.run", return_value=mock_result):
            result = runtime._ask("test")

        assert result == "Plain text response"

    def test_ask_fallback_strips_whitespace(self) -> None:
        runtime = HermesCLILLMRuntime(hermes_path="hermes")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  Hello world  \n"

        with patch("subprocess.run", return_value=mock_result):
            result = runtime._ask("test")

        assert result == "Hello world"


class TestHermesCLILLMRuntimeInterface:
    """Verify HermesCLILLMRuntime implements LLMRuntime."""

    def test_is_subclass_of_llm_runtime(self) -> None:
        from helen.runtime.llm_runtime import LLMRuntime
        assert issubclass(HermesCLILLMRuntime, LLMRuntime)

    def test_has_required_methods(self) -> None:
        runtime = HermesCLILLMRuntime()
        assert hasattr(runtime, "route")
        assert hasattr(runtime, "act")
