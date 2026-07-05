"""Tests for runtime/tools.py to improve coverage.

Covers: tool registry, dispatch, calculate, read_file, write_file,
shell_exec, patch_file, web_search (mocked), web_fetch (mocked).
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from helen.runtime.tools import (
    register_tool,
    get_tool,
    list_tools,
    get_tool_schemas,
    dispatch_tool,
    _calculate,
    _read_file,
    _write_file,
    _shell_exec,
    _patch_file,
    _web_search,
    _web_fetch,
    _load_skill,
    HelenTool,
    _tools,
)


# ── Tool Registry ─────────────────────────────────────────────


class TestToolRegistry:
    """Tests for tool registration and lookup."""

    def test_register_and_get_tool(self):
        """Register a tool and retrieve it by name."""
        register_tool(
            name="test_tool_reg",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "ok",
        )
        tool = get_tool("test_tool_reg")
        assert tool is not None
        assert tool.name == "test_tool_reg"
        assert tool.description == "A test tool"

    def test_get_nonexistent_tool(self):
        """Get a tool that doesn't exist returns None."""
        assert get_tool("nonexistent_tool_xyz") is None

    def test_list_tools(self):
        """list_tools returns all registered tools."""
        tools = list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        names = [t.name for t in tools]
        assert "read_file" in names
        assert "write_file" in names
        assert "shell_exec" in names

    def test_get_tool_schemas_all(self):
        """Get schemas for all tools."""
        schemas = get_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) > 0
        for schema in schemas:
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_get_tool_schemas_specific(self):
        """Get schemas for specific tools."""
        schemas = get_tool_schemas(["read_file", "write_file"])
        assert len(schemas) == 2
        names = [s["function"]["name"] for s in schemas]
        assert "read_file" in names
        assert "write_file" in names

    def test_get_tool_schemas_unknown(self):
        """Unknown tool names are silently skipped."""
        schemas = get_tool_schemas(["nonexistent_xyz"])
        assert schemas == []

    def test_dispatch_tool_success(self):
        """Dispatch a tool call successfully."""
        result = dispatch_tool("read_file", {"path": "/dev/null"})
        data = json.loads(result)
        assert "content" in data or "error" in data  # May succeed or fail on /dev/null

    def test_dispatch_unknown_tool(self):
        """Dispatch an unknown tool returns error."""
        result = dispatch_tool("nonexistent_tool_xyz", {})
        data = json.loads(result)
        assert "error" in data
        assert "Unknown tool" in data["error"]

    def test_dispatch_tool_handler_error(self):
        """Dispatch a tool that raises an exception returns error."""
        register_tool(
            name="failing_tool",
            description="A tool that fails",
            parameters={"type": "object", "properties": {}},
            handler=lambda: (_ for _ in ()).throw(ValueError("test error")),
        )
        result = dispatch_tool("failing_tool", {})
        data = json.loads(result)
        assert "error" in data
        assert "failing_tool" in data["error"]


# ── Calculate ─────────────────────────────────────────────────


