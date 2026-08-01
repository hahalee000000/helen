"""Tests for ChatSessionActor debug/observability tool wrappers.

Verifies that the new P1/P2 tools (emit_debug, search_session_transcript,
get_context_stats, enable_tracing, get_execution_trace) are:
1. Syntactically correct (helen check passes)
2. Resolvable as LLM tools (appear in _build_tools_list output)
3. Delegate correctly to stdlib functions
"""
import os
import tempfile
import unittest

from helen.cli.__main__ import check_command


class TestChatSessionActorToolSyntax(unittest.TestCase):
    """Verify the tool wrapper functions pass helen check."""

    def _check_helen_code(self, code: str) -> int:
        """Write Helen code to a temp file and run helen check."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                return check_command(f.name)
            finally:
                os.unlink(f.name)

    def test_chat_session_actor_passes_check(self):
        """Full ChatSessionActor file passes helen check."""
        actor_path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "helen", "agent", "chat_session_actor.helen"
        )
        # Normalize the path
        actor_path = os.path.normpath(actor_path)
        if not os.path.exists(actor_path):
            self.skipTest(f"File not found: {actor_path}")
        result = check_command(actor_path)
        self.assertEqual(result, 0, "chat_session_actor.helen failed helen check")

    def test_contracts_passes_check(self):
        """Contracts file (CHAT_TOOLS) passes helen check."""
        contracts_path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "helen", "agent", "contracts", "contracts.helen"
        )
        contracts_path = os.path.normpath(contracts_path)
        if not os.path.exists(contracts_path):
            self.skipTest(f"File not found: {contracts_path}")
        result = check_command(contracts_path)
        self.assertEqual(result, 0, "contracts.helen failed helen check")

    def test_emit_debug_syntax(self):
        """emit_debug wrapper function has correct syntax."""
        code = """
agent TestAgent {
    description "test"
    functions {
        fn emit_debug(message: str, data: str): str {
            if data == "" {
                return debug(message)
            }
            let parsed = json_parse(data)
            return debug(message, parsed)
        }
    }
    main {
        let result = emit_debug("test message", "")
    }
}
"""
        result = self._check_helen_code(code)
        self.assertEqual(result, 0, "emit_debug wrapper failed helen check")

    def test_search_session_transcript_syntax(self):
        """search_session_transcript wrapper has correct syntax."""
        code = """
agent TestAgent {
    description "test"
    functions {
        fn search_session_transcript(query: str, limit: int): str {
            let results = search_transcript(query, limit=limit)
            return json_stringify(results)
        }
    }
    main {
        let result = search_session_transcript("test", 10)
    }
}
"""
        result = self._check_helen_code(code)
        self.assertEqual(result, 0, "search_session_transcript wrapper failed helen check")

    def test_get_context_stats_syntax(self):
        """get_context_stats wrapper has correct syntax."""
        code = """
agent TestAgent {
    description "test"
    functions {
        fn get_context_stats(): map {
            return context_stats()
        }
    }
    main {
        let stats = get_context_stats()
    }
}
"""
        result = self._check_helen_code(code)
        self.assertEqual(result, 0, "get_context_stats wrapper failed helen check")

    def test_tracing_tools_syntax(self):
        """enable_tracing and get_execution_trace wrappers have correct syntax."""
        code = """
