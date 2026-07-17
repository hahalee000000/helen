"""Tests for builtin shadowing rejection (v1.23).

Helen v1.23 forbids user-defined symbols from shadowing stdlib builtins.
Since Helen is AI-native (LLM reads and writes the code), shadowing builtins
creates ambiguity: the LLM may misinterpret `log` as math.log vs user variable,
causing incorrect reasoning. Rejection at compile time keeps both LLM and
human readers in sync.

Covers:
1. Variable declarations (let, const, shared let)
2. Function declarations
3. Agent declarations
4. Function/lambda parameters
5. Loop iterator variables
6. Match pattern variable bindings
7. Catch clause error names
8. Import aliases
9. Alias statements
10. Shared store names and method parameters

Also verifies:
- Store method names themselves are NOT checked (they're in a namespace)
- Store field names themselves are NOT checked (namespace is Store.field)
- Non-builtin names still work fine
- Builtin shadowing errors carry ErrorCode.BUILTIN_SHADOWED
"""

from helen.core.errors import ErrorCode, ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer


def _analyze(source: str) -> list:
    """Run semantic analysis and return the list of errors."""
    errors = ErrorReporter()
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    if errors.has_errors:
        raise RuntimeError(f"Parse errors: {[e.message for e in errors.errors]}")
    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)
    return errors.errors


def _assert_shadow_error(errors: list, builtin_name: str):
    """Assert that errors contains exactly one BUILTIN_SHADOWED for builtin_name."""
    shadow_errors = [e for e in errors if e.code == ErrorCode.BUILTIN_SHADOWED]
    assert len(shadow_errors) >= 1, (
        f"expected BUILTIN_SHADOWED for '{builtin_name}', got {[str(e) for e in errors]}"
    )
    assert any(builtin_name in e.message for e in shadow_errors), (
        f"expected error message to mention '{builtin_name}', "
        f"got {[e.message for e in shadow_errors]}"
    )


class TestBuiltinShadowingVariables:
    """let / const / shared let cannot shadow builtins."""

    def test_let_shadows_builtin(self):
        """`let log = []` shadows math.log → rejected."""
        errors = _analyze("""
            main {
                let log = []
            }
        """)
        _assert_shadow_error(errors, "log")

    def test_const_shadows_builtin(self):
        """`const print = 1` shadows print() → rejected."""
        errors = _analyze("""
            const print = 1
            main {}
        """)
        _assert_shadow_error(errors, "print")

    def test_shared_let_shadows_builtin(self):
        """`shared let len = 0` shadows len() → rejected."""
        errors = _analyze("""
            shared let len = 0
            main {}
        """)
        _assert_shadow_error(errors, "len")

    def test_let_non_builtin_ok(self):
        """`let logger = []` — non-builtin name — accepted."""
        errors = _analyze("""
            main {
                let logger = []
            }
        """)
        shadow = [e for e in errors if e.code == ErrorCode.BUILTIN_SHADOWED]
        assert not shadow


class TestBuiltinShadowingFunctions:
    """fn / agent declarations cannot shadow builtins."""

    def test_function_shadows_builtin(self):
        errors = _analyze("""
            fn max(a, b) {
                return a
            }
            main {}
        """)
        _assert_shadow_error(errors, "max")

    def test_agent_shadows_builtin(self):
        errors = _analyze("""
            agent len() {
                main {}
            }
            main {}
        """)
        _assert_shadow_error(errors, "len")


class TestBuiltinShadowingParameters:
    """Function, lambda, and agent parameters cannot shadow builtins."""

    def test_function_param_shadows_builtin(self):
        errors = _analyze("""
            fn foo(log: int) {
                return log
            }
            main {}
        """)
        _assert_shadow_error(errors, "log")

    def test_lambda_param_shadows_builtin(self):
        errors = _analyze("""
            main {
                let f = fn(log) { return log }
            }
        """)
        _assert_shadow_error(errors, "log")

    def test_agent_param_shadows_builtin(self):
        errors = _analyze("""
            agent Worker(print: int) {
                main {}
            }
            main {}
        """)
        _assert_shadow_error(errors, "print")


class TestBuiltinShadowingControlFlow:
    """Loop iterators and match bindings cannot shadow builtins."""

    def test_for_iterator_shadows_builtin(self):
        errors = _analyze("""
            main {
                let items = [1, 2, 3]
                for log in items {
                }
            }
        """)
        _assert_shadow_error(errors, "log")

    def test_match_variable_binding_shadows_builtin(self):
        errors = _analyze("""
            main {
                let x = 5
                match x {
                    case log { return log }
                    default { return 0 }
                }
            }
        """)
        _assert_shadow_error(errors, "log")


class TestBuiltinShadowingExceptions:
    """Catch error names cannot shadow builtins."""

    def test_catch_name_shadows_builtin(self):
        errors = _analyze("""
            main {
                try {
                    let x = 1
                } catch AnyError log {
                }
            }
        """)
        _assert_shadow_error(errors, "log")


class TestBuiltinShadowingImports:
    """Import aliases cannot shadow builtins."""

    def test_python_module_alias_shadows_builtin(self):
        errors = _analyze("""
            import "math" as len
            main {}
        """)
        _assert_shadow_error(errors, "len")


class TestBuiltinShadowingAlias:
    """`alias X as Y` — Y cannot shadow a builtin."""

    def test_alias_shadows_builtin(self):
        errors = _analyze("""
            fn my_func() { return 1 }
            alias my_func as len
            main {}
        """)
        _assert_shadow_error(errors, "len")


class TestBuiltinShadowingStores:
    """Shared store / channel names cannot shadow builtins.
    Store method names themselves are OK (they live in a namespace)."""

    def test_store_name_shadows_builtin(self):
        errors = _analyze("""
            shared store len {
                let v = 0
                fn get(): int { return v }
            }
            main {}
        """)
        _assert_shadow_error(errors, "len")

    def test_store_method_name_ok(self):
        """Store method 'max' is in a namespace (Store.max), no shadowing."""
        errors = _analyze("""
            shared store Math {
                let v = 0
                fn max(a: int, b: int): int { return a }
            }
            main {}
        """)
        shadow = [e for e in errors if e.code == ErrorCode.BUILTIN_SHADOWED]
        assert not shadow

    def test_store_method_param_shadows_builtin(self):
        """Store method parameters ARE checked — they're in function scope."""
        errors = _analyze("""
            shared store Math {
                let v = 0
                fn add(log: int, y: int): int { return log + y }
            }
            main {}
        """)
        _assert_shadow_error(errors, "log")


class TestBuiltinShadowingErrorMessage:
    """Verify the error message includes a helpful hint."""

    def test_error_message_has_hint(self):
        errors = _analyze("""
            main {
                let log = 1
            }
        """)
        shadow = [e for e in errors if e.code == ErrorCode.BUILTIN_SHADOWED]
        assert len(shadow) >= 1
        msg = shadow[0].message
        # Message should suggest alternatives
        assert "log" in msg
        assert "builtin" in msg
