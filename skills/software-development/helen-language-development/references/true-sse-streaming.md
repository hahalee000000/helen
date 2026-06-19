# True SSE Streaming Implementation

Session-specific details for implementing real-time streaming in `HttpLLMRuntime.act_stream()`.

## Problem

Initial implementation of `llm stream` fell back to `act()` and yielded the full response as a single chunk. This defeated the purpose of streaming — users had to wait for the complete response before seeing any output.

## Solution

Implement true Server-Sent Events (SSE) streaming using OpenAI's streaming API with full tool-calling loop support.

## Event Protocol

`act_stream()` yields typed event dicts:

```python
{"type": "content", "content": "..."}           # Text chunk (streaming)
{"type": "tool_call", "name": "...", "args": {}}  # Tool invocation
{"type": "tool_result", "name": "...", "result": "..."}  # Tool result
{"type": "error", "message": "..."}              # Error
```

## Implementation Pattern

### 1. Parser: Bare Form Support

When adding a new LLM statement variant, ensure it supports bare form (no prompt) for consistency with `llm act`:

```python
def _llm_stream_stmt(self) -> LlmStreamStmtNode:
    start = self._previous()  # LLM token
    self._consume(TokenType.STREAM, "Expected 'stream' after 'llm'.")
    
    # Check for bare form (statement terminators or newline)
    bare_form_tokens = (
        TokenType.RIGHT_BRACE, TokenType.SEMICOLON, TokenType.EOF,
        TokenType.RETURN, TokenType.LET, TokenType.CONST,
        TokenType.IF, TokenType.FOR, TokenType.WHILE,
        # ... other statement keywords
    )
    if self._check(*bare_form_tokens):
        prompt_expr = None
    elif self._current().line > start.line:
        prompt_expr = None  # Newline boundary
    else:
        prompt_expr = self._expression()
    
    # Optional on_chunk callback
    on_chunk_expr = None
    if prompt_expr is not None and self._check(TokenType.IDENTIFIER) and self._current().lexeme == "on_chunk":
        self._advance()
        on_chunk_expr = self._expression()
    
    return LlmStreamStmtNode(
        prompt=prompt_expr,
        on_chunk=on_chunk_expr,
        span=self._make_span(start, self._previous())
    )
```

### 2. AST: Optional Prompt Field

```python
@dataclass(frozen=True)
class LlmStreamStmtNode(StatementNode):
    prompt: ExpressionNode | None  # None = bare form
    on_chunk: ExpressionNode | None
    span: SourceSpan
```

### 3. Interpreter: Handle Bare Form + Tool Events

```python
def visit_llm_stream_stmt(self, node: LlmStreamStmtNode) -> object:
    # Bare form: use rendered agent prompt as user message
    if node.prompt is not None:
        prompt = node.prompt.accept(self)
        if not isinstance(prompt, str):
            prompt = self._stringify(prompt)
        system_prompt = self._get_rendered_agent_prompt()
    else:
        # Bare form in agent main block
        prompt = self._get_rendered_agent_prompt()
        if not prompt:
            self.errors.error(
                ErrorCode.RUNTIME_ERROR,
                "llm stream (bare form) requires an agent context with a prompt",
                node.span,
            )
            return None
        system_prompt = self._get_agent_setting("description")
    
    # Build tools list from agent declarations
    tools = self._build_tools_list()
    max_turns = int(self._get_agent_setting("max-turns", 1))
    if tools and max_turns < 3:
        max_turns = 3
    
    for event in self.llm_runtime.act_stream(
        prompt, model=model, temperature=temperature,
        system_prompt=system_prompt, tools=tools, max_turns=max_turns,
    ):
        event_type = event.get("type", "content")
        
        if event_type == "content":
            content = event.get("content", "")
            if content:
                if on_chunk_fn is not None:
                    on_chunk_fn(content)
                else:
                    stream_print_fn = stdlib.lookup("stream_print")
                    stream_print_fn.fn(content)
        
        elif event_type == "tool_call":
            fn_name = event.get("name", "")
            fn_args = event.get("args", {})
            args_str = ", ".join(f"{k}={v!r}" for k, v in fn_args.items())
            print(f"\n🔧 Calling {fn_name}({args_str})...\n", end="", flush=True)
        
        elif event_type == "tool_result":
            fn_name = event.get("name", "")
            result = event.get("result", "")
            display_result = result if len(result) <= 200 else result[:200] + "..."
            print(f"✅ {fn_name} returned: {display_result}\n", end="", flush=True)
        
        elif event_type == "error":
            error_msg = event.get("message", "Unknown error")
            self.errors.error(ErrorCode.RUNTIME_ERROR, f"Streaming error: {error_msg}", node.span)
            break
```

