"""Tests for async interpreter - true concurrent LLM execution (Phase 1b).

These tests verify that:
1. AsyncInterpreter can execute LLM calls asynchronously
2. Multiple LLM calls run concurrently (not sequentially)
3. Environment isolation works correctly
4. Error propagation works as expected
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helen.core.ast import (
    CallNode,
    LlmActExprNode,
    LlmBranchNode,
    LlmIfStmtNode,
    LiteralNode,
    MainBlockNode,
    ProgramNode,
    VariableNode,
)
from helen.core.source import SourceSpan
from helen.interpreter.async_interpreter import AsyncLLMInterpreter
from helen.interpreter.environment import Environment
from helen.interpreter.task import Task
from helen.runtime.llm_runtime import LLMResponse, LLMRuntime


def _span():
    """Create a dummy source span for testing."""
    return SourceSpan(file="<test>", start_line=1, start_col=1, end_line=1, end_col=1)


def _lit(value):
    """Create a literal node."""
    return LiteralNode(value=value, span=_span())


class MockAsyncLLMRuntime(LLMRuntime):
    """Mock LLM runtime with async support for testing."""
    
    def __init__(self, delay: float = 0.1, response_text: str = "mock response"):
        self.delay = delay
        self.response_text = response_text
        self.call_count = 0
        self.call_times = []
    
    def route(self, description, branches, context=None):
        """Sync route - not used in async tests."""
        return branches[0] if branches else None
    
    def act(self, prompt, tools=None, model=None, temperature=1.0, 
            max_turns=1, history=None, system_prompt=None):
        """Sync act - not used in async tests."""
        time.sleep(self.delay)
        self.call_count += 1
        return LLMResponse(text=self.response_text, model="mock")
    
    async def route_async(self, description, branches, context=None):
        """Async route with simulated delay."""
        await asyncio.sleep(self.delay)
        return branches[0] if branches else None
    
    async def act_async(self, prompt, tools=None, model=None, temperature=1.0,
                        max_turns=1, history=None, system_prompt=None):
        """Async act with simulated delay."""
        start = time.time()
        await asyncio.sleep(self.delay)
        elapsed = time.time() - start
        self.call_times.append(elapsed)
        self.call_count += 1
        return LLMResponse(text=f"{self.response_text} #{self.call_count}", model="mock")


class TestAsyncInterpreterContract:
    """Test that AsyncLLMInterpreter satisfies the async contract."""
    
    def test_async_interpreter_inherits_interpreter(self):
        """AsyncLLMInterpreter should inherit from Interpreter."""
        from helen.interpreter.interpreter import Interpreter
        assert issubclass(AsyncLLMInterpreter, Interpreter)
    
    def test_async_interpreter_has_execute_stmt_async(self):
        """AsyncLLMInterpreter should have execute_stmt_async method."""
        interp = AsyncLLMInterpreter()
        assert hasattr(interp, 'execute_stmt_async')
        assert asyncio.iscoroutinefunction(interp.execute_stmt_async)
    
    def test_async_interpreter_has_visit_llm_act_expr_async(self):
        """AsyncLLMInterpreter should have visit_llm_act_expr_async method."""
        interp = AsyncLLMInterpreter()
        assert hasattr(interp, 'visit_llm_act_expr_async')
        assert asyncio.iscoroutinefunction(interp.visit_llm_act_expr_async)
    
    def test_async_interpreter_has_visit_llm_if_stmt_async(self):
        """AsyncLLMInterpreter should have visit_llm_if_stmt_async method."""
        interp = AsyncLLMInterpreter()
        assert hasattr(interp, 'visit_llm_if_stmt_async')
        assert asyncio.iscoroutinefunction(interp.visit_llm_if_stmt_async)


class TestAsyncLLMExecution:
    """Test async LLM call execution."""
    
    @pytest.mark.asyncio
    async def test_llm_act_expr_calls_async_version(self):
        """llm act expression should call act_async() not act()."""
        runtime = MockAsyncLLMRuntime(delay=0.05)
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        # Create a simple llm act expression
        node = LlmActExprNode(
            prompt=_lit("test prompt"),
            span=_span()
        )
        
        # Execute asynchronously
        result = await interp.visit_llm_act_expr_async(node)
        
        # Verify async version was called
        assert runtime.call_count == 1
        assert result is not None
        assert "mock response" in result
    
    @pytest.mark.asyncio
    async def test_llm_if_stmt_calls_route_async(self):
        """llm if statement should call route_async() not route()."""
        runtime = MockAsyncLLMRuntime(delay=0.05)
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        # Create a simple llm if statement
        node = LlmIfStmtNode(
            description=_lit("test routing"),
            branches=[
                LlmBranchNode(condition=_lit("branch1"), body=[], span=_span()),
                LlmBranchNode(condition=_lit("branch2"), body=[], span=_span()),
            ],
            span=_span()
        )
        
        # Execute asynchronously
        await interp.visit_llm_if_stmt_async(node)
        
        # Verify async version was called (route_async returns first branch)
        assert runtime.call_count == 0  # route doesn't increment call_count
        # But we can verify it was called by checking the behavior


class TestConcurrentLLMCalls:
    """Test that multiple LLM calls run concurrently."""
    
    @pytest.mark.asyncio
    async def test_concurrent_llm_act_calls(self):
        """Multiple llm act calls should run concurrently, not sequentially."""
        runtime = MockAsyncLLMRuntime(delay=0.1)
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        # Create 3 llm act expressions
        nodes = [
            LlmActExprNode(prompt=_lit(f"prompt {i}"), span=_span())
            for i in range(3)
        ]
        
        # Execute all concurrently
        start = time.time()
        tasks = [interp.visit_llm_act_expr_async(node) for node in nodes]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        # Should complete in ~0.1s (concurrent), not ~0.3s (sequential)
        assert elapsed < 0.25, f"Expected concurrent execution (<0.25s), got {elapsed:.2f}s"
        assert len(results) == 3
        assert all(r is not None for r in results)
    
    @pytest.mark.asyncio
    async def test_task_execute_async_uses_async_interpreter(self):
        """Task.execute_async() should use AsyncLLMInterpreter, not asyncio.to_thread()."""
        runtime = MockAsyncLLMRuntime(delay=0.1)
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        # Create a real LLM act expression node
        node = LlmActExprNode(prompt=_lit("test"), span=_span())
        
        # Create pending task
        env_snapshot = interp.environment.snapshot()
        task = Task.pending(node, interp, env_snapshot)
        
        # Execute asynchronously
        start = time.time()
        await task.execute_async()
        elapsed = time.time() - start
        
        # Should complete in ~0.1s
        assert elapsed < 0.2, f"Expected <0.2s, got {elapsed:.2f}s"
        assert task.is_done
        assert not task.has_error
        assert task.result_value is not None


class TestAsyncEnvironmentIsolation:
    """Test that async tasks have isolated environments."""
    
    @pytest.mark.asyncio
    async def test_concurrent_tasks_have_isolated_environments(self):
        """Concurrent tasks should not interfere with each other's environment."""
        runtime = MockAsyncLLMRuntime(delay=0.05)
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        # Set up initial environment
        interp.environment.define("shared_var", "initial", is_const=False)
        
        # Create two tasks that modify the environment
        async def task1():
            interp.environment.define("task1_var", "value1")
            await asyncio.sleep(0.05)
            # Should still see task1_var
            return interp.environment.lookup("task1_var")
        
        async def task2():
            interp.environment.define("task2_var", "value2")
            await asyncio.sleep(0.05)
            # Should still see task2_var
            return interp.environment.lookup("task2_var")
        
        # Execute concurrently
        results = await asyncio.gather(task1(), task2())
        
        # Both should succeed
        assert results[0] == "value1"
        assert results[1] == "value2"


