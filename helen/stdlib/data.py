"""Data module for Helen stdlib.

Provides JSON, HTML, Markdown, CSV parsing and generation.
"""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any


# ── JSON operations ────────────────────────────────────────────


def _json_parse(text: str) -> Any:
    """Parse JSON string into Python object.

    Args:
        text: JSON string

    Returns:
        Parsed Python object (dict, list, str, int, float, bool, None)

    Raises:
        ValueError: If JSON is invalid
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def _json_stringify(value: Any, indent: int | None = None) -> str:
    """Convert Python object to JSON string.

    Args:
        value: Python object to serialize
        indent: Optional indentation level for pretty printing

    Returns:
        JSON string

    Raises:
        TypeError: If value is not JSON serializable
    """
    try:
        return json.dumps(value, indent=indent, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise TypeError(f"Cannot serialize to JSON: {e}") from e


def _json_load(path: str) -> Any:
    """Load JSON from file.

    Args:
        path: File path

    Returns:
        Parsed Python object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file: {e}") from e


def _json_save(path: str, value: Any, indent: int | None = None) -> str:
    """Save Python object to JSON file.

    Args:
        path: File path
        value: Python object to serialize
        indent: Optional indentation level

    Returns:
        Success message

    Raises:
        TypeError: If value is not JSON serializable
    """
    import pathlib

    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=indent, ensure_ascii=False)
        return f"Saved JSON to {path}"
    except (TypeError, ValueError) as e:
        raise TypeError(f"Cannot serialize to JSON: {e}") from e


# ── HTML operations ────────────────────────────────────────────


def _html_parse(text: str) -> dict[str, Any]:
    """Parse HTML text into simple structure.

    Args:
        text: HTML string

    Returns:
        Dict with 'tag', 'attrs', 'children', 'text'
    """
    # Simple regex-based parser for basic HTML
    tag_match = re.match(r"<(\w+)([^>]*)>(.*)</\1>", text, re.DOTALL)
    if tag_match:
        tag = tag_match.group(1)
        attrs_str = tag_match.group(2)
        content = tag_match.group(3)

        # Parse attributes
        attrs = {}
        for attr_match in re.finditer(r'(\w+)="([^"]*)"', attrs_str):
            attrs[attr_match.group(1)] = attr_match.group(2)

        return {
            "tag": tag,
            "attrs": attrs,
            "children": [],
            "text": content,
        }

    return {"tag": "text", "attrs": {}, "children": [], "text": text}


def _html_text(html_text: str) -> str:
    """Extract text content from HTML.

    Args:
        html_text: HTML string

    Returns:
        Plain text content
    """
    # Remove all HTML tags
    text = re.sub(r"<[^>]+>", "", html_text)
    # Decode common HTML entities
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return text.strip()


def _html_links(html_text: str) -> list[str]:
    """Extract all links from HTML.

    Args:
        html_text: HTML string

    Returns:
        List of URLs
    """
    # Find all href attributes
    return re.findall(r'href="([^"]+)"', html_text)


