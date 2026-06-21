"""
Helen v1.8 特性测试 - 模式匹配增强
"""
import pytest
import subprocess
from pathlib import Path


@pytest.fixture
def helen_dir():
    return Path(__file__).parent.parent.parent


@pytest.fixture
def temp_helen_file(tmp_path):
    """Create a temporary .helen file for testing."""
    def _create(content: str, name: str = "test.helen") -> Path:
        file_path = tmp_path / name
        file_path.write_text(content)
        return file_path
    return _create


class TestWildcardPattern:
    """通配符模式测试"""

    def test_wildcard_matches_anything(self, temp_helen_file, helen_dir):
        """测试通配符匹配任何值"""
        test_file = temp_helen_file("""
main {
    let value = 42
    match value {
        case 1 { print("one") }
        case _ { print("other") }
    }
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "other" in result.stdout

    def test_wildcard_as_default(self, temp_helen_file, helen_dir):
        """测试通配符作为默认分支"""
        test_file = temp_helen_file("""
fn classify(x) {
    match x {
        case 0 { return "zero" }
        case 1 { return "one" }
        case _ { return "many" }
    }
}

main {
    print(classify(0))
    print(classify(1))
    print(classify(99))
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "zero" in result.stdout
        assert "one" in result.stdout
        assert "many" in result.stdout


class TestVariableBinding:
    """变量绑定模式测试"""

    def test_variable_binding_captures_value(self, temp_helen_file, helen_dir):
        """测试变量绑定捕获匹配的值"""
        test_file = temp_helen_file("""
main {
    let value = 42
    match value {
        case x { print(x) }
    }
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "42" in result.stdout

    def test_variable_binding_with_guard(self, temp_helen_file, helen_dir):
        """测试变量绑定配合guard条件"""
        test_file = temp_helen_file("""
fn classify_num(x) {
    match x {
        case n if n > 0 { return "positive: " + str(n) }
        case n if n < 0 { return "negative: " + str(n) }
        case _ { return "zero" }
    }
}

main {
    print(classify_num(5))
    print(classify_num(-3))
    print(classify_num(0))
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "positive: 5" in result.stdout
        assert "negative: -3" in result.stdout
        assert "zero" in result.stdout


class TestTypePattern:
    """类型模式测试"""

    def test_type_pattern_string(self, temp_helen_file, helen_dir):
        """测试类型模式匹配字符串"""
        test_file = temp_helen_file("""
fn describe_type(value) {
    match value {
        case is String { return "it's a string" }
        case is Int { return "it's an int" }
        case _ { return "unknown type" }
    }
}

main {
    print(describe_type("hello"))
    print(describe_type(42))
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "it's a string" in result.stdout
        assert "it's an int" in result.stdout

    def test_type_pattern_with_binding(self, temp_helen_file, helen_dir):
        """测试类型模式配合变量绑定"""
        test_file = temp_helen_file("""
main {
    let value = "hello"
    match value {
        case is String s { print("string: " + s) }
        case _ { print("not a string") }
    }
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "string: hello" in result.stdout


class TestPatternCombinations:
    """模式组合测试"""

    def test_range_and_wildcard(self, temp_helen_file, helen_dir):
        """测试范围模式和通配符组合"""
        test_file = temp_helen_file("""
fn grade(score) {
    match score {
        case 90..100 { return "A" }
        case 80..89 { return "B" }
        case 70..79 { return "C" }
        case _ { return "F" }
    }
}

main {
    print(grade(95))
    print(grade(85))
    print(grade(75))
    print(grade(50))
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "A" in result.stdout
        assert "B" in result.stdout
        assert "C" in result.stdout
        assert "F" in result.stdout

    def test_variable_binding_in_range(self, temp_helen_file, helen_dir):
        """测试变量绑定与范围模式"""
        test_file = temp_helen_file("""
main {
    let score = 85
    match score {
        case n if n >= 90 { print("excellent: " + str(n)) }
        case n if n >= 80 { print("good: " + str(n)) }
        case n { print("score: " + str(n)) }
    }
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "good: 85" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
