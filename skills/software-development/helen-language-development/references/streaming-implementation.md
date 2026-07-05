# Streaming Implementation Reference

Phase 1-3 streaming features for Helen language (966 tests).

## Architecture Overview

```
Phase 1: Stream output stdlib functions (stream_print, progress_bar, etc.)
Phase 2: llm act statement with on_chunk/on_complete callbacks
Phase 3: Async iterator support (for await, StreamingResponse, streaming true)
```

## Key Files

| File | Purpose |
|------|---------|
| `helen/stdlib/__init__.py` | IO functions: stream_print, stream_clear, progress_bar, stream_cursor_up/down |
| `helen/stdlib/stream_contracts.py` | Protocol contracts for stream functions |
| `helen/runtime/stream_contracts.py` | StreamChunk, StreamingLLMRuntime, LlmStreamCallback protocols |
| `helen/runtime/async_iterator_contracts.py` | AsyncIterable, StreamingResponse, AsyncGenerator protocols |
| `helen/runtime/streaming_response.py` | StreamingResponse async iterable wrapper |
| `helen/core/ast.py` | LlmActExprNode (with on_chunk/on_complete), ForAwaitStmtNode, DeclarationNode.streaming |
| `helen/core/parser.py` | llm act parsing with on_chunk/on_complete, for await parsing, streaming true parsing |
| `helen/core/tokens.py` | STREAMING token, 'streaming' keyword |
| `helen/interpreter/interpreter.py` | visit_llm_act_expr (sync/streaming paths), visit_for_await_stmt, _call_llm_streaming |

## Syntax

```helen
// Basic streaming (auto-prints chunks)
llm act "Write a poem"

// With callback
fn handle(chunk) { stream_print("[" + chunk + "]") }
llm act "Write a story" on_chunk handle

// In agent (bare form uses rendered prompt)
agent Poet(topic: str) {
    prompt "Write about: {{topic}}"
    main { llm act }
}

// Streaming agent with for await (custom chunk processing)
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}

main {
    let response = async Streamer("coding")
    for await chunk in response {
        stream_print(chunk)
    }
}
```

## Stdlib IO Functions (5)

| Function | Signature | Purpose |
|----------|-----------|---------|
| `stream_print` | `(text: str) -> str` | Print without newline, flush immediately |
| `stream_clear` | `() -> str` | Clear current line (ANSI \r\x1b[2K) |
| `progress_bar` | `(current, total, width=40) -> str` | Display progress bar with percentage |
| `stream_cursor_up` | `(n=1) -> str` | Move cursor up n lines (ANSI \x1b[nA) |
| `stream_cursor_down` | `(n=1) -> str` | Move cursor down n lines (ANSI \x1b[nB) |

## Test Files

- `tests/parser/test_llm_stream.py` — Parser tests for llm act with callbacks syntax
- `tests/stdlib/test_stream_output.py` — Stdlib IO function tests (287 lines)
- `tests/runtime/test_streaming_response.py` — Async iteration tests

## Implementation Notes

1. **llm act is a statement, not expression** — when used as a statement with on_chunk/on_complete callbacks; `llm act` can also be used as an expression (returns full response text)
2. **Agent context** — automatically uses agent's model/temperature/prompt settings
3. **Fallback** — if runtime doesn't support streaming, falls back to non-streaming `act()`
4. **History** — full response text recorded to conversation history after streaming completes
5. **on_chunk callback** — must be callable; semantic error if not
6. **for await** — only valid in async context; iterates over AsyncIterable objects
7. **Chunk format compatibility** — `act_stream()` yields dicts `{"content": ...}`, not objects
   - Interpreter must handle both: `isinstance(chunk, dict)` → `chunk.get("content")`, else `chunk.content`
   - `StreamingResponse` yields plain strings (already extracted from chunks)
8. **REPL integration** — when agent uses `llm act` with `on_chunk`, REPL handler must not print return value
   - Output goes directly to stdout during execution
   - Handler adds final newline after streaming completes
