# Method-Level Verification Pattern

> Discovered 2026-06-01 Round 3-4. This is the MOST RELIABLE verification approach for Hellen design doc consistency checks.

## The Problem

Document-level grep (`"node.initializer" in doc`) produces **false positives** because:
- A correct use in `visit_var_decl` masks a wrong use in `visit_return_stmt`
- Structural errors (e.g., `visit_llm_if_stmt` treating `LlmIfStmtNode` as `IfStmtNode`) are invisible at document level
- Boundary detection using `\n\n` often hits docstring ends, not class/method ends

## The Solution: Method-Level Extraction + Assertion

### Core Helper Functions

```python
def get_class_body(doc, name):
    """Extract class body with proper boundary detection."""
    idx = doc.find(f'class {name}')
    if idx == -1:
        return ""
    # Find next structural boundary (NOT just \n\n)
    end = doc.find('\n\n@dataclass', idx + 50)
    if end == -1:
        end = doc.find('\n\n# ', idx + 50)
    if end == -1:
        end = doc.find('\n\nclass ', idx + 50)
    if end == -1:
        end = doc.find('\n\ndef ', idx + 50)
    if end == -1:
        end = min(idx + 1000, len(doc))
    return doc[idx:end]

def get_method_body(doc, name):
    """Extract method body with proper boundary detection."""
    for prefix in ['async def ', 'def ']:
        idx = doc.find(f'{prefix}{name}')
        if idx != -1:
            end = doc.find('\n    def ', idx + len(prefix) + len(name))
            if end == -1:
                end = doc.find('\n    async def ', idx + len(prefix) + len(name))
            if end == -1:
                end = doc.find('\nclass ', idx + 50)
            if end == -1:
                end = min(idx + 3000, len(doc))
            return doc[idx:end]
    return ""

def check_method(doc, method_name, must_have=None, must_not_have=None):
    """Check a method body for required/forbidden patterns."""
    body = get_method_body(doc, method_name)
    if not body:
        return False, f"Method '{method_name}' not found"
    
    issues = []
    if must_have:
        for p in must_have:
            if p not in body:
                issues.append(f"missing '{p}'")
    if must_not_have:
        for p in must_not_have:
            if p in body:
                issues.append(f"FORBIDDEN '{p}'")
    
    return len(issues) == 0, issues
```

### Usage Pattern (Round 4 verification)

```python
# AST Node Class checks
critical_nodes = {
    'VarDeclNode': ['name', 'mutable', 'type_annotation', 'initializer', 'span'],
    'LlmIfStmtNode': ['description', 'branches', 'span'],
    # ...
}
for cls_name, fields in critical_nodes.items():
    body = get_class_body(docs['phase0'], cls_name)
    for field in fields:
        assert field + ':' in body, f"{cls_name} missing '{field}'"

# Parser checks
check_method(docs['p1'], '_var_decl',
    must_have=['initializer=', 'mutable=', 'type_annotation='],
    must_not_have=[])

# Interpreter checks (separate sync/async versions)
check_method(docs['p23'], 'visit_var_decl',
    must_have=['node.initializer'],
    must_not_have=['node.value'])
check_method(docs['p23'], 'visit_llm_if_stmt',
    must_have=['node.description', 'node.branches'],
    must_not_have=['node.then_branch', 'node.prompt'])
```

## Boundary Detection Rules

| Pattern | When to use | Why |
|---------|-------------|-----|
| `\n\n@dataclass` | Class body end | Next dataclass always starts new class |
| `\n\n# ` | Class body end (for sections with comments) | Section headers separate logical blocks |
| `\n\nclass ` | Fallback class boundary | Standard class separator |
| `\n\ndef ` | Fallback for end of file | Method at end of file |
| `\n    def ` | Method body end (4-space indent) | Next method at same indentation |
| `\n    async def ` | Method body end (async) | Next async method |
| `\nclass ` | Method body end (class after method) | Class definition ends method section |

**NEVER use**: `[:500]`, `[:1000]`, or any arbitrary character count as a boundary.

## Completeness Checks

In addition to field-level checks, verify:

1. **All referenced classes exist**: `Visitor.visit_program` references `ProgramNode` → `get_class_body(doc, 'ProgramNode')` must return non-empty
2. **All Visitor interface methods have implementations**: Extract all `def visit_*` from Visitor ABC, verify each exists in P2-3/Remaining
3. **No duplicate method definitions**: `doc.count('def visit_var_decl')` should be ≤ 2 (1 sync + 1 async)

## Why This Beats Document-Level Grep

| Scenario | Document grep | Method-level check |
|----------|--------------|-------------------|
| `visit_var_decl` correct, `visit_return_stmt` wrong with `node.value` | ❌ "node.value in doc" → true, no issue | ✅ `visit_var_decl` passes, `visit_return_stmt` flagged |
| `visit_llm_if_stmt` uses `node.then_branch` (wrong AST) | ❌ "node.then_branch in doc" → true (from `visit_if_stmt`) | ✅ `visit_llm_if_stmt` body doesn't contain `node.branches` |
| Class definition missing entirely | ❌ Can't detect absence with grep | ✅ `get_class_body` returns empty string |
| Duplicate method stub | ❌ Grep finds at least one | ✅ `count() > 2` catches duplicates |
