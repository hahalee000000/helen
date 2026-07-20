# Agent DSL Landscape Research — Mochi / Mog / Barnum / AISP

**调研日期**：2026-07-20
**调研目的**：梳理 GitHub 上 4 个与 AI Agent 相关的编程语言/协议项目，对比 Helen 定位

---

## 📊 总览对比

| 项目 | Stars | Forks | 主语言 | 协议 | 创建时间 | 最新发布 | 定位 |
|------|-------|-------|--------|------|----------|----------|------|
| **mochilang/mochi** | 336 ⭐ | 13 | Go (含 Scheme 组件) | MIT | 2025-05-18 | v0.16.0 (2026-06-01) | Agent/Data/AI 嵌入式 DSL |
| **voltropy/mog** | 139 ⭐ | 9 | Rust | MIT | 2026-02-01 | 无 | 安全 AI agent 脚本语言 |
| **barnum-circus/barnum** | 137 ⭐ | 5 | TypeScript | MIT | 2026-03-10 | 无 | 异步 agent 编排语言 |
| **bar181/aisp-open-core** | 171 ⭐ | 22 | （多语言，无主语言） | Other | 2026-01-12 | 无 | AI 符号协议（非编程语言） |

---

## 🍡 1. mochilang/mochi — Agent/Data/AI 嵌入式语言

- **仓库**：<https://github.com/mochilang/mochi>
- **官网**：<https://mochi-lang.dev>
- **Tagline**："A small, fast, embeddable programming language designed for agents, data, and AI"

### 核心特性

- **静态类型** + 函数式语法 + 流优先语义
- **原生数据集/图/模拟**支持
- **零依赖单二进制**，字节码 VM 内置于 CLI
- **内建 `test` / `expect` 测试块**
- **字节码优化**：常量折叠 + 基于活跃度的死码消除
- **MCP Server 兼容**：可作为 VS Code Agent Mode / Claude Desktop 的 MCP 工具
- **LSP 语言服务器**

### 技术栈

- **主实现**：Go（`go.mod` + `cmd/` 目录）
- **3 个编译器版本**：`compiler/`、`compiler2/`、`compiler3/`（迭代演进）
- **Beam/OTP27 版本**：`Dockerfile.beam-otp27`（Erlang VM 实验版）
- **LLM 集成**：`llm/` 目录，支持 llama.cpp、OpenAI 兼容 API
- **Topics**：`agent`, `ai`, `graph`, `stream`, `leetcode`

### 安装方式

- 预编译二进制（推荐）
- Docker：`docker run -i --rm ghcr.io/mochilang/mochi`
- 源码构建（需 Deno 跑 TS 测试）

### 关键命令

```bash
mochi run examples/hello.mochi
mochi test examples/math.mochi
mochi build examples/hello.mochi -o hello
mochi serve   # 启动 MCP server
```

### MCP 集成示例（Claude Desktop）

```json
{
  "mcpServers": {
    "mochi": {
      "command": "/path/to/mochi",
      "args": ["serve"]
    }
  }
}
```

### 与 Helen 的相似度

**高**。都是面向 agent 的嵌入式 DSL，都有静态类型、MCP 支持、LSP、test 内建。但 Mochi 偏向函数式+流语义，Helen 偏向 prompt-first + 中文双语。

---

## 🔒 2. voltropy/mog — 纯 Rust 安全脚本语言

- **仓库**：<https://github.com/voltropy/mog>
- **Tagline**："A small, statically-typed, embeddable programming language"
- **定位**："Statically-typed Lua with async I/O + capability model"

### 设计哲学（6 条，极克制）

1. **小表面积** — 整个语言可放入 LLM context window
2. **可预测语义** — 无隐式转换、无运算符优先级陷阱、无隐藏控制流
3. **熟悉语法** — `{}`、`fn`、`->`、`:=`，Rust/Go/TS 混合体，LLM 已经能熟练生成
4. **默认安全** — GC + 边界检查 + 无 null + 无裸指针
5. **Host 提供 I/O** — 语言本身无文件/网络/系统访问，所有副作用通过 capability 授予
6. **Host 提供计算** — ML/DB/网络由宿主暴露 capability，语言本身保持精简

