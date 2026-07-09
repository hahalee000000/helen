"""
Helen v1.7 特性测试 - 闭包/匿名函数
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


class TestAnonymousFunctions:
    """匿名函数测试"""
    
    def test_simple_lambda(self, temp_helen_file, helen_dir):
        """测试简单匿名函数"""
        test_file = temp_helen_file("""
main {
    let add = fn(x, y) { return x + y }
    let result = add(3, 4)
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
        assert "7" in result.stdout
    
    def test_lambda_no_params(self, temp_helen_file, helen_dir):
        """测试无参数匿名函数"""
        test_file = temp_helen_file("""
main {
    let greet = fn() { return "Hello" }
    let result = greet()
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
        assert "Hello" in result.stdout
    
    def test_lambda_single_param(self, temp_helen_file, helen_dir):
        """测试单参数匿名函数"""
        test_file = temp_helen_file("""
main {
    let double = fn(x) { return x * 2 }
    let result = double(5)
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
    
    def test_lambda_as_argument(self, temp_helen_file, helen_dir):
        """测试匿名函数作为参数"""
        test_file = temp_helen_file("""
fn apply(f, x) {
    return f(x)
}

main {
    let result = apply(fn(x) { return x * 2 }, 5)
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
    
    def test_lambda_as_return_value(self, temp_helen_file, helen_dir):
        """测试匿名函数作为返回值"""
        test_file = temp_helen_file("""
fn make_adder(n) {
    return fn(x) { return x + n }
}

main {
    let add5 = make_adder(5)
    let result = add5(3)
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
        assert "8" in result.stdout


class TestClosures:
    """闭包测试"""
    
    def test_simple_closure(self, temp_helen_file, helen_dir):
        """测试简单闭包"""
        test_file = temp_helen_file("""
fn make_counter() {
    let count = 0
    return fn() {
        count = count + 1
        return count
    }
}

main {
    let counter = make_counter()
    let r1 = counter()
    let r2 = counter()
    let r3 = counter()
    print(r1)
    print(r2)
    print(r3)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        lines = result.stdout.strip().split('\n')
        assert "1" in lines[0]
        assert "2" in lines[1]
        assert "3" in lines[2]
    
    def test_closure_captures_variable(self, temp_helen_file, helen_dir):
        """测试闭包捕获变量"""
        test_file = temp_helen_file("""
fn make_adder(n) {
    return fn(x) { return x + n }
}

main {
    let add10 = make_adder(10)
    let result = add10(5)
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
    
    def test_multiple_closures_independent(self, temp_helen_file, helen_dir):
        """测试多个闭包独立"""
        test_file = temp_helen_file("""
fn make_counter() {
    let count = 0
    return fn() {
        count = count + 1
        return count
    }
}

main {
    let counter1 = make_counter()
    let counter2 = make_counter()
    
    let r1 = counter1()
    let r2 = counter1()
    let r3 = counter2()
    let r4 = counter1()
    let r5 = counter2()
    
    print(r1)
    print(r2)
    print(r3)
    print(r4)
    print(r5)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        lines = result.stdout.strip().split('\n')
        assert "1" in lines[0]
        assert "2" in lines[1]
        assert "1" in lines[2]
        assert "3" in lines[3]
        assert "2" in lines[4]
    
    def test_closure_modifies_captured(self, temp_helen_file, helen_dir):
        """测试闭包修改捕获的变量"""
        test_file = temp_helen_file("""
fn make_accumulator() {
    let total = 0
    return fn(n) {
        total = total + n
        return total
    }
}

main {
    let acc = make_accumulator()
    let r1 = acc(5)
    let r2 = acc(10)
    let r3 = acc(3)
    print(r1)
    print(r2)
    print(r3)
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        lines = result.stdout.strip().split('\n')
        assert "5" in lines[0]
        assert "15" in lines[1]
        assert "18" in lines[2]
    
    def test_nested_closures(self, temp_helen_file, helen_dir):
        """测试嵌套闭包"""
        test_file = temp_helen_file("""
fn outer() {
    let x = 10
    return fn() {
        let y = 20
        return fn() {
            return x + y
        }
    }
}

main {
    let f = outer()
    let g = f()
    let result = g()
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
        assert "30" in result.stdout


class TestClosureEdgeCases:
    """闭包边界情况测试"""
    
    def test_closure_empty_body(self, temp_helen_file, helen_dir):
        """测试空函数体"""
        test_file = temp_helen_file("""
main {
    let noop = fn() {}
    let result = noop()
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
        # 空函数返回 None，打印为 "None" 或空行
        assert "None" in result.stdout or result.stdout.strip() == ""
    
    def test_closure_immediate_invocation(self, temp_helen_file, helen_dir):
        """测试立即执行的匿名函数"""
        test_file = temp_helen_file("""
main {
    let result = fn(x, y) { return x + y }(3, 4)
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
        assert "7" in result.stdout

    def test_closure_recursive(self, temp_helen_file, helen_dir):
        """测试递归闭包"""
        test_file = temp_helen_file("""
let factorial = fn(n) {
    if n <= 1 {
        return 1
    }
    return n * factorial(n - 1)
}

main {
    let result = factorial(5)
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
        assert "120" in result.stdout

    def test_closure_recursive_fibonacci(self, temp_helen_file, helen_dir):
        """递归闭包 — 斐波那契（多次递归分支）"""
        test_file = temp_helen_file("""
let fib = fn(n) {
    if n <= 1 {
        return n
    }
    return fib(n - 1) + fib(n - 2)
}

main {
    print(fib(10))
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "55" in result.stdout

    def test_closure_recursive_const(self, temp_helen_file, helen_dir):
        """const 初始化的递归闭包"""
        test_file = temp_helen_file("""
const repeat = fn(s: str, n: int): str {
    if n <= 0 {
        return ""
    }
    return s + repeat(s, n - 1)
}

main {
    print(repeat("ab", 3))
}
""")
        result = subprocess.run(
            ["helen", str(test_file)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        assert result.returncode == 0
        assert "ababab" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
