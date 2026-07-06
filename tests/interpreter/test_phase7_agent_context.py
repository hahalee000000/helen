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
                工作记忆令牌 5000
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
            {"file_path": "/test/file.py"},
            "file contents"
        )
        assert "/test/file.py" in interp._agent_context.working_memory.active_files

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
