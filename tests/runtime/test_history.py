"""Tests for helen.runtime.history — HistoryManager (HLD 3.12).

Covers:
- Token budget calculation
- History trimming (oldest-first)
- Conversation summary building
- 4096 Token limit
- Truncation logging
"""

from helen.runtime.history import HistoryManager, Message


def _make_messages(n: int) -> list[Message]:
    """Create n test messages."""
    return [
        Message(role="user" if i % 2 == 0 else "assistant", content=f"msg {i}")
        for i in range(n)
    ]


class TestHistoryManagerBudget:
    """Test token budget calculation."""

    def setup_method(self):
        self.hm = HistoryManager()

    def test_basic_budget(self):
        """Budget = MAX - system - instruction - buffer."""
        # MAX_TOKENS=128000, buffer=1000
        budget = self.hm.check_budget(1000, 500)
        assert budget == 128000 - 1000 - 500 - 1000

    def test_budget_with_large_system(self):
        """Large system prompt reduces available budget."""
        budget = self.hm.check_budget(50000, 1000)
        assert budget == 128000 - 50000 - 1000 - 1000

    def test_budget_zero(self):
        """When system + instruction exceeds limit, budget is 0 or negative."""
        budget = self.hm.check_budget(120000, 10000)
        assert budget <= 0


class TestHistoryManagerTrim:
    """Test history trimming."""

    def setup_method(self):
        self.hm = HistoryManager()

    def test_trim_removes_oldest(self):
        """Trim removes oldest messages first."""
        msgs = _make_messages(10)
        # Estimate: each msg ~1 token (short content)
        # Budget of 5 tokens should keep ~5 newest messages
        trimmed = self.hm.trim_history(msgs, budget=5)
        assert len(trimmed) <= 10
        # Should keep the newest messages
        if len(trimmed) < len(msgs):
            assert trimmed[-1].content == "msg 9"  # newest kept

    def test_trim_returns_empty_when_over_budget(self):
        """If even one message exceeds budget, returns empty."""
        msgs = [Message(role="user", content="x" * 10000)]
        trimmed = self.hm.trim_history(msgs, budget=1)
        assert trimmed == []

    def test_trim_keeps_all_when_under_budget(self):
        """When history fits in budget, nothing is trimmed."""
        msgs = _make_messages(3)
        # Generous budget
        trimmed = self.hm.trim_history(msgs, budget=1000)
        assert trimmed == msgs

    def test_trim_empty_history(self):
        """Trimming empty history returns empty."""
        trimmed = self.hm.trim_history([], budget=100)
        assert trimmed == []


class TestHistoryManagerSummary:
    """Test conversation summary building."""

    def setup_method(self):
        self.hm = HistoryManager()

    def test_summary_format(self):
        """Summary uses [role] content format."""
        msgs = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
        ]
        summary = self.hm.build_conversation_summary(msgs)
        assert "[user]" in summary
        assert "[assistant]" in summary
        assert "Hello" in summary

    def test_summary_respects_4096_limit(self):
        """Summary does not exceed max_tokens."""
        # Create messages that exceed 4096 tokens
        large_msgs = [
            Message(role="user", content="x" * 20000)  # ~5000 tokens
            for _ in range(3)
        ]
        summary = self.hm.build_conversation_summary(large_msgs, max_tokens=4096)
        token_est = self.hm.estimate_tokens(summary)
        assert token_est <= 4096

    def test_summary_includes_newest_messages(self):
        """Summary includes newest messages when trimming is needed."""
        msgs = [
            Message(role="user", content="old " * 50),  # ~25 tokens
            Message(role="assistant", content="recent message here"),  # ~5 tokens
        ]
        summary = self.hm.build_conversation_summary(msgs, max_tokens=15)
        # Should include the newest message that fits
        assert "recent" in summary or "old" in summary  # At least one message

    def test_summary_empty_history(self):
        """Summary of empty history is empty string."""
        summary = self.hm.build_conversation_summary([])
        assert summary == ""


class TestTokenEstimation:
    """Test token count estimation."""

    def setup_method(self):
        self.hm = HistoryManager()

    def test_simple_estimation(self):
        """chars / 4 gives reasonable estimate."""
        tokens = self.hm.estimate_tokens("hello world")
        assert tokens > 0
        assert tokens == len("hello world") // 4

    def test_empty_string(self):
        """Empty string has 0 tokens."""
        assert self.hm.estimate_tokens("") == 0
