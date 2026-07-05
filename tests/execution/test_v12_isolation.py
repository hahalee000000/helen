"""Tests for v1.12 agent isolation improvements.

Covers:
1. ReadOnlyView — read ops, mutation blocking, iter wrapping, index access
2. SharedStore — field access, method calls, locking, internal protection
3. @open agent — module-level let visible
4. @strict agent — deep copy params and return values
5. @sandbox agent — tools forced to empty
6. Closure value capture — reference types deep copied
7. Closure scope check — no bypass for module-level let
"""

import copy
import pytest

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter, ReadOnlyView, SharedStore, SharedStoreMethod
from helen.interpreter.exceptions import ScopeViolationError, AgentError
from helen.runtime.llm_runtime import MockLLMRuntime


def _run(source: str) -> Interpreter:
    """Parse, analyze, and interpret a Helen program."""
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


def _analyze_only(source: str) -> ErrorReporter:
    """Parse and analyze only, return error reporter."""
    errors = ErrorReporter()
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    if errors.has_errors:
        return errors

    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)
    return errors


# ============================================================
# 1. ReadOnlyView
# ============================================================

class TestReadOnlyView:
    """ReadOnlyView tests for read-only parameter wrapping."""

    def test_read_by_index(self):
        """ReadOnlyView supports reading by index."""
        view = ReadOnlyView([10, 20, 30])
        assert view[0] == 10
        assert view[1] == 20
        assert view[2] == 30

    def test_read_dict_by_key(self):
        """ReadOnlyView supports reading dict by key."""
        view = ReadOnlyView({"a": 1, "b": 2})
        assert view["a"] == 1
        assert view["b"] == 2

    def test_len(self):
        """ReadOnlyView supports len()."""
        assert len(ReadOnlyView([1, 2, 3])) == 3
        assert len(ReadOnlyView({"a": 1})) == 1
        assert len(ReadOnlyView([])) == 0

    def test_iter_wraps_nested_mutables(self):
        """Iteration wraps nested list/dict in ReadOnlyView."""
        data = [[1, 2], [3, 4]]
        view = ReadOnlyView(data)
        for item in view:
            assert isinstance(item, ReadOnlyView), f"Expected ReadOnlyView, got {type(item)}"

        # Nested dicts
        data2 = [{"x": 1}, {"y": 2}]
        view2 = ReadOnlyView(data2)
        for item in view2:
            assert isinstance(item, ReadOnlyView)

    def test_iter_flat_values_not_wrapped(self):
        """Flat values (int, str) are NOT wrapped in ReadOnlyView."""
        view = ReadOnlyView([1, "hello", True])
        items = list(view)
        assert items == [1, "hello", True]
        assert not isinstance(items[0], ReadOnlyView)

    def test_mutation_blocked(self):
        """Mutation methods raise ScopeViolationError."""
        view = ReadOnlyView([1, 2, 3])
        with pytest.raises(ScopeViolationError):
            view.append(4)
        with pytest.raises(ScopeViolationError):
            view[0] = 99
        with pytest.raises(ScopeViolationError):
            view.pop()
        with pytest.raises(ScopeViolationError):
            view.clear()

    def test_dict_mutation_blocked(self):
        """Dict mutation methods raise ScopeViolationError."""
        view = ReadOnlyView({"a": 1})
        with pytest.raises(ScopeViolationError):
            view["b"] = 2
        with pytest.raises(ScopeViolationError):
            view.update({"c": 3})
        with pytest.raises(ScopeViolationError):
            view.popitem()

    def test_nested_read(self):
        """Nested list/dict access returns ReadOnlyView."""
        view = ReadOnlyView([[1, 2], [3, 4]])
        inner = view[0]
        assert isinstance(inner, ReadOnlyView)
        assert inner[0] == 1
        assert inner[1] == 2

    def test_nested_mutation_blocked(self):
        """Nested mutation through ReadOnlyView is blocked."""
        data = [[1, 2], [3, 4]]
        view = ReadOnlyView(data)
        inner = view[0]
        with pytest.raises(ScopeViolationError):
            inner.append(99)

    def test_bool(self):
        """ReadOnlyView bool reflects underlying data."""
        assert bool(ReadOnlyView([1])) is True
        assert bool(ReadOnlyView([])) is False
        assert bool(ReadOnlyView({"a": 1})) is True
        assert bool(ReadOnlyView({})) is False

    def test_str(self):
        """ReadOnlyView str shows underlying data."""
        view = ReadOnlyView([1, 2, 3])
        assert str(view) == "[1, 2, 3]"

    def test_contains(self):
        """ReadOnlyView supports `in` operator."""
        view = ReadOnlyView([1, 2, 3])
        assert 2 in view
        assert 99 not in view

    def test_eq(self):
        """ReadOnlyView equality."""
        v1 = ReadOnlyView([1, 2])
        v2 = ReadOnlyView([1, 2])
        assert v1 == v2
        assert v1 == [1, 2]  # compare with raw list

    def test_keys_values_items(self):
        """Dict-like methods work on dict-backed ReadOnlyView."""
        view = ReadOnlyView({"a": 1, "b": 2})
        assert set(view.keys()) == {"a", "b"}
        assert sorted(view.values()) == [1, 2]
        items = view.items()
        assert len(items) == 2

    def test_get_method(self):
        """Dict-like get() method."""
        view = ReadOnlyView({"a": 1})
        assert view.get("a") == 1
        assert view.get("b", 99) == 99
        # Nested mutable wrapped
        view2 = ReadOnlyView({"nested": [1, 2]})
        result = view2.get("nested")
        assert isinstance(result, ReadOnlyView)

    def test_no_unwrap_method(self):
        """unwrap() is not accessible from outside (renamed to _unwrap)."""
        view = ReadOnlyView([1, 2, 3])
        assert not hasattr(view, 'unwrap')


