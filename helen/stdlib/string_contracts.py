"""String module contracts for Helen stdlib.

Defines interfaces for regex, text analysis, encoding, and string operations.
"""

from typing import Any


class StringRegexContract:
    """Contract for regex operations."""

    @staticmethod
    def regex_match(pattern: str, s: str) -> dict[str, Any] | None:
        """Match pattern at the beginning of string.

        Args:
            pattern: Regex pattern
            s: Input string

        Returns:
            Dict with 'match', 'groups', 'start', 'end' if matched, None otherwise

        Raises:
            ValueError: If pattern is invalid
        """
        ...

    @staticmethod
    def regex_search(pattern: str, s: str) -> dict[str, Any] | None:
        """Search for pattern anywhere in string.

        Args:
            pattern: Regex pattern
            s: Input string

        Returns:
            Dict with 'match', 'groups', 'start', 'end' if found, None otherwise

        Raises:
            ValueError: If pattern is invalid
        """
        ...

    @staticmethod
    def regex_replace(pattern: str, s: str, replacement: str) -> str:
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
        ...

    @staticmethod
    def regex_split(pattern: str, s: str) -> list[str]:
        """Split string by regex pattern.

        Args:
            pattern: Regex pattern to split on
            s: Input string

        Returns:
            List of string parts

        Raises:
            ValueError: If pattern is invalid
        """
        ...

    @staticmethod
    def regex_findall(pattern: str, s: str) -> list[str]:
        """Find all occurrences of pattern in string.

        Args:
            pattern: Regex pattern
            s: Input string

        Returns:
            List of all matches

        Raises:
            ValueError: If pattern is invalid
        """
        ...


class StringTextAnalysisContract:
    """Contract for text analysis operations."""

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Simple word tokenization.

        Args:
            text: Input text

        Returns:
            List of word tokens
        """
        ...

    @staticmethod
    def word_count(text: str) -> dict[str, int]:
        """Count word frequencies in text.

        Args:
            text: Input text

        Returns:
            Dict mapping words to their counts
        """
        ...

    @staticmethod
    def levenshtein(s1: str, s2: str) -> int:
        """Calculate Levenshtein (edit) distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Number of edits needed to transform s1 into s2
        """
        ...

    @staticmethod
    def similarity(s1: str, s2: str) -> float:
        """Calculate string similarity (0.0 to 1.0).

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score (1.0 = identical, 0.0 = completely different)
        """
        ...

    @staticmethod
    def remove_punctuation(text: str) -> str:
        """Remove all punctuation from text.

        Args:
            text: Input text

        Returns:
            Text with punctuation removed
        """
        ...

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace: collapse multiple spaces, strip edges.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        ...

    @staticmethod
    def extract_urls(text: str) -> list[str]:
        """Extract all URLs from text.

        Args:
            text: Input text

        Returns:
            List of URLs found in text
        """
        ...

    @staticmethod
    def extract_emails(text: str) -> list[str]:
        """Extract all email addresses from text.

        Args:
            text: Input text

        Returns:
            List of email addresses found in text
        """
        ...


class StringEncodingContract:
    """Contract for encoding operations."""

    @staticmethod
    def base64_encode(s: str) -> str:
        """Base64 encode a string.

        Args:
            s: Input string

        Returns:
            Base64 encoded string
        """
        ...

    @staticmethod
    def base64_decode(s: str) -> str:
        """Base64 decode a string.

        Args:
            s: Base64 encoded string

        Returns:
            Decoded string

        Raises:
            ValueError: If input is not valid base64
        """
        ...

    @staticmethod
    def html_escape(s: str) -> str:
        """Escape HTML special characters.

        Args:
            s: Input string

        Returns:
            HTML-escaped string
        """
        ...

    @staticmethod
    def html_unescape(s: str) -> str:
        """Unescape HTML entities.

        Args:
            s: HTML-escaped string

        Returns:
            Unescaped string
        """
        ...


class StringOpsContract:
    """Contract for additional string operations."""

    @staticmethod
    def repeat(s: str, n: int) -> str:
        """Repeat string n times.

        Args:
            s: Input string
            n: Number of repetitions

        Returns:
            Repeated string
        """
        ...

    @staticmethod
    def reverse(s: str) -> str:
        """Reverse a string.

        Args:
            s: Input string

        Returns:
            Reversed string
        """
        ...

    @staticmethod
    def pad_left(s: str, width: int, char: str = " ") -> str:
        """Pad string on the left to reach desired width.

        Args:
            s: Input string
            width: Desired width
            char: Padding character (default: space)

        Returns:
            Left-padded string
        """
        ...

    @staticmethod
    def pad_right(s: str, width: int, char: str = " ") -> str:
        """Pad string on the right to reach desired width.

        Args:
            s: Input string
            width: Desired width
            char: Padding character (default: space)

        Returns:
            Right-padded string
        """
        ...

    @staticmethod
    def center(s: str, width: int, char: str = " ") -> str:
        """Center string in a field of given width.

        Args:
            s: Input string
            width: Desired width
            char: Padding character (default: space)

        Returns:
            Centered string
        """
        ...

    @staticmethod
    def count(s: str, sub: str) -> int:
        """Count non-overlapping occurrences of substring.

        Args:
            s: Input string
            sub: Substring to count

        Returns:
            Number of occurrences
        """
        ...

    @staticmethod
    def index(s: str, sub: str) -> int:
        """Find index of substring, raise error if not found.

        Args:
            s: Input string
            sub: Substring to find

        Returns:
            Index of first occurrence

        Raises:
            ValueError: If substring not found
        """
        ...
