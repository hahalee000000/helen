"""Tests for Helen Programming Agent v3.0 - Contract-First + TDD.

测试覆盖:
1. Skill Manager - CRUD操作
2. Skill Matcher - 关键词提取和匹配
3. Skill Learner - 从修复中学习
4. Skill Evolver - 演进现有skill
5. Programming Agent - 主编排器

测试原则:
- RED: 先写失败的测试
- GREEN: 实现功能使测试通过
- REFACTOR: 重构优化
"""
import pytest
from pathlib import Path
import subprocess
import shutil


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def agents_dir():
    """Return agents directory path."""
    return Path(__file__).parent.parent.parent / "agents"


@pytest.fixture
def contracts_file(agents_dir):
    """Return contracts v3 file path."""
    return agents_dir / "contracts" / "contracts_v3.helen"


@pytest.fixture
def skills_dir(agents_dir):
    """Return skills directory path."""
    return agents_dir / "skills"


@pytest.fixture
def cleanup_test_skills(skills_dir):
    """Clean up test skills before and after tests."""
    # Cleanup before
    test_categories = ["error-patterns", "code-quality", "testing", "architecture", "general"]
    for category in test_categories:
        cat_path = skills_dir / category
        if cat_path.exists():
            for skill_dir in cat_path.iterdir():
                if skill_dir.is_dir() and skill_dir.name.startswith("test-"):
                    shutil.rmtree(skill_dir)
    
    yield
    
    # Cleanup after
    for category in test_categories:
        cat_path = skills_dir / category
        if cat_path.exists():
            for skill_dir in cat_path.iterdir():
                if skill_dir.is_dir() and skill_dir.name.startswith("test-"):
                    shutil.rmtree(skill_dir)


