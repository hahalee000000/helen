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
        1. <project>/.helen/skills/ (project-level, highest priority)
        2. ~/.helen/skills/ (user-level)
        3. <helen-install>/skills/ (built-in, distributed with language)
        4. ~/.hermes/skills/ (Hermes fallback)
        5. ~/.hermes/hermes-agent/skills/ (Hermes agent skills)
    """
    dirs = []

    # 1. Project-level skills (highest priority)
    # Look for .helen/skills/ in current working directory and parents
    try:
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            project_skills = parent / ".helen" / "skills"
            if project_skills.exists() and project_skills not in dirs:
                dirs.append(project_skills)
                break  # Only use the closest one
    except (OSError, RuntimeError):
        pass  # cwd may not be accessible

    # 2. User-level skills
    helen_skills = HELEN_HOME / "skills"
    if helen_skills.exists() and helen_skills not in dirs:
        dirs.append(helen_skills)

    # 3. Built-in skills (distributed with Helen language)
    # helen/runtime/config.py -> helen/runtime -> helen -> helen package root
    helen_package = Path(__file__).parent.parent.parent
    builtin_skills = helen_package / "skills"
    if builtin_skills.exists() and builtin_skills not in dirs:
        dirs.append(builtin_skills)

    # 4. Hermes fallback
    hermes_skills = HERMES_HOME / "skills"
    if hermes_skills.exists() and hermes_skills not in dirs:
        dirs.append(hermes_skills)

    hermes_agent_skills = HERMES_HOME / "hermes-agent" / "skills"
    if hermes_agent_skills.exists() and hermes_agent_skills not in dirs:
        dirs.append(hermes_agent_skills)

    return dirs


def get_locale() -> str:
    """Get the configured locale for stdlib aliases and error messages.

    Returns the locale code (e.g., "zh", "en", "ja"). Defaults to "zh"
    if not configured. The locale affects:
    - Which stdlib aliases are prioritized in docs/LSP completions
    - Error message language
    - Template generation in `helen init`

    Note: stdlib aliases are always loaded regardless of locale — the
    locale only affects presentation, not capability.
    """
    config = load_config()
    locale = config.get("locale")
    if locale and isinstance(locale, str):
        return locale
    # Default locale: use environment LANG if available, otherwise zh
    import os
    lang = os.environ.get("LANG", "")
    if lang.startswith("zh"):
        return "zh"
    if lang.startswith("ja"):
        return "ja"
    if lang.startswith("ko"):
        return "ko"
    # Default to Chinese (Helen's primary audience)
    return "zh"


def get_locale_aliases() -> dict[str, str]:
    """Get the alias table for the configured locale.

    Returns:
        Dict mapping alias names to canonical stdlib names.
    """
    from helen.stdlib.locales import all_aliases
    locale = get_locale()
    all_locales = all_aliases()
    return all_locales.get(locale, {})


def get_transcript_config() -> dict[str, Any]:
    """Get transcript configuration.

    Returns:
        Dict with transcript settings:
        - enabled: bool (default: True)
        - backend: str (default: "jsonl")
        - session_dir: str (default: "~/.helen/sessions")
        - max_memory_items: int (default: 1000)

    Example config.yaml:
        transcript:
          enabled: true
          backend: "jsonl"
          session_dir: "~/.helen/sessions"
          max_memory_items: 1000
    """
    config = load_config()
    transcript_config = config.get("transcript", {})

    # Apply defaults
    return {
        "enabled": transcript_config.get("enabled", True),
        "backend": transcript_config.get("backend", "jsonl"),
        "session_dir": transcript_config.get("session_dir", str(HELEN_HOME / "sessions")),
        "max_memory_items": transcript_config.get("max_memory_items", 1000),
    }


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
        # Transcript configuration
        if "transcript" in data:
            transcript = data["transcript"]
            config["transcript"] = {}
            if "enabled" in transcript:
                config["transcript"]["enabled"] = bool(transcript["enabled"])
            if "backend" in transcript:
                config["transcript"]["backend"] = str(transcript["backend"])
            if "session_dir" in transcript:
                config["transcript"]["session_dir"] = str(transcript["session_dir"])
            if "max_memory_items" in transcript:
                config["transcript"]["max_memory_items"] = int(transcript["max_memory_items"])
        # Locale setting (top-level)
        if "locale" in data:
            config["locale"] = str(data["locale"])
    except ImportError:
        # PyYAML not installed, try simple parsing
        config.update(_parse_yaml_simple(path))
    except Exception as e:
        import logging
        logging.debug("Failed to load YAML config from %s: %s", path, e)

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
    except Exception as e:
        import logging
        logging.debug("Failed to parse simple YAML config from %s: %s", path, e)

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
    except Exception as e:
        import logging
        logging.debug("Failed to load .env config from %s: %s", path, e)

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
