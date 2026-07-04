---
name: helen-testing
description: "Helen 测试框架使用指南 — TDD 工作流、断言 API、CLI 选项、Agent 测试、v1.10 异常处理"
version: 1.1.0
author: Helen Team
license: MIT
tags: [helen, testing, tdd, assertions, cli, agent-testing, exception-handling, v1.10]
---

# Helen 测试框架

## 概述

Helen 内置完整的测试框架，支持 TDD 开发模式。v1.10 增强了异常处理和 Agent 测试支持。

## 快速开始

### 1. 创建测试文件

**方式 1：回调风格（推荐）**

```helen
// calculator_test.helen

test_suite("Calculator", fn() {
    test_case("adds numbers", fn() {
        assert_equal(2 + 3, 5)
    })
    test_case("subtracts numbers", fn() {
        assert_equal(10 - 4, 6)
    })
})

run_tests()
```

**方式 2：自动发现（最简单）**

```helen
// calculator_test.helen

fn test_add() {
    assert_equal(2 + 3, 5)
}

fn test_subtract() {
    assert_equal(10 - 4, 6)
}

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
| `assert_contains(haystack, needle)` | 断言容器包含元素 |
| `assert_throws(fn)` | 断言抛出异常 |

**assert_contains 示例：**

```helen
fn test_contains() {
    // 字符串
    assert_contains("hello world", "world")
    
    // 数组
    assert_contains([1, 2, 3], 2)
    
    // 对象
    assert_contains({"name": "Helen", "version": "1.0"}, "name")
}
```

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
    .toHaveProperty(key)      // 属性存在
    .toThrow()                // 抛出异常
```

**示例：**

```helen
fn test_expect_api() {
    expect(42).toBe(42)
    expect([1, 2, 3]).toContain(2)
    expect("hello").toStartWith("he")
    expect({"a": 1}).toHaveProperty("a")
}
```

### 异常测试（v1.10 增强）

```helen
fn test_exceptions() {
    // 基础异常测试
    assert_throws(fn() {
        throw RuntimeError("error")
    })
    
    // 特定异常类型（v1.10）
    expect(fn() {
        throw LLMError("API failed")
    }).toThrow()
    
    // 检查异常消息
    try {
        throw RuntimeError("specific error")
    } catch RuntimeError as e {
        assert_contains(e.message, "specific")
    }
}
```

### v1.10 异常层级

Helen v1.10 增强了异常处理，所有 Python stdlib 异常都被包装为 `RuntimeError`：

```
AnyError
├── LLMError
│   ├── TimeoutError
│   └── ModelError
├── ToolError
├── RuntimeError          // 包含所有 stdlib Python 异常
│   ├── ValueError
│   ├── TypeError
│   ├── KeyError
│   └── ...
├── AssertionError
└── AggregateError        // 并发任务错误聚合
```

**测试异常示例：**

```helen
fn test_runtime_errors() {
    // stdlib 异常被包装为 RuntimeError
    expect(fn() {
        let x = int("not a number")  // 会抛出 RuntimeError
    }).toThrow()
    
    // 捕获并检查
    try {
        let arr = [1, 2, 3]
        let x = arr[10]  // 索引越界
    } catch RuntimeError as e {
        assert_contains(e.message, "index")
    }
}
```

## 测试 Agent

### 测试简单 Agent

```helen
agent Adder(a: int, b: int) {
    description "Add two numbers"
    
    main {
        return a + b
    }
}

fn test_adder_agent() {
    let result = Adder(2, 3)
    assert_equal(result, 5)
}
```

### 测试带工具的 Agent

```helen
agent FileProcessor(path: str) {
    description "Process a file"
    tools = ["read_file"]
    
    main {
        let content = read_file(path)
        return len(content)
    }
}

fn test_file_processor() {
    // 准备测试文件
    write_file("test_input.txt", "hello world")
    
    // 测试
    let result = FileProcessor("test_input.txt")
    assert_equal(result, 11)
    
    // 清理
    delete_file("test_input.txt")
}
```

### 测试 Agent 作用域隔离（v1.10）

```helen
shared let shared_counter = 0
const MAX_VALUE = 100

agent CounterAgent {
    description "Test scope isolation"
    
    main {
        // ✅ const 可见
        assert_true(MAX_VALUE > 0)
        
        // ✅ shared let 可见
        shared_counter = shared_counter + 1
        return shared_counter
    }
}

fn test_agent_scope_isolation() {
    shared_counter = 0  // 重置
    
    let r1 = CounterAgent()
    assert_equal(r1, 1)
    
    let r2 = CounterAgent()
    assert_equal(r2, 2)
    
    assert_equal(shared_counter, 2)
}
```

### 测试并发 Agent

```helen
agent SlowWorker(id: str, delay: int) {
    description "Worker with delay"
    
    main {
        sleep(delay)
        return "done: " + id
    }
}

fn test_concurrent_agents() {
    let start = timestamp()
    
    let t1 = async SlowWorker("A", 1)
    let t2 = async SlowWorker("B", 1)
    let t3 = async SlowWorker("C", 1)
    
    let results = await [t1, t2, t3]
    
    let elapsed = timestamp() - start
    
    // 应该并发执行，总时间约 1 秒
    assert_true(elapsed < 2)
    assert_equal(len(results), 3)
}
```

