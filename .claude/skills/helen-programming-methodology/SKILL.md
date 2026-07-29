---
name: helen-programming-methodology
description: "Helen Programming Methodology — complete workflow for contract-first development, TDD, quality assessment, and skill self-evolution"
version: 1.0.0
author: Helen Team
license: MIT
metadata:
  hermes:
    tags: [helen, methodology, contract-first, tdd, quality, skill-evolution, workflow]
---

# Helen Programming Methodology

This skill describes the programming methodology for the Helen language, using a four-stage closed loop: Contract Design → TDD Development → Quality Assessment → Skill Evaluation.

## Core Principles

### 1. Contract-First

Before writing any implementation code, design the interface contract first:

```helen
// contracts/my_module.helen

protocol MyModule {
    fn process_data(input: str): map
    fn validate_config(config: map): bool
}

// Error code definitions
const ERROR_INVALID_INPUT = 1001
const ERROR_CONFIG_MISSING = 1002
const ERROR_PROCESSING_FAILED = 1003

// Helper functions
fn is_valid_input(input: str): bool {
    return len(input) > 0 && len(input) < 1000
}
```

**A contract includes**:
- Protocol definitions (interface signatures)
- Error code constants
- Helper functions (pure functions, no side effects)
- Input/output types for each function

### 2. TDD Development (RED-GREEN-REFACTOR)

Strictly follow the three-stage cycle:

**RED Phase**: Write failing tests

```helen
// tests/test_my_module.helen

import "contracts/my_module.helen"

fn test_process_data_valid_input() {
    let result = process_data("valid input")
    assert_equal(result["status"], "success")
}

fn test_process_data_empty_input() {
    let result = process_data("")
    assert_equal(result["error_code"], ERROR_INVALID_INPUT)
}

fn test_validate_config_missing_field() {
    let config = {"name": "test"}  // missing required_field
    let result = validate_config(config)
    assert_equal(result, false)
}
```

Run the tests and confirm they all FAIL.

**GREEN Phase**: Write the minimal implementation

```helen
// src/my_module.helen

import "contracts/my_module.helen"

fn process_data(input: str): map {
    if !is_valid_input(input) {
        return {
            "status": "error",
            "error_code": ERROR_INVALID_INPUT,
            "message": "Invalid input length"
        }
    }

    // Minimal implementation: just make the tests pass
    return {
        "status": "success",
        "data": input
    }
}

fn validate_config(config: map): bool {
    if !contains(config, "required_field") {
        return false
    }
    return true
}
```

Run the tests and confirm they progressively PASS.

**REFACTOR Phase**: Refactor the code

```helen
// Extract duplicated logic
fn process_data(input: str): map {
    if !is_valid_input(input) {
        return create_error(ERROR_INVALID_INPUT, "Invalid input length")
    }

    return create_success(input)
}

// Helper functions
fn create_error(code: int, message: str): map {
    return {
        "status": "error",
        "error_code": code,
        "message": message
    }
}

fn create_success(data: any): map {
    return {
        "status": "success",
        "data": data
    }
}
```

Run the tests and confirm they all PASS.

### 3. Quality Assessment (7-Dimension Scoring)

After each development cycle, perform a 7-dimension quality assessment:

```helen
// Invoke quality assessment
main {
    let file_path = "src/my_module.helen"
    let quality = get_quality_scores(file_path)

    // Check results
    if quality["scores"]["overall"] < 7.5 {
        print("⚠️ Quality score below threshold, improvement needed")
        print("Security: " + str(quality["scores"]["security"]))
        print("Correctness: " + str(quality["scores"]["correctness"]))
        print("Maintainability: " + str(quality["scores"]["maintainability"]))
        // ... other dimensions
    }
}
```

**7 Dimensions**:
1. **Security** - Input validation, error handling, no hardcoded secrets
2. **Correctness** - Logic correctness, boundary handling, error code coverage
3. **Maintainability** - Code clarity, naming conventions, no duplication
4. **Performance** - No unnecessary loops, reasonable algorithmic complexity
5. **Testability** - Easy to unit test, no side effects
6. **Documentation Completeness** - Sufficient comments, clear interface descriptions
7. **Helen Conformance** - Follows Helen syntax and best practices

