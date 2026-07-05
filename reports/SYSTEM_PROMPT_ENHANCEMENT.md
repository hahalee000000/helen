# Helen 语言系统提示词增强

## 背景

参考 Claude Code 的系统提示词设计，Helen 语言的系统提示词从简单的"Agent 描述 + 技能索引"增强为包含语言规范、最佳实践和指导原则的综合系统提示词。

## 增强内容

### 修改前

系统提示词只包含两部分：
1. Agent 描述（或 prompt 模板）
2. 技能索引（`<available_skills>`）

### 修改后

系统提示词现在包含三个部分：
1. **Helen 语言规范**（`<helen_conventions>`）— 新增
2. Agent 描述（或 prompt 模板）
3. 技能索引（`<available_skills>`）

---

## 新增的 Helen 语言规范

### 1. 核心原则（Core Principles）

```
- Helen is agent-centric: design around `agent` blocks with `prompt`, `tools`, and `main`
- Use `llm act` for LLM interactions (with optional tool calling via `tools` declaration)
- Use `llm if` for LLM-routed branching (classification tasks)
- Prefer composition over inheritance: build small, focused agents that collaborate
```

**目的**：让 LLM 理解 Helen 的设计哲学，避免生成不符合语言特性的代码。

### 2. 技能驱动开发（Skill-Driven Development）

```
**CRITICAL**: Before writing ANY code (tests, main program, or utilities):
1. Scan the available skills below
2. If a skill matches your task, call `load_skill(name='skill-name')` FIRST
3. Follow the loaded skill's instructions precisely

Common skills to load:
- `helen-syntax` — Language syntax, keywords, patterns
- `helen-testing` — Test framework (`fn test_name()`, `assert_true`, `assert_equal`)
- `helen-stdlib` — Built-in functions (string, math, collections, time, etc.)
- `helen-agent-collaboration` — Multi-agent patterns (shared let, channel, shared store)
```

**目的**：强制 LLM 在生成代码前加载相关技能，避免猜测 API 和语法。

### 3. 代码生成最佳实践（Code Generation Best Practices）

```
- **Test-first**: Write tests before implementation when possible
- **Incremental**: Build and verify in small steps, not all at once
- **Error handling**: Use `try-catch` with specific exception types
- **Tool usage**:
  - Use `read_file` to inspect existing code before modifying
  - Use `shell_exec` for running tests (`helen test <file>`) and checks (`helen check <file>`)
  - Use `write_file` to create/update files (not shell commands like `echo >`)
```

**目的**：指导 LLM 遵循工程最佳实践，避免常见的反模式。

### 4. 常见陷阱警告（Common Pitfalls to Avoid）

```
- ❌ Guessing stdlib function names → ✅ Load `helen-stdlib` skill or read source
- ❌ Inventing test syntax → ✅ Load `helen-testing` skill
- ❌ Using Python/C APIs (e.g., `strftime`) → ✅ Use Helen stdlib (e.g., `date_format`)
- ❌ Skipping skill loading → ✅ Always check skills first
```

**目的**：明确列出 session.txt 中发现的典型错误，防止重蹈覆辙。

### 5. 快速参考（Quick Reference）

#### 测试语法

```helen
// Correct test structure
fn test_feature_name() {
    let result = function_under_test()
    assert_true(result > 0)
    assert_equal(result, expected_value)
}

// Run tests
run_tests()  // Executes all fn test_*() functions
```

#### Agent 结构

```helen
agent MyAgent(input: str) {
    description "What this agent does"
    prompt "Task: {{input}}"
    tools ["read_file", "write_file"]  // Optional tool whitelist

    functions {
        fn helper_fn(): str {
            return "processed"
        }
    }

    main {
        let result = llm act  // Uses prompt + tools
        return result
    }
}
```

**目的**：提供最小可运行的代码模板，LLM 可以直接参考。

---

## 技术实现

### 文件修改

1. **`helen/runtime/prompt_builder.py`**
   - 新增 `_build_helen_conventions()` 方法
   - 修改 `build_system_prompt()` 方法，在开头注入 Helen 规范

2. **`helen/interpreter/llm_mixin.py`**
   - 新增 `_build_helen_conventions()` 方法（委托给 PromptBuilder）
   - 修改 `visit_llm_act_expr()` 方法，在系统提示词中注入 Helen 规范

### 系统提示词构建流程

```
1. 构建 Helen 语言规范（_build_helen_conventions）
   ↓
2. 添加 Agent 描述或渲染后的 prompt 模板
   ↓
3. 添加技能索引（build_skill_index）
   ↓
4. 组合为完整的系统提示词
```

### Token 预算

新增的 Helen 规范约占 **800-1000 tokens**，相比典型的 LLM 上下文窗口（32k-128k）来说非常小，但能提供显著的指导价值。

---

## 预期效果

### 修复前的问题（来自 session.txt）

```
1. Agent 生成时间代码 → 猜测 API 用了 strftime() → 报错
2. Agent 生成测试代码 → 猜测语法用了 test "name" { ... } → 解析错误
3. load_skill 只在错误后被动调用
```

### 修复后的预期行为

```
1. Agent 收到编码任务
2. 扫描技能索引 → 发现 helen-stdlib 相关
3. 调用 load_skill('helen-stdlib') → 学习正确的 API
4. 生成正确的代码（使用 date_format 而非 strftime）
5. 生成测试前 → 加载 helen-testing 技能
6. 使用正确的测试语法（fn test_* + assert_true）
```

---

## 测试验证

- ✅ 所有 2384 个测试通过
- ✅ 技能索引测试通过
- ✅ Prompt builder 测试通过
- ✅ Interpreter 测试通过
- ✅ 运行时测试通过

---

## 与 Claude Code 的对比

| 特性 | Claude Code | Helen（增强后） |
|------|------------|----------------|
| 角色定义 | ✅ "You are Claude Code..." | ✅ "You are generating code for Helen..." |
| 工具使用指导 | ✅ 详细的工具选择指南 | ✅ 工具使用最佳实践 |
| 代码风格 | ✅ 命名约定、格式化 | ✅ Agent 结构、测试语法 |
| 错误处理 | ✅ 重试策略、降级方案 | ✅ try-catch、异常类型 |
| 工作流模式 | ✅ TDD、增量开发 | ✅ Test-first、技能驱动 |
| 安全考虑 | ✅ 权限检查、沙箱 | ✅ 工具白名单、隔离级别 |
| 上下文管理 | ✅ 长对话处理 | ✅ 技能索引缓存 |

---

## 未来增强方向

1. **动态技能推荐**：根据任务类型自动推荐最相关的技能
2. **项目上下文注入**：自动检测项目结构并注入相关信息
3. **历史错误学习**：从过去的错误中提取模式并加入规范
4. **多语言支持**：支持中文系统提示词（与 Helen 的双语关键字对齐）

---

## 总结

通过参考 Claude Code 的系统提示词设计，Helen 语言现在拥有了更全面、更指导性的系统提示词。这不仅提高了 LLM 生成正确代码的概率，还建立了一套"技能驱动开发"的工作范式，从根本上解决了之前 session.txt 中暴露的问题。

**核心改进**：
- ✅ 从"被动纠错"到"主动预防"
- ✅ 从"猜测 API"到"技能驱动"
- ✅ 从"孤立开发"到"规范指导"
