"""Tests for File advanced stdlib module.

Tests file information, operations, and temporary files.
"""

import pytest
import tempfile
import os
from pathlib import Path
from helen.stdlib.file_advanced import (
    # File info
    _file_size, _file_modified, _list_dir, _walk_dir,
    # File ops
    _copy_file, _move_file, _delete_file, _delete_dir,
    # Temp files
    _temp_file, _temp_dir,
)


# ── File Info Tests ────────────────────────────────────────────


class TestFileSize:
    """Tests for file_size."""

    def test_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("hello world")
            f.flush()
            path = f.name
        
        try:
            result = _file_size(path)
            assert result == 11  # len("hello world")
        finally:
            os.unlink(path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            path = f.name
        
        try:
            result = _file_size(path)
            assert result == 0
        finally:
            os.unlink(path)

    def test_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _file_size("/nonexistent/file.txt")


class TestFileModified:
    """Tests for file_modified."""

    def test_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test")
            f.flush()
            path = f.name
        
        try:
            result = _file_modified(path)
            # Should be ISO 8601 format
            assert "T" in result
            assert len(result) >= 19
        finally:
            os.unlink(path)

    def test_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _file_modified("/nonexistent/file.txt")


class TestListDir:
    """Tests for list_dir."""

    def test_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            Path(tmpdir, "file1.txt").write_text("test1")
            Path(tmpdir, "file2.txt").write_text("test2")
            Path(tmpdir, "file3.py").write_text("test3")
            
            result = _list_dir(tmpdir)
            assert len(result) == 3
            assert "file1.txt" in result
            assert "file2.txt" in result
            assert "file3.py" in result

    def test_with_pattern(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file1.txt").write_text("test1")
            Path(tmpdir, "file2.txt").write_text("test2")
            Path(tmpdir, "file3.py").write_text("test3")
            
            result = _list_dir(tmpdir, pattern="*.txt")
            assert len(result) == 2
            assert "file1.txt" in result
            assert "file2.txt" in result
            assert "file3.py" not in result

    def test_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _list_dir("/nonexistent/dir")

    def test_not_directory(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            with pytest.raises(NotADirectoryError):
                _list_dir(path)
        finally:
            os.unlink(path)


class TestWalkDir:
    """Tests for walk_dir."""

    def test_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            Path(tmpdir, "file1.txt").write_text("test1")
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "file2.txt").write_text("test2")
            
            result = _walk_dir(tmpdir)
            assert len(result) >= 2  # root + subdir
            
            # Check structure
            dirs = [r[0] for r in result]
            assert tmpdir in dirs

    def test_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _walk_dir("/nonexistent/dir")


# ── File Ops Tests ─────────────────────────────────────────────


class TestCopyFile:
    """Tests for copy_file."""

    def test_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir, "source.txt")
            dst = Path(tmpdir, "dest.txt")
            src.write_text("hello world")
            
            result = _copy_file(str(src), str(dst))
            
            assert "Copied" in result
            assert dst.exists()
            assert dst.read_text() == "hello world"

    def test_nonexistent_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                _copy_file("/nonexistent/file.txt", str(Path(tmpdir, "dest.txt")))


class TestMoveFile:
    """Tests for move_file."""

    def test_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir, "source.txt")
            dst = Path(tmpdir, "dest.txt")
            src.write_text("hello world")
            
            result = _move_file(str(src), str(dst))
            
            assert "Moved" in result
            assert not src.exists()
            assert dst.exists()
            assert dst.read_text() == "hello world"

    def test_nonexistent_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                _move_file("/nonexistent/file.txt", str(Path(tmpdir, "dest.txt")))


class TestDeleteFile:
    """Tests for delete_file."""

    def test_basic(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        
        assert os.path.exists(path)
        result = _delete_file(path)
        assert "Deleted" in result
        assert not os.path.exists(path)

    def test_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _delete_file("/nonexistent/file.txt")


class TestDeleteDir:
    """Tests for delete_dir."""

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir, "empty")
            empty_dir.mkdir()
            
            result = _delete_dir(str(empty_dir))
            assert "Deleted" in result
            assert not empty_dir.exists()

    def test_non_empty_dir_no_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            non_empty = Path(tmpdir, "nonempty")
            non_empty.mkdir()
            Path(non_empty, "file.txt").write_text("test")
            
            with pytest.raises(OSError):
                _delete_dir(str(non_empty), recursive=False)

    def test_non_empty_dir_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            non_empty = Path(tmpdir, "nonempty")
            non_empty.mkdir()
            Path(non_empty, "file.txt").write_text("test")
            
            result = _delete_dir(str(non_empty), recursive=True)
            assert "Deleted" in result
            assert not non_empty.exists()

    def test_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _delete_dir("/nonexistent/dir")


# ── Temp File Tests ────────────────────────────────────────────


class TestTempFile:
    """Tests for temp_file."""

    def test_basic(self):
        result = _temp_file()
        assert os.path.exists(result)
        assert os.path.isfile(result)
        os.unlink(result)

    def test_with_suffix(self):
        result = _temp_file(suffix=".txt")
        assert result.endswith(".txt")
        os.unlink(result)

    def test_with_prefix(self):
        result = _temp_file(prefix="myapp")
        assert "myapp" in os.path.basename(result)
        os.unlink(result)

    def test_with_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _temp_file(dir=tmpdir)
            assert result.startswith(tmpdir)
            os.unlink(result)


class TestTempDir:
    """Tests for temp_dir."""

    def test_basic(self):
        result = _temp_dir()
        assert os.path.exists(result)
        assert os.path.isdir(result)
        os.rmdir(result)

    def test_with_suffix(self):
        result = _temp_dir(suffix="_data")
        assert result.endswith("_data")
        os.rmdir(result)

    def test_with_prefix(self):
        result = _temp_dir(prefix="myapp")
        assert "myapp" in os.path.basename(result)
        os.rmdir(result)

    def test_with_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _temp_dir(dir=tmpdir)
            assert result.startswith(tmpdir)
            os.rmdir(result)
