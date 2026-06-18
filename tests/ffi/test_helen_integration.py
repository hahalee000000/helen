"""Integration tests for Python FFI in Helen programs.

Tests that Helen code can import and use Python modules.
"""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.interpreter.interpreter import Interpreter
from helen.semantic.analyzer import SemanticAnalyzer


class TestHelenPythonFFI:
    """Test Python FFI integration with Helen interpreter."""
    
    def test_import_python_module(self):
        """Helen should be able to import Python modules."""
        source = '''
        import "math" as math
        
        main {
            let result = math.sqrt(16)
            print(result)
        }
        '''
        
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {[str(e) for e in errors.errors]}"
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        assert not errors.has_errors, f"Semantic errors: {[str(e) for e in errors.errors]}"
        
        interp = Interpreter(errors=errors)
        result = interp.interpret(program)
        
        assert not errors.has_errors, f"Runtime errors: {[str(e) for e in errors.errors]}"
    
    def test_import_and_call_function(self):
        """Helen should be able to call Python functions."""
        source = '''
        import "math" as math
        
        main {
            let x = math.sqrt(25)
            let y = math.pow(2, 10)
            print(x)
            print(y)
        }
        '''
        
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interp = Interpreter(errors=errors)
        interp.interpret(program)
        
        assert not errors.has_errors
    
    def test_import_json_module(self):
        """Helen should be able to use json module."""
        source = '''
        import "json" as json
        
        main {
            let data = {"name": "Alice", "age": 30}
            let json_str = json.dumps(data)
            print(json_str)
        }
        '''
        
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interp = Interpreter(errors=errors)
        interp.interpret(program)
        
        assert not errors.has_errors
    
    def test_access_module_constant(self):
        """Helen should be able to access module constants."""
        source = '''
        import "math" as math
        
        main {
            let pi = math.pi
            print(pi)
        }
        '''
        
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interp = Interpreter(errors=errors)
        interp.interpret(program)
        
        assert not errors.has_errors
    
    def test_nested_module_import(self):
        """Helen should be able to import nested modules."""
        source = '''
        import "os.path" as path
        
        main {
            let joined = path.join("a", "b", "c")
            print(joined)
        }
        '''
        
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        
        interp = Interpreter(errors=errors)
        interp.interpret(program)
        
        assert not errors.has_errors
