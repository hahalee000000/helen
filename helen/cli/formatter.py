"""Error/Warning report formatter (HLD 3.11.2).

Formats HelenError and HelenWarning with SourceSpan into
human-readable diagnostics with source context and position indicators.

Format (HLD 3.11.2):
    Error: [ERR_CODE] description
      --> file:line:column
       |
    line |     source line
       |     ^^^^ position indicator
       |
      = detail and suggestion
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from helen.core.errors import HelenError, HelenWarning  # noqa: F401
    from helen.core.source import SourceSpan  # noqa: F401


def format_error(error: "HelenError", source_lines: list[str] | None = None) -> str:
    """Format a HelenError into HLD 3.11.2 diagnostic output.

    Args:
        error: The error to format.
        source_lines: Optional source code lines for context display.

    Returns:
        Formatted error string.
    """
    return _format_diagnostic("Error", error, source_lines)


def format_warning(warning: "HelenWarning", source_lines: list[str] | None = None) -> str:
    """Format a HelenWarning into HLD 3.11.2 diagnostic output.

    Args:
        warning: The warning to format.
        source_lines: Optional source code lines for context display.

    Returns:
        Formatted warning string.
    """
    return _format_diagnostic("Warning", warning, source_lines)


def _format_diagnostic(
    label: str,
    diagnostic: "HelenError | HelenWarning",
    source_lines: list[str] | None = None,
) -> str:
    """Format a diagnostic (error or warning) with source context.

    Args:
        label: "Error" or "Warning".
        diagnostic: The diagnostic to format.
        source_lines: Optional source code lines.

    Returns:
        Formatted diagnostic string.
    """
    parts: list[str] = []

    # Header: Error: [ERR_CODE] description
    code = diagnostic.code.value
    parts.append(f"{label}: [{label[0]}{code:04d}] {diagnostic.message}")

    span = diagnostic.span
    if span is not None:
        # Location: --> file:line:column
        parts.append(f"  --> {span.file}:{span.start_line}:{span.start_col}")

        # Source context
        if source_lines and 0 < span.start_line <= len(source_lines):
            line_text = source_lines[span.start_line - 1]
            # Line number
            parts.append("   |")
            parts.append(f"{span.start_line} | {line_text}")

            # Position indicator
            caret_start = span.start_col - 1
            caret_end = span.end_col - 1 if span.end_col > span.start_col else caret_start + 1
            caret_line = " " * (caret_start) + "^" * max(caret_end - caret_start, 1)
            parts.append(f"   | {caret_line}")
            parts.append("   |")

    # Detail suggestion
    parts.append(f"  = {diagnostic.message}")

    return "\n".join(parts)
