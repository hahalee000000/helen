# 教程 12: 测试框架与 TDD

> 用 Helen 内置测试框架写测试、跑 TDD

---

## 为什么需要测试框架？

Helen 是 AI 原生语言——Agent 写的代码更需要自动化测试保障。内置测试框架让你：

- 用 Helen 语法写测试（不需要外部工具）
- 链式断言（`expect().toBe()`）
- 监听模式（`--watch`）实现 TDD 红-绿-重构循环
- JSON 输出便于 CI 集成

## 快速开始

### 1. 创建测试文件

```helen
// calculator_test.helen

fn add(a, b) { return a + b }
fn subtract(a, b) { return a - b }

fn test_add() {
    assert_equal(add(2, 3), 5)
    assert_equal(add(-1, 1), 0)
}

fn test_subtract() {
    assert_equal(subtract(10, 4), 6)
    assert_equal(subtract(0, 0), 0)
}

test_suite("Calculator")
test_case("adds numbers", test_add)
test_case("subtracts numbers", test_subtract)
test_end_suite()

run_tests()
```

### 2. 运行测试

```bash
$ helen test calculator_test.helen
============================================================
  HELEN TEST RESULTS
============================================================

  Calculator
    ✓ adds numbers (0.1ms)
    ✓ subtracts numbers (0.0ms)

------------------------------------------------------------
  2 passed, 0 failed, 0 skipped (2 total)
  Duration: 0.5ms
============================================================
  ✓ ALL TESTS PASSED
============================================================
```

## 断言函数

| 函数 | 说明 |
|------|------|
| `assert_true(condition)` | 断言条件为真 |
| `assert_equal(actual, expected)` | 断言相等 |
| `assert_not_equal(a, b)` | 断言不等 |
| `assert_throws(fn)` | 断言抛出异常 |

```helen
fn test_assertions() {
    assert_true(10 > 5)
    assert_equal("hello" + " world", "hello world")
    assert_not_equal(1, 2)
    
    try {
        assert_throws(fn() { throw RuntimeError("boom") })
    } catch AssertionError e {
        // 断言失败本身也是 AssertionError
    }
}
```

## Expect 链式 API

更可读的断言风格：

```helen
fn test_expect_chain() {
    // 基本断言
    expect(42).toBe(42)
    expect([1, 2, 3]).toContain(2)
    expect("hello world").toStartWith("hello")
    expect("hello world").toEndWith("world")
    expect([1, 2, 3]).toHaveLength(3)
    
    // 数值比较
    expect(10).toBeGreaterThan(5)
    expect(3).toBeLessThan(7)
    
    // 类型检查
    expect("hello").toBeType("str")
    expect(42).toBeType("int")
    
    // 否定
    expect(42).not_.toBe(0)
    expect([]).not_.toContain(1)
    
    // 深度相等
    expect({"a": 1, "b": 2}).toEqual({"b": 2, "a": 1})
    
    // 正则匹配
    expect("hello123").toMatch("hello\\d+")
    
    // 空值检查
    expect("").toBeEmpty()
    expect([]).toBeEmpty()
    expect("hello").toBeTruthy()
    expect(null).toBeFalsy()
}
```

## 测试套件与过滤

### 多个测试套件

```helen
test_suite("String Utils")
test_case("uppercase", test_upper)
test_case("lowercase", test_lower)
test_end_suite()

test_suite("Math Utils")
test_case("add", test_add)
test_case("multiply", test_multiply)
test_end_suite()

run_tests()
```

### CLI 过滤

```bash
# 只运行某个测试
helen test file.helen --only "adds numbers"

# 只运行某个 suite
helen test file.helen --suite "Calculator"

# 正则过滤
helen test file.helen --filter "add|subtract"
```

## 钩子函数

`before_each` 和 `after_each` 在每个测试前后运行：

```helen
fn setup() {
    // 重置全局状态、初始化数据
    print("Setting up...")
}

fn teardown() {
    // 清理资源
    print("Tearing down...")
}

test_suite("With Hooks")
before_each(setup)
after_each(teardown)
test_case("test1", test_something)
test_case("test2", test_another)
test_end_suite()
```

## 跳过测试

还没写好的测试可以暂时跳过：

```helen
test_suite("Feature")
test_case("completed feature", test_done)
test_case_skip("work in progress", test_wip)    // 跳过
test_end_suite()
```

## TDD 工作流

### 1. RED — 写失败的测试

```helen
// 我们想实现一个 FizzBuzz
fn test_fizzbuzz() {
    expect(fizzbuzz(3)).toBe("Fizz")
    expect(fizzbuzz(5)).toBe("Buzz")
    expect(fizzbuzz(15)).toBe("FizzBuzz")
    expect(fizzbuzz(7)).toBe("7")
}

test_suite("FizzBuzz")
test_case("returns correct string", test_fizzbuzz)
test_end_suite()

run_tests()
```

### 2. GREEN — 实现功能

```helen
fn fizzbuzz(n) {
    if n % 15 == 0 { return "FizzBuzz" }
    if n % 3 == 0 { return "Fizz" }
    if n % 5 == 0 { return "Buzz" }
    return str(n)
}
```

### 3. 监听模式 — 自动重跑

```bash
$ helen test fizzbuzz_test.helen --watch
Watching for changes... (Ctrl+C to stop)
```

保存文件后测试自动重跑，即时反馈。

## JSON 输出与 CI 集成

```bash
$ helen test file.helen --json
{
  "suites": [
    {
      "name": "Calculator",
      "tests": [
        {"name": "adds numbers", "passed": true, "duration_ms": 0.1},
        {"name": "subtracts numbers", "passed": true, "duration_ms": 0.0}
      ]
    }
  ],
  "summary": {"total": 2, "passed": 2, "failed": 0, "skipped": 0}
}
```

在 CI 中使用退出码判断成功/失败：

```yaml
# GitHub Actions 示例
- run: helen test tests/ --json
  # 非零退出码 = 测试失败
```

## 练习

1. 为一个字符串反转函数写测试套件，至少 3 个测试用例
2. 用 `expect` 链式 API 重写一个已有测试
3. 创建一个包含 `before_each` 的测试套件，验证钩子函数正确执行
4. 用 `--watch` 模式实现一个简单的 TDD 循环

---

> **相关文档**: [[toolchain/testing|测试框架 API 参考]] | [[tutorial/01-getting-started|入门指南]]
