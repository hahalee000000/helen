"""Tests for shared let write-back after agent calls (v1.11 fix).

Bug: Agent internal modifications to shared let variables were not visible
to the caller. The agent's isolated Environment received a *copy* of each
shared let value, and mutations were lost when the agent returned.

Fix: After agent execution (in the finally block), write back all shared
let values from the agent's Environment to the caller's scope chain.

Covers:
1. Basic write-back (agent modifies shared let, caller sees new value)
2. Accumulation across multiple agent calls
3. Nested agents modifying shared let
4. Shared let dict/list mutation
5. Write-back happens even when agent throws (exception path)
6. Multiple shared let variables
"""

import pytest

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


def _run(source: str) -> Interpreter:
    """Parse, analyze, and interpret a Helen program. Return the interpreter."""
    errors = ErrorReporter()
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    if errors.has_errors:
        raise RuntimeError(f"Parse errors: {[e.message for e in errors.errors]}")

    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)
    if errors.has_errors:
        raise RuntimeError(f"Semantic errors: {[e.message for e in errors.errors]}")

    interp = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
    interp.interpret(program)
    return interp


class TestSharedLetWriteBack:
    """Agent modifications to shared let must propagate to caller."""

    def test_basic_writeback(self):
        """Agent modifies shared let → caller sees the new value."""
        source = """
shared let counter = 0

agent ModifyShared() {
    main {
        counter = 999
        return "done"
    }
}

main {
    counter = 100
    let result = ModifyShared()
    // counter should now be 999
}
"""
        interp = _run(source)
        assert interp.environment.lookup("counter") == 999

    def test_accumulation_across_calls(self):
        """Multiple agent calls accumulate shared let modifications."""
        source = """
shared let counter = 0

agent Incr() {
    main {
        counter = counter + 1
        return counter
    }
}

main {
    Incr()
    Incr()
    Incr()
}
"""
        interp = _run(source)
        assert interp.environment.lookup("counter") == 3

    def test_nested_agents_writeback(self):
        """Nested agents both modify shared let; both write back."""
        source = """
shared let logs = []

agent Inner() {
    main {
        logs = logs + ["inner"]
        return "inner done"
    }
}

agent Outer() {
    main {
        logs = logs + ["outer-before"]
        Inner()
        logs = logs + ["outer-after"]
        return "outer done"
    }
}

main {
    Outer()
}
"""
        interp = _run(source)
        log = interp.environment.lookup("logs")
        assert log == ["outer-before", "inner", "outer-after"]

    def test_multiple_shared_vars(self):
        """Multiple shared let variables all write back correctly."""
        source = """
shared let a = 1
shared let b = 2

agent Swap() {
    main {
        let tmp = a
        a = b
        b = tmp
        return "swapped"
    }
}

main {
    Swap()
}
"""
        interp = _run(source)
        assert interp.environment.lookup("a") == 2
        assert interp.environment.lookup("b") == 1

    def test_dict_mutation_through_shared_let(self):
        """v1.12: Dict in shared let is now forbidden (must use shared store).

        This test verifies that shared let with reference types (dict, list)
        is rejected at semantic analysis time. The correct way to share
        mutable reference types across agents is via shared store (future).
        """
        source = """
shared let state = {"count": 0}

agent UpdateState() {
    main {
        state["count"] = state["count"] + 1
        return "updated"
    }
}

main {
    UpdateState()
    UpdateState()
}
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        assert not errors.has_errors

        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)

        # v1.12: shared let with reference type should produce an error
        assert errors.has_errors
        assert any("value type" in e.message for e in errors.errors)

    def test_writeback_on_exception(self):
        """Shared let modifications are written back even when agent throws."""
        source = """
shared let counter = 0

agent FailAfterModify() {
    main {
        counter = 42
        let x = 1 / 0
        return "unreachable"
    }
}

main {
    try {
        FailAfterModify()
    } catch AnyError e {
        // expected
    }
}
"""
        interp = _run(source)
        # Write-back happens in the finally block, so even on exception
        # the modification should propagate.
        assert interp.environment.lookup("counter") == 42

    def test_read_from_main_after_agent(self):
        """End-to-end: main reads shared let after agent call."""
        source = """
shared let message = "initial"

agent SetMessage(msg: str) {
    main {
        message = msg
        return "set"
    }
}

main {
    SetMessage(msg="hello from agent")
}
"""
        interp = _run(source)
        assert interp.environment.lookup("message") == "hello from agent"

    def test_agent_reads_caller_updates(self):
        """Each agent call sees the latest shared let value from previous calls."""
        source = """
shared let counter = 0

agent SetToFive() {
    main {
        counter = 5
        return "five"
    }
}

agent DoubleIt() {
    main {
        counter = counter * 2
        return "doubled"
    }
}

main {
    SetToFive()
    // counter is now 5
    DoubleIt()
    // counter is now 10
}
"""
        interp = _run(source)
        assert interp.environment.lookup("counter") == 10


class TestSharedLetWriteBackEdgeCases:
    """Edge cases for shared let write-back."""

    def test_agent_no_modify(self):
        """Agent that reads but doesn't modify shared let should be a no-op."""
        source = """
shared let counter = 100

agent JustRead() {
    main {
        let x = counter
        return x
    }
}

main {
    JustRead()
}
"""
        interp = _run(source)
        assert interp.environment.lookup("counter") == 100

    def test_writeback_preserves_isolation_for_non_shared(self):
        """Non-shared variables defined in agent must NOT leak to caller."""
        source = """
shared let counter = 0

agent CreateLocal() {
    main {
        counter = 42
        let local_var = "should not leak"
        return "done"
    }
}

main {
    CreateLocal()
}
"""
        interp = _run(source)
        assert interp.environment.lookup("counter") == 42
        # local_var should NOT be visible in the caller
        with pytest.raises(NameError):
            interp.environment.lookup("local_var")

    def test_shared_let_initial_value_from_module(self):
        """Shared let with no agent modification keeps module-level value."""
        source = """
shared let value = "module-level"

agent NoTouch() {
    main {
        return "noop"
    }
}

main {
    NoTouch()
}
"""
        interp = _run(source)
        assert interp.environment.lookup("value") == "module-level"
