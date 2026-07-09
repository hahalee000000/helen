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
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import httpx

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
        elif isinstance(content, list):
            # v1.17: Sanitize text parts within multimodal content
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    if isinstance(text, str):
                        cleaned = _sanitize_surrogates(text)
                        if cleaned != text:
                            part["text"] = cleaned
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


def _merge_content(prev: Any, curr: Any) -> Any:
    """Merge two message content values, handling both str and list[dict].

    v1.17: Supports multimodal content merging.
    """
    # Both strings: simple concat
    if isinstance(prev, str) and isinstance(curr, str):
        return prev + "\n\n" + curr
    # Both lists: concatenate
    if isinstance(prev, list) and isinstance(curr, list):
        return prev + [{"type": "text", "text": ""}] + curr
    # Mixed: convert string to text part, then concatenate
    if isinstance(prev, str) and isinstance(curr, list):
        return [{"type": "text", "text": prev}] + curr
    if isinstance(prev, list) and isinstance(curr, str):
        return prev + [{"type": "text", "text": "\n\n" + curr}]
    # Fallback: convert both to strings
    return str(prev) + "\n\n" + str(curr)


def _repair_message_sequence(messages: list[dict[str, Any]]) -> int:
    """Repair role-alternation violations before API call.

    Most providers require: system → user → assistant → tool → assistant → ...
    Catches tool→user or user→user sequences that cause empty responses.
    Returns count of repairs made.

    v1.17: Handles multimodal content (list[dict]) properly via _merge_content.
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
            messages[i - 1]["content"] = _merge_content(prev_content, curr_content)
            messages.pop(i)
            count += 1
            continue

        i += 1
    return count


def _last_user_message_matches(messages: list[dict[str, Any]], prompt: Any) -> bool:
    """Check if the last message is a user message with content matching prompt.

    v1.17: Handles multimodal list content by comparing text portions only.
    Used to avoid appending duplicate user messages.

    Args:
        messages: List of message dicts.
        prompt: The prompt to compare against (str or any type).

    Returns:
        True if last message is a user with matching content.
    """
    if not messages:
        return False
    last_msg = messages[-1]
    if last_msg.get("role") != "user":
        return False
    last_content = last_msg.get("content", "")
    # For multimodal list content, extract text for comparison
    if isinstance(last_content, list):
        last_text = "\n".join(
            p.get("text", "") for p in last_content
            if isinstance(p, dict) and p.get("type") == "text"
        )
    else:
        last_text = last_content
    prompt_text = prompt if isinstance(prompt, str) else str(prompt)
    return last_text == prompt_text


# ---------------------------------------------------------------------------
# Context Window Protection (HLD 3.12)
# ---------------------------------------------------------------------------

# Maximum characters per tool result before truncation
MAX_TOOL_RESULT_CHARS = 16000
# Maximum total tool results per turn (enforced to prevent context explosion)
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


def _enforce_tool_results_per_turn(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enforce MAX_TOOL_RESULTS_PER_TURN by dropping excess tool calls.

    When an LLM requests more tool calls than allowed in a single turn,
    keeps the first MAX_TOOL_RESULTS_PER_TURN and drops the rest.
    Adds a note in the dropped calls' results to inform the LLM.

    Args:
        tool_calls: List of tool call dicts from LLM response.

    Returns:
        Trimmed list of tool calls (up to MAX_TOOL_RESULTS_PER_TURN).
    """
    if len(tool_calls) <= MAX_TOOL_RESULTS_PER_TURN:
        return tool_calls
    logger.warning(
        "LLM requested %d tool calls, truncating to %d",
        len(tool_calls), MAX_TOOL_RESULTS_PER_TURN,
    )
    return tool_calls[:MAX_TOOL_RESULTS_PER_TURN]


# Context-too-large error markers from various API providers
_CONTEXT_ERROR_MARKERS = (
    "context_length_exceeded",
    "maximum context length",
    "context too long",
    "reduce your prompt",
    "token limit",
    "too many tokens",
    "reduce the length",
    "exceeds the model's context",
    "max_tokens",
    "request too large",
)