### 4. Runtime: True SSE Streaming with Tool Calls

```python
def act_stream(
    self,
    prompt: str,
    model: str | None = None,
    temperature: float = 1.0,
    system_prompt: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    max_turns: int = 5,
    history: list[dict[str, Any]] | None = None,
):
    """Stream LLM response with full tool-calling loop."""
    from helen.runtime.tools import dispatch_tool
    
    use_model = model or self.default_model or "default"
    
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    
    url = f"{self.base_url}/chat/completions"
    
    for turn in range(max_turns + 1):
        payload: dict[str, Any] = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
        
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        
        try:
            full_content = ""
            tool_calls_acc: dict[int, dict] = {}  # index -> {id, name, args_str}
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                for line_bytes in response:
                    line = line_bytes.decode("utf-8").strip()
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            chunk_data = json.loads(data_str)
                            choices = chunk_data.get("choices", [])
                            if not choices:
                                continue
                            
                            delta = choices[0].get("delta", {})
                            
                            # Text content chunk
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                                yield {"type": "content", "content": content}
                            
                            # Tool call deltas (streaming accumulation)
                            tc_deltas = delta.get("tool_calls")
                            if tc_deltas:
                                for tc_delta in tc_deltas:
                                    idx = tc_delta.get("index", 0)
                                    if idx not in tool_calls_acc:
                                        tool_calls_acc[idx] = {
                                            "id": tc_delta.get("id", ""),
                                            "name": "",
                                            "args_str": "",
                                        }
                                    acc = tool_calls_acc[idx]
                                    
                                    fn_delta = tc_delta.get("function", {})
                                    if fn_delta.get("name"):
                                        acc["name"] = fn_delta["name"]
                                    if fn_delta.get("arguments"):
                                        acc["args_str"] += fn_delta["arguments"]
                                    if tc_delta.get("id"):
                                        acc["id"] = tc_delta["id"]
                        
                        except json.JSONDecodeError:
                            continue
            
            # After stream completes: check if we got tool calls
            if tool_calls_acc:
                # Build assistant message with tool calls
                assistant_msg: dict[str, Any] = {"role": "assistant", "content": full_content or None}
                assistant_msg["tool_calls"] = [
                    {
                        "id": tool_calls_acc[i]["id"],
                        "type": "function",
                        "function": {
                            "name": tool_calls_acc[i]["name"],
                            "arguments": tool_calls_acc[i]["args_str"],
                        },
                    }
                    for i in sorted(tool_calls_acc.keys())
                ]
                messages.append(assistant_msg)
                
                # Execute each tool and yield events
                for i in sorted(tool_calls_acc.keys()):
                    tc = tool_calls_acc[i]
                    fn_name = tc["name"]
                    try:
                        fn_args = json.loads(tc["args_str"]) if tc["args_str"] else {}
                    except json.JSONDecodeError:
                        fn_args = {}
                    
                    yield {"type": "tool_call", "name": fn_name, "args": fn_args}
                    
                    result = dispatch_tool(fn_name, fn_args)
                    
                    yield {"type": "tool_result", "name": fn_name, "result": result}
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
                
                # Nudge on last turn
                if turn >= max_turns - 1:
                    messages.append({
                        "role": "user",
                        "content": "Based on the tool results above, please provide your final answer now.",
                    })
                
                continue  # Next turn: stream again with tool results
            
            else:
                # No tool calls — final text response, already streamed
                break
        
        except urllib.error.HTTPError as e:
            yield {"type": "error", "message": f"HTTP error {e.code}: {e.reason}"}
            break
        except urllib.error.URLError as e:
            yield {"type": "error", "message": f"HTTP request failed: {e}"}
            break
        except TimeoutError:
            yield {"type": "error", "message": f"Request timed out after {self.timeout}s"}
            break
        except Exception as e:
            yield {"type": "error", "message": f"Unexpected error: {e}"}
            break
```

### 5. REPL Handler: Streaming Output

When converting REPL handlers from `llm act` to `llm stream`:

```python
# Before (llm act):
def _run_helen_assistant(question: str) -> str:
    # ... parse and execute
    result = interp.interpret(program)
    return result if result else "No response generated."

# After (llm stream):
def _run_helen_assistant(question: str) -> bool:
    # ... parse and execute
    try:
        result = interp.interpret(program)
        # Output is streamed directly to stdout by llm stream
        if errors.has_errors:
            print(f"\nError: {errors.format_report()}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        return False

# REPL handler:
if cmd == ":ask":
    print("\n🤔 Thinking...\n")
    _run_helen_assistant(arg)
    # Output is streamed directly to stdout
    print()  # Final newline after streaming completes
    return True
```

