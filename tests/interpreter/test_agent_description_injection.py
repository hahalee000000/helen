"""Test that an agent's ``description`` field is injected into the LLM system
prompt (v1.27.2 fix).

Bug: ``_get_agent_setting("description")`` always returned ``None`` because the
``field_map`` in ``llm_mixin.py`` only contained ``model`` / ``temperature`` /
``max-turns``. As a result, the ``description "..."`` clause declared on an
agent never reached the system prompt assembled for ``llm act`` (nor the
``system_prompt`` passed by the streaming path in ``interpreter.py``).
"""

import pytest
from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


def _run(source: str, mock: MockLLMRuntime | None = None) -> MockLLMRuntime:
    """Parse + interpret ``source``; return the mock runtime capturing calls."""
    errors = ErrorReporter()
    tokens = Scanner(source=source, file='<test>').scan_all()
    program = Parser(tokens, errors).parse()
    assert not errors.has_errors, [str(e) for e in errors._errors]

    runtime = mock or MockLLMRuntime(act_return="ok")
    interp = Interpreter(errors=errors, llm_runtime=runtime)
    interp.interpret(program)
    return runtime


class TestAgentDescriptionInjection:
    """v1.27.2: ``description`` reaches the LLM system prompt."""

    def test_description_injected_into_system_prompt(self):
        """The description string appears in the system_prompt sent to the LLM."""
        source = '''
        agent Greeter() {
            description "You are SENTINEL_DESC_42 a helpful greeter."
            main {
                return llm act "hi"
            }
        }
        main {
            print(Greeter())
        }
        '''
        mock = _run(source)

        assert len(mock.act_history) >= 1, "llm act was not invoked"
        system_prompt = mock.act_history[-1]["system_prompt"] or ""
        assert "SENTINEL_DESC_42" in system_prompt, \
            f"description missing from system_prompt: {system_prompt!r}"

    def test_description_absent_when_not_declared(self):
        """An agent without a description still builds a system prompt, just
        without a description section (and without crashing)."""
        source = '''
        agent Plain() {
            main {
                return llm act "hi"
            }
        }
        main {
            print(Plain())
        }
        '''
        mock = _run(source)

        assert len(mock.act_history) >= 1
        system_prompt = mock.act_history[-1]["system_prompt"] or ""
        # Framework instructions + helen conventions are always present.
        assert "framework_instructions" in system_prompt
        assert "helen_conventions" in system_prompt

    def test_get_agent_setting_returns_description(self):
        """Direct unit test: _get_agent_setting("description") returns the
        declared description string (was always None before the fix)."""
        source = '''
        agent Worker() {
            description "MARKER_GET_SETTING"
            main {
                return "ok"
            }
        }
        main {
            print(Worker())
        }
        '''
        errors = ErrorReporter()
        tokens = Scanner(source=source, file='<test>').scan_all()
        program = Parser(tokens, errors).parse()
        assert not errors.has_errors

        interp = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
        interp.interpret(program)

        # After interpreting, _current_agent points at the last-invoked agent.
        assert interp._current_agent is not None
        assert interp._get_agent_setting("description") == "MARKER_GET_SETTING"
        # Other settings still resolve (regression guard).
        assert interp._get_agent_setting("nonexistent", "fallback") == "fallback"

    def test_chinese_description_injected(self):
        """A CJK description string is injected verbatim."""
        source = '''
        agent 中文助手() {
            description "你是一个哨兵标记_中文"
            main {
                return llm act "你好"
            }
        }
        main {
            print(中文助手())
        }
        '''
        mock = _run(source)

        assert len(mock.act_history) >= 1
        system_prompt = mock.act_history[-1]["system_prompt"] or ""
        assert "哨兵标记_中文" in system_prompt

    def test_description_outside_agent_is_none(self):
        """llm act at module scope (no current agent) must not crash and must
        leave description unset - the framework/conventions still apply."""
        source = '''
        main {
            print(llm act "hi")
        }
        '''
        mock = _run(source)

        assert len(mock.act_history) >= 1
        system_prompt = mock.act_history[-1]["system_prompt"] or ""
        assert "framework_instructions" in system_prompt
