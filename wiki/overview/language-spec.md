# Helen 语言规格

> 版本: v1.9 | 关键字: 89 (45 英文 + 44 中文) | Token 类型: 78 | AST 节点: 50 | Visitor 方法: 47

---

## 关键字一览 (89)

### 中文关键字 (v1.9)

Helen 支持中英双语关键字，中文关键字与英文关键字映射到相同 TokenType，解析器和解释器无需任何改动。中文标识符（变量名、函数名）也完全支持。

| 英文 | 中文 | 说明 |
|------|------|------|
| `let` | `让` | 可变变量 |
| `const` | `常量` | 常量 |
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
| `act` | `执行` | 自主执行 |
| `stream` | `流式执行` | 流式输出 |
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

### Agent 声明 (10)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `agent` | 声明 Agent | `agent Translator { ... }` |
| `description` | Agent 描述 | `description "Translate text"` |
| `model` | 指定模型 | `model "gpt-4"` |
| `tools` | Agent 工具列表 | `tools [search, calculator]` |
| `skills` | Agent 技能索引 | `skills ["web-research"]` |
| `sub-agents` | 子 Agent 声明 | `sub-agents { ... }` |
| `memory` | 持久记忆 | `memory "file://mem.json"` |
| `temperature` | 采样温度 | `temperature 0.7` |
| `max-turns` | 最大交互轮数 | `max-turns 3` |
| `prompt` | 提示词定义 | `prompt """..."""` |

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

### 变量与类型 (4)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `let` | 可变变量 | `let x = 42` |
| `const` | 不可变常量 | `const PI = 3.14` |
| `true` | 布尔真 | `let ok = true` |
| `false` | 布尔假 | `let done = false` |

### 其他 (5)

| 关键字 | 用途 | 示例 |
|---|---|---|
| `import` | 模块导入 | `import "./utils.helen"` |
| `return` | 返回值 | `return result` |
| `as` | 别名 | `import "./lib" as utils` |
| `functions` | Agent 内部函数块 | `functions { fn x() {} }` |
| `main` | Agent 主程序块 | `agent A { main { ... } }` |
| `null` | 空值 | `let x = null` |

**注意**: `main` 块仅在 `agent` 声明体内有效，不是顶层结构。顶层程序由声明序列组成（`let`/`fn`/`agent`/`import`）。

---

## Token 类型 (77)

### 字面量 (7)
`NUMBER` `STRING_DQ` `STRING_SQ` `TRIPLE_DOUBLE` `TRIPLE_SINGLE` `TRUE` `FALSE`

### 标识符与符号 (5)
`IDENTIFIER` `NULL_KW` `DOT` `COMMA` `SEMICOLON`

### 括号 (6)
`LEFT_PAREN` `RIGHT_PAREN` `LEFT_BRACE` `RIGHT_BRACE` `LEFT_BRACKET` `RIGHT_BRACKET`

### 运算符 (15)
`PLUS` `MINUS` `STAR` `SLASH` `PERCENT` `BANG` `BANG_EQUAL` `EQUAL` `EQUAL_EQUAL` `GREATER` `GREATER_EQUAL` `LESS` `LESS_EQUAL` `ARROW` `PIPE`

### 关键字 Token (43)
每个关键字对应一个 TokenType：`AGENT` `DESCRIPTION` `MODEL` `TOOLS` `SKILLS` `SUB_AGENTS` `MEMORY` `TEMPERATURE` `MAX_TURNS` `PROMPT` `LLM` `IMPORT` `LET` `CONST` `IF` `ELSE` `FOR` `WHILE` `BREAK` `CONTINUE` `RETURN` `CALL` `AWAIT` `ASYNC` `MATCH` `CASE` `BRANCH` `OPTION` `DEFAULT` `CHOOSE` `ACT` `TRY` `CATCH` `FINALLY` `ASSERT` `FN` `AS` `IN` `FUNCTIONS` `MAIN` `NULL_KW` `TRUE` `FALSE`

### 注释与文件尾 (2)
`COMMENT_LINE` `COMMENT_BLOCK` `EOF`

---

## AST 节点 (49)

### 表达式节点 (12)
`LiteralNode` `VariableNode` `BinaryOpNode` `UnaryOpNode` `GroupingNode` `CallNode` `CallArgNode` `AccessNode` `IndexNode` `ListLiteralNode` `MapLiteralNode` `MapEntryNode`

### 语句节点 (22)
`ExprStmtNode` `VarDeclNode` `DeclarationNode` `IfStmtNode` `ForStmtNode` `WhileStmtNode` `BreakStmtNode` `ContinueStmtNode` `ReturnStmtNode` `MatchStmtNode` `CaseNode` `TryStmtNode` `CatchClauseNode` `CatchAllNode` `FinallyBlockNode` `FunctionDeclNode` `FnBlockNode` `AsyncCallStmtNode` `ImportStmtNode` `TemplateRefNode` `AgentParamNode` `MainBlockNode`

### LLM 节点 (5)
`LlmActStmtNode` `LlmIfStmtNode` `LlmBranchNode` `LlmActArgNode` `PromptDefNode`

### 声明节点 (3)
`AgentDeclNode` `TypeNode` `OptionalTypeNode` `UnionTypeNode` `LiteralTypeNode`

### 程序节点 (1)
`ProgramNode`

### 基础节点 (4)
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
                    │          helen run main.helen       │
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
    │ Lexer   │──Token[77]──────▶│ Parser  │──AST[49]────────▶│  AST    │
    │         │                   │Pratt×10 │                   │Visitor×46│
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
