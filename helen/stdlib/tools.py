"""Helen Standard Library — Tool wrappers.

Wraps Python tools from helen.runtime.tools so they can be called from Helen code.
This allows agent functions to use built-in tools like web_search, read_file, etc.
"""

from __future__ import annotations

import json
from typing import Any


def _web_search(query: str, num_results: int = 3) -> str:
    """Search the web and return results.

    Args:
        query: Search query string
        num_results: Number of results to return (default 3)

    Returns:
        JSON string with search results
    """
    from helen.runtime.tools import _web_search as py_web_search
    return py_web_search(query, num_results)


def _web_fetch(url: str) -> str:
    """Fetch the text content of a URL.

    Args:
        url: URL to fetch

    Returns:
        JSON string with URL and content
    """
    from helen.runtime.tools import _web_fetch as py_web_fetch
    return py_web_fetch(url)


def _read_file(path: str) -> str:
    """Read the content of a local file.

    Args:
        path: File path to read

    Returns:
        JSON string with path and content
    """
    from helen.runtime.tools import _read_file as py_read_file
    return py_read_file(path)


def _write_file(path: str, content: str) -> str:
    """Write content to a local file.

    Args:
        path: File path to write
        content: Content to write

    Returns:
        JSON string with path, bytes_written, and status
    """
    from helen.runtime.tools import _write_file as py_write_file
    return py_write_file(path, content)


def _shell_exec(command: str, timeout: int = 30, shell: bool = True) -> str:
    """Execute a shell command and return output.

    Args:
        command: Command to execute
        timeout: Timeout in seconds (default 30)
        shell: Whether to use shell execution (default True for full shell syntax support)

    Returns:
        JSON string with command, exit_code, and output
    """
    from helen.runtime.tools import _shell_exec as py_shell_exec
    return py_shell_exec(command, timeout, shell)


def _calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Args:
        expression: Math expression to evaluate

    Returns:
        JSON string with expression and result
    """
    from helen.runtime.tools import _calculate as py_calculate
    return py_calculate(expression)


def _patch_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Patch a file using fuzzy matching.

    Args:
        path: File path to patch
        old_string: Text to find and replace
        new_string: Replacement text
        replace_all: Replace all occurrences (default False)

    Returns:
        JSON string with patch result
    """
    from helen.runtime.tools import _patch_file as py_patch_file
    return py_patch_file(path, old_string, new_string, replace_all)


def _load_skill(name: str) -> str:
    """Load a skill's full SKILL.md content by name.

    Args:
        name: Skill name to load

    Returns:
        JSON string with skill content
    """
    from helen.runtime.tools import _load_skill as py_load_skill
    return py_load_skill(name)