**Thresholds**:
- Overall score < 7.5 → Improvement needed
- Any single dimension < 6.0 → Mandatory improvement

### 4. Skill Evaluation (Skill Evolution)

After each task, evaluate whether new skills have been discovered or existing skills need updating.

**When to create a new skill:**
- Discovered a reusable pattern (appears 3+ times)
- Found a common pitfall worth documenting
- Developed a best practice for a specific domain

**Where to save skills:**
- **Project-specific**: `.helen/skills/<skill-name>/SKILL.md` (highest priority, project-scoped)
- **User-global**: `~/.helen/skills/<skill-name>/SKILL.md` (user-scoped, available to all projects)
- **Never** in Helen installation directory (will be lost on update, requires write permissions)

**Creating a new skill:**

```helen
// Evaluate task for reusable patterns
fn create_skill_from_pattern(task_summary: str) {
    // Check if this warrants a new skill
    if is_reusable_pattern(task_summary) {
        let skill_name = "jwt-refresh-pattern"
        let skill_dir = ".helen/skills/" + skill_name
        
        // Create skill directory
        shell_exec("mkdir -p " + skill_dir)
        
        // Create SKILL.md with proper YAML frontmatter
        let skill_content = """---
name: """ + skill_name + """
description: "JWT token refresh pattern for long-running agent sessions"
version: 1.0.0
author: HelenAgent
tags: [jwt, authentication, session-management]
---

// JWT Refresh Pattern

//# Problem
Access tokens expire during long-running agent sessions, causing API failures.

//# Solution
Implement proactive token refresh 5 minutes before expiration.

//# Code Example
```helen
fn refresh_token_if_needed(token: str): str {
    if is_expiring_soon(token) {
        return call_refresh_api(token)
    }
    return token
}
```
"""
        
        write_file(skill_dir + "/SKILL.md", skill_content)
        print("✅ Created skill: " + skill_name)
    }
}
```

**Updating an existing skill:**

```helen
// Read existing skill
fn update_skill() {
    let skill_path = ".helen/skills/jwt-refresh-pattern/SKILL.md"
    let existing = read_file(skill_path)

    // Append new information
    let addition = """

//# Update (2026-07-25)
Discovered edge case: refresh fails when network is down.
Solution: Implement retry with exponential backoff.

```helen
fn refresh_with_retry(token: str, max_retries: int = 3): str {
    for i in range(max_retries) {
        try {
            return call_refresh_api(token)
        } catch NetworkError {
            sleep(2 ** i)  // Exponential backoff
        }
    }
    throw RuntimeError("Token refresh failed after " + str(max_retries) + " retries")
}
```
"""

    write_file(skill_path, existing + addition)
    print("✅ Updated skill: jwt-refresh-pattern")
}
```

**Skill creation checklist:**
- ✅ Directory name: kebab-case, descriptive (e.g., `jwt-refresh-pattern`)
- ✅ SKILL.md: YAML frontmatter with `name`, `description`, `version`, `author`, `tags`
- ✅ Content: Clear problem statement, solution, code examples
- ✅ Location: `.helen/skills/` (project) or `~/.helen/skills/` (user)
- ❌ **Never** in Helen installation directory

### 5. Context Handoff

Helen transcripts are **isolated by Interpreter instance** (spawn creates a new Interpreter → new session_id), so any cross-agent or cross-process context passing must be **explicitly programmed** — this is a core manifestation of Helen's "explicit over implicit" philosophy.

Core mantra: **"spawn means isolation, handoff must be explicit, debug with tracing, recover with --session"**

> 💡 For the complete context handoff pattern (spawn parameter passing, SharedStore, --session recovery, automatic tracing), see the **helen-agent-collaboration** skill.

## Complete Workflow Example

Four-stage closed-loop example (using a JWT authentication module):

```helen
// Phase 1: Contract Design
// Phase 2 RED-GREEN: TDD Development
// Phase 3: Quality Assessment
// Phase 4: Skill Evaluation
main {
    let contract = call_contractor("Implement user authentication module", "JWT support required")

    let tests = call_test_builder("", contract)
    write_file("tests/test_auth.helen", tests)
    let impl = call_implementer("", tests, contract)
    write_file("src/auth.helen", impl)

    let quality = call_quality_gate("src/auth.helen")
    if quality["verdict"] == "NEEDS_IMPROVEMENT" {
        // Go back to Phase 2 for improvement
    }

    let skills = call_skill_evaluator("Implemented JWT authentication", "src/auth.helen, tests/test_auth.helen")
}
```

