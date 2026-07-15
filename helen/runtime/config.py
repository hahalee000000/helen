"""Helen configuration management.

Helen uses its own configuration directory (~/.helen/) for:
- API keys and LLM endpoint configuration
- Skill directories
- Runtime settings
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
    # helen/runtime/config.py -> helen/runtime -> helen (package dir)
    helen_package_dir = Path(__file__).parent.parent
    builtin_skills = helen_package_dir / "skills"
    if builtin_skills.exists() and builtin_skills not in dirs:
        dirs.append(builtin_skills)

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
        - session_scope: str (default: "auto") - "global" | "project" | "auto"
        - session_dir: str (default: "~/.helen/sessions") - used when scope="global"
        - project_session_dir: str (default: ".helen/sessions") - used when scope="project"
        - max_memory_items: int (default: 1000)

    Session scope controls where transcripts are stored:
        "global"  — Always use ~/.helen/sessions/ (user-wide, shared across all apps)
        "project" — Always use .helen/sessions/ in the current working directory
        "auto"    — Use project mode when a Helen project is detected (cwd/.helen/ or
                    cwd/helen.yaml or cwd/helen.toml exists); otherwise use global mode.
                    This is the default since v1.20.

    The HELEN_SESSION_DIR environment variable overrides both session_dir and
    project_session_dir, forcing a specific path regardless of scope.

    Example config.yaml:
        transcript:
          enabled: true
          backend: "jsonl"
          session_scope: "auto"
          session_dir: "~/.helen/sessions"
          project_session_dir: ".helen/sessions"
          max_memory_items: 1000
    """
    config = load_config()
    transcript_config = config.get("transcript", {})

    # Apply defaults
    return {
        "enabled": transcript_config.get("enabled", True),
        "backend": transcript_config.get("backend", "jsonl"),
        "session_scope": transcript_config.get("session_scope", "auto"),
        "session_dir": transcript_config.get("session_dir", str(HELEN_HOME / "sessions")),
        "project_session_dir": transcript_config.get("project_session_dir", ".helen/sessions"),
        "max_memory_items": transcript_config.get("max_memory_items", 1000),
    }


# ---------------------------------------------------------------------------
# Session scope resolution (v1.20)
# ---------------------------------------------------------------------------

# Valid scope values
SESSION_SCOPES = frozenset({"global", "project", "auto"})

# Files/directories that indicate a "Helen project" when present in cwd
PROJECT_MARKERS = (".helen", "helen.yaml", "helen.yml", "helen.toml")


def detect_project_dir(start_dir: str | None = None) -> str | None:
    """Detect the nearest Helen project directory by walking up from start_dir.

    A directory is considered a Helen project if it contains any of:
      - `.helen/` (directory) — but NOT the user's global ``~/.helen``
      - `helen.yaml` / `helen.yml` / `helen.toml`

    Args:
        start_dir: Directory to start searching from. Defaults to cwd.

    Returns:
        Absolute path to the project directory, or None if no project found.
    """
    from pathlib import Path
    import os

    if start_dir is None:
        start_dir = os.getcwd()

    # Resolve the user's global Helen home (~/.helen) so we can skip it
    try:
        helen_home = Path(HELEN_HOME).resolve()
    except Exception:
        helen_home = None

    current = Path(start_dir).resolve()

    # Walk up to filesystem root
    while True:
        for marker in PROJECT_MARKERS:
            candidate = current / marker
            if candidate.exists():
                # Skip the user's global ~/.helen — it's not a project marker
                if marker == ".helen" and helen_home is not None:
                    try:
                        if candidate.resolve() == helen_home:
                            continue
                    except Exception:
                        pass
                return str(current)
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


