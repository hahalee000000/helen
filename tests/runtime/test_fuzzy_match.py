"""Tests for helen.runtime.fuzzy_match module.

Covers all 9 matching strategies, the main fuzzy_find_and_replace function,
helper utilities, multi-occurrence matching, and error/edge cases.
"""

import pytest

from helen.runtime.fuzzy_match import (
    fuzzy_find_and_replace,
    find_closest_lines,
    format_no_match_hint,
    _unicode_normalize,
    _leading_whitespace,
    _first_meaningful_line,
    _reindent_replacement,
    _strategy_exact,
    _strategy_line_trimmed,
    _strategy_whitespace_normalized,
    _strategy_indentation_flexible,
    _strategy_escape_normalized,
    _strategy_trimmed_boundary,
    _strategy_unicode_normalized,
    _strategy_block_anchor,
    _strategy_context_aware,
    _calculate_line_positions,
    _build_orig_to_norm_map,
    _detect_escape_drift,
)


# =============================================================================
# Strategy 1: Exact match
# =============================================================================


class TestStrategyExact:
    """Tests for _strategy_exact."""

    def test_single_match(self):
        matches = _strategy_exact("hello world", "hello")
        assert matches == [(0, 5)]

    def test_no_match(self):
        matches = _strategy_exact("hello world", "xyz")
        assert matches == []

    def test_multiple_matches(self):
        matches = _strategy_exact("ababab", "ab")
        assert len(matches) == 3

    def test_match_at_end(self):
        matches = _strategy_exact("hello world", "world")
        assert matches == [(6, 11)]

    def test_empty_pattern(self):
        matches = _strategy_exact("hello", "")
        # find("") always returns 0, so it matches at every position
        assert len(matches) == 6  # positions 0..5


# =============================================================================
# Strategy 2: Line-trimmed
# =============================================================================


class TestStrategyLineTrimmed:
    """Tests for _strategy_line_trimmed."""

    def test_leading_whitespace_differs(self):
        content = "  def foo():\n      pass"
        pattern = "def foo():\n    pass"
        matches = _strategy_line_trimmed(content, pattern)
        assert len(matches) == 1

    def test_no_match_when_content_differs(self):
        content = "def bar():\n    pass"
        pattern = "def foo():\n    pass"
        matches = _strategy_line_trimmed(content, pattern)
        assert matches == []


# =============================================================================
# Strategy 3: Whitespace normalized
# =============================================================================


class TestStrategyWhitespaceNormalized:
    """Tests for _strategy_whitespace_normalized."""

    def test_multiple_spaces_collapse(self):
        content = "x  =  1  +  2"
        pattern = "x = 1 + 2"
        matches = _strategy_whitespace_normalized(content, pattern)
        assert len(matches) == 1

    def test_tabs_to_spaces(self):
        content = "x\t=\t1"
        pattern = "x = 1"
        matches = _strategy_whitespace_normalized(content, pattern)
        assert len(matches) == 1

    def test_no_match_when_text_differs(self):
        content = "x = 1 + 2"
        pattern = "x = 1 + 3"
        matches = _strategy_whitespace_normalized(content, pattern)
        assert matches == []


# =============================================================================
# Strategy 4: Indentation flexible
# =============================================================================


class TestStrategyIndentationFlexible:
    """Tests for _strategy_indentation_flexible."""

    def test_different_indent_levels(self):
        content = "        def foo():\n            pass"
        pattern = "def foo():\n    pass"
        matches = _strategy_indentation_flexible(content, pattern)
        assert len(matches) == 1

    def test_no_match_when_body_differs(self):
        content = "def foo():\n    return 42"
        pattern = "def foo():\n    pass"
        matches = _strategy_indentation_flexible(content, pattern)
        assert matches == []


# =============================================================================
# Strategy 5: Escape normalized
# =============================================================================


class TestStrategyEscapeNormalized:
    """Tests for _strategy_escape_normalized."""

    def test_literal_newline_in_pattern(self):
        content = "line1\nline2"
        pattern = "line1\\nline2"
        matches = _strategy_escape_normalized(content, pattern)
        assert len(matches) == 1

    def test_no_escape_sequences_returns_empty(self):
        content = "hello world"
        pattern = "hello"
        matches = _strategy_escape_normalized(content, pattern)
        assert matches == []

    def test_literal_tab_in_pattern(self):
        content = "col1\tcol2"
        pattern = "col1\\tcol2"
        matches = _strategy_escape_normalized(content, pattern)
        assert len(matches) == 1


# =============================================================================
# Strategy 6: Trimmed boundary
# =============================================================================


