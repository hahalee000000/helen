# Coverage Improvement Patterns

Concrete techniques from improving Helen language test coverage (2026-06-19).

## Per-Module Coverage Diagnosis

```bash
# Find uncovered lines in a specific module
pytest tests/<module>/ --cov=helen.<module> --cov-report=term-missing -q

# Example output:
# Name                           Stmts   Miss  Cover   Missing
# ------------------------------------------------------------
# helen/runtime/security.py         92      6    93%   86, 156-163
# ------------------------------------------------------------
```

## Mocking Network/Security Code

### Pattern 1: Mock DNS Resolution for SSRF Tests

```python
from unittest.mock import patch
import socket
import pytest
from helen.runtime.security import validate_url, SecurityError

def test_blocks_private_ip_10():
    """Private IP range 10.0.0.0/8 is blocked."""
    with patch('socket.getaddrinfo') as mock_getaddrinfo:
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('10.0.0.1', 0))
        ]
        with pytest.raises(SecurityError, match="private|reserved"):
            validate_url("http://private.example.com")

def test_blocks_private_ip_172():
    """Private IP range 172.16.0.0/12 is blocked."""
    with patch('socket.getaddrinfo') as mock_getaddrinfo:
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('172.16.0.1', 0))
        ]
        with pytest.raises(SecurityError, match="private|reserved"):
            validate_url("http://internal.example.com")

def test_blocks_private_ip_192():
    """Private IP range 192.168.0.0/16 is blocked."""
    with patch('socket.getaddrinfo') as mock_getaddrinfo:
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('192.168.1.1', 0))
        ]
        with pytest.raises(SecurityError, match="private|reserved"):
            validate_url("http://local.example.com")
```

### Pattern 2: Mock DNS Failure

```python
def test_blocks_unresolvable_hostname():
    """Unresolvable hostnames raise SecurityError."""
    with patch('socket.getaddrinfo') as mock_getaddrinfo:
        mock_getaddrinfo.side_effect = socket.gaierror("Name resolution failed")
        with pytest.raises(SecurityError, match="Cannot resolve"):
            validate_url("http://nonexistent.example.com")
```

### Pattern 3: Test Exception Handling Branches

```python
def test_handles_invalid_ip_gracefully():
    """Invalid IP addresses from DNS are handled gracefully."""
    with patch('socket.getaddrinfo') as mock_getaddrinfo:
        # Return an invalid IP string that will cause ValueError in ipaddress.ip_address()
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('not-a-valid-ip', 0))
        ]
        # Should not raise an error, just skip the invalid IP
        result = validate_url("http://example.com")
        assert result == "http://example.com"
```

## Testing Extracted Utility Modules

When you extract shared code into a utility module (e.g., `type_utils.py`), create a dedicated test file:

```python
# tests/semantic/test_type_utils.py
from helen.core.ast import TypeNode, OptionalTypeNode, UnionTypeNode
from helen.core.source import SourceSpan
from helen.semantic.type_utils import type_from_typenode
from helen.semantic.types import IntType, StringType, OptionalType, UnionType

def make_span():
    """Helper to create dummy SourceSpan for testing."""
    return SourceSpan(file="test.helen", start_line=1, start_col=1,
                      end_line=1, end_col=10)

class TestTypeFromTypenode:
    def test_int_type(self):
        node = TypeNode(name="int", span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, IntType)

    def test_optional_type(self):
        inner = TypeNode(name="int", span=make_span())
        node = OptionalTypeNode(inner=inner, span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, OptionalType)
        assert isinstance(result.inner, IntType)

    def test_union_type(self):
        members = [
            TypeNode(name="int", span=make_span()),
            TypeNode(name="str", span=make_span()),
        ]
        node = UnionTypeNode(members=members, span=make_span())
        result = type_from_typenode(node)
        assert isinstance(result, UnionType)
        assert len(result.members) == 2  # Note: attribute is 'members', not 'types'
```

## Common Pitfalls

### SourceSpan Construction
- `SourceSpan` requires 5 arguments: `(file, start_line, start_col, end_line, end_col)`
- Use a helper function `make_span()` to avoid repetition

### Type System Attributes
- `UnionType` stores types in `members` list, NOT `types`
- `LiteralTypeNode.values` expects `list[ExpressionNode]`, not `list[int]`
- Wrap literal values in `LiteralNode`: `LiteralNode(value=1, span=make_span())`

