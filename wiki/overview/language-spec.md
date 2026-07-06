# Helen 语言规格

> 版本: v1.15 | 关键字: 97 (48.5 英文 + 48.5 中文) | Token 类型: 86 | AST 节点: 64 | Visitor 方法: 58

---

## 关键字一览 (97)

### 中文关键字 (v1.10)

Helen 支持中英双语关键字，中文关键字与英文关键字映射到相同 TokenType，解析器和解释器无需任何改动。中文标识符（变量名、函数名）也完全支持。

| 英文 | 中文 | 说明 |
|------|------|------|
| `let` | `让` | 可变变量 |
| `const` | `常量` | 常量 |
| `shared` | `共享` | 跨 agent 可见变量 (v1.10) |
| `fn` | `函数` | 函数声明 |
| `return` | `返回` | 函数返回 |
| `if` / `else` | `如果` / `否则` | 条件分支 |
| `for` / `in` | `对于` / `属于` | 循环 |
| `while` | `当` | 条件循环 |
| `break` / `continue` | `中断` / `继续` | 循环控制 |
| `match` / `case` / `default` | `匹配` / `情况` / `默认` | 模式匹配 |
| `try` / `catch` / `finally` | `尝试` / `捕获` / `最终` | 异常处理 |
| `throw` | `抛出` | 抛出异常 |
| `assert` | `断言` | 运行时断言 |
| `true` / `false` | `真` / `假` | 布尔值 |
| `null` | `空` | 空值 |
| `is` | `是` | 类型判断 |
| `agent` | `智能体` | 声明 Agent |
| `llm` | `大模型` | LLM 操作 |
| `act` | `执行` | 自主执行（支持 on_chunk/on_complete 流式回调） |
| `async` / `await` | `异步` / `等待` | 异步执行 |
| `prompt` | `提示` | 系统提示 |
| `description` | `描述` | Agent 描述 |
| `model` | `模型` | 指定模型 |
| `tools` | `工具` | 可用工具 |
| `streaming` | `流式输出` | 启用流式 |
| `temperature` | `温度` | 温度参数 |
| `max-turns` | `最大轮次` | 最大轮次 |
| `functions` | `函数区` | 函数定义区 |
| `main` | `主` | 入口 |
| `import` / `as` | `导入` / `作为` | 模块导入 |
| `protocol` / `impl` | `协议` / `实现` | 协议声明 |
| `call` | `调用` | 调用 |
| `branch` | `分支` | 分支 |
| `alias` | `别名` | 函数/变量别名 (v1.10) |
| `store` | `仓库` | Shared Store 声明 (v1.12) |
| `channel` | `通道` | Channel 声明 (v1.13) |

### Agent 声明 (11)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `agent` | 声明 Agent | `agent Translator { ... }` |
| `description` | Agent 描述 | `description "Translate text"` |
| `model` | 指定模型 | `model "gpt-4"` |
| `tools` | LLM 可见工具白名单（两层授权）| `tools = ["web_search", "my_fn"]` |
| `skills` | Agent 技能索引 | `skills ["web-research"]` |
| `sub-agents` | 子 Agent 声明 | `sub-agents { ... }` |
| `memory` | 持久记忆 | `memory "file://mem.json"` |
| `temperature` | 采样温度 | `temperature 0.7` |
| `max-turns` | 最大交互轮数 | `max-turns 3` |
| `prompt` | 提示词定义 | `prompt """..."""` |
| `context` | 上下文配置块 (v1.15) | `context { compression "graduated" }` |

### LLM 语句 (5)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `llm` | LLM 上下文关键字 | `llm if / llm act` |
| `act` | LLM 自主执行 | `llm act target "desc"` |
| `branch` | 条件分支 | `branch "urgent": ...` |

### 控制流 (15)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `if` / `else` | 条件分支 | `if x > 0 { ... } else { ... }` |
| `for` / `in` | 遍历循环 | `for item in list { ... }` |
| `while` | 条件循环 | `while condition { ... }` |
| `break` | 退出循环 | `break` |
| `continue` | 跳过本轮 | `continue` |
| `match` / `case` | 模式匹配 | `match x { case 1: ... }` |
| `default` | 默认分支 | `default: { ... }` |
| `try` / `catch` | 异常处理 | `try { ... } catch RuntimeError { ... }` |
| `finally` | 最终块 | `finally { cleanup() }` |
| `assert` | 运行时断言 | `assert x > 0, "must be positive"` |

