# Helen Skills

Helen 技能系统 — 为 AI Agent 提供专业知识和工作流。

## 目录结构

```
~/helen/skills/                    ← 内置技能（随语言分发）
├── README.md                      ← 本文件
├── LICENSE-THIRD-PARTY.md         ← 第三方许可声明
├── software-development/          ← 开发方法论技能
│   ├── helen-language-development/   ← Helen 语言模式与陷阱
│   ├── helen-syntax/                 ← Helen 语法参考
│   ├── helen-stdlib/                 ← 标准库使用指南
│   ├── helen-security/               ← 安全最佳实践
│   ├── helen-agent-patterns/         ← Agent 设计模式
│   ├── code-quality/                 ← 7 维质量评估
│   ├── debugging/                    ← 调试方法论
│   ├── test-driven-development/      ← TDD RED-GREEN-REFACTOR
│   ├── writing-plans/                ← 实现计划编写
│   ├── plan/                         ← 计划模式（只写不执行）
│   └── subagent-driven-development/  ← 子代理执行工作流
└── devops/                        ← DevOps 技能
    ├── hellen-consistency-checker/   ← 设计文档一致性检查
    └── github/                       ← GitHub 工作流（PR、issue、CI/CD）
```

## 技能搜索优先级

Helen 按以下顺序搜索技能（高优先级覆盖低优先级）：

| 优先级 | 位置 | 说明 |
|--------|------|------|
| 1（最高） | `<project>/.helen/skills/` | **项目级** — 当前项目特有的技能 |
| 2 | `~/.helen/skills/` | **用户级** — 用户的全局技能 |
| 3 | `<helen-install>/skills/` | **内置** — 随 Helen 语言分发（本目录） |
| 4 | `~/.hermes/skills/` | **Hermes 回退** — 兼容 Hermes Agent |
| 5（最低） | `~/.hermes/hermes-agent/skills/` | **Hermes agent 技能** |

### 项目级技能

在你的项目根目录创建 `.helen/skills/` 目录，添加项目特有的技能：

```
my-project/
├── .helen/
│   └── skills/
│       └── my-api/
│           └── SKILL.md       # 项目 API 文档
├── main.helen
└── agents/
```

项目级技能优先级最高，可以覆盖内置技能和用户技能。

## 技能如何工作

Helen 使用**两层技能披露**机制：

1. **Tier 1 — 技能索引**：轻量级元数据（名称 + 描述）注入到系统提示的 `<available_skills>` 部分。帮助 AI 代理决定加载哪个技能。

2. **Tier 2 — 完整内容**：当代理需要某个技能时，调用 `load_skill` 工具读取完整的 `SKILL.md` 内容。

## 技能格式

每个技能是一个包含 `SKILL.md` 文件的目录，使用 YAML frontmatter：

```markdown
---
name: skill-name
description: "技能描述"
version: 1.0.0
author: 作者名
license: MIT
tags: [tag1, tag2]
---

# 技能标题

技能内容（Markdown 格式）...
```

技能还可以包含：
- `references/` — 参考文档
- `templates/` — 模板文件
- `scripts/` — 辅助脚本
- `assets/` — 静态资源

## 内置技能列表

| 技能 | 类别 | 说明 |
|------|------|------|
| `helen-language-development` | Helen 专属 | Helen 语言模式、陷阱、最佳实践 |
| `helen-syntax` | Helen 专属 | Helen 语法参考（关键字、类型、表达式） |
| `helen-stdlib` | Helen 专属 | 185 个标准库函数使用指南 |
| `helen-security` | Helen 专属 | 安全沙箱、路径验证、SSRF 防护 |
| `helen-agent-patterns` | Helen 专属 | Agent 设计模式（路由、并发、错误处理） |
| `code-quality` | 开发 | 7 维代码质量评估方法论 |
| `debugging` | 开发 | 系统化调试方法论 |
| `test-driven-development` | 开发 | TDD RED-GREEN-REFACTOR 工作流 |
| `writing-plans` | 开发 | 实现计划编写指南 |
| `plan` | 开发 | 计划模式（只写计划，不执行） |
| `subagent-driven-development` | 开发 | 子代理驱动的开发工作流 |
| `hellen-consistency-checker` | DevOps | 设计文档与代码一致性检查 |
| `github` | DevOps | GitHub 工作流（PR、issue、CI/CD） |

## 归属声明

本目录中的大部分技能源自 [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research，遵循 MIT 许可证使用。详见 `LICENSE-THIRD-PARTY.md`。

每个技能目录包含 `ATTRIBUTION.md` 文件，提供具体的归属信息。