### Coverage Tool Issues
- `pytest --cov` with full test suite can OOM on memory-constrained machines (1.8GB RAM)
- Run per-module coverage instead: `pytest tests/<module>/ --cov=helen.<module>`
- `coverage run -m pytest` may not produce `.coverage` file if process is killed
- Use `pytest --cov` (integrated) instead of separate `coverage` command
- **Output parsing pitfall**: `pytest --cov` output format varies. Don't rely on grep patterns like `grep -E "^(helen/runtime|TOTAL)"` — they often fail. Use `tail -N` or redirect to file:
  ```bash
  # ✅ Reliable
  pytest --cov=helen.runtime tests/runtime/ -q | tail -15
  
  # ❌ Unreliable
  pytest --cov=helen.runtime tests/runtime/ | grep -E "^(helen/runtime|TOTAL)"
  ```

## Tool Testing Patterns

### Mocking HTTP Calls (urllib)
```python
from unittest.mock import patch, MagicMock
import json

def test_web_fetch_success():
    """Mock urllib.request.urlopen for HTTP testing."""
    html_content = b"<html><body><p>Hello</p></body></html>"
    mock_resp = MagicMock()
    mock_resp.read.return_value = html_content
    mock_resp.__enter__ = lambda s: s  # Support context manager
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = json.loads(_web_fetch("https://example.com"))
        assert "content" in result
        assert "Hello" in result["content"]

def test_web_fetch_network_error():
    """Test error handling when network fails."""
    with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
        result = json.loads(_web_fetch("https://example.com"))
        assert "error" in result
```

### Using tmp_path for File Operations
```python
def test_read_file(tmp_path):
    """tmp_path provides a temporary directory unique to each test."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")
    result = json.loads(_read_file(str(test_file)))
    assert result["content"] == "hello world"

def test_write_file_creates_dirs(tmp_path):
    """tmp_path supports nested directory creation."""
    test_file = tmp_path / "sub" / "dir" / "file.txt"
    result = json.loads(_write_file(str(test_file), "nested"))
    assert result["status"] == "ok"
    assert test_file.read_text() == "nested"
```

### Using monkeypatch for Config/Environment
```python
def test_load_skill_not_found(tmp_path, monkeypatch):
    """monkeypatch replaces functions/attributes for test isolation."""
    monkeypatch.setattr("helen.runtime.config.get_skill_dirs", lambda: [tmp_path])
    result = json.loads(_load_skill("nonexistent_skill"))
    assert "error" in result
    assert "not found" in result["error"].lower()
```

### Testing Shell Commands with stderr
```python
def test_shell_exec_stderr():
    """Shell redirection (>&2) requires bash -c wrapper."""
    # ❌ Doesn't work: shlex.split breaks the redirection
    result = json.loads(_shell_exec("echo error >&2"))
    assert "[stderr]" not in result["output"]  # Fails!
    
    # ✅ Works: use bash -c with shell=False
    result = json.loads(_shell_exec("bash -c 'echo error >&2'", shell=False))
    assert "[stderr]" in result["output"]
```

### Testing Large File Truncation
```python
def test_read_large_file_truncated(tmp_path):
    """Files exceeding size limit are truncated with marker."""
    test_file = tmp_path / "large.txt"
    test_file.write_text("x" * 20000, encoding="utf-8")
    result = json.loads(_read_file(str(test_file)))
    assert "[truncated]" in result["content"]
    # Allow some margin for truncation marker length
    assert len(result["content"]) <= 16020  # 16000 + marker
```

### Mixin Coverage Gap
When you extract code into a mixin class, existing tests exercise it through the host class (e.g., `Interpreter`), not directly. This yields low coverage numbers (30-40%) even though the code IS tested.

**Solutions:**
1. Accept indirect coverage if integration tests are comprehensive
2. Add direct unit tests for the mixin (preferred for shared utilities)
3. Use `# pragma: no cover` on thin delegation methods
4. Adjust `--cov-fail-under` threshold or exclude the module

## Coverage Targets

| Module Type | Target | Rationale |
|-------------|--------|-----------|
| Security-critical (security.py) | 100% | Every branch must be tested |
| Shared utilities (type_utils.py) | 100% | Used by multiple callers |
| Core interpreter logic | 80%+ | Critical path, high confidence |
| LLM integration (llm_mixin.py) | 60%+ | Hard to test without real LLM |
| CLI/tools | 70%+ | User-facing, important |

## Verification

After improving coverage, verify with:

```bash
# Check specific module
pytest tests/runtime/test_security.py --cov=helen.runtime.security --cov-report=term-missing -v

# Expected output:
# Name                        Stmts   Miss  Cover   Missing
# ---------------------------------------------------------
# helen/runtime/security.py      92      0   100%
# ---------------------------------------------------------
```
