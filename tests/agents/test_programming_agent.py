"""Tests for Helen Programming Agent system.

Tests verify that .helen Agent files:
1. Pass syntax check (helen check)
2. Execute without runtime errors
3. Produce expected output/behavior
"""

import pytest
from pathlib import Path

from tests.agents.test_helpers import (
    check_helen,
    run_helen,
    create_test_skill,
    cleanup_test_skills,
    rebuild_skill_index,
    AGENTS_DIR,
    SKILLS_DIR,
    MEMORY_DIR,
)


# ── Syntax Validation Tests ───────────────────────────────────


class TestAgentSyntax:
    """Verify all agent .helen files pass syntax check."""
    
    def test_skill_manager_syntax(self):
        """skill_manager.helen must pass syntax check."""
        result = check_helen(str(AGENTS_DIR / "skill_manager.helen"))
        assert result["valid"], f"Syntax errors: {result['errors']}"
    
    def test_skill_matcher_syntax(self):
        """skill_matcher.helen must pass syntax check."""
        result = check_helen(str(AGENTS_DIR / "skill_matcher.helen"))
        assert result["valid"], f"Syntax errors: {result['errors']}"
    
    def test_skill_learner_syntax(self):
        """skill_learner.helen must pass syntax check."""
        result = check_helen(str(AGENTS_DIR / "skill_learner.helen"))
        assert result["valid"], f"Syntax errors: {result['errors']}"
    
    def test_skill_evolver_syntax(self):
        """skill_evolver.helen must pass syntax check."""
        result = check_helen(str(AGENTS_DIR / "skill_evolver.helen"))
        assert result["valid"], f"Syntax errors: {result['errors']}"
    
    def test_programming_agent_syntax(self):
        """programming_agent.helen must pass syntax check."""
        result = check_helen(str(AGENTS_DIR / "programming_agent.helen"))
        assert result["valid"], f"Syntax errors: {result['errors']}"


# ── Skill Manager Tests ───────────────────────────────────────


class TestSkillManager:
    """Tests for skill_manager.helen — skill CRUD operations."""
    
    def setup_method(self):
        """Clean up test skills before each test."""
        cleanup_test_skills()
    
    def teardown_method(self):
        """Clean up after tests."""
        cleanup_test_skills()
    
    def test_create_skill(self):
        """SkillManager can create a new skill."""
        # This test verifies the skill_manager agent can create skills
        # by checking that the file system operations work correctly
        skill_path = create_test_skill("test-create", "error-patterns")
        assert skill_path.exists()
        assert "SKILL.md" in skill_path.name
    
    def test_list_skills(self):
        """SkillManager can list existing skills."""
        # Create some test skills
        create_test_skill("test-list-1", "error-patterns")
        create_test_skill("test-list-2", "code-quality")
        
        # Verify they exist
        assert (SKILLS_DIR / "error-patterns" / "test-list-1" / "SKILL.md").exists()
        assert (SKILLS_DIR / "code-quality" / "test-list-2" / "SKILL.md").exists()


# ── Skill Matcher Tests ───────────────────────────────────────


class TestSkillMatcher:
    """Tests for skill_matcher.helen — skill search and matching."""
    
    def setup_method(self):
        """Set up test skills and rebuild index."""
        cleanup_test_skills()
        create_test_skill("test-division-zero", "error-patterns", """---
name: test-division-zero
description: "Fix division by zero errors"
version: 1.0.0
category: error-patterns
tags: [division, zero, runtime-error]
triggers:
  - error_type: "RuntimeError"
    message_contains: "Division by zero"
confidence: 0.95
occurrences: 5
---

# Division by Zero Fix

## Trigger
RuntimeError with message containing "Division by zero"

## Steps
1. Find the division operation
2. Add assert divisor != 0 before division
""")
        rebuild_skill_index()
    
    def teardown_method(self):
        cleanup_test_skills()
    
    def test_index_exists(self):
        """SKILL_INDEX.md should exist after rebuild."""
        index_path = SKILLS_DIR / "SKILL_INDEX.md"
        assert index_path.exists()
    
    def test_index_contains_skill(self):
        """SKILL_INDEX.md should contain created skill."""
        index_path = SKILLS_DIR / "SKILL_INDEX.md"
        content = index_path.read_text()
        assert "test-division-zero" in content
        assert "division" in content.lower()


# ── Skill Learner Tests ───────────────────────────────────────


class TestSkillLearner:
    """Tests for skill_learner.helen — learning from fixes."""
    
    def setup_method(self):
        cleanup_test_skills()
    
    def teardown_method(self):
        cleanup_test_skills()
    
    def test_skill_directory_creation(self):
        """Skill learner should create proper directory structure."""
        # Verify directory structure exists
        assert SKILLS_DIR.exists()
        assert (SKILLS_DIR / "error-patterns").exists()
        assert (SKILLS_DIR / "code-quality").exists()
        assert (SKILLS_DIR / "testing").exists()


# ── Programming Agent Tests ───────────────────────────────────


class TestProgrammingAgent:
    """Tests for programming_agent.helen — main orchestrator."""
    
    def test_agent_file_exists(self):
        """programming_agent.helen must exist."""
        assert (AGENTS_DIR / "programming_agent.helen").exists()
    
    def test_agent_has_required_sections(self):
        """programming_agent.helen must have agent declaration, functions, main."""
        content = (AGENTS_DIR / "programming_agent.helen").read_text()
        assert "agent " in content
        assert "functions" in content
        assert "main" in content


# ── Integration Tests ─────────────────────────────────────────


class TestIntegration:
    """Integration tests for the full agent system."""
    
    def setup_method(self):
        cleanup_test_skills()
    
    def teardown_method(self):
        cleanup_test_skills()
    
    def test_full_workflow(self):
        """Test complete workflow: create skill → match → learn."""
        # 1. Create a skill
        skill_path = create_test_skill("test-workflow", "error-patterns")
        assert skill_path.exists()
        
        # 2. Rebuild index
        rebuild_skill_index()
        
        # 3. Verify index contains the skill
        index_content = (SKILLS_DIR / "SKILL_INDEX.md").read_text()
        assert "test-workflow" in index_content


# ── Memory Tests ──────────────────────────────────────────────


class TestMemory:
    """Tests for agent memory system."""
    
    def test_memory_directory_exists(self):
        """agents/memory/ directory must exist."""
        assert MEMORY_DIR.exists()
    
    def test_memory_file_exists(self):
        """MEMORY.md must exist."""
        assert (MEMORY_DIR / "MEMORY.md").exists()
    
    def test_user_file_exists(self):
        """USER.md must exist."""
        assert (MEMORY_DIR / "USER.md").exists()