### 函数与调用 (4)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `fn` | 函数声明 | `fn add(a, b) { return a + b }` |
| `call` | 调用 Agent | `call Translator(text)` |
| `async` | 异步调用 | `async call AgentA()` |
| `await` | 等待结果 | `await [task1, task2]` |

### 变量与类型 (5)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `let` | 可变变量 | `let x = 42` |
| `const` | 不可变常量 | `const PI = 3.14` |
| `shared` | 跨 agent 可见变量 (v1.10) | `shared let counter = 0` |
| `true` | 布尔真 | `let ok = true` |
| `false` | 布尔假 | `let done = false` |

### 其他 (5)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `import` | 模块导入 | `import "./utils.helen"` |
| `return` | 返回值 | `return result` |
| `as` | 别名 | `import "./lib" as utils` |
| `functions` | Agent 能力块（main 可用，LLM 需 tools 授权）| `functions { fn x() {} }` |
| `main` | Agent 主程序块 | `agent A { main { ... } }` |
| `null` | 空值 | `let x = null` |

**注意**: `main` 块仅在 `agent` 声明体内有效，不是顶层结构。顶层程序由声明序列组成（`let`/`fn`/`agent`/`import`）。

---

## Token 类型 (86)

### 字面量 (7)
`NUMBER` `STRING` `TRIPLE_QUOTE_STRING` `TRUE` `FALSE` `NULL_KW` `IDENTIFIER`

### 标识符与符号 (5)
`IDENTIFIER` `DOT` `DOTDOT` `COMMA` `SEMICOLON`

### 括号 (6)
`LEFT_PAREN` `RIGHT_PAREN` `LEFT_BRACE` `RIGHT_BRACE` `LEFT_BRACKET` `RIGHT_BRACKET`

### 运算符 (18)
`PLUS` `MINUS` `STAR` `SLASH` `PERCENT` `BANG` `BANG_EQUAL` `ASSIGN` `EQUAL_EQUAL` `GREATER` `GREATER_EQUAL` `LESS` `LESS_EQUAL` `ARROW` `PIPE` `PIPE_RIGHT` `QUESTION` `AT`

**v1.12**: `AT` (`@`) 用于隔离级别注解 (`@open`/`@strict`/`@sandbox`)

### 关键字 Token (46)
每个关键字对应一个 TokenType：`AGENT` `DESCRIPTION` `MODEL` `TOOLS` `STREAMING` `TEMPERATURE` `MAX_TURNS` `MEMORY` `PROMPT` `LLM` `IMPORT` `LET` `CONST` `IF` `ELSE` `FOR` `WHILE` `BREAK` `CONTINUE` `RETURN` `AWAIT` `ASYNC` `MATCH` `CASE` `BRANCH` `DEFAULT` `ACT` `TRY` `CATCH` `FINALLY` `THROW` `ASSERT` `FN` `AS` `IN` `FUNCTIONS` `MAIN` `PROTOCOL` `IMPL` `IS` `WILDCARD` `SHARED` `NULL_KW` `TRUE` `FALSE` `ALIAS` `STORE` `CHANNEL`

**v1.12**: 新增 `STORE`。**v1.13**: 新增 `CHANNEL`。**v1.14**: 删除 `STREAM`。

### 模板 (2)
`TEMPLATE_OPEN` `TEMPLATE_CLOSE`

### 特殊 (1)
`EOF`

---

## AST 节点 (63)

### 表达式节点 (14)
`LiteralNode` `VariableNode` `BinaryOpNode` `UnaryOpNode` `GroupingNode` `CallNode` `CallArgNode` `AccessNode` `IndexNode` `ListLiteralNode` `MapLiteralNode` `MapEntryNode` `PipeExprNode` `MatchExprNode`

### 语句节点 (25)
`ExprStmtNode` `VarDeclNode` `DeclarationNode` `IfStmtNode` `ForStmtNode` `ForAwaitStmtNode` `WhileStmtNode` `BreakStmtNode` `ContinueStmtNode` `ReturnStmtNode` `MatchStmtNode` `CaseNode` `TryStmtNode` `CatchClauseNode` `CatchAllNode` `FinallyBlockNode` `FunctionDeclNode` `FnBlockNode` `AsyncCallStmtNode` `ImportStmtNode` `TemplateRefNode` `AgentParamNode` `MainBlockNode` `LambdaNode` `AliasStmtNode`

### 协议/实现节点 (2)
`ProtocolDeclNode` `ImplDeclNode`

### LLM 节点 (3)
`LlmActExprNode` `LlmIfStmtNode` `LlmBranchNode`

**v1.14**: `LlmActStmtNode` 和 `LlmStreamStmtNode` 删除，统一为 `LlmActExprNode`（增加 `on_chunk`/`on_complete` 可选字段）。

