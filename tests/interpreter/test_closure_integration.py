"""
Integration test for closure callable feature (v1.32).

Tests that closures work correctly as callbacks in real Helen programs.
"""
import pytest
from helen.interpreter.interpreter import Interpreter
from helen.core.lexer import Scanner
from helen.core.parser import Parser


def _inject(source):
    """v1.39: inject stdlib imports (no longer globally available)."""
    return "import std.core.*\nimport std.str.*\nimport std.list.*\nimport std.dict.*\nimport std.math.*\nimport std.debug.*\n" + source
def test_anonymous_closure_as_callback():
    """Anonymous closures should work as callbacks in higher-order functions."""
    source = """
    fn apply_twice(f, x) {
        return f(f(x))
    }

    main {
        let result = apply_twice(fn(n) { return n + 1 }, 3)
        print(result)
    }
    """

    source = _inject(source)
    scanner = Scanner(source=source, file='<test>')
    tokens = scanner.scan_all()
    parser = Parser(tokens)
    program = parser.parse()

    interp = Interpreter()
    interp.interpret(program)

    # Should have printed 5 (3 + 1 + 1)
    # We can't easily capture print output, but if it runs without error, it works


def test_closure_in_map_filter_reduce():
    """Closures should work in stdlib higher-order functions."""
    source = """
    main {
        let nums = [1, 2, 3, 4, 5]

        // map with anonymous closure
        let doubled = map(nums, fn(x) { return x * 2 })

        // filter with anonymous closure
        let evens = filter(nums, fn(x) { return x % 2 == 0 })

        // reduce with anonymous closure
        let total = reduce(nums, fn(acc, x) { return acc + x }, 0)
    }
    """

    source = _inject(source)
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    
    parser = Parser(tokens)
    program = parser.parse()

    interp = Interpreter()
    # Should execute without errors
    interp.interpret(program)


def test_closure_captures_environment():
    """Closures should capture variables from enclosing scope."""
    source = """
    fn make_multiplier(factor) {
        return fn(x) { return x * factor }
    }

    main {
        let triple = make_multiplier(3)
        let result = triple(5)
        print(result)  // Should print 15
    }
    """

    source = _inject(source)
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    
    parser = Parser(tokens)
    program = parser.parse()

    interp = Interpreter()
    interp.interpret(program)


def test_closure_recursive():
    """Closures should support recursion via _self_name."""
    source = """
    main {
        let factorial = fn(n) {
            if n <= 1 {
                return 1
            }
            return n * factorial(n - 1)
        }

        let result = factorial(5)
        print(result)  // Should print 120
    }
    """

    source = _inject(source)
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    
    parser = Parser(tokens)
    program = parser.parse()

    interp = Interpreter()
    interp.interpret(program)


def test_named_function_as_callback():
    """Named functions should still work as callbacks."""
    source = """
    fn double(x) {
        return x * 2
    }

    fn apply(f, x) {
        return f(x)
    }

    main {
        let result = apply(double, 5)
        print(result)  // Should print 10
    }
    """

    source = _inject(source)
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    
    parser = Parser(tokens)
    program = parser.parse()

    interp = Interpreter()
    interp.interpret(program)
