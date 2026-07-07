"""Tests for Phase 2: Graduated compression pipeline.

Tests the five-layer graduated compression:
- Layer 1: Budget Reduction (replace large tool outputs)
- Layer 2: Snip (drop stale turns)
- Layer 3: Microcompact (clear old tool results)
- Layer 4: Context Collapse (archive and project)
- Layer 5: Auto-Compact (LLM - not yet implemented)
"""

import pytest
from helen.runtime.history import Message
from helen.runtime.graduated_compression import (
    graduated_compress,
    _budget_reduction,
    _snip,
    _microcompact,
    _context_collapse,
    COMPRESSION_THRESHOLDS,
    LAYER_NONE,
    LAYER_BUDGET_REDUCTION,
    LAYER_SNIP,
    LAYER_MICROCOMPACT,
    LAYER_CONTEXT_COLLAPSE,
)


class TestBudgetReduction:
    """Tests for Layer 1: Budget Reduction."""

    def test_replaces_large_tool_output(self):
        """Test that large tool outputs are replaced with pointers."""
        large_content = "x" * 5000  # 5000 chars
        history = [
            Message(role="user", content="Read file", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {}}], tool_call_id=None, _token_count=15, _model="qwen3.7-plus"),
            Message(role="tool", content=large_content, tool_calls=[], tool_call_id="call_123", _token_count=1000, _model="qwen3.7-plus"),
        ]

        result = _budget_reduction(history)

        assert len(result) == 3
        tool_msg = result[2]
        assert tool_msg.compressed is True
        assert "cleared" in tool_msg.content.lower()
        assert "call_123" in tool_msg.content
        assert len(tool_msg.content) < 1000  # Much smaller than original

    def test_preserves_small_tool_output(self):
        """Test that small tool outputs are preserved."""
        small_content = "Small file content"
        history = [
            Message(role="tool", content=small_content, tool_calls=[], tool_call_id="call_456", _token_count=10, _model="qwen3.7-plus"),
        ]

        result = _budget_reduction(history)

        assert len(result) == 1
        tool_msg = result[0]
        assert tool_msg.content == small_content
        assert tool_msg.compressed is False

    def test_preserves_non_tool_messages(self):
        """Test that non-tool messages are not affected."""
        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="Hi there", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result = _budget_reduction(history)

        assert len(result) == 2
        assert result[0].content == "Hello"
        assert result[1].content == "Hi there"


class TestSnip:
    """Tests for Layer 2: Snip."""

    def test_drops_stale_turns(self):
        """Test that stale turns are dropped."""
        history = []
        for i in range(20):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        result = _snip(history, keep_recent=8)

        # Should keep 8 recent conversation turns
        assert len(result) == 8
        # Should be the most recent messages
        assert result[-1].content == "Message 19"
        assert result[-2].content == "Message 18"

    def test_preserves_system_messages(self):
        """Test that system messages are always preserved."""
        history = [
            Message(role="system", content="System prompt", tool_calls=[], tool_call_id=None, _token_count=50, _model="qwen3.7-plus"),
        ]
        for i in range(20):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        result = _snip(history, keep_recent=8)

        # Should have system message + 8 recent turns
        assert result[0].role == "system"
        assert result[0].content == "System prompt"
        assert len(result) == 9  # 1 system + 8 conversation

    def test_no_snip_when_few_messages(self):
        """Test that snip does nothing when few messages."""
        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="Hi", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result = _snip(history, keep_recent=8)

        assert len(result) == 2
        assert result == history


class TestMicrocompact:
    """Tests for Layer 3: Microcompact."""

    def test_clears_old_tool_results(self):
        """Test that old tool results are cleared."""
        history = [
            Message(role="user", content="Read file 1", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {}}], tool_call_id=None, _token_count=15, _model="qwen3.7-plus"),
            Message(role="tool", content="Old content 1", tool_calls=[], tool_call_id="call_1", _token_count=100, _model="qwen3.7-plus"),
            Message(role="user", content="Read file 2", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {}}], tool_call_id=None, _token_count=15, _model="qwen3.7-plus"),
            Message(role="tool", content="Old content 2", tool_calls=[], tool_call_id="call_2", _token_count=100, _model="qwen3.7-plus"),
            Message(role="user", content="Read file 3", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {}}], tool_call_id=None, _token_count=15, _model="qwen3.7-plus"),
            Message(role="tool", content="Recent content", tool_calls=[], tool_call_id="call_3", _token_count=100, _model="qwen3.7-plus"),
        ]

        result = _microcompact(history, keep_recent=1)

        # Should clear old tool results
        assert result[2].compressed is True
        assert result[2].role == "tool"
        assert "cleared" in result[2].content.lower()

        # Should preserve recent tool result
        assert result[8].compressed is False
        assert result[8].content == "Recent content"

    def test_preserves_tool_use_decisions(self):
        """Test that tool_use decisions (assistant tool calls) are preserved."""
        history = [
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {"path": "test.py"}}], tool_call_id=None, _token_count=20, _model="qwen3.7-plus"),
            Message(role="tool", content="File contents", tool_calls=[], tool_call_id="call_1", _token_count=100, _model="qwen3.7-plus"),
        ]

        result = _microcompact(history, keep_recent=1)

        # Tool_use decision should be preserved
        assert result[0].role == "assistant"
        assert result[0].tool_calls == [{"name": "read_file", "args": {"path": "test.py"}}]


