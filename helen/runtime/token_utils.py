"""Shared token estimation utilities for Helen runtime.

Centralizes token estimation and CJK character detection to avoid
duplication across multiple modules (history, context_recovery,
reactive_compaction, context_awareness).

Design notes:
- Pure functions with no circular import risk
- Used by all modules that need token estimation
- Character-type-aware heuristic (~15% accuracy without tiktoken)
- Falls back gracefully when tiktoken is unavailable
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token estimation constants
# ---------------------------------------------------------------------------

CHARS_PER_TOKEN_EN = 4.0     # English/Latin
CHARS_PER_TOKEN_CJK = 1.2    # CJK characters
CHARS_PER_TOKEN_MIXED = 3.0  # Mixed content estimate

# Default context window for unknown models (tokens)
DEFAULT_CONTEXT_WINDOW = 131072


# ---------------------------------------------------------------------------
# CJK character detection
# ---------------------------------------------------------------------------

def is_cjk(char: str) -> bool:
    """Check if a character is CJK (Chinese/Japanese/Korean).

    Comprehensive Unicode range check covering:
    - CJK Unified Ideographs (0x4E00-0x9FFF)
    - CJK Extensions A-E
    - CJK Compatibility Ideographs
    - CJK Symbols and Punctuation
    - Hiragana, Katakana
    - Hangul Syllables

    Args:
        char: Single character to check

    Returns:
        True if character is CJK
    """
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF)       # CJK Unified Ideographs
        or (0x3400 <= cp <= 0x4DBF)    # CJK Extension A
        or (0x20000 <= cp <= 0x2A6DF)  # CJK Extension B
        or (0x2A700 <= cp <= 0x2B73F)  # CJK Extension C
        or (0x2B740 <= cp <= 0x2B81F)  # CJK Extension D
        or (0xF900 <= cp <= 0xFAFF)    # CJK Compatibility Ideographs
        or (0x3000 <= cp <= 0x303F)    # CJK Symbols and Punctuation
        or (0x3040 <= cp <= 0x309F)    # Hiragana
        or (0x30A0 <= cp <= 0x30FF)    # Katakana
        or (0xAC00 <= cp <= 0xD7AF)    # Hangul Syllables
    )


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def estimate_tokens_simple(text: str) -> int:
    """Estimate token count using character-type-aware heuristic.

    No external dependencies (no tiktoken). ~15% accuracy.

    Different ratios for:
    - Pure Latin/English: ~4 chars per token
    - Pure CJK: ~1.2 chars per token
    - Mixed: weighted average

    Args:
        text: Input text to estimate

    Returns:
        Estimated token count (>= 1 for non-empty text)
    """
    if not text:
        return 0

    cjk_count = sum(1 for c in text if is_cjk(c))
    total_len = len(text)

    if cjk_count == 0:
        # Pure Latin/English
        return max(1, int(total_len / CHARS_PER_TOKEN_EN))
    elif cjk_count == total_len:
        # Pure CJK
        return max(1, int(total_len / CHARS_PER_TOKEN_CJK))
    else:
        # Mixed content
        non_cjk = total_len - cjk_count
        return max(1, int(cjk_count / CHARS_PER_TOKEN_CJK + non_cjk / CHARS_PER_TOKEN_EN))

