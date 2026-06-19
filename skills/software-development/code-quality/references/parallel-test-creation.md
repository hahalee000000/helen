# Parallel Test Creation with delegate_task

Technique for rapidly improving test coverage by spawning multiple subagents to create test files in parallel.

## When to Use

- Coverage is below target (e.g., <80%)
- Multiple modules need test coverage
- You have clear understanding of what needs testing (from coverage reports)
- Time is constrained (parallel execution is 3x faster than sequential)

## Pattern: 3-Way Parallel Test Creation

```python
delegate_task(tasks=[
    {
        "goal": "Create test file /path/to/tests/module_a/test_foo.py for /path/to/src/module_a/foo.py. Read the source first, then write comprehensive tests covering all public functions. Write at least 30 test cases.",
        "context": "The module has 0% coverage. Focus on: function X, function Y, error cases. Use pytest style. Mock external dependencies.",
        "toolsets": ["terminal", "file"]
    },
    {
        "goal": "Create test file /path/to/tests/module_b/test_bar.py for /path/to/src/module_b/bar.py. Read the source first, then write comprehensive tests. Write at least 25 test cases.",
        "context": "The module has 20% coverage. Focus on uncovered lines: 45-80, 120-150. Use tmp_path for file operations.",
        "toolsets": ["terminal", "file"]
    },
    {
        "goal": "Create test file /path/to/tests/module_c/test_baz.py for /path/to/src/module_c/baz.py. Read the source first, then write tests. Write at least 40 test cases.",
        "context": "The module is a core interpreter with 43% coverage. Focus on: REPL management, control flow, error handling. Use existing test patterns from /path/to/tests/ as reference.",
        "toolsets": ["terminal", "file"]
    }
])
```

## Key Principles

### 1. Give Each Subagent Full Context
- **File paths**: Absolute paths to source and target test files
- **Coverage data**: Which lines are uncovered (from `--cov-report=term-missing`)
- **Test count**: Minimum number of test cases expected
- **Patterns to follow**: Point to existing test files as examples
- **Mocking guidance**: What external dependencies need mocking

### 2. Let Subagents Read Source First
Don't try to describe every function in the context. Let the subagent read the source file and discover what needs testing. This is more reliable than trying to enumerate all edge cases upfront.

### 3. Specify Test Style
Always specify:
- "Use pytest style" (not unittest)
- "Use tmp_path fixture for file operations"
- "Mock external dependencies with unittest.mock.patch"
- "Write at least N test cases" (set realistic minimums)

### 4. Verify After Parallel Execution
After delegate_task completes:
```bash
# Run all new tests
pytest tests/module_a/ tests/module_b/ tests/module_c/ -v --tb=short

# Check coverage improvement
pytest --cov=helen.module_a tests/module_a/ --cov-report=term-missing -q
pytest --cov=helen.module_b tests/module_b/ --cov-report=term-missing -q
pytest --cov=helen.module_c tests/module_c/ --cov-report=term-missing -q
```

## Real-World Example (Helen Language, 2026-06-19)

**Goal**: Improve coverage for runtime and interpreter modules.

**Delegated tasks**:
1. `test_fuzzy_match.py` — 77 tests, coverage 0% → 90%
2. `test_config_coverage.py` — 50 tests, coverage 20% → 98%
3. `test_interpreter_coverage.py` — 126 tests, coverage 43% → 79%

**Result**: 253 new test cases created in ~9 minutes (parallel), all passing.

**Additional tests created sequentially** (not delegated):
- `test_tools_coverage.py` — 61 tests, coverage 20% → 80%+
- `test_constants.py` — 30 tests, coverage 0% → 100%

**Total**: 344 new test cases, all passing.

## Pitfalls

### Subagent May Not Run Tests
Subagents are instructed to "write tests" but may not run them. Always verify:
```bash
pytest tests/new_test_file.py -v --tb=short
```

### Coverage Tool Output Parsing
`pytest --cov` output format varies. Don't rely on grep patterns like:
```bash
# ❌ Doesn't work reliably
pytest --cov=helen.runtime tests/runtime/ | grep -E "^(helen/runtime|TOTAL)"
```

Instead, use:
```bash
# ✅ Reliable approaches
pytest --cov=helen.runtime tests/runtime/ -q | tail -15
pytest --cov=helen.runtime tests/runtime/ --tb=no | tail -20
```

Or redirect to file:
```bash
pytest --cov=helen.runtime tests/runtime/ > /tmp/cov.txt 2>&1
cat /tmp/cov.txt | tail -20
```

### Subagent May Create Failing Tests
Subagents may write tests that fail due to:
- Incorrect assumptions about API
- Missing imports
- Wrong mock targets

**Fix**: Run tests immediately after delegate_task completes, fix failures manually.

### Memory Constraints
On memory-constrained machines (1.8GB RAM), running full test suite with coverage can OOM. Use per-module coverage:
```bash
# ✅ Safe
pytest --cov=helen.runtime tests/runtime/ -q

# ❌ May OOM
pytest --cov=helen tests/ -q
```

## Tool Testing Patterns

### Mocking HTTP Calls
```python
from unittest.mock import patch, MagicMock
import json

def test_web_fetch_success():
    html_content = b"<html><body><p>Hello</p></body></html>"
    mock_resp = MagicMock()
    mock_resp.read.return_value = html_content
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = json.loads(_web_fetch("https://example.com"))
        assert "content" in result
        assert "Hello" in result["content"]
```

### Using tmp_path for File Operations
```python
def test_read_file(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")
    result = json.loads(_read_file(str(test_file)))
    assert result["content"] == "hello world"
```

### Using monkeypatch for Config/Environment
```python
def test_load_skill_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("helen.runtime.config.get_skill_dirs", lambda: [tmp_path])
    result = json.loads(_load_skill("nonexistent_skill"))
    assert "error" in result
```

### Testing Shell Commands
```python
def test_shell_exec_stderr():
    # ❌ Doesn't work: shell interprets >&2
    result = json.loads(_shell_exec("echo error >&2"))
    
    # ✅ Works: use bash -c with shell=False
    result = json.loads(_shell_exec("bash -c 'echo error >&2'", shell=False))
    assert "[stderr]" in result["output"]
```

## When NOT to Use delegate_task

- **Single module**: If only one module needs tests, just write them directly
- **Complex interdependencies**: If tests for module A depend on tests for module B, sequential is clearer
- **Exploratory testing**: If you're not sure what needs testing, read the source yourself first
- **Quick fixes**: If you just need 5-10 tests, don't bother with delegation overhead