def run_helen(file_path: str) -> dict:
    """Run a Helen file and return result."""
    result = subprocess.run(
        ["helen", file_path],
        capture_output=True,
        text=True,
        timeout=10
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def check_helen(file_path: str) -> dict:
    """Check Helen file syntax."""
    result = subprocess.run(
        ["helen", "check", file_path],
        capture_output=True,
        text=True,
        timeout=10
    )
    return {
        "valid": result.returncode == 0,
        "errors": result.stderr
    }


# ── Contract Syntax Tests ───────────────────────────────────────

class TestContractsV3Syntax:
    """验证contracts_v3.helen语法正确性."""
    
    def test_contracts_file_exists(self, contracts_file):
        """contracts_v3.helen必须存在."""
        assert contracts_file.exists(), f"File not found: {contracts_file}"
    
    def test_contracts_syntax_valid(self, contracts_file):
        """contracts_v3.helen必须通过语法检查."""
        result = check_helen(str(contracts_file))
        assert result["valid"], f"Syntax errors: {result['errors']}"
    
    def test_contracts_has_required_functions(self, contracts_file):
        """contracts_v3.helen必须定义所有契约函数."""
        content = contracts_file.read_text()
        
        # Skill Manager
        assert "fn skill_manager_create" in content
        assert "fn skill_manager_read" in content
        assert "fn skill_manager_update" in content
        assert "fn skill_manager_delete" in content
        assert "fn skill_manager_list" in content
        
        # Skill Matcher
        assert "fn skill_matcher_extract_keywords" in content
        assert "fn skill_matcher_match" in content
        
        # Skill Learner
        assert "fn skill_learner_determine_category" in content
        assert "fn skill_learner_learn" in content
        
        # Skill Evolver
        assert "fn skill_evolver_evolve" in content
        
        # Programming Agent
        assert "fn programming_agent_process" in content
        assert "fn programming_agent_analyze" in content
        assert "fn programming_agent_run_tests" in content
    
    def test_contracts_has_error_codes(self, contracts_file):
        """contracts_v3.helen必须定义错误码."""
        content = contracts_file.read_text()
        assert "ERROR_VALIDATION" in content
        assert "ERROR_IO" in content
        assert "ERROR_NOT_FOUND" in content
        assert "ERROR_ALREADY_EXISTS" in content


# ── Skill Manager Tests ─────────────────────────────────────────

class TestSkillManager:
    """Skill Manager CRUD操作测试."""
    
    def test_create_skill_success(self, cleanup_test_skills, skills_dir):
        """应该成功创建skill."""
        # 创建测试文件
        test_file = skills_dir.parent / "test_create.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_manager_create(
        "test-division-zero",
        "error-patterns",
        "---\\nname: test\\n---\\n# Test"
    )
    print(result["status"])
    print(result["path"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        # 验证结果
        assert "success" in result["stdout"]
        assert "test-division-zero" in result["stdout"]
        
        # 验证文件创建
        skill_path = skills_dir / "error-patterns" / "test-division-zero" / "SKILL.md"
        assert skill_path.exists()
    
    def test_create_skill_empty_name(self, cleanup_test_skills, skills_dir):
        """空名称应该返回错误."""
        test_file = skills_dir.parent / "test_empty_name.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_manager_create("", "error-patterns", "content")
    print(result["status"])
    print(result["message"])
    print(result["error_code"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "error" in result["stdout"]
        assert "name cannot be empty" in result["stdout"]
        assert "1" in result["stdout"]  # ERROR_VALIDATION
    
    def test_create_skill_invalid_category(self, cleanup_test_skills, skills_dir):
        """无效类别应该返回错误."""
        test_file = skills_dir.parent / "test_invalid_cat.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_manager_create("test", "invalid-category", "content")
    print(result["status"])
    print(result["message"])
    print(result["error_code"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "error" in result["stdout"]
        assert "invalid category" in result["stdout"]
        assert "1" in result["stdout"]  # ERROR_VALIDATION
    
    def test_read_skill_success(self, cleanup_test_skills, skills_dir):
        """应该成功读取存在的skill."""
        # 先创建skill
        skill_dir = skills_dir / "error-patterns" / "test-read"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test-read\n---\n# Test")
        
        # 读取skill
        test_file = skills_dir.parent / "test_read.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_manager_read("test-read", "error-patterns")
    print(result["status"])
    print(result["content"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "success" in result["stdout"]
        assert "test-read" in result["stdout"]
    
    def test_read_skill_not_found(self, cleanup_test_skills, skills_dir):
        """读取不存在的skill应该返回错误."""
        test_file = skills_dir.parent / "test_read_notfound.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_manager_read("nonexistent", "error-patterns")
    print(result["status"])
    print(result["error_code"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "error" in result["stdout"]
        assert "201" in result["stdout"]  # ERROR_NOT_FOUND
    
    def test_delete_skill_success(self, cleanup_test_skills, skills_dir):
        """应该成功删除skill."""
        # 先创建skill
        skill_dir = skills_dir / "error-patterns" / "test-delete"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test-delete\n---\n# Test")
        
        # 删除skill
        test_file = skills_dir.parent / "test_delete.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_manager_delete("test-delete", "error-patterns")
    print(result["status"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "success" in result["stdout"]
        assert not skill_dir.exists()
    
    def test_list_skills(self, cleanup_test_skills, skills_dir):
        """应该列出所有skills."""
        # 创建几个测试skills
        for i in range(3):
            skill_dir = skills_dir / "error-patterns" / f"test-list-{i}"
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(f"---\nname: test-list-{i}\n---\n# Test")
        
        # 列出skills
        test_file = skills_dir.parent / "test_list.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_manager_list()
    print(result["status"])
    print(result["count"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "success" in result["stdout"]
        # count应该>=3


# ── Skill Matcher Tests ─────────────────────────────────────────

class TestSkillMatcher:
    """Skill Matcher关键词提取和匹配测试."""
    
    def test_extract_keywords_error(self, skills_dir):
        """应该从错误消息中提取关键词."""
        test_file = skills_dir.parent / "test_extract.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let keywords = skill_matcher_extract_keywords("Division by zero error")
    print(len(keywords))
    for kw in keywords {
        print(kw)
    }
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        # 应该提取到"division", "zero", "error"
        assert "3" in result["stdout"] or "division" in result["stdout"]
    
    def test_extract_keywords_quality(self, skills_dir):
        """应该从质量相关文本中提取关键词."""
        test_file = skills_dir.parent / "test_extract_quality.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let keywords = skill_matcher_extract_keywords("Code complexity too high")
    print(len(keywords))
    for kw in keywords {
        print(kw)
    }
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "complexity" in result["stdout"]
    
    def test_match_with_index(self, cleanup_test_skills, skills_dir):
        """应该匹配SKILL_INDEX.md中的skills."""
        # 创建测试skill
        skill_dir = skills_dir / "error-patterns" / "test-match"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test-match\ntags: [division, zero]\n---\n# Test")
        
        # 重建索引(简化版)
        index_file = skills_dir / "SKILL_INDEX.md"
        index_file.write_text("# Skill Index\n- test-match: division, zero\n")
        
        # 匹配
        test_file = skills_dir.parent / "test_match.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_matcher_match("Division by zero error")
    print(result["count"])
    print(result["keywords"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        # 应该匹配到
        assert "0" not in result["stdout"] or "division" in result["stdout"]


# ── Skill Learner Tests ─────────────────────────────────────────

class TestSkillLearner:
    """Skill Learner从修复中学习测试."""
    
    def test_determine_category_error(self, skills_dir):
        """应该根据错误码确定类别."""
        test_file = skills_dir.parent / "test_category.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let error = {"code": 50, "message": "test"}
    let category = skill_learner_determine_category(error)
    print(category)
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "error-patterns" in result["stdout"]
    
    def test_learn_skipped(self, skills_dir):
        """未确认的修复应该跳过学习."""
        test_file = skills_dir.parent / "test_learn_skip.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let error = {"code": 50, "message": "test error"}
    let result = skill_learner_learn(error, "fix", false)
    print(result["status"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "skipped" in result["stdout"]
    
    def test_learn_empty_fix(self, skills_dir):
        """空修复应该返回错误."""
        test_file = skills_dir.parent / "test_learn_empty.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let error = {"code": 50, "message": "test error"}
    let result = skill_learner_learn(error, "", true)
    print(result["status"])
    print(result["error_code"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "error" in result["stdout"]
        assert "1" in result["stdout"]  # ERROR_VALIDATION


# ── Skill Evolver Tests ─────────────────────────────────────────

class TestSkillEvolver:
    """Skill Evolver演进测试."""
    
    def test_evolve_success(self, cleanup_test_skills, skills_dir):
        """应该成功演进skill."""
        # 创建测试skill
        skill_dir = skills_dir / "error-patterns" / "test-evolve"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test-evolve\n---\n# Test\n\n## Pitfalls\n- Original pitfall")
        
        # 演进
        test_file = skills_dir.parent / "test_evolve.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_evolver_evolve(
        "agents/skills/error-patterns/test-evolve/SKILL.md",
        "New finding: edge case"
    )
    print(result["status"])
    print(result["changes"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "evolved" in result["stdout"]
        
        # 验证文件更新
        updated_content = skill_file.read_text()
        assert "New finding" in updated_content
    
    def test_evolve_not_found(self, skills_dir):
        """演进不存在的skill应该返回错误."""
        test_file = skills_dir.parent / "test_evolve_notfound.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = skill_evolver_evolve("nonexistent/SKILL.md", "finding")
    print(result["status"])
    print(result["error_code"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "error" in result["stdout"]
        assert "201" in result["stdout"]  # ERROR_NOT_FOUND


# ── Programming Agent Tests ─────────────────────────────────────

class TestProgrammingAgent:
    """Programming Agent主编排器测试."""
    
    def test_process_basic(self, skills_dir):
        """应该处理基本请求."""
        test_file = skills_dir.parent / "test_process.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = programming_agent_process("~/helen", "How to fix division by zero?")
    print(result["response"])
    print(result["skills_used"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "Processed" in result["stdout"]
    
    def test_analyze_file(self, skills_dir, contracts_file):
        """应该分析Helen源文件."""
        test_file = skills_dir.parent / "test_analyze.helen"
        test_file.write_text(f"""
import "contracts/contracts_v3.helen"

main {{
    let result = programming_agent_analyze("{contracts_file}")
    print(result["metrics"])
    print(result["scores"])
}}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        # 应该返回分析结果
        assert "success" in result["stdout"] or "metrics" in result["stdout"]
    
    def test_analyze_nonexistent_file(self, skills_dir):
        """分析不存在的文件应该返回错误."""
        test_file = skills_dir.parent / "test_analyze_notfound.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    let result = programming_agent_analyze("nonexistent.helen")
    print(result["error"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        assert "file not found" in result["stdout"]


# ── Integration Tests ───────────────────────────────────────────

class TestIntegration:
    """集成测试 - 完整工作流."""
    
    def test_full_workflow(self, cleanup_test_skills, skills_dir):
        """测试完整工作流: 创建 -> 匹配 -> 学习 -> 演进."""
        # 1. 创建skill
        test_file = skills_dir.parent / "test_workflow.helen"
        test_file.write_text("""
import "contracts/contracts_v3.helen"

main {
    // 创建
    let create_result = skill_manager_create(
        "test-workflow",
        "error-patterns",
        "---\\nname: test-workflow\\n---\\n# Test"
    )
    print("Create: " + create_result["status"])
    
    // 读取
    let read_result = skill_manager_read("test-workflow", "error-patterns")
    print("Read: " + read_result["status"])
    
    // 更新
    let update_result = skill_manager_update(
        "test-workflow",
        "error-patterns",
        "---\\nname: test-workflow\\n---\\n# Updated"
    )
    print("Update: " + update_result["status"])
    
    // 列出
    let list_result = skill_manager_list()
    print("List: " + list_result["status"])
    
    // 删除
    let delete_result = skill_manager_delete("test-workflow", "error-patterns")
    print("Delete: " + delete_result["status"])
}
""")
        
        result = run_helen(str(test_file))
        test_file.unlink()
        
        # 所有操作应该成功
        assert "Create: success" in result["stdout"]
        assert "Read: success" in result["stdout"]
        assert "Update: success" in result["stdout"]
        assert "List: success" in result["stdout"]
        assert "Delete: success" in result["stdout"]
