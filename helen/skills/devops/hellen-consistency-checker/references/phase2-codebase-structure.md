# Phase 2: Semantic Analysis — Codebase Structure and Architecture

> Captured after Phase 2 implementation (2026-06-03). Future agents should reference
> this when implementing Phase 3+ to avoid re-discovering file structure, class names,
> and architectural decisions.

## File Layout

```
hellen/
├── core/
│   ├── ast.py          # AST nodes (Phase 0) — 1028 lines, 47 Visitor methods
│   ├── tokens.py       # Token + TokenType (Phase 0)
│   ├── lexer.py        # Scanner (Phase 0)
│   ├── parser.py       # Pratt Parser + recursive descent (Phase 1)
│   ├── source.py       # SourceSpan (Phase 0)
│   └── errors.py       # ErrorCode (300-350), HellenError, ErrorReporter
├── semantic/           # Phase 2
│   ├── __init__.py     # Public re-exports
│   ├── symbols.py      # Symbol, SymbolKind, SymbolTable
│   ├── types.py        # Type hierarchy, type_compatible, type_of_literal
│   └── analyzer.py     # SemanticAnalyzer(Visitor[None])
└── tests/
    ├── core/           # Phase 0/1 tests (ast, tokens, lexer, parser)
    └── semantic/       # Phase 2 tests
        ├── test_symbols.py              # SymbolTable scope management
        ├── test_types.py                # Type system + compatibility
        ├── test_analyzer.py             # Full pipeline (var decl, agent, function)
        ├── test_var_scope.py            # Block scope, const protection
        ├── test_control_flow_semantics.py # break/continue, llm, match, return
        ├── test_agent_semantics.py      # Agent params, import validation
        └── test_type_check.py           # Type annotation assignment checks
```

## Key AST Node Details (from core/ast.py)

### VarDeclNode
```python
VarDeclNode(name, type_annotation: TypeNode|None, initializer: ExprNode|None,
            mutable: bool, span)
# mutable=True → let, mutable=False → const
```

### AgentDeclNode (Phase 0 definition, NO params field)
```python
AgentDeclNode(name: str, prompt: PromptDefNode|None, span)
# Note: AgentDeclNode does NOT have a params field.
# AgentParamNode exists separately but is used by FunctionDeclNode.params.
# Agent parameter validation in Phase 2 uses _check_param_uniqueness helper.
```

### FunctionDeclNode
```python
FunctionDeclNode(name: str, params: list[AgentParamNode],
                 return_type: TypeNode|None, body: FnBlockNode, span)
# params use AgentParamNode (shared with Agent param design)
```

### ProgramNode (refactored from Phase 1)
```python
ProgramNode(statements: list[ASTNode], span)
# NOT: ProgramNode(imports, agents, functions, main) — that was the old design
```

### LlmBranchNode
```python
LlmBranchNode(condition: ExprNode|None, body: list[StmtNode], span)
# condition=None marks the default branch
```

### MatchStmtNode
```python
MatchStmtNode(subject: ExprNode, cases: list[CaseNode],
              default: list[StmtNode], span)
# default=[] means no default (error in semantic analysis)
```

## SymbolTable Architecture

- **Scope types**: `"global"`, `"agent"`, `"function"`, `"block"`
- **Agent boundary**: `resolve()` stops when crossing from agent scope to parent
  agent scope — only global scope is shared between agents
- **Loop tracking**: `_in_loop` flag on SymbolTable instances (set by analyzer
  when entering for/while bodies)
- **Helper methods**: `is_in_loop_scope()`, `is_in_function_scope()`, `depth()`

## Type System (Phase 2 Scope)

### Hierarchy
```
Type (ABC)
├── AnyType
├── BoolType
├── NumberType
│   ├── IntType
│   └── FloatType
├── StringType
├── NullType
├── OptionalType[T]
├── ListType[T]
├── MapType[K, V]
├── UnionType[A, B, ...]
├── LiteralType(value)
└── AgentType(name)
```

### Compatibility Rules (type_compatible)
- `AnyType` ↔ anything (both directions)
- `IntType` → `NumberType` (subtyping)
- `FloatType` → `NumberType` (subtyping)
- `T` → `OptionalType[T]`
- `NullType` → `OptionalType[T]`
- `LiteralType(v)` → check `type_of_literal(v)` against expected
- `T` → `UnionType` if compatible with any member
- `NumberType` ↛ `IntType` (supertype→subtype is UNSAFE)

### Literal Inference (type_of_literal)
- `bool` → `BoolType()` (checked BEFORE int, since `isinstance(True, int)`)
- `int` → `IntType()`
- `float` → `FloatType()`
- `str` → `StringType()`
- `None` → `NullType()`

## Error Code Organization (errors.py)

| Range | Category | Key Codes |
|-------|----------|-----------|
| 300-309 | Lexical/syntax | SCANNER_ERROR, PARSER_ERROR, UNEXPECTED_TOKEN |
| 310-320 | Parser/semantic (Phase 0/1) | TYPE_MISMATCH, UNDEFINED_VARIABLE, DUPLICATE_DECLARATION |
| 330-350 | Semantic analysis (Phase 2) | UNDECLARED_VARIABLE(332), DUPLICATE_SYMBOL(333), SEMANTIC_TYPE_ERROR(331), BREAK_OUTSIDE_LOOP(338), LLM_IF_NO_DEFAULT(344), MATCH_NO_DEFAULT(345), etc. |

## SemanticAnalyzer Pattern

- `SemanticAnalyzer(Visitor[None])` — side-effect-only visitor, collects errors via ErrorReporter
- Two-pass analysis: (1) collect declarations, (2) analyze bodies
- `_type_from_ast(TypeNode|None) → Type|None` converts AST type nodes to semantic types
- `_infer_type(ExpressionNode) → Type|None` — Phase 2: literal-based only
- Predefined exception set: `{"AnyError", "LLMError", "TimeoutError", "ModelError", "ToolError", "RuntimeError"}`

## Pitfalls for Future Phases

1. **AgentDeclNode lacks params**: The current AST definition has AgentDeclNode with only (name, prompt, span). If Phase 3+ needs Agent parameter validation, either add params to AgentDeclNode or handle it separately.

2. **No CallStmtNode**: The parser produces CallNode for function calls. Agent invocation (`call Agent(...)`) may need a dedicated AST node for semantic parameter validation.

3. **Type inference v1 is literal-only**: `_infer_type` only handles LiteralNode and VariableNode (resolved to declared type). BinaryOpNode, CallNode, etc. return None. Future phases need full expression type inference.

4. **Visitor method coverage**: The Visitor ABC has 47 methods. SemanticAnalyzer implements all but some are no-ops (visit_type, visit_optional_type, visit_union_type, visit_literal_type, visit_agent_param). These are placeholders for later phases.

5. **Import path resolution**: Uses `project_root` for relative path checking. Both raw path and `.hellen`-appended path are tried.
