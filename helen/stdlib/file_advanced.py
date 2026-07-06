"""File advanced operations module for Helen stdlib.

Provides advanced file operations: info, copy, move, delete, temp files,
file search (glob and content search).
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


# ── File information operations ────────────────────────────────


def _file_size(path: str) -> int:
    """Get file size in bytes.

    Args:
        path: File path

    Returns:
        File size in bytes

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return os.path.getsize(path)


def _file_modified(path: str) -> str:
    """Get file modification time.

    Args:
        path: File path

    Returns:
        ISO 8601 formatted datetime string

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    mtime = os.path.getmtime(path)
    dt = datetime.fromtimestamp(mtime)
    return dt.isoformat(timespec="seconds")


def _list_dir(path: str, pattern: str | None = None) -> list[str]:
    """List directory contents.

    Args:
        path: Directory path
        pattern: Optional glob pattern to filter results

    Returns:
        List of file/directory names

    Raises:
        FileNotFoundError: If directory doesn't exist
        NotADirectoryError: If path is not a directory
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: {path}")

    if not os.path.isdir(path):
        raise NotADirectoryError(f"Not a directory: {path}")

    if pattern:
        return [p.name for p in Path(path).glob(pattern)]
    else:
        return os.listdir(path)


def _walk_dir(path: str) -> list[tuple[str, list[str], list[str]]]:
    """Walk directory tree.

    Args:
        path: Root directory path

    Returns:
        List of tuples (dirpath, dirnames, filenames)

    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: {path}")

    result = []
    for dirpath, dirnames, filenames in os.walk(path):
        result.append((dirpath, dirnames, filenames))
    return result


# ── File operations ────────────────────────────────────────────


def _copy_file(src: str, dst: str) -> str:
    """Copy file.

    Args:
        src: Source file path
        dst: Destination file path

    Returns:
        Success message

    Raises:
        FileNotFoundError: If source doesn't exist
    """
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source file not found: {src}")

    shutil.copy2(src, dst)
    return f"Copied {src} to {dst}"


def _move_file(src: str, dst: str) -> str:
    """Move file.

    Args:
        src: Source file path
        dst: Destination file path

    Returns:
        Success message

    Raises:
        FileNotFoundError: If source doesn't exist
    """
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source file not found: {src}")

    shutil.move(src, dst)
    return f"Moved {src} to {dst}"


def _delete_file(path: str) -> str:
    """Delete file.

    Args:
        path: File path

    Returns:
        Success message

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    os.remove(path)
    return f"Deleted file: {path}"


def _delete_dir(path: str, recursive: bool = False) -> str:
    """Delete directory.

    Args:
        path: Directory path
        recursive: If True, delete recursively

    Returns:
        Success message

    Raises:
        FileNotFoundError: If directory doesn't exist
        OSError: If directory is not empty and recursive is False
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: {path}")

    if recursive:
        shutil.rmtree(path)
    else:
        os.rmdir(path)

    return f"Deleted directory: {path}"


# ── Temporary file operations ──────────────────────────────────


def _temp_file(suffix: str = "", prefix: str = "tmp", dir: str | None = None) -> str:
    """Create temporary file.

    Args:
        suffix: File suffix
        prefix: File prefix
        dir: Directory for temporary file (default: system temp dir)

    Returns:
        Path to temporary file
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    os.close(fd)
    return path


def _temp_dir(suffix: str = "", prefix: str = "tmp", dir: str | None = None) -> str:
    """Create temporary directory.

    Args:
        suffix: Directory suffix
        prefix: Directory prefix
        dir: Directory for temporary directory (default: system temp dir)

    Returns:
        Path to temporary directory
    """
    return tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)


# ── File search operations ─────────────────────────────────────


def _glob_files(path: str, pattern: str = "**/*") -> list[str]:
    """Recursively find files matching a glob pattern.

    Args:
        path: Root directory to search
        pattern: Glob pattern (e.g. "*.py", "**/*.txt", "src/**/*.js")
                 Use "**" for recursive matching. Defaults to "**/*" (all files).

    Returns:
        List of matching file paths (relative to the search root)

    Raises:
        FileNotFoundError: If directory doesn't exist
        NotADirectoryError: If path is not a directory

    Examples:
        glob_files("src", "*.py")         # All .py files in src/ (recursive)
        glob_files(".", "*.txt")          # All .txt files (recursive)
        glob_files("docs", "**/*.md")     # All markdown files in docs/
        glob_files(".", "*test*")         # Files/dirs containing "test"
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: {path}")

    if not os.path.isdir(path):
        raise NotADirectoryError(f"Not a directory: {path}")

    # Convert Helen-style glob to Python pathlib pattern
    # Helen uses "**" for recursive, same as pathlib
    root_path = Path(path)

    # Use rglob for patterns without "/" (searches recursively)
    # Use glob for patterns with "/" (respects directory structure)
    if "**" in pattern or "/" not in pattern:
        # For simple patterns like "*.py" or "**/*.py", use rglob
        search_pattern = pattern.replace("**/", "")
        matches = root_path.rglob(search_pattern)
    else:
        # For complex patterns with directory structure
        matches = root_path.glob(pattern)

    # Return paths relative to the search root
    return [str(p.relative_to(root_path)) for p in matches if p.is_file()]


def _grep_files(path: str, pattern: str, regex: bool = False,
                case_sensitive: bool = True, max_results: int = 100) -> list[dict]:
    """Search file contents for a pattern.

    Args:
        path: File or directory to search
        pattern: Text or regex pattern to search for
        regex: If True, treat pattern as regex. If False, literal text. (default: False)
        case_sensitive: Case-sensitive search (default: True)
        max_results: Maximum number of matches to return (default: 100)

    Returns:
        List of matches: [{"file": path, "line": line_number, "text": line_content}, ...]

    Raises:
        FileNotFoundError: If path doesn't exist
        ValueError: If regex pattern is invalid

    Examples:
        grep_files("src/", "TODO")                    # Find "TODO" in all files
        grep_files("src/", "def .*test", regex=true)  # Regex search
        grep_files(".", "error", case_sensitive=false) # Case-insensitive
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    # Compile regex pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        if regex:
            compiled = re.compile(pattern, flags)
        else:
            # Escape for literal match
            compiled = re.compile(re.escape(pattern), flags)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")

    results = []
    search_path = Path(path)

    # Single file search
    if search_path.is_file():
        files_to_search = [search_path]
    else:
        # Directory search - find all files recursively
        files_to_search = [f for f in search_path.rglob("*") if f.is_file()]

    for file_path in files_to_search:
        if len(results) >= max_results:
            break

        # Skip binary files and large files
        try:
            if file_path.stat().st_size > 1_000_000:  # Skip files > 1MB
                continue
        except OSError:
            continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if len(results) >= max_results:
                        break

                    if compiled.search(line):
                        # Make path relative if searching in a directory
                        try:
                            rel_path = str(file_path.relative_to(search_path)) if search_path.is_dir() else str(file_path)
                        except ValueError:
                            rel_path = str(file_path)

                        results.append({
                            "file": rel_path,
                            "line": line_num,
                            "text": line.rstrip('\n\r')
                        })
        except (OSError, IOError):
            # Skip files that can't be read
            continue

    return results
