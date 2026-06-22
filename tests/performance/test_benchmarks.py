"""Performance benchmark tests for Helen language components.

These tests measure the execution time and memory usage of key components:
- Lexer (Scanner)
- Parser
- Interpreter
- Environment (variable lookup)
- Import resolver

Run with: pytest tests/performance/ -v
"""

import time
import tracemalloc
import pytest
from pathlib import Path

from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.interpreter.interpreter import Interpreter
from helen.interpreter.environment import Environment


# ============================================================================
# Lexer Benchmarks
# ============================================================================

class TestLexerPerformance:
    """词法分析器性能测试"""

    def test_simple_tokens(self):
        """测试简单token的词法分析速度"""
        source = "let x = 42;" * 1000
        scanner = Scanner(source)
        
        start = time.perf_counter()
        tokens = scanner.scan_all()
        elapsed = time.perf_counter() - start
        
        print(f"\nLexer: 1000 simple statements in {elapsed*1000:.2f}ms")
        print(f"  Tokens generated: {len(tokens)}")
        print(f"  Speed: {len(tokens)/elapsed:.0f} tokens/sec")
        
        # 应该在100ms内完成
        assert elapsed < 0.1, f"Lexer too slow: {elapsed:.3f}s"

    def test_string_literals(self):
        """测试字符串字面量解析性能"""
        source = 'let s = "hello world";' * 500
        scanner = Scanner(source)
        
        start = time.perf_counter()
        tokens = scanner.scan_all()
        elapsed = time.perf_counter() - start
        
        print(f"\nLexer: 500 string literals in {elapsed*1000:.2f}ms")
        print(f"  Speed: {500/elapsed:.0f} strings/sec")
        
        assert elapsed < 0.1

    def test_long_string(self):
        """测试长字符串解析性能"""
        long_string = "x" * 10000
        source = f'let s = "{long_string}";'
        scanner = Scanner(source)
        
        start = time.perf_counter()
        tokens = scanner.scan_all()
        elapsed = time.perf_counter() - start
        
        print(f"\nLexer: 10KB string in {elapsed*1000:.2f}ms")
        
        assert elapsed < 0.05

    def test_complex_operators(self):
        """测试复杂运算符解析"""
        source = "let x = a + b * c - d / e % f;" * 500
        scanner = Scanner(source)
        
        start = time.perf_counter()
        tokens = scanner.scan_all()
        elapsed = time.perf_counter() - start
        
        print(f"\nLexer: 500 complex expressions in {elapsed*1000:.2f}ms")
        
        assert elapsed < 0.1


# ============================================================================
# Parser Benchmarks
# ============================================================================

class TestParserPerformance:
    """解析器性能测试"""

    def test_simple_program(self):
        """测试简单程序解析速度"""
        source = "let x = 1; let y = 2; let z = x + y;" * 200
        tokens = Scanner(source).scan_all()
        
        start = time.perf_counter()
        parser = Parser(tokens)
        ast = parser.parse()
        elapsed = time.perf_counter() - start
        
        print(f"\nParser: 600 statements in {elapsed*1000:.2f}ms")
        print(f"  Speed: {600/elapsed:.0f} stmts/sec")
        
        assert elapsed < 0.2

    def test_function_declarations(self):
        """测试函数声明解析"""
        source = "fn add(a, b) { return a + b; }" * 100
        tokens = Scanner(source).scan_all()
        
        start = time.perf_counter()
        parser = Parser(tokens)
        ast = parser.parse()
        elapsed = time.perf_counter() - start
        
        print(f"\nParser: 100 function declarations in {elapsed*1000:.2f}ms")
        
        assert elapsed < 0.2

    def test_nested_expressions(self):
        """测试嵌套表达式解析"""
        # 创建深度嵌套的表达式
        expr = "1"
        for i in range(50):
            expr = f"({expr} + {i})"
        source = f"let x = {expr};"
        tokens = Scanner(source).scan_all()
        
        start = time.perf_counter()
        parser = Parser(tokens)
        ast = parser.parse()
        elapsed = time.perf_counter() - start
        
        print(f"\nParser: 50-level nested expression in {elapsed*1000:.2f}ms")
        
        assert elapsed < 0.1


# ============================================================================
# Interpreter Benchmarks
# ============================================================================

