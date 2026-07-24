"""Test that SharedStore methods are preserved after spawn (issue #20).

This test verifies that when a SharedStore is deep-copied during spawn,
its methods are copied and rebound to the new store, not lost.
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
        return [], [str(e) for e in errors._errors]

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


class TestSharedStoreMethodsAfterSpawn:
    """Test that SharedStore methods work correctly after spawn."""

    def test_shared_store_methods_work_after_spawn(self):
        """Integration test: spawn agent can call SharedStore methods."""
        source = """
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
    fn get(): int { return count }
}

agent Worker(reply: Channel) {
    main {
        try {
            Counter.increment()
            Counter.increment()
            let count = Counter.get()
            reply.send({"status": "ok", "count": count})
        } catch RuntimeError err {
            reply.send({"status": "error", "msg": err.message})
        }
        reply.close()
    }
}

main {
    Counter.increment()
    let parent_count = Counter.get()

    let mb = spawn Worker()
    let r = mb.receive()

    print(parent_count)
    print(r["status"])
    print(r["count"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"

        # Parent should have count=1
        assert output[0] == "1", "Parent count should be 1"

        # Child should succeed and have count=3 (starts with 1, increments twice)
        assert output[1] == "ok", f"Child should succeed, got: {output[1]}"
        assert output[2] == "3", "Child's counter should be 3 (1 + 2 increments)"

    def test_shared_store_fields_are_independent_after_spawn(self):
        """Verify that deep-copied store has independent fields."""
        source = """
shared store State {
    let value: int = 10
    fn set_value(v: int) { value = v }
    fn get_value(): int { return value }
}

agent Modifier(reply: Channel) {
    main {
        State.set_value(999)
        reply.send({"modified_value": State.get_value()})
        reply.close()
    }
}

main {
    let original = State.get_value()

    let mb = spawn Modifier()
    let result = mb.receive()

    let after_spawn = State.get_value()

    print(original)
    print(result["modified_value"])
    print(after_spawn)
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"

        # Original value should be 10
        assert output[0] == "10"

        # Modified value (in child) should be 999
        assert output[1] == "999"

        # Parent's value should still be 10 (independent copies)
        assert output[2] == "10", "Parent and child should have independent field copies"

    def test_shared_store_reset_method_after_spawn(self):
        """Test that reset() method works after spawn (issue #20 mentions reset)."""
        source = """
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
    fn reset() { count = 0 }
    fn get(): int { return count }
}

agent Worker(reply: Channel) {
    main {
        Counter.increment()
        Counter.increment()
        Counter.reset()
        reply.send({"count": Counter.get()})
        reply.close()
    }
}

main {
    let mb = spawn Worker()
    let r = mb.receive()
    print(r["count"])
}
"""
        output, errors, result = run_helen(source)
        assert not errors, f"Errors: {errors}"
        assert output[0] == "0", "reset() should work and set count to 0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
