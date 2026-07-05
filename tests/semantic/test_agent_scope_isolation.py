"""Test compile-time detection of agent scope isolation violations.

Agent main {} runs in a completely isolated Environment at runtime
(per HLD 3.5.2).  Module-level let/const variables are NOT visible.
The semantic analyzer should catch these references at compile time
instead of letting them fail with cryptic runtime errors.
"""

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter, ErrorCode
from helen.semantic.analyzer import SemanticAnalyzer


def _analyze(source: str) -> ErrorReporter:
    """Parse and semantically analyze source, returning the error reporter."""
    errors = ErrorReporter()
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    if errors.has_errors:
        return errors  # parser errors, don't run semantic
    analyzer = SemanticAnalyzer(errors=errors)
    analyzer.analyze(program)
    return errors


class TestAgentScopeIsolation:
    """Verify compile-time detection of agent scope boundary violations."""

    def test_read_module_let_from_agent_main(self):
        """Reading module-level let from agent main should be a compile error."""
        source = """\
let _buf = ""
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = _buf  // ❌ module-level variable not visible in agent
    }
}
"""
        errors = _analyze(source)
        assert errors.has_errors
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) >= 1, \
            f"Expected SCOPE_VIOLATION, got: {[str(e) for e in errors.errors]}"
        assert "_buf" in str(scope_errors[0])

    def test_write_module_let_from_agent_main(self):
        """Writing to module-level let from agent main should be a compile error."""
        source = """\
let _buf = ""
agent TestAgent {
    description "test"
    prompt "test"
    main {
        _buf = "new"  // ❌ cannot assign to module-level variable
    }
}
"""
        errors = _analyze(source)
        assert errors.has_errors
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) >= 1, \
            f"Expected SCOPE_VIOLATION, got: {[str(e) for e in errors.errors]}"
        assert "_buf" in str(scope_errors[0])

    def test_read_module_const_from_agent_main(self):
        """Reading module-level const from agent main is now OK (v1.10)."""
        source = """\
const LIMIT = 100
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = LIMIT  // ✅ const is read-only shared across agents
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"const read should be OK in v1.10, got: {scope_errors}"

    def test_read_module_let_from_module_fn_is_ok(self):
        """Module-level fn CAN access module-level let — no error."""
        source = """\
