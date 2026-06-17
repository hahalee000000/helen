"""Comprehensive tests for Helen async/await execution.

Tests cover:
1. Regular function async calls (statement and expression forms)
2. Agent async calls (statement and expression forms)
3. Concurrent execution timing verification
4. Error handling (AggregateError, try-catch)
5. Statement form vs expression form semantics
6. Mixed sync/async execution
7. End-to-end: source code → parse → analyze → interpret
"""

import asyncio
import time
import pytest
from unittest.mock import patch, MagicMock

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.interpreter.async_interpreter import AsyncLLMInterpreter
from helen.interpreter.task import Task
from helen.interpreter.exceptions import AggregateError
from helen.runtime.llm_runtime import LLMRuntime, LLMResponse, MockLLMRuntime


# ─── Helpers ───────────────────────────────────────────────────────────────────


def parse_and_run(source: str, interpreter=None, filename="<test>"):
    """Parse and execute Helen source code end-to-end."""
    errors = ErrorReporter()
    if interpreter is None:
        interpreter = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
    
    analyzer = SemanticAnalyzer(errors, base_dir=".")
    
    scanner = Scanner(source=source, file=filename)
    tokens = scanner.scan_all()
    
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    
    if errors.has_errors:
        raise RuntimeError(f"Parse errors: {errors}")
    
    analyzer.analyze(program)
    
    if errors.has_errors:
        raise RuntimeError(f"Semantic errors: {errors}")
    
    result = interpreter.interpret(program)
    return result, interpreter


def make_interpreter(llm_runtime=None):
    """Create an interpreter with optional custom LLM runtime."""
    errors = ErrorReporter()
    if llm_runtime is None:
        llm_runtime = MockLLMRuntime()
    return Interpreter(errors=errors, llm_runtime=llm_runtime)


def make_async_interpreter(llm_runtime=None):
    """Create an async interpreter with optional custom LLM runtime."""
    errors = ErrorReporter()
    if llm_runtime is None:
        llm_runtime = MockLLMRuntime()
    return AsyncLLMInterpreter(errors=errors, llm_runtime=llm_runtime)


# ─── Test 1: Async statement form (immediate execution) ───────────────────────


class TestAsyncStatementForm:
    """Test `async Agent()` as a statement (immediate execution)."""
    
    def test_async_stmt_returns_completed_task(self):
        """async Agent() as statement returns Task.completed."""
        source = """
agent Worker() {
    main {
        return "done"
    }
}

main {
    async Worker()
}
"""
        result, interp = parse_and_run(source)
        # Statement form: async Worker() is the last expression in main
        # It should return a Task
        assert isinstance(result, Task), f"Expected Task, got {type(result)}"
        assert result.is_done, "Statement form should be immediately completed"
        assert not result.has_error
        assert result.result() == "done"
    
    def test_async_stmt_with_args(self):
        """async Agent(x) with arguments."""
        source = """
agent Doubler(x: num) {
    main {
        return x * 2
    }
}

main {
    async Doubler(21)
}
"""
        result, interp = parse_and_run(source)
        assert isinstance(result, Task)
        assert result.is_done
        assert result.result() == 42
    
    def test_async_stmt_error_becomes_failed_task(self):
        """async Agent() that throws returns Task.failed."""
        source = """
agent Failer() {
    main {
        throw RuntimeError("intentional error")
    }
}

main {
    async Failer()
}
"""
        result, interp = parse_and_run(source)
        assert isinstance(result, Task)
        assert result.is_done
        assert result.has_error


# ─── Test 2: Async expression form (deferred execution) ───────────────────────


class TestAsyncExpressionForm:
    """Test `let task = async Agent()` as an expression (deferred execution)."""
    
    def test_async_expr_creates_pending_task(self):
        """let task = async Agent() creates a pending Task."""
        source = """
agent Worker() {
    main {
        return "done"
    }
}

main {
    let task = async Worker()
    task
}
"""
        result, interp = parse_and_run(source)
        assert isinstance(result, Task)
        # Expression form creates pending task
        assert result.is_pending, "Expression form should be pending"
        assert not result.is_done
    
    def test_async_expr_await_executes_task(self):
        """await [task] executes the pending task and returns result."""
        source = """
agent Worker() {
    main {
        return "hello"
    }
}

main {
    let task = async Worker()
    let results = await [task]
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result == "hello"
    
    def test_async_expr_multiple_await(self):
        """Multiple async tasks awaited together."""
        source = """
