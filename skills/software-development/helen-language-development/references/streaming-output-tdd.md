# Streaming Output Implementation Guide

This document captures the contract-first + TDD workflow used to implement streaming output in Helen (2026-06).

## Workflow: Contract → Test → Implement

When extending Helen with new syntax or capabilities:

### 1. Define Contracts (if applicable)

Create Protocol classes in `helen/<layer>/contracts.py`:

```python
# helen/runtime/stream_contracts.py
from typing import Protocol, runtime_checkable, Iterator

@runtime_checkable
class StreamingLLMRuntime(Protocol):
    def act_stream(self, prompt: str, model: str | None = None,
                   temperature: float = 1.0, system_prompt: str | None = None) -> Iterator[dict]:
        """Stream LLM response chunk by chunk."""
        ...
```

### 2. Write Tests FIRST (RED phase)

Create test files before implementation:
- Parser tests: `tests/parser/test_<feature>.py`
- Execution tests: `tests/execution/test_<feature>.py`
- Integration tests as needed

Example:
```python
# tests/parser/test_llm_stream.py
def test_llm_stream_basic(self):
    source = 'llm stream "Hello"'
    # ... parse and verify LlmStreamStmtNode
```

### 3. Implement to Pass Tests (GREEN phase)

Update ALL layers in this order:

#### Lexer (`helen/core/tokens.py`)
```python
# Add to TokenType enum
STREAM = auto()

# Add to _KEYWORD_MAP
"stream": TokenType.STREAM,

# Update comment: # === Keywords (42 total) ===
```

#### AST (`helen/core/ast.py`)
```python
# Add node class
@dataclass(frozen=True)
class LlmStreamStmtNode(StatementNode):
    prompt: ExpressionNode
    on_chunk: ExpressionNode | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_llm_stream_stmt(self)

# Add abstract method to Visitor class
@abstractmethod
def visit_llm_stream_stmt(self, node: LlmStreamStmtNode) -> R:
    """Visit a LlmStreamStmtNode."""

# Add to ASTPrinter
def visit_llm_stream_stmt(self, node: LlmStreamStmtNode) -> str:
    return self._parenthesize("llm-stream", node.prompt, node.on_chunk)
```

#### Parser (`helen/core/parser.py`)
```python
# Import new AST node
from helen.core.ast import (
    # ...
    LlmStreamStmtNode,
    # ...
)

# Add parsing method
def _llm_stream_stmt(self) -> LlmStreamStmtNode:
    start = self._previous()  # LLM token
    self._consume(TokenType.STREAM, "Expected 'stream' after 'llm'.")
    prompt_expr = self._expression()
    
    on_chunk_expr = None
    if self._check(TokenType.IDENTIFIER) and self._current().lexeme == "on_chunk":
        self._advance()
        on_chunk_expr = self._expression()
    
    return LlmStreamStmtNode(
        prompt=prompt_expr,
        on_chunk=on_chunk_expr,
        span=self._make_span(start, self._previous())
    )

# Update _llm_stmt() to dispatch
def _llm_stmt(self) -> StatementNode:
    self._advance()  # consume LLM
    if self._check(TokenType.IF):
        return self._llm_if_stmt()
    elif self._check(TokenType.ACT):
        return self._llm_act_stmt()
    elif self._check(TokenType.STREAM):
        return self._llm_stream_stmt()
    else:
        self._error("Expected 'if', 'act', or 'stream' after 'llm'.")
```

#### Semantic Analyzer (`helen/semantic/analyzer.py`)
```python
# Import AST node
from helen.core.ast import (
    # ...
    LlmStreamStmtNode,
    # ...
)

# Add visit method
def visit_llm_stream_stmt(self, node: LlmStreamStmtNode) -> None:
    node.prompt.accept(self)
    if node.on_chunk is not None:
        node.on_chunk.accept(self)
```

#### Interpreter (`helen/interpreter/interpreter.py`)
```python
# Import AST node
from helen.core.ast import (
    # ...
    LlmStreamStmtNode,
    # ...
)

# Add visit method
def visit_llm_stream_stmt(self, node: LlmStreamStmtNode) -> object:
    prompt = node.prompt.accept(self)
    if not isinstance(prompt, str):
        prompt = self._stringify(prompt)
    
    # Check if LLM runtime supports streaming
    if not hasattr(self.llm_runtime, 'act_stream'):
        # Fallback to non-streaming
        self.errors.error(
            ErrorCode.RUNTIME_ERROR,
            "LLM runtime does not support streaming. Using fallback.",
            node.span,
        )
        # ... fallback implementation
        return None
    
    # Evaluate callback if provided
    on_chunk_fn = None
    if node.on_chunk is not None:
        on_chunk_fn = node.on_chunk.accept(self)
        if not callable(on_chunk_fn):
            self.errors.error(
                ErrorCode.SEMANTIC_TYPE_ERROR,
                f"on_chunk callback must be callable",
                node.span,
            )
            return None
    
    # Stream response
    try:
        full_response = []
        for chunk in self.llm_runtime.act_stream(prompt, ...):
            if chunk.get('content'):
                full_response.append(chunk['content'])
                if on_chunk_fn is not None:
                    on_chunk_fn(chunk['content'])
                else:
                    # Auto-output using stream_print
                    from helen.stdlib import stdlib
                    stream_print_fn = stdlib.lookup("stream_print")
                    if stream_print_fn:
                        stream_print_fn.fn(chunk['content'])
        
        if on_chunk_fn is None:
            print()  # Add newline at end
        
        return None
    except Exception as e:
        self.errors.error(
            ErrorCode.RUNTIME_ERROR,
            f"Streaming LLM call failed: {e}",
            node.span,
        )
        return None
```