### 声明节点 (5)
`AgentDeclNode` `ContextConfigNode` `SharedStoreDeclNode` `ChannelDeclNode` `TypeNode` `OptionalTypeNode` `UnionTypeNode` `LiteralTypeNode`

**v1.12**: 新增 `SharedStoreDeclNode`。**v1.13**: 新增 `ChannelDeclNode`。**v1.15**: 新增 `ContextConfigNode`。`AgentDeclNode` 增加 `isolation_level` 和 `context_config` 字段。

### 程序节点 (1)
`ProgramNode`

### 基础节点 (3)
`StatementNode` (ABC) `ExpressionNode` (ABC) `ASTNode` (ABC)

---

## 类型系统 (14)

| 类型 | 说明 | Helen 语法 |
|---|---|---|
| `AnyType` | 动态类型 | 默认推断 |
| `BoolType` | 布尔 | `bool` |
| `IntType` | 整数 | `int` |
| `FloatType` | 浮点 | `float` |
| `NumberType` | 数字基类 | — |
| `StringType` | 字符串 | `str` |
| `NullType` | 空值 | `null` |
| `OptionalType` | 可选 `T?` | `str?` |
| `ListType` | 列表 | `list<int>` |
| `MapType` | 映射 | `map<str, int>` |
| `UnionType` | 联合 `A\|B` | `int \| str` |
| `LiteralType` | 字面量 | `"hello"` |
| `AgentType` | Agent 类型 | `Agent<Translator>` |

---

## 架构总览

```
                    ┌──────────────────────────────────────┐
                    │          helen main.helen           │
                    └──────────────────┬───────────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │              CLI (M11)               │
                    │   run → Lex→Parse→Analyze→Interpret  │
                    │   check → Lex→Parse→Analyze          │
                    │   repl → 交互式循环                  │
                    └──────────────────┬───────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
    ┌────▼────┐                   ┌────▼────┐                   ┌────▼────┐
    │  M1:    │                   │  M2:    │                   │  M3:    │
    │ Lexer   │──Token[83]──────▶│ Parser  │──AST[63]────────▶│  AST    │
    │         │                   │Pratt×10 │                   │Visitor×58│
    └─────────┘                   └─────────┘                   └────┬────┘
                                                                     │
         ┌─────────────────────────────┬──────────────────────┬──────▼──────┐
         │                             │                      │             │
    ┌────▼────┐                   ┌────▼────┐           ┌─────▼─────┐ ┌────▼─────┐
    │  M4:    │                   │  M9:    │           │  M5:      │ │  M10:    │
    │Semantic │                   │ Types   │           │Interpreter│ │ Errors   │
    │Analyzer │                   │ ×14     │           │ +LLM     │ │ ×42 codes│
    └─────────┘                   └─────────┘           └─────┬─────┘ └──────────┘
                                                              │
         ┌─────────────────────────────┬──────────────────────┼──────────────┐
         │                             │                      │              │
    ┌────▼────┐                   ┌────▼────┐           ┌─────▼─────┐  ┌────▼────┐
    │  M6:    │                   │  M7:    │           │  M8:      │  │  M16:   │
    │Prompt   │                   │ Runtime │           │Import     │  │History  │
    │Builder  │                   │ABC×12   │           │Resolver   │  │Manager  │
    └─────────┘                   └─────────┘           └───────────┘  └─────────┘
```

---

## v1.10 新特性

### 1. shared let — 跨 agent 可见变量 (v1.10)

```helen
shared let counter = 0

agent Worker {
  main {
    counter += 1  // 可以访问和修改 shared let
  }
}
```

**关键字**: `shared` / `共享`

**规则**:
- 模块级 `let` 在 agent main 中**不可见**（编译时错误）
- 模块级 `const` 自动可见（只读共享）
- `shared let` 显式声明跨 agent 可见的可变变量
- 导入的 `shared let` 被正确跟踪

### 2. Agent 作用域隔离 (v1.10)

```helen
let moduleVar = "模块级"  // agent main 中不可见

agent MyAgent {
  let agentVar = "agent 级"  // agent 作用域
  
  main {
    // moduleVar  // ❌ 编译错误：模块级 let 不可见
    // agentVar   // ❌ 编译错误：agent 作用域变量不可见
    let localVar = "局部"  // ✅ 局部变量
  }
}
```

**规则**:
- `agent main {}` 在完全隔离的环境中运行
- 模块级 `let` 不可见
- 模块级 `const` 自动可见（只读）
- 使用 `shared let` 实现跨 agent 可见
- Agent main 中的闭包可以捕获局部变量

