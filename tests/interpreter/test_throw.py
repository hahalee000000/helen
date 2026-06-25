"""Tests for throw statement functionality."""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.interpreter.exceptions import (
    HelenRuntimeError,
    RuntimeError,
    LLMError,
    TimeoutError,
    ToolError,
)


def _run(code: str):
    """Helper to run Helen code and return (result, errors)."""
    scanner = Scanner(code)
    tokens = scanner.scan_all()
    
    reporter = ErrorReporter()
    parser = Parser(tokens, errors=reporter)
    program = parser.parse()
    
    if reporter.has_errors:
        return None, reporter.errors
    
    analyzer = SemanticAnalyzer(errors=reporter)
    analyzer.analyze(program)
    
    if reporter.has_errors:
        return None, reporter.errors
    
    interpreter = Interpreter()
    try:
        result = interpreter.interpret(program)
        return result, []
    except HelenRuntimeError as e:
        return None, [e]


class TestThrowBasic:
    """Test basic throw statement functionality."""
    
    def test_throw_runtime_error_with_message(self):
        """throw RuntimeError("message") should raise RuntimeError."""
        code = 'throw RuntimeError("something went wrong");'
        result, errors = _run(code)
        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)
        assert "something went wrong" in str(errors[0])
    
    def test_throw_runtime_error_without_message(self):
        """throw RuntimeError should raise RuntimeError with default message."""
        code = 'throw RuntimeError;'
        result, errors = _run(code)
        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)
    
    def test_throw_llm_error(self):
        """throw LLMError should raise LLMError."""
        code = 'throw LLMError("model failed");'
        result, errors = _run(code)
        assert len(errors) == 1
        assert isinstance(errors[0], LLMError)
    
    def test_throw_timeout_error(self):
        """throw TimeoutError should raise TimeoutError."""
        code = 'throw TimeoutError("request timed out");'
        result, errors = _run(code)
        assert len(errors) == 1
        assert isinstance(errors[0], TimeoutError)
    
    def test_throw_tool_error(self):
        """throw ToolError should raise ToolError."""
        code = 'throw ToolError("tool call failed");'
        result, errors = _run(code)
        assert len(errors) == 1
        assert isinstance(errors[0], ToolError)


class TestThrowWithTryCatch:
    """Test throw statements with try-catch blocks."""
    
    def test_throw_caught_by_typed_catch(self):
        """throw RuntimeError should be caught by catch RuntimeError."""
        code = '''
        try {
            throw RuntimeError("test error");
        } catch RuntimeError err {
            print("caught: " + err.message);
        }
        '''
        result, errors = _run(code)
        assert len(errors) == 0
    
    def test_throw_caught_by_parent_catch(self):
        """throw TimeoutError should be caught by catch LLMError (inheritance)."""
        code = '''
        try {
            throw TimeoutError("timeout");
        } catch LLMError err {
            print("caught LLM error");
        }
        '''
        result, errors = _run(code)
        assert len(errors) == 0
    
    def test_throw_caught_by_catch_all(self):
        """throw should be caught by catch-all."""
        code = '''
        try {
            throw RuntimeError("test");
        } catch {
            print("caught any error");
        }
        '''
        result, errors = _run(code)
        assert len(errors) == 0
    
    def test_throw_uncaught_propagates(self):
        """Uncaught throw should propagate up."""
        code = '''
        fn do_fail() {
            throw RuntimeError("fail");
        }
        
        try {
            do_fail();
        } catch RuntimeError err {
            print("caught in caller");
        }
        '''
        result, errors = _run(code)
        assert len(errors) == 0
    
    def test_throw_with_finally(self):
        """throw with finally should execute finally block."""
        code = '''
        let finalized = false
        try {
            throw RuntimeError("test");
        } catch RuntimeError err {
            print("caught");
        } finally {
            finalized = true;
        }
        print(finalized);
        '''
        result, errors = _run(code)
        assert len(errors) == 0


class TestThrowSemanticErrors:
    """Test semantic analysis for throw statements."""
    
    def test_invalid_exception_type(self):
        """throw with invalid exception type should report error."""
        code = 'throw InvalidError("test");'
        result, errors = _run(code)
        assert len(errors) > 0
        # Should be a semantic error about invalid exception type
    
    def test_throw_in_function(self):
        """throw inside function should work."""
        code = '''
        fn validate(x: int) {
            if (x < 0) {
                throw RuntimeError("negative not allowed");
            }
            return x * 2;
        }
        
        try {
            let result = validate(-5)
        } catch RuntimeError err {
            print("validation failed");
        }
        '''
        result, errors = _run(code)
        assert len(errors) == 0


class TestThrowParser:
    """Test parser handling of throw statements."""
    
    def test_parse_throw_with_message(self):
        """Parser should handle throw Type("message")."""
        code = 'throw RuntimeError("test");'
        scanner = Scanner(code)
        tokens = scanner.scan_all()
        reporter = ErrorReporter()
        parser = Parser(tokens, errors=reporter)
        program = parser.parse()
        
        assert not reporter.has_errors
        assert len(program.statements) == 1
    
    def test_parse_throw_without_message(self):
        """Parser should handle throw Type."""
        code = 'throw RuntimeError;'
        scanner = Scanner(code)
        tokens = scanner.scan_all()
        reporter = ErrorReporter()
        parser = Parser(tokens, errors=reporter)
        program = parser.parse()
        
        assert not reporter.has_errors
        assert len(program.statements) == 1
    
    def test_parse_throw_without_semicolon(self):
        """Parser should handle throw without semicolon (optional)."""
        code = 'throw RuntimeError'
        scanner = Scanner(code)
        tokens = scanner.scan_all()
        reporter = ErrorReporter()
        parser = Parser(tokens, errors=reporter)
        program = parser.parse()
        
        assert not reporter.has_errors
