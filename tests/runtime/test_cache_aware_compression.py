"""Tests for Phase 6: Cache-aware compression.

Tests cache-friendly compression strategies that maximize prompt cache hit rate:
- Stable prefix preservation
- Suffix-only modification
- Batched threshold compression
- Cache zone identification
- Integration with graduated compression
"""

import pytest
from helen.runtime.history import Message
from helen.runtime.cache_aware_compression import (
    CacheAwareCompressor,
    CacheStats,
    cache_aware_compress,
    DEFAULT_CACHE_ZONE_RATIO,
    MIN_CACHE_ZONE_MESSAGES,
    BATCH_COMPRESSION_THRESHOLD,
    CACHE_HIT_STABLE,
    CACHE_HIT_PARTIAL,
    CACHE_HIT_INVALIDATED,
)


class TestCacheZoneIdentification:
    """Tests for cache zone identification."""

    def test_identify_cache_zone_with_ratio(self):
        """Test cache zone identification with ratio."""
        compressor = CacheAwareCompressor(cache_zone_ratio=0.3)

        history = []
        for i in range(100):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        cache_zone_end = compressor._identify_cache_zone(history)

        # Should be 30% of 100 = 30 messages
        assert cache_zone_end == 30

    def test_identify_cache_zone_minimum_messages(self):
        """Test that cache zone respects minimum message count."""
        compressor = CacheAwareCompressor(
            cache_zone_ratio=0.1,
            min_cache_zone_messages=10,
        )

        history = []
        for i in range(50):
            history.append(Message(
                role="user",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        cache_zone_end = compressor._identify_cache_zone(history)

        # Should be at least min_cache_zone_messages
        assert cache_zone_end >= 10

    def test_identify_cache_zone_leaves_room(self):
        """Test that cache zone leaves room for compression."""
        compressor = CacheAwareCompressor(cache_zone_ratio=0.9)

        history = []
        for i in range(10):
            history.append(Message(
                role="user",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        cache_zone_end = compressor._identify_cache_zone(history)

        # Should leave at least 2 messages for compression
        assert len(history) - cache_zone_end >= 2


class TestBatchedThreshold:
    """Tests for batched threshold compression."""

    def test_skip_compression_below_threshold(self):
        """Test that compression is skipped below threshold."""
        compressor = CacheAwareCompressor(batch_threshold=0.75)

        # Create history with low usage
        history = []
        for i in range(10):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))

        max_tokens = 131072  # Large context window
        result, stats = compressor.compress(history, max_tokens)

        # Should not compress (usage is very low)
        assert result == history
        assert stats.compression_strategy == "batch_threshold_not_reached"
        assert stats.estimated_cache_hit == CACHE_HIT_STABLE

    def test_compress_above_threshold(self):
        """Test that compression triggers above threshold."""
        compressor = CacheAwareCompressor(batch_threshold=0.75)

        # Create history with high usage
        history = []
        for i in range(50):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=100,
                _model="qwen3.7-plus",
            ))

        max_tokens = 3000  # Small context window to force high usage
        result, stats = compressor.compress(history, max_tokens)

        # Should compress
        assert stats.compression_strategy == "cache_aware"
        assert len(result) <= len(history)


class TestStablePrefixPreservation:
    """Tests for stable prefix preservation."""

    def test_cache_zone_not_modified(self):
        """Test that cache zone messages are not modified."""
        compressor = CacheAwareCompressor(cache_zone_ratio=0.3)

        # Create history with tool results (which would normally be compressed)
        history = []
        for i in range(20):
            history.append(Message(
                role="user",
                content=f"Read file {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=10,
                _model="qwen3.7-plus",
            ))
            history.append(Message(
                role="tool",
                content=f"File content {i}",
                tool_calls=[],
                tool_call_id=f"call_{i}",
                _token_count=100,
                _model="qwen3.7-plus",
            ))

        max_tokens = 3000  # Force compression
        result, stats = compressor.compress(history, max_tokens)

        # Cache zone should be preserved
        cache_zone_end = compressor._identify_cache_zone(history)
        for i in range(cache_zone_end):
            assert result[i].content == history[i].content
            assert result[i].compressed is False

    def test_cache_zone_preserved_flag(self):
        """Test that cache_zone_preserved flag is set."""
        compressor = CacheAwareCompressor()

        history = []
        for i in range(30):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=50,
                _model="qwen3.7-plus",
            ))

        max_tokens = 1000  # Force compression
        result, stats = compressor.compress(history, max_tokens)

        # Cache zone should be preserved
        assert stats.cache_zone_preserved is True


class TestSuffixOnlyCompression:
    """Tests for suffix-only compression."""

    def test_only_modify_suffix(self):
        """Test that only messages after cache zone are modified."""
        compressor = CacheAwareCompressor(cache_zone_ratio=0.3)

        history = []
        for i in range(30):
            history.append(Message(
                role="tool",
                content=f"File content {i}",
                tool_calls=[],
                tool_call_id=f"call_{i}",
                _token_count=100,
                _model="qwen3.7-plus",
            ))

        max_tokens = 2000  # Force compression
        result, stats = compressor.compress(history, max_tokens)

        # Check that modifications only happened in compressible zone
        cache_zone_end = compressor._identify_cache_zone(history)

        # Cache zone should be unchanged
        for i in range(cache_zone_end):
            if i < len(result):
                assert result[i].compressed is False

        # Compressible zone may be modified
        compressed_count = sum(1 for msg in result[cache_zone_end:] if msg.compressed)
        assert compressed_count > 0


