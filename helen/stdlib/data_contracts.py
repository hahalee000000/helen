"""Data module contracts for Helen stdlib.

Defines interfaces for JSON, HTML, Markdown, CSV, YAML/TOML operations.
"""

from __future__ import annotations

from typing import Any


class JsonContract:
    """Contract for JSON operations."""

    @staticmethod
    def json_parse(text: str) -> Any:
        """Parse JSON string into Python object.

        Args:
            text: JSON string

        Returns:
            Parsed Python object (dict, list, str, int, float, bool, None)

        Raises:
            ValueError: If JSON is invalid
        """
        ...

    @staticmethod
    def json_stringify(value: Any, indent: int | None = None) -> str:
        """Convert Python object to JSON string.

        Args:
            value: Python object to serialize
            indent: Optional indentation level for pretty printing

        Returns:
            JSON string

        Raises:
            TypeError: If value is not JSON serializable
        """
        ...

    @staticmethod
    def json_load(path: str) -> Any:
        """Load JSON from file.

        Args:
            path: File path

        Returns:
            Parsed Python object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid
        """
        ...

    @staticmethod
    def json_save(path: str, value: Any, indent: int | None = None) -> str:
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
        ...


class HtmlContract:
    """Contract for HTML operations."""

    @staticmethod
    def html_parse(text: str) -> Any:
        """Parse HTML text into DOM-like structure.

        Args:
            text: HTML string

        Returns:
            Parsed HTML object

        Raises:
            ValueError: If HTML is malformed
        """
        ...

    @staticmethod
    def html_select(html_text: str, selector: str) -> list[Any]:
        """Select elements using CSS selector.

        Args:
            html_text: HTML string
            selector: CSS selector

        Returns:
            List of matching elements

        Raises:
            ValueError: If selector is invalid
        """
        ...

    @staticmethod
    def html_text(html_text: str) -> str:
        """Extract text content from HTML.

        Args:
            html_text: HTML string

        Returns:
            Plain text content
        """
        ...

    @staticmethod
    def html_links(html_text: str) -> list[str]:
        """Extract all links from HTML.

        Args:
            html_text: HTML string

        Returns:
            List of URLs
        """
        ...


class MarkdownContract:
    """Contract for Markdown operations."""

    @staticmethod
    def markdown_parse(text: str) -> Any:
        """Parse Markdown text.

        Args:
            text: Markdown string

        Returns:
            Parsed Markdown object
        """
        ...

    @staticmethod
    def markdown_to_html(text: str) -> str:
        """Convert Markdown to HTML.

        Args:
            text: Markdown string

        Returns:
            HTML string
        """
        ...

    @staticmethod
    def markdown_extract_headings(text: str) -> list[dict[str, Any]]:
        """Extract headings from Markdown.

        Args:
            text: Markdown string

        Returns:
            List of dicts with 'level', 'text', 'id'
        """
        ...


class CsvContract:
    """Contract for CSV operations."""

    @staticmethod
    def csv_parse(text: str, delimiter: str = ",") -> list[list[str]]:
        """Parse CSV text.

        Args:
            text: CSV string
            delimiter: Field delimiter (default: comma)

        Returns:
            List of rows (each row is a list of strings)
        """
        ...

    @staticmethod
    def csv_stringify(rows: list[list[str]], delimiter: str = ",") -> str:
        """Convert rows to CSV string.

        Args:
            rows: List of rows
            delimiter: Field delimiter (default: comma)

        Returns:
            CSV string
        """
        ...

    @staticmethod
    def csv_load(path: str, delimiter: str = ",") -> list[list[str]]:
        """Load CSV from file.

        Args:
            path: File path
            delimiter: Field delimiter

        Returns:
            List of rows

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    @staticmethod
    def csv_save(path: str, rows: list[list[str]], delimiter: str = ",") -> str:
        """Save rows to CSV file.

        Args:
            path: File path
            rows: List of rows
            delimiter: Field delimiter

        Returns:
            Success message
        """
        ...