### 技术栈（纯 Rust）

- **编译器**：`mogc`（`compiler/`，Rust 原生）
- **运行时**：`runtime-rs/`（~6K 行 Rust）
- **QBE 后端**：`rqbe/`（~15K 行 safe Rust 重写的 QBE，进程内原生代码生成）
- **1,146+ 编译器测试** + 186 后端测试

### 编译产物

```bash
mogc program.mog -o program      # 原生二进制
mogc program.mog -O2             # 优化
mogc program.mog --emit-ir       # 输出 QBE IR
mogc program.mog --plugin ...    # 动态链接库
mogc program.mog --link host.rs  # 链接宿主能力
```

### 类型系统

- 基础：`int`/`float`/`bool`/`string`
- **张量元素精度类型**：`i8`~`i64`、`u8`~`u64`、`f16`/`bf16`/`f32`/`f64`（面向 AI tensor）
- 显式 `as` 类型转换，无隐式

### 特性

- 闭包（first-class functions）
- 命名参数 + 默认值
- `if`/`else` 作为表达式
- `for i in 0..10`、`for key, value in map`
- `break`/`continue`
- Async I/O
- Capability 模型（`requires http, model`）

### 显式不做

无裸指针、无手动内存管理、无线程、无 POSIX 系统调用、无继承、无宏、无泛型。**每个省略都是刻意的**。

### Rust 嵌入 API

```rust
use mog::compiler::{compile, compile_to_binary, CompileOptions};

let source = r#"fn main() { println("hello"); }"#;
let result = compile(source, None);
println!("{}", result.ir);  // QBE IL output
```

### C 嵌入 API

```c
#include "mog_compiler.h"

MogCompiler *c = mog_compiler_new();
MogCompileResult *r = mog_compile(c, source, source_len, NULL);
const char *ir = mog_result_ir(r);
```

### 与 Helen 的相似度

**中等**。都是嵌入式 + 面向 agent，但 Mog 更克制、更偏"安全 Lua"，编译到原生码；Helen 更丰富、prompt-first、带中文双语和完整 LLM 工具链。

---

## 🎪 3. barnum-circus/barnum — 异步 Agent 编排语言

- **仓库**：<https://github.com/barnum-circus/barnum>
- **Tagline**："A programming language for parallel and asynchronous computation that makes it easy to orchestrate AI agents"

### 核心问题

LLM agent 上下文满了会健忘，无法可靠执行复杂多步计划。Barnum 用**异步工作流 = 状态机**解决：

- 每个 handler 在**独立 Node.js 子进程**执行
- 每个 agent 步骤**只看到自己需要的上下文**（渐进式上下文披露）
- Rust 运行时管理状态机：跟踪 pending、dispatch、收集结果、推进工作流

### 设计范式

```ts
// handlers 是 TypeScript async 函数
import { createHandler } from "@barnum/barnum/runtime";
import { z } from "zod";

export const refactor = createHandler({
  inputValidator: z.string(),
  handle: async ({ value: file }) => {
    await callAgent({
      prompt: `Refactor ${file}...`,
      allowedTools: ["Read", "Edit"]
    });
  },
}, "refactor");

// 组合子：pipe、forEach、loop、branch、tryCatch、withTimeout
import { pipe } from "@barnum/barnum/pipeline";
listFiles.forEach(pipe(refactor, typeCheck, fix, commit, createPR)).run();
```

### 一等组合子

- `pipe` — 顺序
- `forEach` — fan-out 并行
- `loop` — 带递归回调 `recur`
- `branch` — 模式分支
- `tryCatch` — 错误处理
- `withTimeout` — 超时