def _html_select(html_text: str, selector: str) -> list[dict[str, Any]]:
    """Select elements using CSS selector.

    Supports basic CSS selectors:
    - Tag name: ``div``, ``p``, ``a``
    - Class: ``.classname``
    - ID: ``#id``
    - Attribute: ``[attr]``, ``[attr=value]``
    - Combinations: ``div.class``, ``div#id[attr=val]``

    Args:
        html_text: HTML string
        selector: CSS selector

    Returns:
        List of matching elements as dicts with 'tag', 'attrs', 'text'

    Raises:
        ValueError: If selector is invalid or empty
    """
    if not selector or not selector.strip():
        raise ValueError("Selector cannot be empty")

    selector = selector.strip()

    # Parse selector into components
    tag_pattern = None
    id_value = None
    class_value = None
    attr_name = None
    attr_value = None

    # Extract attribute selector [attr] or [attr=value]
    attr_match = re.search(r'\[(\w+)(?:=["\']?([^"\']*)["\']?)?\]', selector)
    if attr_match:
        attr_name = attr_match.group(1)
        attr_value = attr_match.group(2)  # None if just [attr]
        selector = selector[:attr_match.start()] + selector[attr_match.end():]

    # Extract ID selector #id
    id_match = re.search(r'#([\w-]+)', selector)
    if id_match:
        id_value = id_match.group(1)
        selector = selector[:id_match.start()] + selector[id_match.end():]

    # Extract class selector .class
    class_match = re.search(r'\.([\w-]+)', selector)
    if class_match:
        class_value = class_match.group(1)
        selector = selector[:class_match.start()] + selector[class_match.end():]

    # Remaining is tag name
    remaining = selector.strip()
    if remaining:
        tag_pattern = remaining

    # Validate: at least one selector component must be present
    if not any([tag_pattern, id_value, class_value, attr_name]):
        raise ValueError(f"Invalid selector: '{selector}'")

    # Find all tags in HTML (both normal and self-closing)
    results = []
    # Match both <tag attrs>content</tag> and <tag attrs />
    tag_regex = r'<(\w+)([^>]*?)(?:/>|>(.*?)</\1>)'
    for tag_match in re.finditer(tag_regex, html_text, re.DOTALL):
        tag = tag_match.group(1)
        attrs_str = tag_match.group(2)
        content = tag_match.group(3) or ""

        # Parse attributes from the tag
        attrs: dict[str, str] = {}
        for a_match in re.finditer(r'([\w-]+)=["\']([^"\']*)["\']', attrs_str):
            attrs[a_match.group(1)] = a_match.group(2)
        # Also handle boolean attributes (no value)
        for a_match in re.finditer(r'\s([\w-]+)(?:\s|$)', attrs_str):
            attr_key = a_match.group(1)
            if attr_key not in attrs and '=' not in attrs_str.split(attr_key)[-1][:1]:
                attrs[attr_key] = ""

        # Check tag match
        if tag_pattern and tag != tag_pattern:
            continue

        # Check ID match
        if id_value and attrs.get("id") != id_value:
            continue

        # Check class match
        if class_value:
            classes = attrs.get("class", "").split()
            if class_value not in classes:
                continue

        # Check attribute match
        if attr_name is not None:
            if attr_name not in attrs:
                continue
            if attr_value is not None and attrs[attr_name] != attr_value:
                continue

        results.append({
            "tag": tag,
            "attrs": attrs,
            "text": content,
        })

    return results


# ── Markdown operations ────────────────────────────────────────


def _markdown_to_html(text: str) -> str:
    """Convert Markdown to HTML.

    Args:
        text: Markdown string

    Returns:
        HTML string
    """
    lines = text.split("\n")
    html_lines = []
    in_paragraph = False

    for line in lines:
        line = line.rstrip()

        # Headings
        if line.startswith("# "):
            if in_paragraph:
                html_lines.append("</p>")
                in_paragraph = False
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_paragraph:
                html_lines.append("</p>")
                in_paragraph = False
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_paragraph:
                html_lines.append("</p>")
                in_paragraph = False
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line == "":
            if in_paragraph:
                html_lines.append("</p>")
                in_paragraph = False
        else:
            if not in_paragraph:
                html_lines.append("<p>")
                in_paragraph = True
            # Bold
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            # Italic
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            # Code
            line = re.sub(r"`(.+?)`", r"<code>\1</code>", line)
            html_lines.append(line)

    if in_paragraph:
        html_lines.append("</p>")

    return "\n".join(html_lines)


def _markdown_extract_headings(text: str) -> list[dict[str, Any]]:
    """Extract headings from Markdown.

    Args:
        text: Markdown string

    Returns:
        List of dicts with 'level', 'text', 'id'
    """
    headings = []
    lines = text.split("\n")

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            text_content = match.group(2).strip()
            # Generate ID from text
            heading_id = re.sub(r"[^\w\s-]", "", text_content.lower())
            heading_id = re.sub(r"[-\s]+", "-", heading_id)

            headings.append({
                "level": level,
                "text": text_content,
                "id": heading_id,
            })

    return headings