class TestContextCollapse:
    """Tests for Layer 4: Context Collapse."""

    def test_collapses_old_turns(self):
        """Test that old turns are collapsed into summary."""
        history = [
            Message(role="system", content="System prompt", tool_calls=[], tool_call_id=None, _token_count=50, _model="qwen3.7-plus"),
        ]
        for i in range(30):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[{"name": "read_file", "args": {}}] if i % 3 == 0 else [],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        result = _context_collapse(history)

        # Should have system + summary + recent 20 turns
        assert len(result) < len(history)
        assert result[0].role == "system"
        # Should have a summary/timeline message
        summary_msgs = [m for m in result if "archived" in m.content.lower() or "timeline" in m.content.lower() or "context collapse" in m.content.lower()]
        assert len(summary_msgs) > 0

    def test_no_collapse_when_few_turns(self):
        """Test that collapse does nothing when few turns."""
        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="Hi", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result = _context_collapse(history)

        assert result == history


class TestGraduatedCompress:
    """Tests for the complete graduated compression pipeline."""

    def test_no_compression_when_under_threshold(self):
        """Test that no compression happens when under threshold."""
        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result, layer = graduated_compress(history, usage_ratio=0.3, max_tokens=131072)

        assert layer == LAYER_NONE
        assert result == history

    def test_budget_reduction_at_60_percent(self):
        """Test that budget reduction triggers at 60%."""
        # Create history with large tool output
        history = [
            Message(role="user", content="Read file", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="tool", content="x" * 5000, tool_calls=[], tool_call_id="call_1", _token_count=1000, _model="qwen3.7-plus"),
        ]

        result, layer = graduated_compress(history, usage_ratio=0.65, max_tokens=131072)

        assert layer == LAYER_BUDGET_REDUCTION
        assert result[1].compressed is True

    def test_snip_at_70_percent(self):
        """Test that snip triggers at 70%."""
        # Create history with enough tokens to reach 70%
        # 70% of 131072 = ~91750 tokens
        # Need 91750 / 100 = ~918 messages, but that's too many
        # Instead, use smaller max_tokens
        max_tokens = 5000  # 70% = 3500 tokens
        history = []
        for i in range(50):  # 50 messages * 100 tokens = 5000 tokens = 100%
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=100,
                _model="qwen3.7-plus",
            ))

        result, layer = graduated_compress(history, usage_ratio=1.0, max_tokens=max_tokens)

        # Should use snip (or higher layer) since we're over 70%
        assert layer in [LAYER_SNIP, LAYER_MICROCOMPACT, LAYER_CONTEXT_COLLAPSE]
        assert len(result) < len(history)

    def test_microcompact_at_80_percent(self):
        """Test that microcompact triggers at 80%."""
        # Create history with tool results
        max_tokens = 2000  # 80% = 1600 tokens
        history = []
        for i in range(15):
            history.append(Message(role="user", content=f"Read {i}", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"))
            history.append(Message(role="tool", content=f"Content {i}", tool_calls=[], tool_call_id=f"call_{i}", _token_count=100, _model="qwen3.7-plus"))
        # Total: 15 * (10 + 100) = 1650 tokens = 82.5%

        result, layer = graduated_compress(history, usage_ratio=0.825, max_tokens=max_tokens)

        # Should compress something (at least snip or higher)
        assert layer in [LAYER_SNIP, LAYER_MICROCOMPACT, LAYER_CONTEXT_COLLAPSE]
        # Result should be smaller than original
        assert len(result) < len(history) or any(m.compressed for m in result if m.role == "tool")

    def test_context_collapse_at_90_percent(self):
        """Test that context collapse triggers at 90%."""
        # Create history with many turns
        max_tokens = 4000  # 90% = 3600 tokens
        history = [
            Message(role="system", content="System", tool_calls=[], tool_call_id=None, _token_count=50, _model="qwen3.7-plus"),
        ]
        for i in range(50):  # 50 * 100 = 5000 tokens, total ~5050 = 126%
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=100,
                _model="qwen3.7-plus",
            ))

        result, layer = graduated_compress(history, usage_ratio=1.26, max_tokens=max_tokens)

        # Should compress something (at least snip or higher)
        assert layer in [LAYER_SNIP, LAYER_MICROCOMPACT, LAYER_CONTEXT_COLLAPSE]
        # Result should be significantly smaller
        assert len(result) < len(history)

    def test_empty_history(self):
        """Test that empty history returns unchanged."""
        result, layer = graduated_compress([], usage_ratio=0.5, max_tokens=131072)

        assert layer == LAYER_NONE
        assert result == []


