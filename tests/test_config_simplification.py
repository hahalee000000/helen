"""Tests for simplified config system."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_load_config_from_yaml():
    """Test loading config from config.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""llm:
  base_url: "https://api.example.com/v1"
  api_key: "test-key-123"
  model: "gpt-4-turbo"
  temperature: 0.5
  timeout: 30
""")

        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            from helen.runtime.config import load_config
            config = load_config()

            assert config["base_url"] == "https://api.example.com/v1"
            assert config["api_key"] == "test-key-123"
            assert config["model"] == "gpt-4-turbo"
            assert config["temperature"] == 0.5
            assert config["timeout"] == 30


def test_load_config_env_override():
    """Test that environment variables override config.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""llm:
  base_url: "https://api.example.com/v1"
  api_key: "yaml-key"
  model: "gpt-4"
""")

        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch.dict(os.environ, {
                "HELEN_API_KEY": "env-key",
                "HELEN_MODEL": "claude-3",
            }):
                from helen.runtime.config import load_config
                config = load_config()

                # Env vars should override
                assert config["api_key"] == "env-key"
                assert config["model"] == "claude-3"
                # YAML value should remain
                assert config["base_url"] == "https://api.example.com/v1"


def test_load_config_no_file():
    """Test loading config when no file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch.dict(os.environ, {}, clear=True):
                from helen.runtime.config import load_config
                config = load_config()

                # Should return defaults
                assert config["base_url"] == "https://api.openai.com/v1"
                assert config["model"] == "gpt-4"
                assert config["temperature"] == 0.7
                assert config["timeout"] == 60


def test_is_configured_with_env():
    """Test is_configured() with environment variable."""
    with patch.dict(os.environ, {"HELEN_API_KEY": "test-key"}):
        from helen.runtime.config import is_configured
        assert is_configured() == True


def test_is_configured_with_yaml():
    """Test is_configured() with config.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""llm:
  api_key: "test-key-123"
""")

        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch.dict(os.environ, {}, clear=True):
                from helen.runtime.config import is_configured
                assert is_configured() == True


def test_is_configured_missing():
    """Test is_configured() returns False when not configured."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch.dict(os.environ, {}, clear=True):
                from helen.runtime.config import is_configured
                assert is_configured() == False


def test_is_configured_placeholder():
    """Test is_configured() returns False for placeholder api_key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""llm:
  api_key: "YOUR_API_KEY_HERE"
""")

        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch.dict(os.environ, {}, clear=True):
                from helen.runtime.config import is_configured
                assert is_configured() == False


def test_run_setup_wizard_success():
    """Test setup wizard saves configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch("builtins.input", side_effect=["", "", ""]):  # Use defaults
                with patch("getpass.getpass", return_value="test-key-123"):
                    from helen.runtime.config import run_setup_wizard
                    success = run_setup_wizard()

                    assert success == True

                    # Verify config was saved
                    config_path = Path(tmpdir) / "config.yaml"
                    assert config_path.exists()
                    content = config_path.read_text()
                    assert "test-key-123" in content


def test_run_setup_wizard_custom_values():
    """Test setup wizard with custom values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch("builtins.input", side_effect=[
                "https://custom.api.com/v1",  # base_url
                "claude-3-opus",  # model
            ]):
                with patch("getpass.getpass", return_value="custom-key-456"):
                    from helen.runtime.config import run_setup_wizard
                    success = run_setup_wizard()

                    assert success == True

                    # Verify custom values were saved
                    config_path = Path(tmpdir) / "config.yaml"
                    content = config_path.read_text()
                    assert "https://custom.api.com/v1" in content
                    assert "custom-key-456" in content
                    assert "claude-3-opus" in content


def test_run_setup_wizard_empty_api_key():
    """Test setup wizard rejects empty API key."""
    with patch("getpass.getpass", return_value=""):
        with patch("builtins.input", return_value=""):
            from helen.runtime.config import run_setup_wizard
            success = run_setup_wizard()
            assert success == False


def test_run_setup_wizard_cancelled():
    """Test setup wizard handles KeyboardInterrupt."""
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        from helen.runtime.config import run_setup_wizard
        success = run_setup_wizard()
        assert success == False


def test_run_setup_wizard_eof():
    """Test setup wizard handles EOFError."""
    with patch("builtins.input", side_effect=EOFError):
        from helen.runtime.config import run_setup_wizard
        success = run_setup_wizard()
        assert success == False