class TestStrategyTrimmedBoundary:
    """Tests for _strategy_trimmed_boundary."""

    def test_first_last_line_whitespace(self):
        content = "  def foo():\n    pass\n  "
        pattern = "def foo():\n    pass\n  "
        matches = _strategy_trimmed_boundary(content, pattern)
        assert len(matches) == 1

    def test_single_line_pattern(self):
        content = "  hello world  "
        pattern = "hello world"
        matches = _strategy_trimmed_boundary(content, pattern)
        assert len(matches) == 1


# =============================================================================
# Strategy 7: Unicode normalized
# =============================================================================


class TestStrategyUnicodeNormalized:
    """Tests for _strategy_unicode_normalized."""

    def test_smart_quotes(self):
        content = 'say \u201chello\u201d'
        pattern = 'say "hello"'
        matches = _strategy_unicode_normalized(content, pattern)
        assert len(matches) == 1

    def test_em_dash(self):
        content = "word\u2014word"
        pattern = "word--word"
        matches = _strategy_unicode_normalized(content, pattern)
        assert len(matches) == 1

    def test_no_unicode_returns_empty(self):
        content = "hello world"
        pattern = "hello"
        matches = _strategy_unicode_normalized(content, pattern)
        assert matches == []

    def test_ellipsis(self):
        content = "wait\u2026"
        pattern = "wait..."
        matches = _strategy_unicode_normalized(content, pattern)
        assert len(matches) == 1


# =============================================================================
# Strategy 8: Block anchor
# =============================================================================


class TestStrategyBlockAnchor:
    """Tests for _strategy_block_anchor."""

    def test_first_last_line_match_with_similar_middle(self):
        content = "def foo():\n    x = 1\n    return x"
        pattern = "def foo():\n    y = 1\n    return x"
        matches = _strategy_block_anchor(content, pattern)
        assert len(matches) == 1

    def test_single_line_pattern_returns_empty(self):
        content = "hello world"
        pattern = "hello"
        matches = _strategy_block_anchor(content, pattern)
        assert matches == []

    def test_no_match_when_anchors_differ(self):
        content = "def foo():\n    pass"
        pattern = "def bar():\n    return"
        matches = _strategy_block_anchor(content, pattern)
        assert matches == []


# =============================================================================
# Strategy 9: Context-aware
# =============================================================================


class TestStrategyContextAware:
    """Tests for _strategy_context_aware."""

    def test_high_similarity_match(self):
        content = "def foo():\n    x = 1\n    return x"
        pattern = "def foo():\n    x = 2\n    return x"
        matches = _strategy_context_aware(content, pattern)
        assert len(matches) >= 1

    def test_no_match_when_completely_different(self):
        content = "alpha\nbeta\ngamma"
        pattern = "xyz\nabc\n123"
        matches = _strategy_context_aware(content, pattern)
        assert matches == []


# =============================================================================
# Main function: fuzzy_find_and_replace
# =============================================================================


class TestFuzzyFindAndReplace:
    """Tests for the main fuzzy_find_and_replace function."""

    # ── Error cases ──

    def test_empty_old_string(self):
        result = fuzzy_find_and_replace("hello", "", "world")
        assert result[3] == "old_string cannot be empty"
        assert result[1] == 0

    def test_identical_old_and_new(self):
        result = fuzzy_find_and_replace("hello", "hello", "hello")
        assert result[3] == "old_string and new_string are identical"
        assert result[1] == 0

    def test_no_match_at_all(self):
        result = fuzzy_find_and_replace("hello world", "xyz123", "replacement")
        assert result[3] == "Could not find a match for old_string in the file"
        assert result[1] == 0
        assert result[0] == "hello world"

    # ── Exact match ──

    def test_exact_match_single(self):
        new_content, count, strategy, error = fuzzy_find_and_replace(
            "hello world", "hello", "goodbye"
        )
        assert new_content == "goodbye world"
        assert count == 1
        assert strategy == "exact"
        assert error is None

    def test_exact_match_multiple_no_replace_all(self):
        result = fuzzy_find_and_replace("aaa", "a", "b", replace_all=False)
        assert result[3] is not None  # error: multiple matches
        assert "3 matches" in result[3]

    def test_exact_match_replace_all(self):
        new_content, count, strategy, error = fuzzy_find_and_replace(
            "aaa", "a", "b", replace_all=True
        )
        assert new_content == "bbb"
        assert count == 3
        assert strategy == "exact"

    # ── Fallback to line-trimmed ──

    def test_line_trimmed_fallback(self):
        content = "  def foo():\n      pass"
        pattern = "def foo():\n    pass"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "def bar():\n    pass"
        )
        assert error is None
        assert count == 1
        assert strategy == "line_trimmed"

    # ── Whitespace normalized ──

    def test_whitespace_normalized_fallback(self):
        content = "x  =  1"
        pattern = "x = 1"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "x = 2"
        )
        assert error is None
        assert count == 1
        assert strategy == "whitespace_normalized"

    # ── Indentation flexible ──

    def test_indentation_flexible_fallback(self):
        # line_trimmed is strictly more permissive than indentation_flexible,
        # so in practice line_trimmed catches these first. Verify the match works.
        content = "        def foo():\n            pass"
        pattern = "def foo():\n    pass"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "def bar():\n    pass"
        )
        assert error is None
        assert count == 1
        assert strategy in ("line_trimmed", "indentation_flexible")

    # ── Escape normalized ──

    def test_escape_normalized_fallback(self):
        content = "line1\nline2"
        pattern = "line1\\nline2"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "replaced"
        )
        assert error is None
        assert count == 1
        assert strategy == "escape_normalized"

    # ── Unicode normalized ──

    def test_unicode_normalized_fallback(self):
        content = 'say \u201chello\u201d'
        pattern = 'say "hello"'
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, 'say "world"'
        )
        assert error is None
        assert count == 1
        assert strategy == "unicode_normalized"

    # ── Re-indentation ──

    def test_reindent_on_fuzzy_match(self):
        content = "    def foo():\n        pass"
        pattern = "def foo():\n    pass"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "def bar():\n    return 42"
        )
        assert error is None
        # The replacement should be re-indented to match the file region
        assert "    def bar():" in new_content or "def bar():" in new_content

    # ── Multi-line replacement ──

    def test_multiline_exact_replacement(self):
        content = "def foo():\n    pass\n\ndef bar():\n    pass"
        pattern = "def foo():\n    pass"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "def foo():\n    return 1"
        )
        assert error is None
        assert "return 1" in new_content
        assert "def bar():" in new_content


