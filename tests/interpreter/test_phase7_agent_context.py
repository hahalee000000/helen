"""Tests for Phase 7: Agent context integration and context {} block parsing.

Phase 7 adds:
1. AgentContextManager integration in llm_mixin
2. context {} block parsing in agent declarations
3. Per-agent context configuration (compression, working-memory, etc.)
"""
import pytest
from helen.core.parser import Parser
from helen.core.lexer import Scanner
from helen.core.ast import AgentDeclNode, ContextConfigNode


class TestContextConfigParsing:
    """Test context {} block parsing in agent declarations."""

    def _parse(self, source: str):
        """Helper to parse Helen source."""
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, source)
        return parser.parse()

    def test_context_block_basic(self):
        """Test basic context block parsing."""
        source = '''
        agent TestAgent {
            description "Test agent"
            context {
                compression "graduated"
                cache-aware true
                working-memory true
                working-memory-tokens 5000
            }
            prompt "test"
            main {
                return "ok"
            }
        }
        '''
        program = self._parse(source)
        assert len(program.statements) == 1
        agent = program.statements[0]
        assert isinstance(agent, AgentDeclNode)
        assert agent.context_config is not None
        assert isinstance(agent.context_config, ContextConfigNode)
        assert agent.context_config.compression == "graduated"
        assert agent.context_config.cache_aware is True
        assert agent.context_config.working_memory is True
        assert agent.context_config.working_memory_tokens == 5000

    def test_context_block_compression_options(self):
        """Test different compression options."""
        for compression in ["none", "graduated", "traditional"]:
            source = f'''
            agent TestAgent {{
                context {{
                    compression "{compression}"
                }}
                main {{}}
            }}
            '''
            program = self._parse(source)
            agent = program.statements[0]
            assert agent.context_config.compression == compression

    def test_context_block_cache_aware_false(self):
        """Test cache-aware set to false."""
        source = '''
        agent TestAgent {
            context {
                cache-aware false
            }
            main {}
        }
        '''
        program = self._parse(source)
        agent = program.statements[0]
        assert agent.context_config.cache_aware is False

    def test_context_block_working_memory_false(self):
        """Test working-memory set to false."""
        source = '''
        agent TestAgent {
            context {
                working-memory false
            }
            main {}
        }
        '''
        program = self._parse(source)
        agent = program.statements[0]
        assert agent.context_config.working_memory is False

    def test_context_block_custom_tokens(self):
        """Test custom working-memory-tokens value."""
        source = '''
        agent TestAgent {
            context {
                working-memory-tokens 10000
            }
            main {}
        }
        '''
        program = self._parse(source)
        agent = program.statements[0]
        assert agent.context_config.working_memory_tokens == 10000

    def test_context_block_minimal(self):
        """Test context block with only one option."""
        source = '''
        agent TestAgent {
            context {
                compression "none"
            }
            main {}
        }
        '''
        program = self._parse(source)
        agent = program.statements[0]
        assert agent.context_config.compression == "none"
        # Other fields should have defaults
        assert agent.context_config.cache_aware is True
        assert agent.context_config.working_memory is True
        assert agent.context_config.working_memory_tokens == 5000

    def test_context_block_chinese_keywords(self):
        """Test context block with Chinese keywords."""
        source = '''
        agent TestAgent {
            context {
                压缩 "graduated"
                缓存感知 true
                工作记忆 true
                工作记忆词元 5000
            }
            main {}
        }
        '''
        program = self._parse(source)
        agent = program.statements[0]
        assert agent.context_config.compression == "graduated"
        assert agent.context_config.cache_aware is True
        assert agent.context_config.working_memory is True
        assert agent.context_config.working_memory_tokens == 5000

    def test_context_block_legacy_chinese_keyword(self):
        """Backward compatibility: legacy 工作记忆令牌 still parses.

        v1.17 renamed LLM-context 令牌 → 词元. The parser accepts both
        forms so existing programs don't break.
        """
        source = '''
        agent TestAgent {
            context {
                工作记忆令牌 8000
            }
            main {}
        }
        '''
        program = self._parse(source)
        agent = program.statements[0]
        assert agent.context_config.working_memory_tokens == 8000

    def test_agent_without_context_block(self):
        """Test agent without context block (should have None context_config)."""
        source = '''
        agent TestAgent {
            description "No context config"
            main {}
        }
        '''
        program = self._parse(source)
        agent = program.statements[0]
        assert agent.context_config is None