class TestInterpreterPerformance:
    """解释器性能测试"""

    def test_arithmetic_loop(self):
        """测试算术运算循环"""
        source = """
        let sum = 0;
        let i = 0;
        while i < 1000 {
            sum = sum + i;
            i = i + 1;
        }
        """
        tokens = Scanner(source).scan_all()
        ast = Parser(tokens).parse()
        interpreter = Interpreter()
        
        start = time.perf_counter()
        interpreter.interpret(ast)
        elapsed = time.perf_counter() - start
        
        print(f"\nInterpreter: 1000 iterations loop in {elapsed*1000:.2f}ms")
        print(f"  Speed: {1000/elapsed:.0f} iterations/sec")
        
        # 应该在500ms内完成
        assert elapsed < 0.5

    def test_function_calls(self):
        """测试函数调用性能"""
        source = """
        fn add(a, b) {
            return a + b;
        }
        
        let result = 0;
        let i = 0;
        while i < 100 {
            result = add(result, i);
            i = i + 1;
        }
        """
        tokens = Scanner(source).scan_all()
        ast = Parser(tokens).parse()
        interpreter = Interpreter()
        
        start = time.perf_counter()
        interpreter.interpret(ast)
        elapsed = time.perf_counter() - start
        
        print(f"\nInterpreter: 100 function calls in {elapsed*1000:.2f}ms")
        
        assert elapsed < 0.5

    def test_variable_lookup(self):
        """测试变量查找性能"""
        source = """
        let x = 1;
        let y = 2;
        let z = 3;
        let result = x + y + z;
        """
        tokens = Scanner(source).scan_all()
        ast = Parser(tokens).parse()
        interpreter = Interpreter()
        
        start = time.perf_counter()
        for _ in range(100):
            interpreter.interpret(ast)
        elapsed = time.perf_counter() - start
        
        print(f"\nInterpreter: 100 executions with variable lookup in {elapsed*1000:.2f}ms")
        
        assert elapsed < 0.5


# ============================================================================
# Environment Benchmarks
# ============================================================================

class TestEnvironmentPerformance:
    """环境（作用域）性能测试"""

    def test_variable_lookup_shallow(self):
        """测试浅层作用域变量查找"""
        env = Environment()
        env.define("x", 42)
        
        start = time.perf_counter()
        for _ in range(10000):
            value = env.lookup("x")
        elapsed = time.perf_counter() - start
        
        print(f"\nEnvironment: 10000 shallow lookups in {elapsed*1000:.2f}ms")
        print(f"  Speed: {10000/elapsed:.0f} lookups/sec")
        
        assert elapsed < 0.1

    def test_variable_lookup_deep(self):
        """测试深层作用域变量查找"""
        # 创建10层嵌套的作用域
        env = Environment()
        env.define("x", 42)
        
        current = env
        for i in range(10):
            current = current.enter_scope()
        
        start = time.perf_counter()
        for _ in range(10000):
            value = current.lookup("x")
        elapsed = time.perf_counter() - start
        
        print(f"\nEnvironment: 10000 deep lookups (10 levels) in {elapsed*1000:.2f}ms")
        print(f"  Speed: {10000/elapsed:.0f} lookups/sec")
        
        assert elapsed < 0.2

    def test_scope_creation(self):
        """测试作用域创建性能"""
        env = Environment()
        
        start = time.perf_counter()
        for _ in range(1000):
            child = env.enter_scope()
        elapsed = time.perf_counter() - start
        
        print(f"\nEnvironment: 1000 scope creations in {elapsed*1000:.2f}ms")
        
        assert elapsed < 0.1


# ============================================================================
# Memory Benchmarks
# ============================================================================