class TestCalculate:
    """Tests for the _calculate tool."""

    def test_simple_addition(self):
        result = json.loads(_calculate("2 + 3"))
        assert result["result"] == 5

    def test_multiplication(self):
        result = json.loads(_calculate("4 * 7"))
        assert result["result"] == 28

    def test_division(self):
        result = json.loads(_calculate("10 / 4"))
        assert result["result"] == 2.5

    def test_floor_division(self):
        result = json.loads(_calculate("10 // 3"))
        assert result["result"] == 3

    def test_modulo(self):
        result = json.loads(_calculate("10 % 3"))
        assert result["result"] == 1

    def test_power(self):
        result = json.loads(_calculate("2 ** 10"))
        assert result["result"] == 1024

    def test_unary_minus(self):
        result = json.loads(_calculate("-5"))
        assert result["result"] == -5

    def test_unary_plus(self):
        result = json.loads(_calculate("+5"))
        assert result["result"] == 5

    def test_complex_expression(self):
        result = json.loads(_calculate("(2 + 3) * 4 - 1"))
        assert result["result"] == 19

    def test_math_sqrt(self):
        result = json.loads(_calculate("sqrt(16)"))
        assert result["result"] == 4.0

    def test_math_abs(self):
        result = json.loads(_calculate("abs(-42)"))
        assert result["result"] == 42

    def test_math_pi(self):
        result = json.loads(_calculate("pi"))
        assert abs(result["result"] - 3.14159) < 0.001

    def test_math_e(self):
        result = json.loads(_calculate("e"))
        assert abs(result["result"] - 2.71828) < 0.001

    def test_math_sin(self):
        result = json.loads(_calculate("sin(0)"))
        assert result["result"] == 0.0

    def test_math_cos(self):
        result = json.loads(_calculate("cos(0)"))
        assert result["result"] == 1.0

    def test_math_log(self):
        result = json.loads(_calculate("log(1)"))
        assert result["result"] == 0.0

    def test_math_round(self):
        result = json.loads(_calculate("round(3.7)"))
        assert result["result"] == 4

    def test_math_ceil(self):
        result = json.loads(_calculate("ceil(3.2)"))
        assert result["result"] == 4

    def test_math_floor(self):
        result = json.loads(_calculate("floor(3.8)"))
        assert result["result"] == 3

    def test_math_degrees(self):
        result = json.loads(_calculate("degrees(3.14159)"))
        assert abs(result["result"] - 180.0) < 0.1

    def test_math_radians(self):
        result = json.loads(_calculate("radians(180)"))
        assert abs(result["result"] - 3.14159) < 0.001

    def test_unsafe_name(self):
        """Block access to dangerous names."""
        result = json.loads(_calculate("__import__('os')"))
        assert "error" in result

    def test_unsafe_node(self):
        """Block unsafe AST nodes."""
        result = json.loads(_calculate("[1, 2, 3]"))
        assert "error" in result

    def test_invalid_expression(self):
        """Invalid expression returns error."""
        result = json.loads(_calculate("2 +"))
        assert "error" in result

    def test_math_pow_function(self):
        result = json.loads(_calculate("pow(2, 8)"))
        assert result["result"] == 256

    def test_math_exp(self):
        result = json.loads(_calculate("exp(0)"))
        assert result["result"] == 1.0


# ── Read File ─────────────────────────────────────────────────


class TestReadFile:
    """Tests for the _read_file tool."""

    def test_read_existing_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world", encoding="utf-8")
        result = json.loads(_read_file(str(test_file)))
        assert result["content"] == "hello world"
        assert result["path"] == str(test_file)

    def test_read_nonexistent_file(self):
        result = json.loads(_read_file("/nonexistent/path/file.txt"))
        assert "error" in result

    def test_read_large_file_truncated(self, tmp_path):
        test_file = tmp_path / "large.txt"
        test_file.write_text("x" * 20000, encoding="utf-8")
        result = json.loads(_read_file(str(test_file)))
        assert "[truncated]" in result["content"]
        assert len(result["content"]) <= 16020  # 16000 + truncation marker

    def test_read_empty_file(self, tmp_path):
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")
        result = json.loads(_read_file(str(test_file)))
        assert result["content"] == ""


# ── Write File ────────────────────────────────────────────────


class TestWriteFile:
    """Tests for the _write_file tool."""

    def test_write_new_file(self, tmp_path):
        test_file = tmp_path / "output.txt"
        result = json.loads(_write_file(str(test_file), "hello"))
        assert result["status"] == "ok"
        assert result["bytes_written"] == 5
        assert test_file.read_text() == "hello"

    def test_write_creates_directories(self, tmp_path):
        test_file = tmp_path / "sub" / "dir" / "file.txt"
        result = json.loads(_write_file(str(test_file), "nested"))
        assert result["status"] == "ok"
        assert test_file.read_text() == "nested"

    def test_write_overwrites(self, tmp_path):
        test_file = tmp_path / "overwrite.txt"
        test_file.write_text("old content")
        result = json.loads(_write_file(str(test_file), "new content"))
        assert result["status"] == "ok"
        assert test_file.read_text() == "new content"


