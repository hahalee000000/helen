"""LLM-based semantic compression for context management.

Phase 3: Auto-Compact layer using LLM to generate intelligent summaries.

This module provides the Layer 5 compression that uses the LLM itself
to create high-quality summaries of conversation history.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

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
            content = msg.content

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


def auto_compact(history: list, llm_client: Callable, target_tokens: int = 2000) -> list:
    """Auto-compact layer for graduated compression pipeline.

    This is the Layer 5 compression that uses LLM to generate intelligent summaries.

    Args:
        history: Conversation history to compress
        llm_client: LLM client for generating summaries
        target_tokens: Target token count for the summary

    Returns:
        Compressed history with summary message at the start
    """
    if not history:
        return history

    # Create summarizer
    summarizer = LLMSummarizer(llm_client)

    # Generate summary
    summary_text = summarizer.summarize(history, target_tokens)

    # Create a summary message
    from helen.runtime.history import Message

    summary_msg = Message(
        role="system",
        content=f"[Previous conversation summary - LLM generated]\n\n{summary_text}",
        tool_calls=[],
        tool_call_id=None,
        _token_count=0,  # Will be calculated
        _model=None,
        message_type="system",
        priority=100,
        compressed=False,
    )

    # Mark all old messages as compressed
    compressed_history = []
    for msg in history:
        msg_copy = Message(
            role=msg.role,
            content=msg.content,
            tool_calls=msg.tool_calls,
            tool_call_id=msg.tool_call_id,
            _token_count=msg._token_count,
            _model=msg._model,
            message_type=getattr(msg, 'message_type', None),
            priority=getattr(msg, 'priority', 50),
            compressed=True,  # Mark as compressed
        )
        compressed_history.append(msg_copy)

    # Return: summary + compressed history
    # The HistoryManager will decide whether to keep the compressed history or discard it
    return [summary_msg] + compressed_history


def calculate_next_compaction_threshold(current_usage: float, max_tokens: int) -> float:
    """Calculate the next compaction threshold using the 60% rule.

    The 60% rule prevents "compact-then-compact-again" loops:
    - After compaction, usage = 30% of capacity
    - Next compaction triggers at: 30% + 60% × 70% = 72% of capacity

    Args:
        current_usage: Current token usage
        max_tokens: Maximum context window tokens

    Returns:
        Next compaction threshold (in tokens)
    """
    # After compaction, assume we're at ~30% capacity
    post_compaction_usage = 0.30 * max_tokens

    # Next compaction triggers at 60% of remaining capacity
    # Remaining capacity = max_tokens - post_compaction_usage
    # 60% of remaining = 0.60 * (max_tokens - post_compaction_usage)
    next_threshold = post_compaction_usage + 0.60 * (max_tokens - post_compaction_usage)

    return next_threshold