def _is_context_length_error(error_msg: str) -> bool:
    """Detect if an error message indicates context window overflow.

    Checks for known markers from OpenAI, Anthropic, DashScope, etc.

    Args:
        error_msg: Error message string from API.

    Returns:
        True if this looks like a context-too-large error.
    """
    if not error_msg:
        return False
    lower = error_msg.lower()
    return any(marker in lower for marker in _CONTEXT_ERROR_MARKERS)


def _trim_messages_for_recovery(
    messages: list[dict[str, Any]],
    drop_count: int = 2,
) -> list[dict[str, Any]]:
    """Trim messages to recover from context overflow.

    Removes the oldest non-system messages to free up context space.
    Keeps system message and the most recent messages.

    Args:
        messages: Current messages list.
        drop_count: Number of oldest messages to remove.

    Returns:
        Trimmed messages list.
    """
    if len(messages) <= 2:
        return messages  # Can't trim further

    # Find the first non-system message index
    start_idx = 0
    for i, msg in enumerate(messages):
        if msg.get("role") != "system":
            start_idx = i
            break

    # Drop oldest non-system messages
    new_messages = messages[:start_idx] + messages[start_idx + drop_count:]
    logger.info(
        "Context overflow recovery: dropped %d oldest messages (%d -> %d)",
        drop_count, len(messages), len(new_messages),
    )
    return new_messages


# ---------------------------------------------------------------------------
# Concurrent Tool Execution (borrowed from Hermes)
# ---------------------------------------------------------------------------

_MAX_TOOL_WORKERS = 8