## Helen Syntax Notes

### 1. Logical Operators

```helen
main {
    // ✅ Correct
    if a && b { }
    if a || b { }
    if !a { }

    // ❌ Wrong
    if a and b { }
    if a or b { }
    if not a { }
}
```

### 2. String Slicing

```helen
main {
    // ✅ Correct
    let sub = substring(str, 0, 10)

    // ❌ Wrong
    let sub = str[0:10]
}
```

### 3. Agent Invocation

```helen
// ✅ Correct (function-style call)
fn call_my_agent(param: str): str {
    return MyAgent(param)
}

// ❌ Wrong (using call keyword)
fn call_my_agent(param: str): str {
    return call MyAgent(param)  // Parse error: Expected expression, got CALL
}

// ❌ Wrong (cannot call directly in prompt)
// Writing "MyAgent()" in a prompt will cause an error
```

**Important**: In Helen, agents are first-class citizens and should be called like functions. The `call` keyword causes a parse error in expression position (assignment, argument, return value) and is only valid in statement position (when the return value is not captured).

### 4. Function Return Values

```helen
// ✅ Correct
fn process(): map {
    return {"status": "success", "data": result}
}

// ❌ Wrong (Helen does not support implicit return)
fn process(): map {
    {"status": "success", "data": result}
}
```

### 5. Testing Framework

```helen
main {
    // ✅ Correct
    test_suite("MyModule", fn() {
        test_case("valid input", fn() {
            assert_equal(result, expected)
        })
    })

    // ❌ Wrong (cannot use string as function name)
    test_case("valid input", "test_function")
}
```

## Quality Improvement Suggestions

**Security**: Input validation + parameterized queries (avoid SQL injection), prohibit hardcoded secrets.

**Maintainability**: Extract duplicated logic into shared functions, avoid repeating error handling code in multiple places.

```helen
// ❌ Duplicated logic scattered across multiple places
fn process_a(input: str): map {
    if len(input) == 0 { return {"status": "error", "code": 1001} }
    // ...
}

// ✅ Extract shared validation function
fn validate_input(input: str): map {
    if len(input) == 0 { return create_error(1001, "Empty input") }
    return create_success(input)
}
```

## Skill Self-Evolution Examples

After each task, evaluate whether new skills have been discovered or existing skills need updating:

**Scenario 1: New pitfall discovered** → Create a new skill
```helen
main {
    let task_summary = "Recursive fibonacci n>30 causes stack overflow, switched to iterative implementation"
    let evaluation = call_skill_evaluator(task_summary, "src/math.helen")
    // Suggest creating "recursion-stack-overflow" skill
}
```

**Scenario 2: Update existing skill** → Supplement documentation
```helen
main {
    let task_summary = "Discovered helen-testing does not explain that mock objects must be defined outside test_suite"
    let evaluation = call_skill_evaluator(task_summary, "tests/test_api.helen")
    // Suggest updating helen-testing skill documentation
}
```

---

## Cache Management in the Development Workflow

When developing, be aware of ImportResolver caching behavior: the CLI automatically reloads on each new process, while long-running processes like the REPL and web services cache loaded modules. Prefer the CLI during development; in the REPL, use `:reset` to reset after modifying files.

> 💡 For cache management during development (REPL/web service pitfalls, Python integration, debugging tools), see the **helen-language-development** skill § ImportResolver Caching Mechanism.

---

## Reference Resources

- [Helen Syntax Reference](./helen-syntax/SKILL.md)
- [Helen Standard Library](./helen-stdlib/SKILL.md)
- [TDD Workflow](./test-driven-development/SKILL.md)
- [Code Quality Assessment](./code-quality/SKILL.md)

## Related Skills

- **helen-agent-patterns** — Agent design patterns
- **helen-agent-collaboration** — Multi-agent collaboration patterns
- **helen-testing** — Testing framework usage guide
- **helen-quality** — Code quality assessment
