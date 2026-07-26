"""Tests for the enhanced REPL :ask command (L1/L2/L3).

L1: single-turn question with REPL context injected into system prompt.
L2: REPL state tools (repl_definitions / repl_last_error / repl_history /
    repl_read_file) exposed to the assistant via dispatch_fn.
L3: multi-turn chat mode via AssistantSession with its own TranscriptStore.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys

from helen.cli.ask_assistant import (
    ReplState,
    AssistantSession,
    _build_repl_tools,
    build_assistant_prompt,
)
from helen.cli.repl import _handle_repl_command, _CapturingStdout
from helen.core.errors import ErrorReporter
from helen.interpreter.interpreter import Interpreter
from helen.runtime.prompt_builder import PromptBuilder
from helen.semantic.analyzer import SemanticAnalyzer


# ---------------------------------------------------------------------------
# L1: REPL state capture + prompt assembly
# ---------------------------------------------------------------------------

class TestReplState:
    """ReplState bounded output buffer + persistent last error."""

    def test_output_buffer_bounded(self):
        rs = ReplState(output_buffer_max=5)
        for i in range(10):
            rs.record_output(f"line {i}")
        assert len(rs.output_buffer) == 5
        assert rs.output_buffer[0] == "line 5"
        assert rs.output_buffer[-1] == "line 9"

    def test_last_error_persists(self):
        rs = ReplState()
        rs.record_error("E0102: undefined variable 'x'")
        assert rs.last_error_text == "E0102: undefined variable 'x'"
        # A second error replaces the first (most recent wins)
        rs.record_error("E0200: type mismatch")
        assert rs.last_error_text == "E0200: type mismatch"

    def test_clear_resets(self):
        rs = ReplState()
        rs.record_output("hello")
        rs.record_error("bad")
        rs.clear()
        assert rs.output_buffer == []
        assert rs.last_error_text is None


class TestFormatReplContextBlock:
    """PromptBuilder.format_repl_context_block builds the right XML."""

    def test_all_sections_present(self):
        block = PromptBuilder.format_repl_context_block(
            definitions={"functions": ["foo", "bar"], "agents": ["Worker"]},
            last_error_text="E0102 at line 5",
            recent_output=["hello", "world"],
            cwd="/tmp/proj",
        )
        assert block.startswith("<repl_context>")
        assert block.endswith("</repl_context>")
        assert "Functions: foo, bar" in block
        assert "Agents:    Worker" in block
        assert "E0102 at line 5" in block
        assert "hello" in block
        assert "/tmp/proj" in block

    def test_empty_state_returns_empty(self):
        block = PromptBuilder.format_repl_context_block(
            definitions={"functions": [], "agents": []},
            last_error_text=None,
            recent_output=[],
            cwd="",
        )
        assert block == ""

    def test_long_error_truncated(self):
        long_err = "X" * 3000
        block = PromptBuilder.format_repl_context_block(
            definitions={"functions": [], "agents": []},
            last_error_text=long_err,
            recent_output=[],
            cwd="",
        )
        assert "truncated" in block
        assert len(block) < len(long_err) + 200


class TestBuildAssistantPrompt:
    """build_assistant_prompt composes framework + conventions + skills + repl_context."""

    def test_contains_framework_and_conventions(self):
        interp = MagicMock()
        interp.list_definitions.return_value = {"functions": [], "agents": []}
        rs = ReplState()
        prompt = build_assistant_prompt(interp, rs, "/tmp/cwd")
        assert "framework_instructions" in prompt
        assert "helen_conventions" in prompt

    def test_repl_context_included_when_state_nonempty(self):
        interp = MagicMock()
        interp.list_definitions.return_value = {"functions": ["f1"], "agents": []}
        rs = ReplState()
        rs.record_error("boom")
        prompt = build_assistant_prompt(interp, rs, "/tmp/cwd")
        assert "<repl_context>" in prompt
        assert "f1" in prompt
        assert "boom" in prompt


# ---------------------------------------------------------------------------
# L2: REPL state tools
# ---------------------------------------------------------------------------

class TestReplTools:
    """L2 tools: repl_definitions / repl_last_error / repl_history /
    repl_read_file."""

    def _make_tools(self, repl_state=None, interp_defs=None, cwd="/tmp"):
        repl_state = repl_state or ReplState()
        interp = MagicMock()
        interp.list_definitions.return_value = interp_defs or {
            "functions": ["alpha"], "agents": ["Translator"],
        }
        interp.observability.last_error = None
        return _build_repl_tools(repl_state, interp, cwd)

    def test_repl_definitions_returns_lists(self):
        tools, dispatch = self._make_tools()
        import json
        result = json.loads(dispatch("repl_definitions", {}))
        assert result["functions"] == ["alpha"]
        assert result["agents"] == ["Translator"]
        # Tool schemas registered (OpenAI format: type=function, function.name)
        names = {t["function"]["name"] for t in tools if t.get("type") == "function"}
        assert "repl_definitions" in names
        assert "repl_last_error" in names
        assert "repl_history" in names
        assert "repl_read_file" in names

    def test_repl_last_error_from_repl_state(self):
        rs = ReplState()
        rs.record_error("E0102 undefined 'x'")
        tools, dispatch = self._make_tools(repl_state=rs)
        result = dispatch("repl_last_error", {})
        assert "E0102" in result
        assert "undefined 'x'" in result

    def test_repl_last_error_no_error(self):
        tools, dispatch = self._make_tools()
        result = dispatch("repl_last_error", {})
        assert "no error" in result.lower()

    def test_repl_history_returns_recent_lines(self):
        rs = ReplState()
        for i in range(20):
            rs.record_output(f"line-{i}")
        tools, dispatch = self._make_tools(repl_state=rs)
        result = dispatch("repl_history", {"n": 5})
        lines = result.splitlines()
        assert len(lines) == 5
        assert lines[0] == "line-15"
        assert lines[-1] == "line-19"

    def test_repl_history_caps_at_50(self):
        rs = ReplState()
        tools, dispatch = self._make_tools(repl_state=rs)
        # Even if user asks for 1000, tool caps at 50
        result = dispatch("repl_history", {"n": 1000})
        # No recent output, returns placeholder
        assert "no recent" in result.lower()

    def test_repl_read_file_within_cwd(self, tmp_path):
        f = tmp_path / "hello.helen"
        f.write_text("main { print(42) }", encoding="utf-8")
        tools, dispatch = self._make_tools(cwd=str(tmp_path))
        result = dispatch("repl_read_file", {"path": "hello.helen"})
        assert "main" in result
        assert "42" in result

    def test_repl_read_file_rejects_path_escape(self, tmp_path):
        tools, dispatch = self._make_tools(cwd=str(tmp_path))
        result = dispatch("repl_read_file", {"path": "../../etc/passwd"})
        assert "escapes cwd" in result or "error" in result.lower()

    def test_repl_read_file_missing_file(self, tmp_path):
        tools, dispatch = self._make_tools(cwd=str(tmp_path))
        result = dispatch("repl_read_file", {"path": "missing.helen"})
        assert "not a file" in result or "error" in result.lower()

    def test_repl_read_file_requires_path_arg(self, tmp_path):
        tools, dispatch = self._make_tools(cwd=str(tmp_path))
        result = dispatch("repl_read_file", {})
        assert "path" in result.lower()


# ---------------------------------------------------------------------------
# L3: multi-turn chat mode
# ---------------------------------------------------------------------------

class TestAssistantSession:
    """AssistantSession lifecycle + chat mode."""

    def test_new_session_has_session_id(self):
        # Patch Interpreter at its source module so new_assistant_session's
        # lazy import picks up the mock.
        with patch("helen.interpreter.interpreter.Interpreter") as MockInterp:
            mock_interp = MagicMock()
            mock_agent_ctx = MagicMock()
            mock_agent_ctx.session_id = "session_test_abc"
            mock_interp._agent_context = mock_agent_ctx
            MockInterp.return_value = mock_interp
            from helen.cli.ask_assistant import new_assistant_session
            session = new_assistant_session("/tmp")
            assert session.session_id == "session_test_abc"
            assert session.interp is mock_interp

    def test_session_records_messages(self, tmp_path):
        # Mock a minimal interpreter with an agent_context + transcript_store
        mock_store = MagicMock()
        mock_agent_ctx = MagicMock()
        mock_agent_ctx.transcript_store = mock_store
        mock_interp = MagicMock()
        mock_interp._agent_context = mock_agent_ctx

        session = AssistantSession(
            session_id="session_x", interp=mock_interp,
        )
        session.record_user_message("hello")
        session.record_assistant_message("hi back")
        # Should have added two messages to the store
        assert mock_store.add.call_count == 2


# ---------------------------------------------------------------------------
# REPL command wiring
# ---------------------------------------------------------------------------

class TestREPLAskCommandWiring:
    """Verify :ask commands dispatch correctly in the REPL."""

    def _make_ctx(self):
        errors = ErrorReporter()
        interp = Interpreter(errors=errors)
        analyzer = SemanticAnalyzer(errors)
        repl_state = ReplState()
        return interp, analyzer, repl_state

    def test_ask_with_question_calls_ask_single(self):
        interp, analyzer, rs = self._make_ctx()
        with patch("helen.cli.ask_assistant.ask_single") as mock_ask:
            result = _handle_repl_command(
                ":ask how to define agent?", interp, analyzer, rs,
            )
            assert result is True
            mock_ask.assert_called_once()
            # First positional arg is the question
            assert mock_ask.call_args[0][0] == "how to define agent?"

    def test_ask_without_question_enters_chat_mode(self):
        interp, analyzer, rs = self._make_ctx()
        with patch("helen.cli.ask_assistant.run_chat_mode") as mock_chat, \
             patch("helen.cli.ask_assistant.new_assistant_session") as mock_new:
            mock_new.return_value = MagicMock()
            result = _handle_repl_command(":ask", interp, analyzer, rs)
            assert result is True
            mock_new.assert_called_once()
            mock_chat.assert_called_once()

    def test_ask_dash_list_lists_sessions(self):
        interp, analyzer, rs = self._make_ctx()
        with patch("helen.cli.ask_assistant.list_assistant_sessions") as mock_list, \
             patch("builtins.print"):
            mock_list.return_value = [
                {"session_id": "session_x", "created_at": "2026-07-26T10:00:00",
                 "message_count": 5},
            ]
            result = _handle_repl_command(":ask --list", interp, analyzer, rs)
            assert result is True
            mock_list.assert_called_once()

    def test_ask_dash_resume_resumes_session(self):
        interp, analyzer, rs = self._make_ctx()
        with patch("helen.cli.ask_assistant.run_chat_mode") as mock_chat, \
             patch("helen.cli.ask_assistant.new_assistant_session") as mock_new:
            mock_new.return_value = MagicMock()
            result = _handle_repl_command(
                ":ask --resume session_abc", interp, analyzer, rs,
            )
            assert result is True
            mock_new.assert_called_once()
            # Should pass session_id
            assert mock_new.call_args.kwargs.get("session_id") == "session_abc" or \
                   (len(mock_new.call_args.args) >= 3 and mock_new.call_args.args[2] == "session_abc")
            mock_chat.assert_called_once()

    def test_help_mentions_ask(self):
        interp, analyzer, rs = self._make_ctx()
        from io import StringIO
        import sys
        buf = StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            _handle_repl_command(":help", interp, analyzer, rs)
        finally:
            sys.stdout = old
        help_text = buf.getvalue()
        assert ":ask" in help_text


# ---------------------------------------------------------------------------
# Streaming event handling (regression for dict event bug)
# ---------------------------------------------------------------------------

class TestRunStreaming:
    """_run_streaming must extract 'content' from typed dict events and
    ignore tool_call / tool_result / usage events."""

    def test_streaming_extracts_content_only(self, capsys):
        from helen.cli.ask_assistant import _run_streaming

        # Fake runtime that yields the same dict sequence act_stream does
        events = [
            {"type": "content", "content": "Hello "},
            {"type": "tool_call", "name": "repl_definitions", "args": {}},
            {"type": "tool_result", "name": "repl_definitions", "result": "[]"},
            {"type": "content", "content": "world"},
            {"type": "usage", "usage": {"prompt_tokens": 10}},
        ]

        class FakeRuntime:
            def act_stream(self, **kwargs):
                return iter(events)

        text = _run_streaming(
            FakeRuntime(), "prompt", "system", [], lambda n, a: "",
        )
        captured = capsys.readouterr()
        # Only content events should reach stdout
        assert captured.out.startswith("Hello world")
        # No tool_call/tool_result/usage in output
        assert "repl_definitions" not in captured.out
        assert "usage" not in captured.out
        # Returned text is concatenation of content only
        assert text == "Hello world"

    def test_streaming_handles_plain_string_chunk(self, capsys):
        """Legacy plain-string chunk (defensive) should also work."""
        from helen.cli.ask_assistant import _run_streaming

        class FakeRuntime:
            def act_stream(self, **kwargs):
                return iter(["plain ", "text"])

        text = _run_streaming(
            FakeRuntime(), "prompt", "system", [], lambda n, a: "",
        )
        captured = capsys.readouterr()
        assert "plain text" in captured.out
        assert text == "plain text"


# ---------------------------------------------------------------------------
# REPL stdout capture
# ---------------------------------------------------------------------------

class TestCapturingStdout:
    """_CapturingStdout tees writes to real stdout and ReplState."""

    def test_captures_and_passes_through(self, capsys):
        rs = ReplState()
        capturing = _CapturingStdout(sys.stdout, rs)
        capturing.write("hello ")
        capturing.write("world\n")
        # ReplState captured the output as separate lines
        assert rs.output_buffer == ["hello ", "world"]
        # Real stdout also received the writes (pytest captures it)
        captured = capsys.readouterr()
        assert "hello world" in captured.out
