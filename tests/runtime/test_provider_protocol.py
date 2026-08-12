"""Tests for platform protocol abstraction and auto-detection."""

import pytest

from helen.runtime.provider_protocol import (
    DashScopeProtocol,
    DeepSeekProtocol,
    KimiProtocol,
    MinimaxProtocol,
    OpenAIProtocol,
    PlatformProtocol,
    VolcengineProtocol,
    ZhipuProtocol,
    detect_protocol,
)


class TestProtocolDetection:
    """Test auto-detection of platform protocol from base_url."""

    def test_detect_dashscope(self):
        """DashScope should be detected from URL."""
        protocol = detect_protocol("https://dashscope.aliyuncs.com/compatible-mode/v1")
        assert isinstance(protocol, DashScopeProtocol)
        assert protocol.name == "dashscope"

    def test_detect_volcengine(self):
        """Volcengine Ark should be detected from URL."""
        protocol = detect_protocol("https://ark.cn-beijing.volces.com/api/v3")
        assert isinstance(protocol, VolcengineProtocol)
        assert protocol.name == "volcengine"

    def test_detect_zhipu(self):
        """Zhipu should be detected from URL."""
        protocol = detect_protocol("https://open.bigmodel.cn/api/paas/v4")
        assert isinstance(protocol, ZhipuProtocol)
        assert protocol.name == "zhipu"

    def test_detect_deepseek(self):
        """DeepSeek should be detected from URL."""
        protocol = detect_protocol("https://api.deepseek.com")
        assert isinstance(protocol, DeepSeekProtocol)
        assert protocol.name == "deepseek"

    def test_detect_minimax_china(self):
        """MiniMax China should be detected from URL."""
        protocol = detect_protocol("https://api.minimaxi.com/v1")
        assert isinstance(protocol, MinimaxProtocol)
        assert protocol.name == "minimax"

    def test_detect_minimax_international(self):
        """MiniMax International should be detected from URL."""
        protocol = detect_protocol("https://api.minimax.io/v1")
        assert isinstance(protocol, MinimaxProtocol)
        assert protocol.name == "minimax"

    def test_detect_kimi(self):
        """Kimi should be detected from URL."""
        protocol = detect_protocol("https://api.moonshot.ai/v1")
        assert isinstance(protocol, KimiProtocol)
        assert protocol.name == "kimi"

    def test_detect_openai_default(self):
        """Unknown URL should default to OpenAI protocol."""
        protocol = detect_protocol("https://api.openai.com/v1")
        assert isinstance(protocol, OpenAIProtocol)
        assert protocol.name == "openai"

    def test_detect_unknown_provider(self):
        """Unknown provider should default to OpenAI protocol."""
        protocol = detect_protocol("https://some-unknown-api.com/v1")
        assert isinstance(protocol, OpenAIProtocol)


class TestProtocolDetectionByName:
    """Test config-aware protocol detection by explicit name."""

    def test_detect_by_name_deepseek(self):
        """Explicit protocol_name should override URL detection."""
        protocol = detect_protocol("https://unknown.com/v1", protocol_name="deepseek")
        assert isinstance(protocol, DeepSeekProtocol)
        assert protocol.name == "deepseek"

    def test_detect_by_name_dashscope(self):
        """Name takes priority over URL pattern."""
        protocol = detect_protocol("https://api.deepseek.com", protocol_name="dashscope")
        assert isinstance(protocol, DashScopeProtocol)

    def test_detect_by_name_openai(self):
        """Explicit 'openai' name returns OpenAIProtocol."""
        protocol = detect_protocol("https://unknown.com/v1", protocol_name="openai")
        assert isinstance(protocol, OpenAIProtocol)

    def test_detect_by_unknown_name_fallback(self):
        """Unknown protocol_name falls back to URL detection."""
        protocol = detect_protocol("https://api.deepseek.com", protocol_name="nonexistent")
        assert isinstance(protocol, DeepSeekProtocol)  # URL match still works

    def test_detect_by_unknown_name_unknown_url(self):
        """Both name and URL unknown → OpenAI fallback."""
        protocol = detect_protocol("https://unknown.com", protocol_name="nonexistent")
        assert isinstance(protocol, OpenAIProtocol)

    def test_detect_no_name_url_match(self):
        """No name + matching URL → URL-based detection."""
        protocol = detect_protocol("https://api.moonshot.ai/v1")
        assert isinstance(protocol, KimiProtocol)

    def test_detect_all_known_names(self):
        """All known protocol names can be resolved."""
        from helen.runtime.provider_protocol import _PROTOCOL_NAME_MAP
        for name in ["dashscope", "volcengine", "zhipu", "deepseek", "minimax", "kimi", "openai"]:
            assert name in _PROTOCOL_NAME_MAP, f"Missing: {name}"
            protocol = detect_protocol("https://x.com", protocol_name=name)
            assert protocol.name == name