#### Runtime Interface (`helen/runtime/llm_runtime.py`)
```python
from typing import Any, Iterator

class LLMRuntime(ABC):
    # ... existing methods ...
    
    def act_stream(self, prompt: str, model: str | None = None,
                   temperature: float = 1.0, system_prompt: str | None = None) -> Iterator[dict[str, Any]]:
        """Stream LLM response chunk by chunk.
        
        Default implementation calls act() and yields the full response as a single chunk.
        Override for true streaming support.
        """
        response = self.act(prompt, model=model, temperature=temperature, system_prompt=system_prompt)
        if response and response.text:
            yield {"content": response.text}
```

### 4. Update Test Infrastructure

#### MockVisitor (`tests/core/test_ast.py`)
```python
class MockVisitor(Visitor[str]):
    # ... existing methods ...
    
    def visit_llm_stream_stmt(self, node) -> str:
        self.calls.append("visit_llm_stream_stmt")
        return "<llm_stream>"
```

#### Keyword Count (`tests/core/test_tokens.py`)
```python
def test_keyword_count(self) -> None:
    """keywords() should cover all 42 reserved words."""
    kw = keywords()
    assert len(kw) == 42  # Updated from 41
```

## Critical Pitfalls

### Must Update ALL Visitors

When adding a new AST node, you MUST add visit methods to:
1. `ASTPrinter` in `helen/core/ast.py`
2. `SemanticAnalyzer` in `helen/semantic/analyzer.py`
3. `Interpreter` in `helen/interpreter/interpreter.py`
4. `MockVisitor` in `tests/core/test_ast.py`

**Missing any of these causes**: `TypeError: Can't instantiate abstract class with abstract method`

### Import Resolver Path Safety

**Problem**: REPL uses `base_dir="."` but may import absolute paths like `/tmp/file.json`.

**Solution**: `_is_safe_path()` must allow absolute paths while preventing `../` escape:

```python
def _is_safe_path(self, resolved: str) -> bool:
    abs_resolved = os.path.abspath(resolved)
    abs_base = os.path.abspath(self.base_dir)
    
    # Allow absolute paths (for REPL and external imports)
    if os.path.isabs(resolved):
        return True
    
    return abs_resolved.startswith(abs_base + os.sep) or abs_resolved == abs_base
```

### Data File Duplicate Handling

**Problem**: Multiple imports of same data file with different aliases should all register.

**Solution**: Don't use `_imported_paths` for data files:

```python
def visit_import_stmt(self, node: ImportStmtNode) -> None:
    path = node.module_path
    
    # Resolve and validate path
    target = os.path.join(self.base_dir, path)
    if not os.path.exists(target):
        self.errors.error(...)
        return
    
    # Register data files (always, even if duplicate)
    if path.endswith(('.json', '.md', '.txt', '.yaml', '.yml')):
        alias = node.alias if node.alias else os.path.splitext(os.path.basename(path))[0]
        from helen.semantic.symbols import Symbol
        sym = Symbol(alias, kind="import", is_const=False)
        self.symbols.define(alias, sym)
    
    # Track .helen files to avoid duplicate processing
    if path.endswith('.helen'):
        if path in self._imported_paths:
            return
        self._imported_paths.add(path)
```

## Example: Complete Feature Addition

**Feature**: `llm stream` syntax (Phase 2)

**Files Modified**:
1. `helen/core/tokens.py` - Added `STREAM` token
2. `helen/core/ast.py` - Added `LlmStreamStmtNode` + visitor methods
3. `helen/core/parser.py` - Added `_llm_stream_stmt()`
4. `helen/semantic/analyzer.py` - Added `visit_llm_stream_stmt()`
5. `helen/interpreter/interpreter.py` - Added `visit_llm_stream_stmt()`
6. `helen/runtime/llm_runtime.py` - Added `act_stream()`
7. `tests/core/test_ast.py` - Added `visit_llm_stream_stmt()` to MockVisitor
8. `tests/core/test_tokens.py` - Updated keyword count 41 → 42
9. `tests/parser/test_llm_stream.py` - Added 6 new tests

**Result**: 961 tests pass (955 → 961, +6 new tests)

## Streaming Output Layers

### Phase 1: Standard Library Functions
- `stream_print(text)` - Print without newline
- `stream_clear()` - Clear current line
- `progress_bar(current, total, width=40)` - Display progress bar
- `stream_cursor_up(n=1)` / `stream_cursor_down(n=1)` - Cursor movement

**Location**: `helen/stdlib/__init__.py` (io category)
**Tests**: 22 tests in `tests/stdlib/test_stream_output.py`

### Phase 2: `llm stream` Syntax
```helen
llm stream "prompt"                    // Auto-print chunks
llm stream "prompt" on_chunk callback  // Custom callback
```

**Tests**: 6 tests in `tests/parser/test_llm_stream.py`

### Phase 3: Async Iterator Pattern
```python
from helen.runtime.streaming_response import StreamingResponse

response = StreamingResponse(llm_runtime.act_stream(prompt))
async for chunk in response:
    print(chunk)
```

**Location**: `helen/runtime/streaming_response.py`
**Tests**: 5 tests in `tests/runtime/test_streaming_response.py`

**Total**: 33 new tests, 966 tests pass (933 → 966)