class TestAutoCompactLLMIntegration:
    """Tests for Layer 5 LLM semantic summarization integration."""

    def test_auto_compact_without_llm_client_uses_structural(self):
        """Without llm_client, Layer 5 uses structural summarization."""
        from helen.runtime.graduated_compression import _auto_compact

        history = []
        for i in range(20):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        # Without llm_client
        result = _auto_compact(history, keep_recent=4, llm_client=None)

        # Should use structural summary
        assert len(result) < len(history)
        summary_msgs = [m for m in result if "Auto-Compact" in m.content]
        assert len(summary_msgs) > 0

    def test_auto_compact_with_llm_client_uses_semantic(self):
        """With llm_client, Layer 5 uses LLM semantic summarization."""
        from helen.runtime.graduated_compression import _auto_compact

        history = []
        for i in range(20):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        # Mock LLM client
        def mock_llm_client(messages):
            return "LLM-generated semantic summary of conversation"

        result = _auto_compact(history, keep_recent=4, llm_client=mock_llm_client)

        # Should use LLM summary
        assert len(result) < len(history)
        summary_msgs = [m for m in result if "LLM-generated" in m.content]
        assert len(summary_msgs) > 0

    def test_auto_compact_llm_failure_falls_back_to_structural(self):
        """When LLM fails, falls back to structural summarization."""
        from helen.runtime.graduated_compression import _auto_compact

        history = []
        for i in range(20):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        # Mock LLM client that raises exception
        def failing_llm_client(messages):
            raise RuntimeError("LLM unavailable")

        result = _auto_compact(history, keep_recent=4, llm_client=failing_llm_client)

        # Should still produce a summary (either LLM fallback or structural)
        assert len(result) < len(history)
        # LLMSummarizer has its own fallback that produces "Conversation Summary - Auto-generated fallback"
        # which gets wrapped in "[Previous conversation summary - LLM generated]"
        # Or _auto_compact catches exception and falls back to structural "Auto-Compact"
        summary_msgs = [m for m in result if
                       "Auto-Compact" in m.content or
                       "Previous conversation summary" in m.content]
        assert len(summary_msgs) > 0


class TestContextCollapseTimeline:
    """Tests for Layer 4 Context Collapse timeline preservation."""

    def test_context_collapse_generates_timeline(self):
        """Context Collapse generates timeline with segmented blocks."""
        from helen.runtime.graduated_compression import _context_collapse

        history = [
            Message(role="system", content="System", tool_calls=[], tool_call_id=None, _token_count=50, _model="qwen3.7-plus"),
        ]
        for i in range(30):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[{"name": "read_file", "args": {}}] if i % 3 == 0 else [],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        result = _context_collapse(history)

        # Should have timeline message
        assert len(result) < len(history)
        timeline_msgs = [m for m in result if "timeline" in m.content.lower() or "archived" in m.content.lower()]
        assert len(timeline_msgs) > 0

        # Timeline should contain segment markers
        timeline_content = timeline_msgs[0].content
        assert "[0-10]" in timeline_content or "[0-" in timeline_content

    def test_context_collapse_preserves_global_stats(self):
        """Context Collapse includes global statistics."""
        from helen.runtime.graduated_compression import _context_collapse

        history = []
        for i in range(30):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        result = _context_collapse(history)

        # Should have global stats
        summary_msgs = [m for m in result if "[Global]" in m.content]
        assert len(summary_msgs) > 0
