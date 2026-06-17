"""Hermes CLI-based LLM runtime for the Helen language (HLD §3.6.5, §3.8.1).

Provides a concrete LLMRuntime implementation that delegates LLM calls
to the Hermes Agent CLI (`hermes` command). This enables Helen programs
to use real LLM inference without requiring direct API keys.

Usage:
    from helen.runtime.hermes_cli_llm import HermesCLILLMRuntime
    runtime = HermesCLILLMRuntime()
    response = runtime.act("Translate: hello")
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any

from helen.runtime.llm_runtime import LLMResponse, LLMRuntime


@dataclass
class HermesCLILLMRuntime(LLMRuntime):
    """LLM runtime that delegates to the Hermes Agent CLI.

    Uses `hermes chat` or `hermes ask` to send prompts to the configured
    LLM backend. This approach:
    - Reuses the user's existing Hermes configuration (model, API keys)
    - Supports all Hermes features (skills, tools, memory)
    - Requires the `hermes` CLI to be installed and configured

    Args:
        hermes_path: Path to the hermes CLI binary. Defaults to "hermes".
        default_model: Model to use if not specified in the call.
        timeout: Maximum seconds to wait for an LLM response.

    Raises:
        FileNotFoundError: If the hermes CLI is not found.
    """

    hermes_path: str = "hermes"
    default_model: str | None = None
    timeout: int = 120
    _last_error: str | None = field(default=None, repr=False)

    # ── LLMRuntime interface ───────────────────────────────────

    def route(
        self,
        description: str,
        branches: list[str],
        context: str | None = None,
    ) -> str | None:
        """Route input to one of the given branches via LLM.

        Constructs a classification prompt and asks the LLM to pick
        the best matching branch.

        Args:
            description: The routing context.
            branches: Available branch names.
            context: Optional additional context.

        Returns:
            The selected branch name, or None if classification failed.
        """
        branch_list = ", ".join(branches)
        prompt = (
            f"{description}\n"
            f"Available branches: {branch_list}\n"
            f"Reply with ONLY the branch name that best matches.\n"
        )
        if context:
            prompt += f"\nContext: {context}\n"

        response = self._ask(prompt)
        if response is None:
            return None

        # Try to match the response to a valid branch
        cleaned = response.strip().strip('"').strip("'").lower()
        for branch in branches:
            if cleaned == branch.lower() or cleaned.startswith(branch.lower()):
                return branch

        # Return the first branch as fallback
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
        """Execute an autonomous LLM action.

        Sends the prompt to the LLM and returns the response.

        Args:
            prompt: The prompt text.
            tools: Tool schemas (not yet supported via CLI).
            model: Model override.
            temperature: Sampling temperature.
            max_turns: Maximum interaction turns.
            history: Conversation history (not yet supported via CLI).
            system_prompt: System prompt (prepended to prompt if provided).

        Returns:
            An LLMResponse with the text content.
        """
        # Hermes CLI doesn't support separate system prompt, so prepend it
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        response = self._ask(full_prompt, model=model)
        return LLMResponse(
            text=response or "",
            model=model or self.default_model or "hermes-cli",
        )

    # ── Internal ───────────────────────────────────────────────

    def _ask(self, prompt: str, model: str | None = None) -> str | None:
        """Send a prompt to the hermes CLI and return the response.

        Args:
            prompt: The prompt text.
            model: Optional model override.

        Returns:
            The response text, or None on failure.
        """
        cmd = [self.hermes_path, "-z", prompt]
        if model:
            cmd.extend(["-m", model])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if result.returncode != 0:
                self._last_error = result.stderr.strip()
                return None

            # hermes -z outputs plain text response directly
            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            self._last_error = f"LLM call timed out after {self.timeout}s"
            return None
        except FileNotFoundError:
            self._last_error = f"Hermes CLI not found at '{self.hermes_path}'"
            return None
        except OSError as e:
            self._last_error = f"Hermes CLI error: {e}"
            return None

    @property
    def last_error(self) -> str | None:
        """The error message from the last failed LLM call."""
        return self._last_error
