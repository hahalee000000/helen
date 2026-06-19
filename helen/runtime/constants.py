"""Centralized constants for Helen runtime.

All hardcoded values (URLs, model names, thresholds, limits) are
defined here to ensure consistency and easy configuration.
"""

from __future__ import annotations

from typing import Final

# ── LLM Configuration Defaults ─────────────────────────────────

DEFAULT_MODEL: Final[str] = "qwen3.7-plus"
DEFAULT_BASE_URL: Final[str] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_FALLBACK_URL: Final[str] = "https://coding.dashscope.aliyuncs.com/v1"
DEFAULT_TEMPERATURE: Final[float] = 0.7
DEFAULT_TIMEOUT: Final[int] = 60
DEFAULT_MAX_TURNS: Final[int] = 10

# ── Token Estimation ───────────────────────────────────────────

# Crude heuristic: ~4 characters per token (English text)
CHARS_PER_TOKEN: Final[int] = 4
MAX_HISTORY_TOKENS: Final[int] = 128_000
HISTORY_BUFFER_TOKENS: Final[int] = 1_000

# ── Fuzzy Match Thresholds ────────────────────────────────────

FUZZY_EXACT_THRESHOLD: Final[float] = 1.0
FUZZY_HIGH_THRESHOLD: Final[float] = 0.80
FUZZY_MEDIUM_THRESHOLD: Final[float] = 0.70
FUZZY_LOW_THRESHOLD: Final[float] = 0.50
FUZZY_MIN_THRESHOLD: Final[float] = 0.3

# ── Tool Limits ────────────────────────────────────────────────

MAX_READ_FILE_SIZE: Final[int] = 16_000       # Characters
MAX_WRITE_FILE_SIZE: Final[int] = 64 * 1024 * 1024  # 64 MB
MAX_OUTPUT_SIZE: Final[int] = 8_000           # Characters for tool output
MAX_DIFF_SIZE: Final[int] = 4_000             # Characters for diff output
MAX_DOWNLOAD_SIZE: Final[int] = 100 * 1024 * 1024  # 100 MB
MAX_RESPONSE_SIZE: Final[int] = 8 * 1024 * 1024    # 8 MB

# ── Timeout Defaults ──────────────────────────────────────────

DEFAULT_TOOL_TIMEOUT: Final[int] = 30         # Seconds
DEFAULT_SHELL_TIMEOUT: Final[int] = 30        # Seconds
DEFAULT_FETCH_TIMEOUT: Final[int] = 15        # Seconds
DEFAULT_DOWNLOAD_TIMEOUT: Final[int] = 60     # Seconds
MAX_COMMAND_TIMEOUT: Final[int] = 300         # Seconds

# ── HTTP Configuration ────────────────────────────────────────

DEFAULT_USER_AGENT: Final[str] = "Helen/1.0"
AGENT_USER_AGENT: Final[str] = "HelenAgent/1.0 (https://github.com/hahalee000000/helen)"
DEFAULT_CHUNK_SIZE: Final[int] = 8192         # Bytes for download chunks

# ── Wikipedia API ──────────────────────────────────────────────

WIKI_SUMMARY_URL: Final[str] = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_SEARCH_URL: Final[str] = "https://en.wikipedia.org/w/api.php"

# ── Config Paths ───────────────────────────────────────────────

CONFIG_FILENAME: Final[str] = "config.yaml"
HELEN_HOME_DIRNAME: Final[str] = ".helen"