class TestMemoryUsage:
    """内存使用测试"""

    def test_lexer_memory(self):
        """测试词法分析器内存使用"""
        tracemalloc.start()
        
        source = "let x = 1 + 2 * 3;" * 1000
        scanner = Scanner(source)
        tokens = scanner.scan_all()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"\nLexer Memory:")
        print(f"  Current: {current / 1024:.2f} KB")
        print(f"  Peak: {peak / 1024:.2f} KB")
        print(f"  Tokens: {len(tokens)}")
        print(f"  Per token: {peak / len(tokens):.2f} bytes")
        
        # 峰值内存应该小于10MB
        assert peak < 10_000_000

    def test_parser_memory(self):
        """测试解析器内存使用"""
        tracemalloc.start()
        
        source = "let x = 1; let y = 2;" * 500
        tokens = Scanner(source).scan_all()
        parser = Parser(tokens)
        ast = parser.parse()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"\nParser Memory:")
        print(f"  Current: {current / 1024:.2f} KB")
        print(f"  Peak: {peak / 1024:.2f} KB")
        
        # 峰值内存应该小于20MB
        assert peak < 20_000_000

    def test_interpreter_memory(self):
        """测试解释器内存使用"""
        tracemalloc.start()
        
        source = """
        let sum = 0;
        let i = 0;
        while i < 100 {
            sum = sum + i;
            i = i + 1;
        }
        """
        tokens = Scanner(source).scan_all()
        ast = Parser(tokens).parse()
        interpreter = Interpreter()
        interpreter.interpret(ast)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"\nInterpreter Memory:")
        print(f"  Current: {current / 1024:.2f} KB")
        print(f"  Peak: {peak / 1024:.2f} KB")
        
        # 峰值内存应该小于50MB
        assert peak < 50_000_000


# ============================================================================
# Integration Benchmarks
# ============================================================================

class TestIntegrationPerformance:
    """集成性能测试（完整流程）"""

    def test_full_pipeline_simple(self):
        """测试简单程序的完整执行流程"""
        source = """
        fn factorial(n) {
            if n <= 1 {
                return 1;
            }
            return n * factorial(n - 1);
        }
        
        let result = factorial(10);
        print(result);
        """
        
        start = time.perf_counter()
        
        # Lexing
        tokens = Scanner(source).scan_all()
        lex_time = time.perf_counter() - start
        
        # Parsing
        start = time.perf_counter()
        ast = Parser(tokens).parse()
        parse_time = time.perf_counter() - start
        
        # Interpretation
        start = time.perf_counter()
        interpreter = Interpreter()
        result = interpreter.interpret(ast)
        interp_time = time.perf_counter() - start
        
        total_time = lex_time + parse_time + interp_time
        
        print(f"\nFull Pipeline (factorial):")
        print(f"  Lexing: {lex_time*1000:.2f}ms")
        print(f"  Parsing: {parse_time*1000:.2f}ms")
        print(f"  Interpretation: {interp_time*1000:.2f}ms")
        print(f"  Total: {total_time*1000:.2f}ms")
        
        assert total_time < 1.0

    def test_full_pipeline_loop(self):
        """测试循环程序的完整执行流程"""
        source = """
        let sum = 0;
        for i in range(100) {
            sum = sum + i;
        }
        """
        
        start = time.perf_counter()
        tokens = Scanner(source).scan_all()
        ast = Parser(tokens).parse()
        interpreter = Interpreter()
        result = interpreter.interpret(ast)
        elapsed = time.perf_counter() - start
        
        print(f"\nFull Pipeline (loop): {elapsed*1000:.2f}ms")
        
        assert elapsed < 1.0


# ============================================================================
# Regression Tests
# ============================================================================

class TestPerformanceRegression:
    """性能回归测试 - 确保优化不会导致性能下降"""

    def test_lexer_speed_baseline(self):
        """词法分析器速度基线"""
        source = "let x = 42;" * 1000
        scanner = Scanner(source)
        
        # 预热
        scanner.scan_all()
        
        # 正式测试
        start = time.perf_counter()
        tokens = scanner.scan_all()
        elapsed = time.perf_counter() - start
        
        # 基线：100ms
        baseline = 0.1
        assert elapsed < baseline, f"Performance regression: {elapsed:.3f}s > {baseline}s"

    def test_parser_speed_baseline(self):
        """解析器速度基线"""
        source = "let x = 1; let y = 2;" * 300
        tokens = Scanner(source).scan_all()
        
        # 预热
        Parser(tokens).parse()
        
        # 正式测试
        start = time.perf_counter()
        ast = Parser(tokens).parse()
        elapsed = time.perf_counter() - start
        
        # 基线：200ms
        baseline = 0.2
        assert elapsed < baseline, f"Performance regression: {elapsed:.3f}s > {baseline}s"


if __name__ == "__main__":
    # 可以直接运行此文件进行快速性能测试
    pytest.main([__file__, "-v", "-s"])
