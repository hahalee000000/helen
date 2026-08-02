"""Tests for cross-platform helper functions in agent/utils.helen.

These tests ensure the cross-platform helpers work correctly on Windows, macOS, and Linux.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest


# 获取项目根目录（更可靠的方式）
def _get_project_root() -> Path:
    """获取项目根目录，向上查找直到找到 pyproject.toml"""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    # 回退到默认路径
    return Path(__file__).parent.parent.parent


HELEN_AGENT_DIR = _get_project_root() / "helen" / "agent"


def run_helen_code(code: str, env: dict | None = None) -> str:
    """Run Helen code and return stdout."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False, encoding="utf-8") as f:
        f.write(code)
        f.flush()
        temp_path = f.name

    try:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        result = subprocess.run(
            [sys.executable, "-m", "helen", temp_path],
            capture_output=True,
            text=True,
            env=merged_env,
            timeout=30,
            cwd=HELEN_AGENT_DIR,
        )
        return result.stdout.strip()
    finally:
        os.unlink(temp_path)


class TestGetCwd:
    """Test get_cwd() cross-platform helper."""

    def test_get_cwd_with_env_var(self):
        """get_cwd() should prefer HELEN_WEBUI_CWD env var."""
        test_cwd = "/test/path/with/special-chars_123"
        if sys.platform == "win32":
            test_cwd = "C:\\test\\path\\with\\special-chars_123"

        code = '''
import "utils.helen"
main {
    print(get_cwd())
}
'''
        result = run_helen_code(code, env={"HELEN_WEBUI_CWD": test_cwd})
        assert result == test_cwd

    def test_get_cwd_fallback_without_env(self):
        """get_cwd() should fall back to shell command when env var not set."""
        code = '''
import "utils.helen"
main {
    let cwd = get_cwd()
    // cwd should be a non-empty string
    if len(cwd) > 0 {
        print("OK")
    } else {
        print("FAIL")
    }
}
'''
        env = os.environ.copy()
        env.pop("HELEN_WEBUI_CWD", None)
        result = run_helen_code(code, env=env)
        assert result == "OK"

    def test_get_cwd_with_trailing_backslash(self):
        """get_cwd() should handle paths with trailing backslash (Windows)."""
        if sys.platform != "win32":
            pytest.skip("Windows-only test")

        test_cwd = "C:\\test\\path\\"  # trailing backslash
        code = '''
import "utils.helen"
main {
    print(get_cwd())
}
'''
        result = run_helen_code(code, env={"HELEN_WEBUI_CWD": test_cwd})
        # Should not crash, should return the path (possibly normalized)
        assert "test" in result and "path" in result


class TestGetHome:
    """Test get_home() cross-platform helper."""

    def test_get_home_returns_nonempty(self):
        """get_home() should return a non-empty path."""
        code = '''
import "utils.helen"
main {
    let home = get_home()
    if len(home) > 0 {
        print("OK")
    } else {
        print("FAIL")
    }
}
'''
        result = run_helen_code(code)
        assert result == "OK"

    def test_get_home_prefers_home_env(self):
        """get_home() should prefer HOME env var on Unix."""
        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        test_home = "/test/home/dir"
        code = '''
import "utils.helen"
main {
    print(get_home())
}
'''
        result = run_helen_code(code, env={"HOME": test_home})
        assert result == test_home

    def test_get_home_uses_userprofile_on_windows(self):
        """get_home() should use USERPROFILE on Windows when HOME not set."""
        if sys.platform != "win32":
            pytest.skip("Windows-only test")

        test_home = "C:\\Users\\TestUser"
        code = '''
import "utils.helen"
main {
    print(get_home())
}
'''
        env = {"USERPROFILE": test_home}
        # Remove HOME if present
        result = run_helen_code(code, env=env)
        assert result == test_home
