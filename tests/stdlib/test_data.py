"""Tests for Data stdlib module.

Tests JSON, HTML, Markdown, CSV operations.
"""

import pytest
import tempfile
import os
from helen.stdlib.data import (
    # JSON
    _json_parse, _json_stringify, _json_load, _json_save,
    # HTML
    _html_parse, _html_text, _html_links, _html_select,
    # Markdown
    _markdown_to_html, _markdown_extract_headings, _markdown_parse,
    # CSV
    _csv_parse, _csv_stringify, _csv_load, _csv_save,
)


# ── JSON Tests ─────────────────────────────────────────────────


class TestJsonParse:
    """Tests for json_parse."""

    def test_parse_object(self):
        result = _json_parse('{"name": "Alice", "age": 30}')
        assert result == {"name": "Alice", "age": 30}

    def test_parse_array(self):
        result = _json_parse('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_parse_string(self):
        result = _json_parse('"hello"')
        assert result == "hello"

    def test_parse_number(self):
        result = _json_parse('42')
        assert result == 42

    def test_parse_boolean(self):
        assert _json_parse('true') is True
        assert _json_parse('false') is False

    def test_parse_null(self):
        assert _json_parse('null') is None

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            _json_parse('not valid json')


class TestJsonStringify:
    """Tests for json_stringify."""

    def test_stringify_dict(self):
        result = _json_stringify({"name": "Alice", "age": 30})
        assert '"name"' in result
        assert '"Alice"' in result

    def test_stringify_list(self):
        result = _json_stringify([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_stringify_with_indent(self):
        result = _json_stringify({"a": 1}, indent=2)
        assert "\n" in result
        assert "  " in result

    def test_stringify_nested(self):
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        result = _json_stringify(data)
        assert '"users"' in result


class TestJsonLoadSave:
    """Tests for json_load and json_save."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            data = {"name": "Alice", "age": 30}

            _json_save(path, data)
            loaded = _json_load(path)

            assert loaded == data

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _json_load("/nonexistent/path.json")

    def test_save_with_indent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            data = {"a": 1, "b": 2}

            _json_save(path, data, indent=2)
            content = _json_load(path)

            assert content == data


# ── HTML Tests ─────────────────────────────────────────────────


class TestHtmlParse:
    """Tests for html_parse."""

    def test_parse_simple(self):
        result = _html_parse("<p>Hello</p>")
        assert result is not None

    def test_parse_nested(self):
        result = _html_parse("<div><p>Hello</p></div>")
        assert result is not None


class TestHtmlText:
    """Tests for html_text."""

    def test_extract_text(self):
        result = _html_text("<p>Hello <b>World</b></p>")
        assert "Hello" in result
        assert "World" in result

    def test_strip_tags(self):
        result = _html_text("<div><p>Text</p></div>")
        assert result.strip() == "Text"


class TestHtmlLinks:
    """Tests for html_links."""

    def test_extract_links(self):
        html = '<a href="http://example.com">Link</a>'
        result = _html_links(html)
        assert "http://example.com" in result

    def test_multiple_links(self):
        html = '<a href="http://a.com">A</a><a href="http://b.com">B</a>'
        result = _html_links(html)
        assert len(result) == 2

    def test_no_links(self):
        result = _html_links("<p>No links here</p>")
        assert result == []


class TestHtmlSelect:
    """Tests for html_select."""

    def test_select_by_tag(self):
        html = "<p>One</p><div>Two</div><p>Three</p>"
        result = _html_select(html, "p")
        assert len(result) == 2
        assert result[0]["tag"] == "p"
        assert result[0]["text"] == "One"
        assert result[1]["text"] == "Three"

    def test_select_by_class(self):
        html = '<p class="intro">Hello</p><p class="body">World</p>'
        result = _html_select(html, ".intro")
        assert len(result) == 1
        assert result[0]["text"] == "Hello"

    def test_select_by_id(self):
        html = '<div id="main">Content</div><div id="side">Other</div>'
        result = _html_select(html, "#main")
        assert len(result) == 1
        assert result[0]["text"] == "Content"

    def test_select_by_attribute(self):
        html = '<input type="text" /><input type="hidden" />'
        result = _html_select(html, "[type]")
        assert len(result) == 2

    def test_select_by_attribute_value(self):
        html = '<input type="text" /><input type="hidden" />'
        result = _html_select(html, "[type=hidden]")
        assert len(result) == 1
        assert result[0]["attrs"]["type"] == "hidden"

    def test_select_tag_and_class(self):
        html = '<p class="a">One</p><div class="a">Two</div>'
        result = _html_select(html, "p.a")
        assert len(result) == 1
        assert result[0]["tag"] == "p"

    def test_select_no_match(self):
        html = "<p>Hello</p>"
        result = _html_select(html, "div")
        assert result == []

    def test_select_empty_selector_raises(self):
        with pytest.raises(ValueError):
            _html_select("<p>Hi</p>", "")

    def test_select_preserves_attrs(self):
        html = '<a href="http://x.com" class="link">Click</a>'
        result = _html_select(html, "a")
        assert len(result) == 1
        assert result[0]["attrs"]["href"] == "http://x.com"
        assert result[0]["attrs"]["class"] == "link"


# ── Markdown Tests ─────────────────────────────────────────────


class TestMarkdownToHtml:
    """Tests for markdown_to_html."""

    def test_heading(self):
        result = _markdown_to_html("# Hello")
        assert "<h1>" in result
        assert "Hello" in result

    def test_paragraph(self):
        result = _markdown_to_html("Hello world")
        assert "<p>" in result

    def test_bold(self):
        result = _markdown_to_html("**bold**")
        assert "<strong>" in result or "<b>" in result


class TestMarkdownExtractHeadings:
    """Tests for markdown_extract_headings."""

    def test_extract_h1(self):
        md = "# Heading 1\n\nSome text"
        result = _markdown_extract_headings(md)
        assert len(result) >= 1
        assert result[0]["level"] == 1
        assert "Heading 1" in result[0]["text"]

    def test_extract_multiple(self):
        md = "# H1\n\n## H2\n\n### H3"
        result = _markdown_extract_headings(md)
        assert len(result) >= 3

    def test_no_headings(self):
        md = "Just plain text"
        result = _markdown_extract_headings(md)
        assert result == []


class TestMarkdownParse:
    """Tests for markdown_parse."""

    def test_parse_heading(self):
        md = "# Hello World"
        result = _markdown_parse(md)
        assert len(result) == 1
        assert result[0]["type"] == "heading"
        assert result[0]["level"] == 1
        assert result[0]["text"] == "Hello World"

    def test_parse_multiple_headings(self):
        md = "# H1\n\n## H2\n\n### H3"
        result = _markdown_parse(md)
        assert len(result) == 3
        assert result[0]["level"] == 1
        assert result[1]["level"] == 2
        assert result[2]["level"] == 3

    def test_parse_paragraph(self):
        md = "This is a paragraph.\nSecond line."
        result = _markdown_parse(md)
        assert len(result) == 1
        assert result[0]["type"] == "paragraph"
        assert "paragraph" in result[0]["text"]

    def test_parse_code_block(self):
        md = "```python\nprint('hello')\n```"
        result = _markdown_parse(md)
        assert len(result) == 1
        assert result[0]["type"] == "code_block"
        assert result[0]["language"] == "python"
        assert "print" in result[0]["text"]

    def test_parse_code_block_no_lang(self):
        md = "```\nsome code\n```"
        result = _markdown_parse(md)
        assert result[0]["type"] == "code_block"
        assert result[0]["language"] == ""

    def test_parse_unordered_list(self):
        md = "- item one\n- item two\n- item three"
        result = _markdown_parse(md)
        assert len(result) == 1
        assert result[0]["type"] == "list"
        assert result[0]["ordered"] is False
        assert len(result[0]["items"]) == 3

    def test_parse_ordered_list(self):
        md = "1. first\n2. second\n3. third"
        result = _markdown_parse(md)
        assert len(result) == 1
        assert result[0]["type"] == "list"
        assert result[0]["ordered"] is True
        assert len(result[0]["items"]) == 3

    def test_parse_blockquote(self):
        md = "> This is a quote\n> Second line"
        result = _markdown_parse(md)
        assert len(result) == 1
        assert result[0]["type"] == "blockquote"
        assert "quote" in result[0]["text"]

    def test_parse_horizontal_rule(self):
        md = "---"
        result = _markdown_parse(md)
        assert len(result) == 1
        assert result[0]["type"] == "hr"

    def test_parse_mixed(self):
        md = "# Title\n\nA paragraph.\n\n- item\n\n> quote\n\n---"
        result = _markdown_parse(md)
        types = [b["type"] for b in result]
        assert types == ["heading", "paragraph", "list", "blockquote", "hr"]

    def test_parse_empty(self):
        result = _markdown_parse("")
        assert result == []


# ── CSV Tests ──────────────────────────────────────────────────


class TestCsvParse:
    """Tests for csv_parse."""

    def test_parse_simple(self):
        result = _csv_parse("a,b,c\n1,2,3")
        assert result == [["a", "b", "c"], ["1", "2", "3"]]

    def test_parse_with_quotes(self):
        result = _csv_parse('a,"b,c",d')
        assert result == [["a", "b,c", "d"]]

    def test_parse_custom_delimiter(self):
        result = _csv_parse("a;b;c", delimiter=";")
        assert result == [["a", "b", "c"]]


class TestCsvStringify:
    """Tests for csv_stringify."""

    def test_stringify_simple(self):
        rows = [["a", "b"], ["1", "2"]]
        result = _csv_stringify(rows)
        assert "a,b" in result
        assert "1,2" in result

    def test_stringify_with_quotes(self):
        rows = [["a", "b,c"]]
        result = _csv_stringify(rows)
        assert '"b,c"' in result


class TestCsvLoadSave:
    """Tests for csv_load and csv_save."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.csv")
            rows = [["name", "age"], ["Alice", "30"]]

            _csv_save(path, rows)
            loaded = _csv_load(path)

            assert loaded == rows

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _csv_load("/nonexistent/path.csv")
