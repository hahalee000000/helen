"""Tests for Helen Programming Agent contracts.

Tests verify the contract-first implementation:
1. SkillManager — CRUD operations for skills
2. SkillMatcher — keyword extraction and skill matching
3. SkillLearner — learning from successful fixes
4. SkillEvolver — evolving skills with new findings
5. ProgrammingAgent — orchestration, analysis, test running
6. Index management — auto-maintained skill index

Uses subprocess to run Helen files end-to-end.
"""
import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def agent_dir():
    """Create a temporary agent workspace with contracts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Create directory structure matching contracts' expected paths
        contracts_dir = base / "contracts"
        contracts_dir.mkdir()
        # Contracts use "agents/skills" as SKILLS_BASE_PATH
        agents_skills = base / "agents" / "skills"
        agents_skills.mkdir(parents=True)
        (agents_skills / "error-patterns").mkdir()
        (agents_skills / "code-quality").mkdir()
        (agents_skills / "testing").mkdir()
        (agents_skills / "architecture").mkdir()
        (agents_skills / "general").mkdir()
        # Contracts use "agents/memory" for MEMORY_PATH
        agents_memory = base / "agents" / "memory"
        agents_memory.mkdir(parents=True)
        memory_dir = base / "memory"
        memory_dir.mkdir()

        # Copy contracts file
        src = Path(__file__).parent.parent.parent / "agents" / "contracts" / "contracts.helen"
        dst = contracts_dir / "contracts.helen"
        shutil.copy2(str(src), str(dst))

        # Create a helper to write test files that import contracts
        def _make_test(helen_code: str) -> Path:
            test_file = base / "test_run.helen"
            # Rewrite paths for temp dir
            full_code = f'import "contracts/contracts.helen"\n\n' + helen_code
            test_file.write_text(full_code)
            return test_file

        yield {
            "base": base,
            "make_test": _make_test,
        }


def run_helen(file_path: Path, cwd: Path = None) -> dict:
    """Run a Helen file and return result."""
    result = subprocess.run(
        ["helen", str(file_path)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(cwd) if cwd else None,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# ── SkillManager Tests ────────────────────────────────────────

class TestSkillCreate:
    """Test skill_create(name, category, content)."""

    def test_create_valid_skill(self, agent_dir):
        """Should create a skill file at the correct path."""
        f = agent_dir["make_test"]('''
main {
    let result = skill_create("div-zero", "error-patterns", "---\\nname: div-zero\\n---\\n# Div Zero")
    print(result["status"])
    print(result["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "success" in r["stdout"]
        assert "0" in r["stdout"]

    def test_create_empty_name_rejected(self, agent_dir):
        """Should reject empty name with validation error."""
        f = agent_dir["make_test"]('''
main {
    let result = skill_create("", "error-patterns", "content")
    print(result["status"])
    print(result["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error" in r["stdout"]
        assert "1" in r["stdout"]

    def test_create_invalid_category_rejected(self, agent_dir):
        """Should reject invalid category."""
        f = agent_dir["make_test"]('''
main {
    let result = skill_create("test", "nonexistent", "content")
    print(result["status"])
    print(result["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error" in r["stdout"]

    def test_create_duplicate_rejected(self, agent_dir):
        """Should reject duplicate skill creation."""
        f = agent_dir["make_test"]('''
main {
    let r1 = skill_create("dup-test", "error-patterns", "v1")
    let r2 = skill_create("dup-test", "error-patterns", "v2")
    print(r2["status"])
    print(r2["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error" in r["stdout"]
        assert "202" in r["stdout"]


class TestSkillRead:
    """Test skill_read(name, category)."""

    def test_read_existing_skill(self, agent_dir):
        """Should read skill content after creation."""
        f = agent_dir["make_test"]('''
main {
    skill_create("readable", "testing", "# Readable Skill")
    let result = skill_read("readable", "testing")
    print(result["status"])
    print(result["content"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "success" in r["stdout"]
        assert "Readable Skill" in r["stdout"]

    def test_read_nonexistent_skill(self, agent_dir):
        """Should return not found for missing skill."""
        f = agent_dir["make_test"]('''
main {
    let result = skill_read("nonexistent", "testing")
    print(result["status"])
    print(result["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error" in r["stdout"]
        assert "201" in r["stdout"]


class TestSkillUpdate:
    """Test skill_update(name, category, content)."""

    def test_update_existing_skill(self, agent_dir):
        """Should update skill content."""
        f = agent_dir["make_test"]('''
main {
    skill_create("updatable", "code-quality", "v1")
    let result = skill_update("updatable", "code-quality", "v2-updated")
    print(result["status"])
    let read_back = skill_read("updatable", "code-quality")
    print(read_back["content"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "success" in r["stdout"]
        assert "v2-updated" in r["stdout"]

    def test_update_nonexistent_fails(self, agent_dir):
        """Should fail when updating nonexistent skill."""
        f = agent_dir["make_test"]('''
main {
    let result = skill_update("ghost", "testing", "content")
    print(result["status"])
    print(result["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error" in r["stdout"]
        assert "201" in r["stdout"]


class TestSkillDelete:
    """Test skill_delete(name, category)."""

    def test_delete_existing_skill(self, agent_dir):
        """Should delete skill and make it unreadable."""
        f = agent_dir["make_test"]('''
main {
    skill_create("deletable", "general", "content")
    let del_result = skill_delete("deletable", "general")
    print(del_result["status"])
    let read_after = skill_read("deletable", "general")
    print(read_after["status"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        lines = r["stdout"].strip().split("\n")
        assert "success" in lines[0]
        assert "error" in lines[1]

    def test_delete_nonexistent_fails(self, agent_dir):
        """Should fail when deleting nonexistent skill."""
        f = agent_dir["make_test"]('''
main {
    let result = skill_delete("ghost", "general")
    print(result["status"])
    print(result["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error" in r["stdout"]
        assert "201" in r["stdout"]


class TestSkillList:
    """Test skill_list()."""

    def test_list_empty(self, agent_dir):
        """Should return empty list when no skills exist."""
        f = agent_dir["make_test"]('''
main {
    let result = skill_list()
    print(result["status"])
    print(result["count"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "success" in r["stdout"]
        assert "0" in r["stdout"]

    def test_list_after_create(self, agent_dir):
        """Should list created skills."""
        f = agent_dir["make_test"]('''
main {
    skill_create("s1", "error-patterns", "c1")
    skill_create("s2", "testing", "c2")
    let result = skill_list()
    print(result["count"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "2" in r["stdout"]


# ── SkillMatcher Tests ────────────────────────────────────────

class TestExtractKeywords:
    """Test extract_keywords(context)."""

    def test_extract_error_keywords(self, agent_dir):
        """Should extract error-related keywords."""
        f = agent_dir["make_test"]('''
main {
    let kws = extract_keywords("Division by zero error in function")
    print(len(kws))
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        # Should find at least "division", "zero", "error"
        count = int(r["stdout"].strip())
        assert count >= 3

    def test_extract_quality_keywords(self, agent_dir):
        """Should extract quality-related keywords."""
        f = agent_dir["make_test"]('''
main {
    let kws = extract_keywords("complexity score is too high, security issue")
    print(len(kws))
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        count = int(r["stdout"].strip())
        assert count >= 3

    def test_extract_deduplicates(self, agent_dir):
        """Should not return duplicate keywords."""
        f = agent_dir["make_test"]('''
main {
    let kws = extract_keywords("error error error fail fail")
    print(len(kws))
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        count = int(r["stdout"].strip())
        assert count == 2  # "error" and "fail" only

    def test_extract_empty_context(self, agent_dir):
        """Should return empty list for empty context."""
        f = agent_dir["make_test"]('''
main {
    let kws = extract_keywords("")
    print(len(kws))
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "0" in r["stdout"]


class TestMatchSkills:
    """Test match_skills(context)."""

    def test_match_without_index(self, agent_dir):
        """Should return empty matches when no index exists."""
        f = agent_dir["make_test"]('''
main {
    let result = match_skills("division by zero error")
    print(result["count"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "0" in r["stdout"]

    def test_match_with_index(self, agent_dir):
        """Should match keywords against index content."""
        f = agent_dir["make_test"]('''
main {
    // Create a skill first
    skill_create("div-zero", "error-patterns", "---\\nname: div-zero\\n---\\n# Division by zero fix")
    // Create index at the correct path
    write_file("agents/skills/SKILL_INDEX.md", "# Index\\n## error-patterns\\n### div-zero\\n- Division by zero")
    let result = match_skills("division error in code")
    print(result["count"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        count = int(r["stdout"].strip())
        assert count >= 1


# ── SkillLearner Tests ────────────────────────────────────────

class TestDetermineCategory:
    """Test determine_category(error)."""

    def test_error_pattern_category(self, agent_dir):
        """Should map error codes 1-100 to error-patterns."""
        f = agent_dir["make_test"]('''
main {
    let cat = determine_category({"code": 1, "message": "test"})
    print(cat)
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error-patterns" in r["stdout"]

    def test_code_quality_category(self, agent_dir):
        """Should map error codes 101-200 to code-quality."""
        f = agent_dir["make_test"]('''
main {
    let cat = determine_category({"code": 150, "message": "test"})
    print(cat)
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "code-quality" in r["stdout"]

    def test_testing_category(self, agent_dir):
        """Should map error codes 201-300 to testing."""
        f = agent_dir["make_test"]('''
main {
    let cat = determine_category({"code": 250, "message": "test"})
    print(cat)
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "testing" in r["stdout"]

    def test_default_category(self, agent_dir):
        """Should map unknown codes to general."""
        f = agent_dir["make_test"]('''
main {
    let cat = determine_category({"code": 999, "message": "test"})
    print(cat)
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "general" in r["stdout"]


class TestLearnFromFix:
    """Test learn_from_fix(error, fix, confirmed)."""

    def test_learn_confirmed_fix(self, agent_dir):
        """Should save a new skill from confirmed fix."""
        f = agent_dir["make_test"]('''
main {
    let error = {"code": 1, "message": "division by zero"}
    let result = learn_from_fix(error, "Add assert divisor != 0", true)
    print(result["status"])
    print(result["category"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "success" in r["stdout"]
        assert "error-patterns" in r["stdout"]

    def test_skip_unconfirmed_fix(self, agent_dir):
        """Should skip learning when not confirmed."""
        f = agent_dir["make_test"]('''
main {
    let error = {"code": 1, "message": "test error"}
    let result = learn_from_fix(error, "some fix", false)
    print(result["status"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "skipped" in r["stdout"]

    def test_reject_empty_fix(self, agent_dir):
        """Should reject empty fix string."""
        f = agent_dir["make_test"]('''
main {
    let error = {"code": 1, "message": "test error"}
    let result = learn_from_fix(error, "", true)
    print(result["status"])
    print(result["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error" in r["stdout"]


# ── SkillEvolver Tests ────────────────────────────────────────

class TestEvolveSkill:
    """Test evolve_skill(skill_path, new_finding)."""

    def test_evolve_existing_skill(self, agent_dir):
        """Should append new finding to existing skill."""
        f = agent_dir["make_test"]('''
main {
    skill_create("evolvable", "general", "# Original Content")
    let path = "agents/skills/general/evolvable/SKILL.md"
    let result = evolve_skill(path, "Discovered new edge case")
    print(result["status"])
    let updated = read_file(path)
    print(updated)
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "evolved" in r["stdout"]
        assert "Original Content" in r["stdout"]
        assert "new edge case" in r["stdout"]

    def test_evolve_nonexistent_skill(self, agent_dir):
        """Should fail for nonexistent skill path."""
        f = agent_dir["make_test"]('''
main {
    let result = evolve_skill("agents/skills/general/ghost/SKILL.md", "finding")
    print(result["status"])
    print(result["error_code"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "error" in r["stdout"]
        assert "201" in r["stdout"]


# ── ProgrammingAgent Tests ────────────────────────────────────

class TestProcessInput:
    """Test process_input(project_dir, user_input)."""

    def test_process_basic_input(self, agent_dir):
        """Should process user input and return result."""
        f = agent_dir["make_test"]('''
main {
    let result = process_input(".", "fix division by zero error")
    print(result["response"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "Processed" in r["stdout"]

    def test_process_with_memory(self, agent_dir):
        """Should load agent memory if available."""
        # Create memory file at correct path
        memory_file = agent_dir["base"] / "agents" / "memory" / "MEMORY.md"
        memory_file.write_text("# Agent Memory\n- Test note")

        f = agent_dir["make_test"]('''
main {
    let result = process_input(".", "test input")
    print(result["context_loaded"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "true" in r["stdout"]


class TestAnalyzeFile:
    """Test analyze_file(file_path)."""

    def test_analyze_nonexistent_file(self, agent_dir):
        """Should return error for missing file."""
        f = agent_dir["make_test"]('''
main {
    let result = analyze_file("nonexistent.helen")
    print(result["error"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "file not found" in r["stdout"]

    def test_analyze_existing_file(self, agent_dir):
        """Should analyze an existing Helen file."""
        # Create a sample Helen file
        sample = agent_dir["base"] / "sample.helen"
        sample.write_text('main {\n    let x = 1\n    print(x)\n}\n')

        f = agent_dir["make_test"]('''
main {
    let result = analyze_file("sample.helen")
    print(result["metrics"] != {})
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "true" in r["stdout"]


# ── Index Management Tests ────────────────────────────────────

class TestUpdateSkillIndex:
    """Test update_skill_index()."""

    def test_update_index_empty(self, agent_dir):
        """Should create index even when no skills exist."""
        f = agent_dir["make_test"]('''
main {
    let result = update_skill_index()
    print(result["status"])
    print(result["count"])
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "success" in r["stdout"]
        assert "0" in r["stdout"]

    def test_update_index_with_skills(self, agent_dir):
        """Should include created skills in index."""
        f = agent_dir["make_test"]('''
main {
    skill_create("idx-test", "error-patterns", "# Test Skill")
    let result = update_skill_index()
    print(result["status"])
    print(result["count"])
    let index_content = read_file("agents/skills/SKILL_INDEX.md")
    print(index_content)
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "success" in r["stdout"]
        assert "1" in r["stdout"]
        assert "idx-test" in r["stdout"]


# ── Helper Function Tests ─────────────────────────────────────

class TestHelpers:
    """Test helper functions."""

    def test_is_valid_category(self, agent_dir):
        """Should validate known categories."""
        f = agent_dir["make_test"]('''
main {
    print(is_valid_category("error-patterns"))
    print(is_valid_category("nonexistent"))
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        lines = r["stdout"].strip().split("\n")
        assert "true" in lines[0]
        assert "false" in lines[1]

    def test_build_skill_path(self, agent_dir):
        """Should build correct skill path."""
        f = agent_dir["make_test"]('''
main {
    let p = build_skill_path("error-patterns", "div-zero")
    print(p)
}
''')
        r = run_helen(f, agent_dir["base"])
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        assert "agents/skills/error-patterns/div-zero/SKILL.md" in r["stdout"]
