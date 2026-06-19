# Code-to-Design Compliance Checking

## Overview

After design documents are updated, the **implementation code must be re-checked against the design**. Design-doc-vs-design-doc consistency is only half the battle; code-vs-design is equally critical.

## Key Lesson: AST Structure Changes Have Massive Blast Radius

A single AST node field change cascades through:
1. **AST definition** (`core/ast.py`) — the source of truth
2. **Parser** (`core/parser.py`) — creates AST nodes with specific constructor args
3. **Semantic Analyzer** (`semantic/analyzer.py`) — visits AST and accesses fields
4. **Type Checker** (`semantic/type_checker.py`) — visits AST and accesses fields
5. **Interpreter** (`runtime/interpreter.py`) — visits AST and accesses fields
6. **ASTPrinter** (`core/ast.py`) — serializes AST to string
7. **All test files** — construct AST nodes directly in tests

### Case Study: ProgramNode Refactoring

**Change**: `ProgramNode(imports, agents, functions, main)` → `ProgramNode(statements: list[ASTNode])`

**Blast radius**: 50+ test failures across 10+ files:
- `core/ast.py`: Class definition + ASTPrinter.visit_program
- `core/parser.py`: parse() method
- `semantic/analyzer.py`: visit_program
- `semantic/type_checker.py`: visit_program
- `tests/core/test_ast.py`: 5 test methods
- `tests/parser/test_*.py`: 10+ integration tests
- `tests/semantic/test_*.py`: 20+ semantic tests

**Fix strategy**:
1. Fix AST definition first (source of truth)
2. Fix Parser creation logic
3. Fix all visitor methods (Analyzer, TypeChecker, Interpreter, ASTPrinter)
4. Fix test helper functions (`_program()`, `_empty_program()`)
5. Fix individual test assertions (`len(node.then_branch)` → `len(node.then_branch.body)`)
6. Run full test suite, iterate on remaining failures

## Checklist: After AST Design Change

1. [ ] Update `core/ast.py` class definitions
2. [ ] Update Parser methods that create the changed nodes
3. [ ] Update ALL visitor methods that access the changed fields:
   - Semantic Analyzer visitors
   - Type Checker visitors
   - Interpreter visitors
   - ASTPrinter visitors
4. [ ] Update test helper functions that construct the changed nodes
5. [ ] Update individual test assertions
6. [ ] Run `pytest` — expect cascading failures, fix iteratively

## Method Extraction for Code Verification

When checking code against design, use the same `get_method_body` / `get_class_body` pattern as for design documents:

```python
def get_class_body(code, name):
    """Extract full class body — NOT using \\n\\n boundary."""
    pattern = rf'^class {name}\(.*?\):'
    match = re.search(pattern, code, re.MULTILINE)
    if not match: return ""
    start = match.start()
    # Find next top-level class or def (not inside the class)
    next_def = re.search(r'\n^class |^\nclass |^def ', code[start+10:], re.MULTILINE)
    end = start + 10 + next_def.start() if next_def else len(code)
    return code[start:end]
```

## Common Pitfalls

- **Don't fix tests before code**: Fix AST definition → Parser → Visitors → Tests. If you fix tests first, they'll fail for the wrong reasons.
- **pytest --tb=short is essential**: With 50+ failures, short tracebacks let you categorize quickly.
- **Import errors first**: If tests can't import a module, fix the import before worrying about assertion failures.
- **Check both sync and async visitors**: Python files often have both `def visit_*` (analyzer) and `async def visit_*` (interpreter) for the same node.
