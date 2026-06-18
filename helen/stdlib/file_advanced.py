"""File advanced operations module for Helen stdlib.

Provides advanced file operations: info, copy, move, delete, temp files.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


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
