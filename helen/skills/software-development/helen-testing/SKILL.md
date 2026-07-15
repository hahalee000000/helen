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
    .toStartWith(prefix)      // 开头是
    .toEndWith(suffix)        // 结尾是
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
    
    // v1.18: spawn + Channel
    let m1 = spawn SlowWorker("A", 1)
    let m2 = spawn SlowWorker("B", 1)
    let m3 = spawn SlowWorker("C", 1)
    
    let r1 = m1.receive()
    let r2 = m2.receive()
    let r3 = m3.receive()
    let results = [r1, r2, r3]
    
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

`helen quality` 的测试覆盖维度（权重 15%）基于文件位置启发式评分：

| 策略 | 得分 | 条件 |
|------|:----:|------|
| `// @test-location:` 注解 | **8.0** | 源文件中注解指向已有测试文件 |
| 同级测试文件 | **8.0** | `<name>_test.helen` 或 `test_<name>.helen` |
| 父级 `tests/` 匹配 | **7.0** | 父级 `tests/` 中有文件名匹配的 `*.py` |
| 同级 `tests/` 目录 | **6.0** | 源文件旁 `tests/` 目录含任意测试 |
| 无测试 | **2.0** | 未找到测试 |

**Agent 程序提示**：集成测试的文件名通常不与源文件 stem 匹配，容易落入 6.0。使用 `// @test-location:` 注解显式声明测试位置可得 8.0：

```helen
// @test-location: tests/integration/test_my_agent.py

agent MyAgent {
    description "示例 agent"
    main { llm act "执行任务" }
}
```

## 调试测试

> **核心心智模型**：`pytest` 告诉你"坏没坏"，Helen 自带工具（`debug`/`trace_on`/`:last_error`/`:llm_log`）告诉你"坏在哪里、为什么"。开发 Helen 应用时两者结合使用。

### 开发 Helen 应用时，何时用什么工具

| 场景 | 用什么 | 为什么 |
|------|--------|--------|
| 改完代码，验证没破坏旧功能 | `pytest` | 自动化回归 |
| 验证 stdlib 函数行为 | `pytest`（Python 单元测试） | Python 层可直接 assert |
| 验证新 agent 行为 | `helen <agent.helen>` + `:llm_log` | 需要真实 LLM 调用链路 |
| 程序运行报错 | REPL + `:last_error` | 结构化错误快照（call_stack/scope） |
| 追踪解释器执行流程 | `trace_on()` + `get_trace()` | 看 Python 单元测试看不到的 |
| 变量值不符合预期 | `debug()` 在关键点打桩 | 结构化输出变量状态 |
| LLM 行为异常 | `:llm_log -v` | 看真实 prompt/response |
| 性能问题 | `context_stats()` / `stopwatch_*()` | 上下文占用 + 计时 |

### 使用 debug() 函数

在关键位置打桩，输出结构化调试信息到 stderr：

```helen
fn test_complex_logic() {
    let input = [1, 2, 3, 4, 5]
    
    // 入口打桩：记录输入状态
    debug("test_complex_logic 输入", {"input": input, "len": len(input)})
    
    let result = process(input)
    
    // 出口打桩：记录输出状态
    debug("test_complex_logic 输出", {"result": result})
    
    assert_equal(result, [2, 4, 6, 8, 10])
}
```

**在 Agent 中布局 debug 的最佳实践**：

```helen
agent MyAgent(task: str) {
    main {
        // 1. 入口打桩：记录参数
        debug("MyAgent 启动", {"task": task})
        
        // 2. 前置断言
        assert len(task) > 0, "task 不能为空"
        
        // 3. LLM 调用
        let result = llm act task
        debug("LLM 返回", {"len": len(result)})
        
        // 4. 结果验证
        assert len(result) > 0, "LLM 返回空"
        
        // 5. 出口打桩
        debug("MyAgent 完成", {})
        return result
    }
}
```

### 使用 trace

用 `trace_on()` / `trace_off()` 包裹可疑代码块，追踪执行轨迹：

```helen
fn test_with_trace() {
    trace_on()
    
    let result = complex_function()
    
    let trace_log = get_trace(50)
    print("Execution trace: " + str(trace_log))
    
    trace_off()
    
    assert_true(result > 0)
}
```

### 使用 :last_error 结构化错误

程序报错时，进 REPL 用 `:last_error` 看结构化错误快照：

```bash
$ helen myagent.helen
Error: ...

$ helen repl
> :last_error
{
  "error": {"type": "RuntimeError", "message": "...", "location": "..."},
  "call_stack": [{"function": "main", "args": {...}}],
  "scope": {"task": "...", "result": "..."},
  "trace": [...]
}
```

分析 `call_stack` 定位哪个函数出问题，分析 `scope` 看变量值是否符合预期。

### 使用 :llm_log 检查 LLM 调用

当 Agent 行为奇怪（答案不对、工具调用异常）时：

```bash
$ helen repl
> :llm_log -v
```

看 LLM 实际收到的 prompt、返回的 response、token 用量、调用时长。常见定位：

- **prompt 不对** → 检查 prompt 模板中的变量替换
- **response 被截断** → 看 `max_tokens` / `timeout` 配置
- **tool_calls 异常** → 检查 `tools` 注册和 schema
- **调用失败** → 看 `error` 字段和 `duration_ms`

### 常见调试场景速查

| 症状 | 第一步 |
|------|--------|
| Agent 给错答案 | `:llm_log -v` 看 LLM 真实调用 |
| 工具调用死循环 | `debug()` 在每次 tool 前后打桩 |
| 上下文被意外压缩 | `context_stats()` 查看占用率 |
| spawn 后子 agent 异常 | 子 agent 入口加 `debug("spawned", {...})` |
| 闭包捕获值不对 | 闭包体内 `debug("captured", {"x": x})` |
| 多 Agent 数据错乱 | 收发两端都加 `debug()` 对比 |
| LLM 流式中断 | `on_chunk fn(c) { debug("chunk", c) }` |
| 性能慢 | `stopwatch_start()` + `debug("elapsed", {...})` |

> **完整 cookbook 参见 `debugging` skill §5**：含决策树 + 10 个场景的详细代码示例。

## 相关技能

- **test-driven-development** — TDD 方法论详解
- **helen-agent-patterns** — Agent 设计模式
- **debugging** — 调试方法论



## 测试陷阱与注意事项

### `is` 类型检查不能在函数参数内使用

```helen
// ❌ 错误：`is` 操作符不能在函数调用参数中使用
fn test_type_check() {
    assert_true(x is list)      // 解析错误！
    assert_true(x is str)       // 解析错误！
}

// ✅ 正确：使用 isinstance() 或 type() 函数
fn test_type_check() {
    assert_true(isinstance(x, "list"))   // isinstance 检查类型
    
    // 或者使用 type() 函数
    let t = type(x)
    assert_equal(t, "list")
}
```

### Agent 测试需要 LLM 调用

测试包含 `llm act` 的 Agent 时，测试会实际调用 LLM API。建议：
- 将纯逻辑函数（不依赖 LLM）和 Agent 分开测试
- 纯逻辑测试可以快速运行，Agent 测试标记为集成测试
- 使用 `--filter` 或 `--skip` 选择性运行

```helen
// 纯逻辑函数 — 快速单元测试
fn test_get_config() {
    let config = get_default_config()
    assert_equal(len(config), 4)
}

// Agent 测试 — 需要 LLM，较慢
fn test_agent_returns_valid_structure() {
    let result = MyAgent("test input")
    assert_true(has_key(result, "output"))
}
```