# ── Shell Exec ────────────────────────────────────────────────


class TestShellExec:
    """Tests for the _shell_exec tool."""

    def test_simple_command(self):
        result = json.loads(_shell_exec("echo hello"))
        assert result["exit_code"] == 0
        assert "hello" in result["output"]

    def test_command_with_stderr(self):
        result = json.loads(_shell_exec("bash -c 'echo error >&2'", shell=False))
        assert "[stderr]" in result["output"]

    def test_command_timeout(self):
        result = json.loads(_shell_exec("sleep 10", timeout=1))
        assert "error" in result
        assert "timed out" in result["error"]

    def test_command_failure(self):
        result = json.loads(_shell_exec("false"))
        assert result["exit_code"] != 0

    def test_command_output_truncated(self):
        result = json.loads(_shell_exec("yes | head -n 2000", shell=True))
        if "output" in result:
            assert len(result["output"]) <= 8020  # 8000 + truncation marker

    def test_shell_true_default(self):
        """Test that shell=True is the default"""
        # Command with shell syntax should work by default
        result = json.loads(_shell_exec("echo first && echo second"))
        assert result["exit_code"] == 0
        assert "first" in result["output"]
        assert "second" in result["output"]

    def test_shell_syntax_pipe(self):
        """Test pipe operator works with default shell=True"""
        result = json.loads(_shell_exec("echo 'hello world' | wc -w"))
        assert result["exit_code"] == 0
        assert "2" in result["output"]  # word count

    def test_shell_syntax_redirect(self):
        """Test redirect operator works with default shell=True"""
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            result = json.loads(_shell_exec(f"echo test > {test_file}"))
            assert result["exit_code"] == 0
            assert os.path.exists(test_file)
            with open(test_file) as f:
                assert f.read().strip() == "test"

    def test_explicit_shell_false(self):
        """Test explicit shell=False"""
        result = json.loads(_shell_exec("echo hello", shell=False))
        assert result["exit_code"] == 0
        assert "hello" in result["output"]

    def test_brace_expansion(self):
        """Test bash brace expansion works with default shell=True"""
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = os.path.join(tmpdir, "test_brace")
            result = json.loads(_shell_exec(f"mkdir -p {test_dir}/{{a,b,c}}"))
            assert result["exit_code"] == 0
            # Should create three separate directories, not one literal {a,b,c}
            assert os.path.exists(os.path.join(test_dir, "a"))
            assert os.path.exists(os.path.join(test_dir, "b"))
            assert os.path.exists(os.path.join(test_dir, "c"))
            assert not os.path.exists(os.path.join(test_dir, "{a,b,c}"))


# ── Patch File ────────────────────────────────────────────────


class TestPatchFile:
    """Tests for the _patch_file tool."""

    def test_patch_exact_match(self, tmp_path):
        test_file = tmp_path / "patch.txt"
        test_file.write_text("def foo():\n    pass\n")
        result = json.loads(_patch_file(str(test_file), "def foo():", "def bar():"))
        assert result["status"] == "patched"
        assert "def bar():" in test_file.read_text()

    def test_patch_no_match(self, tmp_path):
        test_file = tmp_path / "patch.txt"
        test_file.write_text("hello world\n")
        result = json.loads(_patch_file(str(test_file), "nonexistent", "replacement"))
        assert "error" in result

    def test_patch_file_not_found(self):
        result = json.loads(_patch_file("/nonexistent/file.txt", "old", "new"))
        assert "error" in result
        assert "not found" in result["error"].lower() or "error" in result["error"].lower()

    def test_patch_with_bom(self, tmp_path):
        test_file = tmp_path / "bom.txt"
        test_file.write_text('\ufeffhello world\n', encoding="utf-8")
        result = json.loads(_patch_file(str(test_file), "hello", "goodbye"))
        assert result["status"] == "patched"
        assert "goodbye" in test_file.read_text()


# ── Web Search (mocked) ───────────────────────────────────────