agent TestAgent {
    description "test"
    functions {
        fn enable_tracing(): str {
            return trace_on()
        }
        fn get_execution_trace(n: int): str {
            return get_trace(n)
        }
    }
    main {
        let status = enable_tracing()
        let trace = get_execution_trace(10)
    }
}
"""
        result = self._check_helen_code(code)
        self.assertEqual(result, 0, "tracing tools wrappers failed helen check")


class TestToolResolution(unittest.TestCase):
    """Verify new tools appear in CHAT_TOOLS and are resolvable."""

    def test_chat_tools_contains_debug_tools(self):
        """CHAT_TOOLS const includes the new debug/observability tools."""
        contracts_path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "helen", "agent", "contracts", "contracts.helen"
        )
        contracts_path = os.path.normpath(contracts_path)
        if not os.path.exists(contracts_path):
            self.skipTest(f"File not found: {contracts_path}")

        with open(contracts_path) as f:
            content = f.read()

        expected_tools = [
            "emit_debug",
            "search_session_transcript",
            "get_context_stats",
            "enable_tracing",
            "get_execution_trace",
            "query_llm_log",
            "query_last_error",
            "query_call_stack",
        ]
        for tool in expected_tools:
            self.assertIn(
                f'"{tool}"', content,
                f"CHAT_TOOLS should contain '{tool}'"
            )

    def test_chat_tools_no_invalid_stdlib_names(self):
        """CHAT_TOOLS no longer contains unresolved stdlib names."""
        contracts_path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "helen", "agent", "contracts", "contracts.helen"
        )
        contracts_path = os.path.normpath(contracts_path)
        if not os.path.exists(contracts_path):
            self.skipTest(f"File not found: {contracts_path}")

        with open(contracts_path) as f:
            content = f.read()

        # These stdlib names should NOT be in CHAT_TOOLS
        # because they can't be resolved as LLM tools
        invalid_names = ["path_exists", "mkdir_p", "list_dir", "glob_files"]
        for name in invalid_names:
            self.assertNotIn(
                f'"{name}"', content,
                f"CHAT_TOOLS should not contain unresolved stdlib name '{name}'"
            )

    def test_actor_has_wrapper_functions(self):
        """ChatSessionActor functions {} block contains wrapper functions."""
        actor_path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "helen", "agent", "chat_session_actor.helen"
        )
        actor_path = os.path.normpath(actor_path)
        if not os.path.exists(actor_path):
            self.skipTest(f"File not found: {actor_path}")

        with open(actor_path) as f:
            content = f.read()

        expected_fns = [
            "fn emit_debug(",
            "fn search_session_transcript(",
            "fn get_context_stats()",
            "fn enable_tracing()",
            "fn get_execution_trace(",
            "fn query_llm_log(",
            "fn query_last_error()",
            "fn query_call_stack()",
        ]
        for fn_sig in expected_fns:
            self.assertIn(
                fn_sig, content,
                f"ChatSessionActor should declare '{fn_sig}' in functions block"
            )


class TestStdlibWrappers(unittest.TestCase):
    """Test the stdlib functions that wrappers delegate to."""

    def test_debug_returns_string(self):
        """stdlib debug() returns a string."""
        from helen.stdlib import _debug
        result = _debug("test message")
        self.assertIsInstance(result, str)
        self.assertIn("[DEBUG]", result)
        self.assertIn("test message", result)

    def test_debug_with_data(self):
        """stdlib debug() with data dict returns formatted output."""
        from helen.stdlib import _debug
        result = _debug("test", {"key": "value"})
        self.assertIsInstance(result, str)
        self.assertIn("key", result)
        self.assertIn("value", result)

    def test_context_stats_returns_dict(self):
        """stdlib context_stats() returns a dict."""
        from helen.stdlib.context import _context_stats
        result = _context_stats()
        self.assertIsInstance(result, dict)
        # Should have basic stats fields
        self.assertIn("total_tokens", result)

    def test_trace_on_returns_string(self):
        """stdlib trace_on() returns a confirmation string."""
        from helen.stdlib import _trace_on
        result = _trace_on()
        self.assertIsInstance(result, str)
        # Should indicate tracing is enabled (or warn if no context)
        self.assertTrue(
            "enabled" in result.lower() or "warning" in result.lower(),
            f"Unexpected trace_on result: {result}"
        )


class TestObservabilityStdlibFunctions(unittest.TestCase):
    """Test the new observability stdlib functions."""

    def test_get_llm_log_returns_string(self):
        """stdlib get_llm_log() returns a string."""
        from helen.stdlib import _get_llm_log
        result = _get_llm_log(5)
        self.assertIsInstance(result, str)

    def test_get_llm_log_without_context(self):
        """stdlib get_llm_log() handles no interpreter context."""
        from helen.stdlib import _get_llm_log, _set_interpreter_observability
        # Save and clear context
        saved = __import__('helen.stdlib', fromlist=['_interpreter_observability'])._interpreter_observability
        _set_interpreter_observability(None)
        result = _get_llm_log()
        self.assertIn("no interpreter", result.lower())
        # Restore context
        _set_interpreter_observability(saved)

    def test_get_last_error_returns_string(self):
        """stdlib get_last_error() returns a string."""
        from helen.stdlib import _get_last_error
        result = _get_last_error()
        self.assertIsInstance(result, str)

    def test_get_call_stack_returns_string(self):
        """stdlib get_call_stack() returns a string."""
        from helen.stdlib import _get_call_stack
        result = _get_call_stack()
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
