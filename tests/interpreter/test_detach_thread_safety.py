"""Tests for detach thread safety (Issue #29)."""

from __future__ import annotations

import threading
import time

import pytest

from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime


class TestDetachThreadSafety:
    """Test detach thread safety and environment isolation."""

    def test_detach_creates_environment_snapshot(self):
        """Test that detach creates an environment snapshot for isolation."""
        source = """
let counter = 0

agent IncrementCounter {
    description "Increment counter"
    main {
        counter = counter + 1
    }
}

counter = 0
detach IncrementCounter()
detach IncrementCounter()
detach IncrementCounter()

// Counter should still be 0 (main process environment is isolated)
print(counter)
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="test.helen")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()

        runtime = MockLLMRuntime()
        interpreter = Interpreter(errors=errors, llm_runtime=runtime)

        # Execute the program
        interpreter.interpret(program)

        # The main process counter should still be 0
        # because detach creates isolated environment snapshots
        counter_value = interpreter.environment.lookup("counter")
        assert counter_value == 0, f"Expected counter to be 0, got {counter_value}"

    def test_detach_isolated_environment(self):
        """Test that detached agents cannot modify main process variables."""
        source = """
let shared_data = "original"

agent ModifyData {
    description "Modify shared data"
    main {
        shared_data = "modified"
    }
}

shared_data = "original"
detach ModifyData()

// shared_data should still be "original"
print(shared_data)
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="test.helen")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()

        runtime = MockLLMRuntime()
        interpreter = Interpreter(errors=errors, llm_runtime=runtime)

        # Execute the program
        interpreter.interpret(program)

        # The main process shared_data should still be "original"
        shared_data_value = interpreter.environment.lookup("shared_data")
        assert shared_data_value == "original", \
            f"Expected shared_data to be 'original', got {shared_data_value}"

    def test_detach_multiple_agents_no_race_condition(self):
        """Test that multiple detach agents don't cause race conditions."""
        source = """
let results = []

agent AddResult(value: int) {
    description "Add result"
    main {
        results.append(value)
    }
}

// Launch multiple agents concurrently
detach AddResult(1)
detach AddResult(2)
detach AddResult(3)
detach AddResult(4)
detach AddResult(5)

// results should still be empty (main process is isolated)
print(len(results))
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="test.helen")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()

        runtime = MockLLMRuntime()
        interpreter = Interpreter(errors=errors, llm_runtime=runtime)

        # Execute the program
        interpreter.interpret(program)

        # The main process results should still be empty
        results_value = interpreter.environment.lookup("results")
        assert len(results_value) == 0, \
            f"Expected results to be empty, got {len(results_value)} items"

    def test_detach_error_isolation(self):
        """Test that errors in detached agents don't affect main process."""
        source = """
let status = "running"

agent FailingAgent {
    description "Agent that fails"
    main {
        // This will cause an error
        undefined_variable = 42
        status = "failed"
    }
}

status = "running"
detach FailingAgent()

// status should still be "running" (error is isolated)
print(status)
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="test.helen")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()

        runtime = MockLLMRuntime()
        interpreter = Interpreter(errors=errors, llm_runtime=runtime)

        # Execute the program (should not raise exception)
        interpreter.interpret(program)

        # The main process status should still be "running"
        status_value = interpreter.environment.lookup("status")
        assert status_value == "running", \
            f"Expected status to be 'running', got {status_value}"
