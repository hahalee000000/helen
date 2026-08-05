"""Tests for thinking mode support (v1.36)."""

import pytest
from helen.core.tokens import TokenType, keywords
from helen.core.parser import Parser
from helen.core.lexer import Scanner


class TestThinkingModeKeywords:
    """Test new thinking mode keywords are properly registered."""

    def test_thinking_mode_english_keyword(self):
        """'thinking-mode' should be a registered keyword."""
        kw = keywords()
        assert "thinking-mode" in kw
        assert kw["thinking-mode"] == TokenType.THINKING_MODE

    def test_thinking_mode_chinese_keyword(self):
        """'思考模式' should be a registered keyword."""
        kw = keywords()
        assert "思考模式" in kw
        assert kw["思考模式"] == TokenType.THINKING_MODE

    def test_reasoning_effort_english_keyword(self):
        """'reasoning-effort' should be a registered keyword."""
        kw = keywords()
        assert "reasoning-effort" in kw
        assert kw["reasoning-effort"] == TokenType.REASONING_EFFORT

    def test_reasoning_effort_chinese_keyword(self):
        """'推理强度' should be a registered keyword."""
        kw = keywords()
        assert "推理强度" in kw
        assert kw["推理强度"] == TokenType.REASONING_EFFORT

    def test_provider_is_context_keyword(self):
        """'provider' should NOT be a formal keyword (it's a context keyword for llm act).

        v1.36: provider is used as a clause in llm act (e.g., llm act "x" provider("openai")),
        so it cannot be a reserved keyword. 提供商 is handled as a context keyword too.
        """
        kw = keywords()
        # provider should NOT be in formal keywords
        assert "provider" not in kw
        # 提供商 should NOT be in formal keywords either (context keyword)
        assert "提供商" not in kw


class TestThinkingModeParsing:
    """Test thinking mode parsing in agent declarations."""

    def _parse_agent(self, source: str):
        """Helper to parse an agent declaration."""
        scanner = Scanner(source, "test.helen")
        tokens = scanner.scan_all()
        parser = Parser(tokens, "test.helen")
        program = parser.parse()
        # Find the agent declaration in program statements
        for stmt in program.statements:
            if hasattr(stmt, 'declarations'):
                return stmt
        return None

    def test_parse_thinking_mode_true(self):
        """Parse thinking-mode true in agent declaration."""
        source = '''
agent 助手() {
    描述 "测试"
    思考模式 true
    主函 { 返回 llm act "你好" }
}
'''
        agent = self._parse_agent(source)
        assert agent is not None
        # Find thinking_mode declaration
        thinking_decl = None
        for decl in agent.declarations:
            if decl.thinking_mode is not None:
                thinking_decl = decl
                break
        assert thinking_decl is not None
        assert thinking_decl.thinking_mode.value is True

    def test_parse_thinking_mode_false(self):
        """Parse thinking-mode false in agent declaration."""
        source = '''
agent 助手() {
    描述 "测试"
    思考模式 false
    主函 { 返回 llm act "你好" }
}
'''
        agent = self._parse_agent(source)
        assert agent is not None
        thinking_decl = None
        for decl in agent.declarations:
            if decl.thinking_mode is not None:
                thinking_decl = decl
                break
        assert thinking_decl is not None
        assert thinking_decl.thinking_mode.value is False

    def test_parse_reasoning_effort(self):
        """Parse reasoning-effort in agent declaration."""
        source = '''
agent 助手() {
    描述 "测试"
    推理强度 "high"
    主函 { 返回 llm act "你好" }
}
'''
        agent = self._parse_agent(source)
        assert agent is not None
        effort_decl = None
        for decl in agent.declarations:
            if decl.reasoning_effort is not None:
                effort_decl = decl
                break
        assert effort_decl is not None
        assert effort_decl.reasoning_effort.value == "high"

    def test_parse_english_keywords(self):
        """Parse English thinking-mode and reasoning-effort keywords."""
        source = '''
agent Assistant() {
    description "test"
    thinking-mode true
    reasoning-effort "max"
    main { return llm act "hello" }
}
'''
        agent = self._parse_agent(source)
        assert agent is not None
        thinking_decl = None
        effort_decl = None
        for decl in agent.declarations:
            if decl.thinking_mode is not None:
                thinking_decl = decl
            if decl.reasoning_effort is not None:
                effort_decl = decl
        assert thinking_decl is not None
        assert thinking_decl.thinking_mode.value is True
        assert effort_decl is not None
        assert effort_decl.reasoning_effort.value == "max"

    def test_parse_provider_override(self):
        """Parse provider override in agent declaration."""
        source = '''
agent 助手() {
    描述 "测试"
    提供商 "智谱"
    主函 { 返回 llm act "你好" }
}
'''
        agent = self._parse_agent(source)
        assert agent is not None
        provider_decl = None
        for decl in agent.declarations:
            if decl.provider is not None:
                provider_decl = decl
                break
        assert provider_decl is not None
        assert provider_decl.provider.value == "智谱"
