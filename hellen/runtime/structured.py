"""Structured output for LLM function calling in the Hellen language.

Generates and parses function calling schemas for llm if (route) and
llm choose (choose) statements, following HLD 3.6.6 and 3.13.
"""

from __future__ import annotations

from typing import Any


class StructuredOutput:
    """LLM structured output generation and parsing.

    Generates function calling schemas for route/choose operations
    and parses LLM responses to extract validated branch/option names.
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
    def build_choose_schema(options: list[str]) -> dict[str, Any]:
        """Generate function calling schema for llm choose.

        Args:
            options: List of available option names.

        Returns:
            A function calling schema dict with enum constraint on the
            'option' parameter.
        """
        return {
            "type": "function",
            "function": {
                "name": "select",
                "description": "Select the most appropriate option",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "option": {
                            "type": "string",
                            "enum": list(options),
                            "description": "The selected option name",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Selection confidence 0.0-1.0",
                        },
                    },
                    "required": ["option"],
                },
            },
        }

    @staticmethod
    def parse_choose_response(response: dict[str, Any] | None, options: list[str]) -> str | None:
        """Parse an LLM choose response and validate against available options.

        Args:
            response: The parsed JSON response from the LLM.
            options: List of valid option names.

        Returns:
            The validated option name, or None if parsing/validation failed.
        """
        if response is None:
            return None

        # Extract option from function calling response
        option = None
        if isinstance(response, dict):
            option = response.get("option")
            if option is None and "arguments" in response:
                args = response["arguments"]
                if isinstance(args, dict):
                    option = args.get("option")

        # Validate: option must be in the enum
        if option is not None and option in options:
            return option
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

    @staticmethod
    def build_choose_prompt(description: str, options: list[str],
                            context: str | None = None) -> str:
        """Build the choice prompt for llm choose.

        Args:
            description: The choice description.
            options: List of option names.
            context: Optional context string.

        Returns:
            The full prompt string.
        """
        prompt = (
            f"Given the following context and options, select exactly ONE:\n\n"
            f"Description: {description}\n"
        )
        if context:
            prompt += f"Context: {context}\n"
        prompt += f"Available options: {', '.join(options)}\n\n"
        prompt += "Return your selection using the select function."
        return prompt