class TestAgentContextManagerIntegration:
    """Test AgentContextManager integration in interpreter."""

    def test_agent_context_manager_initialization(self):
        """Test that AgentContextManager is initialized in interpreter."""
        from helen.interpreter.interpreter import Interpreter

        interp = Interpreter()
        assert hasattr(interp, '_agent_context')
        assert interp._agent_context is not None

    def test_agent_context_manager_default_settings(self):
        """Test default AgentContextManager settings."""
        from helen.interpreter.interpreter import Interpreter

        interp = Interpreter()
        assert interp._agent_context.compression_enabled is True
        assert interp._agent_context.working_memory_enabled is True
        assert interp._agent_context.working_memory.max_tokens == 5000

    def test_update_working_memory_from_message(self):
        """Test updating working memory from a message."""
        from helen.interpreter.interpreter import Interpreter

        interp = Interpreter()
        interp._agent_context.update_from_message(
            "Working on src/main.py and fixing bug",
            "assistant"
        )
        # Should have extracted file reference
        assert len(interp._agent_context.working_memory.active_files) > 0

    def test_update_working_memory_from_tool_call(self):
        """Test updating working memory from a tool call."""
        from helen.interpreter.interpreter import Interpreter

        interp = Interpreter()
        interp._agent_context.update_from_tool_call(
            "read_file",
            {"path": "/test/file.py"},
            "file contents"
        )
        assert "/test/file.py" in interp._agent_context.working_memory.active_files

    def test_update_working_memory_from_tool_call_string_args(self):
        """Regression: update_from_tool_call must accept JSON-string args.

        The production caller in llm_mixin._record_llm_response_to_history passes
        args_raw (a JSON-encoded string from the API's tool_calls), not a dict.
        Previously this crashed with "'str' object has no attribute 'get'".
        """
        from helen.interpreter.interpreter import Interpreter

        interp = Interpreter()

        # read_file with JSON string args
        interp._agent_context.update_from_tool_call(
            "read_file",
            '{"path": "/from/json.py"}',
            "file contents"
        )
        assert "/from/json.py" in interp._agent_context.working_memory.active_files

        # shell_exec with JSON string args — this was the specific crash site
        interp._agent_context.update_from_tool_call(
            "shell_exec",
            '{"command": "date"}',
            "2026-07-11"
        )
        # Should not crash; error tracking only fires on non-zero exit or
        # "error" in result, so no assertion needed beyond "didn't raise".

        # Malformed JSON falls back to empty dict — no crash
        interp._agent_context.update_from_tool_call(
            "write_file",
            'not-json',
            "ok"
        )

        # Non-string, non-dict args (int, list) also tolerated
        interp._agent_context.update_from_tool_call("read_file", 42, "ok")
        interp._agent_context.update_from_tool_call("read_file", [], "ok")
        interp._agent_context.update_from_tool_call("read_file", None, "ok")

    def test_prepare_context_with_working_memory(self):
        """Test prepare_context returns messages with working memory."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.history import Message

        interp = Interpreter()
        # Add some history
        interp._history.append(Message("user", "Hello"))
        interp._history.append(Message("assistant", "Hi there"))

        messages = interp._agent_context.prepare_context(
            system_prompt="You are a helpful assistant",
            history=interp._history,
            max_tokens=131072,
            current_prompt="Test"
        )

        # Should have system message + history
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"


class TestContextConfigDefaults:
    """Test ContextConfigNode default values."""

    def test_default_values(self):
        """Test ContextConfigNode has correct defaults."""
        config = ContextConfigNode()
        assert config.compression == "graduated"
        assert config.cache_aware is True
        assert config.working_memory is True
        assert config.working_memory_tokens == 5000

    def test_custom_values(self):
        """Test ContextConfigNode with custom values."""
        config = ContextConfigNode(
            compression="none",
            cache_aware=False,
            working_memory=False,
            working_memory_tokens=10000
        )
        assert config.compression == "none"
        assert config.cache_aware is False
        assert config.working_memory is False
        assert config.working_memory_tokens == 10000


class TestASTPrinterContextConfig:
    """Test ASTPrinter can print ContextConfigNode."""

    def test_print_context_config(self):
        """Test ASTPrinter prints context config correctly."""
        from helen.core.ast import ASTPrinter

        config = ContextConfigNode(
            compression="graduated",
            cache_aware=True,
            working_memory=True,
            working_memory_tokens=5000
        )
        printer = ASTPrinter()
        result = config.accept(printer)
        assert "context-config" in result
        assert "compression=graduated" in result
        assert "cache_aware=True" in result
        assert "working_memory=True" in result
        assert "tokens=5000" in result


class TestUnifiedCompressionArchitecture:
    """Tests for unified compression architecture (traditional + cache-aware composition)."""

    def test_compression_strategy_default(self):
        """Default strategy is 'graduated'."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager()
        assert mgr.compression_strategy == "graduated"
        assert mgr.compression_enabled is True

    def test_compression_strategy_traditional(self):
        """Strategy 'traditional' is accepted and tracked."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager(compression_strategy="traditional")
        assert mgr.compression_strategy == "traditional"
        assert mgr.compression_enabled is True

    def test_compression_strategy_none(self):
        """Strategy 'none' disables compression."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager(compression_strategy="none")
        assert mgr.compression_strategy == "none"
        assert mgr.compression_enabled is False

    def test_backward_compat_compression_enabled_true(self):
        """Old-style compression_enabled=True still works (maps to 'graduated')."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager(compression_enabled=True)
        assert mgr.compression_strategy == "graduated"
        assert mgr.compression_enabled is True

    def test_backward_compat_compression_enabled_false(self):
        """Old-style compression_enabled=False still works (maps to 'none')."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager(compression_enabled=False)
        assert mgr.compression_strategy == "none"
        assert mgr.compression_enabled is False

    def test_backward_compat_property_setter(self):
        """compression_enabled setter still works."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager()
        mgr.compression_enabled = False
        assert mgr.compression_strategy == "none"
        mgr.compression_enabled = True
        assert mgr.compression_strategy == "graduated"

    def test_unknown_strategy_falls_back_to_graduated(self):
        """Unknown strategy strings fall back to 'graduated'."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager(compression_strategy="unknown")
        assert mgr.compression_strategy == "graduated"

    def test_strategy_setter(self):
        """compression_strategy setter works for valid and invalid values."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager()
        mgr.compression_strategy = "traditional"
        assert mgr.compression_strategy == "traditional"
        mgr.compression_strategy = "invalid"
        assert mgr.compression_strategy == "graduated"  # fallback

    def test_get_stats_includes_strategy(self):
        """get_stats() reports compression_strategy."""
        from helen.interpreter.agent_context import AgentContextManager

        mgr = AgentContextManager(compression_strategy="traditional")
        stats = mgr.get_stats()
        assert stats["compression_strategy"] == "traditional"
        assert stats["compression_enabled"] is True

    def test_no_compression_returns_original_history(self):
        """strategy='none' returns history unchanged."""
        from helen.interpreter.agent_context import AgentContextManager
        from helen.runtime.history import Message

        mgr = AgentContextManager(
            compression_strategy="none",
            working_memory_enabled=False,
        )
        history = [Message("user", f"msg {i}") for i in range(20)]
        result = mgr._compress_history(history, max_tokens=131072)
        assert result is history  # same object, no compression

    def test_traditional_strategy_calls_history_manager(self):
        """strategy='traditional' produces compressed output for large history."""
        from helen.interpreter.agent_context import AgentContextManager
        from helen.runtime.history import Message

        mgr = AgentContextManager(
            compression_strategy="traditional",
            cache_aware_enabled=False,
            working_memory_enabled=False,
        )
        # Create history that exceeds a tiny max_tokens to trigger compression
        history = [
            Message("user", "x" * 500, _token_count=100)
            for _ in range(20)
        ]
        # max_tokens small enough to trigger compression
        result = mgr._compress_history(history, max_tokens=500)
        # Should produce some result (possibly compressed)
        assert isinstance(result, list)

    def test_graduated_strategy_runs(self):
        """strategy='graduated' runs graduated_compress."""
        from helen.interpreter.agent_context import AgentContextManager
        from helen.runtime.history import Message

        mgr = AgentContextManager(
            compression_strategy="graduated",
            cache_aware_enabled=False,
            working_memory_enabled=False,
        )
        history = [
            Message("user", "x" * 500, _token_count=100)
            for _ in range(20)
        ]
        result = mgr._compress_history(history, max_tokens=500)
        assert isinstance(result, list)

    def test_cache_aware_wraps_graduated(self):
        """cache_aware + graduated: cache zone preserved, suffix compressed."""
        from helen.interpreter.agent_context import AgentContextManager
        from helen.runtime.history import Message

        mgr = AgentContextManager(
            compression_strategy="graduated",
            cache_aware_enabled=True,
            working_memory_enabled=False,
        )
        # Create history with distinct first N messages (cache zone)
        history = [
            Message("user", f"cache-msg-{i}", _token_count=10)
            for i in range(5)
        ] + [
            Message("user", f"suffix-{i}" + "x" * 500, _token_count=100)
            for i in range(20)
        ]
        original_first_5 = [m.content for m in history[:5]]

        # Use tiny max_tokens to force compression
        result = mgr._compress_history(history, max_tokens=200)

        # Cache zone (first 5 messages) should be preserved verbatim
        result_first_5 = [m.content for m in result[:5]]
        assert result_first_5 == original_first_5

        # Cache stats should reflect cache-aware wrapping
        assert mgr._last_cache_stats is not None
        assert "cache_aware+graduated" in mgr._last_cache_stats.compression_strategy

    def test_cache_aware_wraps_traditional(self):
        """cache_aware + traditional: cache zone preserved, suffix compressed traditionally."""
        from helen.interpreter.agent_context import AgentContextManager
        from helen.runtime.history import Message

        mgr = AgentContextManager(
            compression_strategy="traditional",
            cache_aware_enabled=True,
            working_memory_enabled=False,
        )
        history = [
            Message("user", f"cache-{i}", _token_count=10)
            for i in range(5)
        ] + [
            Message("user", f"body-{i}" + "x" * 500, _token_count=100)
            for i in range(20)
        ]
        original_first_5 = [m.content for m in history[:5]]

        result = mgr._compress_history(history, max_tokens=200)

        # Cache zone preserved
        result_first_5 = [m.content for m in result[:5]]
        assert result_first_5 == original_first_5

        # Stats reflect traditional+cache-aware
        assert mgr._last_cache_stats is not None
        assert "cache_aware+traditional" in mgr._last_cache_stats.compression_strategy

    def test_short_history_skips_compression(self):
        """Small histories (below threshold) skip compression."""
        from helen.interpreter.agent_context import AgentContextManager
        from helen.runtime.history import Message

        for strategy in ["graduated", "traditional"]:
            mgr = AgentContextManager(compression_strategy=strategy)
            # 5 tiny messages with large max_tokens → well under any threshold
            history = [Message("user", f"msg {i}") for i in range(5)]
            result = mgr._compress_history(history, max_tokens=131072)
            assert result is history
