# Helen Language Quality Assessment Patterns (2026-06)

## 7-Dimension Quality Assessment Framework

Applied 3 times to Helen codebase. Each round produced measurable improvements.

### Dimensions & Weights

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| 1. Architecture Design | 20% | Layer clarity, pattern usage, separation of concerns |
| 2. Code Quality | 15% | Dead code, silent exceptions, code duplication, function length |
| 3. Security | 20% | Input validation, sandbox coverage, path/URL/command validation |
| 4. Test Coverage | 15% | pytest --cov per module, test/source ratio, edge cases |
| 5. Documentation | 10% | docstring coverage, tutorial sync, language consistency |
| 6. Maintainability | 10% | Code duplication, shared utilities, dependency direction |
| 7. Engineering Standards | 10% | flake8, type annotations, CI/CD, pre-commit |

### Assessment Workflow

```
1. Scan codebase: wc -l, find patterns, grep for issues
2. Run metrics: flake8, pytest --cov, test count
3. Score each dimension (1-10) with evidence
4. Prioritize fixes: P0 (immediate) → P1 (this iteration) → P2 (continuous)
5. Execute fixes with tests
6. Verify: all tests pass, flake8=0, coverage improved
7. Commit + push
```

## Common Issues Found & Fixed

### P0: Silent Exception Swallowing

**Pattern:** `except Exception: pass` — errors hidden, debugging impossible.

**Locations found:**
- `runtime/tools.py`: Wikipedia API calls (2 places)
- `runtime/config.py`: YAML/env config loading (3 places)
- `interpreter/interpreter.py`: async event loop check (1 place)
- `lsp/server.py`: LSP diagnostics (1 place)

**Fix:** Add `logging.debug()` with context:
```python
# Before:
except Exception:
    pass

# After:
except Exception as e:
    import logging
    logging.debug("Wikipedia API failed for query %r: %s", query, e)
```

### P0: Dead TYPE_CHECKING Blocks

**Pattern:** `if TYPE_CHECKING: pass` — leftover from refactoring, adds noise.

**Locations found (8 total, 3 had actual imports):**
- `core/ast.py`
- `semantic/analyzer.py`
- `interpreter/interpreter.py`
- `semantic/symbols.py`
- `cli/formatter.py`
- `runtime/prompt_builder.py`
- `core/tokens.py`
- `core/errors.py`

**Fix:** Remove empty blocks entirely. Keep blocks with actual imports.

### P0: Expired Comments

**Pattern:** Comments referencing completed phases as if still pending.

**Example:** `# Import & LLM (stubs for Phase 3)` — methods fully implemented.

**Fix:** Remove "(stubs for Phase 3)" qualifier.

### P1: Coverage Gaps

**Low-coverage files discovered:**

| File | Before | After | Strategy |
|------|--------|-------|----------|
| `runtime/config.py` | 20% | 98% | 50 test cases for all config functions |
| `runtime/fuzzy_match.py` | 0% | 90% | 77 test cases covering all 9 strategies |
| `runtime/constants.py` | 0% | 100% | 30 test cases for all constants |
| `runtime/tools.py` | 20% | 80%+ | 61 test cases with mocked HTTP |
| `interpreter/interpreter.py` | 43% | 79% | 126 test cases for visit methods |

**Key insight:** Contract files (`*_contracts.py`) at 0% are expected — they're Protocol definitions tested indirectly through implementations.

### P1: History Truncation Stub

**Pattern:** `pass` placeholder where logging should happen.

**Location:** `runtime/history.py:132`

**Fix:**
```python
# Before:
if truncated > 0:
    # _truncation_count would be stored for logging
    pass

# After:
if truncated > 0:
    import logging
    logging.debug("History truncated: %d messages omitted", truncated)
```

## Coverage Improvement Techniques

### Mocking External APIs

```python
from unittest.mock import patch, MagicMock

def test_wikipedia_api_success(self):
    mock_data = json.dumps({"title": "Python", "extract": "..."}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = json.loads(_web_search("Python"))
        assert "results" in result
```

### Testing File Operations

```python
def test_read_large_file_truncated(self, tmp_path):
    test_file = tmp_path / "large.txt"
    test_file.write_text("x" * 20000, encoding="utf-8")
    result = json.loads(_read_file(str(test_file)))
    assert "[truncated]" in result["content"]
```

### Testing Shell Commands

```python
def test_command_with_stderr(self):
    # Use bash -c for shell redirection, not raw shell=True
    result = json.loads(_shell_exec("bash -c 'echo error >&2'", shell=False))
    assert "[stderr]" in result["output"]
```

## Assessment Results Over Time

| Round | Score | Key Changes |
|-------|-------|-------------|
| 1st | 7.10/10 | Initial assessment, identified 12+ security issues |
| 2nd | 7.45/10 | Security sandbox added, dead code found |
| 3rd | 7.93/10 | All P0/P1/P2 fixed, 344 new tests |

### Metrics Progression

| Metric | Round 1 | Round 3 |
|--------|---------|---------|
| flake8 warnings | 571 | 0 |
| Silent exceptions | 6+ | 0 |
| Dead TYPE_CHECKING | 8 | 0 |
| Test cases | 1,401 | 1,805 |
| Test/source ratio | 0.87 | 1.03 |
| interpreter coverage | 43% | 79% |
| runtime coverage | 47% | ~63% |

## Pitfalls

1. **Coverage tool memory:** Running `pytest --cov` on full test suite can OOM on 1.8GB RAM machines. Run per-module instead.
2. **grep false positives:** `except.*:\s*$` matches both `except Exception:` and `except Exception as e:`. Use `except Exception:\s*$` for silent catches.
3. **TYPE_CHECKING blocks:** Some have actual imports (keep them), some are empty (delete). Check each individually.
4. **Contract files at 0%:** `*_contracts.py` files are Protocol definitions — they're tested indirectly. Don't count them as coverage gaps.
5. **shell=True in tests:** When testing stderr capture, use `bash -c 'cmd >&2'` with `shell=False`, not raw `shell=True`.
