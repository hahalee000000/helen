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

        # Clear env override so yaml value is actually exercised
        # (tests/conftest.py sets HELEN_API_KEY for subprocess-based tests)
        with patch.dict(os.environ, {}, clear=False), \
             patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            os.environ.pop("HELEN_API_KEY", None)
            os.environ.pop("HELEN_BASE_URL", None)
            os.environ.pop("HELEN_MODEL", None)
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
                    # Mock probe for unknown URL (api.openai.com not in known patterns)
                    from helen.runtime.probe import ProbeResult
                    mock_result = ProbeResult(success=True, protocol_name="openai")
                    with patch("helen.runtime.probe.probe_connectivity", return_value=mock_result):
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
                    from helen.runtime.probe import ProbeResult
                    mock_result = ProbeResult(success=True, protocol_name="openai")
                    with patch("helen.runtime.probe.probe_connectivity", return_value=mock_result):
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


# --- v1.40: Protocol and capabilities config fields ---


def test_save_config_with_protocol():
    """Test saving config with protocol field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            from helen.runtime.config import save_config
            config = {
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "sk-test",
                "model": "deepseek-v4",
                "protocol": "deepseek",
            }
            config_path = save_config(config)
            content = config_path.read_text()
            assert 'protocol: "deepseek"' in content
            assert 'base_url: "https://api.deepseek.com/v1"' in content


def test_save_config_with_capabilities():
    """Test saving config with capabilities section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            from helen.runtime.config import save_config
            config = {
                "base_url": "https://api.example.com/v1",
                "api_key": "sk-test",
                "model": "model-x",
                "protocol": "custom",
                "capabilities": {"thinking": True, "vision": False, "streaming": True},
            }
            config_path = save_config(config)
            content = config_path.read_text()
            assert "capabilities:" in content
            assert "thinking: true" in content
            assert "vision: false" in content
            assert "streaming: true" in content


def test_load_config_with_protocol():
    """Test loading config with protocol and capabilities fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""llm:
  base_url: "https://api.deepseek.com/v1"
  api_key: "sk-test"
  model: "deepseek-v4"
  protocol: "deepseek"
  capabilities:
    thinking: true
    vision: false
""")
        with patch.dict(os.environ, {}, clear=False), \
             patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            os.environ.pop("HELEN_API_KEY", None)
            os.environ.pop("HELEN_BASE_URL", None)
            os.environ.pop("HELEN_MODEL", None)
            from helen.runtime.config import load_config
            config = load_config()
            assert config["protocol"] == "deepseek"
            assert config["capabilities"]["thinking"] is True
            assert config["capabilities"]["vision"] is False


def test_load_config_backward_compatible():
    """Test that old config without protocol/capabilities still loads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""llm:
  base_url: "https://api.openai.com/v1"
  api_key: "sk-test"
  model: "gpt-4"
""")
        with patch.dict(os.environ, {}, clear=False), \
             patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            os.environ.pop("HELEN_API_KEY", None)
            os.environ.pop("HELEN_BASE_URL", None)
            os.environ.pop("HELEN_MODEL", None)
            from helen.runtime.config import load_config
            config = load_config()
            assert config["base_url"] == "https://api.openai.com/v1"
            assert "protocol" not in config
            assert "capabilities" not in config


def test_setup_wizard_known_provider():
    """Test setup wizard detects known provider by URL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch("builtins.input", side_effect=[
                "https://dashscope.aliyuncs.com/compatible-mode/v1",  # base_url
                "qwen3.7-plus",  # model
            ]), patch("getpass.getpass", return_value="sk-test-key"):
                from helen.runtime.config import run_setup_wizard
                success = run_setup_wizard()
                assert success is True
                # Verify config has protocol field
                config_path = Path(tmpdir) / "config.yaml"
                content = config_path.read_text()
                assert 'protocol: "dashscope"' in content


def test_setup_wizard_probe_connectivity_success():
    """Test setup wizard probes connectivity for unknown URL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch("builtins.input", side_effect=[
                "https://unknown-provider.com/v1",  # base_url (not in known patterns)
                "test-model",  # model
            ]), patch("getpass.getpass", return_value="sk-test-key"):
                # Mock probe_connectivity to return success
                from helen.runtime.probe import ProbeResult
                mock_result = ProbeResult(success=True, protocol_name="openai")
                with patch("helen.runtime.probe.probe_connectivity", return_value=mock_result):
                    from helen.runtime.config import run_setup_wizard
                    success = run_setup_wizard()
                    assert success is True


def test_setup_wizard_probe_connection_failure():
    """Test setup wizard shows error for connection failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("helen.runtime.config.HELEN_HOME", Path(tmpdir)):
            with patch("builtins.input", side_effect=[
                "https://bad-url.com/v1",
                "model",
            ]), patch("getpass.getpass", return_value="sk-test-key"):
                from helen.runtime.probe import ProbeResult
                mock_result = ProbeResult(
                    success=False,
                    error_type="connection",
                    error_message="Connection refused",
                )
                with patch("helen.runtime.probe.probe_connectivity", return_value=mock_result):
                    from helen.runtime.config import run_setup_wizard
                    success = run_setup_wizard()
                    assert success is False
                    # Config should NOT be saved on hard failure
                    config_path = Path(tmpdir) / "config.yaml"
                    assert not config_path.exists()

