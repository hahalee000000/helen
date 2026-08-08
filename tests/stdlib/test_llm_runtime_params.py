"""Tests for v1.39.8 runtime LLM parameter override stdlib functions."""

import pytest
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


def _make_interp() -> Interpreter:
    return Interpreter(llm_runtime=MockLLMRuntime())


class TestRuntimeOverrides:
    """Test _runtime_overrides dict on interpreter."""

    def test_default_empty(self):
        interp = _make_interp()
        assert interp._runtime_overrides == {}

    def test_set_temperature(self):
        interp = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _set_temperature, _get_temperature
        _set_interpreter_ref(interp)
        _set_temperature(0.3)
        assert _get_temperature() == 0.3
        assert interp._runtime_overrides["temperature"] == 0.3
        _set_interpreter_ref(None)

    def test_set_max_turns(self):
        interp = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _set_max_turns, _get_max_turns
        _set_interpreter_ref(interp)
        _set_max_turns(5)
        assert _get_max_turns() == 5
        _set_interpreter_ref(None)

    def test_set_max_tokens(self):
        interp = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _set_max_tokens, _get_max_tokens
        _set_interpreter_ref(interp)
        _set_max_tokens(4000)
        assert _get_max_tokens() == 4000
        _set_interpreter_ref(None)

    def test_set_thinking_mode(self):
        interp = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _set_thinking_mode, _get_thinking_mode
        _set_interpreter_ref(interp)
        _set_thinking_mode(True)
        assert _get_thinking_mode() is True
        _set_interpreter_ref(None)

    def test_set_reasoning_effort(self):
        interp = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _set_reasoning_effort, _get_reasoning_effort
        _set_interpreter_ref(interp)
        _set_reasoning_effort("high")
        assert _get_reasoning_effort() == "high"
        _set_interpreter_ref(None)

    def test_get_defaults_when_no_override(self):
        interp = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _get_temperature, _get_max_turns, _get_max_tokens
        _set_interpreter_ref(interp)
        assert _get_temperature() == 1.0
        assert _get_max_turns() == 1
        assert _get_max_tokens() is None
        _set_interpreter_ref(None)

    def test_get_identity_params_no_agent(self):
        interp = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _get_model, _get_description, _get_provider
        _set_interpreter_ref(interp)
        assert _get_model() is None
        assert _get_description() is None
        assert _get_provider() is None
        _set_interpreter_ref(None)

    def test_no_interpreter_ref_is_safe(self):
        """All functions should be safe when _interpreter_ref is None."""
        from helen.stdlib.llm_control import (
            _set_interpreter_ref, _set_temperature, _get_temperature,
            _set_max_turns, _get_max_turns, _set_max_tokens, _get_max_tokens,
            _set_thinking_mode, _get_thinking_mode,
            _set_reasoning_effort, _get_reasoning_effort,
            _get_model, _get_description, _get_provider,
        )
        _set_interpreter_ref(None)
        # set_* should silently do nothing
        _set_temperature(0.5)
        _set_max_turns(3)
        _set_max_tokens(1000)
        _set_thinking_mode(True)
        _set_reasoning_effort("low")
        # get_* should return defaults
        assert _get_temperature() == 1.0
        assert _get_max_turns() == 1
        assert _get_max_tokens() is None
        assert _get_thinking_mode() is None
        assert _get_reasoning_effort() is None
        assert _get_model() is None
        assert _get_description() is None
        assert _get_provider() is None

    def test_per_interpreter_isolation(self):
        """Two interpreters should have independent overrides."""
        interp_a = _make_interp()
        interp_b = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _set_temperature, _get_temperature
        _set_interpreter_ref(interp_a)
        _set_temperature(0.2)
        _set_interpreter_ref(interp_b)
        _set_temperature(0.8)
        _set_interpreter_ref(interp_a)
        assert _get_temperature() == 0.2
        _set_interpreter_ref(interp_b)
        assert _get_temperature() == 0.8
        _set_interpreter_ref(None)

    def test_override_replaces_previous(self):
        interp = _make_interp()
        from helen.stdlib.llm_control import _set_interpreter_ref, _set_temperature, _get_temperature
        _set_interpreter_ref(interp)
        _set_temperature(0.5)
        assert _get_temperature() == 0.5
        _set_temperature(0.9)
        assert _get_temperature() == 0.9
        _set_interpreter_ref(None)


class TestStdlibRegistration:
    """Test that new functions are registered in stdlib."""

    def test_functions_registered(self):
        from helen.stdlib import stdlib
        expected = [
            "set_temperature", "get_temperature",
            "set_max_turns", "get_max_turns",
            "set_max_tokens", "get_max_tokens",
            "set_thinking_mode", "get_thinking_mode",
            "set_reasoning_effort", "get_reasoning_effort",
            "get_model", "get_description", "get_provider",
        ]
        for name in expected:
            assert stdlib.lookup(name) is not None, f"{name} not registered"

    def test_chinese_aliases(self):
        from helen.stdlib import stdlib
        alias_pairs = [
            ("设置温度", "set_temperature"),
            ("获取温度", "get_temperature"),
            ("设置最大轮次", "set_max_turns"),
            ("设置思考模式", "set_thinking_mode"),
            ("获取模型", "get_model"),
        ]
        for zh, canonical in alias_pairs:
            assert stdlib.lookup(zh) is not None, f"Chinese alias '{zh}' not found"