class TestDashScopeProtocol:
    """Test DashScope protocol specifics."""

    def test_build_payload_with_thinking(self):
        """DashScope uses enable_thinking parameter."""
        protocol = DashScopeProtocol()
        payload = {"model": "qwen-plus", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="qwen-plus",
            thinking_enabled=True,
            reasoning_effort="high",
        )
        assert result["enable_thinking"] is True
        assert result["thinking_budget"] == 16384  # high = 16384

    def test_build_payload_without_thinking(self):
        """Without thinking, no extra fields added."""
        protocol = DashScopeProtocol()
        payload = {"model": "qwen-plus", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="qwen-plus",
            thinking_enabled=False,
        )
        assert "enable_thinking" not in result


class TestZhipuProtocol:
    """Test Zhipu protocol specifics."""

    def test_tool_choice_auto_only(self):
        """Zhipu only supports tool_choice='auto'."""
        protocol = ZhipuProtocol()
        assert protocol.supports_tool_choice("auto") is True
        assert protocol.supports_tool_choice("required") is False
        assert protocol.supports_tool_choice("none") is False

    def test_build_payload_with_thinking(self):
        """Zhipu uses thinking.type parameter."""
        protocol = ZhipuProtocol()
        payload = {"model": "glm-5.2", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="glm-5.2",
            thinking_enabled=True,
            reasoning_effort="max",
        )
        assert result["thinking"] == {"type": "enabled"}
        assert result["reasoning_effort"] == "max"


class TestDeepSeekProtocol:
    """Test DeepSeek protocol specifics."""

    def test_build_payload_with_thinking(self):
        """DeepSeek uses thinking.type parameter."""
        protocol = DeepSeekProtocol()
        payload = {"model": "deepseek-v4-pro", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="deepseek-v4-pro",
            thinking_enabled=True,
            reasoning_effort="high",
        )
        assert result["thinking"] == {"type": "enabled"}
        assert result["reasoning_effort"] == "high"


class TestMinimaxProtocol:
    """Test MiniMax protocol specifics."""

    def test_build_payload_always_sets_reasoning_split(self):
        """MiniMax always sets reasoning_split=true."""
        protocol = MinimaxProtocol()
        payload = {"model": "MiniMax-M3", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="MiniMax-M3",
            thinking_enabled=False,
        )
        assert result["reasoning_split"] is True

    def test_parse_response_with_reasoning_details(self):
        """MiniMax returns reasoning_details in response."""
        protocol = MinimaxProtocol()
        response_data = {
            "choices": [{
                "message": {
                    "content": "Answer",
                    "reasoning_content": "Thinking",
                    "reasoning_details": [{"type": "reasoning", "text": "..."}],
                },
                "finish_reason": "stop",
            }],
        }
        result = protocol.parse_response(response_data)
        assert result["content"] == "Answer"
        assert result["reasoning_content"] == "Thinking"
        assert "reasoning_details" in result