### 架构亮点

- **代数效应处理器**（Algebraic Effect Handlers）
- **TypeScript AST** 作为语言载体
- **Zod schema** 做输入输出验证
- **Worktree 隔离** 支持

### Demos

| Demo | 描述 |
|------|------|
| `simple-workflow` | 列文件 → 重构/类型检查/修复/提交/PR |
| `retry-on-error` | 失败重试流水线 |
| `convert-folder-to-ts` | JS 转 TS，迭代类型错误 |
| `identify-and-address-refactors` | worktree 隔离重构 |

### 进阶模式（Repertoire）

- `tryCatch` with retry
- `withTimeout`
- worktree 隔离
- LLM-powered code review loops

### 文档体系

- [Architecture overview](https://barnum-circus.github.io/docs/architecture/)
- [TypeScript AST](https://barnum-circus.github.io/docs/architecture/typescript-ast)
- [Compiler and execution model](https://barnum-circus.github.io/docs/architecture/compiler)
- [Algebraic effect handlers](https://barnum-circus.github.io/docs/architecture/algebraic-effect-handlers)
- [Validation](https://barnum-circus.github.io/docs/architecture/validation)

### 与 Helen 的相似度

**低**。Barnum 不是独立的语言，是 TypeScript 的编排 DSL。核心是**工作流状态机 + 代数效应 + 上下文隔离**。Helen 的 `spawn` + `Channel` 模型与 Barnum 思路有相似之处，但 Barnum 更工程化、更偏生产级 agent 编排。

---

## 🔣 4. bar181/aisp-open-core — AI 符号协议（非编程语言）

- **仓库**：<https://github.com/bar181/aisp-open-core>
- **Tagline**："The Assembly Language for AI Cognition"
- **作者**：Bradley Ross

### 它不是编程语言

AISP 是**协议/符号系统**——用数学符号（逻辑、类型论、范畴论）替代模糊的自然语言 prompt。

### 核心主张

| 指标 | 传统 Prompt | AISP |
|------|-------------|------|
| 歧义率 | 40-65% | <2% |
| 误解率 | 25-40% | <1% |
| 10 步流水线成功率 | 59% | 95% |
| 澄清请求 | 3-5 次/任务 | 0-1 次 |

**97 倍提升**在多步流水线成功率。

### 512 个官方符号（Σ_512）

8 类 × 64 个：

| 类别 | 用途 |
|------|------|
| Transmuters | 转换器 |
| Topologics | 拓扑 |
| Quantifiers | 量词 |
| Contractors | 约束 |
| Domains | 域 |
| Intents | 意图 |
| Delimiters | 分隔符 |
| Reserved | 保留 |

### 速查（Rosetta Stone）

| 自然语言 | AISP 符号 | 类别 |
|---------|-----------|------|
| "for all, every" | `∀` | Quantifier |
| "there exists" | `∃` | Quantifier |
| "exists unique" | `∃!` | Quantifier |
| "defined as" | `≜` | Definition |
| "assigned, becomes" | `≔` | Assignment |
| "implies" | `⇒` | Logic |
| "iff" | `⇔` | Logic |
| "and" / "or" / "not" | `∧` `∨` `¬` | Logic |
| "element of" | `∈` | Set |
| "subset of" | `⊆` | Set |
| "union" / "intersection" | `∪` `∩` | Set |
| "true" / "false" | `⊤` `⊥` | Truth |
| "lambda" | `λ` | Function |
| "maps to" | `↦` | Function |

### 示例

| 自然语言 | AISP 表示 |
|---------|-----------|
| "Define x as 5" | `x≜5` |
| "For all users, if admin then allow" | `∀u∈Users:admin(u)⇒allow(u)` |
| "There exists a valid solution" | `∃x:valid(x)` |

### 质量分级（按语义密度 δ）

| 等级 | 符号 | δ 阈值 | 用途 |
|------|------|--------|------|
| Platinum | ◊⁺⁺ | ≥ 0.75 | 生产规范、AI-AI 契约 |
| Gold | ◊⁺ | ≥ 0.60 | 高质量文档 |
| Silver | ◊ | ≥ 0.40 | 工作草稿 |
| Bronze | ◊⁻ | ≥ 0.20 | 初始转换 |
| Reject | ⊘ | < 0.20 | 无效 |

### 工具链

```bash
# npm
npx aisp-converter "Define x as 5"   # 自然语言 → AISP：x≜5
npx aisp-validator validate spec.aisp
npx aisp-validator tier myspec.aisp  # 输出：◊⁺ Gold

# Rust（最快）
cargo install aisp aisp-converter
aisp validate spec.aisp
```

### 文档体系

| 文档 | 用途 |
|------|------|
| **AI_GUIDE.md** | AISP 5.1 Platinum 官方规范（AI 直接可读） |
| **HUMAN_GUIDE.md** | 人类教程 |
| **CHEATSHEET.md** | 512 符号速查 |
| **reference.md** | 完整 512 符号词汇表 |
| **guides/advanced/01_PHYSICS.md** | 信号理论、Pockets、Binding |
| **guides/advanced/02_COGNITION.md** | Hebbian 学习、Ghost Search、递归 |
| **guides/advanced/03_MATH.md** | 范畴论、Error Algebra、推理 |
| **guides/advanced/04_AGENT.md** | 模板、证据、执行 |

### 与 Helen 的关系

**互补**。AISP 可以替代 Helen 的 prompt 写法——把自然语言 prompt 替换为精确的 AISP 符号，降低 LLM 歧义。Helen 的 `llm act "prompt"` 中的 prompt 部分可以用 AISP 符号重写。

---

## 🎯 对 Helen 的启示

| 项目 | 可借鉴的点 |
|------|-----------|
| **Mochi** | MCP Server 集成、字节码优化、`test`/`expect` 内建、流语义 |
| **Mog** | 极克制设计哲学、capability 模型、rqbe 进程内原生编译、tensor 精度类型 |
| **Barnum** | `pipe`/`forEach`/`loop`/`branch` 一等编排组合子、代数效应、handler 子进程隔离 |
| **AISP** | 512 符号协议可作为 Helen prompt 的精确表达层，降低 LLM 决策点 |

### 详细建议

1. **MCP Server**：Mochi 已经有 `mochi serve`，Helen 可以考虑把 `helen lsp` 扩展为同时支持 MCP 协议
2. **字节码优化**：Helen 当前是纯解释执行，可参考 Mochi 的常量折叠 + 死码消除
3. **Capability 模型**：Mog 的 `requires http, model` 显式声明思路比 Helen 的 `tools = [...]` 更声明式
4. **编排组合子**：Barnum 的 `pipe`/`forEach`/`loop`/`branch` 可作为 Helen `spawn` + `Channel` 的高层封装
5. **AISP 集成**：可在 stdlib 中提供 `aisp()` 函数，将自然语言转 AISP 符号后喂给 LLM

---

## 📈 市场观察

- **Stars 量级**：Mochi (336) > AISP (171) > Mog (139) > Barnum (137)，都处于早期阶段
- **活跃度**：Mochi 最活跃（v0.16.0 已发布，持续迭代），其他 3 个都未发布正式版本
- **语言载体**：Rust (Mog) 和 Go (Mochi) 是主流实现选择；Barnum 选择 TypeScript 是因其定位是 TS 编排 DSL
- **共同趋势**：所有项目都在解决"如何让 LLM agent 可靠地执行复杂任务"——通过嵌入式语言、能力约束、状态机编排、符号精确化等不同角度

---

**相关文档**：

- Helen 当前版本：v1.23.0（2026-07-20）
- Helen 多模态提案：`reports/multimodal-proposal.md`
- Helen spawnagent 提案：`reports/spawnagent-proposal.md`
