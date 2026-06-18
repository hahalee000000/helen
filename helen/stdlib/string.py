"""String module for Helen stdlib.

Provides regex, text analysis, encoding, and string operations.
"""

from __future__ import annotations

import base64
import html
import re
import string as _string_module
from typing import Any


# ── Regex operations ───────────────────────────────────────────


def _regex_match(pattern: str, s: str) -> dict[str, Any] | None:
    """Match pattern at the beginning of string.

    Args:
        pattern: Regex pattern
        s: Input string

    Returns:
        Dict with 'match', 'groups', 'start', 'end' if matched, None otherwise

    Raises:
        ValueError: If pattern is invalid
    """
    try:
        m = re.match(pattern, s)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e

    if m is None:
        return None

    return {
        "match": m.group(0),
        "groups": m.groups() if m.groups() else (),
        "start": m.start(),
        "end": m.end(),
    }


def _regex_search(pattern: str, s: str) -> dict[str, Any] | None:
    """Search for pattern anywhere in string.

    Args:
        pattern: Regex pattern
        s: Input string

    Returns:
        Dict with 'match', 'groups', 'start', 'end' if found, None otherwise

    Raises:
        ValueError: If pattern is invalid
    """
    try:
        m = re.search(pattern, s)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e

    if m is None:
        return None

    return {
        "match": m.group(0),
        "groups": m.groups() if m.groups() else (),
        "start": m.start(),
        "end": m.end(),
    }


def _regex_replace(pattern: str, s: str, replacement: str) -> str:
    """Replace all occurrences of pattern in string.

    Args:
        pattern: Regex pattern
        s: Input string
        replacement: Replacement string (supports \\1, \\2 for groups)

    Returns:
        String with replacements made

    Raises:
        ValueError: If pattern is invalid
    """
    try:
        return re.sub(pattern, replacement, s)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e


def _regex_split(pattern: str, s: str) -> list[str]:
    """Split string by regex pattern.

    Args:
        pattern: Regex pattern to split on
        s: Input string

    Returns:
        List of string parts

    Raises:
        ValueError: If pattern is invalid
    """
    try:
        return re.split(pattern, s)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e


def _regex_findall(pattern: str, s: str) -> list[str]:
    """Find all occurrences of pattern in string.

    Args:
        pattern: Regex pattern
        s: Input string

    Returns:
        List of all matches

    Raises:
        ValueError: If pattern is invalid
    """
    try:
        return re.findall(pattern, s)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e


# ── Text analysis operations ───────────────────────────────────


def _tokenize(text: str) -> list[str]:
    """Simple word tokenization.

    Args:
        text: Input text

    Returns:
        List of word tokens
    """
    return re.findall(r"\w+", text)


def _word_count(text: str) -> dict[str, int]:
    """Count word frequencies in text (case-insensitive).

    Args:
        text: Input text

    Returns:
        Dict mapping words to their counts
    """
    words = re.findall(r"\w+", text.lower())
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    return counts


def _levenshtein(s1: str, s2: str) -> int:
    """Calculate Levenshtein (edit) distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Number of edits needed to transform s1 into s2
    """
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost is 0 if characters match, 1 otherwise
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _similarity(s1: str, s2: str) -> float:
    """Calculate string similarity (0.0 to 1.0).

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score (1.0 = identical, 0.0 = completely different)
    """
    if s1 == s2:
        return 1.0

    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0

    distance = _levenshtein(s1, s2)
    return 1.0 - (distance / max_len)


def _remove_punctuation(text: str) -> str:
    """Remove all punctuation from text.

    Args:
        text: Input text

    Returns:
        Text with punctuation removed
    """
    return text.translate(str.maketrans("", "", _string_module.punctuation))


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces, strip edges.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    return re.sub(r"\s+", " ", text).strip()


def _extract_urls(text: str) -> list[str]:
    """Extract all URLs from text.

    Args:
        text: Input text

    Returns:
        List of URLs found in text
    """
    url_pattern = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
    return re.findall(url_pattern, text)


def _extract_emails(text: str) -> list[str]:
    """Extract all email addresses from text.

    Args:
        text: Input text

    Returns:
        List of email addresses found in text
    """
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return re.findall(email_pattern, text)


# ── Encoding operations ────────────────────────────────────────


def _base64_encode(s: str) -> str:
    """Base64 encode a string.

    Args:
        s: Input string

    Returns:
        Base64 encoded string
    """
    return base64.b64encode(s.encode("utf-8")).decode("utf-8")


def _base64_decode(s: str) -> str:
    """Base64 decode a string.

    Args:
        s: Base64 encoded string

    Returns:
        Decoded string

    Raises:
        ValueError: If input is not valid base64
    """
    try:
        return base64.b64decode(s.encode("utf-8")).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Invalid base64 input: {e}") from e


def _html_escape(s: str) -> str:
    """Escape HTML special characters.

    Args:
        s: Input string

    Returns:
        HTML-escaped string
    """
    return html.escape(s, quote=True)


def _html_unescape(s: str) -> str:
    """Unescape HTML entities.

    Args:
        s: HTML-escaped string

    Returns:
        Unescaped string
    """
    return html.unescape(s)


# ── String operations ──────────────────────────────────────────


def _repeat(s: str, n: int) -> str:
    """Repeat string n times.

    Args:
        s: Input string
        n: Number of repetitions

    Returns:
        Repeated string
    """
    return s * n


def _reverse(s: str) -> str:
    """Reverse a string.

    Args:
        s: Input string

    Returns:
        Reversed string
    """
    return s[::-1]


def _pad_left(s: str, width: int, char: str = " ") -> str:
    """Pad string on the left to reach desired width.

    Args:
        s: Input string
        width: Desired width
        char: Padding character (default: space)

    Returns:
        Left-padded string
    """
    if len(s) >= width:
        return s
    return char[0] * (width - len(s)) + s


def _pad_right(s: str, width: int, char: str = " ") -> str:
    """Pad string on the right to reach desired width.

    Args:
        s: Input string
        width: Desired width
        char: Padding character (default: space)

    Returns:
        Right-padded string
    """
    if len(s) >= width:
        return s
    return s + char[0] * (width - len(s))


def _center(s: str, width: int, char: str = " ") -> str:
    """Center string in a field of given width.

    Args:
        s: Input string
        width: Desired width
        char: Padding character (default: space)

    Returns:
        Centered string
    """
    if len(s) >= width:
        return s
    return s.center(width, char[0])


def _count(s: str, sub: str) -> int:
    """Count non-overlapping occurrences of substring.

    Args:
        s: Input string
        sub: Substring to count

    Returns:
        Number of occurrences
    """
    return s.count(sub)


def _index(s: str, sub: str) -> int:
    """Find index of substring, raise error if not found.

    Args:
        s: Input string
        sub: Substring to find

    Returns:
        Index of first occurrence

    Raises:
        ValueError: If substring not found
    """
    idx = s.find(sub)
    if idx == -1:
        raise ValueError(f"Substring '{sub}' not found in '{s}'")
    return idx