class TestKimiProtocol:
    """Test Kimi protocol specifics."""

    def test_extract_streaming_usage_from_choices(self):
        """Kimi: usage at choices[0].usage, not top-level."""
        protocol = KimiProtocol()
        chunk = {
            "choices": [{
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            }],
        }
        usage = protocol.extract_streaming_usage(chunk)
        assert usage == {"prompt_tokens": 10, "completion_tokens": 20}

    def test_extract_streaming_usage_fallback(self):
        """Kimi: fallback to top-level usage if not in choices."""
        protocol = KimiProtocol()
        chunk = {
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "choices": [],
        }
        usage = protocol.extract_streaming_usage(chunk)
        assert usage == {"prompt_tokens": 10, "completion_tokens": 20}


class TestVolcengineProtocol:
    """Test Volcengine protocol specifics."""

    def test_build_payload_with_thinking(self):
        """Volcengine uses thinking.type parameter."""
        protocol = VolcengineProtocol()
        payload = {"model": "doubao-pro", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="doubao-pro",
            thinking_enabled=True,
        )
        assert result["thinking"] == {"type": "enabled"}

    def test_parse_response_with_encrypted_content(self):
        """Volcengine: encrypted_content takes priority."""
        protocol = VolcengineProtocol()
        response_data = {
            "choices": [{
                "message": {
                    "content": "Answer",
                    "reasoning_content": "Normal thinking",
                    "encrypted_content": "Encrypted thinking",
                },
                "finish_reason": "stop",
            }],
        }
        result = protocol.parse_response(response_data)
        assert result["reasoning_content"] == "Encrypted thinking"