## Testing

### Parser Test: Bare Form

```python
def test_llm_stream_bare_form(self):
    """llm stream without prompt should parse as bare form."""
    source = 'llm stream'
    errors = ErrorReporter()
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    
    assert not errors.has_errors, "Bare form should parse OK"
    assert len(program.statements) == 1
    
    stmt = program.statements[0]
    assert isinstance(stmt, LlmStreamStmtNode)
    assert stmt.prompt is None  # Bare form has no prompt
```

### Runtime Test: Content Events

```python
def test_act_stream_yields_content_events(self):
    """act_stream should yield content events from SSE response."""
    runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
    
    sse_lines = [
        b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
        b'data: {"choices": [{"delta": {"content": " World"}}]}\n',
        b'data: [DONE]\n',
    ]
    
    mock_response = MagicMock()
    mock_response.__enter__ = MagicMock(return_value=iter(sse_lines))
    mock_response.__exit__ = MagicMock(return_value=False)
    
    with patch('urllib.request.urlopen', return_value=mock_response):
        events = list(runtime.act_stream("test prompt"))
    
    assert len(events) == 2
    assert events[0] == {"type": "content", "content": "Hello"}
    assert events[1] == {"type": "content", "content": " World"}
```

### Runtime Test: Tool Call Streaming

```python
def test_act_stream_tool_calls(self):
    """act_stream should accumulate and yield tool call events."""
    runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
    
    # Mock SSE with tool call deltas then a final text response
    sse_lines_turn1 = [
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "web_search", "arguments": ""}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\\"query\\""}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ":\\"test\\"}"}}]}}]}\n',
        b'data: [DONE]\n',
    ]
    sse_lines_turn2 = [
        b'data: {"choices": [{"delta": {"content": "Final answer"}}]}\n',
        b'data: [DONE]\n',
    ]
    
    responses = [iter(sse_lines_turn1), iter(sse_lines_turn2)]
    call_count = [0]
    
    def mock_urlopen(*args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=responses[call_count[0]])
        mock_resp.__exit__ = MagicMock(return_value=False)
        call_count[0] += 1
        return mock_resp
    
    with patch('urllib.request.urlopen', side_effect=mock_urlopen):
        with patch('helen.runtime.tools.dispatch_tool', return_value="search result"):
            events = list(runtime.act_stream("test prompt", tools=[{"type": "function"}]))
    
    tool_calls = [e for e in events if e["type"] == "tool_call"]
    tool_results = [e for e in events if e["type"] == "tool_result"]
    contents = [e for e in events if e["type"] == "content"]
    
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "web_search"
    assert tool_calls[0]["args"] == {"query": "test"}
    
    assert len(tool_results) == 1
    assert tool_results[0]["result"] == "search result"
    
    assert len(contents) == 1
    assert contents[0]["content"] == "Final answer"
```

## Pitfalls

1. **Bare form consistency**: If `llm act` supports bare form, `llm stream` must also support it for agent contexts
2. **Event-based protocol**: `act_stream()` yields typed event dicts with `"type"` field, not just content strings
3. **Tool call delta accumulation**: OpenAI streams tool calls incrementally — must accumulate `function.name` and `function.arguments` across multiple SSE chunks before executing
4. **Multi-turn loop**: After tool execution, must loop back and stream again with tool results in messages
5. **REPL handler conversion**: When switching from `llm act` to `llm stream`, change return type from `str` to `bool` and print errors to stderr
6. **SSE parsing**: Skip malformed JSON lines gracefully (don't crash on invalid data)
7. **Empty content**: Skip chunks with `content == ""` to avoid unnecessary output
8. **Test updates**: When adding bare form support, update "missing prompt should error" tests to "bare form should parse OK"
9. **dispatch_tool import location**: In tests, patch `helen.runtime.tools.dispatch_tool`, not `helen.runtime.http_llm.dispatch_tool` (it's imported inside the function)
10. **Tool result truncation**: Long tool results should be truncated for display (200 chars) to avoid flooding the terminal

## Verification

```bash
# Test bare form parsing
python -m pytest tests/parser/test_llm_stream.py -v

# Test SSE streaming
python -m pytest tests/runtime/test_http_llm_stream.py -v

# Test REPL integration
python -m pytest tests/cli/test_repl_ask.py -v

# Full test suite
python -m pytest tests/ --tb=short -q
```

Expected: 971+ tests pass.
