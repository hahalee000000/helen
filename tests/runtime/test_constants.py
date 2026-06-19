"""Tests for runtime/constants.py to improve coverage.

Verifies all constants are defined with correct types and values.
"""
import pytest

from helen.runtime import constants


class TestLLMConfiguration:
    """LLM configuration constants."""

    def test_default_model(self):
        assert isinstance(constants.DEFAULT_MODEL, str)
        assert len(constants.DEFAULT_MODEL) > 0

    def test_default_base_url(self):
        assert isinstance(constants.DEFAULT_BASE_URL, str)
        assert constants.DEFAULT_BASE_URL.startswith("https://")

    def test_default_fallback_url(self):
        assert isinstance(constants.DEFAULT_FALLBACK_URL, str)
        assert constants.DEFAULT_FALLBACK_URL.startswith("https://")

    def test_default_temperature(self):
        assert isinstance(constants.DEFAULT_TEMPERATURE, float)
        assert 0.0 <= constants.DEFAULT_TEMPERATURE <= 2.0

    def test_default_timeout(self):
        assert isinstance(constants.DEFAULT_TIMEOUT, int)
        assert constants.DEFAULT_TIMEOUT > 0

    def test_default_max_turns(self):
        assert isinstance(constants.DEFAULT_MAX_TURNS, int)
        assert constants.DEFAULT_MAX_TURNS > 0


class TestTokenEstimation:
    """Token estimation constants."""

    def test_chars_per_token(self):
        assert isinstance(constants.CHARS_PER_TOKEN, int)
        assert constants.CHARS_PER_TOKEN > 0

    def test_max_history_tokens(self):
        assert isinstance(constants.MAX_HISTORY_TOKENS, int)
        assert constants.MAX_HISTORY_TOKENS > 1000

    def test_history_buffer_tokens(self):
        assert isinstance(constants.HISTORY_BUFFER_TOKENS, int)
        assert constants.HISTORY_BUFFER_TOKENS > 0


class TestFuzzyMatchThresholds:
    """Fuzzy match threshold constants."""

    def test_thresholds_ordered(self):
        """Thresholds should be in descending order."""
        assert constants.FUZZY_EXACT_THRESHOLD > constants.FUZZY_HIGH_THRESHOLD
        assert constants.FUZZY_HIGH_THRESHOLD > constants.FUZZY_MEDIUM_THRESHOLD
        assert constants.FUZZY_MEDIUM_THRESHOLD > constants.FUZZY_LOW_THRESHOLD
        assert constants.FUZZY_LOW_THRESHOLD > constants.FUZZY_MIN_THRESHOLD

    def test_exact_threshold_is_one(self):
        assert constants.FUZZY_EXACT_THRESHOLD == 1.0

    def test_all_thresholds_positive(self):
        assert constants.FUZZY_HIGH_THRESHOLD > 0
        assert constants.FUZZY_MEDIUM_THRESHOLD > 0
        assert constants.FUZZY_LOW_THRESHOLD > 0
        assert constants.FUZZY_MIN_THRESHOLD > 0


class TestToolLimits:
    """Tool limit constants."""

    def test_max_read_file_size(self):
        assert isinstance(constants.MAX_READ_FILE_SIZE, int)
        assert constants.MAX_READ_FILE_SIZE > 0

    def test_max_write_file_size(self):
        assert isinstance(constants.MAX_WRITE_FILE_SIZE, int)
        assert constants.MAX_WRITE_FILE_SIZE > 0
        assert constants.MAX_WRITE_FILE_SIZE == 64 * 1024 * 1024

    def test_max_output_size(self):
        assert isinstance(constants.MAX_OUTPUT_SIZE, int)
        assert constants.MAX_OUTPUT_SIZE > 0

    def test_max_diff_size(self):
        assert isinstance(constants.MAX_DIFF_SIZE, int)
        assert constants.MAX_DIFF_SIZE > 0

    def test_max_download_size(self):
        assert isinstance(constants.MAX_DOWNLOAD_SIZE, int)
        assert constants.MAX_DOWNLOAD_SIZE == 100 * 1024 * 1024

    def test_max_response_size(self):
        assert isinstance(constants.MAX_RESPONSE_SIZE, int)
        assert constants.MAX_RESPONSE_SIZE == 8 * 1024 * 1024


class TestTimeoutDefaults:
    """Timeout default constants."""

    def test_default_tool_timeout(self):
        assert isinstance(constants.DEFAULT_TOOL_TIMEOUT, int)
        assert constants.DEFAULT_TOOL_TIMEOUT > 0

    def test_default_shell_timeout(self):
        assert isinstance(constants.DEFAULT_SHELL_TIMEOUT, int)
        assert constants.DEFAULT_SHELL_TIMEOUT > 0

    def test_default_fetch_timeout(self):
        assert isinstance(constants.DEFAULT_FETCH_TIMEOUT, int)
        assert constants.DEFAULT_FETCH_TIMEOUT > 0

    def test_default_download_timeout(self):
        assert isinstance(constants.DEFAULT_DOWNLOAD_TIMEOUT, int)
        assert constants.DEFAULT_DOWNLOAD_TIMEOUT > 0

    def test_max_command_timeout(self):
        assert isinstance(constants.MAX_COMMAND_TIMEOUT, int)
        assert constants.MAX_COMMAND_TIMEOUT >= constants.DEFAULT_SHELL_TIMEOUT


class TestHTTPConfiguration:
    """HTTP configuration constants."""

    def test_default_user_agent(self):
        assert isinstance(constants.DEFAULT_USER_AGENT, str)
        assert "Helen" in constants.DEFAULT_USER_AGENT

    def test_agent_user_agent(self):
        assert isinstance(constants.AGENT_USER_AGENT, str)
        assert "HelenAgent" in constants.AGENT_USER_AGENT

    def test_default_chunk_size(self):
        assert isinstance(constants.DEFAULT_CHUNK_SIZE, int)
        assert constants.DEFAULT_CHUNK_SIZE > 0


class TestWikipediaAPI:
    """Wikipedia API URL constants."""

    def test_wiki_summary_url(self):
        assert isinstance(constants.WIKI_SUMMARY_URL, str)
        assert "wikipedia" in constants.WIKI_SUMMARY_URL

    def test_wiki_search_url(self):
        assert isinstance(constants.WIKI_SEARCH_URL, str)
        assert "wikipedia" in constants.WIKI_SEARCH_URL


class TestConfigPaths:
    """Config path constants."""

    def test_config_filename(self):
        assert constants.CONFIG_FILENAME == "config.yaml"

    def test_helen_home_dirname(self):
        assert constants.HELEN_HOME_DIRNAME == ".helen"