class TestBaseProtocol:
    """Test base protocol default behavior."""

    def test_parse_response_standard(self):
        """Standard response parsing."""
        protocol = PlatformProtocol()
        response_data = {
            "choices": [{
                "message": {
                    "content": "Hello",
                    "reasoning_content": "",
                    "tool_calls": [],
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        result = protocol.parse_response(response_data)
        assert result["content"] == "Hello"
        assert result["reasoning_content"] == ""
        assert result["tool_calls"] == []
        assert result["finish_reason"] == "stop"
        assert result["usage"] == {"prompt_tokens": 10, "completion_tokens": 20}

    def test_parse_error_standard(self):
        """Standard error parsing."""
        protocol = PlatformProtocol()
        response_body = {
            "error": {
                "message": "Invalid API key",
                "type": "authentication_error",
            }
        }
        error_msg = protocol.parse_error(401, response_body)
        assert error_msg == "Invalid API key"

    def test_is_context_overflow_error(self):
        """Context overflow detection."""
        protocol = PlatformProtocol()
        assert protocol.is_context_overflow_error("context length exceeded") is True
        assert protocol.is_context_overflow_error("maximum context length") is True
        assert protocol.is_context_overflow_error("too many tokens") is True
        assert protocol.is_context_overflow_error("normal error") is False


class TestBackwardCompatibility:
    """Ensure protocol abstraction doesn't break existing behavior."""

    def test_default_protocol_is_openai(self):
        """Unknown providers should use OpenAI protocol."""
        protocol = detect_protocol("https://unknown-api.com/v1")
        assert isinstance(protocol, OpenAIProtocol)

    def test_payload_building_preserves_existing_fields(self):
        """Protocol should not remove existing payload fields."""
        protocol = OpenAIProtocol()
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
            "tools": [{"type": "function", "function": {"name": "test"}}],
            "max_tokens": 100,
        }
        result = protocol.build_request_payload(
            payload,
            model_id="gpt-4",
            thinking_enabled=False,
        )
        # All original fields should be preserved
        assert result["model"] == "gpt-4"
        assert result["messages"] == payload["messages"]
        assert result["temperature"] == 0.7
        assert result["tools"] == payload["tools"]
        assert result["max_tokens"] == 100


class TestVolcengineEndpointIdValidation:
    """Test Doubao Endpoint ID validation (v1.37)."""

    def test_endpoint_id_accepted_without_warning(self, caplog):
        """Valid endpoint ID (ep-XXXXX) should not log warning."""
        import logging
        protocol = VolcengineProtocol()
        with caplog.at_level(logging.DEBUG, logger='helen.runtime.provider_protocol'):
            payload = protocol.build_request_payload(
                {"model": "ep-20240918xxxxx-xxxxx", "messages": []},
                model_id="ep-20240918xxxxx-xxxxx",
            )
        # No warning about endpoint ID should be logged
        assert not any("instead of Endpoint ID" in r.message for r in caplog.records)

    def test_model_name_logs_debug_warning(self, caplog):
        """Direct model name should log debug warning for production usage."""
        import logging
        protocol = VolcengineProtocol()
        with caplog.at_level(logging.DEBUG, logger='helen.runtime.provider_protocol'):
            protocol.build_request_payload(
                {"model": "doubao-pro-128k", "messages": []},
                model_id="doubao-pro-128k",
            )
        # Debug warning should be logged
        assert any("instead of Endpoint ID" in r.message for r in caplog.records)

    def test_empty_model_id_no_validation(self):
        """Empty model ID should skip validation."""
        protocol = VolcengineProtocol()
        # Should not raise
        payload = protocol.build_request_payload(
            {"model": "", "messages": []},
            model_id="",
        )
        assert payload["model"] == ""


# ---------------------------------------------------------------------------
# Custom Provider Dynamic Loading
# ---------------------------------------------------------------------------


import copy

from helen.runtime import provider_protocol as pp


@pytest.fixture
def isolated_custom_providers(monkeypatch, tmp_path):
    """Isolate custom provider state + redirect providers dir to tmp_path."""
    # Save original state
    original_state = copy.deepcopy(pp._CUSTOM_PROVIDERS_STATE)
    original_map_snapshot = dict(pp._PROTOCOL_NAME_MAP)

    # Reset state for the test
    pp._CUSTOM_PROVIDERS_STATE["loaded"] = False
    pp._CUSTOM_PROVIDERS_STATE["snapshot"] = None
    pp._CUSTOM_PROVIDERS_STATE["loaded_names"] = set()

    # Redirect get_helen_home() so providers dir is under tmp_path
    monkeypatch.setattr(
        "helen.runtime.provider_protocol._get_providers_dir",
        lambda: tmp_path / "providers",
    )

    yield tmp_path / "providers"

    # Restore
    pp._CUSTOM_PROVIDERS_STATE.clear()
    pp._CUSTOM_PROVIDERS_STATE.update(original_state)
    pp._PROTOCOL_NAME_MAP.clear()
    pp._PROTOCOL_NAME_MAP.update(original_map_snapshot)


_VALID_PROVIDER_SOURCE = '''
from helen.runtime.provider_protocol import PlatformProtocol


class FooProtocol(PlatformProtocol):
    name = "foo"

    def build_request_payload(self, base_payload, *, model_id,
                              thinking_enabled=False, reasoning_effort=None):
        base_payload["foo_marker"] = True
        return base_payload
'''


class TestCustomProviderLoading:
    """Test dynamic loading from ~/.helen/providers/."""

    def test_no_providers_dir_is_noop(self, isolated_custom_providers, caplog):
        """Non-existent providers dir should not error."""
        import logging
        with caplog.at_level(logging.WARNING, logger='helen.runtime.provider_protocol'):
            pp._load_custom_providers()
        assert not any("failed" in r.message.lower() for r in caplog.records)
        assert pp._CUSTOM_PROVIDERS_STATE["loaded"] is True
        assert pp._CUSTOM_PROVIDERS_STATE["loaded_names"] == set()

    def test_empty_providers_dir_is_noop(self, isolated_custom_providers):
        """Empty providers dir should not register anything."""
        isolated_custom_providers.mkdir(parents=True)
        pp._load_custom_providers()
        assert pp._CUSTOM_PROVIDERS_STATE["loaded_names"] == set()

    def test_loads_valid_provider_by_name(self, isolated_custom_providers):
        """Custom provider is registered into _PROTOCOL_NAME_MAP by its `name`."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "foo.py").write_text(_VALID_PROVIDER_SOURCE)

        pp._load_custom_providers()

        assert "foo" in pp._PROTOCOL_NAME_MAP
        assert pp._PROTOCOL_NAME_MAP["foo"].name == "foo"
        assert "foo" in pp._CUSTOM_PROVIDERS_STATE["loaded_names"]

    def test_detect_protocol_resolves_custom_name(self, isolated_custom_providers):
        """detect_protocol() with custom provider name should return the custom class."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "foo.py").write_text(_VALID_PROVIDER_SOURCE)

        protocol = pp.detect_protocol("https://unknown.api/v1", protocol_name="foo")
        assert protocol.name == "foo"
        # The override method should actually be called
        payload = protocol.build_request_payload(
            {"model": "m"}, model_id="m",
        )
        assert payload.get("foo_marker") is True

    def test_builtin_name_not_overridden(self, isolated_custom_providers, caplog):
        """Custom provider using a built-in name is skipped."""
        import logging
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        # Try to override the built-in "openai" name
        (providers_dir / "evil.py").write_text('''
from helen.runtime.provider_protocol import OpenAIProtocol


class EvilProtocol(OpenAIProtocol):
    name = "openai"
''')

        with caplog.at_level(logging.DEBUG, logger='helen.runtime.provider_protocol'):
            pp._load_custom_providers()

        # Still the original built-in class
        assert pp._PROTOCOL_NAME_MAP["openai"] is pp.OpenAIProtocol
        assert "openai" not in pp._CUSTOM_PROVIDERS_STATE["loaded_names"]
        assert any("shadows built-in" in r.message for r in caplog.records)

    def test_invalid_python_is_skipped(self, isolated_custom_providers, caplog):
        """Syntactically invalid .py file is logged and skipped."""
        import logging
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "broken.py").write_text("def foo(:\n  this is not python\n")

        # Also write a valid one next to it — should still load
        (providers_dir / "good.py").write_text(_VALID_PROVIDER_SOURCE)

        with caplog.at_level(logging.WARNING, logger='helen.runtime.provider_protocol'):
            pp._load_custom_providers()

        assert any("failed to load" in r.message for r in caplog.records)
        # The good one is still loaded
        assert "foo" in pp._PROTOCOL_NAME_MAP

    def test_file_without_subclass_is_noop(self, isolated_custom_providers):
        """A .py file with no PlatformProtocol subclass registers nothing."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "helper.py").write_text("x = 1\ndef f(): pass\n")

        pp._load_custom_providers()
        assert pp._CUSTOM_PROVIDERS_STATE["loaded_names"] == set()

    def test_class_without_name_is_skipped(self, isolated_custom_providers, caplog):
        """Provider class missing the `name` attribute is skipped with warning."""
        import logging
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "noname.py").write_text('''
from helen.runtime.provider_protocol import PlatformProtocol


class NoNameProtocol(PlatformProtocol):
    pass  # no `name` attribute
''')

        with caplog.at_level(logging.WARNING, logger='helen.runtime.provider_protocol'):
            pp._load_custom_providers()

        assert any("missing explicit `name`" in r.message for r in caplog.records)

    def test_multiple_classes_in_one_file(self, isolated_custom_providers):
        """All PlatformProtocol subclasses in one file are registered."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "multi.py").write_text('''
from helen.runtime.provider_protocol import PlatformProtocol


class AlphaProtocol(PlatformProtocol):
    name = "alpha"


class BetaProtocol(PlatformProtocol):
    name = "beta"
''')

        pp._load_custom_providers()
        assert "alpha" in pp._PROTOCOL_NAME_MAP
        assert "beta" in pp._PROTOCOL_NAME_MAP

    def test_private_files_skipped(self, isolated_custom_providers):
        """Files starting with `_` or `.` should not be loaded."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "_private.py").write_text(_VALID_PROVIDER_SOURCE)
        (providers_dir / ".hidden.py").write_text(_VALID_PROVIDER_SOURCE)
        (providers_dir / "__init__.py").write_text("")

        pp._load_custom_providers()
        assert "foo" not in pp._PROTOCOL_NAME_MAP

    def test_cache_hit_skips_rescan(self, isolated_custom_providers, monkeypatch):
        """Second call with no changes should be a no-op (cache hit)."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "foo.py").write_text(_VALID_PROVIDER_SOURCE)

        pp._load_custom_providers()
        snapshot_after_first = pp._CUSTOM_PROVIDERS_STATE["snapshot"]
        assert "foo" in pp._PROTOCOL_NAME_MAP

        # Replace the loader with a spy to verify _load_one_provider_file isn't called
        spy_calls = []
        original = pp._load_one_provider_file
        def spy(fp):
            spy_calls.append(fp)
            return original(fp)
        monkeypatch.setattr(pp, "_load_one_provider_file", spy)

        pp._load_custom_providers()
        assert spy_calls == [], "Cache hit should not re-scan files"
        assert pp._CUSTOM_PROVIDERS_STATE["snapshot"] == snapshot_after_first

    def test_added_file_triggers_reload(self, isolated_custom_providers):
        """Adding a new file invalidates cache and registers new provider."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)

        pp._load_custom_providers()
        assert "foo" not in pp._PROTOCOL_NAME_MAP

        (providers_dir / "foo.py").write_text(_VALID_PROVIDER_SOURCE)
        pp._load_custom_providers()
        assert "foo" in pp._PROTOCOL_NAME_MAP

    def test_removed_file_unregisters_provider(self, isolated_custom_providers):
        """Removing a file unregisters the custom protocol."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        foo_file = providers_dir / "foo.py"
        foo_file.write_text(_VALID_PROVIDER_SOURCE)

        pp._load_custom_providers()
        assert "foo" in pp._PROTOCOL_NAME_MAP

        foo_file.unlink()
        pp._load_custom_providers()
        assert "foo" not in pp._PROTOCOL_NAME_MAP
        assert "foo" not in pp._CUSTOM_PROVIDERS_STATE["loaded_names"]

    def test_edited_file_applies_changes(self, isolated_custom_providers):
        """Editing a file to add a new class registers the new class."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        foo_file = providers_dir / "foo.py"
        foo_file.write_text(_VALID_PROVIDER_SOURCE)

        pp._load_custom_providers()
        assert "bar" not in pp._PROTOCOL_NAME_MAP

        # Edit the file to add a new class (mtime must change)
        import os, time
        time.sleep(0.05)
        foo_file.write_text(_VALID_PROVIDER_SOURCE + '''

class BarProtocol(PlatformProtocol):
    name = "bar"
''')
        # Force mtime to differ on filesystems with coarse resolution
        new_time = os.path.getmtime(foo_file) + 1
        os.utime(foo_file, (new_time, new_time))

        pp._load_custom_providers()
        assert "bar" in pp._PROTOCOL_NAME_MAP
        assert "foo" in pp._PROTOCOL_NAME_MAP  # Old class still present

    def test_imported_subclass_not_double_registered(self, isolated_custom_providers):
        """Classes imported into the provider file are not re-registered."""
        providers_dir = isolated_custom_providers
        providers_dir.mkdir(parents=True)
        (providers_dir / "reexport.py").write_text('''
# This file re-exports an existing protocol — should NOT register OpenAIProtocol again
from helen.runtime.provider_protocol import OpenAIProtocol  # noqa: F401


class CustomProtocol(OpenAIProtocol):
    name = "custom_reexport"
''')

        pp._load_custom_providers()
        assert "custom_reexport" in pp._PROTOCOL_NAME_MAP
        # The built-in "openai" should remain the original class
        assert pp._PROTOCOL_NAME_MAP["openai"] is pp.OpenAIProtocol