### 测试 Agent 错误处理

```helen
agent FailingAgent(task: str) {
    description "Agent that may fail"
    
    main {
        if task == "fail" {
            throw RuntimeError("Intentional failure")
        }
        return "success: " + task
    }
}

fn test_agent_error_handling() {
    // 正常情况
    let result = FailingAgent("ok")
    assert_equal(result, "success: ok")
    
    // 异常情况
    expect(fn() {
        FailingAgent("fail")
    }).toThrow()
}
```

## 测试套件组织

### 使用 before_each / after_each

```helen
before_each(fn() {
    // 每个测试前执行
    write_file("test_data.txt", "initial")
})

after_each(fn() {
    // 每个测试后执行
    delete_file("test_data.txt")
})

fn test_read_data() {
    let content = read_file("test_data.txt")
    assert_equal(content, "initial")
}

fn test_modify_data() {
    write_file("test_data.txt", "modified")
    let content = read_file("test_data.txt")
    assert_equal(content, "modified")
}
```

### 嵌套测试套件

```helen
test_suite("Math", fn() {
    test_suite("Addition", fn() {
        test_case("positive numbers", fn() {
            assert_equal(2 + 3, 5)
        })
        test_case("negative numbers", fn() {
            assert_equal(-1 + -2, -3)
        })
    })
    
    test_suite("Multiplication", fn() {
        test_case("positive numbers", fn() {
            assert_equal(2 * 3, 6)
        })
        test_case("with zero", fn() {
            assert_equal(5 * 0, 0)
        })
    })
})

run_tests()
```

## CLI 选项

### 基本用法

```bash
# 运行所有测试
helen test my_test.helen

# 运行特定测试套件
helen test my_test.helen --suite "Math"

# 运行特定测试用例
helen test my_test.helen --only "adds numbers"

# JSON 输出
helen test my_test.helen --json

# 详细输出
helen test my_test.helen --verbose

# Watch 模式（文件变化自动重跑）
helen test my_test.helen --watch
```

### 过滤测试

```bash
# 只运行匹配的测试
helen test my_test.helen --only "test_add"

# 排除匹配的测试
helen test my_test.helen --skip "slow_tests"

# 组合过滤
helen test my_test.helen --suite "Math" --only "addition"
```

## 测试最佳实践

### 1. 测试命名规范

```helen
// ✅ 清晰的测试命名
fn test_add_positive_numbers() { ... }
fn test_add_negative_numbers() { ... }
fn test_add_zero() { ... }

// ❌ 模糊的命名
fn test_add() { ... }
fn test1() { ... }
```

### 2. 独立测试

```helen
// ✅ 每个测试独立
fn test_feature_a() {
    let data = setup_data()
    assert_equal(process(data), expected_a)
}

fn test_feature_b() {
    let data = setup_data()  // 重新设置
    assert_equal(process(data), expected_b)
}

// ❌ 测试间依赖
fn test_feature_a() {
    global_data = setup_data()
    assert_equal(process(global_data), expected_a)
}

fn test_feature_b() {
    // 依赖 test_feature_a 的结果
    assert_equal(process(global_data), expected_b)
}
```

### 3. 测试边界条件

```helen
fn test_edge_cases() {
    // 空输入
    assert_equal(process([]), [])
    
    // 单元素
    assert_equal(process([1]), [1])
    
    // 最大值
    assert_equal(process([MAX_INT]), [MAX_INT])
    
    // 边界值
    assert_equal(process([0]), [0])
    assert_equal(process([-1]), [-1])
}
```

### 4. 使用 mock 数据

```helen
fn test_with_mock_data() {
    // 准备 mock 数据
    let mock_user = {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com"
    }
    
    // 测试
    let result = format_user(mock_user)
    assert_equal(result, "Test User (test@example.com)")
}
```

## 持续集成

### GitHub Actions 示例

```yaml
name: Helen Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Helen
        run: pip install -e .
      - name: Run tests
        run: helen test tests/*.helen --json > results.json
      - name: Check results
        run: |
          if [ $(jq '.failed' results.json) -gt 0 ]; then
            exit 1
          fi
```

### 测试覆盖率

```bash
# 生成覆盖率报告（需要额外工具）
helen test tests/*.helen --coverage --output coverage.html
```

## 调试测试

### 使用 debug() 函数

```helen
fn test_complex_logic() {
    let input = [1, 2, 3, 4, 5]
    
    debug("Input: " + str(input))
    
    let result = process(input)
    
    debug("Result: " + str(result))
    
    assert_equal(result, [2, 4, 6, 8, 10])
}
```

### 使用 trace

```helen
fn test_with_trace() {
    trace_on()
    
    let result = complex_function()
    
    let trace_log = get_trace()
    print("Execution trace: " + str(trace_log))
    
    trace_off()
    
    assert_true(result > 0)
}
```

## 相关技能

- **test-driven-development** — TDD 方法论详解
- **helen-agent-patterns** — Agent 设计模式
- **debugging** — 调试方法论