# ============================================================
# 2. ReadOnlyView in agent context (integration tests)
# ============================================================

class TestReadOnlyViewAgentIntegration:
    """Test ReadOnlyView behavior when passed as agent parameter."""

    def test_agent_can_read_param_by_index(self):
        """Agent can read parameter list by index."""
        source = """
agent Reader(items: list) {
    main {
        return items[0]
    }
}

let result = Reader(items = [10, 20, 30])
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 10

    def test_agent_can_iterate_param(self):
        """Agent can iterate over parameter list."""
        source = """
agent Summer(items: list) {
    main {
        let total = 0
        for item in items {
            total = total + item
        }
        return total
    }
}

let result = Summer(items = [1, 2, 3, 4])
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 10

    def test_agent_cannot_modify_param(self):
        """Agent cannot modify parameter list."""
        source = """
agent Mutator(items: list) {
    main {
        items[0] = 999
        return items[0]
    }
}

let result = Mutator(items = [1, 2, 3])
"""
        # The mutation is blocked at runtime by ReadOnlyView's __setitem__
        # (wrapped in AgentError since it occurs inside an agent call)
        with pytest.raises((ScopeViolationError, AgentError, RuntimeError)):
            _run(source)

    def test_agent_cannot_append_to_param(self):
        """Agent cannot append to parameter list."""
        source = """
agent Mutator(items: list) {
    main {
        items.append(999)
        return "done"
    }
}

let result = Mutator(items = [1, 2, 3])
"""
        with pytest.raises((ScopeViolationError, AgentError, RuntimeError)):
            _run(source)

    def test_agent_can_read_nested_param(self):
        """Agent can read nested list in parameter."""
        source = """
agent Reader(matrix: list) {
    main {
        return matrix[0][1]
    }
}

let result = Reader(matrix = [[1, 2], [3, 4]])
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 2

    def test_param_mutation_doesnt_affect_caller(self):
        """Caller's data is protected even if agent tries to mutate through iteration."""
        source = """
agent AttemptMutate(items: list) {
    main {
        // This should fail — items is read-only
        for item in items {
            // Can't modify item since it's a nested ReadOnlyView
        }
        return len(items)
    }
}

let data = [1, 2, 3]
let result = AttemptMutate(items = data)
"""
        interp = _run(source)
        # Original data is unchanged
        assert interp.environment.lookup("data") == [1, 2, 3]
        assert interp.environment.lookup("result") == 3

    def test_agent_can_iterate_dict_param(self):
        """Agent can read dict parameter values."""
        source = """
agent Reader(config: dict) {
    main {
        return config.get("name")
    }
}

let result = Reader(config = {"name": "Alice"})
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == "Alice"


# ============================================================
# 3. Closure value capture
# ============================================================

class TestClosureValueCapture:
    """Test that closures deep-copy reference types."""

    def test_closure_captures_list_snapshot(self):
        """Closure captures a snapshot of list, not a reference."""
        source = """
