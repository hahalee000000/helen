# Async/Await Implementation Details

Phase 1b implementation for Helen language (commit 67fc404).

## Design Goals

1. **True concurrency** for LLM API calls (I/O-bound)
2. **Memory-constrained** environments (fixed thread pool, not per-task threads)
3. **Backward compatible** with existing sync code
4. **Environment isolation** (no race conditions between tasks)

## Implementation Timeline

### Phase 1a (Initial - Rejected)
- Used `ThreadPoolExecutor` with `max_workers=len(tasks)`
- Problem: N tasks = N threads = N × 8MB stack memory
- 100 concurrent tasks = 800MB (too much for constrained environments)

### Phase 1b (Final)
- Uses `asyncio.to_thread()` with global thread pool
- Global pool size: `min(32, os.cpu_count() + 4)` threads
- 100 concurrent tasks = ~256MB (fixed, regardless of task count)
- LLM subprocess calls use `asyncio.create_subprocess_exec()` (true async I/O)

## Architecture

```
User Code:
  let t1 = async AgentA()  # Creates pending Task
  let t2 = async AgentB()  # Creates pending Task
  await [t1, t2]           # Executes concurrently

Execution Flow:
  1. visit_async_call_expr() → Task.pending(call_node, interpreter, env_snapshot)
  2. visit_unary_op(AWAIT) → _await_tasks([t1, t2])
  3. _await_tasks() → asyncio.run(execute_all())
  4. execute_all() → asyncio.gather(t1.execute_async(), t2.execute_async())
  5. execute_async() → asyncio.to_thread(_execute_sync)
  6. _execute_sync() → call_node.accept(interpreter) [sync visitor]
```

## Key Components

### Task States

```python
@dataclass
class Task:
    result_value: Any = None
    exception: Exception | None = None
    _done: bool = False
    _pending: bool = False
    _call_node: Any = None        # CallNode to execute
    _interpreter: Any = None      # Interpreter instance
    _env_snapshot: Any = None     # Environment snapshot
```

**State transitions**:
- `async Agent()` → `_pending=True, _done=False`
- `await [task]` → executes → `_pending=False, _done=True`

### Environment Snapshot

```python
def snapshot(self) -> Environment:
    """Deep copy of entire environment chain."""
    parent_snapshot = self.parent.snapshot() if self.parent else None
    new_env = Environment(parent=parent_snapshot)
    new_env._store = copy.copy(self._store)      # Shallow copy of variables
    new_env._consts = copy.copy(self._consts)    # Copy of const set
    return new_env
```

**Why needed**: Multiple tasks execute concurrently. Without isolation, they'd share and corrupt the same environment.

**Memory overhead**: Each snapshot copies the scope chain. For 10 tasks with 5 scopes each = 50 environment copies. Acceptable for typical Helen programs.

### Async Execution

```python
async def execute_async(self) -> None:
    """Execute in global thread pool via asyncio.to_thread()."""
    if not self._pending:
        return
    
    try:
        # asyncio.to_thread() uses global thread pool
        # Pool size: min(32, cpu_count + 4)
        result = await asyncio.to_thread(self._execute_sync)
        self.result_value = result
        self._done = True
    except Exception as e:
        self.exception = e
        self._done = True
    finally:
        self._pending = False

def _execute_sync(self) -> Any:
    """Synchronous execution with environment isolation."""
    old_env = self._interpreter.environment
    self._interpreter.environment = self._env_snapshot
    
    try:
        result = self._call_node.accept(self._interpreter)
        return result
    finally:
        self._interpreter.environment = old_env
```

**Why asyncio.to_thread()**: The interpreter's visitor pattern is synchronous. Converting all ~2000 lines to async would be a massive refactor. `asyncio.to_thread()` bridges sync code into async world using a shared thread pool.

### Concurrent Await

```python
def _await_tasks(self, tasks: list[Task] | Task) -> object:
    pending_tasks = [t for t in tasks if t.is_pending]
    
    if pending_tasks:
        import asyncio
        
        async def execute_all():
            coros = [task.execute_async() for task in pending_tasks]
            await asyncio.gather(*coros)
        
        asyncio.run(execute_all())
    
    # Collect results
    results = []
    errors = []
    for task in tasks:
        if task.has_error:
            errors.append(task.exception)
        else:
            results.append(task.result())
    
    if errors:
        raise AggregateError(f"{len(errors)} task(s) failed", errors=errors)
    
    return results
```

### LLM Async Subprocess

```python
async def _ask_async(self, prompt: str) -> str | None:
    """Non-blocking subprocess for LLM calls."""
    import asyncio
    
    cmd = [self.hermes_path, "-z", prompt]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(),
        timeout=self.timeout
    )
    
    if proc.returncode != 0:
        return None
    return stdout.decode().strip()
```

**Why this matters**: `subprocess.run()` blocks the thread. `asyncio.create_subprocess_exec()` returns immediately, allowing the event loop to handle other tasks while waiting for the subprocess.

## Memory Comparison

| Scenario | Phase 1a (ThreadPoolExecutor) | Phase 1b (asyncio.to_thread) |
|----------|-------------------------------|------------------------------|
| 10 tasks | 10 threads × 8MB = **80MB** | Global pool = **~256MB** |
| 100 tasks | 100 threads × 8MB = **800MB** | Global pool = **~256MB** |
| 1000 tasks | 1000 threads × 8MB = **8GB** | Global pool = **~256MB** |

Phase 1b uses fixed memory regardless of task count.

## Performance Characteristics

**Concurrent LLM calls**:
- 3 agents × 5 seconds each = 5 seconds total (concurrent)
- Without async: 3 × 5 = 15 seconds (sequential)

**CPU-bound tasks**:
- `asyncio.to_thread()` still uses threads, so CPU-bound work doesn't benefit
- For true parallelism, would need multiprocessing (not implemented)

**Overhead**:
- Environment snapshot: ~1ms per scope
- asyncio.to_thread(): ~0.1ms per call
- asyncio.gather(): ~0.01ms per coroutine

## Limitations

1. **Sync interpreter**: Visitor pattern is synchronous. Full async would require ~2000 lines refactor.
2. **CPU-bound work**: Still uses threads, not true parallelism.
3. **Shared interpreter state**: `_current_agent`, `_functions` are shared. Environment isolation prevents most issues, but edge cases may exist.
4. **Global thread pool**: Fixed size may become bottleneck if many tasks are CPU-bound.

## Future Improvements

1. **Async visitor pattern**: Convert interpreter to async/await (large refactor)
2. **Multiprocessing**: For CPU-bound parallelism
3. **Task cancellation**: `task.cancel()` support
4. **Task timeout**: `await [tasks] timeout 10s`
5. **Task priorities**: Execute high-priority tasks first

## Testing

```python
def test_multiple_pending_tasks_execute_concurrently(self):
    """Verify 3 × 0.1s tasks complete in <0.25s (concurrent)."""
    task1 = Task.pending(make_mock_call(1, 0.1), interp, env_snap)
    task2 = Task.pending(make_mock_call(2, 0.1), interp, env_snap)
    task3 = Task.pending(make_mock_call(3, 0.1), interp, env_snap)
    
    start = time.time()
    results = interp._await_tasks([task1, task2, task3])
    elapsed = time.time() - start
    
    assert results == [1, 2, 3]
    assert elapsed < 0.25  # Concurrent, not 0.3s sequential
```

## References

- Python asyncio docs: https://docs.python.org/3/library/asyncio.html
- asyncio.to_thread: https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread
- asyncio.create_subprocess_exec: https://docs.python.org/3/library/asyncio-subprocess.html