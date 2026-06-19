# Code-to-Design Compliance: 2026-06-01 Session Report

## AST Structure Changes Applied

### 1. ProgramNode: imports/agents/functions/main → statements

**Phase 0 design change**:
```python
# OLD
class ProgramNode:
    imports: list[ImportStmtNode]
    agents: list[AgentDeclNode]
    functions: list[FunctionDeclNode]
    main: MainBlockNode | None

# NEW
class ProgramNode:
    statements: list[ASTNode]
```

**Code fixes applied** (in order):

| Layer | File | Fix |
|-------|------|-----|
| AST | `core/ast.py` | Changed class definition + ASTPrinter.visit_program |
| Parser | `core/parser.py` | parse() collects all declarations into `statements` list. Fixed `_is_at_end()` → `is_at_end()`. Added `SourceSpan` import for empty program fallback. |
| Analyzer | `semantic/analyzer.py` | visit_program: replaced 4 separate loops with `for stmt in node.statements` |
| TypeChecker | `semantic/type_checker.py` | visit_program: same pattern |
| Tests (helpers) | `test_analyzer.py`, `test_var_scope.py`, `test_agent_semantics.py`, `test_control_flow_semantics.py`, `test_type_check.py` | Updated `_program()`, `_empty_program()`, `_program_with_imports()` to use `statements=[...]` |
| Tests (assertions) | All test files | `program.agents[0]` → `program.statements[0]`, `program.main.body` → `program.statements[0].body` (or `program.statements[-1].body`) |

### 2. IfStmtNode/ForStmtNode/WhileStmtNode: body list → MainBlockNode wrapper

**Phase 0 design change**:
```python
# OLD
class IfStmtNode:
    then_branch: list[StatementNode]
    else_branch: list[StatementNode] | None

class ForStmtNode:
    body: list[StatementNode]

# NEW
class IfStmtNode:
    then_branch: MainBlockNode | StatementNode
    else_branch: MainBlockNode | StatementNode | None

class ForStmtNode:
    body: MainBlockNode | StatementNode
```

**Code fixes applied**:

| Layer | File | Fix |
|-------|------|-----|
| AST | `core/ast.py` | Changed field types for IfStmtNode, ForStmtNode, WhileStmtNode, FunctionDeclNode |
| Parser | `core/parser.py` | Wrapped `_block()` results in `MainBlockNode(body=raw, span=...)` for if/while/for/function. Fixed `_previous()` → `previous()`. |
| ASTPrinter | `core/ast.py` | visit_main_block: `*node.body` was correct (MainBlockNode.body IS a list) |
| Tests (control_flow) | `test_control_flow.py` | `stmt.then_branch` → `stmt.then_branch.body`, added `MainBlockNode` import |
| Tests (functions) | `test_functions.py` | `stmt.body` → `stmt.body.body`, `stmt.body == []` → `len(stmt.body.body) == 0` |
| Tests (integration) | `test_integration.py` | `if_stmt.then_branch` → `if_stmt.then_branch.body`, `program.agents` → `program.statements` |

### 3. FunctionDeclNode: body list → MainBlockNode

**Same pattern**: Parser now wraps function body statements in `MainBlockNode(body=..., span=...)`. Tests access via `fn_decl.body.body`.

## Key Lessons

### Lesson 1: Fix Code Before Tests
Always fix the implementation layers (AST → Parser → Visitors) before touching tests. Fixing tests first creates false failures that mask the real issues.

### Lesson 2: `_previous()` vs `previous()` API Inconsistency
The Parser had mixed internal method naming: `_is_at_end()` vs `is_at_end()`, `_previous()` vs `previous()`. The `parse()` method was rewritten to use the public API (`is_at_end()`, `previous()`), not the underscore-prefixed variants that may not exist.

### Lesson 3: Empty Body Span Fallback
When constructing `MainBlockNode` from an empty `_block()` result, there's no first statement to borrow a span from. Use `self.previous().span` as fallback:
```python
body_span = body_stmts[0].span if body_stmts else self.previous().span
body = MainBlockNode(body=body_stmts, span=body_span)
```

### Lesson 4: ASTPrinter `*node.body` Works Correctly
MainBlockNode.body IS a `list[StatementNode]`, so `self._parenthesize("block", *node.body)` in visit_main_block is correct and does NOT need the `.body.body` double-access pattern. Only the test assertions and visitor field access need the double-access.

### Lesson 5: Test Assertion Pattern
The systematic replacement for body access in tests:
- `node.then_branch` → `node.then_branch.body` (for IfStmtNode)
- `node.else_branch` → `node.else_branch.body` (for IfStmtNode, if not None)
- `node.body` → `node.body.body` (for ForStmtNode, WhileStmtNode, FunctionDeclNode)
- `len(node.body)` → `len(node.body.body)`
- `isinstance(node.body[0], X)` → `isinstance(node.body.body[0], X)`
- `node.body == []` → `len(node.body.body) == 0`
