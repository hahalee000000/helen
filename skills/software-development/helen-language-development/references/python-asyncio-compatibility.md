# Python Asyncio Compatibility Patterns

## Context

When implementing async/await features in Helen language (or any Python-based interpreter/REPL), several compatibility issues arise across Python versions and execution contexts.

## Event Loop Detection in REPL vs Script

### Problem

`asyncio.get_running_loop()` raises `RuntimeError` when no event loop is running, but the exception handling can be unreliable in certain contexts (REPL environments, nested calls).

### Solution

Use `asyncio.get_event_loop()` with `is_running()` check:

```python
import asyncio

# Safe event loop detection
in_event_loop = False
try:
    _loop = asyncio.get_event_loop()
    if _loop.is_running():
        in_event_loop = True
except Exception:
    # No event loop or can't determine
    in_event_loop = False

if in_event_loop:
    # Already in event loop (e.g., REPL) - use executor directly
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(sync_function)
        result = future.result()
else:
    # No event loop - use asyncio.run()
    asyncio.run(async_function())
```

### Why This Works

- `get_event_loop()` is more permissive than `get_running_loop()`
- `is_running()` explicitly checks loop state
- Catching `Exception` (not just `RuntimeError`) handles edge cases
- Works in REPL, scripts, tests, and nested contexts

## Python 3.7+ Compatibility

### Problem

`asyncio.to_thread()` was introduced in Python 3.9. Using it breaks on Python 3.7 and 3.8.

### Solution

Use `loop.run_in_executor()` which is available in Python 3.7+:

```python
# ❌ Python 3.9+ only
result = await asyncio.to_thread(sync_function, arg1, arg2)

# ✅ Python 3.7+ compatible
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, sync_function, arg1, arg2)
```

### When to Use Each

| API | Python Version | Use Case |
|-----|---------------|----------|
| `asyncio.to_thread()` | 3.9+ | Modern code, no backward compat needed |
| `loop.run_in_executor()` | 3.7+ | Library code, REPL, backward compatibility |

### Implementation Pattern

For Helen interpreter (or similar), the pattern is:

```python
async def execute_async(self):
    if isinstance(self._interpreter, AsyncInterpreter):
        # True async execution
        result = await self._execute_async()
    else:
        # Fallback to thread pool (Python 3.7+ compatible)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._execute_sync)
```

## Testing Async Code

### pytest-asyncio Configuration

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
```

With `strict` mode, all async tests must be decorated:

```python
import pytest

@pytest.mark.asyncio
async def test_async_behavior():
    result = await async_function()
    assert result == expected
```

### Common Pitfall

Forgetting `@pytest.mark.asyncio` decorator causes:
```
FAILED test_async.py::test_name - async def functions are not natively supported.
```

Always add the decorator for async test functions.

## REPL-Specific Considerations

### Problem

REPL environments may already have a running event loop. Calling `asyncio.run()` inside a running loop raises:
```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

### Solution

Detect the loop state and branch accordingly (see "Event Loop Detection" above).

### Testing REPL Behavior

To test REPL-like behavior:

```python
import asyncio

async def test_in_event_loop():
    # Simulate REPL environment
    loop = asyncio.get_event_loop()
    # Now test code that detects running loop
    result = await some_async_function()
    assert result == expected
```

## Summary Checklist

When implementing async features in Python-based interpreters:

- [ ] Use `get_event_loop()` + `is_running()` for loop detection
- [ ] Use `run_in_executor()` for Python 3.7+ compatibility (not `to_thread()`)
- [ ] Handle both REPL (running loop) and script (no loop) contexts
- [ ] Decorate async tests with `@pytest.mark.asyncio`
- [ ] Test in both REPL and script execution modes
- [ ] Document Python version requirements (3.7+ minimum)
