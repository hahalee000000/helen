"""Tests for stdlib module imports (v1.34)."""

import pytest


class TestStdlibModuleImport:
    """Test stdlib module import functionality."""

    def test_selective_import(self):
        """Test selective import: import std.str.{upper, lower}."""
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser

        source = """
import std.str.{upper, lower}

main {
    print(upper("hello"))
    print(lower("WORLD"))
}
"""
        lexer = Scanner(source)
        tokens = lexer.scan_all()
        parser = Parser(tokens)
        program = parser.parse()

        # Should parse without errors
        assert program is not None
        assert len(program.statements) >= 2  # import + main

    def test_wildcard_import(self):
        """Test wildcard import: import std.list.*."""
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser

        source = """
import std.list.*

main {
    print(sort([3, 1, 2]))
}
"""
        lexer = Scanner(source)
        tokens = lexer.scan_all()
        parser = Parser(tokens)
        program = parser.parse()

        assert program is not None

    def test_namespace_import(self):
        """Test namespace import: import std.dict as Dict."""
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser

        source = """
import std.dict as Dict

main {
    let data = {"a": 1}
    print(Dict.keys(data))
}
"""
        lexer = Scanner(source)
        tokens = lexer.scan_all()
        parser = Parser(tokens)
        program = parser.parse()

        assert program is not None

    def test_execution_selective(self):
        """Test execution of selective import."""
        from helen.interpreter.interpreter import Interpreter
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.core.errors import ErrorReporter

        source = """
import std.str.{upper}

main {
    let result = upper("test")
    return result
}
"""
        lexer = Scanner(source)
        tokens = lexer.scan_all()
        parser = Parser(tokens)
        program = parser.parse()

        # Semantic analysis
        errors = ErrorReporter()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        assert not errors.has_errors

        # Execute
        interpreter = Interpreter()
        result = interpreter.interpret(program)

        assert result == "TEST"

    def test_execution_wildcard(self):
        """Test execution of wildcard import."""
        from helen.interpreter.interpreter import Interpreter
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.core.errors import ErrorReporter

        source = """
import std.list.*

main {
    let sorted = sort([3, 1, 2])
    return sorted
}
"""
        lexer = Scanner(source)
        tokens = lexer.scan_all()
        parser = Parser(tokens)
        program = parser.parse()

        errors = ErrorReporter()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        assert not errors.has_errors

        interpreter = Interpreter()
        result = interpreter.interpret(program)

        assert result == [1, 2, 3]

    def test_execution_namespace(self):
        """Test execution of namespace import."""
        from helen.interpreter.interpreter import Interpreter
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.core.errors import ErrorReporter

        source = """
import std.dict as Dict

main {
    let data = {"name": "Alice"}
    let keys_result = Dict.keys(data)
    return keys_result
}
"""
        lexer = Scanner(source)
        tokens = lexer.scan_all()
        parser = Parser(tokens)
        program = parser.parse()

        errors = ErrorReporter()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        assert not errors.has_errors

        interpreter = Interpreter()
        result = interpreter.interpret(program)

        assert "name" in result

    def test_invalid_module(self):
        """Test error on invalid module name."""
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.core.errors import ErrorReporter

        source = """
import std.invalid.{func}

main {
    return 0
}
"""
        lexer = Scanner(source)
        tokens = lexer.scan_all()
        parser = Parser(tokens)
        program = parser.parse()

        errors = ErrorReporter()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)

        assert errors.has_errors
        assert "Unknown stdlib module" in str(errors.errors)

    def test_invalid_function(self):
        """Test error on invalid function name."""
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.core.errors import ErrorReporter

        source = """
import std.str.{invalid_func}

main {
    return 0
}
"""
        lexer = Scanner(source)
        tokens = lexer.scan_all()
        parser = Parser(tokens)
        program = parser.parse()

        errors = ErrorReporter()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)

        assert errors.has_errors
        assert "not found in module" in str(errors.errors)
