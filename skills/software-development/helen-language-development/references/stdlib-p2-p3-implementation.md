# Stdlib P2+P3 Implementation Patterns

> P2 (System, Crypto) + P3 (Data Formats) implementation lessons from 2026-06-18

## Overview

P2+P3 added 39 functions across 3 modules:
- **System** (16): Environment variables, process management, logging
- **Crypto** (11): Hash functions (MD5, SHA1, SHA256, SHA512, HMAC), random operations
- **Data Formats** (12): YAML, TOML, XML parsing and generation

Total stdlib: 185 functions, 355 tests, 100% pass rate

## Conditional Dependencies Pattern

### Problem
Some data formats (YAML, TOML) require third-party libraries, but stdlib should have zero hard dependencies.

### Solution
Use conditional imports with graceful degradation:

```python
# Try to import YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Try to import TOML support (Python 3.11+ has tomllib)
try:
    import tomllib
    HAS_TOML_READ = True
except ImportError:
    try:
        import toml
        HAS_TOML_READ = True
    except ImportError:
        HAS_TOML_READ = False

def _yaml_parse(text: str) -> Any:
    """Parse YAML string."""
    if not HAS_YAML:
        raise ImportError(
            "PyYAML is required for YAML support. "
            "Install with: pip install pyyaml"
        )
    
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}") from e
```

### Key Points
1. **Check at function entry**, not module load time
2. **Provide clear error message** with install command
3. **Use module-level flags** (`HAS_YAML`, `HAS_TOML_READ`) for conditional logic
4. **Fallback chain**: Try multiple implementations (tomllib → toml)
5. **Document dependencies** in docstrings and error messages

### Testing
```python
def test_yaml_parse_basic(self):
    # Test with dependency installed
    result = _yaml_parse("name: Alice\nage: 30")
    assert result == {"name": "Alice", "age": 30}

def test_yaml_parse_invalid(self):
    with pytest.raises(ValueError):
        _yaml_parse("invalid: yaml: :")
```

## Logging System Integration

### Architecture
Use Python's `logging` module with Helen-specific configuration:

```python
import logging

# Configure logger
_logger = logging.getLogger("helen")
_logger.setLevel(logging.DEBUG)

# Create console handler
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.DEBUG)

# Create formatter
_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_console_handler.setFormatter(_formatter)

# Add handler (avoid duplicates)
if not _logger.handlers:
    _logger.addHandler(_console_handler)

def _log_debug(message: str) -> str:
    """Log debug message."""
    _logger.debug(message)
    return f"[DEBUG] {message}"

def _log_set_level(level: str) -> str:
    """Set logging level."""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    level_upper = level.upper()
    if level_upper not in level_map:
        raise ValueError(
            f"Invalid log level: {level}. "
            f"Must be one of {list(level_map.keys())}"
        )
    
    _logger.setLevel(level_map[level_upper])
    _console_handler.setLevel(level_map[level_upper])
    return f"Log level set to {level_upper}"

def _log_to_file(path: str) -> str:
    """Set log output to file."""
    file_handler = logging.FileHandler(path)
    file_handler.setLevel(_logger.level)
    file_handler.setFormatter(_formatter)
    _logger.addHandler(file_handler)
    return f"Logging to file: {path}"
```

### Key Points
1. **Module-level logger** shared across all log functions
2. **Avoid duplicate handlers** with `if not _logger.handlers` check
3. **Return formatted message** for Helen program inspection
4. **Support multiple outputs** (console + file)
5. **Level mapping** with validation

## Process Management

### Sync vs Async Execution

```python
import subprocess

def _exec(command: str, shell: bool = True, timeout: int | None = None) -> dict[str, Any]:
    """Execute command and wait for result."""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"Command timed out after {timeout}s") from e

def _exec_async(command: str, shell: bool = True) -> int:
    """Execute command asynchronously."""
    process = subprocess.Popen(
        command,
        shell=shell,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return process.pid
```

### Key Points
1. **Sync**: `subprocess.run()` with `capture_output=True`
2. **Async**: `subprocess.Popen()` with output redirected to DEVNULL
3. **Timeout handling**: Catch `subprocess.TimeoutExpired`, raise `TimeoutError`
4. **Return structured result**: Dict with returncode, stdout, stderr
5. **Shell parameter**: Allow both shell and non-shell execution