let arr = [1, 2, 3]
let f = fn() { return arr }
arr.append(4)
let result = f()
"""
        interp = _run(source)
        # f() should return [1, 2, 3] (snapshot), not [1, 2, 3, 4]
        assert interp.environment.lookup("result") == [1, 2, 3]

    def test_closure_captures_dict_snapshot(self):
        """Closure captures a snapshot of dict, not a reference."""
        source = """
let d = {"a": 1}
let f = fn() { return d }
d["b"] = 2
let result = f()
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == {"a": 1}

    def test_closure_mutation_doesnt_affect_original(self):
        """Mutation inside closure doesn't affect the captured variable."""
        source = """
let arr = [1, 2, 3]
let f = fn() {
    let inner = arr
    return len(inner)
}
let result = f()
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 3
        assert interp.environment.lookup("arr") == [1, 2, 3]

    def test_closure_captures_value_types(self):
        """Value types are captured normally (no deep copy needed)."""
        source = """
let x = 42
let f = fn() { return x }
let result = f()
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 42


# ============================================================
# 4. Closure scope check (no bypass)
# ============================================================

class TestClosureScopeCheck:
    """Test that closures in agent main cannot bypass scope checks."""

    def test_closure_cannot_access_module_let(self):
        """Closure inside agent main cannot access module-level let."""
        source = """
let secret = "hidden"

agent Worker() {
    main {
        let f = fn() { return secret }
        return f()
    }
}
"""
        errors = _analyze_only(source)
        assert errors.has_errors
        error_messages = [e.message for e in errors.errors]
        assert any("scope isolation" in m for m in error_messages)

    def test_closure_can_access_agent_local(self):
        """Closure inside agent main CAN access agent-local variables."""
        source = """
agent Worker() {
    main {
        let local_var = 42
        let f = fn() { return local_var }
        return f()
    }
}
"""
        errors = _analyze_only(source)
        assert not errors.has_errors

    def test_closure_can_access_const(self):
        """Closure inside agent main CAN access module-level const."""
        source = """
const MAX = 100

agent Worker() {
    main {
        let f = fn() { return MAX }
        return f()
    }
}
"""
        errors = _analyze_only(source)
        assert not errors.has_errors

    def test_closure_cannot_assign_to_module_let(self):
        """Closure inside agent main cannot assign to module-level let."""
        source = """
let counter = 0

agent Worker() {
    main {
        let f = fn() { counter = 1 }
        f()
        return "done"
    }
}
"""
        errors = _analyze_only(source)
        assert errors.has_errors
        error_messages = [e.message for e in errors.errors]
        assert any("scope isolation" in m for m in error_messages)


# ============================================================
# 5. @open agent
# ============================================================

class TestOpenAgent:
    """Test @open (L0) agent isolation level."""

    def test_open_agent_can_access_module_let(self):
        """@open agent can access module-level let."""
        source = """
let debug_info = "test data"

@open agent Debug() {
    main {
        return debug_info
    }
}

let result = Debug()
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == "test data"

    def test_open_agent_can_modify_module_let(self):
        """@open agent can modify module-level let."""
        source = """
let counter = 0

@open agent Incrementer() {
    main {
        counter = counter + 1
        return counter
    }
}

let result = Incrementer()
"""
        interp = _run(source)
        assert interp.environment.lookup("counter") == 1
        assert interp.environment.lookup("result") == 1


# ============================================================
# 6. @strict agent
# ============================================================

class TestStrictAgent:
    """Test @strict (L2) agent isolation level — deep copy params and return."""

    def test_strict_deep_copies_params(self):
        """@strict agent gets deep copy of mutable parameters."""
        source = """
@strict agent Worker(items: list) {
    main {
        // items is a deep copy — but since it's a regular list (not ReadOnlyView),
        // modifications are allowed but don't affect the caller
        return len(items)
    }
}

let data = [1, 2, 3]
let result = Worker(items = data)
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 3
        # Original data unchanged
        assert interp.environment.lookup("data") == [1, 2, 3]

    def test_strict_deep_copies_return_value(self):
        """@strict agent's return value is deep copied."""
        source = """
@strict agent Maker() {
    main {
        let arr = [1, 2, 3]
        return arr
    }
}

let result = Maker()
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == [1, 2, 3]


# ============================================================
# 7. @sandbox agent
# ============================================================

class TestSandboxAgent:
    """Test @sandbox (L3) agent isolation level — no tools."""

    def test_sandbox_agent_runs(self):
        """@sandbox agent can execute basic logic."""
        source = """
@sandbox agent Safe(input: str) {
    main {
        return input
    }
}

