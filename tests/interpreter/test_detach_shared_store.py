"""Tests for detach + shared store/channel integration.

v1.17: Detached agents can now access and update shared store/channel instances.
This enables controlled cross-thread communication while maintaining thread safety
through SharedStore's internal RLock mechanism.
"""
import pytest
import time
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


def run_helen_code(code: str) -> Interpreter:
    """Helper to run Helen code and return the interpreter state."""
    errors = ErrorReporter()
    scanner = Scanner(source=code, file="test.helen")
    tokens = scanner.scan_all()

    parser = Parser(tokens, errors=errors)
    ast = parser.parse()

    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(ast)

    interpreter = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
    interpreter.interpret(ast)

    return interpreter


class TestDetachSharedStore:
    """Test detach with shared store integration."""

    def test_detach_can_update_shared_store(self):
        """Detached agent can update shared store (visible to main thread)."""
        code = """
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
}

detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
"""
        interpreter = run_helen_code(code)
        time.sleep(0.2)  # Wait for detached tasks

        counter = interpreter.environment.lookup("Counter")
        result = counter.get_field("count")
        assert result == 3, f"Expected count=3, got {result}"

    def test_detach_can_call_shared_store_methods(self):
        """Detached agent can call shared store methods."""
        code = """
shared store TaskRegistry {
    let tasks: list = []
    fn add(task: str) { tasks.append(task) }
}

detach TaskRegistry.add("task1")
detach TaskRegistry.add("task2")
"""
        interpreter = run_helen_code(code)
        time.sleep(0.2)

        registry = interpreter.environment.lookup("TaskRegistry")
        tasks = registry.get_field("tasks")
        assert len(tasks) == 2, f"Expected 2 tasks, got {len(tasks)}"
        assert "task1" in tasks
        assert "task2" in tasks

    def test_multiple_detaches_share_same_store(self):
        """Multiple detached operations share the same shared store."""
        code = """
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
}

detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
"""
        interpreter = run_helen_code(code)
        time.sleep(0.2)

        counter = interpreter.environment.lookup("Counter")
        result = counter.get_field("count")
        assert result == 5, f"Expected count=5, got {result}"


class TestDetachChannel:
    """Test detach with channel integration."""

    def test_detach_can_access_channel(self):
        """Detached agent can access channel (same as shared store)."""
        code = """
channel MessageQueue {
    let messages: list = []
    fn send(msg: str) { messages.append(msg) }
}

detach MessageQueue.send("hello")
detach MessageQueue.send("world")
"""
        interpreter = run_helen_code(code)
        time.sleep(0.2)

        queue = interpreter.environment.lookup("MessageQueue")
        messages = queue.get_field("messages")
        assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
        assert "hello" in messages
        assert "world" in messages

    def test_channel_thread_safety(self):
        """Channel operations are thread-safe with multiple detached agents."""
        code = """
channel Counter {
    let value: int = 0
    fn increment() { value = value + 1 }
}

detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()
"""
        interpreter = run_helen_code(code)
        time.sleep(0.3)

        counter = interpreter.environment.lookup("Counter")
        result = counter.get_field("value")
        assert result == 10, f"Expected value=10, got {result}"


class TestDetachSharedStoreWithOtherVariables:
    """Test that shared store works correctly alongside regular variables."""

    def test_regular_variables_still_isolated(self):
        """Regular variables are still deep-copied (not shared)."""
        code = """
let regular_var: int = 10

shared store SharedCounter {
    let count: int = 0
    fn increment() { count = count + 1 }
}

detach SharedCounter.increment()
"""
        interpreter = run_helen_code(code)
        time.sleep(0.2)

        # Shared store should be updated
        counter = interpreter.environment.lookup("SharedCounter")
        result = counter.get_field("count")
        assert result == 1, f"Expected count=1, got {result}"

        # Regular variable should still exist (isolated)
        regular = interpreter.environment.lookup("regular_var")
        assert regular == 10, f"Expected regular_var=10, got {regular}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