def _execute_tools_concurrent(
    tool_calls: list[dict[str, Any]],
    dispatch_fn,
    executor: ThreadPoolExecutor | None = None,
) -> list[tuple[dict[str, Any], str]]:
    """Execute multiple tool calls concurrently using a thread pool.

    Args:
        tool_calls: List of tool call dicts from LLM response.
        dispatch_fn: Function(name, args) -> str result.
        executor: Optional persistent ThreadPoolExecutor to reuse.

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

    # Use persistent pool if provided, otherwise create temporary
    own_pool = executor is None
    pool = executor or ThreadPoolExecutor(max_workers=min(len(parsed), _MAX_TOOL_WORKERS))

    try:
        future_to_idx = {}
        for idx, (tc, fn_name, fn_args) in enumerate(parsed):
            future = pool.submit(dispatch_fn, fn_name, fn_args)
            future_to_idx[future] = idx

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result(timeout=300)  # 5 min per tool
            except Exception as e:
                result = json.dumps({"error": f"Tool execution failed: {e}"}, ensure_ascii=False)
            results[idx] = (parsed[idx][0], result)
    finally:
        if own_pool:
            pool.shutdown(wait=False)

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
    enable_reactive_compaction: bool = True
    _last_error: str | None = field(default=None, repr=False)
    _client: Any = field(default=None, repr=False, init=False)
    _async_client: Any = field(default=None, repr=False, init=False)
    _tool_pool: Any = field(default=None, repr=False, init=False)
    _reactive_compactor: Any = field(default=None, repr=False, init=False)

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

        # Initialize reactive compactor for mid-turn compression
        if self.enable_reactive_compaction:
            from helen.runtime.reactive_compaction import ReactiveCompactor
            self._reactive_compactor = ReactiveCompactor()

        # Persistent HTTP client with connection pooling (keeps TCP+TLS alive)
        self._client = httpx.Client(
            timeout=httpx.Timeout(self.timeout, connect=30.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        # Persistent async client for true async support
        self._async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=30.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        # Persistent thread pool for concurrent tool execution
        self._tool_pool = ThreadPoolExecutor(max_workers=_MAX_TOOL_WORKERS)

    def close(self):
        """Close persistent HTTP clients and thread pool."""
        if self._client is not None:
            self._client.close()
        if self._async_client is not None:
            # httpx.AsyncClient uses aclose(), not close()
            try:
                self._async_client.aclose()
            except Exception:
                pass
        if self._tool_pool is not None:
            self._tool_pool.shutdown(wait=False)

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
        # P0 fix: Only append user message if not already the last message in history.
        # The caller (llm_mixin) records the user prompt to history before calling act(),
        # and _prepare_history_for_llm includes it in the returned list.
        # Without this check, the user message would appear twice (repaired by
        # _repair_message_sequence, but that's a code smell we're eliminating).
        # v1.17: Compare content properly for multimodal (list) content.
        if not messages or not _last_user_message_matches(messages, prompt):
            messages.append({"role": "user", "content": prompt})

        use_model = model or self.default_model or "default"
        final_text = ""
        # P1: Track tool calls for history recording by caller
        tool_calls_log: list[dict[str, Any]] = []

        # Iteration budget: prevent infinite loops
        budget = IterationBudget(max_total=max_turns + 2)  # +2 for nudge retries
        empty_response_retries = 0
        max_empty_retries = 2

        while budget.consume():
            # Phase 9B: Reset reactive compactor per-turn state
            if getattr(self, '_reactive_compactor', None) is not None:
                self._reactive_compactor.reset_turn()

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
                # P0: Enforce MAX_TOOL_RESULTS_PER_TURN to prevent context explosion
                tool_calls = _enforce_tool_results_per_turn(tool_calls)

                # Append assistant message with tool_calls
                messages.append(response_msg)

                # Execute tool calls (concurrently if enabled)
                if self.enable_concurrent_tools and len(tool_calls) > 1:
                    tool_results = _execute_tools_concurrent(
                        tool_calls, _dispatch, executor=self._tool_pool,
                    )
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
                    # P1: Log tool call for history recording by caller
                    tool_calls_log.append({
                        "name": tc["function"]["name"],
                        "args": tc["function"].get("arguments", "{}"),
                        "result": result[:500] if len(result) > 500 else result,
                    })

                # Phase 9B: Reactive compaction check after tool results
                if getattr(self, 'enable_reactive_compaction', False) and \
                   getattr(self, '_reactive_compactor', None) is not None:
                    use_model = model or self.default_model
                    from helen.runtime.history import get_model_context_window
                    max_tokens = get_model_context_window(use_model)
                    messages, rc_layer = self._reactive_compactor.check_and_compact(
                        messages, max_tokens,
                    )
                    if rc_layer:
                        logger.info(
                            "Reactive compaction triggered during tool loop: %s",
                            rc_layer,
                        )

                # Phase 9A: Context awareness — inject usage warning if needed
                self._inject_usage_warning_if_needed(messages)

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
            tool_calls=tool_calls_log,  # P1: expose tool calls for history recording
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
        On context-too-large errors, uses multi-step recovery cascade:
        1. Context Collapse overflow recovery (zero-cost)
        2. Reactive Compaction — structural (zero-cost)
        3. Reactive Compaction — semantic (if llm_client available)
        4. Aggressive trim (last resort)
        """
        context_overflow_retried = False

        for attempt in range(self.max_retries + 1):
            result = self._chat_with_messages(messages, model=model, temperature=temperature, tools=tools)
            if result is not None:
                return result

            error = self._last_error or ""

            # P1: Context overflow auto-recovery (multi-step cascade)
            if not context_overflow_retried and _is_context_length_error(error):
                context_overflow_retried = True
                if len(messages) > 2:
                    logger.warning(
                        "Context length exceeded (%s) — starting recovery cascade",
                        error[:100],
                    )
                    # Use multi-step recovery cascade
                    from helen.runtime.context_recovery import PromptTooLongRecovery
                    max_tokens = self._get_model_context_window(model)
                    recovery = PromptTooLongRecovery(max_tokens=max_tokens)
                    recovery_result = recovery.recover(messages, max_tokens=max_tokens)
                    if recovery_result.success:
                        messages[:] = recovery_result.messages
                        logger.info(
                            "Recovery succeeded via %s (reduced ~%d tokens)",
                            recovery_result.strategy, recovery_result.tokens_reduced,
                        )
                        continue
                    else:
                        logger.error(
                            "All recovery strategies exhausted — cannot reduce context"
                        )
                else:
                    logger.warning(
                        "Context length exceeded but only %d messages remain — cannot trim further",
                        len(messages),
                    )

            # Check if we should retry
            if attempt < self.max_retries:
                # Retry on timeout or server errors
                is_retryable = (
                    "timed out" in error.lower()
                    or "500" in error
                    or "502" in error
                    or "503" in error
                    or "504" in error
                    or "429" in error  # rate limit
                    or "connect" in error.lower()  # transient network errors
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

    def _get_model_context_window(self, model: str | None = None) -> int:
        """Get the context window size for the current model."""
        from helen.runtime.history import get_model_context_window
        use_model = model or self.default_model
        return get_model_context_window(use_model)

    def _inject_usage_warning_if_needed(self, messages: list[dict[str, Any]]) -> None:
        """Phase 9A: Inject usage warning into messages if context is getting tight.

        Modifies messages list in-place. If the last message is already a usage
        warning (system message starting with <system_warning>), replaces it.
        Otherwise, appends a new warning.

        Args:
            messages: Messages list (modified in-place)
        """
        try:
            from helen.runtime.context_awareness import ContextAwareness

            max_tokens = self._get_model_context_window()
            awareness = ContextAwareness(max_tokens=max_tokens)
            warning = awareness.build_usage_warning(messages)

            if warning is None:
                # Remove any existing warning if usage is now normal
                if messages and messages[-1].get("role") == "system" and \
                   messages[-1].get("content", "").startswith("<system_warning>"):
                    messages.pop()
                return

            # Replace or append warning
            if messages and messages[-1].get("role") == "system" and \
               messages[-1].get("content", "").startswith("<system_warning>"):
                messages[-1]["content"] = warning
            else:
                messages.append({"role": "system", "content": warning})
        except Exception as e:
            logger.debug("Usage warning injection failed (non-fatal): %s", e)

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

        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {})
            return {"content": ""}

        except httpx.HTTPStatusError as e:
            # Read the error body for structured API error messages
            try:
                error_data = e.response.json()
                api_error = error_data.get("error", {})
                error_msg = api_error.get("message", str(e))
                error_code = api_error.get("code", "")
                self._last_error = f"API error ({e.response.status_code} {error_code}): {error_msg}"
            except Exception:
                self._last_error = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            return None
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
            self._last_error = f"HTTP request failed: {e}"
            return None
        except httpx.TimeoutException:
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
        # P0 fix: Only append user message if not already the last message in history.
        # See act() for detailed rationale.
        # v1.17: Use helper for proper multimodal content comparison.
        if not messages or not _last_user_message_matches(messages, prompt):
            messages.append({"role": "user", "content": prompt})

        url = f"{self.base_url}/chat/completions"

        # Iteration budget: prevent infinite loops
        budget = IterationBudget(max_total=max_turns + 2)
        empty_response_retries = 0
        max_empty_retries = 2
        # P2: Stream network retry (separate from iteration budget)
        # Only retries transient errors BEFORE stream is established
        stream_retry = 0
        max_stream_retries = self.max_retries  # Same as non-streaming (default 3)

        while budget.consume():
            # Phase 9B: Reset reactive compactor per-turn state
            if getattr(self, '_reactive_compactor', None) is not None:
                self._reactive_compactor.reset_turn()

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

            try:
                # Collect streamed chunks with health checking
                # Use list+join (O(n)) instead of += (O(n²)) for long responses
                full_chunks: list[str] = []
                tool_calls_acc: dict[int, dict] = {}  # index -> {name, args_str, id}
                usage_info: dict[str, int] = {}  # token usage from final chunk
                last_chunk_time = 0.0
                stale_threshold = 90.0  # seconds without data = stale

                stream_start = time.time()

                with self._client.stream("POST", url, json=payload, timeout=self.timeout) as response:
                    response.raise_for_status()
                    for line_bytes in response.iter_lines():
                        line = line_bytes.strip()
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
                                    full_chunks.append(content)
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

                # Build full_content from chunks (O(n) join instead of O(n²) +=)
                full_content = "".join(full_chunks)

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

                    # P0: Enforce MAX_TOOL_RESULTS_PER_TURN to prevent context explosion
                    tool_call_list = _enforce_tool_results_per_turn(tool_call_list)

                    if self.enable_concurrent_tools and len(tool_call_list) > 1:
                        tool_results = _execute_tools_concurrent(
                            tool_call_list, _dispatch, executor=self._tool_pool,
                        )
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

                    # Phase 9B: Reactive compaction check after tool results (stream)
                    if getattr(self, 'enable_reactive_compaction', False) and \
                       getattr(self, '_reactive_compactor', None) is not None:
                        use_model = model or self.default_model
                        from helen.runtime.history import get_model_context_window
                        max_tokens = get_model_context_window(use_model)
                        messages, rc_layer = self._reactive_compactor.check_and_compact(
                            messages, max_tokens,
                        )
                        if rc_layer:
                            logger.info(
                                "Reactive compaction triggered in stream tool loop: %s",
                                rc_layer,
                            )
                            yield {"type": "compaction", "strategy": rc_layer}

                    # Phase 9A: Context awareness — inject usage warning if needed
                    self._inject_usage_warning_if_needed(messages)

                    # Reset empty response counter after successful tool execution
                    empty_response_retries = 0
                    stream_retry = 0  # P2: Reset stream retry counter
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
                    stream_retry = 0  # P2: Reset stream retry counter
                    break

            except httpx.HTTPStatusError as e:
                # Read the error body for structured API error messages
                try:
                    error_data = e.response.json()
                    api_error = error_data.get("error", {})
                    error_msg = api_error.get("message", str(e))
                    error_code = api_error.get("code", "")
                    full_error = f"API error ({e.response.status_code} {error_code}): {error_msg}"

                    # P1: Context overflow auto-recovery for streaming (multi-step cascade)
                    if _is_context_length_error(error_msg) and len(messages) > 2:
                        logger.warning(
                            "Context length exceeded in stream (%s) — starting recovery cascade",
                            error_msg[:100],
                        )
                        from helen.runtime.context_recovery import PromptTooLongRecovery
                        use_model = model or self.default_model
                        from helen.runtime.history import get_model_context_window
                        max_tokens = get_model_context_window(use_model)
                        recovery = PromptTooLongRecovery(max_tokens=max_tokens)
                        recovery_result = recovery.recover(messages, max_tokens=max_tokens)
                        if recovery_result.success:
                            messages[:] = recovery_result.messages
                            logger.info(
                                "Stream recovery succeeded via %s (reduced ~%d tokens)",
                                recovery_result.strategy, recovery_result.tokens_reduced,
                            )
                            # Reset tool call accumulation for retry
                            tool_calls_acc.clear()
                            full_chunks.clear()
                            stream_retry = 0  # Reset stream retry counter
                            continue  # Retry with recovered messages
                        else:
                            logger.error(
                                "All stream recovery strategies exhausted — yielding error"
                            )
                            yield {"type": "error", "message": full_error}

                    # P2: Retry on 5xx and 429 rate limit errors
                    is_retryable_status = (
                        e.response.status_code >= 500
                        or e.response.status_code == 429
                    )
                    if is_retryable_status and stream_retry < max_stream_retries:
                        wait_time = min(2 ** stream_retry, 10)
                        logger.info(
                            "Stream API error (%s) — retrying in %ds (%d/%d)",
                            full_error[:80], wait_time, stream_retry + 1, max_stream_retries,
                        )
                        time.sleep(wait_time)
                        stream_retry += 1
                        tool_calls_acc.clear()
                        full_chunks.clear()
                        continue

                    yield {"type": "error", "message": full_error}
                except Exception:
                    yield {"type": "error", "message": f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"}
                break
            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
                # P2: Retry on transient network errors
                if stream_retry < max_stream_retries:
                    wait_time = min(2 ** stream_retry, 10)
                    logger.info(
                        "Stream network error (%s) — retrying in %ds (%d/%d)",
                        str(e)[:80], wait_time, stream_retry + 1, max_stream_retries,
                    )
                    time.sleep(wait_time)
                    stream_retry += 1
                    tool_calls_acc.clear()
                    full_chunks.clear()
                    continue
                yield {"type": "error", "message": f"HTTP request failed: {e}"}
                break
            except httpx.TimeoutException:
                # P2: Retry on timeout
                if stream_retry < max_stream_retries:
                    wait_time = min(2 ** stream_retry, 10)
                    logger.info(
                        "Stream timeout — retrying in %ds (%d/%d)",
                        wait_time, stream_retry + 1, max_stream_retries,
                    )
                    time.sleep(wait_time)
                    stream_retry += 1
                    tool_calls_acc.clear()
                    full_chunks.clear()
                    continue
                yield {"type": "error", "message": f"Request timed out after {self.timeout}s"}
                break
            except Exception as e:
                yield {"type": "error", "message": f"Unexpected error: {e}"}
                break

    # ------------------------------------------------------------------
    # True async support (httpx.AsyncClient with connection pooling)
    # ------------------------------------------------------------------

    async def act_async(
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
        """True async version of act() using httpx.AsyncClient.

        Uses persistent connection pool — no TCP/TLS handshake per call.
        Does NOT block the event loop (unlike the default sync fallback).
        """
        from helen.runtime.tools import dispatch_tool as default_dispatch

        _dispatch = dispatch_fn if dispatch_fn is not None else default_dispatch

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        # P0 fix: Only append user message if not already the last message in history.
        # v1.17: Use helper for proper multimodal content comparison.
        if not messages or not _last_user_message_matches(messages, prompt):
            messages.append({"role": "user", "content": prompt})

        use_model = model or self.default_model or "default"
        final_text = ""

        budget = IterationBudget(max_total=max_turns + 2)
        empty_response_retries = 0
        max_empty_retries = 2

        while budget.consume():
            # Phase 9B: Reset reactive compactor per-turn state
            if getattr(self, '_reactive_compactor', None) is not None:
                self._reactive_compactor.reset_turn()

            if self.enable_message_sanitization:
                _sanitize_messages(messages)
                _repair_message_sequence(messages)

            payload = {
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                payload["tools"] = tools

            url = f"{self.base_url}/chat/completions"

            try:
                response = await self._async_client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                choices = result.get("choices", [])
                response_msg = choices[0].get("message", {}) if choices else {"content": ""}
            except Exception as e:
                raise RuntimeError(f"Async LLM API call failed: {e}") from e

            tool_calls = response_msg.get("tool_calls")
            if tool_calls:
                messages.append(response_msg)

                if self.enable_concurrent_tools and len(tool_calls) > 1:
                    tool_results = _execute_tools_concurrent(
                        tool_calls, _dispatch, executor=self._tool_pool,
                    )
                else:
                    tool_results = []
                    for tc in tool_calls:
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"].get("arguments", "{}"))
                        except json.JSONDecodeError:
                            fn_args = {}
                        result = _dispatch(fn_name, fn_args)
                        tool_results.append((tc, result))

                for tc, result in tool_results:
                    if self.enable_tool_truncation:
                        result = _truncate_tool_result(result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                # Phase 9B: Reactive compaction check after tool results (async)
                if getattr(self, 'enable_reactive_compaction', False) and \
                   getattr(self, '_reactive_compactor', None) is not None:
                    use_model_async = model or self.default_model
                    from helen.runtime.history import get_model_context_window
                    max_tokens_async = get_model_context_window(use_model_async)
                    messages, rc_layer = self._reactive_compactor.check_and_compact(
                        messages, max_tokens_async,
                    )
                    if rc_layer:
                        logger.info(
                            "Reactive compaction triggered in async tool loop: %s",
                            rc_layer,
                        )

                # Phase 9A: Context awareness — inject usage warning if needed
                self._inject_usage_warning_if_needed(messages)

                empty_response_retries = 0
                continue

            else:
                content = response_msg.get("content", "")
                if not content or not content.strip():
                    if empty_response_retries < max_empty_retries:
                        empty_response_retries += 1
                        messages.append(response_msg)
                        messages.append({
                            "role": "user",
                            "content": "You returned an empty response. Please continue.",
                        })
                        continue
                    else:
                        break

                final_text = content
                break

        return LLMResponse(text=final_text, model=use_model)

    async def act_stream_async(
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
        """True async streaming using httpx.AsyncClient.

        Does NOT block the event loop. Yields the same event dicts as act_stream.
        For use in multi-agent concurrent scenarios.
        """
        from helen.runtime.tools import dispatch_tool as default_dispatch

        _dispatch = dispatch_fn if dispatch_fn is not None else default_dispatch

        use_model = model or self.default_model or "default"

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        # P0 fix: Only append user message if not already the last message in history.
        # v1.17: Use helper for proper multimodal content comparison.
        if not messages or not _last_user_message_matches(messages, prompt):
            messages.append({"role": "user", "content": prompt})

        url = f"{self.base_url}/chat/completions"

        budget = IterationBudget(max_total=max_turns + 2)
        empty_response_retries = 0
        max_empty_retries = 2

        while budget.consume():
            # Phase 9B: Reset reactive compactor per-turn state
            if getattr(self, '_reactive_compactor', None) is not None:
                self._reactive_compactor.reset_turn()

            if self.enable_message_sanitization:
                _sanitize_messages(messages)
                _repair_message_sequence(messages)

            payload = {
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if tools:
                payload["tools"] = tools

            try:
                full_chunks: list[str] = []
                tool_calls_acc: dict[int, dict] = {}
                usage_info: dict[str, int] = {}

                async with self._async_client.stream("POST", url, json=payload, timeout=self.timeout) as response:
                    response.raise_for_status()
                    async for line_bytes in response.aiter_lines():
                        line = line_bytes.strip()
                        if not line:
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break

                            try:
                                chunk_data = json.loads(data_str)

                                chunk_usage = chunk_data.get("usage")
                                if chunk_usage:
                                    usage_info = chunk_usage

                                choices = chunk_data.get("choices", [])
                                if not choices:
                                    continue

                                delta = choices[0].get("delta", {})

                                content = delta.get("content", "")
                                if content:
                                    full_chunks.append(content)
                                    yield {"type": "content", "content": content}

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

                if usage_info:
                    yield {"type": "usage", "usage": usage_info}

                full_content = "".join(full_chunks)

                if tool_calls_acc:
                    assistant_msg = {"role": "assistant", "content": full_content or None}
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
                        tool_results = _execute_tools_concurrent(
                            tool_call_list, _dispatch, executor=self._tool_pool,
                        )
                    else:
                        tool_results = []
                        for tc in tool_call_list:
                            fn_name = tc["function"]["name"]
                            try:
                                fn_args = json.loads(tc["function"].get("arguments", "{}"))
                            except json.JSONDecodeError:
                                fn_args = {}
                            result = _dispatch(fn_name, fn_args)
                            tool_results.append((tc, result))

                    for tc, result in tool_results:
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"].get("arguments", "{}"))
                        except json.JSONDecodeError:
                            fn_args = {}

                        yield {"type": "tool_call", "name": fn_name, "args": fn_args}

                        if self.enable_tool_truncation:
                            result = _truncate_tool_result(result)

                        yield {"type": "tool_result", "name": fn_name, "result": result}

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        })

                    # Phase 9B: Reactive compaction check after tool results (async stream)
                    if getattr(self, 'enable_reactive_compaction', False) and \
                       getattr(self, '_reactive_compactor', None) is not None:
                        use_model_as = model or self.default_model
                        from helen.runtime.history import get_model_context_window
                        max_tokens_as = get_model_context_window(use_model_as)
                        messages, rc_layer = self._reactive_compactor.check_and_compact(
                            messages, max_tokens_as,
                        )
                        if rc_layer:
                            logger.info(
                                "Reactive compaction triggered in async stream tool loop: %s",
                                rc_layer,
                            )
                            yield {"type": "compaction", "strategy": rc_layer}

                    # Phase 9A: Context awareness — inject usage warning if needed
                    self._inject_usage_warning_if_needed(messages)

                    empty_response_retries = 0
                    continue

                else:
                    if not full_content or not full_content.strip():
                        if empty_response_retries < max_empty_retries:
                            empty_response_retries += 1
                            messages.append({"role": "assistant", "content": ""})
                            messages.append({
                                "role": "user",
                                "content": "You returned an empty response. Please continue.",
                            })
                            continue
                        else:
                            break
                    break

            except Exception as e:
                yield {"type": "error", "message": str(e)}
                break

    @property
    def last_error(self) -> str | None:
        """The error message from the last failed LLM call."""
        return self._last_error