let result = Safe(input = "hello")
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == "hello"

    def test_sandbox_agent_deep_copies_params(self):
        """@sandbox agent gets deep copy of parameters (like @strict)."""
        source = """
@sandbox agent Safe(items: list) {
    main {
        return len(items)
    }
}

let data = [1, 2, 3]
let result = Safe(items = data)
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 3
        assert interp.environment.lookup("data") == [1, 2, 3]


# ============================================================
# 8. SharedStore
# ============================================================

class TestSharedStore:
    """Test SharedStore — structured shared mutable state."""

    def test_basic_store_creation(self):
        """SharedStore can be created and fields accessed."""
        store = SharedStore("Counter", {"count": 0}, {})
        assert store.get_field("count") == 0

    def test_field_set(self):
        """SharedStore fields can be set."""
        store = SharedStore("Counter", {"count": 0}, {})
        store.set_field("count", 42)
        assert store.get_field("count") == 42

    def test_private_attr_blocked(self):
        """Internal attributes cannot be modified via __setattr__."""
        store = SharedStore("Test", {"x": 1}, {})
        # Setting _-prefixed attributes is blocked
        with pytest.raises(AttributeError):
            store._fields = {}
        with pytest.raises(AttributeError):
            store._name = "hacked"

    def test_private_attr_set_blocked(self):
        """Internal attributes cannot be set from outside."""
        store = SharedStore("Test", {"x": 1}, {})
        with pytest.raises(AttributeError):
            store._fields = {}

    def test_method_overwrite_blocked(self):
        """Cannot overwrite a method with a field assignment."""
        methods = {"get": lambda: None}
        store = SharedStore("Test", {"x": 1}, methods)
        with pytest.raises(AttributeError):
            store.set_field = "something"

    def test_nonexistent_field_error(self):
        """Accessing nonexistent field raises AttributeError."""
        store = SharedStore("Test", {"x": 1}, {})
        with pytest.raises(AttributeError):
            store.get_field("nonexistent")

    def test_store_in_helen_program(self):
        """Shared store works in a full Helen program."""
        source = """
shared store Counter {
    let count: int = 0

    fn increment() {
        count = count + 1
    }

    fn get(): int {
        return count
    }
}

Counter.increment()
Counter.increment()
Counter.increment()
let result = Counter.get()
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 3

    def test_store_accessible_from_agent(self):
        """Shared store is accessible from inside agent main."""
        source = """
shared store Counter {
    let count: int = 0

    fn increment() {
        count = count + 1
    }

    fn get(): int {
        return count
    }
}

agent Worker() {
    main {
        Counter.increment()
        Counter.increment()
        return Counter.get()
    }
}

let result = Worker()
"""
        interp = _run(source)
        assert interp.environment.lookup("result") == 2

    def test_store_fields_clash_detection(self):
        """Semantic analysis detects duplicate field names."""
        source = """
shared store Bad {
    let x: int = 1
    let x: int = 2
}
"""
        errors = _analyze_only(source)
        assert errors.has_errors

    def test_store_method_field_clash_detection(self):
        """Semantic analysis detects method/field name clashes."""
        source = """
shared store Bad {
    let x: int = 1
    fn x() { return 1 }
}
"""
        errors = _analyze_only(source)
        assert errors.has_errors


# ============================================================
# 9. Decorator parsing
# ============================================================

class TestDecoratorParsing:
    """Test that decorators are parsed correctly."""

    def test_open_decorator(self):
        """@open is parsed correctly."""
        source = """
@open agent Debug() {
    main { return 1 }
}
"""
        errors = _analyze_only(source)
        assert not errors.has_errors

    def test_strict_decorator(self):
        """@strict is parsed correctly."""
        source = """
@strict agent Safe() {
    main { return 1 }
}
"""
        errors = _analyze_only(source)
        assert not errors.has_errors

    def test_sandbox_decorator(self):
        """@sandbox is parsed correctly."""
        source = """
@sandbox agent Isolated() {
    main { return 1 }
}
"""
        errors = _analyze_only(source)
        assert not errors.has_errors

    def test_chinese_decorators(self):
        """Chinese decorators @开放, @严格, @沙箱 work."""
        source = """
@开放 agent Debug() {
    主函 { 返回 1 }
}
"""
        errors = _analyze_only(source)
        assert not errors.has_errors

    def test_unknown_decorator_error(self):
        """Unknown decorator is rejected."""
        source = """
@unknown agent Bad() {
    main { return 1 }
}
"""
        errors = _analyze_only(source)
        assert errors.has_errors
