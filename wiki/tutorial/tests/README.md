# Tutorial Test System

This directory contains automatically generated test files extracted from the Helen tutorial documentation. These tests verify both the Helen language implementation and the tutorial correctness.

## Overview

The test system extracts `helen` code blocks from `wiki/tutorial/*.md` files and generates `.helen` test files that can be validated using `helen check` (syntax + semantic analysis).

**Statistics:**
- 235 code blocks extracted from 17 tutorial files
- 98 tests pass
- 10 tests correctly fail (intentional error examples)
- 107 tests fail (tutorial issues or missing context)
- 19 tests skipped (require external files/Python modules)
- 1 unexpected pass (should fail but passes)

## Files

### Generator
- **`generate_tests.py`** — Extracts code blocks from tutorial markdown and generates test files
- **`run_tests.sh`** — Runs `helen check` on all generated tests and reports results

### Test Structure
```
tests/
├── 01-getting-started/
│   ├── block_001_01_getting_started.helen
│   ├── block_002_01_getting_started.helen
│   └── ...
├── 02-variables-and-types/
│   ├── block_001_02_variables_and_types.helen
│   ├── block_007_02_variables_and_types.helen  # @should_fail
│   └── ...
└── ...
```

Each generated `.helen` file contains:
- Header comment linking to source (file:line)
- `@should_fail` marker for intentional error examples
- `@skip: <reason>` for tests requiring external resources
- Preceding context (agent/fn declarations) auto-prepended for fragments

## Usage

### Generate Tests
```bash
python wiki/tutorial/generate_tests.py
```

This extracts all `helen` code blocks from tutorial files and generates test files in `wiki/tutorial/tests/`.

### Run Tests
```bash
bash wiki/tutorial/run_tests.sh
```

This runs `helen check` on each test file and reports:
- **OK** — Test passes (syntax + semantics valid)
- **SHOULD_FAIL** — Error example that correctly fails
- **FAIL** — Test fails (tutorial or implementation issue)
- **UNEXPECTED_OK** — Error example that should fail but passes
- **SKIP** — Test requires external resources

## Classification Logic

The generator classifies each code block:

| Condition | Type | Action |
|-----------|------|--------|
| Contains ❌ markers or `// Error:` | `error` | Generate with `@should_fail` |
| Has `main {}` or only declarations | `complete` | Generate as-is |
| Contains `import "./..."` | `skip` | Skip — needs external files |
| Contains Python FFI imports | `skip` | Skip — needs Python modules |
| Other | `fragment` | Prepend context from preceding blocks |

## Known Tutorial Issues

The test system has identified several tutorial issues that need fixing:

### 1. Return Type Syntax Errors
Multiple tutorials use `->` for return type annotation, but Helen uses `:` syntax:

**Wrong (tutorial):**
```helen
fn greet(name: string) -> string {
    return "Hello, " + name + "!"
}
```

**Correct (Helen syntax):**
```helen
fn greet(name: string): string {
    return "Hello, " + name + "!"
}
```

**Affected files:** `01-getting-started.md`, `03-functions.md`, and others

### 2. Undefined Variables/Functions
Many fragments reference functions or variables not defined in the block:
- `expensiveFunction()`, `getUser()`, `isValid()`, `processData()` in `04-control-flow.md`
- `fix_code()` in `11-building-agents.md` and `14-observability.md`
- `stream_print()` in `07-spawn.md`

These are either:
- Intentional placeholders (tutorial examples)
- Missing context from preceding blocks
- Functions that should be defined but aren't shown

### 3. Duplicate Declarations
Context accumulation causes duplicate variable declarations when blocks redefine the same variable:
```helen
// Context from block 1
let a = [1, 2]
let b = [3, 4]

// Block 2 code
let a = [5, 6]  // Error: duplicate declaration
```

### 4. Syntax Templates
Some blocks show syntax templates rather than runnable code:
```helen
alias <canonical> as <alias_name>
```

These should be marked as non-runnable examples.

### 5. Type Checking Gaps
The tutorial claims `add(1.5, 2)` should fail with type mismatch, but Helen's semantic analyzer doesn't enforce strict type checking at compile time. This passes `helen check` when it "should fail" according to the tutorial.

## Test Results Summary

**Pass Rate:** 98/235 (41.7%)

**Breakdown by Tutorial File:**
- `01-getting-started.md`: 3/5 pass (2 fail — syntax errors)
- `02-variables-and-types.md`: 14/22 pass (4 should_fail, 4 fail)
- `03-functions.md`: 11/20 pass (4 should_fail, 4 fail, 1 unexpected_ok)
- `04-control-flow.md`: 2/24 pass (1 should_fail, 21 fail — many undefined refs)
- `05-agents.md`: 10/25 pass (15 fail — undefined refs)
- `06-llm-statements.md`: 8/14 pass (6 fail)
- `07-spawn.md`: 6/16 pass (10 fail)
- `08-modules.md`: 1/9 pass (1 should_fail, 7 fail — all imports)
- `09-python-ffi.md`: 1/12 pass (11 skip — all Python FFI)
- `10-stdlib.md`: 28/42 pass (14 fail)
- `11-building-agents.md`: 3/6 pass (1 should_fail, 2 fail)
- `12-testing.md`: 6/8 pass (2 fail)
- `13-skills.md`: 2/2 pass
- `14-observability.md`: 3/6 pass (3 fail)
- `15-python-bridge.md`: 1/1 pass
- `16-quality-assessment.md`: 1/1 pass
- `17-multimodal.md`: 10/22 pass (12 fail)

## Improving Test Coverage

To improve test pass rates:

1. **Fix tutorial syntax errors** — Update `->` to `:` for return types
2. **Add missing definitions** — Define placeholder functions or mark as intentional
3. **Improve context handling** — Generator could detect variable redefinitions
4. **Mark syntax templates** — Add `@skip: syntax template` to non-runnable examples
5. **Create stub files** — Generate stub files for import examples

## Architecture

### Generator (`generate_tests.py`)
- Parses markdown to extract `helen` code blocks
- Classifies blocks (complete/fragment/error/skip)
- Accumulates context (agent/fn declarations) per file
- Generates `.helen` test files with metadata

### Runner (`run_tests.sh`)
- Iterates over generated test files
- Runs `helen check` on each
- Interprets results based on `@should_fail` / `@skip` markers
- Reports summary statistics

## Future Enhancements

1. **Execution testing** — Run tests with `helen` (not just `helen check`) to verify runtime behavior
2. **Expected output validation** — Compare actual output with tutorial-claimed output
3. **Incremental context** — Better handling of cross-block dependencies
4. **Import stubs** — Generate stub files for import examples
5. **Tutorial auto-fix** — Generate patches for tutorial syntax errors

## Maintenance

When tutorial files are updated:
1. Re-run `python wiki/tutorial/generate_tests.py`
2. Re-run `bash wiki/tutorial/run_tests.sh`
3. Review new failures or changes in pass/fail status
4. Fix tutorial issues or update generator logic as needed

## Contact

For questions about the test system, see the Helen project documentation or open an issue in the repository.
