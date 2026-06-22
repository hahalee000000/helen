"""v1.8 edge case tests - boundary conditions and error handling.

Tests edge cases for:
- Pipe operator with complex expressions
- Pattern matching with nested structures
- Empty/malformed inputs
- Const protection edge cases
"""
import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.interpreter.interpreter import Interpreter
from helen.semantic.analyzer import SemanticAnalyzer


class TestPipeEdgeCases:
    """Edge cases for pipe operator |>."""

    def test_pipe_with_nested_calls(self):
        """Test pipe with nested function calls."""
        source = """
        fn double(x) { return x * 2 }
        fn add_one(x) { return x + 1 }
        let result = 5 |> double |> add_one
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        assert result == 11  # (5 * 2) + 1

    def test_pipe_with_lambda(self):
        """Test pipe with lambda expressions."""
        source = """
        let result = 10 |> fn(x) { return x * 3 }
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        assert result == 30

    def test_pipe_chain_three_functions(self):
        """Test chaining three functions with pipe."""
        source = """
        fn inc(x) { return x + 1 }
        fn dbl(x) { return x * 2 }
        fn sq(x) { return x * x }
        let result = 2 |> inc |> dbl |> sq
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        assert result == 36  # ((2+1)*2)^2


class TestPatternMatchingEdgeCases:
    """Edge cases for pattern matching."""

    def test_match_with_wildcard_only(self):
        """Test match with only wildcard pattern."""
        source = """
        let x = 42
        match x {
            case _ { return 99 }
        }
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        assert result == 99

    def test_match_variable_binding(self):
        """Test match with variable binding."""
        source = """
        let x = 10
        match x {
            case n { return n * 2 }
        }
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        assert result == 20

    def test_match_multiple_cases(self):
        """Test match with multiple cases."""
        source = """
        let x = 2
        match x {
            case 1 { return 10 }
            case 2 { return 20 }
            case 3 { return 30 }
            case _ { return 99 }
        }
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        assert result == 20


class TestConstEdgeCases:
    """Edge cases for const protection."""

    def test_const_reassignment_in_function(self):
        """Test that const cannot be reassigned inside function."""
        source = """
        const MAX = 100
        fn update() {
            MAX = 200
        }
        update()
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        # Should have CONST_ASSIGNMENT error
        assert any("const" in str(e).lower() for e in errors.errors)

    def test_let_can_be_reassigned(self):
        """Test that let variables can be reassigned."""
        source = """
        let x = 10
        x = 20
        return x
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        assert result == 20


class TestEmptyInputs:
    """Test empty and minimal inputs."""

    def test_empty_program(self):
        """Test parsing empty program."""
        source = ""
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        assert len(program.statements) == 0

    def test_whitespace_only(self):
        """Test parsing whitespace-only program."""
        source = "   \n\n   \t  "
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        assert len(program.statements) == 0

    def test_comment_only(self):
        """Test parsing comment-only program."""
        source = "// This is a comment\n/* Block comment */"
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        assert len(program.statements) == 0


class TestBreakContinueEdgeCases:
    """Edge cases for break/continue."""

    def test_break_in_nested_loop(self):
        """Test break in nested loop only breaks inner loop."""
        source = """
        let count = 0
        let i = 0
        while i < 3 {
            let j = 0
            while j < 5 {
                if j == 2 {
                    break
                }
                count = count + 1
                j = j + 1
            }
            i = i + 1
        }
        return count
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        # Inner loop runs 2 times (j=0,1) for each of 3 outer iterations
        assert result == 6

    def test_continue_skips_iteration(self):
        """Test continue skips rest of loop body."""
        source = """
        let sum = 0
        let i = 0
        while i < 5 {
            if i == 2 {
                i = i + 1
                continue
            }
            sum = sum + i
            i = i + 1
        }
        return sum
        """
        errors = ErrorReporter()
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interpreter = Interpreter(errors)
        result = interpreter.interpret(program)
        
        # 0 + 1 + 3 + 4 = 8 (skips 2)
        assert result == 8
