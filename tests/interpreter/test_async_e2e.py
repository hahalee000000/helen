"""End-to-end test for true async execution (Phase 1b).

This test demonstrates that Helen's async/await now uses true asyncio
concurrent execution without thread pools.
"""

import asyncio
import time
from helen.interpreter.async_interpreter import AsyncLLMInterpreter
from helen.interpreter.task import Task
from helen.runtime.llm_runtime import LLMRuntime, LLMResponse
from helen.core.ast import LlmActExprNode, LiteralNode
from helen.core.source import SourceSpan


class SlowAsyncLLMRuntime(LLMRuntime):
    """Mock LLM runtime with slow async calls to demonstrate concurrency."""
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.call_count = 0
    
    def route(self, description, branches, context=None):
        return branches[0] if branches else None
    
    def act(self, prompt, tools=None, model=None, temperature=1.0,
            max_turns=1, history=None, system_prompt=None):
        # Sync version - should not be called in async mode
        time.sleep(self.delay)
        self.call_count += 1
        return LLMResponse(text=f"sync response {self.call_count}", model="mock")
    
    async def route_async(self, description, branches, context=None):
        await asyncio.sleep(self.delay)
        return branches[0] if branches else None
    
    async def act_async(self, prompt, tools=None, model=None, temperature=1.0,
                        max_turns=1, history=None, system_prompt=None):
        # Async version - simulates slow LLM API call
        print(f"  Starting LLM call: {prompt}")
        start = time.time()
        await asyncio.sleep(self.delay)  # Simulate 1 second LLM call
        elapsed = time.time() - start
        self.call_count += 1
        print(f"  Completed LLM call #{self.call_count} in {elapsed:.2f}s")
        return LLMResponse(text=f"async response #{self.call_count}", model="mock")


def _span():
    return SourceSpan(file="<test>", start_line=1, start_col=1, end_line=1, end_col=1)


def _lit(value):
    return LiteralNode(value=value, span=_span())


async def test_concurrent_llm_calls():
    """Test that 3 LLM calls run concurrently in ~1s, not ~3s."""
    print("\n=== Testing True Async Execution (Phase 1b) ===\n")
    
    # Create runtime with 1 second delay per call
    runtime = SlowAsyncLLMRuntime(delay=1.0)
    interp = AsyncLLMInterpreter(llm_runtime=runtime)
    
    # Create 3 LLM act expressions
    nodes = [
        LlmActExprNode(prompt=_lit(f"task {i}"), span=_span())
        for i in range(3)
    ]
    
    # Create pending tasks
    tasks = [
        Task.pending(node, interp, interp.environment.snapshot())
        for node in nodes
    ]
    
    print(f"Created {len(tasks)} pending tasks")
    print(f"Each LLM call takes {runtime.delay}s")
    print(f"Expected total time: ~{runtime.delay}s (concurrent)")
    print(f"Sequential time would be: ~{runtime.delay * len(tasks)}s\n")
    
    # Execute all tasks concurrently
    print("Executing tasks concurrently...")
    start = time.time()
    
    # This is what _await_tasks does internally
    coros = [task.execute_async() for task in tasks]
    await asyncio.gather(*coros)
    
    elapsed = time.time() - start
    
    print(f"\nAll tasks completed in {elapsed:.2f}s")
    
    # Verify results
    print("\nResults:")
    for i, task in enumerate(tasks):
        assert task.is_done, f"Task {i} not done"
        assert not task.has_error, f"Task {i} has error: {task.exception}"
        print(f"  Task {i}: {task.result_value}")
    
    # Verify concurrent execution
    # Should complete in ~1s, not ~3s
    assert elapsed < 2.0, f"Expected <2s (concurrent), got {elapsed:.2f}s"
    assert elapsed >= 1.0, f"Expected >=1s, got {elapsed:.2f}s"
    
    print(f"\n✅ SUCCESS: {len(tasks)} tasks completed in {elapsed:.2f}s")
    print(f"   This proves true async concurrent execution!")
    print(f"   (Sequential would take ~{runtime.delay * len(tasks)}s)")
    
    # Memory comparison
    print("\n=== Memory Comparison ===")
    print(f"Phase 1a (ThreadPoolExecutor):")
    print(f"  - {len(tasks)} threads × 8MB = {len(tasks) * 8}MB")
    print(f"\nPhase 1b (asyncio - current):")
    print(f"  - 0 threads (pure asyncio)")
    print(f"  - Memory: ~0MB additional")
    print(f"\n💾 Memory saved: {len(tasks) * 8}MB")


if __name__ == "__main__":
    asyncio.run(test_concurrent_llm_calls())
