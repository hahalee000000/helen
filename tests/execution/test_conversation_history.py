"""Tests for helen.interpreter.interpreter — conversation history integration (HLD 3.6.6, 3.12).

Covers:
- _get_context() returns conversation summary from history
- _add_to_history() accumulates messages
- history property returns a copy
- clear_history() resets state
- LLM statements (act/if/choose) record to history
- Summary is capped at 4096 tokens
"""

from helen.interpreter.interpreter import Interpreter
from helen.core.errors import ErrorReporter
from helen.runtime.llm_runtime import MockLLMRuntime, LLMResponse


class TestGetContext:
    """Test _get_context() integration with HistoryManager."""

    def setup_method(self):
        self.interp = Interpreter(
            errors=ErrorReporter(),
            llm_runtime=MockLLMRuntime(),
        )

    def test_get_context_empty_history(self):
        """Returns None when history is empty."""
        assert self.interp._get_context() is None

    def test_get_context_single_message(self):
        """Returns formatted summary for single message."""
        self.interp._add_to_history("user", "Hello world")
        ctx = self.interp._get_context()
        assert ctx is not None
        assert "[user]" in ctx
        assert "Hello world" in ctx

    def test_get_context_multiple_messages(self):
        """Returns chronological summary for multiple messages."""
        self.interp._add_to_history("user", "question")
        self.interp._add_to_history("assistant", "answer")
        ctx = self.interp._get_context()
        assert ctx is not None
        assert "[user]" in ctx
        assert "[assistant]" in ctx
        # User message should come before assistant
        assert ctx.index("[user]") < ctx.index("[assistant]")

    def test_get_context_4096_token_cap(self):
        """Summary does not exceed 4096 tokens."""
        # Add messages that would exceed 4096 tokens
        large_content = "x" * 20000  # ~5000 tokens each
        for i in range(5):
            self.interp._add_to_history("user" if i % 2 == 0 else "assistant", large_content)
        ctx = self.interp._get_context()
        assert ctx is not None
        token_est = len(ctx) // 4
        assert token_est <= 4096

    def test_get_context_uses_history_manager_format(self):
        """Uses [role] content format from HistoryManager."""
        self.interp._add_to_history("user", "test input")
        self.interp._add_to_history("assistant", "test output")
        ctx = self.interp._get_context()
        assert "[user] test input" in ctx
        assert "[assistant] test output" in ctx


class TestAddToHistory:
    """Test _add_to_history() method."""

    def setup_method(self):
        self.interp = Interpreter(
            errors=ErrorReporter(),
            llm_runtime=MockLLMRuntime(),
        )

    def test_add_single_message(self):
        """Adds a message to history."""
        self.interp._add_to_history("user", "hello")
        assert len(self.interp.history) == 1
        assert self.interp.history[0].role == "user"
        assert self.interp.history[0].content == "hello"

    def test_add_multiple_messages(self):
        """Accumulates multiple messages."""
        self.interp._add_to_history("user", "msg1")
        self.interp._add_to_history("assistant", "msg2")
        self.interp._add_to_history("user", "msg3")
        assert len(self.interp.history) == 3

    def test_all_roles_supported(self):
        """Supports all standard roles."""
        for role in ["user", "assistant", "system", "tool"]:
            self.interp._add_to_history(role, f"{role} message")
        assert len(self.interp.history) == 4


class TestHistoryProperty:
    """Test history property."""

    def setup_method(self):
        self.interp = Interpreter(
            errors=ErrorReporter(),
            llm_runtime=MockLLMRuntime(),
        )

    def test_returns_copy(self):
        """Returns a copy, not the internal list."""
        self.interp._add_to_history("user", "test")
        h1 = self.interp.history
        h2 = self.interp.history
        assert h1 is not h2  # Different objects

    def test_modifying_copy_does_not_affect_internal(self):
        """Modifying the returned copy doesn't affect internal state."""
        self.interp._add_to_history("user", "test")
        h = self.interp.history
        h.clear()
        assert len(self.interp.history) == 1  # Internal still has the message


class TestClearHistory:
    """Test clear_history() method."""

    def setup_method(self):
        self.interp = Interpreter(
            errors=ErrorReporter(),
            llm_runtime=MockLLMRuntime(),
        )

    def test_clear_empties_history(self):
        """Clear removes all messages."""
        self.interp._add_to_history("user", "msg1")
        self.interp._add_to_history("assistant", "msg2")
        self.interp.clear_history()
        assert len(self.interp.history) == 0
        assert self.interp._get_context() is None

    def test_clear_allows_new_messages(self):
        """Can add messages after clearing."""
        self.interp._add_to_history("user", "old")
        self.interp.clear_history()
        self.interp._add_to_history("user", "new")
        assert len(self.interp.history) == 1
        assert self.interp.history[0].content == "new"


class TestLlmStatementsRecordHistory:
    """Test that LLM statements record interactions to history."""

    def setup_method(self):
        self.runtime = MockLLMRuntime(act_return=LLMResponse(text="result"))
        self.interp = Interpreter(
            errors=ErrorReporter(),
            llm_runtime=self.runtime,
        )

    def test_llm_if_records_to_history(self):
        """llm if records description and routing to history."""
        from helen.core.ast import (
            LlmIfStmtNode, LlmBranchNode, LiteralNode, SourceSpan,
        )
        self.runtime.route_return = "urgent"
        span = SourceSpan("test.helen", 1, 1, 1, 30)
        branch_urgent = LlmBranchNode(
            span=span,
            condition=LiteralNode(span=span, value="urgent"),
            body=[],
        )
        branch_default = LlmBranchNode(
            span=span,
            condition=None,
            body=[],
        )
        node = LlmIfStmtNode(
            span=span,
            description="Classify priority",
            branches=[branch_urgent, branch_default],
        )
        self.interp.visit_llm_if_stmt(node)
        # Verify history was recorded
        assert len(self.interp.history) == 2
        assert "[route]" in self.interp.history[0].content
        assert "[routed to: urgent]" in self.interp.history[1].content