### 3. 子脚本/字段赋值 (v1.10)

```helen
let arr = [1, 2, 3]
arr[0] = 10  // ✅ 数组索引赋值

let obj = { name: "Alice", age: 30 }
obj.age = 31  // ✅ 对象字段赋值
```

### 4. 短路求值 (v1.10)

```helen
let x = false && expensiveCall()  // expensiveCall() 不会执行
let y = true || expensiveCall()   // expensiveCall() 不会执行
```

**运算符**: `&&` 和 `||` 短路求值

### 5. 返回类型注解语法 (v1.10)

```helen
// ✅ 新语法（仅支持）
fn add(a: int, b: int): int {
  return a + b
}

// ❌ 旧语法（已移除）
// fn add(a: int, b: int) -> int { ... }
```

### 6. 异常处理增强 (v1.10)

```helen
try {
  // Python stdlib 异常会被包装为 RuntimeError
  let result = int("not a number")
} catch RuntimeError as e {
  print(e.message)  // 包含原始异常信息
}
```

### 7. 异步 HTTP 支持 (v1.10)

```helen
agent MyAgent {
  main {
    // 同步方法
    llm act "task"
    
    // 异步方法 (v1.10)
    await llm act_async "task"
  }
}
```

**方法**:
- `act_async()` — 异步执行
- `act_stream_async()` — 异步流式执行
- 基于 `httpx.AsyncClient` 实现

---

## v1.11-v1.14 新特性

### v1.11: shared let 写回 + 异常层级修复

- Agent 内修改 `shared let` 后，新值自动写回全局环境
- 异常层级修复：`HelenRuntimeError` 层次更清晰

### v1.12: Agent 隔离增强 + Shared Store

#### 1. 隔离级别注解

```helen
@open agent Permissive { main { ... } }      // 可访问模块 let
@strict agent Strict { main { ... } }        // shared let 深拷贝
@sandbox agent Sandbox { main { ... } }      // 禁用外部工具，禁止 shared let
```

| 隔离级别 | 模块 let | 模块 const | shared let | 外部工具 |
|----------|----------|------------|------------|----------|
| 标准 (默认) | ❌ | ✅ | ✅ | ✅ |
| `@open` | ✅ | ✅ | ✅ | ✅ |
| `@strict` | ❌ | ✅ | ✅ (深拷贝) | ✅ |
| `@sandbox` | ❌ | ✅ | ❌ | ❌ |

#### 2. Shared Store

```helen
shared store Cache {
    data: dict = {}
    _lock_count: int = 0  // 私有字段（_前缀）

    fn get(key): any { return data[key] }
    fn set(key, value) { data[key] = value }
}
```

#### 3. 隔离关键修复

- 参数默认值和 `functions{}` 变量在 agent env 中求值
- 引用类型参数自动 `ReadOnlyView` 包装
- 闭包采用值捕获（替代环境引用捕获）
- `shared let` 限制为值类型（int/float/str/bool）
- 复合赋值（`arr[i]=x`、`obj.field=x`）隔离检查修复

### v1.13: Channel 通道 + 中文关键字补全

```helen
channel TaskQueue {
    pending: list = []
    fn enqueue(task) { pending.append(task) }
    fn dequeue(): any { return pending.shift() }
}
```

- `channel`/`通道` 声明，语法与 shared store 一致
- 运行时复用 `SharedStore` 类（线程安全）
- 语义上表示通信端点，而非共享状态容器
- 新增关键字 `store`/`仓库`、`channel`/`通道`

### v1.14: 合并 llm stream 到 llm act

**Breaking change**: `llm stream` 关键字已删除。

```helen
// 旧语法（v1.13 及以前）
llm stream "写长文" on_chunk handle_chunk

// 新语法（v1.14+）
llm act "写长文" on_chunk handle_chunk
```

- `llm act` 支持可选 `on_chunk`/`on_complete` 回调
- 无回调 → 同步执行（`act()`）
- 有回调 → 流式执行（`act_stream()`）
- 关键字数 94 → 92，`stream`/`流式执行` 不再是关键字
- `STREAM` TokenType 删除，`LlmStreamStmtNode` 删除

---

## 相关页面

- [[syntax/keywords|关键字参考]]
- [[syntax/grammar|语法规范]]
- [[compiler/ast|AST 节点定义]]
- [[interpreter/execution|执行引擎]]
- [[tutorial/05-agents|Agent 编程教程]]

---

**最后更新**: 2026-07-05  
**版本**: v1.14