def resolve_session_dir(
    scope: str | None = None,
    cwd: str | None = None,
    env_override: str | None = None,
) -> tuple[str, str]:
    """Resolve the actual session directory based on scope, env, and project detection.

    Priority (highest first):
    1. env_override (HELEN_SESSION_DIR env var)
    2. Resolved scope-specific path:
       - scope="global"  → ~/.helen/sessions
       - scope="project" → <project_dir>/.helen/sessions (or cwd/.helen/sessions if no project)
       - scope="auto"    → project if project detected, else global

    Args:
        scope: "global" | "project" | "auto" (default: read from config)
        cwd: Current working directory (default: os.getcwd())
        env_override: Override path from environment (default: read HELEN_SESSION_DIR)

    Returns:
        Tuple of (resolved_path: str, detected_scope: str) where detected_scope
        is the actual scope used ("global" or "project"), which may differ from
        the configured scope when scope="auto".
    """
    import os
    from pathlib import Path

    config = get_transcript_config()

    if scope is None:
        scope = config.get("session_scope", "auto")
    if scope not in SESSION_SCOPES:
        import logging
        logging.getLogger(__name__).warning(
            "Unknown session_scope %r, falling back to 'auto'", scope
        )
        scope = "auto"

    if cwd is None:
        cwd = os.getcwd()

    if env_override is None:
        env_override = os.environ.get("HELEN_SESSION_DIR")

    # Env override takes absolute priority
    if env_override:
        return (str(Path(env_override).expanduser().resolve()), "env_override")

    # Resolve based on scope
    if scope == "global":
        return (str(Path(config["session_dir"]).expanduser().resolve()), "global")

    if scope == "project":
        project_dir = detect_project_dir(cwd)
        if project_dir is None:
            # No project found — fall back to cwd
            project_dir = cwd
        base = Path(project_dir) / config.get("project_session_dir", ".helen/sessions")
        return (str(base.resolve()), "project")

    # scope == "auto"
    project_dir = detect_project_dir(cwd)
    if project_dir is not None:
        base = Path(project_dir) / config.get("project_session_dir", ".helen/sessions")
        return (str(base.resolve()), "project")
    else:
        return (str(Path(config["session_dir"]).expanduser().resolve()), "global")


def get_multimodal_config() -> dict[str, Any]:
    """Get multimodal configuration (v1.17 Phase 3).

    Returns:
        Dict with multimodal settings:
        - max_media_size_mb: float (default: 20) - Maximum single media size
        - max_media_per_request: int (default: 10) - Maximum media per llm act
        - media_external_threshold_mb: float (default: 1.0) - Threshold for external storage
        - media_cache_dir: str (default: "~/.helen/media_cache")
        - video_frame_interval: float (default: 1.0) - Video frame extraction interval

    Example config.yaml:
        multimodal:
          max_media_size_mb: 20
          max_media_per_request: 10
          media_external_threshold_mb: 1.0
          media_cache_dir: "~/.helen/media_cache"
          video_frame_interval: 1.0
    """
    config = load_config()
    multimodal_config = config.get("multimodal", {})

    # Apply defaults
    return {
        "max_media_size_mb": multimodal_config.get("max_media_size_mb", 20.0),
        "max_media_per_request": multimodal_config.get("max_media_per_request", 10),
        "media_external_threshold_mb": multimodal_config.get("media_external_threshold_mb", 1.0),
        "media_cache_dir": multimodal_config.get("media_cache_dir", str(HELEN_HOME / "media_cache")),
        "video_frame_interval": multimodal_config.get("video_frame_interval", 1.0),
    }


def load_config() -> dict[str, Any]:
    """Load Helen configuration.

    Loads from multiple sources and merges them:
    1. ~/.helen/.env (Helen .env)
    2. ~/.helen/config.yml (Helen YAML)
    3. ~/.helen/config.yaml (Helen YAML, highest priority)

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
            if "session_scope" in transcript:
                scope = str(transcript["session_scope"])
                if scope in ("global", "project", "auto"):
                    config["transcript"]["session_scope"] = scope
                else:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Invalid session_scope %r in config, expected "
                        "'global' | 'project' | 'auto'", scope
                    )
            if "session_dir" in transcript:
                config["transcript"]["session_dir"] = str(transcript["session_dir"])
            if "project_session_dir" in transcript:
                config["transcript"]["project_session_dir"] = str(transcript["project_session_dir"])
            if "max_memory_items" in transcript:
                config["transcript"]["max_memory_items"] = int(transcript["max_memory_items"])
        # Multimodal configuration (v1.17)
        if "multimodal" in data:
            multimodal = data["multimodal"]
            config["multimodal"] = {}
            if "max_media_size_mb" in multimodal:
                config["multimodal"]["max_media_size_mb"] = float(multimodal["max_media_size_mb"])
            if "max_media_per_request" in multimodal:
                config["multimodal"]["max_media_per_request"] = int(multimodal["max_media_per_request"])
            if "media_external_threshold_mb" in multimodal:
                config["multimodal"]["media_external_threshold_mb"] = float(multimodal["media_external_threshold_mb"])
            if "media_cache_dir" in multimodal:
                config["multimodal"]["media_cache_dir"] = str(multimodal["media_cache_dir"])
            if "video_frame_interval" in multimodal:
                config["multimodal"]["video_frame_interval"] = float(multimodal["video_frame_interval"])
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
