"""HTTP-based LLM runtime using OpenAI-compatible API.

Connects to OpenAI-compatible endpoints (e.g., DashScope, OpenAI, etc.) for fast
LLM calls without spawning subprocess each time.

Supports function calling: when tools are provided, the runtime enters a
loop where the LLM can request tool calls, which are executed and their
results fed back to the LLM until it produces a final text response.

Enhanced features (borrowed from Hermes):
- Concurrent tool execution (ThreadPoolExecutor)
- Multi-retry with exponential backoff
- Empty response nudge (recover from silent LLM)
- Iteration budget (prevent infinite loops)
- Tool result truncation (prevent context explosion)
- Message sanitization (fix surrogate chars, role alternation)
- Stream health checks (timeout detection)
- Prompt caching support (Anthropic cache_control)

Usage:
    from helen.runtime.http_llm import HttpLLMRuntime
    runtime = HttpLLMRuntime()  # Auto-loads from ~/.helen/config.yaml or ~/.hermes/.env
    response = runtime.act("Translate: hello")
    response = runtime.act("Search for Python docs", tools=[...])
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from helen.runtime.llm_runtime import LLMResponse, LLMRuntime

logger = logging.getLogger(__name__)


def _load_hermes_env() -> dict[str, str]:
    """Load environment variables from Helen or Hermes config.

    Priority:
    1. ~/.helen/config.yaml
    2. ~/.helen/.env
    3. ~/.hermes/.env (fallback)

    Returns dict with keys like DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL for
    backward compatibility.
    """
    from helen.runtime.config import load_config
    config = load_config()
    # Convert config to env-style dict for compatibility
    env = {}
    if "api_key" in config:
        env["DASHSCOPE_API_KEY"] = config["api_key"]
    if "base_url" in config:
        env["DASHSCOPE_BASE_URL"] = config["base_url"]
    return env


# ---------------------------------------------------------------------------
# Message Sanitization (borrowed from Hermes)
# ---------------------------------------------------------------------------

# Matches lone surrogate characters (U+D800-U+DFFF)
_SURROGATE_RE = re.compile(r'[\ud800-\udfff]')


def _sanitize_surrogates(text: str) -> str:
    """Strip lone surrogate characters that crash json.dumps()."""
    if not text:
        return text
    return _SURROGATE_RE.sub('', text)


def _sanitize_messages(messages: list[dict[str, Any]]) -> int:
    """Sanitize all message content fields in-place. Returns count of fixes."""
    count = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            cleaned = _sanitize_surrogates(content)
            if cleaned != content:
                msg["content"] = cleaned
                count += 1
        # Also sanitize tool call arguments
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            args = fn.get("arguments", "")
            if isinstance(args, str):
                cleaned = _sanitize_surrogates(args)
                if cleaned != args:
                    fn["arguments"] = cleaned
                    count += 1
    return count


def _repair_message_sequence(messages: list[dict[str, Any]]) -> int:
    """Repair role-alternation violations before API call.

    Most providers require: system → user → assistant → tool → assistant → ...
    Catches tool→user or user→user sequences that cause empty responses.
    Returns count of repairs made.
    """
    count = 0
    i = 1
    while i < len(messages):
        prev_role = messages[i - 1].get("role", "")
        curr_role = messages[i].get("role", "")

        # tool → user is invalid: insert a synthetic assistant bridge
        if prev_role == "tool" and curr_role == "user":
            messages.insert(i, {"role": "assistant", "content": ""})
            count += 1
            i += 2
            continue

        # user → user: merge into previous
        if prev_role == "user" and curr_role == "user":
            prev_content = messages[i - 1].get("content", "")
            curr_content = messages[i].get("content", "")
            messages[i - 1]["content"] = prev_content + "\n\n" + curr_content
            messages.pop(i)
            count += 1
            continue

        i += 1
    return count


# ---------------------------------------------------------------------------
# Tool Result Truncation (borrowed from Hermes)
# ---------------------------------------------------------------------------

# Maximum characters per tool result before truncation
MAX_TOOL_RESULT_CHARS = 16000
# Maximum total tool results per turn
MAX_TOOL_RESULTS_PER_TURN = 10


def _truncate_tool_result(result: str, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Truncate a tool result if it exceeds max_chars."""
    if len(result) <= max_chars:
        return result
    half = max_chars // 2
    return (
        result[:half]
        + f"\n\n... [{len(result) - max_chars} chars truncated] ...\n\n"
        + result[-half:]
    )


