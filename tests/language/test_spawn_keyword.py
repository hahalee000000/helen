"""Tests for spawn/分生 keyword rename (Phase 7)."""

import pytest
from helen.core.tokens import TokenType, keywords
from helen.core.lexer import Scanner


class TestSpawnKeyword:
    """Phase 7: spawnagent → spawn/分生 keyword rename."""

    def _scan(self, source_text: str):
        scanner = Scanner(source=source_text)
        return scanner.scan_all()

    def test_spawn_keyword_tokenizes(self):
        """`spawn` tokenizes to TokenType.SPAWN."""
        tokens = self._scan("spawn")
        spawn_tokens = [t for t in tokens if t.type == TokenType.SPAWN]
        assert len(spawn_tokens) == 1
        assert spawn_tokens[0].lexeme == "spawn"

    def test_fensheng_chinese_keyword_tokenizes(self):
        """`分生` tokenizes to TokenType.SPAWN."""
        tokens = self._scan("分生")
        spawn_tokens = [t for t in tokens if t.type == TokenType.SPAWN]
        assert len(spawn_tokens) == 1
        assert spawn_tokens[0].lexeme == "分生"

    def test_spawnagent_no_longer_keyword(self):
        """`spawnagent` is no longer a valid keyword."""
        kw = keywords()
        assert "spawnagent" not in kw

    def test_shengcheng_no_longer_spawn(self):
        """`生成` is no longer mapped to SPAWN token."""
        kw = keywords()
        # 生成 might not be in keywords at all now (used only for on_generate)
        if "生成" in kw:
            assert kw["生成"] != TokenType.SPAWN

    def test_spawn_keyword_count_unchanged(self):
        """Total keyword count stays at 89 (renamed, not added/removed)."""
        kw = keywords()
        assert len(kw) == 89

    def test_spawn_expr_node_exists(self):
        """SpawnExprNode exists in AST module."""
        from helen.core.ast import SpawnExprNode
        assert SpawnExprNode is not None

    def test_spawnagent_expr_node_removed(self):
        """SpawnagentExprNode no longer exists."""
        import helen.core.ast as ast_module
        assert not hasattr(ast_module, "SpawnagentExprNode")

    def test_spawn_parses_as_expression(self):
        """`spawn Worker("task")` parses without error."""
        from helen.core.parser import Parser
        from helen.core.errors import ErrorReporter

        scanner = Scanner(source='spawn Worker("task")')
        tokens = scanner.scan_all()
        errors = ErrorReporter()
        parser = Parser(tokens, errors)
        program = parser.parse()

        # Just verify parsing doesn't crash
        assert program is not None


class TestSpawnVisitorRenamed:
    """Verify visitor methods are renamed."""

    def test_visitor_has_visit_spawn_expr(self):
        """Visitor abstract class has visit_spawn_expr method."""
        from helen.core.ast import Visitor
        assert hasattr(Visitor, 'visit_spawn_expr')

    def test_visitor_no_visit_spawnagent_expr(self):
        """Visitor no longer has visit_spawnagent_expr method."""
        from helen.core.ast import Visitor
        assert not hasattr(Visitor, 'visit_spawnagent_expr')

    def test_interpreter_has_visit_spawn_expr(self):
        """Interpreter has visit_spawn_expr method."""
        from helen.interpreter.interpreter import Interpreter
        assert hasattr(Interpreter, 'visit_spawn_expr')

    def test_analyzer_has_visit_spawn_expr(self):
        """SemanticAnalyzer has visit_spawn_expr method."""
        from helen.semantic.analyzer import SemanticAnalyzer
        assert hasattr(SemanticAnalyzer, 'visit_spawn_expr')


class TestStdlibAliases:
    """Verify Chinese stdlib aliases for LLM control functions."""

    def test_cancel_llm_call_registered(self):
        from helen.stdlib import stdlib
        assert stdlib.lookup("cancel_llm_call") is not None

    def test_current_llm_call_id_registered(self):
        from helen.stdlib import stdlib
        assert stdlib.lookup("current_llm_call_id") is not None

    def test_cancel_all_llm_calls_registered(self):
        from helen.stdlib import stdlib
        assert stdlib.lookup("cancel_all_llm_calls") is not None

    def test_chinese_aliases_exist(self):
        """Chinese aliases for LLM control functions are registered."""
        from helen.stdlib.locales.zh import ALIASES
        assert "取消大模型调用" in ALIASES
        assert ALIASES["取消大模型调用"] == "cancel_llm_call"
        assert "当前大模型调用id" in ALIASES
        assert "取消所有大模型调用" in ALIASES
