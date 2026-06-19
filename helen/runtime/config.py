"""Helen configuration management.

Helen uses its own configuration directory (~/.helen/) for:
- API keys and LLM endpoint configuration
- Skill directories
- Runtime settings

Falls back to Hermes configuration (~/.hermes/) for backward compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# Helen home directory
HELEN_HOME = Path.home() / ".helen"

# Configuration file paths (in priority order)
CONFIG_FILES = [
    HELEN_HOME / "config.yaml",
    HELEN_HOME / "config.yml",
    HELEN_HOME / ".env",
]

# Hermes fallback
HERMES_HOME = Path.home() / ".hermes"
HERMES_ENV = HERMES_HOME / ".env"

# Default LLM settings
DEFAULT_LLM_CONFIG = {
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4",
    "temperature": 0.7,
    "timeout": 60,
}


def get_helen_home() -> Path:
    """Get Helen home directory, creating if needed."""
    HELEN_HOME.mkdir(parents=True, exist_ok=True)
    return HELEN_HOME


def get_skill_dirs() -> list[Path]:
    """Get list of skill directories in priority order.

    Returns:
        List of paths to scan for skills:
        1. ~/.helen/skills/ (Helen native)
        2. ~/.hermes/skills/ (Hermes fallback)
        3. ~/.hermes/hermes-agent/skills/ (Hermes agent skills)
    """
    dirs = []

    # Helen native skills
    helen_skills = HELEN_HOME / "skills"
    if helen_skills.exists():
        dirs.append(helen_skills)

    # Hermes fallback
    hermes_skills = HERMES_HOME / "skills"
    if hermes_skills.exists():
        dirs.append(hermes_skills)

    hermes_agent_skills = HERMES_HOME / "hermes-agent" / "skills"
    if hermes_agent_skills.exists():
        dirs.append(hermes_agent_skills)

    return dirs


def load_config() -> dict[str, Any]:
    """Load Helen configuration.

    Loads from multiple sources and merges them:
    1. ~/.hermes/.env (base fallback)
    2. ~/.helen/.env (Helen .env)
    3. ~/.helen/config.yml (Helen YAML)
    4. ~/.helen/config.yaml (Helen YAML, highest priority)

    Later sources override earlier ones.

    Returns:
        Configuration dictionary with keys:
        - base_url: LLM API endpoint
        - api_key: API key
        - model: Default model name
        - temperature: Default temperature
        - timeout: Request timeout
    """
    config = DEFAULT_LLM_CONFIG.copy()

    # Load from all sources in order (later overrides earlier)
    sources = [
        (HERMES_ENV, _load_env_config),
        (HELEN_HOME / ".env", _load_env_config),
        (HELEN_HOME / "config.yml", _load_yaml_config),
        (HELEN_HOME / "config.yaml", _load_yaml_config),
    ]

    for path, loader in sources:
        if path.exists():
            source_config = loader(path)
            # Only update keys that are present in source
            for key, value in source_config.items():
                if value is not None and value != "":
                    config[key] = value

    return config


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """Load configuration from YAML file."""
    config = {}
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Map YAML keys to config keys
        if "llm" in data:
            llm = data["llm"]
            if "base_url" in llm:
                config["base_url"] = llm["base_url"]
            if "api_key" in llm:
                config["api_key"] = llm["api_key"]
            if "model" in llm:
                config["model"] = llm["model"]
            if "temperature" in llm:
                config["temperature"] = float(llm["temperature"])
            if "timeout" in llm:
                config["timeout"] = int(llm["timeout"])
    except ImportError:
        # PyYAML not installed, try simple parsing
        config.update(_parse_yaml_simple(path))
    except Exception:
        pass

    return config


def _parse_yaml_simple(path: Path) -> dict[str, Any]:
    """Simple YAML parser for basic key-value pairs (no PyYAML dependency)."""
    config = {}
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()

        # Simple parser for llm: section
        in_llm_section = False
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped == "llm:":
                in_llm_section = True
                continue
            if in_llm_section:
                if stripped and not stripped.startswith("#"):
                    if ":" in stripped and not line.startswith(" "):
                        # New top-level section
                        in_llm_section = False
                        continue
                    if ":" in stripped:
                        key, _, value = stripped.partition(":")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == "base_url":
                            config["base_url"] = value
                        elif key == "api_key":
                            config["api_key"] = value
                        elif key == "model":
                            config["model"] = value
                        elif key == "temperature":
                            config["temperature"] = float(value)
                        elif key == "timeout":
                            config["timeout"] = int(value)
    except Exception:
        pass

    return config


def _load_env_config(path: Path) -> dict[str, Any]:
    """Load configuration from .env file."""
    config = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    # Map env vars to config keys
                    if key in ("HELEN_BASE_URL", "DASHSCOPE_BASE_URL", "OPENAI_BASE_URL"):
                        config["base_url"] = value
                    elif key in ("HELEN_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY"):
                        config["api_key"] = value
                    elif key in ("HELEN_MODEL", "DEFAULT_MODEL"):
                        config["model"] = value
                    elif key in ("HELEN_TEMPERATURE", "TEMPERATURE"):
                        config["temperature"] = float(value)
                    elif key in ("HELEN_TIMEOUT", "TIMEOUT"):
                        config["timeout"] = int(value)
    except Exception:
        pass

    return config


def save_config(config: dict[str, Any]) -> Path:
    """Save configuration to ~/.helen/config.yaml.

    Args:
        config: Configuration dictionary

    Returns:
        Path to saved config file
    """
    get_helen_home()  # Ensure directory exists

    config_path = HELEN_HOME / "config.yaml"

    # Build YAML content
    lines = ["# Helen configuration", ""]

    if "base_url" in config or "api_key" in config or "model" in config:
        lines.append("llm:")
        if "base_url" in config:
            lines.append(f'  base_url: "{config["base_url"]}"')
        if "api_key" in config:
            lines.append(f'  api_key: "{config["api_key"]}"')
        if "model" in config:
            lines.append(f'  model: "{config["model"]}"')
        if "temperature" in config:
            lines.append(f"  temperature: {config['temperature']}")
        if "timeout" in config:
            lines.append(f"  timeout: {config['timeout']}")

    with open(config_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return config_path