## XML Dict Representation

### Problem
XML has attributes, text content, and nested elements. Need a dict-based representation.

### Solution
Use special keys for attributes and text:

```python
def _xml_to_dict(element: ET.Element) -> dict[str, Any]:
    """Convert XML element to dict."""
    result: dict[str, Any] = {}
    
    # Attributes: @attribute_name
    if element.attrib:
        for key, value in element.attrib.items():
            result[f"@{key}"] = value
    
    # Children
    children = list(element)
    if children:
        child_dict = {}
        for child in children:
            child_result = _xml_to_dict(child)
            if child.tag in child_dict:
                # Convert to list if multiple elements with same tag
                if not isinstance(child_dict[child.tag], list):
                    child_dict[child.tag] = [child_dict[child.tag]]
                child_dict[child.tag].append(child_result[child.tag])
            else:
                child_dict[child.tag] = child_result[child.tag]
        result.update(child_dict)
    elif element.text and element.text.strip():
        # Text content: #text
        if result:
            result["#text"] = element.text.strip()
        else:
            result = element.text.strip()
    
    return {element.tag: result}

def _dict_to_xml(data: Any, parent: ET.Element | None = None, tag: str = "root") -> ET.Element:
    """Convert dict to XML element."""
    if parent is None:
        element = ET.Element(tag)
    else:
        element = ET.SubElement(parent, tag)
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key.startswith("@"):
                # Attribute
                element.set(key[1:], str(value))
            elif key == "#text":
                # Text content
                element.text = str(value)
            else:
                # Child element
                if isinstance(value, list):
                    for item in value:
                        _dict_to_xml(item, element, key)
                else:
                    _dict_to_xml(value, element, key)
    else:
        element.text = str(data)
    
    return element
```

### Example

```python
# XML:
# <user id="1">
#   <name>Alice</name>
#   <age>30</age>
# </user>

# Dict:
{
    "user": {
        "@id": "1",
        "name": "Alice",
        "age": "30"
    }
}

# Usage:
result = _xml_parse('<user id="1"><name>Alice</name></user>')
# => {"user": {"@id": "1", "name": "Alice"}}

xml_str = _xml_stringify({"@id": "1", "name": "Alice"}, root="user")
# => '<user id="1"><name>Alice</name></user>'
```

### Key Points
1. **@ prefix** for attributes: `@id`, `@class`, etc.
2. **#text** for text content when mixed with attributes/children
3. **List conversion** for multiple elements with same tag
4. **Recursive conversion** for nested structures
5. **Round-trip support**: parse → modify → stringify

## Hash Functions

### Implementation

```python
import hashlib
import hmac

def _md5(text: str) -> str:
    """Calculate MD5 hash."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def _sha256(text: str) -> str:
    """Calculate SHA256 hash."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _hmac_sha256(key: str, message: str) -> str:
    """Calculate HMAC-SHA256."""
    return hmac.new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

def _hash_file(path: str, algorithm: str = "sha256") -> str:
    """Calculate hash of file contents."""
    algorithm_map = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }
    
    if algorithm not in algorithm_map:
        raise ValueError(
            f"Unsupported algorithm: {algorithm}. "
            f"Must be one of {list(algorithm_map.keys())}"
        )
    
    try:
        hasher = algorithm_map[algorithm]()
        with open(path, "rb") as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
```

### Key Points
1. **Encode to UTF-8** before hashing
2. **Return hex digest** (not raw bytes)
3. **Chunked reading** for large files (8KB chunks)
4. **Algorithm validation** with clear error messages
5. **HMAC** for message authentication

## Random Operations

### Implementation

```python
import random

def _random() -> float:
    """Generate random float between 0 and 1."""
    return random.random()

def _randint(min_val: int, max_val: int) -> int:
    """Generate random integer in range."""
    return random.randint(min_val, max_val)

def _choice(items: list[Any]) -> Any:
    """Choose random item from list."""
    if not items:
        raise ValueError("Cannot choose from empty list")
    return random.choice(items)

def _shuffle(items: list[Any]) -> list[Any]:
    """Shuffle list randomly."""
    result = items.copy()  # Don't modify original
    random.shuffle(result)
    return result

def _sample(items: list[Any], k: int) -> list[Any]:
    """Sample k items from list without replacement."""
    if not items:
        raise ValueError("Cannot sample from empty list")
    if k > len(items):
        raise ValueError(
            f"Cannot sample {k} items from list of length {len(items)}"
        )
    return random.sample(items, k)
```

