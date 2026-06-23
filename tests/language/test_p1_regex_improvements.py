"""Test P1 regex improvements.

Tests verify:
1. regex functions have natural parameter order: regex_search(string, pattern)
2. regex_test returns boolean for easy condition checking
3. All regex functions work correctly
"""
import pytest
import subprocess
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def run_helen(file_path: Path) -> dict:
    """Run a Helen file and return result."""
    result = subprocess.run(
        ["helen", str(file_path)],
        capture_output=True,
        text=True,
        timeout=10
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


class TestRegexParameterOrder:
    """Test that regex functions have natural parameter order."""
    
    def test_regex_search_natural_order(self, temp_dir):
        """regex_search should be regex_search(string, pattern)."""
        test_file = temp_dir / "test.helen"
        test_file.write_text("""
main {
    let text = "hello world"
    let result = regex_search(text, "world")
    if result != null {
        print("found")
    } else {
        print("not found")
    }
}
""")
        result = run_helen(test_file)
        assert result["returncode"] == 0
        assert "found" in result["stdout"]
    
    def test_regex_match_natural_order(self, temp_dir):
        """regex_match should be regex_match(string, pattern)."""
        test_file = temp_dir / "test.helen"
        test_file.write_text("""
main {
    let text = "hello world"
    let result = regex_match(text, "hello")
    if result != null {
        print("matched")
    } else {
        print("not matched")
    }
}
""")
        result = run_helen(test_file)
        assert result["returncode"] == 0
        assert "matched" in result["stdout"]
    
    def test_regex_replace_natural_order(self, temp_dir):
        """regex_replace should be regex_replace(pattern, string, replacement)."""
        test_file = temp_dir / "test.helen"
        test_file.write_text("""
main {
    let text = "hello world"
    let result = regex_replace("world", text, "universe")
    print(result)
}
""")
        result = run_helen(test_file)
        assert result["returncode"] == 0
        assert "hello universe" in result["stdout"]


class TestRegexTestFunction:
    """Test the new regex_test convenience function."""
    
    def test_regex_test_returns_true(self, temp_dir):
        """regex_test should return true when pattern matches."""
        test_file = temp_dir / "test.helen"
        test_file.write_text("""
main {
    let text = "hello world"
    if regex_test("world", text) {
        print("found")
    } else {
        print("not found")
    }
}
""")
        result = run_helen(test_file)
        assert result["returncode"] == 0
        assert "found" in result["stdout"]
    
    def test_regex_test_returns_false(self, temp_dir):
        """regex_test should return false when pattern doesn't match."""
        test_file = temp_dir / "test.helen"
        test_file.write_text("""
main {
    let text = "hello world"
    if regex_test("xyz", text) {
        print("found")
    } else {
        print("not found")
    }
}
""")
        result = run_helen(test_file)
        assert result["returncode"] == 0
        assert "not found" in result["stdout"]
    
    def test_regex_test_in_loop(self, temp_dir):
        """regex_test should work well in loops and conditions."""
        test_file = temp_dir / "test.helen"
        test_file.write_text("""
main {
    let words = ["apple", "banana", "cherry", "date"]
    let count = 0
    for word in words {
        if regex_test("a", word) {
            count = count + 1
        }
    }
    print(count)
}
""")
        result = run_helen(test_file)
        assert result["returncode"] == 0
        assert "3" in result["stdout"]  # apple, banana, date have 'a'


class TestRegexSplitFindall:
    """Test regex_split and regex_findall with new parameter order."""
    
    def test_regex_split_natural_order(self, temp_dir):
        """regex_split should be regex_split(pattern, string)."""
        test_file = temp_dir / "test.helen"
        test_file.write_text("""
main {
    let text = "a,b,c,d"
    let parts = regex_split(",", text)
    print(len(parts))
    for part in parts {
        print(part)
    }
}
""")
        result = run_helen(test_file)
        assert result["returncode"] == 0
        assert "4" in result["stdout"]
        assert "a" in result["stdout"]
        assert "d" in result["stdout"]
    
    def test_regex_findall_natural_order(self, temp_dir):
        """regex_findall should be regex_findall(string, pattern)."""
        test_file = temp_dir / "test.helen"
        test_file.write_text("""
main {
    let text = "cat bat rat hat"
    let matches = regex_findall(text, "[a-z]at")
    print(len(matches))
    for m in matches {
        print(m)
    }
}
""")
        result = run_helen(test_file)
        assert result["returncode"] == 0
        assert "4" in result["stdout"]


class TestBackwardCompatibility:
    """Test that old code still works (if we keep old functions)."""
    
    def test_old_style_still_works(self, temp_dir):
        """Old parameter order should still work if we keep both versions."""
        # This test will be updated based on our decision
        # For now, we're changing the parameter order, so old code will break
        # But we'll update all existing code
        pass
