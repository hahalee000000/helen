---
name: helen-programming-methodology
description: "Helen 编程方法论 — 契约驱动、TDD、质量评估、技能自进化的完整工作流"
version: 1.0.0
author: Helen Team
license: MIT
metadata:
  hermes:
    tags: [helen, methodology, contract-first, tdd, quality, skill-evolution, workflow]
---

# Helen 编程方法论

本技能描述 Helen 语言的编程方法论，采用四阶段闭环：契约设计 → TDD 开发 → 质量评估 → 技能评估。

## 核心原则

### 1. 契约先行（Contract-First）

在编写任何实现代码之前，先设计接口契约：

```helen
// contracts/my_module.helen

protocol MyModule {
    fn process_data(input: str): map
    fn validate_config(config: map): bool
}

// 错误码定义
const ERROR_INVALID_INPUT = 1001
const ERROR_CONFIG_MISSING = 1002
const ERROR_PROCESSING_FAILED = 1003

// 辅助函数
fn is_valid_input(input: str): bool {
    return len(input) > 0 && len(input) < 1000
}
```

**契约包含**：
- Protocol 定义（接口签名）
- 错误码常量
- 辅助函数（纯函数，无副作用）
- 每个函数的输入/输出类型

### 2. TDD 开发（RED-GREEN-REFACTOR）

严格按三阶段循环：

**RED 阶段**：生成失败的测试

```helen
// tests/test_my_module.helen

import "contracts/my_module.helen"

fn test_process_data_valid_input() {
    let result = process_data("valid input")
    assert_equal(result["status"], "success")
}

fn test_process_data_empty_input() {
    let result = process_data("")
    assert_equal(result["error_code"], ERROR_INVALID_INPUT)
}

fn test_validate_config_missing_field() {
    let config = {"name": "test"}  // 缺少 required_field
    let result = validate_config(config)
    assert_equal(result, false)
}
```

运行测试，确认全部 FAIL。

**GREEN 阶段**：编写最小实现

```helen
// src/my_module.helen

import "contracts/my_module.helen"

fn process_data(input: str): map {
    if !is_valid_input(input) {
        return {
            "status": "error",
            "error_code": ERROR_INVALID_INPUT,
            "message": "Invalid input length"
        }
    }
    
    // 最小实现：只让测试通过
    return {
        "status": "success",
        "data": input
    }
}

fn validate_config(config: map): bool {
    if !contains(config, "required_field") {
        return false
    }
    return true
}
```

运行测试，确认逐步 PASS。

**REFACTOR 阶段**：重构代码

```helen
// 提取重复逻辑
fn process_data(input: str): map {
    if !is_valid_input(input) {
        return create_error(ERROR_INVALID_INPUT, "Invalid input length")
    }
    
    return create_success(input)
}

// 辅助函数
fn create_error(code: int, message: str): map {
    return {
        "status": "error",
        "error_code": code,
        "message": message
    }
}

fn create_success(data: any): map {
    return {
        "status": "success",
        "data": data
    }
}
```

运行测试，确认全部 PASS。

### 3. 质量评估（7 维评分）

每次开发完成后，进行 7 维质量评估：

```helen
// 调用质量评估
let file_path = "src/my_module.helen"
let quality = get_quality_scores(file_path)

// 检查结果
if quality["scores"]["overall"] < 7.5 {
    print("⚠️ 质量分数低于阈值，需要改进")
    print("安全性: " + str(quality["scores"]["security"]))
    print("正确性: " + str(quality["scores"]["correctness"]))
    print("可维护性: " + str(quality["scores"]["maintainability"]))
    // ... 其他维度
}
```

**7 个维度**：
1. **安全性** - 输入验证、错误处理、无硬编码密钥
2. **正确性** - 逻辑正确、边界处理、错误码覆盖
3. **可维护性** - 代码清晰、命名规范、无重复
4. **性能** - 无不必要的循环、合理的算法复杂度
5. **可测试性** - 易于单元测试、无副作用
6. **文档完整性** - 注释充分、接口说明清晰
7. **Helen 规范** - 遵循 Helen 语法和最佳实践

**阈值**：
- 总分 < 7.5 → 需要改进
- 单项 < 6.0 → 必须改进

### 4. 技能评估（Skill Evolution）

每次任务完成后，评估是否产生新技能或需要更新现有技能：

```helen
// 任务摘要
let task_summary = "实现了字符串反转函数，使用 TDD 开发，发现递归实现会导致栈溢出"
let files_changed = "src/string_utils.helen, tests/test_string_utils.helen"

// 调用技能评估
let evaluation = call_skill_evaluator(task_summary, files_changed)

// 处理评估结果
if evaluation["new_skills"] != null {
    for skill in evaluation["new_skills"] {
        print("💡 建议创建新技能: " + skill["name"])
        save_new_skill(skill["name"], skill["category"], skill["tags"], skill["content"])
    }
}

if evaluation["updates"] != null {
    for update in evaluation["updates"] {
        print("🔄 建议更新技能: " + update["name"])
        update_existing_skill(update["path"], update["addition"])
    }
}
```

