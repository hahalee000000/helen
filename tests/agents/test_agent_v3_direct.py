"""Tests for Helen Programming Agent v3.0 - 直接函数测试.

由于Helen不支持模块导入,测试文件直接包含函数定义或使用
Python作为胶水层进行测试.
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
def agent_file(agents_dir):
    """Return programming_agent_v3.helen file path."""
    return agents_dir / "programming_agent_v3.helen"


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


def run_helen_file(content: str, workdir: Path) -> dict:
    """Create temp file, run it, and return result."""
    test_file = workdir / "temp_test.helen"
    test_file.write_text(content)
    
    result = subprocess.run(
        ["helen", str(test_file)],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=workdir
    )
    
    test_file.unlink()
    
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


# ── Syntax Tests ────────────────────────────────────────────────

class TestAgentV3Syntax:
    """验证programming_agent_v3.helen语法正确性."""
    
    def test_agent_file_exists(self, agent_file):
        """programming_agent_v3.helen必须存在."""
        assert agent_file.exists()
    
    def test_agent_syntax_valid(self, agent_file):
        """programming_agent_v3.helen必须通过语法检查."""
        result = subprocess.run(
            ["helen", "check", str(agent_file)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax errors: {result.stderr}"
    
    def test_agent_executes(self, agent_file):
        """programming_agent_v3.helen必须能正常执行."""
        result = subprocess.run(
            ["helen", str(agent_file)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Helen Programming Agent v3.0" in result.stdout


# ── Skill Manager Tests ─────────────────────────────────────────

class TestSkillManager:
    """Skill Manager CRUD操作测试."""
    
    def test_create_skill_empty_name(self, cleanup_test_skills, agents_dir):
        """空名称应该返回错误."""
        content = """
const SKILL_CATEGORIES = ["error-patterns", "code-quality", "testing", "architecture", "general"]
const SKILLS_BASE_PATH = "agents/skills"
const ERROR_VALIDATION = 1

fn skill_manager_create(name: str, category: str, content: str) -> map {
    if name == "" {
        return {
            "status": "error",
            "message": "name cannot be empty",
            "path": "",
            "error_code": ERROR_VALIDATION
        }
    }
    return {"status": "success", "message": "ok", "path": "", "error_code": 0}
}

