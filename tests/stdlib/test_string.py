"""Tests for String stdlib module.

Tests regex, text analysis, encoding, and string operations.
"""

import pytest
from helen.stdlib.string import (
    # Regex
    _regex_match, _regex_search, _regex_replace, _regex_split, _regex_findall,
    # Text analysis
    _tokenize, _word_count, _levenshtein, _similarity,
    _remove_punctuation, _normalize_whitespace, _extract_urls, _extract_emails,
    # Encoding
    _base64_encode, _base64_decode, _html_escape, _html_unescape,
    # String ops
    _repeat, _reverse, _pad_left, _pad_right, _center, _count, _index,
)


# ── Regex Tests ────────────────────────────────────────────────


class TestRegexMatch:
    """Tests for regex_match."""

    def test_match_at_start(self):
        result = _regex_match(r"hello", "hello world")
        assert result is not None
        assert result["match"] == "hello"
        assert result["start"] == 0
        assert result["end"] == 5

    def test_no_match(self):
        result = _regex_match(r"world", "hello world")
        assert result is None

    def test_match_with_groups(self):
        result = _regex_match(r"(\w+)\s(\w+)", "hello world")
        assert result is not None
        assert result["groups"] == ("hello", "world")

    def test_invalid_pattern(self):
        with pytest.raises(ValueError):
            _regex_match(r"[invalid", "test")


class TestRegexSearch:
    """Tests for regex_search."""

    def test_search_anywhere(self):
        result = _regex_search(r"world", "hello world")
        assert result is not None
        assert result["match"] == "world"
        assert result["start"] == 6

    def test_search_not_found(self):
        result = _regex_search(r"xyz", "hello world")
        assert result is None

    def test_search_with_groups(self):
        result = _regex_search(r"(\d+)", "abc 123 def")
        assert result is not None
        assert result["match"] == "123"
        assert result["groups"] == ("123",)


class TestRegexReplace:
    """Tests for regex_replace."""

    def test_basic_replace(self):
        result = _regex_replace(r"\d+", "abc 123 def 456", "NUM")
        assert result == "abc NUM def NUM"

    def test_replace_with_groups(self):
        result = _regex_replace(r"(\w+)@(\w+)", "user@host", r"\1 at \2")
        assert result == "user at host"

    def test_no_match(self):
        result = _regex_replace(r"\d+", "hello", "NUM")
        assert result == "hello"


class TestRegexSplit:
    """Tests for regex_split."""

    def test_basic_split(self):
        result = _regex_split(r"\s+", "hello   world  foo")
        assert result == ["hello", "world", "foo"]

    def test_split_by_comma(self):
        result = _regex_split(r",\s*", "a, b, c, d")
        assert result == ["a", "b", "c", "d"]

    def test_no_match(self):
        result = _regex_split(r"\d+", "hello")
        assert result == ["hello"]


class TestRegexFindall:
    """Tests for regex_findall."""

    def test_find_all_numbers(self):
        result = _regex_findall(r"\d+", "abc 123 def 456 ghi 789")
        assert result == ["123", "456", "789"]

    def test_find_all_words(self):
        result = _regex_findall(r"\w+", "hello world")
        assert result == ["hello", "world"]

    def test_no_matches(self):
        result = _regex_findall(r"\d+", "hello world")
        assert result == []


# ── Text Analysis Tests ────────────────────────────────────────


class TestTokenize:
    """Tests for tokenize."""

    def test_basic_tokenize(self):
        result = _tokenize("Hello, world! How are you?")
        assert result == ["Hello", "world", "How", "are", "you"]

    def test_empty_string(self):
        result = _tokenize("")
        assert result == []

    def test_multiple_spaces(self):
        result = _tokenize("hello   world")
        assert result == ["hello", "world"]


class TestWordCount:
    """Tests for word_count."""

    def test_basic_count(self):
        result = _word_count("hello world hello")
        assert result == {"hello": 2, "world": 1}

    def test_case_insensitive(self):
        result = _word_count("Hello hello HELLO")
        assert result == {"hello": 3}

    def test_empty_string(self):
        result = _word_count("")
        assert result == {}


class TestLevenshtein:
    """Tests for levenshtein distance."""

    def test_identical(self):
        assert _levenshtein("hello", "hello") == 0

    def test_one_edit(self):
        assert _levenshtein("hello", "hallo") == 1

    def test_insertion(self):
        assert _levenshtein("hell", "hello") == 1

    def test_deletion(self):
        assert _levenshtein("hello", "hell") == 1

    def test_completely_different(self):
        assert _levenshtein("abc", "xyz") == 3

    def test_empty_strings(self):
        assert _levenshtein("", "") == 0
        assert _levenshtein("hello", "") == 5
        assert _levenshtein("", "hello") == 5


class TestSimilarity:
    """Tests for similarity."""

    def test_identical(self):
        assert _similarity("hello", "hello") == 1.0

    def test_completely_different(self):
        assert _similarity("abc", "xyz") == 0.0

    def test_similar(self):
        score = _similarity("hello", "hallo")
        assert 0.7 < score < 1.0

    def test_empty_strings(self):
        assert _similarity("", "") == 1.0


