"""Tests for hellen.runtime.llm_runtime — LLMRuntime interface and MockLLMRuntime."""

from hellen.runtime.llm_runtime import LLMResponse, MockLLMRuntime


class TestMockLLMRoute:
    def test_route_returns_preset(self):
        runtime = MockLLMRuntime(route_return="query")
        result = runtime.route("test", ["query", "command", "chat"])
        assert result == "query"

    def test_route_returns_none(self):
        runtime = MockLLMRuntime(route_return=None)
        result = runtime.route("test", ["query", "command"])
        assert result is None

    def test_route_records_history(self):
        runtime = MockLLMRuntime(route_return="query")
        runtime.route("classify input", ["a", "b"], context="ctx")
        assert len(runtime.route_history) == 1
        assert runtime.route_history[0]["description"] == "classify input"
        assert runtime.route_history[0]["branches"] == ["a", "b"]

    def test_route_raises_exception(self):
        from hellen.interpreter.exceptions import TimeoutError

        runtime = MockLLMRuntime(route_fail=TimeoutError("timeout"))
        try:
            runtime.route("test", ["a"])
            assert False, "Should have raised"
        except TimeoutError:
            pass


class TestMockLLMChoose:
    def test_choose_returns_preset(self):
        runtime = MockLLMRuntime(choose_return="option_a")
        result = runtime.choose("pick one", ["option_a", "option_b"])
        assert result == "option_a"

    def test_choose_returns_none(self):
        runtime = MockLLMRuntime(choose_return=None)
        result = runtime.choose("pick", ["a", "b"])
        assert result is None

    def test_choose_records_history(self):
        runtime = MockLLMRuntime(choose_return="a")
        runtime.choose("select", ["a", "b"], context="ctx")
        assert len(runtime.choose_history) == 1
        assert runtime.choose_history[0]["options"] == ["a", "b"]


class TestMockLLMAct:
    def test_act_returns_preset_string(self):
        runtime = MockLLMRuntime(act_return="Hello world")
        response = runtime.act("greet")
        assert isinstance(response, LLMResponse)
        assert response.text == "Hello world"

    def test_act_returns_preset_response(self):
        resp = LLMResponse(text="custom", model="test-model")
        runtime = MockLLMRuntime(act_return=resp)
        response = runtime.act("test")
        assert response is resp
        assert response.text == "custom"

    def test_act_returns_empty_on_none(self):
        runtime = MockLLMRuntime(act_return=None)
        response = runtime.act("test")
        assert response.text == ""

    def test_act_records_history(self):
        runtime = MockLLMRuntime(act_return="hi")
        runtime.act("greet user", temperature=0.5)
        assert len(runtime.act_history) == 1
        assert runtime.act_history[0]["prompt"] == "greet user"
        assert runtime.act_history[0]["temperature"] == 0.5

    def test_act_raises_exception(self):
        from hellen.interpreter.exceptions import ModelError

        runtime = MockLLMRuntime(act_fail=ModelError("quota"))
        try:
            runtime.act("test")
            assert False, "Should have raised"
        except ModelError:
            pass

    def test_reset_clears_history(self):
        runtime = MockLLMRuntime(route_return="a", act_return="hi")
        runtime.route("test", ["a"])
        runtime.act("test")
        runtime.reset()
        assert len(runtime.route_history) == 0
        assert len(runtime.act_history) == 0
