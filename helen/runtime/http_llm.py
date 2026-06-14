"""HTTP-based LLM runtime using OpenAI-compatible API.

Connects to OpenAI-compatible endpoints (e.g., DashScope, OpenAI, etc.) for fast
LLM calls without spawning subprocess each time.

Usage:
    from helen.runtime.http_llm import HttpLLMRuntime
    runtime = HttpLLMRuntime()  # Auto-loads from ~/.hermes/.env
    response = runtime.act("Translate: hello")
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from helen.runtime.llm_runtime import LLMResponse, LLMRuntime


def _load_hermes_env() -> dict[str, str]:
    """Load environment variables from ~/.hermes/.env file."""
    env_file = Path.home() / ".hermes" / ".env"
    if not env_file.exists():
        return {}
    
    env_vars = {}
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    
    return env_vars


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
        """Auto-load configuration from ~/.hermes/.env if not provided."""
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

    def choose(
        self,
        description: str,
        options: list[str],
        context: str | None = None,
    ) -> str | None:
        """Choose one option from the list via LLM."""
        option_list = ", ".join(options)
        prompt = (
            f"{description}\n"
            f"Available options: {option_list}\n"
            f"Reply with ONLY the option name you choose.\n"
        )
        if context:
            prompt += f"\nContext: {context}\n"

        response = self._chat(prompt)
        if response is None:
            return None

        # Try to match the response to a valid option
        cleaned = response.strip().strip('"').strip("'").lower()
        for option in options:
            if cleaned == option.lower() or cleaned.startswith(option.lower()):
                return option

        return options[0] if options else None

    def act(
        self,
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 1.0,
        max_turns: int = 1,
        history: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Execute an autonomous LLM action."""
        response = self._chat(prompt, model=model, temperature=temperature)
        return LLMResponse(
            text=response or "",
            model=model or self.default_model or "http-api",
        )

    def _chat(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 1.0,
    ) -> str | None:
        """Send a chat completion request to the API.

        Args:
            prompt: The prompt text.
            model: Optional model override.
            temperature: Sampling temperature.

        Returns:
            The response text, or None on failure.
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model or self.default_model or "default",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

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
                # OpenAI format: {"choices": [{"message": {"content": "..."}}]}
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                return ""

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

    @property
    def last_error(self) -> str | None:
        """The error message from the last failed LLM call."""
        return self._last_error