### 5. 上下文接力（Context Handoff）

Helen 的 transcript 按 **Interpreter 实例隔离**（spawn 创建新 Interpreter → 新 session_id），任何跨 agent / 跨进程的上下文传递都必须**显式编程**——这是 Helen "显式优于隐式"哲学的核心体现。

核心口诀：**"spawn 即隔离，接力靠显式，调试用追踪，恢复用 --session"**

> 💡 完整的上下文接力模式（spawn 传参、SharedStore、--session 恢复、自动追踪）详见 **helen-agent-collaboration** skill。

## 完整工作流示例

四阶段闭环示例（以 JWT 认证模块为例）：

```helen
// Phase 1: 契约设计
let contract = call_contractor("实现用户认证模块", "需要 JWT 支持")

// Phase 2 RED-GREEN: TDD 开发
let tests = call_test_builder("", contract)
write_file("tests/test_auth.helen", tests)
let impl = call_implementer("", tests, contract)
write_file("src/auth.helen", impl)

// Phase 3: 质量评估
let quality = call_quality_gate("src/auth.helen")
if quality["verdict"] == "NEEDS_IMPROVEMENT" {
    // 回到 Phase 2 改进
}

// Phase 4: 技能评估
let skills = call_skill_evaluator("实现了 JWT 认证", "src/auth.helen, tests/test_auth.helen")
```

## Helen 语法注意事项

### 1. 逻辑运算符

```helen
// ✅ 正确
if a && b { }
if a || b { }
if !a { }

// ❌ 错误
if a and b { }
if a or b { }
if not a { }
```

### 2. 字符串截取

```helen
// ✅ 正确
let sub = substring(str, 0, 10)

// ❌ 错误
let sub = str[0:10]
```

### 3. Agent 调用

```helen
// ✅ 正确（函数式调用）
fn call_my_agent(param: str): str {
    return MyAgent(param)
}

// ❌ 错误（使用 call 关键字）
fn call_my_agent(param: str): str {
    return call MyAgent(param)  // 解析错误：Expected expression, got CALL
}

// ❌ 错误（不能在 prompt 中直接调用）
// prompt 中写 "MyAgent()" 会报错
```

**重要**：Helen 中 Agent 是一等公民，应该像函数一样调用。`call` 关键字在表达式位置（赋值、参数、返回值）会导致解析错误，仅用于语句位置（不接收返回值时）。

### 4. 函数返回值

```helen
// ✅ 正确
fn process(): map {
    return {"status": "success", "data": result}
}

// ❌ 错误（Helen 不支持隐式返回）
fn process(): map {
    {"status": "success", "data": result}
}
```

### 5. 测试框架

```helen
// ✅ 正确
test_suite("MyModule", fn() {
    test_case("valid input", fn() {
        assert_equal(result, expected)
    })
})

// ❌ 错误（不能用字符串作为函数名）
test_case("valid input", "test_function")
```

## 质量改进建议

**安全性**：输入验证 + 参数化查询（避免 SQL 注入），禁止硬编码密钥。

**可维护性**：提取重复逻辑为公共函数，避免多处重复的错误处理代码。

```helen
// ❌ 重复逻辑散布多处
fn process_a(input: str): map {
    if len(input) == 0 { return {"status": "error", "code": 1001} }
    // ...
}

// ✅ 提取公共验证函数
fn validate_input(input: str): map {
    if len(input) == 0 { return create_error(1001, "Empty input") }
    return create_success(input)
}
```

## 技能自进化示例

每次任务完成后，评估是否产生新技能或需要更新现有技能：

**场景 1：发现新陷阱** → 创建新技能
```helen
let task_summary = "递归斐波那契 n>30 栈溢出，改用迭代实现"
let evaluation = call_skill_evaluator(task_summary, "src/math.helen")
// 建议创建 "recursion-stack-overflow" 技能
```

**场景 2：更新现有技能** → 补充文档
```helen
let task_summary = "发现 helen-testing 未说明 mock 对象必须在 test_suite 外部定义"
let evaluation = call_skill_evaluator(task_summary, "tests/test_api.helen")
// 建议更新 helen-testing 技能文档
```

---

## 开发工作流中的缓存管理

开发时需注意 ImportResolver 缓存行为：CLI 每次新进程自动重新加载，REPL 和 Web 服务的长进程会缓存已加载模块。开发时优先用 CLI，REPL 中修改文件后用 `:reset` 重置。

> 💡 开发时的缓存管理（REPL/Web 服务陷阱、Python 集成、调试工具）详见 **helen-language-development** skill § ImportResolver 缓存机制。

---

## 参考资源

- [Helen 语法参考](./helen-syntax/SKILL.md)
- [Helen 标准库](./helen-stdlib/SKILL.md)
- [TDD 工作流](./test-driven-development/SKILL.md)
- [代码质量评估](./code-quality/SKILL.md)

## 相关技能

- **helen-agent-patterns** — Agent 设计模式
- **helen-agent-collaboration** — 多 Agent 协作模式
- **helen-testing** — 测试框架使用指南
- **helen-quality** — 代码质量评估
