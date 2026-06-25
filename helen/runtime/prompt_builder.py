"""Prompt Builder for Helen (HLD 3.7).

Handles template rendering, Skill Index injection (Tier 1), and
System/User prompt construction for LLM calls.
"""

from __future__ import annotations

import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from helen.runtime import Runtime, SkillMeta
    from helen.core.ast import AgentDeclNode


# Regex to match {{var_name}} templates
_TEMPLATE_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class PromptBuilder:
    """Build and render prompts for LLM calls (HLD 3.7).

    Features:
    - Single-pass template rendering ({{var}} substitution in prompt blocks)
    - Skill Index Tier 1 injection (lightweight name + description)
    - System/User prompt assembly from AgentDeclNode
    """

    def __init__(self, runtime: "Runtime") -> None:
        self._runtime = runtime

    def render(self, template: str, env: dict[str, object]) -> str:
        """Render {{var}} placeholders in a template string (single pass).

        Only renders in prompt blocks — plain strings with {{}} are left
        untouched to prevent accidental template injection.

        Per HLD 3.7.2:
        - {{var}} rendering only applies in prompt triple-quote blocks
        - Template rendering is one-time; rendered {{...}} is NOT re-rendered
        - Undefined variables: keep original placeholder text
        """
        def _replacer(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name in env:
                value = env[var_name]
                # Convert value to string without re-rendering
                if value is None:
                    return "null"
                if isinstance(value, bool):
                    return "true" if value else "false"
                return str(value)
            # Undefined: keep original placeholder
            return match.group(0)

        return _TEMPLATE_RE.sub(_replacer, template)

    def build_system_prompt(self, agent_decl: "AgentDeclNode") -> str:
        """Build the System Prompt for an agent (HLD 3.7.1).

        Components:
        1. Agent description
        2. Skill Index Tier 1 (<available_skills>)
        3. Tool schemas (including load_skill)

        Per HLD 3.7.1 progressive disclosure:
        - Tier 1: Skill Index (lightweight) in System Prompt
        - Tier 2: Full SKILL.md loaded on-demand via load_skill tool
        """
        parts = []

        # 1. Agent description
        for decl in agent_decl.declarations:
            if decl.description is not None:
                from helen.core.ast import LiteralNode
                if isinstance(decl.description, LiteralNode):
                    parts.append(decl.description.value)
                    break

        # 2. Skill Index (Tier 1)
        skill_index = self.build_skill_index()
        if skill_index:
            parts.append(skill_index)

        return "\n\n".join(parts)

    def build_user_prompt(
        self, agent_decl: "AgentDeclNode", context: str | None = None
    ) -> str:
        """Build the User Prompt for an agent.

        Renders the agent's prompt template with current environment
        variables and optional conversation context.

        Args:
            agent_decl: The parsed agent declaration.
            context: Optional conversation summary.

        Returns:
            Rendered User Prompt string.
        """
        # Get prompt content from agent declaration
        if agent_decl.prompt is None:
            return ""

        template = agent_decl.prompt.content

        # Build env from agent declarations
        env: dict[str, object] = {}
        for decl in agent_decl.declarations:
            from helen.core.ast import LiteralNode
            field_map = {
                "description": "description",
                "model": "model",
                "temperature": "temperature",
                "max_turns": "max_turns",
            }
            for field_name, var_name in field_map.items():
                value = getattr(decl, field_name, None)
                if value is not None and isinstance(value, LiteralNode):
                    env[var_name] = value.value

        # Inject _memory_content if available
        if "_memory_content" not in env:
            env["_memory_content"] = ""

        # Inject context
        if context is not None:
            env["conversation_summary"] = context

        return self.render(template, env)

    def build_route_prompt(
        self, description: str, branches: list[str], context: str | None = None
    ) -> str:
        """Build prompt for llm if routing (HLD 3.6.6)."""
        prompt = (
            f"Given the following context and options, classify into exactly ONE branch:\n\n"
            f"Description: {description}\n"
        )
        if context:
            prompt += f"Context: {context}\n"
        prompt += f"Available branches: {', '.join(branches)}\n\n"
        prompt += "Return your classification using the classify function."
        return prompt

    def build_skill_index(self) -> str:
        """Build the Tier 1 Skill Index for System Prompt injection.

        Scans skills via runtime.list_skills() and formats as
        <available_skills> XML block with name + description + category + tags.
        """
        skills = self._runtime.list_skills()
        if not skills:
            return ""

        # Group by category
        by_category: dict[str, list[SkillMeta]] = {}
        for s in skills:
            by_category.setdefault(s.category or "uncategorized", []).append(s)

        lines = ["<available_skills>"]
        lines.append("Before replying, scan skills below. If relevant,")
        lines.append("use load_skill tool to load full content.")
        lines.append("")

        for category, skill_list in sorted(by_category.items()):
            lines.append(f"  {category}:")
            for s in skill_list:
                tag_str = f" (tags: {', '.join(s.tags)})" if s.tags else ""
                lines.append(f"    - {s.name}: {s.description}{tag_str}")

        lines.append("</available_skills>")
        return "\n".join(lines)
