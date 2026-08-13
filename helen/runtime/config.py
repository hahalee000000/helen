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

# Configuration file path
CONFIG_FILE = HELEN_HOME / "config.yaml"

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

    # Track whether caller passed an explicit scope. When None, the scope is
    # derived from config, and HELEN_SESSION_DIR env override should apply
    # (it redirects where the CURRENT session lives). But when the caller
    # explicitly asks for "global" or "project", the env override must NOT
    # hijack the resolution — otherwise list_sessions("global") would return
    # the project dir whenever the agent has called set_session_dir().
    explicit_scope = scope is not None
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

    # Env override applies to default/auto resolution only, NOT to explicit
    # global/project scope requests (which must return their true directories).
    if env_override and (not explicit_scope or scope == "auto"):
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

    Loads from two sources (later overrides earlier):
    1. ~/.helen/config.yaml (YAML configuration)
    2. Environment variables: HELEN_BASE_URL, HELEN_API_KEY, HELEN_MODEL

    Returns:
        Configuration dictionary with keys:
        - base_url: LLM API endpoint
        - api_key: API key
        - model: Default model name
        - temperature: Default temperature
        - timeout: Request timeout
    """
    import os

    config = DEFAULT_LLM_CONFIG.copy()

    # Load from config.yaml
    config_path = HELEN_HOME / "config.yaml"
    if config_path.exists():
        yaml_config = _load_yaml_config(config_path)
        for key, value in yaml_config.items():
            if value is not None and value != "":
                config[key] = value

    # Override with environment variables (highest priority)
    env_mappings = {
        "HELEN_BASE_URL": "base_url",
        "HELEN_API_KEY": "api_key",
        "HELEN_MODEL": "model",
    }
    for env_var, config_key in env_mappings.items():
        env_value = os.environ.get(env_var)
        if env_value:
            config[config_key] = env_value

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
            if "protocol" in llm:
                config["protocol"] = str(llm["protocol"])
            if "capabilities" in llm:
                caps = llm["capabilities"]
                if isinstance(caps, dict):
                    config["capabilities"] = {str(k): bool(v) for k, v in caps.items()}
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
    except Exception as e:
        import logging
        logging.debug("Failed to load YAML config from %s: %s", path, e)

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
        if "protocol" in config:
            lines.append(f'  protocol: "{config["protocol"]}"')
        if "capabilities" in config and isinstance(config["capabilities"], dict):
            lines.append("  capabilities:")
            for key, val in config["capabilities"].items():
                lines.append(f"    {key}: {str(val).lower()}")

    with open(config_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return config_path


def is_configured() -> bool:
    """Check if Helen is configured with required LLM settings.

    Returns True if either:
    - config.yaml exists with non-empty api_key, OR
    - HELEN_API_KEY environment variable is set

    Returns:
        True if configured, False otherwise
    """
    import os

    # Check environment variable first (highest priority)
    if os.environ.get("HELEN_API_KEY"):
        return True

    # Check config.yaml
    config_path = HELEN_HOME / "config.yaml"
    if not config_path.exists():
        return False

    try:
        config = _load_yaml_config(config_path)
        api_key = config.get("api_key")
        # Check that api_key exists and is not a placeholder
        return bool(api_key and api_key != "YOUR_API_KEY_HERE")
    except Exception:
        return False


def _print_supported_providers() -> None:
    """Print bilingual list of supported providers."""
    print("  支持的 Provider / Supported providers:")
    print("  • 通义千问 (DashScope)")
    print("  • 火山引擎 (Volcengine)")
    print("  • 智谱 (Zhipu/GLM)")
    print("  • DeepSeek")
    print("  • MiniMax")
    print("  • Kimi (Moonshot)")
    print("  • OpenAI 及兼容平台 / OpenAI compatible platforms")


def _print_custom_provider_hint() -> None:
    """Print bilingual hint about creating custom providers via helen agent."""
    print()
    print("  如需支持此 Provider / To add support for this provider:")
    print("  1. 先配置一个可用的 Helen 环境 / First set up a working Helen environment")
    print("  2. 运行 / Run: helen agent")
    print("  3. 让 agent 生成 PlatformProtocol 子类，保存到 ~/.helen/providers/<name>.py")
    print("     Ask the agent to generate a PlatformProtocol subclass")
    print("     and save it to ~/.helen/providers/<name>.py")


def run_setup_wizard() -> bool:
    """Interactive setup wizard with connectivity probing.

    Flow:
    1. Collect base_url / api_key / model from user
    2. Match against known provider URL patterns
    3. If matched → save config with protocol name → success
    4. If not matched → Layer 1 connectivity probe
       - Hard error (connection/auth/model) → print error, don't save, fail
       - Success → save config, success
       - Protocol mismatch → ask for deep probe
    5. Deep probe (Layer 2+3) if user agrees
    6. Save config with detected protocol/capabilities

    Returns:
        True if configuration was saved successfully, False otherwise
    """
    import getpass

    from helen.runtime.provider_protocol import _PLATFORM_PATTERNS, detect_protocol

    print("=" * 60)
    print("🚀 Helen Setup Wizard")
    print("=" * 60)
    print()
    print("Configure your LLM API settings:")
    print("配置 LLM API 设置：")
    print()

    try:
        # Prompt for base_url
        default_base_url = DEFAULT_LLM_CONFIG["base_url"]
        base_url = input(f"API Base URL [{default_base_url}]: ").strip()
        if not base_url:
            base_url = default_base_url

        # Prompt for api_key (masked)
        print()
        print("Your API key will be masked (input not visible):")
        print("API Key（输入不可见）:")
        api_key = getpass.getpass("API Key: ").strip()
        if not api_key:
            print("❌ Error / 错误: API key is required / API key 不能为空")
            return False

        # Prompt for model
        default_model = DEFAULT_LLM_CONFIG["model"]
        model = input(f"Model [{default_model}]: ").strip()
        if not model:
            model = default_model

        # Step 1: Match known provider by URL pattern
        protocol = detect_protocol(base_url)
        is_known = False
        for pattern, _ in _PLATFORM_PATTERNS:
            if pattern in base_url:
                is_known = True
                break

        if is_known:
            config = {
                "base_url": base_url,
                "api_key": api_key,
                "model": model,
                "protocol": protocol.name,
            }
            config_path = save_config(config)
            print()
            print(f"✅ Detected provider / 检测到 Provider: {protocol.name}")
            print(f"✅ Configuration saved to / 配置已保存: {config_path}")
            print()
            print("You can now run Helen programs:")
            print("现在可以运行 Helen 程序：")
            print("  helen <file.helen>")
            print()
            return True

        # Step 2: Unknown provider — Layer 1 connectivity probe
        print()
        print("⏳ Testing connectivity / 正在测试连通性...")

        from helen.runtime.probe import probe_connectivity

        result = probe_connectivity(base_url, api_key, model)

        if not result.success:
            if result.error_type == "connection":
                print()
                print(f"❌ 无法连接到 {base_url}")
                print(f"   Cannot connect to {base_url}")
                print(f"   {result.error_message}")
                print()
                print("   请检查 URL 是否正确，网络是否通畅")
                print("   Please check the URL and your network connection")
                return False

            elif result.error_type == "auth":
                print()
                print("❌ API Key 无效 / Invalid API Key")
                print(f"   {result.error_message}")
                print()
                print("   请检查 API Key 是否正确")
                print("   Please check your API key")
                return False

            elif result.error_type == "model_not_found":
                print()
                print(f"❌ 模型 '{model}' 不存在 / Model '{model}' not found")
                print(f"   {result.error_message}")
                print()
                print("   请检查模型名称是否正确")
                print("   Please check the model name")
                return False

            else:
                # Protocol mismatch — Layer 1 failed but connection is OK
                print()
                print("⚠️ Provider 协议不完全兼容 / Provider protocol not fully compatible")
                print(f"   {result.error_message}")

                # Ask for deep probe
                print()
                try:
                    deep = input(
                        "是否进行深度探测以检测协议变体？(会消耗少量 API tokens) / "
                        "Deep probe for protocol variants? (costs a few API tokens) [y/N]: "
                    ).strip().lower()
                except (KeyboardInterrupt, EOFError):
                    deep = "n"

                if deep in ("y", "yes", "是"):
                    from helen.runtime.probe import run_full_probe

                    print("⏳ Deep probing / 深度探测中...")
                    deep_result = run_full_probe(base_url, api_key, model, deep=True)

                    if deep_result.success:
                        config = {
                            "base_url": base_url,
                            "api_key": api_key,
                            "model": model,
                            "protocol": deep_result.protocol_name,
                            "capabilities": deep_result.capabilities,
                        }
                        config_path = save_config(config)
                        print()
                        print(f"✅ Detected provider / 检测到 Provider: {deep_result.protocol_name}")
                        caps = deep_result.capabilities
                        if caps:
                            cap_strs = [f"{k}={v}" for k, v in caps.items()]
                            print(f"   Capabilities / 能力: {', '.join(cap_strs)}")
                        print(f"✅ Configuration saved / 配置已保存: {config_path}")
                        print()
                        return True

                    # Deep probe failed — save with fallback + guidance
                    config = {
                        "base_url": base_url,
                        "api_key": api_key,
                        "model": model,
                    }
                    config_path = save_config(config)
                    print()
                    print("⚠️ No matching protocol found. Saved with default protocol.")
                    print("   未找到匹配的协议。已使用默认协议保存。")
                    print(f"   Config saved / 配置已保存: {config_path}")
                    print()
                    _print_supported_providers()
                    _print_custom_provider_hint()
                    print()
                    return True

                # User declined deep probe — save with default
                config = {
                    "base_url": base_url,
                    "api_key": api_key,
                    "model": model,
                }
                config_path = save_config(config)
                print()
                print(f"✅ Configuration saved (default protocol) / 配置已保存（默认协议）: {config_path}")
                print()
                print("If you encounter issues, try deep probe or create a custom adapter:")
                print("如果遇到问题，可尝试深度探测或创建自定义适配器：")
                print("  helen agent")
                print("  # Ask the agent to generate a PlatformProtocol subclass")
                print()
                return True

        # Layer 1 succeeded — save config
        config = {
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "protocol": result.protocol_name or "openai",
        }
        config_path = save_config(config)
        print()
        print("✅ Connectivity OK / 连通性正常")
        print(f"✅ Configuration saved to / 配置已保存: {config_path}")
        print()
        print("You can now run Helen programs:")
        print("现在可以运行 Helen 程序：")
        print(f"  helen <file.helen>")
        print()
        return True

    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user / 设置已被用户取消")
        return False
    except EOFError:
        # Non-interactive environment
        print("\n❌ Error / 错误: Cannot run interactive wizard in non-interactive mode")
        print("   无法在非交互模式下运行设置向导")
        return False