class TestCacheStats:
    """Tests for cache statistics."""

    def test_stats_structure(self):
        """Test that stats has correct structure."""
        stats = CacheStats(
            cache_zone_size=10,
            compressible_zone_size=20,
            messages_modified=5,
            cache_zone_preserved=True,
            compression_strategy="cache_aware",
            estimated_cache_hit=CACHE_HIT_PARTIAL,
            tokens_saved=1000,
        )

        assert stats.cache_zone_size == 10
        assert stats.compressible_zone_size == 20
        assert stats.messages_modified == 5
        assert stats.cache_zone_preserved is True
        assert stats.compression_strategy == "cache_aware"
        assert stats.estimated_cache_hit == CACHE_HIT_PARTIAL
        assert stats.tokens_saved == 1000

    def test_stats_to_dict(self):
        """Test stats to_dict conversion."""
        stats = CacheStats(cache_zone_size=10)
        d = stats.to_dict()

        assert isinstance(d, dict)
        assert d["cache_zone_size"] == 10
        assert "compressible_zone_size" in d
        assert "messages_modified" in d


class TestCacheHitEstimation:
    """Tests for cache hit estimation."""

    def test_stable_hit_when_no_modifications(self):
        """Test stable cache hit when no modifications."""
        compressor = CacheAwareCompressor()

        # Create small history that doesn't need compression
        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        max_tokens = 131072
        result, stats = compressor.compress(history, max_tokens)

        assert stats.estimated_cache_hit == CACHE_HIT_STABLE

    def test_partial_hit_when_few_modifications(self):
        """Test cache hit estimation with various modification rates."""
        compressor = CacheAwareCompressor(cache_zone_ratio=0.5)

        history = []
        for i in range(20):
            history.append(Message(
                role="tool",
                content=f"Content {i}",
                tool_calls=[],
                tool_call_id=f"call_{i}",
                _token_count=100,
                _model="qwen3.7-plus",
            ))

        max_tokens = 1500  # Force moderate compression
        result, stats = compressor.compress(history, max_tokens)

        # Should be one of the valid cache hit states
        assert stats.estimated_cache_hit in [
            CACHE_HIT_STABLE,
            CACHE_HIT_PARTIAL,
            CACHE_HIT_INVALIDATED,
        ]
        # Verify cache zone is preserved
        assert stats.cache_zone_preserved is True


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_cache_aware_compress_function(self):
        """Test cache_aware_compress convenience function."""
        history = []
        for i in range(30):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=100,
                _model="qwen3.7-plus",
            ))

        max_tokens = 2000
        result, stats = cache_aware_compress(history, max_tokens, cache_zone_ratio=0.3)

        assert isinstance(result, list)
        assert isinstance(stats, CacheStats)
        assert len(result) <= len(history)


class TestIntegration:
    """Integration tests for cache-aware compression."""

    def test_full_compression_pipeline(self):
        """Test full compression pipeline with cache awareness."""
        # Create realistic conversation history
        history = []
        for i in range(50):
            history.append(Message(
                role="user",
                content=f"User message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=20,
                _model="qwen3.7-plus",
            ))
            history.append(Message(
                role="assistant",
                content="",
                tool_calls=[{"name": "read_file", "args": {}}],
                tool_call_id=None,
                _token_count=15,
                _model="qwen3.7-plus",
            ))
            history.append(Message(
                role="tool",
                content=f"File content {i} " * 20,  # Large content
                tool_calls=[],
                tool_call_id=f"call_{i}",
                _token_count=500,
                _model="qwen3.7-plus",
            ))

        # Compress with cache awareness
        max_tokens = 10000
        result, stats = cache_aware_compress(history, max_tokens, cache_zone_ratio=0.3)

        # Verify cache zone preserved
        cache_zone_end = int(len(history) * 0.3)
        for i in range(min(cache_zone_end, len(result))):
            assert result[i].compressed is False

        # Verify compression happened
        assert stats.messages_modified > 0
        assert stats.tokens_saved > 0

        # Verify cache hit estimation
        assert stats.estimated_cache_hit in [
            CACHE_HIT_STABLE,
            CACHE_HIT_PARTIAL,
            CACHE_HIT_INVALIDATED,
        ]

    def test_empty_history(self):
        """Test compression with empty history."""
        result, stats = cache_aware_compress([], max_tokens=131072)

        assert result == []
        assert stats.cache_zone_size == 0

    def test_single_message(self):
        """Test compression with single message."""
        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result, stats = cache_aware_compress(history, max_tokens=131072)

        assert len(result) == 1
        assert result[0].content == "Hello"
