"""Tests for File advanced stdlib module.

Tests file information, operations, temporary files, and file search.
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
    # File search
    _glob_files, _grep_files,
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


# ── File Search Tests ──────────────────────────────────────────


class TestGlobFiles:
    """Tests for glob_files."""

    def test_basic_recursive(self):
        """Test recursive glob with simple pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            Path(tmpdir, "file1.py").write_text("test1")
            Path(tmpdir, "file2.txt").write_text("test2")
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "file3.py").write_text("test3")
            Path(subdir, "file4.txt").write_text("test4")

            result = _glob_files(tmpdir, "*.py")
            assert len(result) == 2
            assert "file1.py" in result
            assert any("file3.py" in r for r in result)

    def test_all_files(self):
        """Test finding all files with default pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.txt").write_text("a")
            Path(tmpdir, "b.txt").write_text("b")
            subdir = Path(tmpdir, "sub")
            subdir.mkdir()
            Path(subdir, "c.txt").write_text("c")

            result = _glob_files(tmpdir)
            assert len(result) == 3

    def test_explicit_recursive(self):
        """Test explicit ** pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "root.md").write_text("root")
            deep = Path(tmpdir, "a", "b", "c")
            deep.mkdir(parents=True)
            Path(deep, "deep.md").write_text("deep")

            result = _glob_files(tmpdir, "**/*.md")
            assert len(result) == 2
            assert "root.md" in result
            assert any("deep.md" in r for r in result)

    def test_complex_pattern(self):
        """Test complex glob pattern with directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir, "src")
            src.mkdir()
            Path(src, "main.py").write_text("main")
            Path(src, "utils.py").write_text("utils")
            tests = Path(tmpdir, "tests")
            tests.mkdir()
            Path(tests, "test_main.py").write_text("test")

            result = _glob_files(tmpdir, "src/*.py")
            assert len(result) == 2
            assert all("src/" in r for r in result)

    def test_empty_directory(self):
        """Test glob on empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _glob_files(tmpdir, "*.py")
            assert result == []

    def test_nonexistent_directory(self):
        """Test glob on nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            _glob_files("/nonexistent/dir", "*.py")

    def test_not_a_directory(self):
        """Test glob on a file instead of directory."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            with pytest.raises(NotADirectoryError):
                _glob_files(path, "*.py")
        finally:
            os.unlink(path)


class TestGrepFiles:
    """Tests for grep_files."""

    def test_basic_literal_search(self):
        """Test literal text search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "file1.txt")
            file1.write_text("Hello world\nThis is a test\nAnother line")
            file2 = Path(tmpdir, "file2.txt")
            file2.write_text("No match here\nBut test is here")

            result = _grep_files(tmpdir, "test")
            assert len(result) == 2
            assert all(m["file"] in ["file1.txt", "file2.txt"] for m in result)
            assert result[0]["line"] == 2  # "test" on line 2 in file1
            assert result[1]["line"] == 2  # "test" on line 2 in file2

    def test_regex_search(self):
        """Test regex pattern search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "code.py")
            file1.write_text("def foo():\n    pass\n\ndef bar():\n    pass")

            result = _grep_files(tmpdir, r"def \w+\(\)", regex=True)
            assert len(result) == 2
            assert result[0]["line"] == 1
            assert result[1]["line"] == 4

    def test_case_insensitive(self):
        """Test case-insensitive search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "mixed.txt")
            file1.write_text("ERROR: something failed\nWarning: minor issue\nerror: another one")

            result = _grep_files(tmpdir, "error", case_sensitive=False)
            assert len(result) == 2

    def test_single_file(self):
        """Test searching a single file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line 1\nline 2 with match\nline 3\nline 4 with match")
            f.flush()
            path = f.name

        try:
            result = _grep_files(path, "match")
            assert len(result) == 2
            assert result[0]["line"] == 2
            assert result[1]["line"] == 4
        finally:
            os.unlink(path)

    def test_max_results(self):
        """Test max_results limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "many.txt")
            file1.write_text("\n".join([f"match line {i}" for i in range(50)]))

            result = _grep_files(tmpdir, "match", max_results=10)
            assert len(result) == 10

    def test_no_matches(self):
        """Test search with no matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "clean.txt")
            file1.write_text("no matches here\nanother clean line")

            result = _grep_files(tmpdir, "xyz123")
            assert result == []

    def test_invalid_regex(self):
        """Test invalid regex pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "test.txt")
            file1.write_text("test")

            with pytest.raises(ValueError, match="Invalid regex"):
                _grep_files(tmpdir, "[invalid", regex=True)

    def test_nonexistent_path(self):
        """Test search on nonexistent path."""
        with pytest.raises(FileNotFoundError):
            _grep_files("/nonexistent/path", "pattern")

    def test_skip_binary_large_files(self):
        """Test that large files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file > 1MB
            large_file = Path(tmpdir, "large.txt")
            with open(large_file, "w") as f:
                f.write("x" * 1_500_000)

            result = _grep_files(tmpdir, "x")
            # Should be skipped due to size
            assert result == []
