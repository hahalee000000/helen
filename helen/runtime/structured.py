"""Structured output for LLM function calling in the Helen language.

Generates and parses function calling schemas for llm if (route) statements,
following HLD 3.6.6 and 3.13.
"""

from __future__ import annotations

from typing import Any


class StructuredOutput:
    """LLM structured output generation and parsing.

    Generates function calling schemas for route operations
    and parses LLM responses to extract validated branch names.
    """

    @staticmethod
    def build_route_schema(branches: list[str]) -> dict[str, Any]:
        """Generate function calling schema for llm if routing.

        Args:
            branches: List of available branch names.

        Returns:
            A function calling schema dict with enum constraint on the
            'branch' parameter (HLD 3.6.6 ROUTE_FUNCTION_SCHEMA).
        """
        return {
            "type": "function",
            "function": {
                "name": "classify",
                "description": "Classify input into the most appropriate branch",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "branch": {
                            "type": "string",
                            "enum": list(branches),
                            "description": "The selected branch name",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Classification confidence 0.0-1.0",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Reasoning for the classification (optional)",
                        },
                    },
                    "required": ["branch"],
                },
            },
        }

    @staticmethod
    def parse_route_response(response: dict[str, Any] | None, branches: list[str]) -> str | None:
        """Parse an LLM route response and validate against available branches.

        Args:
            response: The parsed JSON response from the LLM.
            branches: List of valid branch names.

        Returns:
            The validated branch name, or None if parsing/validation failed.
        """
        if response is None:
            return None

        # Extract branch from function calling response
        branch = None
        if isinstance(response, dict):
            # Direct function calling response: {"branch": "query", ...}
            branch = response.get("branch")
            # Or nested: {"arguments": {"branch": "query"}}
            if branch is None and "arguments" in response:
                args = response["arguments"]
                if isinstance(args, dict):
                    branch = args.get("branch")

        # Validate: branch must be in the enum
        if branch is not None and branch in branches:
            return branch
        return None

    @staticmethod
    def build_route_prompt(description: str, branches: list[str],
                           context: str | None = None) -> str:
        """Build the routing prompt for llm if (HLD 3.6.6).

        Args:
            description: The routing description.
            branches: List of branch names.
            context: Optional conversation summary.

        Returns:
            The full prompt string.
        """
        prompt = (
            f"Given the following context and options, classify into exactly ONE branch:\n\n"
            f"Description: {description}\n"
        )
        if context:
            prompt += f"Context: {context}\n"
        prompt += f"Available branches: {', '.join(branches)}\n\n"
        prompt += "Return your classification using the classify function."
        return prompt
