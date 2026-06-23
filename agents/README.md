# Helen Programming Agent

> 用纯 Helen 语言实现的自进化编程助手，具备 Hermes 级别的技能自进化能力。

## 架构

```
agents/
├── programming_agent.helen     # 主 Agent（agent block + LLM 集成）
├── contracts/
│   └── contracts.helen         # 协议定义 + 函数实现（契约优先）
├── skills/                     # 技能库（全局，跨项目共享）
│   ├── SKILL_INDEX.md          # 自动维护的技能索引
│   ├── error-patterns/         # 错误修复模式
│   ├── code-quality/           # 代码质量改进
│   ├── testing/                # 测试模式
│   └── architecture/           # 架构模式
├── memory/                     # Agent 记忆
│   ├── MEMORY.md               # Agent 学习笔记
│   └── USER.md                 # 用户偏好
└── README.md
```

## 设计原则

1. **纯 Helen 语言**：Agent 和所有业务逻辑用 Helen 编写
2. **契约优先 + TDD**：Protocol 定义接口 → Python 测试验证 → Helen 实现
3. **技能自进化**：解决问题 → 提取模式 → 保存 SKILL.md → 下次复用
4. **全局共享**：技能存储在 `agents/skills/`，跨项目复用

## 核心模块

| 模块 | 功能 | 协议 |
|------|------|------|
| SkillManager | 技能 CRUD | `SkillManagerContract` |
| SkillMatcher | 关键词搜索匹配 | `SkillMatcherContract` |
| SkillLearner | 从修复中学习 | `SkillLearnerContract` |
| SkillEvolver | 技能进化更新 | `SkillEvolverContract` |
| ProgrammingAgent | 编排 + 质量分析 | `ProgrammingAgentContract` |

## 使用方式

```bash
# 直接运行
helen agents/programming_agent.helen

# 语法检查
helen agents/contracts/contracts.helen
helen agents/programming_agent.helen

# 运行测试
python -m pytest tests/agents/test_contracts.py -v
```

## 自进化循环

```
用户遇到问题 → Agent 诊断 → 搜索技能库
    ├── 匹配到 → 复用已知方案
    └── 未匹配 → LLM 推理解决
         ↓
用户确认修复成功 → 提取模式 → 保存为 SKILL.md
         ↓
更新 SKILL_INDEX.md → 下次自动匹配
```

## 技能格式（兼容 Hermes）

```markdown
---
name: skill-name
description: "技能描述"
version: 1.0.0
category: error-patterns
---

# 技能名称

## 触发条件
- 错误类型 / 场景描述

## 修复步骤
1. 步骤一
2. 步骤二

## 陷阱
- 边界情况
```

## 测试覆盖

- **35 个 Python 测试**覆盖所有契约函数
- 测试使用 subprocess 运行 Helen 代码，验证端到端行为
- 涵盖：CRUD、关键词提取、技能匹配、学习、进化、索引管理

## Helen 语言特性使用

| 特性 | 版本 | 用途 |
|------|------|------|
| `agent` block | v1.5 | Agent 定义 |
| `protocol` | v1.7 | 接口契约 |
| `import` | v1.6 | 模块导入 |
| `match` 表达式 | v1.8 | 范围模式匹配 |
| `\|\|` / `&&` | v1.7 | 逻辑运算 |
| `!` 操作符 | v1.7 | 逻辑非 |
| `regex_test` | v1.8 | 布尔正则检查 |
| `{{var}}` 模板 | v1.5 | Prompt 渲染 |
| `llm stream` | v1.8 | 流式输出 |
| 闭包 `fn() {}` | v1.7 | 匿名函数 + 环境捕获 |
| `map/filter` + lambda | v1.7 | 函数式数据处理 |

## Helen 语言不足（开发中发现）

详见 `memory/MEMORY.md` 的「Helen 语言不足」部分。

**已修复**：
- ✅ `join(list, sep)` 参数顺序 — v1.8.1 修复
- ✅ Regex 函数参数顺序统一 — v1.8.1 修复
- ✅ `true`/`false` 打印为小写 — v1.8.1 修复

**待改进**：
- 无字符串插值，长字符串拼接冗长
- 多行字符串保留缩进，影响 prompt 模板可读性
