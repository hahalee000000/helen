"""HTTP-based LLM runtime using OpenAI-compatible API.

Connects to OpenAI-compatible endpoints (e.g., DashScope, OpenAI, etc.) for fast
LLM calls without spawning subprocess each time.

Supports function calling: when tools are provided, the runtime enters a
loop where the LLM can request tool calls, which are executed and their
results fed back to the LLM until it produces a final text response.

Usage:
    from helen.runtime.http_llm import HttpLLMRuntime
    runtime = HttpLLMRuntime()  # Auto-loads from ~/.helen/config.yaml or ~/.hermes/.env
    response = runtime.act("Translate: hello")
    response = runtime.act("Search for Python docs", tools=[...])
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any

from helen.runtime.llm_runtime import LLMResponse, LLMRuntime


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


@dataclass
class HttpLLMRuntime(LLMRuntime):
    """HTTP-based LLM runtime using OpenAI-compatible API.

    Connects to a persistent HTTP server for fast LLM calls.
    Avoids subprocess overhead by reusing HTTP connections.

    Args:
        base_url: Base URL of the OpenAI-compatible API
        api_key: API key for authentication
        default_model: Default model to use
        timeout: Request timeout in seconds
    """

    base_url: str = ""
    api_key: str = ""
    default_model: str | None = None
    timeout: int = 120
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
    ) -> LLMResponse:
        """Execute an autonomous LLM action with optional function calling.

        When tools are provided, enters a loop: LLM may request tool calls,
        which are executed and fed back until the LLM produces a final text
        response or max_turns is reached.
        """
        from helen.runtime.tools import dispatch_tool

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        use_model = model or self.default_model or "default"
        final_text = ""

        for turn in range(max_turns + 1):  # +1 for final nudge response
            response_msg = self._chat_with_messages(
                messages, model=use_model, temperature=temperature, tools=tools,
            )
            if response_msg is None:
                break

            # Check if LLM wants tool calls
            tool_calls = response_msg.get("tool_calls")
            if tool_calls and turn < max_turns:
                # Append assistant message with tool_calls
                messages.append(response_msg)
                # Execute each tool call and append results
                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"].get("arguments", "{}"))
                    except json.JSONDecodeError:
                        fn_args = {}
                    result = dispatch_tool(fn_name, fn_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
                # If this is the last tool turn, nudge LLM to produce final answer
                if turn >= max_turns - 1:
                    messages.append({
                        "role": "user",
                        "content": "Based on the tool results above, please provide your final answer now. Do not make more tool calls.",
                    })
                # Continue loop — LLM will see tool results
                continue
            else:
                # No tool calls (or exhausted turns) — this is the final text response
                final_text = response_msg.get("content", "")
                break

        return LLMResponse(
            text=final_text,
            model=use_model,
        )

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
    ):
        """Stream LLM response with full tool-calling loop.

        Yields event dicts:
            {"type": "content", "content": "..."}     — text chunk
            {"type": "tool_call", "name": "...", "args": {...}}  — tool invocation
            {"type": "tool_result", "name": "...", "result": "..."}  — tool result
            {"type": "error", "message": "..."}       — error
        """
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
            # Build streaming request
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
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )

            try:
                # Collect streamed chunks
                full_content = ""
                tool_calls_acc: dict[int, dict] = {}  # index -> {name, args_str, id}

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

    @property
    def last_error(self) -> str | None:
        """The error message from the last failed LLM call."""
        return self._last_error
