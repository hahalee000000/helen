# 技能系统

> Helen 技能系统 — 为 AI Agent 提供专业知识和工作流

---

## 概述

Helen 技能系统采用**三层搜索架构**，确保语言自带知识、用户自定义和项目特定技能都能被正确使用。

```
┌─────────────────────────────────────────┐
│  🥇 项目级  <project>/.helen/skills/    │  ← 最高优先级
├─────────────────────────────────────────┤
│  🥈 用户级  ~/.helen/skills/            │  ← 用户全局技能
├─────────────────────────────────────────┤
│  🥉 内置    ~/helen/skills/             │  ← 随语言分发
├─────────────────────────────────────────┤
│  4️⃣ Hermes  ~/.hermes/skills/          │  ← 兼容回退
├─────────────────────────────────────────┤
│  5️⃣ Hermes  ~/.hermes/hermes-agent/    │  ← 兼容回退
│           skills/                       │
└─────────────────────────────────────────┘
```

**高优先级覆盖低优先级**：如果多个目录中有同名技能，优先级高的版本会被使用。

---

## 三层搜索详解

### 🥇 项目级技能

位于项目根目录的 `.helen/skills/`，用于存放项目特有的知识：

```
my-project/
├── .helen/
│   └── skills/
│       └── my-api/
│           └── SKILL.md       # 项目 API 文档
├── main.helen
└── agents/
```

**用途**：
- 项目 API 文档
- 业务规则说明
- 团队编码规范
- 部署指南

**优点**：
- 可以 git 提交，团队共享
- 不污染用户全局技能
- 优先级最高，确保项目知识被优先使用

### 🥈 用户级技能

位于 `~/.helen/skills/`，用于存放用户的全局技能：

```bash
~/.helen/
├── config.yaml
└── skills/
    └── my-workflow/
        └── SKILL.md
```

**用途**：
- 个人常用工作流
- 跨项目通用的自定义技能

### 🥉 内置技能

位于 `<helen-install>/skills/`，随 Helen 语言一起分发：

```
~/helen/skills/
├── README.md
├── LICENSE-THIRD-PARTY.md
├── software-development/
│   ├── helen-language-development/   # Helen 语言模式与陷阱
│   ├── helen-syntax/                 # 语法参考
│   ├── helen-stdlib/                 # 标准库指南
│   ├── helen-security/               # 安全最佳实践
│   ├── helen-agent-patterns/         # Agent 设计模式
│   ├── code-quality/                 # 7 维质量评估
│   ├── debugging/                    # 调试方法论
│   ├── test-driven-development/      # TDD 工作流
│   └── ...
└── devops/
    ├── hellen-consistency-checker/   # 设计一致性检查
    └── github/                       # GitHub 工作流
```

**当前内置 13 个技能**：

| 技能 | 类别 | 说明 |
|------|------|------|
| `helen-language-development` | Helen 专属 | 语言模式、陷阱、最佳实践 |
| `helen-syntax` | Helen 专属 | 语法参考（关键字、类型、表达式） |
| `helen-stdlib` | Helen 专属 | 193 个标准库函数使用指南 |
| `helen-agent-patterns` | Helen 专属 | Agent 设计模式 |
| `code-quality` | 开发 | 7 维代码质量评估 |
| `debugging` | 开发 | 系统化调试方法论 |
| `test-driven-development` | 开发 | TDD RED-GREEN-REFACTOR |
| `writing-plans` | 开发 | 实现计划编写 |
| `plan` | 开发 | 计划模式（只写不执行） |
| `subagent-driven-development` | 开发 | 子代理驱动开发 |
| `hellen-consistency-checker` | DevOps | 设计文档一致性检查 |
| `github` | DevOps | GitHub 工作流 |

---

## 两层披露机制

Helen 使用**两层技能披露**，平衡知识覆盖和 token 消耗：

### Tier 1 — 技能索引（轻量）

所有技能的名称、描述和标签被收集成索引，注入到 LLM 的系统提示中：

```
<available_skills>
Before replying, scan skills below. If relevant,
use load_skill tool to load full content.

  devops:
    - github: Complete GitHub workflow (tags: GitHub, Git, Pull-Requests, Issues, Code-Review)
  software-development:
    - helen-syntax: Helen 语法参考 (tags: helen, syntax, reference, language)
    - helen-stdlib: 193 个标准库函数 (tags: helen, stdlib, builtins, reference)
  ...
</available_skills>
```

**特点**：
- 包含 name + description + category + **tags**（轻量级）
- tags 字段帮助 LLM 通过关键词快速定位相关技能，提升命中率
- 帮助 LLM 决定需要加载哪个技能

### Tier 2 — 完整加载（按需）

当 LLM 需要某个技能的详细内容时，调用 `load_skill` 工具：

```python
# LLM 通过 function calling 调用
load_skill(name="helen-stdlib")
# 返回完整的 SKILL.md 内容
```

**特点**：
- 按需加载，节省 token
- 包含完整的参考文档和示例

---

## 技能格式

每个技能是一个包含 `SKILL.md` 的目录：

```
my-skill/
├── SKILL.md          # 必需：技能主文件
├── references/       # 可选：参考文档
├── templates/        # 可选：模板文件
├── scripts/          # 可选：辅助脚本
└── assets/           # 可选：静态资源
```

### SKILL.md 格式

```markdown
---
name: my-skill
description: "技能描述"
version: 1.0.0
author: 作者名
license: MIT
tags: [helen, tutorial]
---

# 技能标题

## 概述
技能内容...

## 示例
代码示例...
```

---

## 创建自定义技能

### 1. 项目级技能

```bash
cd my-project/
mkdir -p .helen/skills/my-api/
cat > .helen/skills/my-api/SKILL.md << 'EOF'
---
name: my-api
description: "My Project API 文档"
version: 1.0.0
---

# My API

## Endpoints
- GET /api/users
- POST /api/users
EOF
```

### 2. 用户级技能

```bash
mkdir -p ~/.helen/skills/my-workflow/
# 创建 SKILL.md...
```

---

## 实现细节

技能搜索由 `helen/runtime/config.py` 的 `get_skill_dirs()` 函数实现：

```python
def get_skill_dirs() -> list[Path]:
    """返回技能目录列表，按优先级排序。"""
    dirs = []

    # 1. 项目级（当前目录向上查找 .helen/skills/）
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        project_skills = parent / ".helen" / "skills"
        if project_skills.exists():
            dirs.append(project_skills)
            break

    # 2. 用户级
    helen_skills = Path.home() / ".helen" / "skills"
    if helen_skills.exists():
        dirs.append(helen_skills)

    # 3. 内置（随 Helen 安装）
    helen_package = Path(__file__).parent.parent.parent
    builtin_skills = helen_package / "skills"
    if builtin_skills.exists():
        dirs.append(builtin_skills)

    # 4-5. Hermes 回退
    hermes_skills = Path.home() / ".hermes" / "skills"
    if hermes_skills.exists():
        dirs.append(hermes_skills)

    return dirs
```

---

## 统计

| 层级 | 技能数 | 说明 |
|------|--------|------|
| 内置 | 13 | 随 Helen 分发 |
| Hermes 回退 | 63 | 兼容 Hermes Agent |
| Hermes Agent | 73 | Hermes 核心技能 |
| **总计** | **149** | 所有可用技能 |
