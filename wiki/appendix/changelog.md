# 版本历史

> Helen v1.9 | Phase 0-10 全部实现 + 中文语法

---

## v1.9: 中文语法支持 (当前)

| 改进 | 说明 | 状态 |
|------|------|------|
| 中文关键字 | 44 个中文关键字映射到相同 TokenType | ✅ |
| 中文标识符 | CJK 统一表意文字支持（变量名、函数名） | ✅ |
| 中英混合 | 中英文关键字可自由混用 | ✅ |
| 零侵入 | 解析器、解释器、AST 零改动 | ✅ |

**设计**：中文关键字在词法层直接映射到英文 TokenType（如 `让` → `LET`），下游完全无感知。仅修改 `tokens.py`（+44 行映射）和 `lexer.py`（+30 行 CJK 字符集）。

**示例**：

```helen
// 纯中文
函数 斐波那契(n: int): int {
    如果 n <= 1 {
        返回 n
    } 否则 {
        返回 斐波那契(n - 1) + 斐波那契(n - 2)
    }
}

// 中英混合
让 结果 = 斐波那契(10)
const LIMIT = 100
如果 结果 < LIMIT {
    print("OK")
}
```

**质量**: 30 个新测试，1480+ 核心测试通过，0 regression

---

## v1.8: 函数式编程增强 (当前)

| 改进 | 说明 | 状态 |
|------|------|------|
| 管道操作符 `\|>` | `value \|> fn` 等价于 `fn(value)` | ✅ |
| 通配符模式 | `case _ { }` 匹配任何值 | ✅ |
| 变量绑定模式 | `case x { }` 绑定值到变量 | ✅ |
| 类型模式 | `case is Type { }` 检查类型 | ✅ |
| 类型模式带绑定 | `case is Type name { }` | ✅ |

**新增语法**：

```helen
// 管道操作符
let result = "hello" |> upper |> strip
let doubled = 5 |> double

// 通配符模式
match value {
    case 1 { print("one") }
    case _ { print("other") }  // 匹配任何值
}

// 变量绑定
match value {
    case n if n > 0 { print("positive: " + str(n)) }
    case n if n < 0 { print("negative: " + str(n)) }
    case _ { print("zero") }
}

// 类型模式
match value {
    case is String { print("it's a string") }
    case is Int { print("it's an int") }
    case _ { print("unknown type") }
}

// 类型模式带绑定
match value {
    case is String s { print("string: " + s) }
    case _ { print("not a string") }
}
```

**质量**: 19 个新测试，307+ 核心测试通过

---

## v1.7: 闭包与协议

| 改进 | 说明 | 状态 |
|------|------|------|
| 闭包/匿名函数 | `fn(x, y) { return x + y }` | ✅ |
| 词法作用域 | 闭包捕获定义时环境 | ✅ |
| 协议声明 | `protocol Name { fn method() }` | ✅ |
| 协议实现 | `impl Name for Type { }` | ✅ |

**新增语法**：

```helen
// 匿名函数
let add = fn(x, y) { return x + y }
print(add(1, 2))  // 3

// 闭包
fn make_counter() {
    let count = 0
    return fn() {
        count = count + 1
        return count
    }
}

let counter = make_counter()
print(counter())  // 1
print(counter())  // 2

// 协议声明
protocol Printable {
    fn to_string(self) -> String
}

// 协议实现（鸭子类型）
struct Point {
    x: Int
    y: Int
}

impl Printable for Point {
    fn to_string(self) -> String {
        return "Point(" + str(self.x) + ", " + str(self.y) + ")"
    }
}
```

**质量**: 22 个新测试，148 passed, 4 xfailed

---

## v1.6: 短期改进

| 改进 | 说明 | 状态 |
|------|------|------|
| 模块导入函数访问 | `import "module.helen" as mod` 后可访问 `mod.fn()` | ✅ |
| 错误信息增强 | 更清晰的错误提示和建议 | ✅ |

**质量**: 测试全部通过

---

## v1.5: 语言增强

| 改进 | 说明 | 状态 |
|------|------|------|
| 移除 `skills` 保留字 | `skills` 不再是关键字，可用作变量名 | ✅ |
| Agent functions 块变量 | `functions {}` 支持 `let`/`const` 声明 | ✅ |
| List 方法 | 自动支持 Python list 所有方法 | ✅ |
| Match 范围匹配 | `case 1..10 { }` 语法 | ✅ |
| Match 守卫条件 | `case x if x > 5 { }` 语法 | ✅ |

**新增语法**：