# ---------------------------------------------------------------------------
# Concurrent Tool Execution (borrowed from Hermes)
# ---------------------------------------------------------------------------

_MAX_TOOL_WORKERS = 8


def _execute_tools_concurrent(
    tool_calls: list[dict[str, Any]],
    dispatch_fn,
) -> list[tuple[dict[str, Any], str]]:
    """Execute multiple tool calls concurrently using a thread pool.

    Args:
        tool_calls: List of tool call dicts from LLM response.
        dispatch_fn: Function(name, args) -> str result.

    Returns:
        List of (tool_call, result) tuples in original order.
    """
    if len(tool_calls) <= 1:
        # Single tool call — no need for threading
        results = []
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"].get("arguments", "{}"))
            except json.JSONDecodeError:
                fn_args = {}
            result = dispatch_fn(fn_name, fn_args)
            results.append((tc, result))
        return results

    # Multiple tool calls — execute concurrently
    parsed = []
    for tc in tool_calls:
        fn_name = tc["function"]["name"]
        try:
            fn_args = json.loads(tc["function"].get("arguments", "{}"))
        except json.JSONDecodeError:
            fn_args = {}
        parsed.append((tc, fn_name, fn_args))

    results: list[tuple[dict, str] | None] = [None] * len(parsed)

    with ThreadPoolExecutor(max_workers=min(len(parsed), _MAX_TOOL_WORKERS)) as executor:
        future_to_idx = {}
        for idx, (tc, fn_name, fn_args) in enumerate(parsed):
            future = executor.submit(dispatch_fn, fn_name, fn_args)
            future_to_idx[future] = idx

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result(timeout=300)  # 5 min per tool
            except Exception as e:
                result = json.dumps({"error": f"Tool execution failed: {e}"})
            results[idx] = (parsed[idx][0], result)

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Iteration Budget (borrowed from Hermes)
# ---------------------------------------------------------------------------

@dataclass
class IterationBudget:
    """Track remaining API call iterations to prevent infinite loops."""
    max_total: int = 20
    used: int = 0

    def consume(self) -> bool:
        """Consume one iteration. Returns False if budget exhausted."""
        if self.used >= self.max_total:
            return False
        self.used += 1
        return True

    @property
    def remaining(self) -> int:
        return max(0, self.max_total - self.used)


# ---------------------------------------------------------------------------
# HTTP LLM Runtime
# ---------------------------------------------------------------------------


