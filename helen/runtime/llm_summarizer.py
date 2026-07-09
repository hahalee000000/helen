"""LLM-based semantic compression for context management.

Phase 3: Auto-Compact layer using LLM to generate intelligent summaries.

This module provides the Layer 5 compression that uses the LLM itself
to create high-quality summaries of conversation history.
"""

from __future__ import annotations

import logging
from typing import Callable

from helen.runtime.history import _message_text

logger = logging.getLogger(__name__)


class LLMSummarizer:
    """Generate intelligent summaries of conversation history using LLM.

    This class handles the semantic compression layer (Layer 5) of the
    graduated compression pipeline.
    """

    def __init__(self, llm_client: Callable, model: str = "qwen3.7-plus"):
        """Initialize the LLM summarizer.

        Args:
            llm_client: A callable that accepts messages and returns LLM response.
                        Expected signature: llm_client(messages) -> str
            model: Model name to use for summarization
        """
        self.llm_client = llm_client
        self.model = model

    def summarize(self, history: list, target_tokens: int = 2000) -> str:
        """Generate a structured summary of conversation history.

        Uses the LLM to create an intelligent summary that preserves:
        - Task objectives and goals
        - Key decisions and rationale
        - File modifications and their purpose
        - Completed work
        - Pending tasks
        - Important constraints and patterns

        Args:
            history: List of Message objects to summarize
            target_tokens: Target token count for the summary

        Returns:
            Structured summary text
        """
        if not history:
            return ""

        # Build the summarization prompt
        prompt = self._build_summarization_prompt(history, target_tokens)

        # Call LLM
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a conversation summarizer. Create concise, structured summaries that preserve critical information for continuing the conversation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            summary = self.llm_client(messages)

            logger.info(f"Generated LLM summary: {len(summary)} chars")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate LLM summary: {e}")
            # Fall back to simple summary
            return self._fallback_summary(history)

    def _build_summarization_prompt(self, history: list, target_tokens: int) -> str:
        """Build the prompt for LLM summarization.

        Args:
            history: Conversation history
            target_tokens: Target token count

        Returns:
            Formatted prompt for the LLM
        """
        # Format conversation history for the prompt
        conversation_text = []
        for msg in history:
            role = msg.role
            # v1.17: Use _message_text for multimodal content safety
            content = _message_text(msg.content)

            # Skip system messages in the summary
            if role == "system":
                continue

            # Handle tool results specially
            if role == "tool":
                if msg.compressed:
                    conversation_text.append(f"[Tool result: {msg.tool_call_id or 'unknown'} - cleared]")
                else:
                    # Include first 200 chars of tool result
                    preview = content[:200] + "..." if len(content) > 200 else content
                    conversation_text.append(f"[Tool result: {preview}]")
            else:
                conversation_text.append(f"{role.upper()}: {content}")

        conversation_str = "\n".join(conversation_text)

        # Build the prompt
        prompt = f"""Please summarize the following conversation history.

Target length: ~{target_tokens} tokens (approximately {target_tokens * 4} characters)

Preserve:
- Task objectives and goals
- Key decisions and their rationale
- File modifications and their purpose
- Completed work items
- Pending tasks
- Important constraints, patterns, or error messages

Discard:
- Repetitive exploration attempts
- Detailed intermediate outputs
- Outdated temporary data
- Verbose explanations that can be inferred

Output format:
## Task Objective
[What the user is trying to accomplish]

## Key Decisions
- [Decision 1 and rationale]
- [Decision 2 and rationale]

## File Changes
- path/to/file.py: [What was changed and why]

## Completed
- [Completed item 1]
- [Completed item 2]

## Pending
- [ ] [Pending item 1]
- [ ] [Pending item 2]

## Important Notes
- [Constraint, pattern, or error to remember]

---

Conversation History:
{conversation_str}
"""
        return prompt

    def _fallback_summary(self, history: list) -> str:
        """Generate a simple fallback summary when LLM fails.

        Args:
            history: Conversation history

        Returns:
            Simple summary text
        """
        user_msgs = [m for m in history if m.role == "user"]
        assistant_msgs = [m for m in history if m.role == "assistant"]
        tool_msgs = [m for m in history if m.role == "tool"]

        summary = f"""[Conversation Summary - Auto-generated fallback]

Turns: {len(user_msgs)} user, {len(assistant_msgs)} assistant, {len(tool_msgs)} tool
Total messages: {len(history)}

This is a simplified summary because LLM summarization failed.
The conversation has been compressed to save context window space.
"""
        return summary
