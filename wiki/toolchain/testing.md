# 测试框架

Helen 内置了完整的测试框架，支持 TDD（测试驱动开发）工作流。

## 概述

Helen 测试框架提供：

- **简单 API** — `test_suite` / `test_case` / `test_end_suite`
- **丰富断言** — `assert_*` + `expect().toBe()` 链式
- **灵活过滤** — `--only` / `--suite` / `--filter`
- **TDD 支持** — `--watch` 监听模式
- **CI 集成** — `--json` 输出
- **跳过测试** — `test_case_skip`
- **钩子函数** — `before_each` / `after_each`

## 快速开始

### 创建测试文件

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

### 运行测试

```bash
helen test calculator_test.helen
```

## 断言函数

| 函数 | 说明 |
|------|------|
| `assert_true(condition)` | 断言条件为真 |
| `assert_equal(actual, expected)` | 断言相等 |
| `assert_not_equal(a, b)` | 断言不等 |
| `assert_throws(fn)` | 断言抛出异常 |

## Expect 链式 API

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

## CLI 选项

### 过滤

```bash
helen test file.helen --only "test name"      # 单个测试
helen test file.helen --suite "Suite Name"    # 单个 suite
helen test file.helen --filter "pattern"      # 正则过滤
```

### 输出

```bash
helen test file.helen --json                  # JSON 输出
helen test file.helen --coverage              # 覆盖率提示
```

### 监听

```bash
helen test file.helen --watch                 # 文件变更自动重跑
helen test file.helen --watch --filter "add"  # 监听 + 过滤
```

## TDD 工作流

### 1. RED — 写失败的测试

```helen
fn test_new_feature() {
    assert_equal(feature.do_something(), expected)
}

test_suite("Feature")
test_case("works", test_new_feature)
test_end_suite()

run_tests()
```

### 2. GREEN — 实现功能

```bash
helen test test.helen --watch
```

编辑代码，保存后测试自动重跑。

### 3. REFACTOR — 重构

改进代码，保持测试通过。

## 钩子函数

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

## 跳过测试

```helen
test_case_skip("not ready", test_wip)
```

## 输出示例

```
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

## 相关文档

- [教程](../tutorial/01-getting-started.md)
- [CLI 工具](../toolchain/cli.md)
- [标准库](../toolchain/stdlib.md)
