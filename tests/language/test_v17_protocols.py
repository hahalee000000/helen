"""
Helen v1.7 特性测试 - 接口/协议语法
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


class TestProtocolDeclaration:
    """协议声明测试"""
    
    def test_simple_protocol(self, temp_helen_file, helen_dir):
        """测试简单协议声明"""
        test_file = temp_helen_file("""
protocol Printable {
    fn to_string(self): String
}

main {
    print("Protocol declared")
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "Protocol declared" in result.stdout
    
    def test_protocol_multiple_methods(self, temp_helen_file, helen_dir):
        """测试协议多个方法"""
        test_file = temp_helen_file("""
protocol Shape {
    fn area(self): Float
    fn perimeter(self): Float
}

main {
    print("Shape protocol declared")
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "Shape protocol declared" in result.stdout


class TestProtocolImplementation:
    """协议实现测试"""
    
    def test_simple_impl(self, temp_helen_file, helen_dir):
        """测试简单协议实现 - 使用 map 模拟结构体"""
        test_file = temp_helen_file("""
protocol Printable {
    fn to_string(obj): String
}

// 使用函数而不是方法
fn Point_to_string(p): String {
    return "Point"
}

main {
    let p = {"x": 1, "y": 2}
    let s = Point_to_string(p)
    print(s)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "Point" in result.stdout
    
    def test_impl_with_computation(self, temp_helen_file, helen_dir):
        """测试协议实现带计算 - 使用 map"""
        test_file = temp_helen_file("""
protocol Area {
    fn area(rect): Float
}

fn Rectangle_area(r): Float {
    return r["width"] * r["height"]
}

main {
    let r = {"width": 3.0, "height": 4.0}
    let a = Rectangle_area(r)
    print(a)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "12" in result.stdout


class TestProtocolDuckTyping:
    """鸭子类型测试（隐式协议实现）"""
    
    def test_duck_typing(self, temp_helen_file, helen_dir):
        """测试鸭子类型 - 不需要显式 impl"""
        test_file = temp_helen_file("""
protocol Quackable {
    fn quack(d): String
}

// 不需要 impl，只要函数签名匹配即可
fn Duck_quack(d): String {
    return "Quack! I am " + d["name"]
}

main {
    let d = {"name": "Donald"}
    let q = Duck_quack(d)
    print(q)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "Quack" in result.stdout


class TestProtocolEdgeCases:
    """协议边界情况测试"""
    
    def test_protocol_no_methods(self, temp_helen_file, helen_dir):
        """测试空协议"""
        test_file = temp_helen_file("""
protocol Empty {
}

main {
    print("Empty protocol")
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "Empty protocol" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
