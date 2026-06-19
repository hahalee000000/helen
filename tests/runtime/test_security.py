"""Security tests for Helen runtime.

Tests path traversal prevention, SSRF protection, command injection,
and other security constraints.
"""

import os
import tempfile

import pytest

from helen.runtime.security import (
    SecurityError,
    mask_env_value,
    safe_env_list,
    validate_command,
    validate_kill_signal,
    validate_path,
    validate_pid,
    validate_url,
)


# ── Path Safety Tests ──────────────────────────────────────────


class TestValidatePath:
    """Tests for validate_path()."""

    def test_allows_relative_path_within_base(self, tmp_path):
        """Relative paths within base_dir are allowed."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        result = validate_path(str(test_file), base_dir=str(tmp_path))
        assert result == str(test_file)

    def test_blocks_path_traversal(self, tmp_path):
        """Path traversal with ../ is blocked."""
        with pytest.raises(SecurityError, match="traversal|blocked|escape"):
            validate_path("../../etc/passwd", base_dir=str(tmp_path))

    def test_blocks_proc_access(self, tmp_path):
        """Access to /proc is blocked."""
        with pytest.raises(SecurityError, match="blocked"):
            validate_path("/proc/self/environ", base_dir=str(tmp_path))

    def test_blocks_sys_access(self, tmp_path):
        """Access to /sys is blocked."""
        with pytest.raises(SecurityError, match="blocked"):
            validate_path("/sys/kernel/hostname", base_dir=str(tmp_path))

    def test_blocks_etc_shadow(self, tmp_path):
        """Access to /etc/shadow is blocked."""
        with pytest.raises(SecurityError, match="blocked"):
            validate_path("/etc/shadow", base_dir=str(tmp_path))

    def test_must_exist_raises_for_missing(self, tmp_path):
        """must_exist=True raises for non-existent paths."""
        with pytest.raises(SecurityError, match="does not exist"):
            validate_path(
                str(tmp_path / "nonexistent.txt"),
                base_dir=str(tmp_path),
                must_exist=True,
            )

    def test_allows_existing_file(self, tmp_path):
        """Existing files pass validation."""
        test_file = tmp_path / "exists.txt"
        test_file.write_text("data")
        result = validate_path(
            str(test_file), base_dir=str(tmp_path), must_exist=True
        )
        assert os.path.exists(result)


class TestValidatePathExists:
    """Tests for validate_path_exists()."""

    def test_allows_existing_file(self, tmp_path):
        """Existing files pass validation."""
        from helen.runtime.security import validate_path_exists
        test_file = tmp_path / "exists.txt"
        test_file.write_text("data")
        result = validate_path_exists(str(test_file), base_dir=str(tmp_path))
        assert os.path.exists(result)

    def test_raises_for_missing_file(self, tmp_path):
        """Non-existent files raise SecurityError."""
        from helen.runtime.security import validate_path_exists
        with pytest.raises(SecurityError, match="does not exist"):
            validate_path_exists(
                str(tmp_path / "nonexistent.txt"), base_dir=str(tmp_path)
            )

    def test_blocks_path_traversal(self, tmp_path):
        """Path traversal is blocked."""
        from helen.runtime.security import validate_path_exists
        with pytest.raises(SecurityError, match="traversal|blocked|escape"):
            validate_path_exists("../../etc/passwd", base_dir=str(tmp_path))


# ── URL Safety Tests (SSRF Protection) ────────────────────────


class TestValidateUrl:
    """Tests for validate_url()."""

    def test_allows_https_url(self):
        """HTTPS URLs to public hosts are allowed."""
        result = validate_url("https://example.com/api")
        assert result == "https://example.com/api"

    def test_allows_http_url(self):
        """HTTP URLs to public hosts are allowed."""
        result = validate_url("http://example.com/page")
        assert result == "http://example.com/page"

    def test_blocks_localhost(self):
        """localhost URLs are blocked (SSRF)."""
        with pytest.raises(SecurityError, match="localhost"):
            validate_url("http://localhost/admin")

    def test_blocks_127_0_0_1(self):
        """127.0.0.1 URLs are blocked (SSRF)."""
        with pytest.raises(SecurityError, match="localhost|private|reserved"):
            validate_url("http://127.0.0.1/admin")

    def test_blocks_0_0_0_0(self):
        """0.0.0.0 URLs are blocked (SSRF)."""
        with pytest.raises(SecurityError, match="localhost|private|reserved"):
            validate_url("http://0.0.0.0/admin")

    def test_blocks_invalid_scheme(self):
        """Non-http(s) schemes are blocked."""
        with pytest.raises(SecurityError, match="scheme"):
            validate_url("file:///etc/passwd")

    def test_blocks_ftp_scheme(self):
        """FTP scheme is blocked."""
        with pytest.raises(SecurityError, match="scheme"):
            validate_url("ftp://example.com/file")

    def test_blocks_no_hostname(self):
        """URLs without hostname are blocked."""
        with pytest.raises(SecurityError, match="hostname"):
            validate_url("http:///path")

    def test_blocks_private_ip_10(self):
        """Private IP range 10.0.0.0/8 is blocked."""
        from unittest.mock import patch
        import socket
        # Mock getaddrinfo to return a private IP
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('10.0.0.1', 0))
            ]
            with pytest.raises(SecurityError, match="private|reserved"):
                validate_url("http://private.example.com")

    def test_blocks_private_ip_172(self):
        """Private IP range 172.16.0.0/12 is blocked."""
        from unittest.mock import patch
        import socket
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('172.16.0.1', 0))
            ]
            with pytest.raises(SecurityError, match="private|reserved"):
                validate_url("http://internal.example.com")

    def test_blocks_private_ip_192(self):
        """Private IP range 192.168.0.0/16 is blocked."""
        from unittest.mock import patch
        import socket
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('192.168.1.1', 0))
            ]
            with pytest.raises(SecurityError, match="private|reserved"):
                validate_url("http://local.example.com")

    def test_blocks_unresolvable_hostname(self):
        """Unresolvable hostnames raise SecurityError."""
        from unittest.mock import patch
        import socket
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.gaierror("Name resolution failed")
            with pytest.raises(SecurityError, match="Cannot resolve"):
                validate_url("http://nonexistent.example.com")

    def test_handles_invalid_ip_gracefully(self):
        """Invalid IP addresses from DNS are handled gracefully."""
        from unittest.mock import patch
        import socket
        # Mock getaddrinfo to return an invalid IP string
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('not-a-valid-ip', 0))
            ]
            # Should not raise an error, just skip the invalid IP
            result = validate_url("http://example.com")
            assert result == "http://example.com"


# ── Command Safety Tests ──────────────────────────────────────


class TestValidateCommand:
    """Tests for validate_command()."""

    def test_allows_safe_command(self):
        """Safe commands are allowed."""
        result = validate_command("ls -la")
        assert result == "ls -la"

    def test_blocks_rm_rf_root(self):
        """rm -rf / is blocked."""
        with pytest.raises(SecurityError, match="Dangerous"):
            validate_command("rm -rf /")

    def test_blocks_fork_bomb(self):
        """Fork bomb is blocked."""
        with pytest.raises(SecurityError, match="Dangerous"):
            validate_command(":(){:|:&};:")

    def test_blocks_chmod_777_root(self):
        """chmod -R 777 / is blocked."""
        with pytest.raises(SecurityError, match="Dangerous"):
            validate_command("chmod -R 777 /")

    def test_allows_list_command(self):
        """List commands are allowed."""
        result = validate_command(["ls", "-la", "/tmp"])
        assert result == ["ls", "-la", "/tmp"]


# ── Process Safety Tests ──────────────────────────────────────


class TestValidatePid:
    """Tests for validate_pid()."""

    def test_blocks_pid_0(self):
        """PID 0 (system) is blocked."""
        with pytest.raises(SecurityError, match="system"):
            validate_pid(0)

    def test_blocks_pid_1(self):
        """PID 1 (init) is blocked."""
        with pytest.raises(SecurityError, match="system"):
            validate_pid(1)

    def test_blocks_self(self):
        """Current process PID is blocked."""
        with pytest.raises(SecurityError, match="current"):
            validate_pid(os.getpid())

    def test_allows_other_pid(self):
        """Other PIDs are allowed."""
        result = validate_pid(99999)
        assert result == 99999


class TestValidateKillSignal:
    """Tests for validate_kill_signal()."""

    def test_allows_sigterm(self):
        """SIGTERM is allowed."""
        import signal
        result = validate_kill_signal(signal.SIGTERM)
        assert result == signal.SIGTERM

    def test_allows_sigint(self):
        """SIGINT is allowed."""
        import signal
        result = validate_kill_signal(signal.SIGINT)
        assert result == signal.SIGINT

    def test_blocks_sigkill(self):
        """SIGKILL is blocked (not in allowed list)."""
        import signal
        with pytest.raises(SecurityError, match="not allowed"):
            validate_kill_signal(signal.SIGKILL)


# ── Environment Safety Tests ─────────────────────────────────


class TestMaskEnvValue:
    """Tests for mask_env_value()."""

    def test_masks_password(self):
        """Password values are masked."""
        result = mask_env_value("DB_PASSWORD", "supersecret123")
        assert "supersecret123" not in result
        assert "****" in result

    def test_masks_api_key(self):
        """API key values are masked."""
        result = mask_env_value("OPENAI_API_KEY", "sk-1234567890abcdef")
        assert "sk-1234567890abcdef" not in result
        assert result.startswith("sk")
        assert "****" in result

    def test_masks_token(self):
        """Token values are masked."""
        result = mask_env_value("AUTH_TOKEN", "mytoken123")
        assert "mytoken123" not in result

    def test_does_not_mask_normal_var(self):
        """Normal env vars are not masked."""
        result = mask_env_value("HOME", "/home/user")
        assert result == "/home/user"

    def test_masks_short_value(self):
        """Short sensitive values are fully masked."""
        result = mask_env_value("SECRET", "abc")
        assert result == "****"


class TestSafeEnvList:
    """Tests for safe_env_list()."""

    def test_masks_sensitive_vars(self):
        """Sensitive env vars are masked in the list."""
        os.environ["TEST_API_KEY"] = "test-key-12345"
        try:
            result = safe_env_list()
            assert "test-key-12345" not in result.get("TEST_API_KEY", "")
            assert "****" in result.get("TEST_API_KEY", "")
        finally:
            del os.environ["TEST_API_KEY"]

    def test_preserves_normal_vars(self):
        """Normal env vars are preserved."""
        os.environ["TEST_NORMAL_VAR"] = "hello"
        try:
            result = safe_env_list()
            assert result.get("TEST_NORMAL_VAR") == "hello"
        finally:
            del os.environ["TEST_NORMAL_VAR"]
