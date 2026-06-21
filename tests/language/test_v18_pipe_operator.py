"""
Helen v1.8 特性测试 - 管道操作符 |>
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


class TestPipeOperatorBasic:
    """管道操作符基本测试"""

    def test_pipe_single_function(self, temp_helen_file, helen_dir):
        """测试单个管道：value |> fn"""
        test_file = temp_helen_file("""
fn double(x) {
    return x * 2
}

main {
    let result = 5 |> double
    print(result)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "10" in result.stdout

    def test_pipe_chained(self, temp_helen_file, helen_dir):
        """测试链式管道：value |> fn1 |> fn2"""
        test_file = temp_helen_file("""
fn double(x) {
    return x * 2
}

fn add_one(x) {
    return x + 1
}

main {
    let result = 5 |> double |> add_one
    print(result)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "11" in result.stdout  # (5 * 2) + 1 = 11

    def test_pipe_with_builtin(self, temp_helen_file, helen_dir):
        """测试管道使用内置函数"""
        test_file = temp_helen_file("""
main {
    let result = "hello" |> upper
    print(result)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "HELLO" in result.stdout

    def test_pipe_with_closure(self, temp_helen_file, helen_dir):
        """测试管道使用闭包"""
        test_file = temp_helen_file("""
main {
    let add = fn(x, y) { return x + y }
    let add5 = fn(x) { return add(x, 5) }
    let result = 10 |> add5
    print(result)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "15" in result.stdout


class TestPipeOperatorAdvanced:
    """管道操作符高级测试"""

    def test_pipe_with_list_operations(self, temp_helen_file, helen_dir):
        """测试管道与列表操作"""
        test_file = temp_helen_file("""
main {
    let numbers = [1, 2, 3, 4, 5]
    let result = numbers |> len
    print(result)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "5" in result.stdout

    def test_pipe_with_string_operations(self, temp_helen_file, helen_dir):
        """测试管道与字符串操作"""
        test_file = temp_helen_file("""
main {
    let result = "  hello world  " |> strip |> upper
    print(result)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "HELLO WORLD" in result.stdout

    def test_pipe_multiple_chains(self, temp_helen_file, helen_dir):
        """测试多个管道链"""
        test_file = temp_helen_file("""
fn inc(x) { return x + 1 }
fn double(x) { return x * 2 }

main {
    let a = 1 |> inc |> inc |> inc
    let b = 10 |> double |> double
    print(a)
    print(b)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "4" in result.stdout  # 1 + 1 + 1 + 1
        assert "40" in result.stdout  # 10 * 2 * 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