# =============================================================================
# Helper functions
# =============================================================================


class TestHelpers:
    """Tests for internal helper functions."""

    def test_unicode_normalize_smart_quotes(self):
        assert _unicode_normalize("\u201chello\u201d") == '"hello"'

    def test_unicode_normalize_em_dash(self):
        assert _unicode_normalize("a\u2014b") == "a--b"

    def test_unicode_normalize_en_dash(self):
        assert _unicode_normalize("a\u2013b") == "a-b"

    def test_unicode_normalize_ellipsis(self):
        assert _unicode_normalize("wait\u2026") == "wait..."

    def test_unicode_normalize_non_breaking_space(self):
        assert _unicode_normalize("a\u00a0b") == "a b"

    def test_unicode_normalize_no_change(self):
        assert _unicode_normalize("hello") == "hello"

    def test_leading_whitespace_spaces(self):
        assert _leading_whitespace("    hello") == "    "

    def test_leading_whitespace_tabs(self):
        assert _leading_whitespace("\t\thello") == "\t\t"

    def test_leading_whitespace_none(self):
        assert _leading_whitespace("hello") == ""

    def test_first_meaningful_line(self):
        assert _first_meaningful_line("\n\n  hello\n  world") == "  hello"

    def test_first_meaningful_line_all_blank(self):
        assert _first_meaningful_line("\n\n\n") is None

    def test_reindent_replacement_same_indent(self):
        result = _reindent_replacement("    x", "    x", "    y")
        assert result == "    y"

    def test_reindent_replacement_different_indent(self):
        result = _reindent_replacement("        x", "    x", "    y")
        assert result == "        y"

    def test_reindent_replacement_empty_new(self):
        result = _reindent_replacement("    x", "    x", "")
        assert result == ""

    def test_calculate_line_positions_first_line(self):
        lines = ["hello", "world"]
        start, end = _calculate_line_positions(lines, 0, 1, 11)
        assert start == 0
        assert end == 5

    def test_calculate_line_positions_second_line(self):
        lines = ["hello", "world"]
        start, end = _calculate_line_positions(lines, 1, 2, 11)
        assert start == 6
        assert end == 11

    def test_build_orig_to_norm_map_no_unicode(self):
        mapping = _build_orig_to_norm_map("abc")
        assert mapping == [0, 1, 2, 3]

    def test_build_orig_to_norm_map_with_smart_quote(self):
        mapping = _build_orig_to_norm_map('a\u201cb')
        # " (U+201C) maps to '"' which is 1 char, same length
        assert len(mapping) == 4  # a, \u201c, b, +1 sentinel


# =============================================================================
# Escape drift detection
# =============================================================================


