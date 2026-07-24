"""Test that shared let variables are visible after spawn (issue #21).

This test verifies that shared let variables declared at module level
are accessible in spawned agents.
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


class TestSharedLetAfterSpawn:
    """Test that shared let variables are visible in spawned agents."""

    def test_shared_let_visible_in_spawned_agent(self):
        """Test that shared let is accessible after spawn."""
        source = """
shared let shared_value = "hello-from-parent"

agent Worker(reply: Channel) {
    main {
        reply.send({"value": shared_value})
        reply.close()
    }
}

main {
    let mb = spawn Worker()
    let r = mb.receive()
    print(r["value"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"
        assert output[0] == "hello-from-parent", "shared let should be visible in spawned agent"

    def test_shared_let_mutable_in_spawned_agent(self):
        """Test that shared let can be modified in spawned agent (independent copy)."""
        source = """
shared let counter = 10

agent Modifier(reply: Channel) {
    main {
        counter = 999
        reply.send({"modified": counter})
        reply.close()
    }
}

main {
    let original = counter

    let mb = spawn Modifier()
    let r = mb.receive()

    let after_spawn = counter

    print(original)
    print(r["modified"])
    print(after_spawn)
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"

        # Original value should be 10
        assert output[0] == "10"

        # Modified value (in child) should be 999
        assert output[1] == "999"

        # Parent's value should still be 10 (independent copies due to deep copy)
        assert output[2] == "10", "Parent and child should have independent copies"

    def test_multiple_shared_let_visible(self):
        """Test that multiple shared let variables are all visible."""
        source = """
shared let val1 = "first"
shared let val2 = 42
shared let val3 = true

agent Worker(reply: Channel) {
    main {
        reply.send({
            "v1": val1,
            "v2": val2,
            "v3": val3
        })
        reply.close()
    }
}

main {
    let mb = spawn Worker()
    let r = mb.receive()
    print(r["v1"])
    print(r["v2"])
    print(r["v3"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"
        assert output[0] == "first"
        assert output[1] == "42"
        assert output[2] == "true"

    def test_shared_let_with_nested_spawn(self):
        """Test that shared let works with nested spawn."""
        source = """
shared let depth = 0

agent Level2(reply: Channel) {
    main {
        reply.send({"depth": depth})
        reply.close()
    }
}

agent Level1(reply: Channel) {
    main {
        let mb2 = spawn Level2()
        let r2 = mb2.receive()
        reply.send(r2)
        reply.close()
    }
}

main {
    let mb1 = spawn Level1()
    let r1 = mb1.receive()
    print(r1["depth"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"
        assert output[0] == "0", "shared let should be visible through nested spawn"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
