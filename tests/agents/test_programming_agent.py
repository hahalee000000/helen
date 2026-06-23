"""Tests for Helen Programming Agent main agent block.

Verifies that the agent block parses correctly and can be invoked.
"""
import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def agent_workspace():
    """Create a workspace with the agent files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Copy agent directory structure
        agents_src = Path(__file__).parent.parent.parent / "agents"
        agents_dst = base / "agents"
        shutil.copytree(str(agents_src), str(agents_dst))

        # Create required directories
        (agents_dst / "skills" / "error-patterns").mkdir(parents=True, exist_ok=True)
        (agents_dst / "skills" / "code-quality").mkdir(parents=True, exist_ok=True)
        (agents_dst / "skills" / "testing").mkdir(parents=True, exist_ok=True)
        (agents_dst / "skills" / "architecture").mkdir(parents=True, exist_ok=True)
        (agents_dst / "skills" / "general").mkdir(parents=True, exist_ok=True)
        (agents_dst / "memory").mkdir(parents=True, exist_ok=True)

        yield base


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


class TestAgentParsing:
    """Test that the agent file parses without errors."""

    def test_contracts_parse(self, agent_workspace):
        """contracts.helen should parse without errors."""
        contracts = agent_workspace / "agents" / "contracts" / "contracts.helen"
        r = run_helen(contracts, agent_workspace)
        assert r["returncode"] == 0, f"Parse error: {r['stderr']}"

    def test_agent_parse(self, agent_workspace):
        """programming_agent.helen should parse without errors."""
        agent = agent_workspace / "agents" / "programming_agent.helen"
        r = run_helen(agent, agent_workspace)
        assert r["returncode"] == 0, f"Parse error: {r['stderr']}"


class TestAgentFunctions:
    """Test agent functions can be called via import."""

    def test_search_skills_via_agent(self, agent_workspace):
        """Agent's search_skills function should work via import."""
        test_file = agent_workspace / "test_search.helen"
        test_file.write_text('''
import "agents/contracts/contracts.helen"

main {
    let result = match_skills("division by zero error")
    print(result["count"])
    print(len(result["keywords"]))
}
''')
        r = run_helen(test_file, agent_workspace)
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        lines = r["stdout"].strip().split("\n")
        assert int(lines[0]) >= 0  # count
        assert int(lines[1]) >= 2  # keywords found

    def test_skill_crud_cycle(self, agent_workspace):
        """Full CRUD cycle should work end-to-end."""
        test_file = agent_workspace / "test_crud.helen"
        test_file.write_text('''
import "agents/contracts/contracts.helen"

main {
    // Create
    let created = skill_create("crud-test", "general", "# CRUD Test")
    print(created["status"])

    // Read
    let read_back = skill_read("crud-test", "general")
    print(read_back["status"])

    // Update
    let updated = skill_update("crud-test", "general", "# CRUD Test v2")
    print(updated["status"])

    // List
    let listed = skill_list()
    print(listed["count"])

    // Delete
    let deleted = skill_delete("crud-test", "general")
    print(deleted["status"])

    // Verify deleted
    let after = skill_read("crud-test", "general")
    print(after["status"])
}
''')
        r = run_helen(test_file, agent_workspace)
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        lines = r["stdout"].strip().split("\n")
        assert lines[0] == "success"   # create
        assert lines[1] == "success"   # read
        assert lines[2] == "success"   # update
        assert lines[3] == "1"         # list count
        assert lines[4] == "success"   # delete
        assert lines[5] == "error"     # read after delete

    def test_learn_and_evolve(self, agent_workspace):
        """Learn from fix then evolve the skill."""
        test_file = agent_workspace / "test_learn_evolve.helen"
        test_file.write_text('''
import "agents/contracts/contracts.helen"

main {
    // Learn from a fix
    let error = {"code": 1, "message": "null reference access"}
    let learned = learn_from_fix(error, "Add null check before access", true)
    print(learned["status"])
    print(learned["category"])

    // Evolve the skill
    let skill_path = "agents/skills/" + learned["category"] + "/" + learned["name"] + "/SKILL.md"
    let evolved = evolve_skill(skill_path, "Also check array bounds")
    print(evolved["status"])
}
''')
        r = run_helen(test_file, agent_workspace)
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        lines = r["stdout"].strip().split("\n")
        assert lines[0] == "success"            # learned
        assert lines[1] == "error-patterns"     # category
        assert lines[2] == "evolved"            # evolved

    def test_index_management(self, agent_workspace):
        """Index should update after skill operations."""
        test_file = agent_workspace / "test_index.helen"
        test_file.write_text('''
import "agents/contracts/contracts.helen"

main {
    skill_create("idx-a", "error-patterns", "# A")
    skill_create("idx-b", "testing", "# B")

    let result = update_skill_index()
    print(result["status"])
    print(result["count"])

    let content = read_file("agents/skills/SKILL_INDEX.md")
    print(content)
}
''')
        r = run_helen(test_file, agent_workspace)
        assert r["returncode"] == 0, f"stderr: {r['stderr']}"
        lines = r["stdout"].strip().split("\n")
        assert lines[0] == "success"
        assert lines[1] == "2"
        # Index content should mention both skills
        full_output = "\n".join(lines)
        assert "idx-a" in full_output
        assert "idx-b" in full_output
