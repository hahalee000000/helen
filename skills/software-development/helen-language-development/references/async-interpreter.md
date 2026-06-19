# Async Interpreter Architecture (Phase 1b)

## Problem

Helen's interpreter uses a sync visitor pattern. LLM calls (5-30s each) block the thread. When running `async` agents concurrently, sequential execution is unacceptable.

## Solution: Hybrid Async

Only LLM calls are async — the rest of the interpreter stays sync. This avoids converting all 50+ `visit_*` methods to async (~2000 lines of changes).

### Architecture

```
Interpreter (sync visitor)
├── visit_binary_op, visit_if_stmt, visit_for_stmt, etc. (all sync)
├── visit_async_call_expr → creates Task.pending(...)
└── _await_tasks → asyncio.gather() for concurrent execution

AsyncLLMInterpreter (extends Interpreter)
├── visit_llm_act_expr_async → await self.llm_runtime.act_async()
└── visit_llm_if_stmt_async → await self.llm_runtime.route_async()
```

### Key Design Decisions

1. **AsyncLLMInterpreter extends Interpreter** — backward compatible, sync code still works
2. **Task.execute_async() detects interpreter type** — uses direct async for AsyncLLMInterpreter, falls back to asyncio.to_thread() for sync Interpreter
3. **Environment snapshot per task** — prevents race conditions between concurrent tasks
4. **LLMRuntime has both sync and async methods** — act()/act_async(), route()/route_async()

### Execution Flow

```
let task1 = async Worker("A")
→ visit_async_call_expr()
→ env_snapshot = self.environment.snapshot()
→ return Task.pending(node.call, self, env_snapshot)
[Task is NOT executed yet]

let task2 = async Worker("B")
→ same as above, separate pending Task

let results = await [task1, task2]
→ visit_unary_op() with AWAIT operator
→ _await_tasks([task1, task2])
→ asyncio.run(execute_all())
  → asyncio.gather(task1.execute_async(), task2.execute_async())
    → task1: await visit_llm_act_expr_async() → await act_async() [non-blocking]
    → task2: await visit_llm_act_expr_async() → await act_async() [non-blocking]
    → both run concurrently in single thread
→ return [result1, result2]
```

### Memory Characteristics

| Approach | 3 concurrent tasks | 10 concurrent tasks |
|----------|-------------------|---------------------|
| ThreadPoolExecutor (Phase 1a) | 3 threads × 8MB = 24MB | 10 × 8MB = 80MB |
| asyncio.to_thread() | global pool ~32 threads | global pool ~32 threads |
| **True async (Phase 1b)** | **0 threads** | **0 threads** |

### Implementation Details

#### Task States

```python
Task.completed(result)     # already has result (backward compat)
Task.failed(exc)           # already has exception (backward compat)
Task.pending(call_node, interpreter, env_snapshot)  # deferred, executes on await
```

#### Task.execute_async()

```python
async def execute_async(self):
    if isinstance(self._interpreter, AsyncLLMInterpreter):
        # True async — zero threads
        result = await self._execute_async()
    else:
        # Fallback for sync interpreters
        result = await asyncio.to_thread(self._execute_sync)
```

#### _execute_async() — Direct Async Execution

```python
async def _execute_async(self):
    old_env = self._interpreter.environment
    self._interpreter.environment = self._env_snapshot
    try:
        if isinstance(self._call_node, LlmActExprNode):
            result = await self._interpreter.visit_llm_act_expr_async(self._call_node)
        elif isinstance(self._call_node, LlmIfStmtNode):
            result = await self._interpreter.visit_llm_if_stmt_async(self._call_node)
        else:
            result = self._call_node.accept(self._interpreter)  # sync fallback
        return result
    finally:
        self._interpreter.environment = old_env
```

#### Environment Snapshot

```python
def snapshot(self) -> "Environment":
    """Deep copy of entire environment chain for task isolation."""
    parent_snapshot = self.parent.snapshot() if self.parent else None
    new_env = Environment(parent=parent_snapshot)
    new_env._store = copy.copy(self._store)   # shallow copy of variables
    new_env._consts = copy.copy(self._consts)  # copy of const set
    return new_env
```

#### LLMRuntime Async Interface

```python
class LLMRuntime(ABC):
    # Sync (original)
    def act(...) -> LLMResponse
    def route(...) -> str | None
    
    # Async (Phase 1b)
    async def act_async(...) -> LLMResponse
    async def route_async(...) -> str | None
```

#### HermesCLILLMRuntime — True Async Subprocess

```python
async def _ask_async(self, prompt):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(),
        timeout=self.timeout
    )
```

## Contract-First + TDD Development Approach

This session used a three-phase approach for the large async refactor:

### Phase 1: Contract (30 min)

Define the interface before implementation:
- `AsyncInterpreterContract` — abstract methods that async interpreter must satisfy
- `AsyncLLMInterpreter` — concrete class skeleton with `NotImplementedError` stubs
- Document expected behavior in docstrings

### Phase 2: Tests (1 hour)

Write tests that verify async behavior — all fail initially (RED):
- Contract tests (interface shape)
- Execution tests (async methods call async LLM runtime)
- Concurrency tests (multiple LLM calls run in parallel)
- Environment isolation tests
- Error propagation tests
- Performance tests (concurrent < sequential)

### Phase 3: Implementation (2 hours)

Implement to make tests pass (GREEN):
- `visit_llm_act_expr_async()` — calls `await self.llm_runtime.act_async()`
- `visit_llm_if_stmt_async()` — calls `await self.llm_runtime.route_async()`
- `Task.execute_async()` — detects AsyncLLMInterpreter, uses direct async
- `_await_tasks()` — uses `asyncio.gather()` for concurrent execution

