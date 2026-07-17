"""
Helen v1.8 特性测试 - Struct方法支持（使用map模拟）

由于Helen目前没有struct声明语法，我们使用map和函数来模拟struct方法。
这展示了如何使用现有特性实现类似struct方法的功能。
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


class TestStructLikePatterns:
    """使用map和函数模拟struct方法"""

    def test_map_with_functions(self, temp_helen_file, helen_dir):
        """测试使用map和函数模拟struct方法"""
        test_file = temp_helen_file("""
fn point_to_string(p): String {
    return "Point(" + str(p["x"]) + ", " + str(p["y"]) + ")"
}

main {
    let p = {"x": 3, "y": 4}
    print(point_to_string(p))
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "Point(3, 4)" in result.stdout

    def test_map_with_computation_functions(self, temp_helen_file, helen_dir):
        """测试使用函数对map进行计算"""
        test_file = temp_helen_file("""
fn rectangle_area(r): Int {
    return r["width"] * r["height"]
}

fn rectangle_perimeter(r): Int {
    return 2 * (r["width"] + r["height"])
}

main {
    let r = {"width": 5, "height": 3}
    print(rectangle_area(r))
    print(rectangle_perimeter(r))
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "15" in result.stdout  # area
        assert "16" in result.stdout  # perimeter


class TestMethodStyleWithClosures:
    """使用函数模拟方法风格"""

    def test_function_composition(self, temp_helen_file, helen_dir):
        """测试使用函数组合模拟方法链"""
        test_file = temp_helen_file("""
fn counter_increment(n) {
    return n + 1
}

main {
    let c0 = 0
    let c1 = counter_increment(c0)
    let c2 = counter_increment(c1)
    print(c2)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "2" in result.stdout


class TestPipeWithStructLike:
    """管道与struct-like模式结合"""

    def test_pipe_with_map_operations(self, temp_helen_file, helen_dir):
        """测试管道操作与map操作"""
        test_file = temp_helen_file("""
fn get_x(p) {
    return p["x"]
}

fn double(n) {
    return n * 2
}

main {
    let p = {"x": 5, "y": 3}
    let result = p |> get_x |> double
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
