"""Prompt Builder for Helen (HLD 3.7).

Handles template rendering, Skill Index injection (Tier 1), and
System/User prompt construction for LLM calls.

P2 unification: This module is now the single source of truth for
prompt construction. LlmMixin uses PromptBuilder for:
- Template rendering (with nested variable access)
- Skill Index construction (with mtime-based caching)
- System/User prompt assembly

Previously, llm_mixin.py had its own inline implementations of these
features. They are now consolidated here for maintainability.
"""

from __future__ import annotations

import os
import re

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helen.runtime import Runtime, SkillMeta
    from helen.core.ast import AgentDeclNode


# Regex to match {{var_name}} or {{var.path}} templates (supports nested access)
_TEMPLATE_RE = re.compile(r"\{\{\s*(\w+(?:\.\w+)*)\s*\}\}")

# Max description length in skill index (tokens are limited)
_SKILL_DESC_MAX_LEN = 100


class PromptBuilder:
    """Build and render prompts for LLM calls (HLD 3.7).

    Features:
    - Single-pass template rendering ({{var}} and {{a.b.c}} substitution)
    - Skill Index Tier 1 injection (lightweight name + description + tags)
    - System/User prompt assembly from AgentDeclNode
    - mtime-based Skill Index caching (avoid rebuilding on every call)
    """

    def __init__(self, runtime: "Runtime | None" = None) -> None:
        self._runtime = runtime
        # Skill index cache (mtime-based)
        self._skill_index_cache: str | None = None
        self._skill_index_mtime: float = 0.0
        self._skill_dirs: list[str] = []

    def set_skill_dirs(self, dirs: list[str]) -> None:
        """Set skill directories for mtime-based cache invalidation.

        Args:
            dirs: List of skill directory paths to monitor.
        """
        self._skill_dirs = dirs

    def render(self, template: str, env: dict[str, Any] | Any = None) -> str:
        """Render {{var}} placeholders in a template string (single pass).

        Supports nested attribute access: {{settings.model}} looks up
        env["settings"]["model"] or env.settings.model.

        Per HLD 3.7.2:
        - {{var}} rendering only applies in prompt blocks
        - Template rendering is one-time; rendered {{...}} is NOT re-rendered
        - Undefined variables: keep original placeholder text

        Args:
            template: Template string with {{var}} placeholders.
            env: Dict-like object or object with attribute access for variable lookup.
                 Can be a plain dict, an Environment object, or any object supporting
                 key/attribute access.

        Returns:
            Rendered template string.
        """
        def _replacer(match: re.Match) -> str:
            var_path = match.group(1).strip()
            parts = var_path.split(".")
            # Lookup the first part
            try:
                if isinstance(env, dict):
                    value = env.get(parts[0])
                elif env is not None:
                    # Support Environment.lookup() method (Helen interpreter)
                    if hasattr(env, 'lookup') and callable(env.lookup):
                        try:
                            value = env.lookup(parts[0])
                        except (NameError, KeyError):
                            return match.group(0)
                    elif hasattr(env, '__getitem__'):
                        try:
                            value = env[parts[0]]
                        except (KeyError, TypeError):
                            return match.group(0)
                    else:
                        value = getattr(env, parts[0], None)
                else:
                    return match.group(0)
            except Exception:
                return match.group(0)

            # Navigate nested attributes
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    value = None
                    break

            if value is None:
                return match.group(0)  # Keep original if not found

            # Convert to string
            if isinstance(value, bool):
                return "true" if value else "false"
            return str(value)

        return _TEMPLATE_RE.sub(_replacer, template)

    def build_system_prompt(self, agent_decl: "AgentDeclNode") -> str:
        """Build the System Prompt for an agent (HLD 3.7.1).

        P2: System/User role separation.
        System prompt contains: framework instructions, Helen conventions,
        agent description, and skill index. Agent's prompt field is NOT
        included here — it's used as user prompt (task description).

        Components:
        1. Framework instructions (tool use, skills, parallel calls, completion)
        2. Helen language conventions and best practices
        3. Agent description (role definition)
        4. Skill Index Tier 1 (<available_skills>)

        Per HLD 3.7.1 progressive disclosure:
        - Tier 1: Skill Index (lightweight) in System Prompt
        - Tier 2: Full SKILL.md loaded on-demand via load_skill tool
        """
        parts = []

        # 1. Framework instructions (P0+P1: tool use, skills, parallel, completion)
        framework = self._build_framework_instructions()
        if framework:
            parts.append(framework)

        # 2. Helen language conventions (always included)
        helen_conventions = self._build_helen_conventions()
        if helen_conventions:
            parts.append(helen_conventions)

        # 3. Agent description (role definition, NOT the prompt field)
        for decl in agent_decl.declarations:
            if decl.description is not None:
                from helen.core.ast import LiteralNode
                if isinstance(decl.description, LiteralNode):
                    parts.append(decl.description.value)
                    break

        # 4. Skill Index (Tier 1)
        skill_index = self.build_skill_index()
        if skill_index:
            parts.append(skill_index)

        return "\n\n".join(parts)

    def _build_framework_instructions(self) -> str:
        """Build framework-level behavioral instructions (P0+P1).

        These instructions are injected before agent-specific content and
        provide foundational behavioral guidance for all agents:
        - P0: Tool use enforcement (MUST use tools, not describe)
        - P0: Skill loading enforcement (MUST load relevant skills)
        - P1: Parallel tool calls (batch independent calls)
        - P1: Completion criteria (working artifact, not description)

        Inspired by Hermes system prompt patterns.
        """
        return """<framework_instructions>
You are a Helen agent with tools and skills available. Follow these rules:

## 1. Tool Use (CRITICAL)
You MUST use your tools to take action — do not describe what you would do
without actually doing it. When tools are available, use them instead of
telling the user what you would do. Execute, don't describe.

## 2. Skills (CRITICAL)
Before replying, scan <available_skills> below. If any skill matches or is
even partially relevant to your task, you MUST load it with load_skill and
follow its instructions. Err on the side of loading.

## 3. Parallel Tool Calls
When you need multiple independent pieces of information, request them
together in a single response instead of one tool call per turn. Independent
reads, searches, and read-only commands should be batched.

## 4. Completion Criteria
The deliverable is a working artifact backed by real tool output — not a
description of one. Keep working until you have actually exercised the code
or produced the requested result. Don't stop at "I would do X" — actually do X.
</framework_instructions>"""

    def _build_helen_conventions(self) -> str:
        """Build Helen language conventions and best practices section.

        This provides foundational guidance for generating correct Helen code,
        inspired by Claude Code's system prompt structure.
        """
        return """<helen_conventions>
You are generating code for Helen, a prompt-first Agent programming language.

## Core Principles
- Helen is agent-centric: design around `agent` blocks with `prompt`, `tools`, and `main`
- Use `llm act` for LLM interactions (with optional tool calling via `tools` declaration)
- Use `llm if` for LLM-routed branching (classification tasks)
- Prefer composition over inheritance: build small, focused agents that collaborate

## Skill-Driven Development
**CRITICAL**: Before writing ANY code (tests, main program, or utilities):
1. Scan the available skills below
2. If a skill matches your task, call `load_skill(name='skill-name')` FIRST
3. Follow the loaded skill's instructions precisely

Common skills to load:
- `helen-syntax` — Language syntax, keywords, patterns
- `helen-testing` — Test framework (`fn test_name()`, `assert_true`, `assert_equal`)
- `helen-stdlib` — Built-in functions (string, math, collections, time, etc.)
- `helen-agent-collaboration` — Multi-agent patterns (shared let, channel, shared store)

## Code Generation Best Practices
- **Test-first**: Write tests before implementation when possible
- **Incremental**: Build and verify in small steps, not all at once
- **Error handling**: Use `try-catch` with specific exception types
- **Tool usage**:
  - Use `read_file` to inspect existing code before modifying
  - Use `shell_exec` for running tests (`helen test <file>`) and checks (`helen check <file>`)
  - Use `write_file` to create/update files (not shell commands like `echo >`)

## Common Pitfalls to Avoid
- ❌ Guessing stdlib function names → ✅ Load `helen-stdlib` skill or read source
- ❌ Inventing test syntax → ✅ Load `helen-testing` skill
- ❌ Using Python/C APIs (e.g., `strftime`) → ✅ Use Helen stdlib (e.g., `date_format`)
- ❌ Skipping skill loading → ✅ Always check skills first

## Testing Syntax (Quick Reference)
```helen
// Correct test structure
fn test_feature_name() {
    let result = function_under_test()
    assert_true(result > 0)
    assert_equal(result, expected_value)
}

// Run tests
run_tests()  // Executes all fn test_*() functions
```

## Agent Structure (Quick Reference)
```helen
agent MyAgent(input: str) {
    description "What this agent does"
    prompt "Task: {{input}}"
    tools ["read_file", "write_file"]  // Optional tool whitelist

    functions {
        fn helper_fn(): str {
            return "processed"
        }
    }

    main {
        let result = llm act  // Uses prompt + tools
        return result
    }
}
```
</helen_conventions>"""

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

        Scans skills and formats as <available_skills> XML block with
        name + description + category + tags.

        Caching: Uses max mtime across all skill directories to detect
        changes. Only rebuilds when skills are added/removed/modified.
        """
        if not self._runtime:
            return self._skill_index_cache or ""

        # Compute max mtime across all skill directories
        max_mtime = self._compute_skill_mtime()

        # Return cached index if mtime hasn't changed
        if max_mtime == self._skill_index_mtime and self._skill_index_cache is not None:
            return self._skill_index_cache

        # Rebuild the index
        try:
            skills = self._runtime.list_skills()
            if not skills:
                self._skill_index_cache = ""
                self._skill_index_mtime = max_mtime
                return ""

            # Group by category
            by_category: dict[str, list] = {}
            for s in skills:
                by_category.setdefault(s.category or "uncategorized", []).append(s)

            lines = ["<available_skills>"]
            lines.append("Before replying, scan skills below. If a skill matches or is")
            lines.append("even partially relevant to your task, you MUST load it with")
            lines.append("load_skill and follow its instructions. Err on the side of loading.")
            lines.append("")

            for category, skill_list in sorted(by_category.items()):
                lines.append(f"  {category}:")
                for s in skill_list:
                    # Truncate long descriptions (save tokens)
                    desc = s.description
                    if len(desc) > _SKILL_DESC_MAX_LEN:
                        desc = desc[:_SKILL_DESC_MAX_LEN - 3] + "..."
                    tag_str = f" (tags: {', '.join(s.tags)})" if s.tags else ""
                    lines.append(f"    - {s.name}: {desc}{tag_str}")

            lines.append("</available_skills>")
            result = "\n".join(lines)
            self._skill_index_cache = result
            self._skill_index_mtime = max_mtime
            return result
        except Exception:
            # If skill listing fails, silently continue without skills
            self._skill_index_cache = ""
            self._skill_index_mtime = max_mtime
            return ""

    def _compute_skill_mtime(self) -> float:
        """Compute max mtime across all skill directories.

        Returns:
            Maximum modification time of any SKILL.md file, or 0.0 if none found.
        """
        max_mtime = 0.0
        for base in self._skill_dirs:
            base_str = str(base)
            if os.path.exists(base_str):
                try:
                    for root, dirs, files in os.walk(base_str):
                        if "SKILL.md" in files:
                            skill_md = os.path.join(root, "SKILL.md")
                            mtime = os.path.getmtime(skill_md)
                            if mtime > max_mtime:
                                max_mtime = mtime
                except Exception:
                    pass
        return max_mtime

    def invalidate_skill_cache(self) -> None:
        """Force rebuild of skill index on next call."""
        self._skill_index_cache = None
        self._skill_index_mtime = 0.0