```helen
// skills 可用作变量名
let skills = ["coding", "testing"]
print(skills)

// Agent functions 块中的变量
agent MyAgent {
    functions {
        let config = "default"
        const MAX_RETRIES = 3
        
        fn get_config() -> str {
            return config
        }
    }
}

// List 方法
let items = [1, 2, 3]
items.append(4)
items.sort()
items.reverse()

// Match 范围匹配
let score = 85
match score {
    case 90..100 { print("A") }
    case 80..89 { print("B") }
    default { print("F") }
}

// Match 守卫条件
match x {
    case 1..100 if x == 42 { print("the answer") }
    case 1..100 { print("in range") }
    default { print("out of range") }
}
```

**质量**: 25 个新测试，309 个核心测试通过

---

## Phase 10: AI 原生可观测性

| 模块 | 交付 | 状态 |
|---|---|---|
| Observability | `helen/runtime/observability.py` | ✅ |
| assert 语句 | Token + AST + Parser + Interpreter | ✅ |
| debug() 内置函数 | `helen/stdlib/__init__.py` | ✅ |
| REPL 调试命令 | `:trace`, `:last_error`, `:llm_log` | ✅ |
| LLM 审计日志 | `helen/interpreter/llm_mixin.py` | ✅ |

**新增**:
- `helen.runtime.observability` — AI 原生可观测性模块（CallStackTracker、ExecutionTracer、ErrorSnapshot、LLMAuditLog、ObservabilityManager）
- `assert` 语句 — 运行时假设验证，失败自动捕获结构化错误上下文
- `debug(message, data?)` — 结构化调试输出到 stderr（JSON 格式）
- `trace_on()` / `trace_off()` / `get_trace(n)` — 程序化执行追踪控制
- REPL `:trace on|off|show` — 执行追踪 REPL 命令
- REPL `:last_error` — 显示上次错误的结构化上下文（人类可读格式）
- REPL `:llm_log [n]` — 显示 LLM 调用审计日志
- LLM 审计 — `llm act` 和 `llm stream` 自动记录调用详情（prompt/response/tokens/耗时/tool_calls）
- `AssertionError` — 新增预定义异常类型

**设计理念**: 放弃传统交互式 Debugger（断点/单步），转向 AI 原生可观测性。AI 不需要暂停/恢复，而是需要结构化的、可机器消费的上下文（JSON 错误快照、调用栈、追踪日志、LLM 审计）。REPL 中 `:last_error` 显示人类可读格式，编程访问可通过 `snapshot.to_json()` 获取 JSON 格式。

**质量**: 273+ tests passing, 新增 24 个 observability 测试

---

## Phase 9: 质量提升与架构优化

| 模块 | 交付 | 状态 |
|---|---|---|
| LLM Mixin 拆分 | `helen/interpreter/llm_mixin.py` | ✅ |
| CI/CD | `.github/workflows/ci.yml` | ✅ |
| 技能系统独立化 | `~/.helen/skills/` (145 skills) | ✅ |

**新增**:
- `helen.interpreter.llm_mixin` — LlmMixin 类，从 Interpreter 拆分 LLM 相关方法（visit_llm_act/if/stream、工具构建、历史管理、模板渲染）
- `.github/workflows/ci.yml` — GitHub Actions CI/CD（pytest + flake8 + coverage）
- `~/.helen/skills/` — 9 个 Helen 原生技能 + 136 个 Hermes fallback = 145 个技能
- `ATTRIBUTION.md` + `LICENSE-THIRD-PARTY.md` — MIT 协议归属声明

**代码质量**:
- flake8 警告从 571 → **0**
- 清理死代码：`visit_binary_op` 不可达分支、空 `_check_llm_usage`/`_check_async_usage` 方法
- 修复静默异常：15+ 处 `except Exception` 添加 `logging.debug()`
- 修复 F821：移除 `parser.py` 中 `AsyncCallExprNode` 未定义名称
- 消除代码重复：统一 `_type_from_typenode()`、`Message` 类
- 新增 344 个测试用例（interpreter/runtime 覆盖率提升）

**质量**: 1,805 tests, flake8 0 warnings, 综合评分 7.93/10

---

## Phase 8: 独立运行时

| 模块 | 交付 | 状态 |
|---|---|---|
| Config 系统 | `helen/runtime/config.py` | ✅ |
| 内置工具 | `helen/runtime/tools.py` (7 工具) | ✅ |
| 模糊匹配 | `helen/runtime/fuzzy_match.py` (9 策略) | ✅ |
| Function Calling | 多轮工具调用 + nudge | ✅ |
| `helen init` | 配置初始化 CLI 命令 | ✅ |