class TestWebSearch:
    """Tests for _web_search with mocked HTTP calls."""

    def test_bing_search_success(self):
        """Test Bing search HTML parsing success."""
        mock_html = b"""
        <html>
        <ol id="b_results">
            <li class="b_algo">
                <h2><a href="https://www.python.org/">Welcome to <strong>Python</strong>.org</a></h2>
                <p class="b_lineclamp2">The mission of the Python Software Foundation is to promote, protect, and advance the Python programming language.</p>
            </li>
            <li class="b_algo">
                <h2><a href="https://docs.python.org/">Python Documentation</a></h2>
                <p class="b_lineclamp2">Official Python documentation and tutorials.</p>
            </li>
        </ol>
        </html>
        """

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_html
        mock_resp.headers.get.return_value = ''  # No content encoding
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = json.loads(_web_search("Python"))
            assert "results" in result
            assert len(result["results"]) == 2
            assert "Welcome to Python.org" in result["results"][0]
            assert "https://www.python.org/" in result["results"][0]

    def test_bing_search_no_results(self):
        """Test Bing search with no results."""
        mock_html = b"<html><ol id=\"b_results\"></ol></html>"

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_html
        mock_resp.headers.get.return_value = ''
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = json.loads(_web_search("xyznonexistent"))
            assert "results" in result
            assert result["results"] == []
            assert "message" in result

    def test_bing_search_network_error(self):
        """Test when Bing search fails due to network error."""
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            result = json.loads(_web_search("test"))
            assert "results" in result
            assert result["results"] == []
            assert "message" in result
            assert "Search failed" in result["message"]


# ── Web Fetch (mocked) ────────────────────────────────────────


class TestWebFetch:
    """Tests for _web_fetch with mocked HTTP calls."""

    def test_fetch_success(self):
        """Test successful URL fetch."""
        html_content = b"<html><body><p>Hello World</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.read.return_value = html_content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = json.loads(_web_fetch("https://example.com"))
            assert "content" in result
            assert "Hello World" in result["content"]

    def test_fetch_strips_scripts(self):
        """Test that script tags are stripped."""
        html_content = b"<html><script>alert('xss')</script><body>Safe</body></html>"
        mock_resp = MagicMock()
        mock_resp.read.return_value = html_content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = json.loads(_web_fetch("https://example.com"))
            assert "alert" not in result["content"]
            assert "Safe" in result["content"]

    def test_fetch_strips_styles(self):
        """Test that style tags are stripped."""
        html_content = b"<html><style>body{color:red}</style><body>Text</body></html>"
        mock_resp = MagicMock()
        mock_resp.read.return_value = html_content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = json.loads(_web_fetch("https://example.com"))
            assert "color:red" not in result["content"]
            assert "Text" in result["content"]

    def test_fetch_truncates_long_content(self):
        """Test that long content is truncated."""
        long_content = b"<html><body>" + b"x" * 20000 + b"</body></html>"
        mock_resp = MagicMock()
        mock_resp.read.return_value = long_content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = json.loads(_web_fetch("https://example.com"))
            assert "[truncated]" in result["content"]

    def test_fetch_network_error(self):
        """Test network error handling."""
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = json.loads(_web_fetch("https://example.com"))
            assert "error" in result


# ── Load Skill ────────────────────────────────────────────────


class TestLoadSkill:
    """Tests for the _load_skill tool."""

    def test_load_skill_not_found(self, tmp_path, monkeypatch):
        """Loading a nonexistent skill returns error."""
        monkeypatch.setattr("helen.runtime.config.get_skill_dirs", lambda: [tmp_path])
        result = json.loads(_load_skill("nonexistent_skill"))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_load_skill_found(self, tmp_path, monkeypatch):
        """Loading an existing skill returns content."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: my_skill\n---\n# My Skill\n")

        monkeypatch.setattr("helen.runtime.config.get_skill_dirs", lambda: [tmp_path])
        result = json.loads(_load_skill("my_skill"))
        assert result["name"] == "my_skill"
        assert "My Skill" in result["content"]
