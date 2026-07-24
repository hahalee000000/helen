# 教程 13: 技能系统

> 让 Agent 带着专业知识工作

---

## 什么是技能？

技能（Skill）是模块化的知识单元，以 Markdown 文件形式存在。它们让 LLM 在需要时加载特定领域的知识，而不是把所有知识塞进 system prompt。

## Agent vs Skill：本质区别

> **Agent 是"谁来做"，Skill 是"怎么做"的知识。**

| 维度 | Agent（智能体） | Skill（技能） |
|------|----------------|--------------|
| **本质** | 运行时实体 | 静态文档 |
| **语言级别** | 一等公民（语法支持） | 外部概念（纯 Markdown） |
| **可调用** | ✅ `Agent()` 像函数调用 | ❌ 不可调用 |
| **有状态** | ✅ 维护对话/工具状态 | ❌ 无状态 |
| **执行逻辑** | ✅ `main { }` 块 | ❌ 无执行逻辑 |
| **用途** | **执行**任务 | **指导**如何执行 |

**Agent 是执行者**：有 model、temperature、tools，可被调用、组合，实际执行 LLM 调用和工具操作。像**员工**。

**Skill 是知识库**：纯 Markdown 文档，提供模式、最佳实践、API 用法，被 Agent 读取作为上下文。像**手册**。

**用 Agent** 当你需要实际执行操作、维护状态、被代码调用。  
**用 Skill** 当你需要提供知识、文档化工作流、让多个 Agent 共享知识。

**实际关系**：Agent 可以加载 Skill 作为知识源：

```helen
agent Developer {
    tools = ["load_skill"]
    main {
        let guide = load_skill("helen-testing")
        return llm act "Follow: " + guide
    }
}
```

## 技能目录结构

```
~/.helen/skills/
├── web-search/
│   ├── SKILL.md           # 主文件（必须）
│   ├── references/        # 参考资料
│   ├── templates/         # 模板文件
│   └── scripts/           # 辅助脚本
└── code-review/
    └── SKILL.md
```

## SKILL.md 格式

```markdown
---
name: web-search
description: Search the web for information
version: 1.0.0
author: Your Name
tags: [web, search, research]
---

# Web Search Skill

## When to Use
- User asks for current information
- Need to verify facts

## How to Use
1. Use web_search tool
2. Analyze results
3. Summarize findings
```

## 三层搜索架构

技能按优先级从高到低搜索：

| 优先级 | 目录 | 说明 |
|--------|------|------|
| 1（最高） | `<project>/.helen/skills/` | 项目级，团队共享 |
| 2 | `~/.helen/skills/` | 用户级，个人全局 |
| 3 | `<helen>/skills/` | 内置级，随语言分发（13 个） |
| 可选 | `~/.hermes/skills/` | Hermes 回退（如已安装） |

同名技能，高优先级覆盖低优先级。

## 两层披露机制

### 第一层：技能索引

所有技能的 name + description + **tags** 被扫描并注入 system prompt：

```
<available_skills>
Before replying, scan skills below. If a skill matches or is
even partially relevant to your task, you MUST load it with
load_skill and follow its instructions. Err on the side of loading.

  research:
    - web-search: Search the web for information (tags: web, search, research)
  dev:
    - code-review: Review code for quality and security (tags: review, security, quality)
</available_skills>
```

**v1.15 强化**：技能索引现在包含 **MUST load** 强制指令，要求 LLM 在技能相关时必须加载，而不是可选的。这确保 agent 在生成代码前主动学习相关技能，避免猜测 API 和语法。

**tags 字段**是提升技能命中率的关键。LLM 根据标签中的关键词匹配用户意图，比仅靠 description 文字匹配更准确。建议使用统一的命名规范（小写、英文关键词）。

### 第二层：按需加载

LLM 看到索引后，判断需要时调用 `load_skill` 工具获取完整内容。

```helen
// 基本加载
load_skill("helen-testing")

// 同时列出参考文档
load_skill("helen-language-development", include_references=true)
```

### 第三层：参考文档

技能可包含 `references/` 目录，存放深度参考文档。LLM 可通过以下方式访问：

```helen
// 列出所有参考文档（名称、路径、大小、前 3 行预览）
list_skill_references("helen-language-development")

// 用 read_file 加载具体参考文档
read_file(".../references/parser-disambiguation.md")
```

参考文档不自动加载，由 LLM 按需查阅，节省 token。

## LLM 语句中的技能感知

`llm act` 自动注入技能索引到 system prompt：

```helen
agent Researcher(query) {
    description: "Research topics using web search"
    
    main {
        // LLM 在这里可以看到所有可用技能
        llm act "Research: " + query
    }
}
```

LLM 在执行时会看到所有可用技能，并能根据需要参考相关技能的知识。

## 技能管理最佳实践

### 命名规范

```
✅ web-search, code-review, data-analysis
❌ WebSearch, code_review, dataAnalysis
```

### 粒度控制

```
✅ 一个技能 = 一个明确的任务领域
❌ 一个技能 = 所有事情（太宽泛）
❌ 一个技能 = 一行指令（太细碎）
```

### 分层组织

```
项目级（.helen/skills/）  → 项目特定规范、API 约定
用户级（~/.helen/skills/） → 个人偏好、常用工作流
内置级（helen/skills/）    → 通用技能、语言相关
```

## 内置技能

Helen 自带 16 个内置技能，分为 Helen 语言专用和通用两类：

### Helen 语言专用技能

| 技能 | 行数 | 说明 |
|------|------|------|
| `helen-syntax` | 632 | 完整语言语法参考（89 关键字、类型、表达式） |
| `helen-stdlib` | 739 | 203 个内置函数分类参考与示例 |
| `helen-testing` | 705 | 测试框架使用、TDD 工作流、Agent 测试 |
| `helen-quality` | 133 | 7 维质量评估指南 |
| `helen-agent-patterns` | 815 | 单 Agent 设计模式（7 大模式 + 最佳实践） |
| `helen-agent-collaboration` | 545 | 多 Agent 协作模式（6 大模式） |
| `helen-language-development` | 674 | 语言实现模式（AST、解析器、解释器扩展） |
| `helen-programming-methodology` | 383 | 契约驱动 + TDD + 质量评估工作流 |
| `helen-python-bridge` | 576 | Python ↔ Helen 集成（FFI + Bridge） |
| `hellen-consistency-checker` | 1041 | 设计文档一致性检查 |

### 通用技能

| 技能 | 行数 | 说明 |
|------|------|------|
| `code-quality` | 402 | 7 维评分、预提交验证、并行清理 |
| `debugging` | 610 | 系统化调试方法论 + 语言特定工具 |
| `planning` | 330 | Plan 模式 + 实现计划编写技巧（由 plan 和 writing-plans 合并） |
| `test-driven-development` | 354 | 严格 TDD 执行（RED-GREEN-REFACTOR） |
| `subagent-driven-development` | 624 | 通过子 Agent 执行计划，两阶段审查 |
| `github` | 323 | 完整 GitHub 工作流（PR、Issue、CI/CD） |

> 💡 技能系统经过重组优化，总行数从 10,672 减少到 9,086（-15%），上下文占用显著降低。

## 练习

1. 在 `~/.helen/skills/` 下创建一个 `greeting` 技能
2. 为当前项目创建 `.helen/skills/` 目录，添加项目规范技能
3. 在 REPL 中用 `:ask` 测试技能是否被正确感知
4. 编写 Helen 程序，使用 `llm act` 调用会参考技能的 Agent