let _buf = ""
fn _helper(): str {
    return _buf  // ✅ functions see module-level variables
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"Module fn should see module vars, got: {scope_errors}"

    def test_agent_calls_module_fn_is_ok(self):
        """Agent main calling a module-level fn is fine — no error."""
        source = """\
fn _helper(): str {
    return "ok"
}
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = _helper()  // ✅ calling functions is fine
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"Agent calling module fn should be ok, got: {scope_errors}"

    def test_agent_uses_stdlib_is_ok(self):
        """Agent main using stdlib functions is fine — no error."""
        source = """\
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = len("hello")  // ✅ stdlib is injected into agent env
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0

    def test_agent_local_variable_is_ok(self):
        """Agent main declaring and using its own variables is fine."""
        source = """\
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = 42  // ✅ local to agent main
        let y = x + 1
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0

    def test_getter_setter_pattern_is_ok(self):
        """The recommended getter/setter pattern should produce no errors."""
        source = """\
let _buf = ""
fn _buf_reset() { _buf = "" }
fn _buf_get(): str { return _buf }

agent TestAgent {
    description "test"
    prompt "test"
    main {
        _buf_reset()  // ✅ via function
        let x = _buf_get()  // ✅ via function
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"Getter/setter pattern should be ok, got: {scope_errors}"

    def test_error_message_is_helpful(self):
        """Error message should explain the issue clearly."""
        source = """\
let _router_buf = ""
agent QuestionRouter {
    description "test"
    prompt "test"
    main {
        _router_buf = ""  // ❌
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) >= 1
        msg = str(scope_errors[0])
        assert "agent scope isolation" in msg.lower()
        assert "_router_buf" in msg
        assert "shared let" in msg.lower() or "setter" in msg.lower() or "getter" in msg.lower() or "parameter" in msg.lower()

    def test_multiple_agents_each_isolated(self):
        """Each agent main is independently checked."""
        source = """\
let _a = ""
let _b = ""
agent AgentA {
    description "a"
    prompt "a"
    main {
        _a = "x"  // ❌ triggers both read + write scope errors
    }
}
agent AgentB {
    description "b"
    prompt "b"
    main {
        _b = "y"  // ❌ triggers both read + write scope errors
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        # Each assignment triggers 2 errors: read of _a/_b (left side)
        # and write to _a/_b (assignment).  2 agents × 2 = 4.
        assert len(scope_errors) == 4, \
            f"Expected 4 scope violations, got {len(scope_errors)}: {scope_errors}"

    # ── P1: const read-only sharing ────────────────────────────────────

    def test_const_read_from_agent_main_is_ok(self):
        """Reading module-level const from agent main should be OK (v1.10)."""
        source = """\
const LIMIT = 100
const NAME = "Helen"
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = LIMIT  // ✅ const is read-only shared
        let y = NAME   // ✅ const is read-only shared
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"const read should be OK, got: {scope_errors}"

    def test_const_write_from_agent_main_is_error(self):
        """Writing to const from agent main should still be an error."""
        source = """\
const LIMIT = 100
agent TestAgent {
    description "test"
    prompt "test"
    main {
        LIMIT = 200  // ❌ const is read-only
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) >= 1
        assert "const" in str(scope_errors[0]).lower()

    # ── P2: shared let ─────────────────────────────────────────────────

    def test_shared_let_read_from_agent_main_is_ok(self):
        """Reading shared let from agent main should be OK."""
        source = """\
shared let _buf = ""
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = _buf  // ✅ shared let is cross-agent visible
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"shared let read should be OK, got: {scope_errors}"

    def test_shared_let_write_from_agent_main_is_ok(self):
        """Writing to shared let from agent main should be OK."""
        source = """\
shared let _buf = ""
agent TestAgent {
    description "test"
    prompt "test"
    main {
        _buf = "new"  // ✅ shared let is writable across agents
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"shared let write should be OK, got: {scope_errors}"

    def test_shared_const_read_from_agent_main_is_ok(self):
        """Reading shared const from agent main should be OK."""
        source = """\
shared const LIMIT = 100
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = LIMIT  // ✅ shared const is read-only shared
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0

    def test_plain_let_still_blocked(self):
        """Plain let (not shared) should still be blocked from agent main."""
        source = """\
let _buf = ""
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let x = _buf  // ❌ plain let is not cross-agent
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) >= 1

    # ── P3: closure callbacks ──────────────────────────────────────────

    def test_closure_callback_in_agent_main(self):
        """Closure (lambda) capturing agent-local variable should be OK."""
        source = """\
agent TestAgent {
    description "test"
    prompt "test"
    main {
        let buf = ""
        let cb = fn(chunk) {
            buf = buf + chunk
        }
        llm act "hello" on_chunk cb
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"closure callback should be OK, got: {scope_errors}"

    # ------------------------------------------------------------------
    # Agent-local variables in nested control-flow blocks
    # ------------------------------------------------------------------

    def test_let_in_try_catch_inside_agent_main_is_local(self):
        """let variable used in try-catch inside agent main is agent-local."""
        source = """
agent Test() {
    main {
        let result = ""
        try {
            result = "success"
        } catch {
            result = "failed"
        }
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"let in try-catch should be local, got: {scope_errors}"

    def test_let_in_if_inside_agent_main_is_local(self):
        """let variable used in if block inside agent main is agent-local."""
        source = """
agent Test() {
    main {
        let x = 1
        if true {
            x = 2
        }
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"let in if should be local, got: {scope_errors}"

    def test_let_in_for_inside_agent_main_is_local(self):
        """let variable used in for block inside agent main is agent-local."""
        source = """
agent Test() {
    main {
        let total = 0
        for i in [1, 2, 3] {
            total = total + i
        }
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"let in for should be local, got: {scope_errors}"

    def test_let_in_while_inside_agent_main_is_local(self):
        """let variable used in while block inside agent main is agent-local."""
        source = """
agent Test() {
    main {
        let count = 0
        while count < 5 {
            count = count + 1
        }
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"let in while should be local, got: {scope_errors}"

    def test_let_in_match_inside_agent_main_is_local(self):
        """let variable used in match block inside agent main is agent-local."""
        source = """
agent Test() {
    main {
        let x = 1
        match x {
            case 1 { x = 2 }
            default { x = 3 }
        }
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        assert len(scope_errors) == 0, \
            f"let in match should be local, got: {scope_errors}"

    # ------------------------------------------------------------------
    # Agent parameters are visible inside main {}
    # ------------------------------------------------------------------

    def test_agent_params_visible_in_main(self):
        """Agent parameters should be recognized inside agent main."""
        source = """
agent Doubler(x: num) {
    main {
        return x * 2
    }
}
"""
        errors = _analyze(source)
        undeclared = [e for e in errors.errors
                      if e.code == ErrorCode.UNDECLARED_VARIABLE]
        assert len(undeclared) == 0, \
            f"agent params should be visible, got: {undeclared}"

    def test_agent_params_in_nested_blocks(self):
        """Agent parameters should be visible in nested blocks inside main."""
        source = """
agent Classifier(x: num) {
    main {
        if x > 0 {
            return "positive"
        }
    }
}
"""
        errors = _analyze(source)
        scope_errors = [e for e in errors.errors
                        if e.code == ErrorCode.SCOPE_VIOLATION]
        undeclared = [e for e in errors.errors
                      if e.code == ErrorCode.UNDECLARED_VARIABLE]
        assert len(scope_errors) == 0, \
            f"agent param in if should be OK, got: {scope_errors}"
        assert len(undeclared) == 0, \
            f"agent param should not be undeclared, got: {undeclared}"