### Key Points
1. **Don't modify original list** in shuffle (return new list)
2. **Validate inputs** (empty lists, k > len)
3. **Clear error messages**
4. **Use Python's random module** (Mersenne Twister)

## Testing Patterns

### File I/O with Temp Directories

```python
def test_save_and_load(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.yaml")
        data = {"name": "Alice", "age": 30}
        
        _yaml_save(path, data)
        loaded = _yaml_load(path)
        
        assert loaded == data
```

### Error Handling

```python
def test_invalid_yaml(self):
    with pytest.raises(ValueError):
        _yaml_parse("invalid: yaml: :")

def test_nonexistent_file(self):
    with pytest.raises(FileNotFoundError):
        _yaml_load("/nonexistent/path.yaml")

def test_invalid_algorithm(self):
    with pytest.raises(ValueError):
        _hash_file("test.txt", "invalid")
```

### Conditional Dependencies

```python
def test_yaml_parse_basic(self):
    # Only runs if PyYAML is installed
    result = _yaml_parse("name: Alice")
    assert result == {"name": "Alice"}
```

## Registration in __init__.py

### Import Pattern

```python
# Import with underscore prefix
from helen.stdlib.system import (
    _env_get, _env_set, _env_list, _env_delete,
    _exec, _exec_async, _pid, _exit, _kill,
    _log_debug, _log_info, _log_warn, _log_error, _log_critical,
    _log_set_level, _log_to_file,
)

from helen.stdlib.crypto import (
    _md5, _sha1, _sha256, _sha512, _hmac_sha256, _hash_file,
    _random, _randint, _choice, _shuffle, _sample,
)

from helen.stdlib.data_formats import (
    _yaml_parse, _yaml_stringify, _yaml_load, _yaml_save,
    _toml_parse, _toml_stringify, _toml_load, _toml_save,
    _xml_parse, _xml_stringify, _xml_load, _xml_save,
)
```

### Registration Pattern

```python
# System environment operations
BuiltinFunction("env_get", "Get environment variable", 
                "env_get(key, default?)", _env_get, "system"),
BuiltinFunction("env_set", "Set environment variable",
                "env_set(key, value)", _env_set, "system"),

# Crypto hash operations
BuiltinFunction("md5", "Calculate MD5 hash",
                "md5(text)", _md5, "crypto"),
BuiltinFunction("sha256", "Calculate SHA256 hash",
                "sha256(text)", _sha256, "crypto"),

# Data formats YAML operations
BuiltinFunction("yaml_parse", "Parse YAML",
                "yaml_parse(text)", _yaml_parse, "data"),
```

### Category Organization
- `system` — Environment, process, logging
- `crypto` — Hash functions, random operations
- `data` — YAML, TOML, XML (extends existing data category)

## Pitfalls

1. **Conditional import scope**: Check `HAS_YAML` at function entry, not module level
2. **Logging handler duplication**: Use `if not _logger.handlers` guard
3. **XML attribute naming**: Use `@` prefix consistently
4. **XML text content**: Use `#text` when mixed with attributes
5. **Shuffle mutation**: Return new list, don't modify original
6. **File hash chunks**: Use 8KB chunks for memory efficiency
7. **TOML version compatibility**: Try `tomllib` (3.11+) then fallback to `toml`
8. **Process timeout**: Catch `subprocess.TimeoutExpired`, not generic `TimeoutError`
9. **HMAC key encoding**: Encode both key and message to UTF-8
10. **Random seed**: Don't set seed in stdlib (let user control randomness)

## Summary

P2+P3 patterns extend stdlib with:
- **System integration** (env vars, processes, logging)
- **Security primitives** (hashing, HMAC, random)
- **Data format diversity** (YAML, TOML, XML)

All follow contract-first + TDD, zero hard dependencies, graceful degradation for optional features.
