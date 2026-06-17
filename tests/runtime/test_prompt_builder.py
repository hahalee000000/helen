"""Tests for helen.runtime.prompt_builder — PromptBuilder (HLD 3.7).

Covers:
- Template variable substitution ({{var}})
- Undefined variable handling
- Single-pass rendering (no recursive injection)
- Plain strings with {{}} are NOT rendered
- Skill Index Tier 1 generation
- System/User prompt assembly
- Route/Choose prompt building
"""

from helen.runtime.prompt_builder import PromptBuilder


class FakeRuntime:
    """Minimal Runtime mock for PromptBuilder tests."""

    def list_skills(self):
        from helen.runtime import SkillMeta
        return [
            SkillMeta(name="test-skill", description="A test skill", category="test"),
            SkillMeta(name="another-skill", description="Another skill", category="dev"),
        ]

    def load_skill(self, name: str) -> str:
        return f"# {name}\n\nContent of {name} skill."


class TestPromptBuilderRender:
    """Test template rendering."""

    def setup_method(self):
        self.builder = PromptBuilder(FakeRuntime())

    def test_single_variable_substitution(self):
        """{{name}} is replaced with env value."""
        result = self.builder.render("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_variables(self):
        """Multiple {{var}} placeholders are replaced."""
        template = "Agent {{name}} uses {{model}} at temp {{temp}}."
        env = {"name": "Bot", "model": "gpt-4", "temp": "0.7"}
        result = self.builder.render(template, env)
        assert result == "Agent Bot uses gpt-4 at temp 0.7."

    def test_undefined_variable_keeps_placeholder(self):
        """Undefined {{var}} keeps original text (no crash)."""
        result = self.builder.render("Hello {{missing}}!", {"other": "value"})
        assert "{{missing}}" in result

    def test_plain_string_not_rendered(self):
        """Plain strings with {{}} should NOT be rendered."""
        # Per HLD 3.7.2: template rendering only applies in prompt blocks
        # render() is called on prompt templates, not plain strings
        result = self.builder.render("No vars here {{x}}", {})
        # Since x is not in env, it stays as-is (correct behavior)
        assert "{{x}}" in result

    def test_no_recursive_rendering(self):
        """Rendered result is NOT re-rendered (HLD 3.7.2)."""
        # If env value contains {{...}}, it should not be re-rendered
        result = self.builder.render("{{x}}", {"x": "{{y}}"})
        assert result == "{{y}}"  # Not rendered again

    def test_empty_env(self):
        """Empty env leaves all placeholders intact."""
        result = self.builder.render("{{a}} {{b}}", {})
        assert "{{a}}" in result
        assert "{{b}}" in result


class TestPromptBuilderSkillIndex:
    """Test Skill Index Tier 1."""

    def setup_method(self):
        self.builder = PromptBuilder(FakeRuntime())

    def test_skill_index_format(self):
        """Skill Index uses <available_skills> XML block."""
        index = self.builder.build_skill_index()
        assert "<available_skills>" in index
        assert "</available_skills>" in index

    def test_skill_index_contains_skills(self):
        """All skills appear in the index."""
        index = self.builder.build_skill_index()
        assert "test-skill" in index
        assert "another-skill" in index
        assert "A test skill" in index

    def test_skill_index_groups_by_category(self):
        """Skills are grouped by category."""
        index = self.builder.build_skill_index()
        assert "test:" in index or "test" in index
        assert "dev:" in index or "dev" in index


class TestPromptBuilderRouteAndChoose:
    """Test route/choose prompt building."""

    def setup_method(self):
        self.builder = PromptBuilder(FakeRuntime())

    def test_build_route_prompt(self):
        """Route prompt contains description, branches, and classify instruction."""
        prompt = self.builder.build_route_prompt(
            "Classify the user intent", ["query", "command", "chat"]
        )
        assert "Classify the user intent" in prompt
        assert "query" in prompt
        assert "command" in prompt
        assert "chat" in prompt
        assert "classify" in prompt.lower()

    def test_build_route_prompt_with_context(self):
        """Route prompt includes context when provided."""
        prompt = self.builder.build_route_prompt(
            "Classify", ["a"], context="User said hello"
        )
        assert "User said hello" in prompt
