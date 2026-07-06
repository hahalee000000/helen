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

## 完整工作流示例

```helen
// Phase 1: 契约设计
let requirement = "实现一个安全的用户认证模块"
let context = "项目: auth_service, 需要 JWT 支持"
let contract = call_contractor(requirement, context)
print("✅ Phase 1 完成: 契约设计")
print(contract)

// 用户确认契约后继续

// Phase 2 RED: 生成测试
let source = ""  // 空实现
let tests = call_test_builder(source, contract)
write_file("tests/test_auth.helen", tests)
let red_check = run_helen_tests("tests/")
print("✅ Phase 2 RED 完成: 测试全部 FAIL")

// Phase 2 GREEN: 编写实现
let impl = call_implementer(source, tests, contract)
write_file("src/auth.helen", impl)
let green_check = run_helen_tests("tests/")
if green_check["success"] {
    print("✅ Phase 2 GREEN 完成: 测试全部 PASS")
}

// Phase 3: 质量评估
let before = get_quality_scores("src/auth.helen")
let quality = call_quality_gate("src/auth.helen", before)
print("✅ Phase 3 完成: 质量评估")
print(quality)

if quality["verdict"] == "NEEDS_IMPROVEMENT" {
    // 回到 Phase 2 改进
    print("⚠️ 质量不达标，需要改进")
}

// Phase 4: 技能评估
let summary = "实现了 JWT 认证模块，发现需要处理 token 过期的边界情况"
let files = "src/auth.helen, tests/test_auth.helen"
let skills = call_skill_evaluator(summary, files)
print("✅ Phase 4 完成: 技能评估")
print(skills)
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

### 安全性改进

```helen
// ❌ 不安全
fn process_user_input(input: str): map {
    let query = "SELECT * FROM users WHERE name = '" + input + "'"
    // SQL 注入风险
}

// ✅ 安全
fn process_user_input(input: str): map {
    if !is_valid_input(input) {
        return create_error(ERROR_INVALID_INPUT, "Invalid input")
    }
    let query = "SELECT * FROM users WHERE name = ?"
    let params = [input]
    // 使用参数化查询
}
```

### 可维护性改进

```helen
// ❌ 难维护（重复逻辑）
fn process_a(input: str): map {
    if len(input) == 0 {
        return {"status": "error", "code": 1001}
    }
    // ... 处理逻辑
}

fn process_b(input: str): map {
    if len(input) == 0 {
        return {"status": "error", "code": 1001}
    }
    // ... 类似的处理逻辑
}

// ✅ 易维护（提取公共函数）
fn validate_input(input: str): map {
    if len(input) == 0 {
        return create_error(1001, "Empty input")
    }
    return create_success(input)
}

fn process_a(input: str): map {
    let validation = validate_input(input)
    if validation["status"] == "error" {
        return validation
    }
    // ... 处理逻辑
}
```

## 技能自进化示例

### 场景 1：发现新陷阱

```helen
// 任务：实现递归斐波那契
// 问题：n > 30 时栈溢出

let task_summary = """
实现了递归斐波那契函数，发现 n > 30 时会导致栈溢出。
解决方案：改用迭代实现，或使用尾递归优化。
"""

// SkillEvaluator 评估
let evaluation = call_skill_evaluator(task_summary, "src/math.helen")

// 结果：建议创建新技能
// {
//   "new_skills": [{
//     "name": "recursion-stack-overflow",
//     "category": "error-patterns",
//     "tags": "[helen, recursion, stack-overflow, performance]",
//     "content": "# 递归栈溢出\n\n## 触发条件\n- 递归深度 > 30\n- 无尾递归优化\n\n## 解决方案\n1. 改用迭代实现\n2. 使用尾递归（如果 Helen 支持）\n3. 增加递归深度检查"
//   }]
// }

save_new_skill("recursion-stack-overflow", "error-patterns", "[helen, recursion, stack-overflow]", "...")
```

### 场景 2：更新现有技能

```helen
// 任务：使用 helen-testing 技能编写测试
// 问题：发现技能文档没提到 mock 对象必须在 test_suite 外部定义

let task_summary = """
使用 helen-testing 技能编写测试，发现 mock 对象必须在 test_suite 外部定义，
不能在 test_case 内部定义，否则会导致作用域错误。
"""

// SkillEvaluator 评估
let evaluation = call_skill_evaluator(task_summary, "tests/test_api.helen")

// 结果：建议更新现有技能
// {
//   "updates": [{
//     "name": "helen-testing",
//     "path": "~/.helen/skills/software-development/helen-testing/SKILL.md",
//     "addition": "\n## 新陷阱\n- mock 对象必须在 test_suite 外部定义，不能在 test_case 内部"
//   }]
// }

update_existing_skill("~/.helen/skills/software-development/helen-testing/SKILL.md", "## 新陷阱\n...")
```

## 参考资源

- [Helen 语法参考](./helen-syntax/SKILL.md)
- [Helen 标准库](./helen-stdlib/SKILL.md)
- [TDD 工作流](./test-driven-development/SKILL.md)
- [代码质量评估](./code-quality/SKILL.md)
