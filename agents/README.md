# Helen Programming Agent

> 用 Helen 语言编写的自进化编程助手，具备 Hermes 级别的技能自进化能力。

## 架构

```
agents/
├── programming_agent.helen     # 核心编排 Agent
├── skill_manager.helen         # 技能 CRUD
├── skill_matcher.helen         # 技能搜索匹配
├── skill_learner.helen         # 技能学习（自进化）
├── skill_evolver.helen         # 技能进化（更新）
├── contracts/                  # Python 接口契约
│   ├── __init__.py
│   └── agent_contracts.py
├── skills/                     # 技能库（全局，跨项目共享）
│   ├── SKILL_INDEX.md
│   ├── error-patterns/
│   ├── code-quality/
│   ├── testing/
│   └── architecture/
├── memory/                     # Agent 记忆
│   ├── MEMORY.md
│   └── USER.md
├── HELEN_LANGUAGE_ISSUES.md    # Helen 语言不足记录
└── README.md
```

## Agent 说明

### ProgrammingAgent（核心编排）

协调所有子 Agent，提供完整的编程辅助。

**参数**：
- `project_dir: str` — 项目目录
- `user_input: str` — 用户输入

**工作流**：
1. 加载 Agent 记忆
2. 搜索技能库匹配已知模式
3. 如果匹配到技能，优先复用
4. 如果没有匹配，用 LLM 推理
5. 如果修复成功，提取新模式保存为技能
6. 更新 Agent 记忆

### SkillManager（技能 CRUD）

管理技能的创建、读取、更新、删除、列表。

**参数**：
- `action: str` — "create" | "read" | "update" | "delete" | "list"
- `name: str` — 技能名称
- `category: str` — 技能类别
- `content: str` — SKILL.md 内容

### SkillMatcher（技能搜索）

根据上下文搜索匹配的技能。

**参数**：
- `context: str` — 错误信息、代码片段或问题

**返回**：
- 匹配的技能列表
- 提取的关键词

### SkillLearner（技能学习）

从成功修复中学习新模式，保存为新技能。

**参数**：
- `error: map` — 错误信息
- `fix: str` — 应用的修复
- `confirmed: bool` — 用户是否确认修复成功

### SkillEvolver（技能进化）

根据新发现更新已有技能。

**参数**：
- `skill_path: str` — 技能文件路径
- `new_finding: str` — 新发现

## 技能格式

```markdown
---
name: skill-name
description: "技能描述"
version: 1.0.0
category: error-patterns
tags: [tag1, tag2]
triggers:
  - error_type: "RuntimeError"
    message_contains: "error message"
confidence: 0.9
occurrences: 5
---

# Skill Name

## Trigger
触发条件描述

## Steps
1. 步骤一
2. 步骤二

## Pitfalls
- 注意事项
```

## 自进化循环

```
解决问题 → 用户确认 → 提取模式 → 保存为技能 → 下次复用
```

## 使用方法

```helen
// 在 Helen 代码中使用
let result = ProgrammingAgent(
    project_dir="~/my-project",
    user_input="How do I fix division by zero?"
)
print(result["response"])
```

## 开发

### 运行测试

```bash
python -m pytest tests/agents/ -v
```

### 检查语法

```bash
helen check agents/programming_agent.helen
helen check agents/skill_manager.helen
# ...
```

## Helen 语言不足

开发过程中发现的 Helen 语言限制记录在 `HELEN_LANGUAGE_ISSUES.md`。

主要问题：
1. 不支持 `and` / `or` / `else if`
2. 不支持闭包
3. 不支持匿名函数作为参数
4. 保留字过多（match, skills, user 等）
5. Agent functions 块只能有 fn 声明
