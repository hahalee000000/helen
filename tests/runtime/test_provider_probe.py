"""Tests for helen.runtime.probe — provider connectivity probing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from helen.runtime.probe import (
    ProbeResult,
    _classify_error,
    _make_request,
    _parse_standard_response,
    probe_capabilities,
    probe_connectivity,
    probe_protocol_variants,
    run_full_probe,
)


class TestProbeResult:
    """Test ProbeResult dataclass."""

    def test_default_values(self):
        result = ProbeResult(success=True)
        assert result.success is True
        assert result.error_type is None
        assert result.error_message is None
        assert result.protocol_name is None
        assert result.capabilities == {}

    def test_with_error(self):
        result = ProbeResult(
            success=False,
            error_type="auth",
            error_message="Invalid API key",
        )
        assert result.success is False
        assert result.error_type == "auth"

    def test_with_capabilities(self):
        result = ProbeResult(
            success=True,
            protocol_name="deepseek",
            capabilities={"thinking": True, "vision": False},
        )
        assert result.protocol_name == "deepseek"
        assert result.capabilities["thinking"] is True


class TestClassifyError:
    """Test error classification logic."""

    def test_connection_error(self):
        error_type, msg = _classify_error(-1, None, "Connection refused")
        assert error_type == "connection"
        assert "Connection refused" in msg

    def test_auth_401(self):
        error_type, msg = _classify_error(401, {"error": {"message": "Invalid key"}}, "")
        assert error_type == "auth"

    def test_auth_403(self):
        error_type, msg = _classify_error(403, None, "Forbidden")
        assert error_type == "auth"

    def test_model_not_found_404(self):
        error_data = {"error": {"message": "Model 'xyz' not found"}}
        error_type, msg = _classify_error(404, error_data, "")
        assert error_type == "model_not_found"

    def test_404_generic(self):
        error_type, msg = _classify_error(404, None, "Not found")
        assert error_type == "model_not_found"

    def test_protocol_error_500(self):
        error_data = {"error": {"message": "Internal server error"}}
        error_type, msg = _classify_error(500, error_data, "")
        assert error_type == "protocol"


class TestParseStandardResponse:
    """Test standard response parsing."""

    def test_valid_response(self):
        data = {"choices": [{"message": {"content": "Hello!"}}]}
        result = _parse_standard_response(data)
        assert result is not None
        assert result["content"] == "Hello!"

    def test_response_with_reasoning(self):
        data = {"choices": [{"message": {"content": "2", "reasoning_content": "1+1=2"}}]}
        result = _parse_standard_response(data)
        assert result is not None
        assert result["reasoning_content"] == "1+1=2"

    def test_empty_choices(self):
        assert _parse_standard_response({"choices": []}) is None

    def test_none_data(self):
        assert _parse_standard_response(None) is None

    def test_malformed_data(self):
        assert _parse_standard_response({"unexpected": "format"}) is None


class TestProbeConnectivity:
    """Test Layer 1 connectivity probe."""

    def _mock_response(self, status_code=200, json_data=None, text=""):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {}
        mock_resp.text = text
        return mock_resp

    @patch("helen.runtime.probe.httpx.Client")
    def test_success_openai(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = self._mock_response(
            200, {"choices": [{"message": {"content": "Hi!"}}]}
        )

        result = probe_connectivity("https://api.openai.com/v1", "sk-test", "gpt-4")
        assert result.success is True
        assert result.protocol_name == "openai"

    @patch("helen.runtime.probe.httpx.Client")
    def test_success_dashscope(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = self._mock_response(
            200, {"choices": [{"message": {"content": "Hi!"}}]}
        )

        result = probe_connectivity("https://dashscope.aliyuncs.com/v1", "sk-test", "qwen-plus")
        assert result.success is True
        assert result.protocol_name == "dashscope"

    @patch("helen.runtime.probe.httpx.Client")
    def test_connection_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        result = probe_connectivity("https://bad-url.com/v1", "sk-test", "model")
        assert result.success is False
        assert result.error_type == "connection"

    @patch("helen.runtime.probe.httpx.Client")
    def test_timeout_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("Timed out")

        result = probe_connectivity("https://slow.com/v1", "sk-test", "model")
        assert result.success is False
        assert result.error_type == "connection"

    @patch("helen.runtime.probe.httpx.Client")
    def test_auth_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = self._mock_response(
            401, {"error": {"message": "Invalid API key"}}, "Unauthorized"
        )

        result = probe_connectivity("https://api.openai.com/v1", "bad-key", "gpt-4")
        assert result.success is False
        assert result.error_type == "auth"

    @patch("helen.runtime.probe.httpx.Client")
    def test_model_not_found(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = self._mock_response(
            404, {"error": {"message": "Model 'xyz' not found"}}, "Not found"
        )

        result = probe_connectivity("https://api.openai.com/v1", "sk-test", "xyz")
        assert result.success is False
        assert result.error_type == "model_not_found"

    @patch("helen.runtime.probe.httpx.Client")
    def test_protocol_mismatch(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        # 200 but unparseable
        mock_client.post.return_value = self._mock_response(200, {"unexpected": "format"})

        result = probe_connectivity("https://unknown.com/v1", "sk-test", "model")
        assert result.success is False
        assert result.error_type == "protocol"


class TestProbeProtocolVariants:
    """Test Layer 2 protocol variant detection."""

    def _mock_response(self, status_code=200, json_data=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {}
        mock_resp.text = ""
        return mock_resp

    @patch("helen.runtime.probe.httpx.Client")
    def test_deepseek_match(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        # DashScope fails, DeepSeek succeeds with reasoning
        responses = [
            self._mock_response(400),  # DashScope fails
            self._mock_response(
                200,
                {"choices": [{"message": {"content": "2", "reasoning_content": "1+1=2"}}]},
            ),  # DeepSeek matches
        ]
        mock_client.post.side_effect = responses

        result = probe_protocol_variants("https://unknown.com/v1", "sk-test", "model")
        assert result is not None
        name, caps = result
        assert name == "deepseek"
        assert caps.get("thinking") is True

    @patch("helen.runtime.probe.httpx.Client")
    def test_no_match(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        # All variants fail
        mock_client.post.return_value = self._mock_response(400)

        result = probe_protocol_variants("https://unknown.com/v1", "sk-test", "model")
        assert result is None


class TestProbeCapabilities:
    """Test Layer 3 capability probing."""

    def _mock_response(self, status_code=200, json_data=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {}
        mock_resp.text = ""
        return mock_resp

    @patch("helen.runtime.probe.httpx.Client")
    def test_vision_supported(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Vision succeeds, tool_choice fails
        responses = [
            self._mock_response(200, {"choices": [{"message": {"content": "A dot"}}]}),
            self._mock_response(400),  # tool_choice "required" fails
        ]
        mock_client.post.side_effect = responses

        caps = probe_capabilities("https://api.openai.com/v1", "sk-test", "gpt-4")
        assert caps["vision"] is True
        assert caps["tool_choice_required"] is False

    @patch("helen.runtime.probe.httpx.Client")
    def test_vision_not_supported(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        # Both probes fail
        mock_client.post.return_value = self._mock_response(400)

        caps = probe_capabilities("https://unknown.com/v1", "sk-test", "model")
        assert caps["vision"] is False
        assert caps["tool_choice_required"] is False


class TestRunFullProbe:
    """Test full probe orchestration."""

    def _mock_response(self, status_code=200, json_data=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {}
        mock_resp.text = ""
        return mock_resp

    @patch("helen.runtime.probe.httpx.Client")
    def test_shallow_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = self._mock_response(
            200, {"choices": [{"message": {"content": "Hi"}}]}
        )

        result = run_full_probe("https://api.openai.com/v1", "sk-test", "gpt-4", deep=False)
        assert result.success is True
        assert result.protocol_name == "openai"

    @patch("helen.runtime.probe.httpx.Client")
    def test_shallow_hard_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("refused")

        result = run_full_probe("https://bad.com/v1", "sk-test", "model", deep=False)
        assert result.success is False
        assert result.error_type == "connection"

    @patch("helen.runtime.probe.httpx.Client")
    def test_deep_protocol_match(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Layer 1: protocol mismatch; Layer 2: DeepSeek matches
        responses = [
            self._mock_response(200, {"unexpected": "format"}),  # Layer 1: unparseable
            self._mock_response(400),  # DashScope fails
            self._mock_response(
                200,
                {"choices": [{"message": {"content": "2", "reasoning_content": "1+1=2"}}]},
            ),  # DeepSeek matches
        ]
        mock_client.post.side_effect = responses

        result = run_full_probe("https://unknown.com/v1", "sk-test", "model", deep=True)
        assert result.success is True
        assert result.protocol_name == "deepseek"

    @patch("helen.runtime.probe.httpx.Client")
    def test_shallow_protocol_mismatch_no_deep(self, mock_client_cls):
        """Without deep=True, protocol mismatch returns immediately."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = self._mock_response(200, {"unexpected": "format"})

        result = run_full_probe("https://unknown.com/v1", "sk-test", "model", deep=False)
        assert result.success is False
        assert result.error_type == "protocol"