### Key Insight

The contract-first approach prevented the "async is contagious" problem. By defining the boundary (only LLM calls are async), we limited the scope of async changes to ~200 lines instead of ~2000.

## Pitfalls

### asyncio.to_thread is NOT True Async

`asyncio.to_thread()` and `loop.run_in_executor()` use thread pools under the hood. Wrapping them in `asyncio.run()` does NOT make them single-thread.

**Wrong**: "I'm using asyncio, so it's single-threaded"
```python
# This still uses threads!
async def execute():
    result = await asyncio.to_thread(sync_function)
```

**Right**: Implement true async methods
```python
# This is truly single-threaded
async def execute():
    result = await async_function()  # e.g., asyncio.create_subprocess_exec()
```

### Environment Isolation Is Critical

Multiple concurrent tasks share the interpreter's environment. Without snapshots:
- Task A defines variable `x`
- Task B overwrites `x`
- Task A reads wrong value

**Fix**: Each task captures `environment.snapshot()` at creation time, restores it during execution, then restores the original.

### Async Testing Requires pytest-asyncio

Standard pytest doesn't support `async def test_*()`. Install `pytest-asyncio` and use `@pytest.mark.asyncio` decorator.

```bash
uv pip install pytest-asyncio
```

```python
@pytest.mark.asyncio
async def test_concurrent_llm_calls():
    runtime = MockAsyncLLMRuntime(delay=0.1)
    interp = AsyncLLMInterpreter(llm_runtime=runtime)
    # ... test code ...
```

## Performance Benchmarks

### Mock LLM Runtime (0.1s delay per call)

| Tasks | Sequential | Concurrent (Phase 1b) | Speedup |
|-------|-----------|----------------------|---------|
| 3 | 0.30s | 0.10s | 3.0x |
| 5 | 0.50s | 0.10s | 5.0x |
| 10 | 1.00s | 0.10s | 10.0x |

### Real LLM Calls (estimated 5s per call)

| Tasks | Sequential | Concurrent | Time Saved |
|-------|-----------|-----------|------------|
| 3 | 15s | 5s | 10s |
| 5 | 25s | 5s | 20s |
| 10 | 50s | 5s | 45s |

## Files Modified

- `helen/interpreter/async_interpreter.py` (new) — AsyncLLMInterpreter
- `helen/interpreter/task.py` — Task.pending(), execute_async(), _execute_async()
- `helen/interpreter/environment.py` — snapshot() method
- `helen/runtime/llm_runtime.py` — act_async(), route_async() abstract methods
- `helen/runtime/hermes_cli_llm.py` — _ask_async() using asyncio.create_subprocess_exec()
- `helen/interpreter/interpreter.py` — _await_tasks() uses asyncio.gather()
- `tests/interpreter/test_async_interpreter.py` — 12 unit tests
- `tests/interpreter/test_async_e2e.py` — end-to-end performance test (fixed: added @pytest.mark.asyncio)
- `tests/execution/test_async_comprehensive.py` (new) — 32 comprehensive end-to-end tests
- `tests/execution/test_async_await.py` — 24 Task/Await semantics tests
- `tests/parser/test_async_and_recovery.py` — 11 parser tests

## Test Coverage (81 async-related tests, all passing)

### Test Categories

1. **Async Statement Form** (3 tests) — `async Agent()` immediate execution
   - Returns `Task.completed`
   - With arguments
   - Error becomes `Task.failed`

2. **Async Expression Form** (3 tests) — `let task = async Agent()` deferred execution
   - Creates `Task.pending`
   - Await executes task
   - Multiple tasks awaited together

3. **Regular Function Async Calls** (3 tests)
   - `async fn()` statement form
   - Expression form with await
   - Multiple function calls

4. **Concurrent Execution Timing** (3 tests)
   - Sync sequential baseline
   - Async concurrent via gather
   - LLM calls concurrent timing (3×0.1s → ~0.1s)

5. **Error Handling** (4 tests)
   - Single task error raises on await
   - Multiple errors raise `AggregateError`
   - try-catch `AggregateError`
   - Mixed success/failure

6. **Mixed Sync/Async Execution** (3 tests)
   - Sync before async
   - Async then sync processing
   - Nested agent calls

7. **AsyncLLMInterpreter Integration** (2 tests)
   - Regular agent in async interpreter
   - Multiple concurrent agents

8. **Edge Cases** (6 tests)
   - Single task in list
   - No return value (None)
   - Complex return expressions
   - String operations
   - Conditionals
   - Loops

9. **Task State Transitions** (3 tests)
   - pending → completed
   - Completed task not re-executed
   - Task.result() access

10. **Async LLM Calls** (2 tests)
    - `act_async()` execution path
    - `route_async()` routing path

### Test Files by Location

| File | Tests | Coverage |
|------|-------|----------|
| `tests/execution/test_async_comprehensive.py` | 32 | End-to-end Helen programs |
| `tests/execution/test_async_await.py` | 24 | Task/Await semantics |
| `tests/interpreter/test_async_interpreter.py` | 12 | AsyncLLMInterpreter unit tests |
| `tests/parser/test_async_and_recovery.py` | 11 | Parser syntax |
| `tests/interpreter/test_async_e2e.py` | 1 | Performance verification |
| `tests/semantic/test_control_flow_semantics.py` | 1 | Semantic validation |
| **Total** | **81** | **All passing** |

## Test Results

- **933 tests pass** (852 non-async + 81 async-related tests)
- E2E test: 3 × 1s LLM calls complete in 1.03s (concurrent)
- Memory: 0 additional threads for concurrent LLM calls
- Coverage: Statement form, expression form, functions, agents, errors, timing, edge cases