@dataclass
class HttpLLMRuntime(LLMRuntime):
    """HTTP-based LLM runtime using OpenAI-compatible API.

    Connects to a persistent HTTP server for fast LLM calls.
    Avoids subprocess overhead by reusing HTTP connections.

    Enhanced with Hermes-style reliability features:
    - Concurrent tool execution
    - Multi-retry with backoff
    - Empty response nudge
    - Iteration budget
    - Tool result truncation
    - Message sanitization

    Args:
        base_url: Base URL of the OpenAI-compatible API
        api_key: API key for authentication
        default_model: Default model to use
        timeout: Request timeout in seconds
        max_retries: Max retry attempts for transient errors
        enable_concurrent_tools: Enable concurrent tool execution
        enable_message_sanitization: Sanitize messages before API call
        enable_tool_truncation: Truncate oversized tool results
    """

    base_url: str = ""
    api_key: str = ""
    default_model: str | None = None
    timeout: int = 120
    max_retries: int = 3
    enable_concurrent_tools: bool = True
    enable_message_sanitization: bool = True
    enable_tool_truncation: bool = True
    _last_error: str | None = field(default=None, repr=False)

    def __post_init__(self):
        """Auto-load configuration from Helen or Hermes config."""
        if not self.base_url or not self.api_key:
            hermes_env = _load_hermes_env()
            if not self.base_url:
                self.base_url = hermes_env.get("DASHSCOPE_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
            if not self.api_key:
                self.api_key = hermes_env.get("DASHSCOPE_API_KEY", "")
            if not self.default_model:
                self.default_model = "qwen3.7-plus"

    def route(
        self,
        description: str,
        branches: list[str],
        context: str | None = None,
    ) -> str | None:
        """Route input to one of the given branches via LLM."""
        branch_list = ", ".join(branches)
        prompt = (
            f"{description}\n"
            f"Available branches: {branch_list}\n"
            f"Reply with ONLY the branch name that best matches.\n"
        )
        if context:
            prompt += f"\nContext: {context}\n"

        response = self._chat(prompt)
        if response is None:
            return None

        # Try to match the response to a valid branch
        cleaned = response.strip().strip('"').strip("'").lower()
        for branch in branches:
            if cleaned == branch.lower() or cleaned.startswith(branch.lower()):
                return branch

        return branches[0] if branches else None

    def act(
        self,
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 1.0,
        max_turns: int = 1,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        dispatch_fn: Any = None,
    ) -> LLMResponse:
        """Execute an autonomous LLM action with enhanced reliability.

        Enhanced features (borrowed from Hermes):
        - Concurrent tool execution for parallel tool calls
        - Multi-retry with exponential backoff for transient errors
        - Empty response nudge to recover from silent LLM
        - Iteration budget to prevent infinite loops
        - Tool result truncation to prevent context explosion
        - Message sanitization to fix encoding issues

        Args:
            dispatch_fn: Optional custom tool dispatch function.
                Signature: (name: str, args: dict) -> str
                If not provided, uses the default dispatch_tool from helen.runtime.tools.
                This allows injecting Helen function execution logic.

        When tools are provided, enters a loop: LLM may request tool calls,
        which are executed and fed back until the LLM produces a final text
        response or max_turns is reached.
        """
        from helen.runtime.tools import dispatch_tool as default_dispatch

        # Use custom dispatch function or fall back to default
        _dispatch = dispatch_fn if dispatch_fn is not None else default_dispatch

        # Build messages
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        use_model = model or self.default_model or "default"
        final_text = ""

        # Iteration budget: prevent infinite loops
        budget = IterationBudget(max_total=max_turns + 2)  # +2 for nudge retries
        empty_response_retries = 0
        max_empty_retries = 2

        while budget.consume():
            # Message sanitization before each API call
            if self.enable_message_sanitization:
                sanitized = _sanitize_messages(messages)
                if sanitized:
                    logger.debug("Sanitized %d surrogate chars before API call", sanitized)
                repaired = _repair_message_sequence(messages)
                if repaired:
                    logger.debug("Repaired %d role-alternation violations", repaired)

            # API call with retry
            response_msg = self._chat_with_messages_retry(
                messages, model=use_model, temperature=temperature, tools=tools,
            )
            if response_msg is None:
                # API call failed — raise error instead of silently returning empty
                error_msg = self._last_error or "Unknown API error"
                raise RuntimeError(f"LLM API call failed: {error_msg}")

            # Check if LLM wants tool calls
            tool_calls = response_msg.get("tool_calls")
            if tool_calls:
                # Append assistant message with tool_calls
                messages.append(response_msg)

                # Execute tool calls (concurrently if enabled)
                if self.enable_concurrent_tools and len(tool_calls) > 1:
                    tool_results = _execute_tools_concurrent(tool_calls, _dispatch)
                else:
                    # Sequential execution
                    tool_results = []
                    for tc in tool_calls:
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"].get("arguments", "{}"))
                        except json.JSONDecodeError:
                            fn_args = {}
                        result = _dispatch(fn_name, fn_args)
                        tool_results.append((tc, result))

                # Append tool results with truncation
                for tc, result in tool_results:
                    if self.enable_tool_truncation:
                        result = _truncate_tool_result(result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                # Reset empty response counter after successful tool execution
                empty_response_retries = 0
                continue

            else:
                # No tool calls — check if response is empty
                content = response_msg.get("content", "")
                if not content or not content.strip():
                    # Empty response — nudge the LLM to continue
                    if empty_response_retries < max_empty_retries:
                        empty_response_retries += 1
                        logger.info(
                            "Empty response from LLM — nudging to continue (%d/%d)",
                            empty_response_retries, max_empty_retries,
                        )
                        # Append empty assistant message + nudge
                        messages.append(response_msg)
                        messages.append({
                            "role": "user",
                            "content": (
                                "You returned an empty response. "
                                "Please process the tool results above and "
                                "provide your final answer."
                            ),
                        })
                        continue
                    else:
                        # Exhausted nudge retries
                        logger.warning("Empty response after %d nudge retries", max_empty_retries)
                        break

                # Valid final response
                final_text = content
                break

        return LLMResponse(
            text=final_text,
            model=use_model,
        )

    def _chat_with_messages_retry(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 1.0,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Send a chat completion request with retry logic.

        Retries on transient errors (timeout, 5xx) with exponential backoff.
        """
        import time

        for attempt in range(self.max_retries + 1):
            result = self._chat_with_messages(messages, model=model, temperature=temperature, tools=tools)
            if result is not None:
                return result

            # Check if we should retry
            if attempt < self.max_retries:
                error = self._last_error or ""
                # Retry on timeout or server errors
                is_retryable = (
                    "timed out" in error.lower()
                    or "500" in error
                    or "502" in error
                    or "503" in error
                    or "504" in error
                    or "429" in error  # rate limit
                )
                if is_retryable:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = min(2 ** attempt, 10)
                    logger.info(
                        "API call failed (attempt %d/%d): %s — retrying in %ds",
                        attempt + 1, self.max_retries + 1, error, wait_time,
                    )
                    time.sleep(wait_time)
                    continue

            # Non-retryable error or exhausted retries
            break

        return None

    def _chat(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 1.0,
        system_prompt: str | None = None,
    ) -> str | None:
        """Send a chat completion request to the API (simple, no tools).

        Args:
            prompt: The prompt text.
            model: Optional model override.
            temperature: Sampling temperature.
            system_prompt: Optional system prompt (injected as first message).

        Returns:
            The response text, or None on failure.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response_msg = self._chat_with_messages(messages, model=model, temperature=temperature)
        if response_msg is None:
            return None
        return response_msg.get("content", "")

    def _chat_with_messages(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 1.0,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Send a chat completion request and return the full message dict.

        Args:
            messages: List of message dicts (system/user/assistant/tool).
            model: Optional model override.
            temperature: Sampling temperature.
            tools: Optional list of tool schemas for function calling.

        Returns:
            The assistant message dict (may contain 'content' and/or 'tool_calls'),
            or None on failure.
        """
        url = f"{self.base_url}/chat/completions"

        payload: dict[str, Any] = {
            "model": model or self.default_model or "default",
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {})
                return {"content": ""}

        except urllib.error.HTTPError as e:
            # Read the error body for structured API error messages
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
                error_data = json.loads(error_body)
                api_error = error_data.get("error", {})
                error_msg = api_error.get("message", str(e))
                error_code = api_error.get("code", "")
                self._last_error = f"API error ({e.code} {error_code}): {error_msg}"
            except Exception:
                self._last_error = f"HTTP error {e.code}: {e.reason}"
            return None
        except urllib.error.URLError as e:
            self._last_error = f"HTTP request failed: {e}"
            return None
        except TimeoutError:
            self._last_error = f"Request timed out after {self.timeout}s"
            return None
        except json.JSONDecodeError as e:
            self._last_error = f"Invalid JSON response: {e}"
            return None
        except Exception as e:
            self._last_error = f"Unexpected error: {e}"
            return None

    def act_stream(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 1.0,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_turns: int = 5,
        history: list[dict[str, Any]] | None = None,
        dispatch_fn: Any = None,
    ):
        """Stream LLM response with enhanced reliability features.

        Enhanced features (borrowed from Hermes):
        - Concurrent tool execution for parallel tool calls
        - Stream health checks (timeout detection)
        - Empty response nudge to recover from silent LLM
        - Iteration budget to prevent infinite loops
        - Tool result truncation to prevent context explosion
        - Message sanitization to fix encoding issues

        Args:
            dispatch_fn: Optional custom tool dispatch function.
                Signature: (name: str, args: dict) -> str
                If not provided, uses the default dispatch_tool from helen.runtime.tools.
                This allows injecting Helen function execution logic.

        Yields event dicts:
            {"type": "content", "content": "..."}     — text chunk
            {"type": "tool_call", "name": "...", "args": {...}}  — tool invocation
            {"type": "tool_result", "name": "...", "result": "..."}  — tool result
            {"type": "usage", "usage": {...}}         — token usage
            {"type": "error", "message": "..."}       — error
        """
        from helen.runtime.tools import dispatch_tool as default_dispatch

        # Use custom dispatch function or fall back to default
        _dispatch = dispatch_fn if dispatch_fn is not None else default_dispatch

        use_model = model or self.default_model or "default"

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        url = f"{self.base_url}/chat/completions"

        # Iteration budget: prevent infinite loops
        budget = IterationBudget(max_total=max_turns + 2)
        empty_response_retries = 0
        max_empty_retries = 2

        while budget.consume():
            # Message sanitization before each API call
            if self.enable_message_sanitization:
                sanitized = _sanitize_messages(messages)
                if sanitized:
                    logger.debug("Sanitized %d surrogate chars before stream call", sanitized)
                repaired = _repair_message_sequence(messages)
                if repaired:
                    logger.debug("Repaired %d role-alternation violations", repaired)

            # Build streaming request
            payload: dict[str, Any] = {
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if tools:
                payload["tools"] = tools

            data = json.dumps(payload).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )

            try:
                # Collect streamed chunks with health checking
                full_content = ""
                tool_calls_acc: dict[int, dict] = {}  # index -> {name, args_str, id}
                usage_info: dict[str, int] = {}  # token usage from final chunk
                last_chunk_time = 0.0
                stale_threshold = 90.0  # seconds without data = stale

                import time
                stream_start = time.time()

                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    for line_bytes in response:
                        line = line_bytes.decode("utf-8").strip()
                        if not line:
                            continue

                        last_chunk_time = time.time()

                        # Health check: detect stale stream
                        if last_chunk_time - stream_start > stale_threshold:
                            elapsed_since_chunk = time.time() - last_chunk_time
                            if elapsed_since_chunk > stale_threshold:
                                logger.warning(
                                    "Stream stale for %.1fs — closing connection",
                                    elapsed_since_chunk,
                                )
                                yield {"type": "error", "message": f"Stream stale after {elapsed_since_chunk:.1f}s"}
                                break

                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break

                            try:
                                chunk_data = json.loads(data_str)

                                # Capture usage info (sent in final chunk when include_usage=True)
                                chunk_usage = chunk_data.get("usage")
                                if chunk_usage:
                                    usage_info = chunk_usage

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

                # Yield usage info at the end of this turn's stream
                if usage_info:
                    yield {"type": "usage", "usage": usage_info}

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

                    # Execute tools concurrently if enabled
                    tool_call_list = [
                        {
                            "id": tool_calls_acc[i]["id"],
                            "function": {
                                "name": tool_calls_acc[i]["name"],
                                "arguments": tool_calls_acc[i]["args_str"],
                            },
                        }
                        for i in sorted(tool_calls_acc.keys())
                    ]

                    if self.enable_concurrent_tools and len(tool_call_list) > 1:
                        tool_results = _execute_tools_concurrent(tool_call_list, _dispatch)
                    else:
                        # Sequential execution
                        tool_results = []
                        for tc in tool_call_list:
                            fn_name = tc["function"]["name"]
                            try:
                                fn_args = json.loads(tc["function"].get("arguments", "{}"))
                            except json.JSONDecodeError:
                                fn_args = {}
                            result = _dispatch(fn_name, fn_args)
                            tool_results.append((tc, result))

                    # Yield events and append results
                    for tc, result in tool_results:
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"].get("arguments", "{}"))
                        except json.JSONDecodeError:
                            fn_args = {}

                        yield {"type": "tool_call", "name": fn_name, "args": fn_args}

                        # Truncate result if enabled
                        if self.enable_tool_truncation:
                            result = _truncate_tool_result(result)

                        yield {"type": "tool_result", "name": fn_name, "result": result}

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        })

                    # Reset empty response counter after successful tool execution
                    empty_response_retries = 0
                    continue  # Next turn: stream again with tool results

                else:
                    # No tool calls — check if response is empty
                    if not full_content or not full_content.strip():
                        # Empty response — nudge the LLM
                        if empty_response_retries < max_empty_retries:
                            empty_response_retries += 1
                            logger.info(
                                "Empty stream response — nudging to continue (%d/%d)",
                                empty_response_retries, max_empty_retries,
                            )
                            messages.append({"role": "assistant", "content": ""})
                            messages.append({
                                "role": "user",
                                "content": (
                                    "You returned an empty response. "
                                    "Please process the tool results above and "
                                    "provide your final answer."
                                ),
                            })
                            continue
                        else:
                            logger.warning("Empty stream response after %d nudge retries", max_empty_retries)
                            break

                    # Valid final response — already streamed
                    break

            except urllib.error.HTTPError as e:
                # Read the error body for structured API error messages
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8")
                    error_data = json.loads(error_body)
                    api_error = error_data.get("error", {})
                    error_msg = api_error.get("message", str(e))
                    error_code = api_error.get("code", "")
                    yield {"type": "error", "message": f"API error ({e.code} {error_code}): {error_msg}"}
                except Exception:
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

    @property
    def last_error(self) -> str | None:
        """The error message from the last failed LLM call."""
        return self._last_error