def _markdown_parse(text: str) -> list[dict[str, Any]]:
    """Parse Markdown text into structured blocks.

    Recognizes: headings, paragraphs, code blocks (fenced),
    unordered lists, ordered lists, blockquotes, horizontal rules.

    Args:
        text: Markdown string

    Returns:
        List of block dicts. Each dict has a ``type`` key and
        type-specific keys:
        - ``heading``: ``{type, level, text}``
        - ``paragraph``: ``{type, text}``
        - ``code_block``: ``{type, language, text}``
        - ``list``: ``{type, ordered, items: [str]}``
        - ``blockquote``: ``{type, text}``
        - ``hr``: ``{type}``
    """
    lines = text.split("\n")
    blocks: list[dict[str, Any]] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank line — skip
        if not stripped:
            i += 1
            continue

        # Fenced code block (``` or ~~~)
        fence_match = re.match(r'^(`{3,}|~{3,})(\w*)', stripped)
        if fence_match:
            fence_char = fence_match.group(1)[0]
            fence_len = len(fence_match.group(1))
            language = fence_match.group(2) or ""
            code_lines: list[str] = []
            i += 1
            while i < n:
                close = re.match(
                    rf'^{re.escape(fence_char)}{{{fence_len},}}\s*$',
                    lines[i].strip(),
                )
                if close:
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "type": "code_block",
                "language": language,
                "text": "\n".join(code_lines),
            })
            continue

        # Horizontal rule (---, ***, ___)
        if re.match(r'^[-*_]{3,}\s*$', stripped) and len(set(stripped.replace(' ', ''))) == 1:
            blocks.append({"type": "hr"})
            i += 1
            continue

        # Heading (# ... ######)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            blocks.append({
                "type": "heading",
                "level": len(heading_match.group(1)),
                "text": heading_match.group(2).strip(),
            })
            i += 1
            continue

        # Blockquote (> ...)
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                content = re.sub(r'^>\s?', '', lines[i].strip())
                quote_lines.append(content)
                i += 1
            blocks.append({
                "type": "blockquote",
                "text": "\n".join(quote_lines),
            })
            continue

        # Unordered list (- or * or +)
        if re.match(r'^[-*+]\s+', stripped):
            items: list[str] = []
            while i < n and re.match(r'^\s*[-*+]\s+', lines[i]):
                item_text = re.sub(r'^\s*[-*+]\s+', '', lines[i])
                items.append(item_text)
                i += 1
            blocks.append({
                "type": "list",
                "ordered": False,
                "items": items,
            })
            continue

        # Ordered list (1. 2. etc.)
        if re.match(r'^\d+\.\s+', stripped):
            items = []
            while i < n and re.match(r'^\s*\d+\.\s+', lines[i]):
                item_text = re.sub(r'^\s*\d+\.\s+', '', lines[i])
                items.append(item_text)
                i += 1
            blocks.append({
                "type": "list",
                "ordered": True,
                "items": items,
            })
            continue

        # Paragraph (default — collect consecutive non-blank, non-special lines)
        para_lines: list[str] = []
        while i < n:
            l = lines[i]
            ls = l.strip()
            if not ls:
                break
            if re.match(r'^(#{1,6})\s+', ls):
                break
            if re.match(r'^(`{3,}|~{3,})', ls):
                break
            if re.match(r'^[-*_]{3,}\s*$', ls) and len(set(ls.replace(' ', ''))) == 1:
                break
            if ls.startswith(">"):
                break
            if re.match(r'^[-*+]\s+', ls):
                break
            if re.match(r'^\d+\.\s+', ls):
                break
            para_lines.append(ls)
            i += 1
        if para_lines:
            blocks.append({
                "type": "paragraph",
                "text": " ".join(para_lines),
            })

    return blocks


# ── CSV operations ─────────────────────────────────────────────


def _csv_parse(text: str, delimiter: str = ",") -> list[list[str]]:
    """Parse CSV text.

    Args:
        text: CSV string
        delimiter: Field delimiter (default: comma)

    Returns:
        List of rows (each row is a list of strings)
    """
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return list(reader)


def _csv_stringify(rows: list[list[str]], delimiter: str = ",") -> str:
    """Convert rows to CSV string.

    Args:
        rows: List of rows
        delimiter: Field delimiter (default: comma)

    Returns:
        CSV string
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)
    writer.writerows(rows)
    return output.getvalue()


def _csv_load(path: str, delimiter: str = ",") -> list[list[str]]:
    """Load CSV from file.

    Args:
        path: File path
        delimiter: Field delimiter

    Returns:
        List of rows

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            return list(reader)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")


def _csv_save(path: str, rows: list[list[str]], delimiter: str = ",") -> str:
    """Save rows to CSV file.

    Args:
        path: File path
        rows: List of rows
        delimiter: Field delimiter

    Returns:
        Success message
    """
    import pathlib

    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerows(rows)

    return f"Saved CSV to {path}"