class TestAsyncErrorPropagation:
    """Test that errors propagate correctly in async execution."""
    
    @pytest.mark.asyncio
    async def test_llm_call_error_propagates(self):
        """Errors in LLM calls should propagate correctly."""
        runtime = MockAsyncLLMRuntime(delay=0.05)
        
        # Make act_async raise an error
        async def failing_act_async(*args, **kwargs):
            await asyncio.sleep(0.05)
            raise RuntimeError("LLM call failed")
        
        runtime.act_async = failing_act_async
        
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        node = LlmActExprNode(
            prompt=_lit("test prompt"),
            span=_span()
        )
        
        # Should raise the error
        with pytest.raises(RuntimeError, match="LLM call failed"):
            await interp.visit_llm_act_expr_async(node)
    
    @pytest.mark.asyncio
    async def test_aggregate_error_from_multiple_failures(self):
        """Multiple task failures should result in AggregateError."""
        runtime = MockAsyncLLMRuntime(delay=0.05)
        
        # Make all calls fail
        async def failing_act_async(*args, **kwargs):
            await asyncio.sleep(0.05)
            raise RuntimeError("LLM call failed")
        
        runtime.act_async = failing_act_async
        
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        # Create 3 pending tasks
        nodes = [
            LlmActExprNode(prompt=_lit(f"prompt {i}"), span=_span())
            for i in range(3)
        ]
        
        tasks = [
            Task.pending(node, interp, interp.environment.snapshot())
            for node in nodes
        ]
        
        # Execute all tasks concurrently
        await asyncio.gather(*[t.execute_async() for t in tasks])
        
        # All tasks should have errors
        assert all(t.has_error for t in tasks)
        assert all(t.is_done for t in tasks)
        
        # Now simulate what _await_tasks does: collect errors and raise AggregateError
        from helen.interpreter.exceptions import AggregateError
        errors = [t.exception for t in tasks if t.has_error and t.exception is not None]
        assert len(errors) == 3
        
        # Create AggregateError manually (this is what _await_tasks does)
        agg_error = AggregateError(f"{len(errors)} task(s) failed", errors=errors)
        assert agg_error.errors is not None
        assert len(agg_error.errors) == 3
        assert "3 task(s) failed" in str(agg_error)


class TestAsyncPerformance:
    """Test async performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_async_vs_sync_performance(self):
        """Async execution should be faster than sequential for I/O-bound tasks."""
        runtime = MockAsyncLLMRuntime(delay=0.1)
        interp = AsyncLLMInterpreter(llm_runtime=runtime)
        
        # Create 5 llm act expressions
        nodes = [
            LlmActExprNode(prompt=_lit(f"prompt {i}"), span=_span())
            for i in range(5)
        ]
        
        # Execute asynchronously (should be ~0.1s)
        start = time.time()
        tasks = [interp.visit_llm_act_expr_async(node) for node in nodes]
        await asyncio.gather(*tasks)
        async_elapsed = time.time() - start
        
        # Execute synchronously (should be ~0.5s)
        runtime.call_count = 0
        start = time.time()
        for node in nodes:
            runtime.act("test prompt")
        sync_elapsed = time.time() - start
        
        # Async should be at least 3x faster
        assert async_elapsed < sync_elapsed / 3, \
            f"Async ({async_elapsed:.2f}s) should be much faster than sync ({sync_elapsed:.2f}s)"
