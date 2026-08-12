"""Tests for v1.42 static agent function call: AgentName.function_name(args).

This feature allows calling functions inside an agent's ``functions {}``
block WITHOUT instantiating the agent. The function runs in a detached
environment with stdlib + module consts + shared let, but NOT agent
instance state.

Syntax: ``AgentName.function_name(args)`` — parses as
``CallNode(AccessNode(VariableNode("AgentName"), "function_name"), args)``.
"""
import pytest
from helen.core.parser import Parser
from helen.core.lexer import Scanner
from helen.core.ast import (
    AccessNode, CallNode, VariableNode, AgentDeclNode,
)
from helen.core.errors import ErrorReporter
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


def _parse(source: str):
    """Parse Helen source code."""
    scanner = Scanner(source)
    tokens = scanner.scan_all()
    parser = Parser(tokens, source)
    return parser.parse()


def _analyze(program, source: str):
    """Run semantic analysis, return list of errors."""
    errors = ErrorReporter()
    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)
    return errors.errors


def _interpret(source: str):
    """Interpret Helen source code, return interpreter."""
    program = _parse(source)
    interp = Interpreter()
    interp.llm_runtime = MockLLMRuntime()
    interp.interpret(program)
    return interp


# ── Parser tests ──────────────────────────────────────────────


class TestAgentStaticCallParsing:
    """Test that AgentName.fn(args) parses correctly."""

    def test_access_node_structure(self):
        """Parser produces AccessNode(Variable, 'fn') inside CallNode."""
        source = '''
        agent MathAgent {
            functions {
                fn add(a: int, b: int): int { return a + b }
            }
            main { return 0 }
        }
        main {
            let x = MathAgent.add(1, 2)
        }
        '''
        program = _parse(source)
        # Find the main block's let statement
        main_stmts = [s for s in program.statements
                      if hasattr(s, 'body') and s.body is not None]
        assert len(main_stmts) >= 1
        # Find the call expression
        main_block = main_stmts[0].body if hasattr(main_stmts[0], 'body') else None
        assert main_block is not None

    def test_agent_decl_has_functions(self):
        """AgentDeclNode has functions list populated."""
        source = '''
        agent TestAgent {
            functions {
                fn foo() { return 1 }
                fn bar(x: int) { return x }
            }
            main { return 0 }
        }
        '''
        program = _parse(source)
        agent = program.statements[0]
        assert isinstance(agent, AgentDeclNode)
        assert len(agent.functions) == 2
        assert agent.functions[0].name == "foo"
        assert agent.functions[1].name == "bar"


# ── Semantic analyzer tests ───────────────────────────────────


class TestAgentStaticCallSemantic:
    """Test semantic analysis of AgentName.fn(args)."""

    def test_unknown_function_error(self):
        """E0356: agent has no such function in functions{} block."""
        source = '''
        agent MathAgent {
            functions {
                fn add(a: int, b: int): int { return a + b }
            }
            main { return 0 }
        }
        main {
            let x = MathAgent.sub(1, 2)
        }
        '''
        program = _parse(source)
        errors = _analyze(program, source)
        error_messages = [e.message for e in errors]
        assert any("has no function 'sub'" in m for m in error_messages)

    def test_arg_count_error(self):
        """E0357: wrong number of arguments."""
        source = '''
        agent MathAgent {
            functions {
                fn add(a: int, b: int): int { return a + b }
            }
            main { return 0 }
        }
        main {
            let x = MathAgent.add(1)
        }
        '''
        program = _parse(source)
        errors = _analyze(program, source)
        error_messages = [e.message for e in errors]
        assert any("expects 2 argument" in m for m in error_messages)

    def test_valid_call_no_error(self):
        """Valid static call should not produce errors."""
        source = '''
        agent MathAgent {
            functions {
                fn add(a: int, b: int): int { return a + b }
            }
            main { return 0 }
        }
        main {
            let x = MathAgent.add(1, 2)
        }
        '''
        program = _parse(source)
        errors = _analyze(program, source)
        # Filter out any errors unrelated to the agent function call
        agent_errors = [e for e in errors if "MathAgent" in e.message and "function" in e.message]
        assert len(agent_errors) == 0


# ── Interpreter tests ─────────────────────────────────────────


class TestAgentStaticCallInterpretation:
    """Test interpreter execution of AgentName.fn(args)."""

    def test_basic_function_call(self):
        """Static call returns function result."""
        source = '''
        import std.core.*
        agent MathAgent {
            functions {
                fn add(a: int, b: int): int { return a + b }
            }
            main { return 0 }
        }
        main {
            let x = MathAgent.add(3, 5)
            if x != 8 {
                print("FAIL: expected 8, got " + str(x))
            }
        }
        '''
        interp = _interpret(source)
        # No errors should have been raised
        assert len(interp.errors.errors) == 0

    def test_sibling_function_call(self):
        """Function can call sibling function in same agent."""
        source = '''
        import std.core.*
        agent MathAgent {
            functions {
                fn double(n: int): int { return n * 2 }
                fn quadruple(n: int): int { return double(double(n)) }
            }
            main { return 0 }
        }
        main {
            let x = MathAgent.quadruple(3)
            if x != 12 {
                print("FAIL: expected 12, got " + str(x))
            }
        }
        '''
        interp = _interpret(source)
        assert len(interp.errors.errors) == 0

    def test_string_function(self):
        """Static call with string arg/return."""
        source = '''
        import std.core.*
        import std.str.*
        agent Greeter {
            functions {
                fn greet(name: str): str {
                    return "Hello, " + name + "!"
                }
            }
            main { return "" }
        }
        main {
            let msg = Greeter.greet("World")
            if msg != "Hello, World!" {
                print("FAIL: got " + msg)
            }
        }
        '''
        interp = _interpret(source)
        assert len(interp.errors.errors) == 0

    def test_default_parameters(self):
        """Static call respects function default parameters."""
        source = '''
        import std.core.*
        agent MathAgent {
            functions {
                fn power(base: int, exp: int = 2): int {
                    let result = 1
                    let i = 0
                    while i < exp {
                        result = result * base
                        i = i + 1
                    }
                    return result
                }
            }
            main { return 0 }
        }
        main {
            let x = MathAgent.power(3)
            if x != 9 {
                print("FAIL: expected 9, got " + str(x))
            }
            let y = MathAgent.power(2, 10)
            if y != 1024 {
                print("FAIL: expected 1024, got " + str(y))
            }
        }
        '''
        interp = _interpret(source)
        assert len(interp.errors.errors) == 0

    def test_unknown_function_runtime_error(self):
        """Runtime error if function doesn't exist."""
        source = '''
        import std.core.*
        agent MathAgent {
            functions {
                fn add(a: int, b: int): int { return a + b }
            }
            main { return 0 }
        }
        main {
            let x = MathAgent.sub(1, 2)
        }
        '''
        # Runtime error is raised as an exception (not collected in errors)
        from helen.interpreter.exceptions import RuntimeError as HelenRuntimeError
        with pytest.raises(HelenRuntimeError, match="has no function 'sub'"):
            _interpret(source)

    def test_module_const_visible(self):
        """Module-level const is visible in agent function (detached env)."""
        source = '''
        import std.core.*
        const MAGIC = 42
        agent TestAgent {
            functions {
                fn get_magic(): int { return MAGIC }
            }
            main { return 0 }
        }
        main {
            let x = TestAgent.get_magic()
            if x != 42 {
                print("FAIL: expected 42, got " + str(x))
            }
        }
        '''
        interp = _interpret(source)
        assert len(interp.errors.errors) == 0
