"""Tests for Helen Programming Agent contracts.

Tests the contract functions by running Helen programs via subprocess.
This validates the contracts work correctly when executed.
"""
import pytest
import subprocess
from pathlib import Path


@pytest.fixture
def helen_dir():
    """Return the helen project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def agents_dir():
    """Return the agents directory."""
    return Path(__file__).parent.parent.parent / "agents"


def run_helen(code, cwd=None):
    """Run Helen code and return stdout."""
    import tempfile
    import os
    # Write temp file in cwd so relative imports work
    work_dir = cwd or os.getcwd()
    temp_path = os.path.join(work_dir, "_test_temp.helen")
    with open(temp_path, 'w') as f:
        f.write(code)
    try:
        result = subprocess.run(
            ["helen", "_test_temp.helen"],
            capture_output=True,
            text=True,
            cwd=work_dir
        )
    finally:
        os.unlink(temp_path)
    return result


class TestContractsSyntax:
    """Test that contract files pass syntax check."""

    def test_contracts_check(self, agents_dir):
        """contracts.helen passes syntax check."""
        result = subprocess.run(
            ["helen", "check", "contracts/contracts.helen"],
            capture_output=True,
            text=True,
            cwd=agents_dir
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_programming_agent_check(self, agents_dir):
        """programming_agent.helen passes syntax check."""
        result = subprocess.run(
            ["helen", "check", "programming_agent.helen"],
            capture_output=True,
            text=True,
            cwd=agents_dir
        )
        assert result.returncode == 0
        assert "OK" in result.stdout


class TestProgrammingAgentExecution:
    """Test that the programming agent runs correctly."""

    def test_programming_agent_runs(self, agents_dir):
        """programming_agent.helen executes and prints header."""
        result = subprocess.run(
            ["helen", "programming_agent.helen"],
            capture_output=True,
            text=True,
            cwd=agents_dir
        )
        assert result.returncode == 0
        assert "Helen Programming Agent" in result.stdout
        assert "v1.0" in result.stdout

    def test_programming_agent_lists_functions(self, agents_dir):
        """programming_agent.helen lists all contract functions."""
        result = subprocess.run(
            ["helen", "programming_agent.helen"],
            capture_output=True,
            text=True,
            cwd=agents_dir
        )
        assert result.returncode == 0
        # Check that all major function groups are listed
        assert "skill_create" in result.stdout
        assert "skill_read" in result.stdout
        assert "extract_keywords" in result.stdout
        assert "determine_category" in result.stdout
        assert "evolve_skill" in result.stdout
        assert "process_input" in result.stdout
        assert "analyze_file" in result.stdout


class TestContractFunctions:
    """Test individual contract functions via Helen execution."""

    def test_is_valid_category(self, agents_dir):
        """is_valid_category returns correct results."""
        code = '''
import "contracts/contracts.helen"

main {
    print(is_valid_category("testing"))
    print(is_valid_category("invalid"))
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "true" in result.stdout.lower()
        assert "false" in result.stdout.lower()

    def test_skill_path_construction(self, agents_dir):
        """skill_path constructs correct paths."""
        code = '''
import "contracts/contracts.helen"

main {
    print(skill_path("testing", "my-skill"))
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "agents/skills/testing/my-skill/SKILL.md" in result.stdout

    def test_skill_dir_construction(self, agents_dir):
        """skill_dir constructs correct directories."""
        code = '''
import "contracts/contracts.helen"

main {
    print(skill_dir("testing", "my-skill"))
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "agents/skills/testing/my-skill" in result.stdout

    def test_skill_create_validates_name(self, agents_dir):
        """skill_create rejects empty name."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = skill_create("", "testing", "content")
    print(result["status"])
    print(result["error_code"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "error" in result.stdout
        assert "1" in result.stdout  # ERROR_VALIDATION

    def test_skill_create_validates_category(self, agents_dir):
        """skill_create rejects invalid category."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = skill_create("test", "invalid-cat", "content")
    print(result["status"])
    print(result["error_code"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "error" in result.stdout
        assert "1" in result.stdout  # ERROR_VALIDATION

    def test_skill_read_not_found(self, agents_dir):
        """skill_read returns error for non-existent skill."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = skill_read("non-existent", "testing")
    print(result["status"])
    print(result["error_code"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "error" in result.stdout
        assert "201" in result.stdout  # ERROR_NOT_FOUND

    def test_extract_keywords_finds_error_kws(self, agents_dir):
        """extract_keywords finds error-related keywords."""
        code = '''
import "contracts/contracts.helen"

main {
    let kws = extract_keywords("Division by zero error")
    print(len(kws))
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        # Should find at least "division", "zero", "error"
        assert int(result.stdout.strip()) >= 1

    def test_extract_keywords_empty_for_unrelated(self, agents_dir):
        """extract_keywords returns empty for unrelated text."""
        code = '''
import "contracts/contracts.helen"

main {
    let kws = extract_keywords("hello world")
    print(len(kws))
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "0" in result.stdout

    def test_determine_category_validation(self, agents_dir):
        """determine_category maps validation errors correctly."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = determine_category({"code": 1, "message": "test"})
    print(result["category"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "error-patterns" in result.stdout

    def test_determine_category_io(self, agents_dir):
        """determine_category maps IO errors correctly."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = determine_category({"code": 101, "message": "test"})
    print(result["category"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "code-quality" in result.stdout

    def test_determine_category_default(self, agents_dir):
        """determine_category defaults to general."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = determine_category({"code": 999, "message": "test"})
    print(result["category"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "general" in result.stdout

    def test_learn_from_fix_skips_unconfirmed(self, agents_dir):
        """learn_from_fix skips when not confirmed."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = learn_from_fix({"message": "err"}, "fix", false)
    print(result["status"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "skipped" in result.stdout

    def test_learn_from_fix_rejects_empty(self, agents_dir):
        """learn_from_fix rejects empty fix."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = learn_from_fix({"message": "err"}, "", true)
    print(result["status"])
    print(result["error_code"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "error" in result.stdout
        assert "1" in result.stdout  # ERROR_VALIDATION

    def test_evolve_skill_missing_file(self, agents_dir):
        """evolve_skill returns error for missing file."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = evolve_skill("/non/existent/path.md", "finding")
    print(result["status"])
    print(result["error_code"])
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "error" in result.stdout
        assert "201" in result.stdout  # ERROR_NOT_FOUND

    def test_process_input_returns_structure(self, agents_dir):
        """process_input returns valid structure."""
        code = '''
import "contracts/contracts.helen"

main {
    let result = process_input(".", "hello world")
    print(result["response"] != null)
    print(result["skills_used"] != null)
}
'''
        result = run_helen(code, cwd=agents_dir)
        assert result.returncode == 0
        assert "true" in result.stdout.lower()


class TestProtocolDeclarations:
    """Test that protocol declarations are valid."""

    def test_protocols_declared(self, agents_dir):
        """All 5 protocols are declared in contracts.helen."""
        contracts_file = agents_dir / "contracts" / "contracts.helen"
        content = contracts_file.read_text()

        assert "protocol SkillManagerContract" in content
        assert "protocol SkillMatcherContract" in content
        assert "protocol SkillLearnerContract" in content
        assert "protocol SkillEvolverContract" in content
        assert "protocol ProgrammingAgentContract" in content


class TestFileCleanup:
    """Test that obsolete files have been removed."""

    def test_no_versioned_files(self, agents_dir):
        """No versioned .helen files remain."""
        import os
        for f in os.listdir(agents_dir):
            assert "_v2" not in f, f"Obsolete file found: {f}"
            assert "_v3" not in f, f"Obsolete file found: {f}"

    def test_no_old_skill_agents(self, agents_dir):
        """Old skill_*.helen agent files removed."""
        import os
        files = os.listdir(agents_dir)
        assert "skill_manager.helen" not in files
        assert "skill_matcher.helen" not in files
        assert "skill_learner.helen" not in files
        assert "skill_evolver.helen" not in files

    def test_contracts_no_version(self, agents_dir):
        """contracts directory has no versioned files."""
        import os
        contracts_dir = agents_dir / "contracts"
        files = os.listdir(contracts_dir)
        assert "contracts.helen" in files
        assert "contracts_v3.helen" not in files
