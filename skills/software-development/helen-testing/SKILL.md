---
name: helen-testing
description: "Helen 测试框架使用指南 — TDD 工作流、断言 API、CLI 选项"
version: 1.0.0
author: Helen Team
license: MIT
metadata:
  hermes:
    tags: [helen, testing, tdd, assertions, cli]
---

# Helen 测试框架

## 概述

Helen 内置完整的测试框架，支持 TDD 开发模式。

## 快速开始

### 1. 创建测试文件

```helen
// calculator_test.helen

fn test_add() {
    assert_equal(2 + 3, 5)
}

fn test_subtract() {
    assert_equal(10 - 4, 6)
}

test_suite("Calculator")
test_case("adds numbers", test_add)
test_case("subtracts numbers", test_subtract)
test_end_suite()

run_tests()
```

### 2. 运行测试

```bash
helen test calculator_test.helen
```

## 断言 API

### 基础断言

| 函数 | 说明 |
|------|------|
| `assert_true(condition)` | 断言条件为真 |
| `assert_equal(actual, expected)` | 断言相等 |
| `assert_not_equal(a, b)` | 断言不等 |
| `assert_throws(fn)` | 断言抛出异常 |

### Expect 链式 API

```helen
expect(value)
    .toBe(expected)           // 严格相等
    .toEqual(expected)        // 深度相等
    .toContain(item)          // 包含
    .toBeGreaterThan(n)       // 大于
    .toBeLessThan(n)          // 小于
    .toMatch(pattern)         // 正则匹配
    .toStartWith(prefix)      // 以...开头
    .toEndWith(suffix)        // 以...结尾
    .toHaveLength(n)          // 长度
    .toBeEmpty()              // 为空
    .toBeTruthy()             // 为真
    .toBeFalsy()              // 为假
    .toBeType("str")          // 类型检查
    .toThrow()                // 抛出异常
    .not_.toBe(x)             // 否定
```

### 示例

```helen
fn test_expect() {
    // 相等
    expect(42).toBe(42)
    
    // 包含
    expect("hello world").toContain("world")
    expect([1, 2, 3]).toContain(2)
    
    // 比较
    expect(10).toBeGreaterThan(5)
    
    // 字符串
    expect("test123").toMatch("[0-9]+")
    
    // 否定
    expect(5).not_.toBe(6)
    
    // 链式
    expect("hello world")
        .toContain("hello")
        .toStartWith("hello")
}
```

## 测试组织

### 方式 1：简单注册（推荐）

```helen
test_suite("Math")
test_case("adds", test_add)
test_case("subtracts", test_subtract)
test_end_suite()

test_suite("String")
test_case("uppercases", test_upper)
test_end_suite()
```

### 方式 2：钩子函数

```helen
fn setup() {
    // 每个测试前运行
}

fn teardown() {
    // 每个测试后运行
}

test_suite("With hooks")
before_each(setup)
after_each(teardown)
test_case("test1", test_something)
test_end_suite()
```

### 跳过测试

```helen
test_case_skip("not ready", test_wip)
```

## CLI 选项

### 过滤

```bash
# 运行单个测试
helen test file.helen --only "adds numbers"

# 运行单个 suite
helen test file.helen --suite "Calculator"

# 按模式过滤（正则）
helen test file.helen --filter "add|subtract"
```

### 输出

```bash
# JSON 格式（CI 集成）
helen test file.helen --json

# 覆盖率提示
helen test file.helen --coverage
```

### 监听模式（TDD）

```bash
# 文件变更自动重跑
helen test file.helen --watch

# 监听 + 过滤
helen test file.helen --watch --filter "add"
```

## TDD 工作流

### 1. RED — 写失败的测试

```helen
// my_feature_test.helen
import "my_feature" as feature

fn test_new_feature() {
    assert_equal(feature.do_something(), expected_result)
}

test_suite("New Feature")
test_case("does something", test_new_feature)
test_end_suite()

run_tests()
```

```bash
helen test my_feature_test.helen --watch
```

### 2. GREEN — 实现功能

```helen
// my_feature.helen
fn do_something() {
    return expected_result
}
```

保存文件 → 测试自动重跑 → 看到通过！

### 3. REFACTOR — 重构

改进代码，保持测试通过。

## 输出示例

```
============================================================
  HELEN TEST RESULTS
============================================================

  Calculator
    ✓ adds numbers (0.1ms)
    ✓ subtracts numbers (0.0ms)
    ○ skipped test (skipped)

------------------------------------------------------------
  2 passed, 0 failed, 1 skipped (3 total)
  Duration: 0.5ms
============================================================
  ✓ ALL TESTS PASSED
============================================================
```

## 完整示例

```helen
// string_utils_test.helen

fn test_reverse() {
    assert_equal(reverse("hello"), "olleh")
    assert_equal(reverse(""), "")
}

fn test_uppercase() {
    expect(upper("hello")).toBe("HELLO")
}

fn test_contains() {
    expect("hello world").toContain("world")
    expect("hello world").not_.toContain("xyz")
}

test_suite("String Utils")
test_case("reverse", test_reverse)
test_case("uppercase", test_uppercase)
test_case("contains", test_contains)
test_end_suite()

run_tests()
```

## 相关文档

- [教程](../../docs/tutorial.md#测试框架)
- [Wiki](../../../wiki/helen/toolchain/testing.md)
- [示例](../../examples/test_example.helen)