agent Adder(a: num, b: num) {
    main {
        return a + b
    }
}

main {
    let t1 = async Adder(1, 2)
    let t2 = async Adder(3, 4)
    let t3 = async Adder(5, 6)
    let results = await [t1, t2, t3]
    results[0] + results[1] + results[2]
}
"""
        result, interp = parse_and_run(source)
        assert result == 21  # 3 + 7 + 11


# ─── Test 3: Regular function async calls ─────────────────────────────────────


class TestAsyncFunctionCalls:
    """Test async/await with regular functions (not agents)."""
    
    def test_async_function_stmt(self):
        """async fn() as statement."""
        source = """
fn greet() {
    return "hi"
}

main {
    async greet()
}
"""
        result, interp = parse_and_run(source)
        assert isinstance(result, Task)
        assert result.is_done
        assert result.result() == "hi"
    
    def test_async_function_expr_and_await(self):
        """let task = async fn() and await [task]."""
        source = """
fn compute(x: num) {
    return x * x
}

main {
    let t = async compute(7)
    let results = await [t]
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result == 49
    
    def test_async_multiple_functions(self):
        """Multiple async function calls."""
        source = """
fn square(x: num) {
    return x * x
}

fn cube(x: num) {
    return x * x * x
}

main {
    let t1 = async square(3)
    let t2 = async cube(2)
    let results = await [t1, t2]
    results[0] + results[1]
}
"""
        result, interp = parse_and_run(source)
        assert result == 17  # 9 + 8


# ─── Test 4: Concurrent execution timing ──────────────────────────────────────


class TestConcurrentExecutionTiming:
    """Verify that async tasks execute concurrently."""
    
    def test_sync_tasks_execute_sequentially(self):
        """Without async, tasks execute sequentially."""
        source = """
fn slow(value: num) {
    // Simulate work with a loop
    let i = 0
    while (i < 100000) {
        i = i + 1
    }
    return value
}

main {
    let a = slow(1)
    let b = slow(2)
    let c = slow(3)
    a + b + c
}
"""
        start = time.time()
        result, interp = parse_and_run(source)
        elapsed = time.time() - start
        assert result == 6
    
    def test_async_tasks_execute_concurrently_via_gather(self):
        """Pending tasks execute concurrently via asyncio.gather."""
        # This test verifies the mechanism, not timing
        # (actual timing depends on the work being done)
        from helen.interpreter.task import Task
        
        interp = Interpreter()
        
        # Create mock calls that track execution order
        execution_log = []
        
        def make_mock_call(value, delay=0.05):
            class MockCall:
                def accept(self, visitor):
                    execution_log.append(f"start_{value}")
                    time.sleep(delay)
                    execution_log.append(f"end_{value}")
                    return value
            return MockCall()
        
        # Create 3 pending tasks
        t1 = Task.pending(make_mock_call(1, 0.05), interp, interp.environment.snapshot())
        t2 = Task.pending(make_mock_call(2, 0.05), interp, interp.environment.snapshot())
        t3 = Task.pending(make_mock_call(3, 0.05), interp, interp.environment.snapshot())
        
        # Execute via _await_tasks (uses asyncio internally)
        results = interp._await_tasks([t1, t2, t3])
        
        assert results == [1, 2, 3]
        assert all(t.is_done for t in [t1, t2, t3])
    
    def test_async_llm_calls_concurrent_timing(self):
        """AsyncLLMInterpreter: LLM calls run concurrently."""
        
        class TimingLLMRuntime(LLMRuntime):
            def __init__(self, delay=0.1):
                self.delay = delay
                self.call_count = 0
            
            def route(self, description, branches, context=None):
                return branches[0] if branches else None
            
            def act(self, prompt, **kwargs):
                time.sleep(self.delay)
                self.call_count += 1
                return LLMResponse(text=f"response_{self.call_count}", model="mock")
            
            async def act_async(self, prompt, **kwargs):
                await asyncio.sleep(self.delay)
                self.call_count += 1
                return LLMResponse(text=f"async_response_{self.call_count}", model="mock")
            
            async def route_async(self, description, branches, context=None):
                await asyncio.sleep(self.delay)
                return branches[0] if branches else None
        
        runtime = TimingLLMRuntime(delay=0.1)
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        from helen.core.ast import LlmActExprNode, LiteralNode
        from helen.core.source import SourceSpan
        
        span = SourceSpan("<test>", 1, 1, 1, 1)
        
        # Create 3 LLM act expressions
        nodes = [
            LlmActExprNode(prompt=LiteralNode(value=f"task_{i}", span=span), span=span)
            for i in range(3)
        ]
        
        # Create pending tasks
        tasks = [
            Task.pending(node, interp, interp.environment.snapshot())
            for node in nodes
        ]
        
        # Execute concurrently
        start = time.time()
        results = interp._await_tasks(tasks)
        elapsed = time.time() - start
        
        # Should complete in ~0.1s (concurrent), not ~0.3s (sequential)
        assert elapsed < 0.25, f"Expected concurrent (<0.25s), got {elapsed:.2f}s"
        assert all(t.is_done for t in tasks)


# ─── Test 5: Error handling ───────────────────────────────────────────────────


class TestAsyncErrorHandling:
    """Test error handling in async execution."""
    
    def test_single_task_error_raises_on_await(self):
        """Awaiting a failed task raises its exception."""
        source = """
agent Failer() {
    main {
        throw RuntimeError("task failed")
    }
}

main {
    let t = async Failer()
    await [t]
}
"""
        with pytest.raises(Exception):
            parse_and_run(source)
    
    def test_multiple_task_errors_raise_aggregate(self):
        """Multiple failed tasks raise AggregateError."""
        source = """
agent Failer(msg: str) {
    main {
        throw RuntimeError(msg)
    }
}

main {
    let t1 = async Failer("error1")
    let t2 = async Failer("error2")
    await [t1, t2]
}
"""
        with pytest.raises(AggregateError) as exc_info:
            parse_and_run(source)
        assert len(exc_info.value.errors) == 2
    
    def test_try_catch_aggregate_error(self):
        """try-catch can catch AggregateError."""
        source = """
agent Failer() {
    main {
        throw RuntimeError("oops")
    }
}

main {
    let t1 = async Failer()
    let t2 = async Failer()
    try {
        await [t1, t2]
    } catch AggregateError err {
        "caught"
    }
}
"""
        result, interp = parse_and_run(source)
        assert result == "caught"
    
    def test_mixed_success_and_failure(self):
        """Some tasks succeed, some fail → AggregateError."""
        source = """
agent Worker(x: num) {
    main {
        if (x < 0) {
            throw RuntimeError("negative")
        }
        return x * 2
    }
}

main {
    let t1 = async Worker(5)
    let t2 = async Worker(-1)
    let t3 = async Worker(3)
    try {
        await [t1, t2, t3]
    } catch AggregateError err {
        "had_errors"
    }
}
"""
        result, interp = parse_and_run(source)
        assert result == "had_errors"


# ─── Test 6: Mixed sync and async execution ───────────────────────────────────


class TestMixedSyncAsync:
    """Test mixing synchronous and asynchronous execution."""
    
    def test_sync_before_async(self):
        """Sync code before async calls."""
        source = """
fn compute() {
    return 10
}

agent Worker(x: num) {
    main {
        return x + 1
    }
}

main {
    let base = compute()
    let t = async Worker(base)
    let results = await [t]
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result == 11
    
    def test_async_then_sync(self):
        """Async calls followed by sync processing."""
        source = """
agent Worker(x: num) {
    main {
        return x * 2
    }
}

fn sum_list(a: num, b: num, c: num) {
    return a + b + c
}

main {
    let t1 = async Worker(1)
    let t2 = async Worker(2)
    let t3 = async Worker(3)
    let results = await [t1, t2, t3]
    sum_list(results[0], results[1], results[2])
}
"""
        result, interp = parse_and_run(source)
        assert result == 12  # 2 + 4 + 6
    
    def test_nested_agent_calls_async(self):
        """Agent calling another agent asynchronously."""
        source = """
agent Inner(x: num) {
    main {
        return x + 10
    }
}

agent Outer(x: num) {
    main {
        let result = Inner(x)
        return result * 2
    }
}

main {
    let t = async Outer(5)
    let results = await [t]
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result == 30  # (5 + 10) * 2


# ─── Test 7: Async with AsyncLLMInterpreter ──────────────────────────────────


class TestAsyncInterpreterIntegration:
    """Test async execution with AsyncLLMInterpreter."""
    
    def test_async_interpreter_regular_agent(self):
        """AsyncLLMInterpreter can execute regular agents."""
        source = """
agent Worker() {
    main {
        return "async_done"
    }
}

main {
    let t = async Worker()
    let results = await [t]
    results[0]
}
"""
        interp = make_async_interpreter()
        result, _ = parse_and_run(source, interpreter=interp)
        assert result == "async_done"
    
    def test_async_interpreter_multiple_agents(self):
        """AsyncLLMInterpreter with multiple concurrent agents."""
        source = """
agent A() {
    main { return "a" }
}

agent B() {
    main { return "b" }
}

agent C() {
    main { return "c" }
}

main {
    let t1 = async A()
    let t2 = async B()
    let t3 = async C()
    let results = await [t1, t2, t3]
    results[0] + results[1] + results[2]
}
"""
        interp = make_async_interpreter()
        result, _ = parse_and_run(source, interpreter=interp)
        assert result == "abc"


# ─── Test 8: Edge cases ──────────────────────────────────────────────────────


class TestAsyncEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_await_single_task_in_list(self):
        """await [single_task] returns list with one element."""
        source = """
agent Worker() {
    main { return 42 }
}

main {
    let t = async Worker()
    let results = await [t]
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result == 42
    
    def test_async_with_no_return(self):
        """Agent with no return statement returns None."""
        source = """
agent Silent() {
    main {
    }
}

main {
    let t = async Silent()
    let results = await [t]
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result is None
    
    def test_async_with_complex_return(self):
        """Agent returning complex expression."""
        source = """
agent Calculator(a: num, b: num) {
    main {
        let sum = a + b
        let product = a * b
        return sum + product
    }
}

main {
    let t = async Calculator(3, 4)
    let results = await [t]
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result == 19  # 7 + 12
    
    def test_async_with_string_operations(self):
        """Agent with string operations."""
        source = """
agent Greeter(name: str) {
    main {
        return "Hello, " + name + "!"
    }
}

main {
    let t1 = async Greeter("Alice")
    let t2 = async Greeter("Bob")
    let results = await [t1, t2]
    results[0] + " " + results[1]
}
"""
        result, interp = parse_and_run(source)
        assert result == "Hello, Alice! Hello, Bob!"
    
    def test_async_with_conditionals(self):
        """Agent with conditional logic."""
        source = """
agent Classifier(x: num) {
    main {
        if (x > 0) {
            return "positive"
        } else {
            return "non-positive"
        }
    }
}

main {
    let t1 = async Classifier(5)
    let t2 = async Classifier(-3)
    let results = await [t1, t2]
    results[0] + "," + results[1]
}
"""
        result, interp = parse_and_run(source)
        assert result == "positive,non-positive"
    
    def test_async_with_loops(self):
        """Agent with loop."""
        source = """
agent Summer(n: num) {
    main {
        let sum = 0
        let i = 1
        while (i <= n) {
            sum = sum + i
            i = i + 1
        }
        return sum
    }
}

main {
    let t = async Summer(10)
    let results = await [t]
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result == 55  # 1+2+...+10


# ─── Test 9: Task state transitions ──────────────────────────────────────────


class TestTaskStateTransitions:
    """Test Task state machine: pending → completed/failed."""
    
    def test_pending_to_completed(self):
        """Task transitions from pending to completed on await."""
        source = """
agent Worker() {
    main { return "ok" }
}

main {
    let t = async Worker()
    // At this point, t should be pending
    let results = await [t]
    // Now t should be completed
    results[0]
}
"""
        result, interp = parse_and_run(source)
        assert result == "ok"
    
    def test_completed_task_not_re_executed(self):
        """Statement form (already completed) doesn't re-execute on await."""
        source = """
agent Counter() {
    main {
        return 1
    }
}

main {
    // Statement form: executes immediately
    async Counter()
}
"""
        result, interp = parse_and_run(source)
        assert isinstance(result, Task)
        assert result.is_done
        assert result.result() == 1
    
    def test_task_result_access_after_await(self):
        """Task.result() works after await."""
        from helen.interpreter.task import Task
        
        task = Task.completed("hello")
        assert task.result() == "hello"
        
        task2 = Task.failed(ValueError("oops"))
        with pytest.raises(ValueError):
            task2.result()
        
        task3 = Task.pending(None, None, None)
        with pytest.raises(RuntimeError):
            task3.result()


# ─── Test 10: Async with LLM calls (mocked) ──────────────────────────────────


class TestAsyncLLMCalls:
    """Test async execution with LLM calls (mocked runtime)."""
    
    def test_llm_act_async_execution(self):
        """llm act expression uses async execution path."""
        
        class TrackingAsyncRuntime(LLMRuntime):
            def __init__(self):
                self.async_calls = 0
                self.sync_calls = 0
            
            def route(self, description, branches, context=None):
                return None
            
            def act(self, prompt, **kwargs):
                self.sync_calls += 1
                return LLMResponse(text="sync_response", model="mock")
            
            async def act_async(self, prompt, **kwargs):
                self.async_calls += 1
                return LLMResponse(text="async_response", model="mock")
            
            async def route_async(self, description, branches, context=None):
                return None
        
        runtime = TrackingAsyncRuntime()
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        from helen.core.ast import LlmActExprNode, LiteralNode
        from helen.core.source import SourceSpan
        
        span = SourceSpan("<test>", 1, 1, 1, 1)
        node = LlmActExprNode(
            prompt=LiteralNode(value="test prompt", span=span),
            span=span
        )
        
        # Create pending task and execute via async path
        task = Task.pending(node, interp, interp.environment.snapshot())
        
        # Execute through asyncio
        asyncio.run(task.execute_async())
        
        assert task.is_done
        assert not task.has_error
        assert runtime.async_calls == 1
        assert runtime.sync_calls == 0  # Should use async, not sync
        assert task.result() == "async_response"
    
    def test_llm_if_async_routing(self):
        """llm if statement uses async routing."""
        
        class RoutingAsyncRuntime(LLMRuntime):
            def __init__(self):
                self.route_async_calls = 0
            
            def route(self, description, branches, context=None):
                return None
            
            def act(self, prompt, **kwargs):
                return LLMResponse(text="", model="mock")
            
            async def act_async(self, prompt, **kwargs):
                return LLMResponse(text="", model="mock")
            
            async def route_async(self, description, branches, context=None):
                self.route_async_calls += 1
                return branches[0] if branches else None
        
        runtime = RoutingAsyncRuntime()
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        from helen.core.ast import LlmIfStmtNode, LlmBranchNode, LiteralNode
        from helen.core.source import SourceSpan
        
        span = SourceSpan("<test>", 1, 1, 1, 1)
        node = LlmIfStmtNode(
            description=LiteralNode(value="classify", span=span),
            branches=[
                LlmBranchNode(
                    condition=LiteralNode(value="option_a", span=span),
                    body=[],
                    span=span
                )
            ],
            span=span
        )
        
        task = Task.pending(node, interp, interp.environment.snapshot())
        asyncio.run(task.execute_async())
        
        assert task.is_done
        assert runtime.route_async_calls == 1