main {
    let result = skill_manager_create("", "error-patterns", "content")
    print(result["status"])
    print(result["message"])
    print(result["error_code"])
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "error" in result["stdout"]
        assert "name cannot be empty" in result["stdout"]
        assert "1" in result["stdout"]
    
    def test_create_skill_invalid_category(self, cleanup_test_skills, agents_dir):
        """无效类别应该返回错误."""
        content = """
const SKILL_CATEGORIES = ["error-patterns", "code-quality", "testing", "architecture", "general"]
const SKILLS_BASE_PATH = "agents/skills"
const ERROR_VALIDATION = 1

fn skill_manager_create(name: str, category: str, content: str) -> map {
    let valid_category = false
    for cat in SKILL_CATEGORIES {
        if cat == category {
            valid_category = true
        }
    }
    if valid_category == false {
        return {
            "status": "error",
            "message": "invalid category: " + category,
            "path": "",
            "error_code": ERROR_VALIDATION
        }
    }
    return {"status": "success", "message": "ok", "path": "", "error_code": 0}
}

main {
    let result = skill_manager_create("test", "invalid-category", "content")
    print(result["status"])
    print(result["message"])
    print(result["error_code"])
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "error" in result["stdout"]
        assert "invalid category" in result["stdout"]
    
    def test_create_and_read_skill(self, cleanup_test_skills, agents_dir):
        """应该能创建并读取skill."""
        content = """
const SKILL_CATEGORIES = ["error-patterns", "code-quality", "testing", "architecture", "general"]
const SKILLS_BASE_PATH = "agents/skills"
const ERROR_VALIDATION = 1
const ERROR_IO = 101
const ERROR_NOT_FOUND = 201
const ERROR_ALREADY_EXISTS = 202

fn skill_manager_create(name: str, category: str, content: str) -> map {
    if name == "" {
        return {"status": "error", "message": "name cannot be empty", "path": "", "error_code": ERROR_VALIDATION}
    }
    
    let valid_category = false
    for cat in SKILL_CATEGORIES {
        if cat == category {
            valid_category = true
        }
    }
    if valid_category == false {
        return {"status": "error", "message": "invalid category", "path": "", "error_code": ERROR_VALIDATION}
    }
    
    let skill_dir = SKILLS_BASE_PATH + "/" + category + "/" + name
    let skill_path = skill_dir + "/SKILL.md"
    
    if path_exists(skill_path) {
        return {"status": "error", "message": "skill already exists", "path": skill_path, "error_code": ERROR_ALREADY_EXISTS}
    }
    
    let mkdir_result = exec("mkdir -p " + skill_dir, true)
    if mkdir_result["returncode"] != 0 {
        return {"status": "error", "message": "failed to create directory", "path": "", "error_code": ERROR_IO}
    }
    
    let write_result = write_file(skill_path, content)
    if write_result == false {
        return {"status": "error", "message": "failed to write", "path": "", "error_code": ERROR_IO}
    }
    
    return {"status": "success", "message": "Skill created: " + name, "path": skill_path, "error_code": 0}
}

fn skill_manager_read(name: str, category: str) -> map {
    let skill_path = SKILLS_BASE_PATH + "/" + category + "/" + name + "/SKILL.md"
    
    if path_exists(skill_path) == false {
        return {"status": "error", "message": "skill not found", "content": "", "path": "", "error_code": ERROR_NOT_FOUND}
    }
    
    let content = read_file(skill_path)
    return {"status": "success", "message": "Skill loaded", "content": content, "path": skill_path, "error_code": 0}
}

fn skill_manager_delete(name: str, category: str) -> map {
    let skill_dir = SKILLS_BASE_PATH + "/" + category + "/" + name
    
    if path_exists(skill_dir) == false {
        return {"status": "error", "message": "skill not found", "error_code": ERROR_NOT_FOUND}
    }
    
    let rm_result = exec("rm -rf " + skill_dir, true)
    if rm_result["returncode"] != 0 {
        return {"status": "error", "message": "failed to delete", "error_code": ERROR_IO}
    }
    
    return {"status": "success", "message": "Skill deleted: " + name, "error_code": 0}
}

main {
    // 先删除可能存在的skill
    skill_manager_delete("test-create-read", "error-patterns")
    
    // 创建
    let create_result = skill_manager_create(
        "test-create-read",
        "error-patterns",
        "---\\nname: test\\n---\\n# Test Skill"
    )
    print("Create: " + create_result["status"])
    if create_result["status"] == "error" {
        print("Create error: " + create_result["message"])
    }
    
    // 读取
    let read_result = skill_manager_read("test-create-read", "error-patterns")
    print("Read: " + read_result["status"])
    print("Content contains test: " + str(regex_search("Test Skill", read_result["content"]) != null))
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "Create: success" in result["stdout"]
        assert "Read: success" in result["stdout"]
        assert "True" in result["stdout"] or "true" in result["stdout"]
    
    def test_delete_skill(self, cleanup_test_skills, agents_dir):
        """应该能删除skill."""
        content = """
const SKILL_CATEGORIES = ["error-patterns", "code-quality", "testing", "architecture", "general"]
const SKILLS_BASE_PATH = "agents/skills"
const ERROR_IO = 101
const ERROR_NOT_FOUND = 201

fn skill_manager_delete(name: str, category: str) -> map {
    let skill_dir = SKILLS_BASE_PATH + "/" + category + "/" + name
    
    if path_exists(skill_dir) == false {
        return {"status": "error", "message": "skill not found", "error_code": ERROR_NOT_FOUND}
    }
    
    let rm_result = exec("rm -rf " + skill_dir, true)
    if rm_result["returncode"] != 0 {
        return {"status": "error", "message": "failed to delete", "error_code": ERROR_IO}
    }
    
    return {"status": "success", "message": "Skill deleted: " + name, "error_code": 0}
}

main {
    // 先创建
    exec("mkdir -p agents/skills/error-patterns/test-delete", true)
    write_file("agents/skills/error-patterns/test-delete/SKILL.md", "test")
    
    // 删除
    let result = skill_manager_delete("test-delete", "error-patterns")
    print(result["status"])
    print(result["message"])
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "success" in result["stdout"]
        assert "deleted" in result["stdout"]


# ── Skill Matcher Tests ─────────────────────────────────────────

class TestSkillMatcher:
    """Skill Matcher关键词提取测试."""
    
    def test_extract_keywords_error(self, agents_dir):
        """应该从错误消息中提取关键词."""
        content = """
fn skill_matcher_extract_keywords(context: str) -> list {
    let keywords = []
    let lower_context = context.lower()
    
    let error_keywords = ["division", "zero", "error", "exception", "fail", "crash"]
    for kw in error_keywords {
        if regex_search(kw, lower_context) != null {
            keywords.append(kw)
        }
    }
    
    return keywords
}

main {
    let keywords = skill_matcher_extract_keywords("Division by zero error")
    print(len(keywords))
    for kw in keywords {
        print(kw)
    }
}
"""
        result = run_helen_file(content, agents_dir)
        
        # 应该提取到"division", "zero", "error"
        assert "3" in result["stdout"]
        assert "division" in result["stdout"]
        assert "zero" in result["stdout"]
        assert "error" in result["stdout"]
    
    def test_extract_keywords_quality(self, agents_dir):
        """应该从质量相关文本中提取关键词."""
        content = """
fn skill_matcher_extract_keywords(context: str) -> list {
    let keywords = []
    let lower_context = context.lower()
    
    let quality_keywords = ["complexity", "quality", "score", "metric", "security"]
    for kw in quality_keywords {
        if regex_search(kw, lower_context) != null {
            keywords.append(kw)
        }
    }
    
    return keywords
}

main {
    let keywords = skill_matcher_extract_keywords("Code complexity too high")
    print(len(keywords))
    for kw in keywords {
        print(kw)
    }
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "complexity" in result["stdout"]


# ── Skill Learner Tests ─────────────────────────────────────────

class TestSkillLearner:
    """Skill Learner类别确定测试."""
    
    def test_determine_category_error_patterns(self, agents_dir):
        """错误码1-100应该映射到error-patterns."""
        content = """
fn skill_learner_determine_category(error: map) -> str {
    let error_code = 0
    if error["code"] != null {
        error_code = error["code"]
    }
    
    match error_code {
        case 1..100 { return "error-patterns" }
        case 101..200 { return "code-quality" }
        case 201..300 { return "testing" }
        case 301..400 { return "architecture" }
        default { return "general" }
    }
}

main {
    let error = {"code": 50, "message": "test"}
    let category = skill_learner_determine_category(error)
    print(category)
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "error-patterns" in result["stdout"]
    
    def test_determine_category_code_quality(self, agents_dir):
        """错误码101-200应该映射到code-quality."""
        content = """
fn skill_learner_determine_category(error: map) -> str {
    let error_code = 0
    if error["code"] != null {
        error_code = error["code"]
    }
    
    match error_code {
        case 1..100 { return "error-patterns" }
        case 101..200 { return "code-quality" }
        case 201..300 { return "testing" }
        case 301..400 { return "architecture" }
        default { return "general" }
    }
}

main {
    let error = {"code": 150, "message": "test"}
    let category = skill_learner_determine_category(error)
    print(category)
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "code-quality" in result["stdout"]
    
    def test_learn_skipped_when_not_confirmed(self, agents_dir):
        """未确认的修复应该跳过学习."""
        content = """
fn skill_learner_learn(error: map, fix: str, confirmed: bool) -> map {
    if confirmed == false {
        return {
            "status": "skipped",
            "path": "",
            "category": "",
            "name": "",
            "error_code": 0
        }
    }
    return {"status": "saved", "path": "", "category": "", "name": "", "error_code": 0}
}

main {
    let error = {"code": 50, "message": "test error"}
    let result = skill_learner_learn(error, "fix", false)
    print(result["status"])
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "skipped" in result["stdout"]


# ── Integration Tests ───────────────────────────────────────────

class TestIntegration:
    """集成测试."""
    
    def test_full_workflow(self, cleanup_test_skills, agents_dir):
        """测试完整工作流."""
        content = """
const SKILL_CATEGORIES = ["error-patterns", "code-quality", "testing", "architecture", "general"]
const SKILLS_BASE_PATH = "agents/skills"
const ERROR_VALIDATION = 1
const ERROR_IO = 101
const ERROR_NOT_FOUND = 201
const ERROR_ALREADY_EXISTS = 202

fn skill_manager_create(name: str, category: str, content: str) -> map {
    if name == "" {
        return {"status": "error", "message": "name cannot be empty", "path": "", "error_code": ERROR_VALIDATION}
    }
    
    let skill_dir = SKILLS_BASE_PATH + "/" + category + "/" + name
    let skill_path = skill_dir + "/SKILL.md"
    
    let mkdir_result = exec("mkdir -p " + skill_dir, true)
    if mkdir_result["returncode"] != 0 {
        return {"status": "error", "message": "mkdir failed", "path": "", "error_code": ERROR_IO}
    }
    
    let write_result = write_file(skill_path, content)
    if write_result == false {
        return {"status": "error", "message": "write failed", "path": "", "error_code": ERROR_IO}
    }
    
    return {"status": "success", "message": "created", "path": skill_path, "error_code": 0}
}

fn skill_manager_read(name: str, category: str) -> map {
    let skill_path = SKILLS_BASE_PATH + "/" + category + "/" + name + "/SKILL.md"
    
    if path_exists(skill_path) == false {
        return {"status": "error", "message": "not found", "content": "", "path": "", "error_code": ERROR_NOT_FOUND}
    }
    
    let content = read_file(skill_path)
    return {"status": "success", "message": "loaded", "content": content, "path": skill_path, "error_code": 0}
}

fn skill_manager_delete(name: str, category: str) -> map {
    let skill_dir = SKILLS_BASE_PATH + "/" + category + "/" + name
    
    if path_exists(skill_dir) == false {
        return {"status": "error", "message": "not found", "error_code": ERROR_NOT_FOUND}
    }
    
    let rm_result = exec("rm -rf " + skill_dir, true)
    if rm_result["returncode"] != 0 {
        return {"status": "error", "message": "rm failed", "error_code": ERROR_IO}
    }
    
    return {"status": "success", "message": "deleted", "error_code": 0}
}

main {
    // 创建
    let create_result = skill_manager_create(
        "test-workflow",
        "error-patterns",
        "---\\nname: test\\n---\\n# Test"
    )
    print("Create: " + create_result["status"])
    
    // 读取
    let read_result = skill_manager_read("test-workflow", "error-patterns")
    print("Read: " + read_result["status"])
    
    // 删除
    let delete_result = skill_manager_delete("test-workflow", "error-patterns")
    print("Delete: " + delete_result["status"])
}
"""
        result = run_helen_file(content, agents_dir)
        
        assert "Create: success" in result["stdout"]
        assert "Read: success" in result["stdout"]
        assert "Delete: success" in result["stdout"]
