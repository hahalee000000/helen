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
