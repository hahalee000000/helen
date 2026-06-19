# Security Hardening & Quality Improvements (2026-06-19)

## Overview

Comprehensive P0/P1/P2 quality improvement pass on the Helen codebase.

## P0 — Security Fixes

### New Module: `helen/runtime/security.py`
- `validate_path()` — realpath + blocked dirs (/proc, /sys, /etc/shadow)
- `validate_url()` — scheme whitelist + SSRF check (resolve hostname, block private IPs)
- `validate_command()` — block dangerous patterns (rm -rf /, fork bombs)
- `validate_pid()` — block PID 0/1/self
- `validate_kill_signal()` — whitelist safe signals only
- `safe_env_list()` — mask PASSWORD/SECRET/TOKEN/API_KEY values
- `SecurityError` exception class

### Integration Changes

| File | Change |
|------|--------|
| `runtime/tools.py` | `_web_fetch` → `validate_url()`, `_read_file`/`_write_file`/`_patch_file` → `validate_path()`, `_shell_exec` → `validate_command()` + `shell=False` default |
| `stdlib/system.py` | `_exec`/`_exec_async` → `validate_command()` + `shell=False` default, `_kill` → `validate_pid()` + `validate_kill_signal()`, `_env_list` → `safe_env_list()` |
| `stdlib/network.py` | `_http_request`/`_http_download` → `validate_url()` + download size limit |
| `runtime/import_resolver.py` | `_is_safe_path()` uses `realpath()` (no absolute path bypass) |

### Key Default Changes
- `shell=True` → `shell=False` (tools.py, system.py)
- Uses `shlex.split()` to safely parse command strings when shell=False

## P1 — Code Quality

### flake8: 571 → 0 warnings
- Trailing whitespace: `sed -i 's/[[:space:]]*$//'`
- F401 unused imports: removed ~25 unused imports
- F811 redefinitions: fixed `_reverse` collision in stdlib/__init__.py
- F841 unused variables: removed `result =`, `old_val =`
- E-codes: fixed alignment, blank lines, ambiguous variable names

### Dead Code Removal
- Removed unreachable ASSIGN branch in `visit_binary_op` (interpreter.py)
- Removed empty `_check_llm_usage()` method (analyzer.py)
- Cleaned up `_check_async_usage()` docstring (analyzer.py)

### Code Deduplication
1. **`_type_from_typenode`** → extracted to `semantic/type_utils.py` (shared by analyzer.py and interpreter.py)
2. **`Message` class** → unified in `runtime/history.py` (runtime/__init__.py now imports it)
3. **`bare_form_tokens`** → extracted to `BARE_FORM_TOKENS` module constant in parser.py (3 occurrences → 1)

## P2 — Engineering

### New Files
- `.github/workflows/ci.yml` — CI/CD (lint + test matrix + coverage)
- `tests/runtime/test_security.py` — 30+ security test cases
- `helen/runtime/constants.py` — centralized hardcoded values
- `helen/semantic/type_utils.py` — shared type conversion utility

### Documentation
- Translated all 69 Chinese docstrings in `parser.py` to English

## Commit
- **Hash**: `6886ca0`
- **Files changed**: 44
- **Lines**: +1,471 / -821

## Pitfalls Discovered

1. **GitHub PAT workflow scope**: Pushing `.github/workflows/` files requires PAT with `workflow` scope. If push fails, commit locally and push other changes first.

2. **flake8 E127/E128 alignment**: These are column-sensitive — must read exact line context before fixing. Don't guess the alignment.

3. **`execute_code` timeout**: Using many `patch()` calls in a single `execute_code` script can timeout. Use individual `patch` calls or small `terminal` python scripts instead.

4. **Return type broadening**: When extracting shared utilities, the return type may need to be broadened (e.g., from union of specific subtypes to base `Type`) to satisfy type checkers at all call sites.

5. **Import cleanup cascade**: After extracting shared utilities, the old imports in consumer modules become unused — must clean up F401 warnings after deduplication.

6. **Security changes can break tests**: Always run full test suite after security changes — they can break legitimate use cases (e.g., tests that use absolute paths or shell=True).
