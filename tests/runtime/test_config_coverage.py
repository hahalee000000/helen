"""Comprehensive tests for helen.runtime.config module.

Covers: load_config, _load_yaml_config, _parse_yaml_simple,
_load_env_config, save_config, get_helen_home, get_skill_dirs.
Uses tmp_path and monkeypatch to avoid touching real ~/.helen/.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from helen.runtime.config import (
    DEFAULT_LLM_CONFIG,
    _load_env_config,
    _load_yaml_config,
    _parse_yaml_simple,
    get_helen_home,
    get_skill_dirs,
    load_config,
    save_config,
)
import helen.runtime.config as config_module


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def isolated_helen(tmp_path, monkeypatch):
    """Redirect HELEN_HOME / HERMES_HOME to tmp_path so tests are isolated."""
    helen_home = tmp_path / ".helen"
    hermes_home = tmp_path / ".hermes"
    helen_home.mkdir()
    hermes_home.mkdir()

    monkeypatch.setattr(config_module, "HELEN_HOME", helen_home)
    monkeypatch.setattr(config_module, "HERMES_HOME", hermes_home)
    monkeypatch.setattr(config_module, "HERMES_ENV", hermes_home / ".env")
    monkeypatch.setattr(
        config_module,
        "CONFIG_FILES",
        [helen_home / "config.yaml", helen_home / "config.yml", helen_home / ".env"],
    )
    return types.SimpleNamespace(helen_home=helen_home, hermes_home=hermes_home)


# ── get_helen_home ───────────────────────────────────────────────────────────


class TestGetHelenHome:
    def test_creates_directory_if_missing(self, tmp_path, monkeypatch):
        target = tmp_path / "new_helen"
        monkeypatch.setattr(config_module, "HELEN_HOME", target)
        result = get_helen_home()
        assert target.exists()
        assert result == target

    def test_returns_existing_directory(self, isolated_helen):
        result = get_helen_home()
        assert result == isolated_helen.helen_home
        assert result.exists()


# ── _load_env_config ─────────────────────────────────────────────────────────


class TestLoadEnvConfig:
    def test_basic_key_value(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("HELEN_API_KEY=sk-test-123\nHELEN_MODEL=gpt-3.5-turbo\n")
        result = _load_env_config(env)
        assert result == {"api_key": "sk-test-123", "model": "gpt-3.5-turbo"}

    def test_quoted_values(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text('HELEN_BASE_URL="https://api.example.com"\n')
        result = _load_env_config(env)
        assert result == {"base_url": "https://api.example.com"}

    def test_single_quoted_values(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("HELEN_API_KEY='my-key'\n")
        result = _load_env_config(env)
        assert result == {"api_key": "my-key"}

    def test_comments_and_blank_lines(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("# comment\n\nHELEN_TIMEOUT=30\n  # another comment\n")
        result = _load_env_config(env)
        assert result == {"timeout": 30}

    def test_temperature_float(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("HELEN_TEMPERATURE=0.5\n")
        result = _load_env_config(env)
        assert result == {"temperature": 0.5}

    def test_dashscope_aliases(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("DASHSCOPE_BASE_URL=https://dash.example.com\nDASHSCOPE_API_KEY=dk-123\n")
        result = _load_env_config(env)
        assert result["base_url"] == "https://dash.example.com"
        assert result["api_key"] == "dk-123"

    def test_openai_aliases(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("OPENAI_BASE_URL=https://oai.example.com\nOPENAI_API_KEY=ok-456\n")
        result = _load_env_config(env)
        assert result["base_url"] == "https://oai.example.com"
        assert result["api_key"] == "ok-456"

    def test_default_model_alias(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("DEFAULT_MODEL=claude-3\n")
        result = _load_env_config(env)
        assert result == {"model": "claude-3"}

    def test_temperature_alias(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("TEMPERATURE=0.9\n")
        result = _load_env_config(env)
        assert result == {"temperature": 0.9}

    def test_timeout_alias(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("TIMEOUT=120\n")
        result = _load_env_config(env)
        assert result == {"timeout": 120}

    def test_unknown_keys_ignored(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("SOME_RANDOM_VAR=hello\nHELEN_API_KEY=valid\n")
        result = _load_env_config(env)
        assert result == {"api_key": "valid"}

    def test_nonexistent_file_returns_empty(self, tmp_path):
        result = _load_env_config(tmp_path / "missing.env")
        assert result == {}

    def test_line_without_equals_ignored(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("no_equals_here\nHELEN_MODEL=gpt-4\n")
        result = _load_env_config(env)
        assert result == {"model": "gpt-4"}


# ── _parse_yaml_simple ───────────────────────────────────────────────────────


class TestParseYamlSimple:
    def test_basic_llm_section(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  base_url: https://api.test.com\n  model: gpt-4\n")
        result = _parse_yaml_simple(yml)
        assert result == {"base_url": "https://api.test.com", "model": "gpt-4"}

    def test_api_key(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  api_key: sk-abc\n")
        result = _parse_yaml_simple(yml)
        assert result == {"api_key": "sk-abc"}

    def test_temperature_and_timeout(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  temperature: 0.3\n  timeout: 45\n")
        result = _parse_yaml_simple(yml)
        assert result == {"temperature": 0.3, "timeout": 45}

    def test_quoted_values_stripped(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text('llm:\n  base_url: "https://quoted.com"\n  api_key: \'single-q\'\n')
        result = _parse_yaml_simple(yml)
        assert result["base_url"] == "https://quoted.com"
        assert result["api_key"] == "single-q"

    def test_comments_inside_llm_ignored(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  # this is a comment\n  model: gpt-4\n")
        result = _parse_yaml_simple(yml)
        assert result == {"model": "gpt-4"}

    def test_new_top_level_section_ends_llm(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  model: gpt-4\nother_section:\n  key: value\n")
        result = _parse_yaml_simple(yml)
        assert result == {"model": "gpt-4"}

    def test_no_llm_section_returns_empty(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("other:\n  key: value\n")
        result = _parse_yaml_simple(yml)
        assert result == {}

    def test_empty_file(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("")
        result = _parse_yaml_simple(yml)
        assert result == {}

    def test_nonexistent_file_returns_empty(self, tmp_path):
        result = _parse_yaml_simple(tmp_path / "missing.yaml")
        assert result == {}


# ── _load_yaml_config ────────────────────────────────────────────────────────


class TestLoadYamlConfig:
    def test_with_yaml_available(self, tmp_path):
        """When PyYAML is available, use it to parse."""
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  base_url: https://yaml.test\n  model: gpt-4-turbo\n  temperature: 0.8\n  timeout: 90\n")
        result = _load_yaml_config(yml)
        assert result["base_url"] == "https://yaml.test"
        assert result["model"] == "gpt-4-turbo"
        assert result["temperature"] == 0.8
        assert result["timeout"] == 90

    def test_yaml_with_api_key(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  api_key: secret-key\n")
        result = _load_yaml_config(yml)
        assert result["api_key"] == "secret-key"

    def test_yaml_empty_file(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("")
        result = _load_yaml_config(yml)
        assert result == {}

    def test_yaml_no_llm_key(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("other_key: value\n")
        result = _load_yaml_config(yml)
        assert result == {}

    def test_fallback_to_simple_parser_on_import_error(self, tmp_path, monkeypatch):
        """When yaml import fails, fall back to _parse_yaml_simple."""
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  model: fallback-model\n")

        # Make `import yaml` raise ImportError inside _load_yaml_config
        real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("No module named 'yaml'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fake_import)
        result = _load_yaml_config(yml)
        assert result == {"model": "fallback-model"}

    def test_yaml_partial_llm_keys(self, tmp_path):
        yml = tmp_path / "config.yaml"
        yml.write_text("llm:\n  model: only-model\n")
        result = _load_yaml_config(yml)
        assert result == {"model": "only-model"}
        assert "base_url" not in result


# ── load_config ──────────────────────────────────────────────────────────────


class TestLoadConfig:
    def test_defaults_when_no_files(self, isolated_helen):
        result = load_config()
        assert result == DEFAULT_LLM_CONFIG.copy()

    def test_loads_from_helen_env(self, isolated_helen):
        env = isolated_helen.helen_home / ".env"
        env.write_text("HELEN_API_KEY=from-env\n")
        result = load_config()
        assert result["api_key"] == "from-env"
        # Other keys still have defaults
        assert result["model"] == DEFAULT_LLM_CONFIG["model"]

    def test_loads_from_hermes_env(self, isolated_helen):
        env = isolated_helen.hermes_home / ".env"
        env.write_text("HELEN_MODEL=hermes-model\n")
        result = load_config()
        assert result["model"] == "hermes-model"

    def test_helen_env_overrides_hermes_env(self, isolated_helen):
        hermes_env = isolated_helen.hermes_home / ".env"
        hermes_env.write_text("HELEN_MODEL=old-model\n")
        helen_env = isolated_helen.helen_home / ".env"
        helen_env.write_text("HELEN_MODEL=new-model\n")
        result = load_config()
        assert result["model"] == "new-model"

    def test_yaml_overrides_env(self, isolated_helen):
        env = isolated_helen.helen_home / ".env"
        env.write_text("HELEN_MODEL=env-model\n")
        yml = isolated_helen.helen_home / "config.yaml"
        yml.write_text("llm:\n  model: yaml-model\n")
        result = load_config()
        assert result["model"] == "yaml-model"

    def test_config_yaml_overrides_config_yml(self, isolated_helen):
        yml = isolated_helen.helen_home / "config.yml"
        yml.write_text("llm:\n  model: yml-model\n")
        yaml_file = isolated_helen.helen_home / "config.yaml"
        yaml_file.write_text("llm:\n  model: yaml-model\n")
        result = load_config()
        assert result["model"] == "yaml-model"

    def test_empty_values_not_applied(self, isolated_helen):
        env = isolated_helen.helen_home / ".env"
        env.write_text("HELEN_API_KEY=\n")
        result = load_config()
        # Empty string should not override default
        assert "api_key" not in result or result.get("api_key") == DEFAULT_LLM_CONFIG.get("api_key")

    def test_all_sources_merged(self, isolated_helen):
        hermes_env = isolated_helen.hermes_home / ".env"
        hermes_env.write_text("HELEN_TIMEOUT=100\n")
        helen_env = isolated_helen.helen_home / ".env"
        helen_env.write_text("HELEN_TEMPERATURE=0.2\n")
        yml = isolated_helen.helen_home / "config.yaml"
        yml.write_text("llm:\n  model: merged-model\n")
        result = load_config()
        assert result["timeout"] == 100
        assert result["temperature"] == 0.2
        assert result["model"] == "merged-model"
        # Defaults still present
        assert result["base_url"] == DEFAULT_LLM_CONFIG["base_url"]


# ── save_config ──────────────────────────────────────────────────────────────


class TestSaveConfig:
    def test_creates_config_file(self, isolated_helen):
        path = save_config({"model": "saved-model"})
        assert path.exists()
        assert path == isolated_helen.helen_home / "config.yaml"

    def test_writes_llm_section(self, isolated_helen):
        save_config({"base_url": "https://saved.com", "api_key": "key123", "model": "gpt-4"})
        content = (isolated_helen.helen_home / "config.yaml").read_text()
        assert "llm:" in content
        assert 'base_url: "https://saved.com"' in content
        assert 'api_key: "key123"' in content
        assert 'model: "gpt-4"' in content

    def test_writes_temperature_and_timeout(self, isolated_helen):
        save_config({"model": "x", "temperature": 0.5, "timeout": 30})
        content = (isolated_helen.helen_home / "config.yaml").read_text()
        assert "temperature: 0.5" in content
        assert "timeout: 30" in content

    def test_creates_helen_home_if_missing(self, tmp_path, monkeypatch):
        new_home = tmp_path / "brand_new"
        monkeypatch.setattr(config_module, "HELEN_HOME", new_home)
        path = save_config({"model": "test"})
        assert new_home.exists()
        assert path == new_home / "config.yaml"

    def test_header_comment(self, isolated_helen):
        save_config({"model": "x"})
        content = (isolated_helen.helen_home / "config.yaml").read_text()
        assert content.startswith("# Helen configuration")

    def test_empty_config_no_llm_section(self, isolated_helen):
        save_config({})
        content = (isolated_helen.helen_home / "config.yaml").read_text()
        assert "llm:" not in content

    def test_roundtrip(self, isolated_helen):
        """Save then load should preserve values."""
        original = {"base_url": "https://rt.com", "api_key": "rt-key", "model": "rt-model", "temperature": 0.1, "timeout": 15}
        save_config(original)
        loaded = load_config()
        assert loaded["base_url"] == "https://rt.com"
        assert loaded["api_key"] == "rt-key"
        assert loaded["model"] == "rt-model"
        assert loaded["temperature"] == 0.1
        assert loaded["timeout"] == 15


# ── get_skill_dirs ───────────────────────────────────────────────────────────


class TestGetSkillDirs:
    def test_empty_when_no_dirs(self, isolated_helen):
        result = get_skill_dirs()
        assert result == []

    def test_helen_skills_dir(self, isolated_helen):
        (isolated_helen.helen_home / "skills").mkdir()
        result = get_skill_dirs()
        assert isolated_helen.helen_home / "skills" in result

    def test_hermes_skills_dir(self, isolated_helen):
        (isolated_helen.hermes_home / "skills").mkdir()
        result = get_skill_dirs()
        assert isolated_helen.hermes_home / "skills" in result

    def test_hermes_agent_skills_dir(self, isolated_helen):
        agent_skills = isolated_helen.hermes_home / "hermes-agent" / "skills"
        agent_skills.mkdir(parents=True)
        result = get_skill_dirs()
        assert agent_skills in result

    def test_priority_order(self, isolated_helen):
        (isolated_helen.helen_home / "skills").mkdir()
        (isolated_helen.hermes_home / "skills").mkdir()
        agent_skills = isolated_helen.hermes_home / "hermes-agent" / "skills"
        agent_skills.mkdir(parents=True)
        result = get_skill_dirs()
        assert result[0] == isolated_helen.helen_home / "skills"
        assert result[1] == isolated_helen.hermes_home / "skills"
        assert result[2] == agent_skills