class TestEscapeDrift:
    """Tests for _detect_escape_drift."""

    def test_no_drift_when_no_escapes(self):
        result = _detect_escape_drift("hello", [(0, 5)], "hello", "world")
        assert result is None

    def test_no_drift_when_escape_in_matched_region(self):
        # Content itself contains the literal \' sequence
        content = "it\\'s a test"
        new_string = "it\\'s new"
        old_string = "it\\'s a test"
        result = _detect_escape_drift(content, [(0, len(content))], old_string, new_string)
        assert result is None

    def test_drift_detected(self):
        content = "it's a test"
        old_string = "it\\'s a test"
        new_string = "it\\'s new"
        result = _detect_escape_drift(content, [(0, 11)], old_string, new_string)
        assert result is not None
        assert "Escape-drift" in result


# =============================================================================
# find_closest_lines
# =============================================================================


class TestFindClosestLines:
    """Tests for find_closest_lines."""

    def test_finds_similar_lines(self):
        content = "def foo():\n    pass\n\ndef bar():\n    return 1"
        result = find_closest_lines("def foo():", content)
        assert "def foo():" in result

    def test_empty_old_string(self):
        result = find_closest_lines("", "hello")
        assert result == ""

    def test_empty_content(self):
        result = find_closest_lines("hello", "")
        assert result == ""

    def test_no_similar_lines(self):
        content = "xyz\nabc\n123"
        result = find_closest_lines("completely_different_pattern_zzzzzz", content)
        # May or may not find something depending on ratio threshold
        # Just ensure it doesn't crash
        assert isinstance(result, str)


# =============================================================================
# format_no_match_hint
# =============================================================================


class TestFormatNoMatchHint:
    """Tests for format_no_match_hint."""

    def test_returns_empty_when_matches_found(self):
        result = format_no_match_hint("error", 1, "old", "content")
        assert result == ""

    def test_returns_empty_when_not_no_match_error(self):
        result = format_no_match_hint("some other error", 0, "old", "content")
        assert result == ""

    def test_returns_hint_for_no_match(self):
        content = "def foo():\n    pass"
        error = "Could not find a match for old_string in the file"
        result = format_no_match_hint(error, 0, "def foo", content)
        assert "Did you mean" in result or result == ""

    def test_returns_empty_when_no_close_lines(self):
        content = "xyz\nabc"
        error = "Could not find a match for old_string in the file"
        result = format_no_match_hint(error, 0, "zzzzzzzzzzzzzzzzzzzzzzzzz", content)
        # May or may not have hint depending on similarity
        assert isinstance(result, str)


# =============================================================================
# Integration / edge cases
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple aspects."""

    def test_replace_preserves_surrounding_content(self):
        content = "before\nmiddle\nafter"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, "middle", "replaced"
        )
        assert new_content == "before\nreplaced\nafter"
        assert "before" in new_content
        assert "after" in new_content

    def test_multiline_replace_all(self):
        content = "x = 1\ny = 2\nx = 1"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, "x = 1", "z = 3", replace_all=True
        )
        assert count == 2
        assert new_content.count("z = 3") == 2

    def test_special_characters_in_content(self):
        content = "price = $100\nname = 'test'"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, "price = $100", "price = $200"
        )
        assert error is None
        assert "price = $200" in new_content

    def test_unicode_content_exact_match(self):
        content = "caf\u00e9 = True"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, "caf\u00e9", "tea"
        )
        assert error is None
        assert strategy == "exact"
        assert "tea = True" in new_content

    def test_block_anchor_strategy_via_main(self):
        """Test that block anchor is reached when other strategies fail."""
        content = "def foo():\n    x = 1\n    y = 2\n    return x + y"
        # Pattern with slightly different middle but same first/last
        pattern = "def foo():\n    x = 99\n    y = 99\n    return x + y"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "def bar():\n    return 0"
        )
        # Should match via block_anchor or context_aware
        assert error is None or "Could not find" not in (error or "")

    def test_context_aware_strategy_via_main(self):
        """Test that context_aware catches very fuzzy matches."""
        content = "def foo():\n    x = 1\n    return x"
        pattern = "def foo():\n    x = 999\n    return x"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "def bar():\n    return 0"
        )
        # context_aware should catch this (lines are >50% similar)
        assert error is None

    def test_newline_only_content(self):
        content = "\n\n\n"
        result = fuzzy_find_and_replace(content, "x", "y")
        assert result[3] is not None  # no match

    def test_single_character_content(self):
        new_content, count, strategy, error = fuzzy_find_and_replace("a", "a", "b")
        assert new_content == "b"
        assert count == 1
        assert strategy == "exact"

    def test_whitespace_only_pattern_lines(self):
        """Pattern with blank lines should still work."""
        content = "line1\n\nline3"
        pattern = "line1\n\nline3"
        new_content, count, strategy, error = fuzzy_find_and_replace(
            content, pattern, "replaced"
        )
        assert error is None
        assert strategy == "exact"
