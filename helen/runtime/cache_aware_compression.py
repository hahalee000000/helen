"""Cache-aware compression strategies for context management.

Phase 6: Cache-friendly compression that maximizes prompt cache hit rate.

Design Principles:
1. Stable Prefix: Keep first N messages unchanged (cache-friendly zone)
2. Suffix Modification: Only modify messages at the end of the list
3. Batched Compression: Compress only when reaching threshold (reduce frequency)
4. Compression Boundary: Use stable markers instead of inserting new messages

Expected Benefits:
- Cache hit rate: 10-20% → 70-80%
- Cost reduction: 50-70%
- Latency reduction: 30-50%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from helen.runtime.history import Message
from helen.runtime.graduated_compression import (
    _microcompact as microcompact,
    _budget_reduction as budget_reduction,
    _calculate_usage_ratio,
    COMPRESSION_THRESHOLDS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 6: Cache-aware compression constants
# ---------------------------------------------------------------------------

# Default cache-friendly zone ratio (30% of messages)
DEFAULT_CACHE_ZONE_RATIO = 0.30

# Minimum messages to keep in cache zone
MIN_CACHE_ZONE_MESSAGES = 5

# Batch compression threshold (only compress when usage reaches this)
BATCH_COMPRESSION_THRESHOLD = 0.75

# Cache statistics
CACHE_HIT_STABLE = "stable"
CACHE_HIT_PARTIAL = "partial"
CACHE_HIT_INVALIDATED = "invalidated"


@dataclass
class CacheStats:
    """Statistics for cache-aware compression."""

    cache_zone_size: int = 0
    compressible_zone_size: int = 0
    messages_modified: int = 0
    cache_zone_preserved: bool = True
    compression_strategy: str = "none"
    estimated_cache_hit: str = CACHE_HIT_STABLE
    tokens_saved: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "cache_zone_size": self.cache_zone_size,
            "compressible_zone_size": self.compressible_zone_size,
            "messages_modified": self.messages_modified,
            "cache_zone_preserved": self.cache_zone_preserved,
            "compression_strategy": self.compression_strategy,
            "estimated_cache_hit": self.estimated_cache_hit,
            "tokens_saved": self.tokens_saved,
        }


class CacheAwareCompressor:
    """Cache-friendly compression strategies.

    Implements compression that maximizes prompt cache hit rate by:
    - Preserving the first N messages (cache-friendly zone)
    - Only modifying messages at the end of the list
    - Using batched compression to reduce frequency
    - Avoiding insertion of new messages at the beginning
    """

    def __init__(
        self,
        cache_zone_ratio: float = DEFAULT_CACHE_ZONE_RATIO,
        min_cache_zone_messages: int = MIN_CACHE_ZONE_MESSAGES,
        batch_threshold: float = BATCH_COMPRESSION_THRESHOLD,
    ):
        """Initialize cache-aware compressor.

        Args:
            cache_zone_ratio: Ratio of messages to keep in cache zone (0.0-1.0)
            min_cache_zone_messages: Minimum number of messages in cache zone
            batch_threshold: Usage ratio threshold before triggering compression
        """
        self.cache_zone_ratio = cache_zone_ratio
        self.min_cache_zone_messages = min_cache_zone_messages
        self.batch_threshold = batch_threshold

    def compress(
        self,
        history: list[Message],
        max_tokens: int,
        usage_ratio: float | None = None,
    ) -> tuple[list[Message], CacheStats]:
        """Compress history with cache-aware strategy.

        Args:
            history: Conversation history
            max_tokens: Maximum context window tokens
            usage_ratio: Current usage ratio (calculated if None)

        Returns:
            (compressed_history, cache_stats)
        """
        if not history:
            return history, CacheStats()

        # Calculate usage ratio if not provided
        if usage_ratio is None:
            usage_ratio = _calculate_usage_ratio(history, max_tokens)

        # Batch threshold: don't compress until we reach the threshold
        if usage_ratio < self.batch_threshold:
            logger.debug(
                f"Cache-aware: Usage {usage_ratio:.2%} below threshold {self.batch_threshold:.2%}, skipping compression"
            )
            return history, CacheStats(
                cache_zone_size=len(history),
                compressible_zone_size=0,
                messages_modified=0,
                compression_strategy="batch_threshold_not_reached",
                estimated_cache_hit=CACHE_HIT_STABLE,
            )

        # Identify cache-friendly zone
        cache_zone_end = self._identify_cache_zone(history)

        # Calculate initial tokens
        initial_tokens = sum(msg.token_count for msg in history)

        # Apply cache-aware compression
        compressed, stats = self._apply_cache_aware_compression(
            history, cache_zone_end, max_tokens
        )

        # Calculate final tokens
        final_tokens = sum(msg.token_count for msg in compressed)
        stats.tokens_saved = initial_tokens - final_tokens

        return compressed, stats

    def _identify_cache_zone(self, history: list[Message]) -> int:
        """Identify the end index of the cache-friendly zone.

        The cache zone is the first N messages that should be preserved
        to maximize cache hit rate.

        Args:
            history: Conversation history

        Returns:
            End index of cache zone (exclusive)
        """
        if not history:
            return 0

        # Calculate cache zone size based on ratio
        ratio_based_size = int(len(history) * self.cache_zone_ratio)

        # Ensure minimum size
        cache_zone_size = max(ratio_based_size, self.min_cache_zone_messages)

        # Don't exceed history length
        cache_zone_size = min(cache_zone_size, len(history))

        # Ensure we leave room for compression (at least 2 messages)
        if len(history) - cache_zone_size < 2:
            cache_zone_size = max(0, len(history) - 2)

        logger.debug(
            f"Cache zone: {cache_zone_size} / {len(history)} messages "
            f"({cache_zone_size / len(history):.1%})"
        )

        return cache_zone_size

    def _apply_cache_aware_compression(
        self,
        history: list[Message],
        cache_zone_end: int,
        max_tokens: int,
    ) -> tuple[list[Message], CacheStats]:
        """Apply cache-aware compression outside the cache zone.

        Strategy:
        1. Keep cache zone (first N messages) completely unchanged
        2. Apply microcompact only to messages after cache zone
        3. If still over limit, apply budget_reduction to compressible zone
        4. Never insert new messages at the beginning

        Args:
            history: Conversation history
            cache_zone_end: End index of cache zone
            max_tokens: Maximum context window tokens

        Returns:
            (compressed_history, cache_stats)
        """
        if cache_zone_end >= len(history):
            # Entire history is cache zone, no compression possible
            return history, CacheStats(
                cache_zone_size=len(history),
                compressible_zone_size=0,
                messages_modified=0,
                cache_zone_preserved=True,
                compression_strategy="cache_zone_only",
                estimated_cache_hit=CACHE_HIT_STABLE,
            )

        # Split into cache zone and compressible zone
        cache_zone = history[:cache_zone_end]
        compressible_zone = history[cache_zone_end:]

        initial_tokens = sum(msg.token_count for msg in compressible_zone)
        messages_modified = 0

        # Strategy 1: Microcompact compressible zone only
        compressed_zone = microcompact(compressible_zone, keep_recent=3)
        messages_modified = sum(1 for msg in compressed_zone if msg.compressed)

        # Check if compression was sufficient
        new_tokens = sum(msg.token_count for msg in compressed_zone)
        total_tokens = sum(msg.token_count for msg in cache_zone) + new_tokens
        usage_ratio = total_tokens / max_tokens

        # Strategy 2: If still over limit, apply budget_reduction
        if usage_ratio >= COMPRESSION_THRESHOLDS["auto_compact"]:
            compressed_zone = budget_reduction(compressed_zone)
            messages_modified += sum(1 for msg in compressed_zone if msg.compressed)
            logger.debug("Cache-aware: Applied budget_reduction to compressible zone")

        # Strategy 3: If still over limit, apply snip to compressible zone
        # (but keep at least 2 messages in compressible zone)
        new_tokens = sum(msg.token_count for msg in compressed_zone)
        total_tokens = sum(msg.token_count for msg in cache_zone) + new_tokens
        usage_ratio = total_tokens / max_tokens

        if usage_ratio >= COMPRESSION_THRESHOLDS["auto_compact"] and len(compressed_zone) > 2:
            # Keep only the last 3 messages in compressible zone
            compressed_zone = compressed_zone[-3:]
            messages_modified += len(compressible_zone) - 3
            logger.debug("Cache-aware: Applied snip to compressible zone (kept last 3)")

        # Reconstruct history: cache zone + compressed zone
        result = cache_zone + compressed_zone

        # Determine cache hit estimate
        if messages_modified == 0:
            estimated_hit = CACHE_HIT_STABLE
        elif messages_modified < len(compressible_zone) * 0.5:
            estimated_hit = CACHE_HIT_PARTIAL
        else:
            estimated_hit = CACHE_HIT_INVALIDATED

        stats = CacheStats(
            cache_zone_size=len(cache_zone),
            compressible_zone_size=len(compressible_zone),
            messages_modified=messages_modified,
            cache_zone_preserved=True,  # Always preserve cache zone
            compression_strategy="cache_aware",
            estimated_cache_hit=estimated_hit,
        )

        logger.debug(
            f"Cache-aware compression: "
            f"cache_zone={len(cache_zone)}, "
            f"compressed_zone={len(compressed_zone)}, "
            f"modified={messages_modified}, "
            f"cache_hit={estimated_hit}"
        )

        return result, stats


def cache_aware_compress(
    history: list[Message],
    max_tokens: int,
    cache_zone_ratio: float = DEFAULT_CACHE_ZONE_RATIO,
) -> tuple[list[Message], CacheStats]:
    """Convenience function for cache-aware compression.

    Args:
        history: Conversation history
        max_tokens: Maximum context window tokens
        cache_zone_ratio: Ratio of messages to keep in cache zone

    Returns:
        (compressed_history, cache_stats)
    """
    compressor = CacheAwareCompressor(cache_zone_ratio=cache_zone_ratio)
    return compressor.compress(history, max_tokens)