class TestRemovePunctuation:
    """Tests for remove_punctuation."""

    def test_basic(self):
        result = _remove_punctuation("Hello, world!")
        assert result == "Hello world"

    def test_no_punctuation(self):
        result = _remove_punctuation("hello world")
        assert result == "hello world"

    def test_all_punctuation(self):
        result = _remove_punctuation("!@#$%^&*()")
        assert result == ""


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace."""

    def test_multiple_spaces(self):
        result = _normalize_whitespace("hello   world")
        assert result == "hello world"

    def test_tabs_and_newlines(self):
        result = _normalize_whitespace("hello\t\tworld\n\nfoo")
        assert result == "hello world foo"

    def test_leading_trailing(self):
        result = _normalize_whitespace("  hello world  ")
        assert result == "hello world"


class TestExtractUrls:
    """Tests for extract_urls."""

    def test_extract_http(self):
        result = _extract_urls("Visit http://example.com for more")
        assert result == ["http://example.com"]

    def test_extract_https(self):
        result = _extract_urls("Go to https://example.com/path?q=1")
        assert result == ["https://example.com/path?q=1"]

    def test_multiple_urls(self):
        result = _extract_urls("See http://a.com and https://b.com")
        assert len(result) == 2

    def test_no_urls(self):
        result = _extract_urls("no urls here")
        assert result == []


class TestExtractEmails:
    """Tests for extract_emails."""

    def test_extract_email(self):
        result = _extract_emails("Contact user@example.com for info")
        assert result == ["user@example.com"]

    def test_multiple_emails(self):
        result = _extract_emails("a@b.com and c@d.org")
        assert len(result) == 2

    def test_no_emails(self):
        result = _extract_emails("no emails here")
        assert result == []


# ── Encoding Tests ─────────────────────────────────────────────


class TestBase64:
    """Tests for base64 encode/decode."""

    def test_encode(self):
        result = _base64_encode("Hello, World!")
        assert result == "SGVsbG8sIFdvcmxkIQ=="

    def test_decode(self):
        result = _base64_decode("SGVsbG8sIFdvcmxkIQ==")
        assert result == "Hello, World!"

    def test_roundtrip(self):
        original = "测试中文 🎉"
        encoded = _base64_encode(original)
        decoded = _base64_decode(encoded)
        assert decoded == original

    def test_decode_invalid(self):
        with pytest.raises(ValueError):
            _base64_decode("not valid base64!!!")


class TestHtmlEscape:
    """Tests for html_escape/unescape."""

    def test_escape(self):
        result = _html_escape('<script>alert("xss")</script>')
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&quot;" in result

    def test_unescape(self):
        result = _html_unescape("&lt;b&gt;bold&lt;/b&gt;")
        assert result == "<b>bold</b>"

    def test_roundtrip(self):
        original = '<a href="test?a=1&b=2">link</a>'
        escaped = _html_escape(original)
        unescaped = _html_unescape(escaped)
        assert unescaped == original


# ── String Ops Tests ───────────────────────────────────────────


class TestRepeat:
    """Tests for repeat."""

    def test_basic(self):
        assert _repeat("ab", 3) == "ababab"

    def test_zero(self):
        assert _repeat("hello", 0) == ""

    def test_one(self):
        assert _repeat("hello", 1) == "hello"


class TestReverse:
    """Tests for reverse."""

    def test_basic(self):
        assert _reverse("hello") == "olleh"

    def test_empty(self):
        assert _reverse("") == ""

    def test_palindrome(self):
        assert _reverse("racecar") == "racecar"


class TestPadLeft:
    """Tests for pad_left."""

    def test_basic(self):
        assert _pad_left("42", 5, "0") == "00042"

    def test_default_char(self):
        assert _pad_left("hi", 5) == "   hi"

    def test_no_padding_needed(self):
        assert _pad_left("hello", 3) == "hello"


class TestPadRight:
    """Tests for pad_right."""

    def test_basic(self):
        assert _pad_right("hi", 5) == "hi   "

    def test_custom_char(self):
        assert _pad_right("42", 5, "0") == "42000"


class TestCenter:
    """Tests for center."""

    def test_basic(self):
        result = _center("hi", 6)
        assert result == "  hi  "

    def test_odd_padding(self):
        result = _center("hi", 7, "-")
        assert result == "---hi--"  # Python center puts extra on right


class TestCount:
    """Tests for count."""

    def test_basic(self):
        assert _count("hello world hello", "hello") == 2

    def test_no_match(self):
        assert _count("hello world", "xyz") == 0

    def test_overlapping(self):
        # Non-overlapping count
        assert _count("aaa", "aa") == 1


class TestIndex:
    """Tests for index."""

    def test_found(self):
        assert _index("hello world", "world") == 6

    def test_not_found(self):
        with pytest.raises(ValueError):
            _index("hello world", "xyz")

    def test_first_occurrence(self):
        assert _index("abcabc", "bc") == 1
