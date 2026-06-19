# Helen Configuration System

## Overview

Helen uses an independent configuration system (`~/.helen/`) that no longer requires Hermes. Configuration is loaded from multiple sources and merged (later overrides earlier).

## File Locations

| Path | Format | Priority |
|------|--------|----------|
| `~/.helen/config.yaml` | YAML | Highest |
| `~/.helen/config.yml` | YAML | High |
| `~/.helen/.env` | .env | Medium |
| `~/.hermes/.env` | .env | Low (fallback) |

## YAML Config Format

```yaml
# ~/.helen/config.yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key: "sk-..."
  model: "gpt-4"
  temperature: 0.7
  timeout: 60
```

## .env Config Format

```bash
# ~/.helen/.env or ~/.hermes/.env
# Multiple provider prefixes supported:
HELEN_API_KEY=***
HELEN_BASE_URL=xxx
# or
DASHSCOPE_API_KEY=***
DASHSCOPE_BASE_URL=xxx
# or
OPENAI_API_KEY=***
OPENAI_BASE_URL=xxx
```

## Skill Directories

Priority order (first match wins for skill lookup):
1. `~/.helen/skills/` — Helen native
2. `~/.hermes/skills/` — Hermes fallback
3. `~/.hermes/hermes-agent/skills/` — Hermes agent skills

## CLI Commands

```bash
helen init              # Create ~/.helen/ with default config.yaml
helen                   # REPL (uses config)
helen run file.helen    # Script mode (uses config)
```

## Code API

```python
from helen.runtime.config import load_config, get_skill_dirs, get_helen_home

config = load_config()       # Merged config dict
skill_dirs = get_skill_dirs() # List[Path] in priority order
home = get_helen_home()      # Path to ~/.helen/
```

## Key Pitfalls

1. **Merge, not first-match**: All existing config files are loaded and merged. A key in `config.yaml` overrides the same key in `.env`, but keys only in `.env` are still present.

2. **Multiple env var prefixes**: `_load_env_config()` recognizes `HELEN_*`, `DASHSCOPE_*`, and `OPENAI_*` prefixes for `API_KEY` and `BASE_URL`. This ensures backward compatibility.

3. **YAML parsing without PyYAML**: `_parse_yaml_simple()` handles basic `key: value` pairs in the `llm:` section without requiring the `pyyaml` package. If PyYAML is installed, `_load_yaml_config()` uses it for full YAML support.

4. **`get_helen_home()` creates the directory**: Calling `get_helen_home()` will create `~/.helen/` if it doesn't exist. This is intentional for `helen init`.

5. **Skill directory existence check**: `get_skill_dirs()` only returns directories that actually exist. Non-existent directories are silently skipped.

## Implementation Files

- `helen/runtime/config.py` — Configuration loading and management
- `helen/cli/__main__.py` — `init_command()` implementation
- `helen/runtime/http_llm.py` — Uses `load_config()` via `_load_hermes_env()`
- `helen/runtime/__init__.py` — `HelenHermesRuntime._find_skill_directories()` uses `get_skill_dirs()`
