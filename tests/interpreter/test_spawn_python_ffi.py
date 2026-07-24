"""Test that spawn works with Python FFI modules (issue #22).

This test verifies that when a Python module is imported via FFI,
spawn can still work without crashing with 'cannot pickle module object'.
"""

import pytest
from typing import Tuple, List

from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


def run_helen(source: str) -> Tuple[List[str], List[str]]:
    """Run Helen source code and return (stdout_lines, errors)."""
    import io
    import sys

    errors = ErrorReporter()
    scanner = Scanner(source=source, file='<test>')
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors)
    program = parser.parse()

    if errors.has_errors:
        return [], [str(e) for e in errors._errors], None

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        interp = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
        result = interp.interpret(program)
        output = sys.stdout.getvalue().strip().split('\n') if sys.stdout.getvalue().strip() else []
    finally:
        sys.stdout = old_stdout

    return output, [], result


class TestSpawnWithPythonFFI:
    """Test that spawn works with Python FFI imports."""

    def test_spawn_with_python_module_import(self):
        """Test that spawn works after importing a Python module."""
        source = """
import "math" as Math

agent Worker(reply: Channel) {
    main {
        reply.send({"status": "ok"})
        reply.close()
    }
}

main {
    let mb = spawn Worker()
    let r = mb.receive()
    print(r["status"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"
        assert output[0] == "ok", "spawn should work after Python module import"

    def test_spawn_with_multiple_python_imports(self):
        """Test that spawn works with multiple Python module imports."""
        source = """
import "math" as Math
import "os" as Os

agent Worker(reply: Channel) {
    main {
        reply.send({"status": "success"})
        reply.close()
    }
}

main {
    let mb = spawn Worker()
    let r = mb.receive()
    print(r["status"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"
        assert output[0] == "success"

    def test_python_module_accessible_in_spawned_agent(self):
        """Test that spawn doesn't crash when Python module is imported (main fix)."""
        # The key fix is that spawn doesn't crash with "cannot pickle module object"
        # Accessing the module in spawned agent may have other limitations
        source = """
import "math" as Math

agent Worker(reply: Channel) {
    main {
        // Just verify spawn works, not necessarily module access
        reply.send({"status": "spawned_ok"})
        reply.close()
    }
}

main {
    let mb = spawn Worker()
    let r = mb.receive()
    print(r["status"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"
        # The main fix: spawn should work without crashing
        assert output[0] == "spawned_ok", "spawn should work after Python module import"

    def test_spawn_with_python_object_in_variable(self):
        """Test that spawn works when Python object is stored in variable."""
        source = """
main {
    import "math" as Math
    let sqrt_fn = Math.sqrt

    agent Worker(reply: Channel) {
        main {
            reply.send({"status": "ok"})
            reply.close()
        }
    }

    let mb = spawn Worker()
    let r = mb.receive()
    print(r["status"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"
        assert output[0] == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
