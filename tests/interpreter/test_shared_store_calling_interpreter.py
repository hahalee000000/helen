"""Regression test: shared store methods use the CALLING interpreter's env.

Bug (v1.39.2): SharedStoreMethod captured the creating interpreter at
construction time. When the store was deep-copied during spawn, the copied
methods still referenced the parent interpreter. When the spawned
interpreter called the method, it ran in the parent's env chain, causing
stdlib functions imported by the spawned code (but not by the parent) to
be unresolved.

Symptom: "'context_stats' is not callable" when /context was invoked in
a spawned ChatSessionActor, because ContextManager.get_stats() (a shared
store method) resolved context_stats in the parent interpreter's env
where it wasn't visible via the same path.

Fix (v1.39.3): visit_call now sets a thread-local current interpreter
reference before dispatching to SharedStoreMethod, so the method runs
against the CALLING interpreter's env chain.
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
    source = "import std.core.*\nimport std.str.*\nimport std.list.*\nimport std.dict.*\nimport std.math.*\nimport std.debug.*\n" + source
    import io
    import sys

    errors = ErrorReporter()
    scanner = Scanner(source=source, file='<test>')
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors)
    program = parser.parse()

    if errors.has_errors:
        return [], [str(e) for e in errors._errors]

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        interp = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
        result = interp.interpret(program)
        output = sys.stdout.getvalue().strip().split('\n') if sys.stdout.getvalue().strip() else []
    finally:
        sys.stdout = old_stdout
    return output, []


class TestSharedStoreMethodUsesCallingInterpreter:
    """Shared store methods must resolve names in the calling interpreter's env."""

    def test_shared_store_method_sees_caller_stdlib(self):
        """A shared store method can call stdlib functions imported by the caller.

        Minimal reproduction of the v1.39.2 bug: a shared store method called
        from a function that imported std.context.* must find context_stats.
        """
        source = """
import std.context.*

shared store Stats {
    fn get_count(): int {
        let s = context_stats()
        return s["message_count"]
    }
}

fn get_count_via_store(): int {
    return Stats.get_count()
}

main {
    print(str(get_count_via_store()))
}
"""
        output, errs = run_helen(source)
        assert not errs, f"Errors: {errs}"
        assert output == ["0"]

    def test_spawned_agent_shared_store_method_resolves_names(self):
        """Spawned agent's shared store method resolves names in spawned env.

        Directly reproduces the v1.39.2 bug: after spawn, the shared store
        method (deep-copied) must still be able to call context_stats via
        the spawned interpreter's env chain.
        """
        source = """
import std.context.*

shared store StatsBox {
    fn describe(): str {
        try {
            let s = context_stats()
            return "count=" + str(s["message_count"])
        } catch RuntimeError err {
            return "ERROR:" + err.message
        } catch {
            return "ERROR:unknown"
        }
    }
}

fn read_stats(): str {
    return StatsBox.describe()
}

agent Worker(reply: Channel) {
    description "Spawned worker"
    functions {
        fn do_work(): str {
            return read_stats()
        }
    }
    main {
        reply.send(do_work())
    }
}

main {
    let mb = spawn Worker()
    let result = mb.receive()
    print(result)
}
"""
        output, errs = run_helen(source)
        assert not errs, f"Errors: {errs}"
        assert len(output) == 1, f"Expected one line, got: {output}"
        # Should NOT say "ERROR:'context_stats' is not callable"
        assert output[0].startswith("count="), f"Expected count=N, got: {output[0]}"
