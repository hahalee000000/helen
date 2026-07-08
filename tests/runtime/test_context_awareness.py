"""Tests for Phase 9A: Context Awareness."""

import pytest
from helen.runtime.context_awareness import (
    ContextAwareness,
    USAGE_NORMAL,
    USAGE_WARNING,
    USAGE_CRITICAL,
    USAGE_EMERGENCY,
    WARNING_THRESHOLD,
    CRITICAL_THRESHOLD,
    EMERGENCY_THRESHOLD,
)


class TestContextAwareness:
    """Test ContextAwareness class."""

    def test_no_warning_at_normal_usage(self):
        """No warning when usage is normal (< 50%)."""
        awareness = ContextAwareness(max_tokens=100_000)
        # 10 small messages = ~1000 tokens, usage ~1%
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]

        warning = awareness.build_usage_warning(messages)

        assert warning is None

    def test_warning_at_50_percent(self):
        """Warning injected at 50% usage."""
        awareness = ContextAwareness(max_tokens=10_000)
        # ~5000 tokens: 5000 * 4 chars = 20000 chars
        messages = [{"role": "user", "content": "x" * 20000}]

        warning = awareness.build_usage_warning(messages)

        assert warning is not None
        assert "<system_warning>" in warning
        assert "Token usage:" in warning

    def test_critical_at_75_percent(self):
        """Critical warning at 75% usage."""
        awareness = ContextAwareness(max_tokens=10_000)
        # ~7500 tokens: 7500 * 4 chars = 30000 chars
        messages = [{"role": "user", "content": "x" * 30000}]

        warning = awareness.build_usage_warning(messages)

        assert warning is not None
        assert "CRITICAL" not in warning  # Not emergency yet
        assert "summarizing" in warning.lower() or "consider" in warning.lower()

    def test_emergency_at_90_percent(self):
        """Emergency warning at 90% usage."""
        awareness = ContextAwareness(max_tokens=10_000)
        # ~9000 tokens: 9000 * 4 chars = 36000 chars
        messages = [{"role": "user", "content": "x" * 36000}]

        warning = awareness.build_usage_warning(messages)

        assert warning is not None
        assert "CRITICAL" in warning
        assert "MUST be concise" in warning

    def test_empty_messages(self):
        """Empty messages don't cause errors."""
        awareness = ContextAwareness(max_tokens=100_000)

        warning = awareness.build_usage_warning([])

        assert warning is None


class TestUsageLevels:
    """Test usage level classification."""

    def test_normal(self):
        awareness = ContextAwareness()
        assert awareness.get_usage_level(0.3) == USAGE_NORMAL
        assert awareness.get_usage_level(0.0) == USAGE_NORMAL
        assert awareness.get_usage_level(0.49) == USAGE_NORMAL

    def test_warning(self):
        awareness = ContextAwareness()
        assert awareness.get_usage_level(0.50) == USAGE_WARNING
        assert awareness.get_usage_level(0.60) == USAGE_WARNING
        assert awareness.get_usage_level(0.74) == USAGE_WARNING

    def test_critical(self):
        awareness = ContextAwareness()
        assert awareness.get_usage_level(0.75) == USAGE_CRITICAL
        assert awareness.get_usage_level(0.80) == USAGE_CRITICAL
        assert awareness.get_usage_level(0.89) == USAGE_CRITICAL

    def test_emergency(self):
        awareness = ContextAwareness()
        assert awareness.get_usage_level(0.90) == USAGE_EMERGENCY
        assert awareness.get_usage_level(0.95) == USAGE_EMERGENCY
        assert awareness.get_usage_level(1.0) == USAGE_EMERGENCY
        assert awareness.get_usage_level(1.5) == USAGE_EMERGENCY


class TestThresholds:
    """Test threshold constants."""

    def test_threshold_ordering(self):
        assert WARNING_THRESHOLD < CRITICAL_THRESHOLD < EMERGENCY_THRESHOLD

    def test_threshold_values(self):
        assert WARNING_THRESHOLD == 0.50
        assert CRITICAL_THRESHOLD == 0.75
        assert EMERGENCY_THRESHOLD == 0.90