**新增**:
- `helen init` — 初始化 `~/.helen/` 配置目录
- `helen.runtime.config` — 独立配置管理（YAML + .env，4 级优先级）
- `helen.runtime.tools` — 7 个内置工具（web_search/web_fetch/read_file/write_file/patch_file/shell_exec/calculate）
- `helen.runtime.fuzzy_match` — 从 Hermes 集成的模糊匹配引擎（9 策略，860 行）
- Function Calling 多轮循环 + nudge 机制
- Agent `prompt` 字段作为 `system_prompt` 注入 LLM 调用
- 脚本模式直接使用 `HttpLLMRuntime`（不再 Mock）

**独立化**:
- `~/.helen/config.yaml` — Helen 独立 LLM 配置
- `~/.helen/skills/` — Helen 原生 skill 目录
- `fuzzy_match.py` — 模糊匹配引擎内置，无需 Hermes
- 向后兼容 `~/.hermes/.env` 和 `~/.hermes/skills/`

**质量**: 904 tests, 全部通过

---

## Phase 7: 工具链完善

| 模块 | 交付 | 状态 |
|---|---|---|
| M12 LSP Server | 诊断/补全/跳转 | ✅ |
| M13 VS Code Extension | TextMate 语法高亮 | ✅ |
| M15 Standard Library | 24 builtins | ✅ |

**新增**:
- `HelenHermesRuntime` — 完整 Runtime ABC 实现
- `cancel_llm_call` — LLM 调用取消机制
- `_get_context()` — 对话历史集成 HistoryManager
- `helen doc` — 文档生成子命令
- VS Code 扩展：语法高亮、括号配对、自动闭合

**质量**: 811 tests, 86.29% coverage, flake8 0 errors

---

## Phase 6: CLI 与 REPL

| 模块 | 交付 |
|---|---|
| M11 CLI | `helen run/check/repl` |
| M10 Error Formatter | HLD 3.11.2 格式输出 |

---

## Phase 5: 运行时基础设施

| 模块 | 交付 |
|---|---|
| M7 Runtime ABC | 12 抽象方法 |
| M6 PromptBuilder | 两层渐进式披露 |
| M16 HistoryManager | Token 预算/截断/摘要 |
| M17 StructuredOutput | LLM 路由 function calling |

---

## Phase 4: 解释执行与 LLM 集成

| 模块 | 交付 |
|---|---|
| M5 Interpreter | AST 遍历执行 |
| M8 ImportResolver | 多格式/路径安全/循环检测 |
| M14 Test Framework | pytest 集成 |

**关键实现**:
- `Environment` 作用域链
- `_call_agent()` 隔离 Environment
- `async call` + `await [list]` Promise.all
- `AggregateError` 并发错误聚合
- Agent 参数接口声明

---

## Phase 3: 语义分析

| 模块 | 交付 |
|---|---|
| M4 SemanticAnalyzer | 符号表/作用域/类型检查 |
| M9 Type System | 14 种类型 |

**关键实现**:
- 6 种作用域 (global/agent/fn/block/catch/loop)
- 46 Visitor 方法全部实现
- Agent 边界检查
- const 赋值保护

---

## Phase 2: AST 与错误处理

| 模块 | 交付 |
|---|---|
| M3 AST Nodes | 49 节点类 |
| M10 Errors | 42 ErrorCode |

**关键实现**:
- Visitor 模式 (46 抽象方法)
- SourceSpan 全链路
- `@dataclass(frozen=True)` 不可变节点

---

## Phase 1: 语法分析

| 模块 | 交付 |
|---|---|
| M2 Parser | Pratt Parsing × 10 级 |

**关键实现**:
- EBNF 392 行完整语法
- Panic mode 错误恢复
- `llm` 上下文关键字消歧
- `async` 前缀处理
- Agent 参数解析

---

## Phase 0: 词法分析

| 模块 | 交付 |
|---|---|
| M1 Lexer | 手写扫描器 |

**关键实现**:
- 42 关键字 (39 + true/false/null)
- 77 Token 类型
- Maximal Munch
- 三引号字符串
- 连字符关键字消歧 (`sub-agents`/`max-turns`)
- SourceSpan

---

## 质量指标演进

| Phase | 测试数 | 覆盖率 | flake8 |
|---|---|---|---|
| Phase 0-1 | 276 | 91.23% | 0 |
| Phase 0-2 | 535 | 89% | 0 |
| Phase 0-4 | 554 | 88% | 0 |
| Phase 0-5 | 604 | 88% | 0 |
| Phase 0-6 | 638 | 88% | 0 |
| Phase 0-7 (CLI) | 670 | 87% | 0 |
| Phase 0-7 (全部) | 811 | 86.29% | 0 |
| **Phase 0-8 (独立运行时)** | **904** | **—** | **0** |
| Phase 0-8 (stdlib 扩展) | 1,030 | — | 0 |
| Phase 0-9 (质量提升) | 1,461 | — | 0 |
| **Phase 0-9 (最终)** | **1,805** | **—** | **0** |
