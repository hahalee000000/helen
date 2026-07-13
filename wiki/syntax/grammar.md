# 语法规范 (Grammar)

> 模块 M2 | `helen/core/parser.py` | 测试: `tests/parser/`

---

## 概述

Helen Parser 使用 **Pratt Parsing**（10 级优先级表）+ 递归下降，将 Token 流转换为 AST。

---

## EBNF 完整语法

### 程序与块

```ebnf
program       → declaration* main_block?
declaration   → decorator? (agent_decl | fn_decl | import_stmt | shared_store_decl)
decorator     → "@" IDENTIFIER
main_block    → "main" "{" statement* "}"
```

### Agent 声明

```ebnf
agent_decl    → "agent" IDENTIFIER "{" agent_body "}"
agent_body    → agent_setting* prompt_def? functions_block?
agent_setting → "description" string
              | "model" string
              | "tools" "[" string ("," string)* "]"
              | "sub-agents" "{" agent_param* "}"
              | "memory" string
              | "temperature" NUMBER
              | "max-turns" NUMBER
agent_param   → IDENTIFIER ":" type?
prompt_def    → "prompt" string
functions_block → "functions" "{" (var_decl | fn_decl)* "}"
var_decl      → ("let" | "const" | "shared" "let") IDENTIFIER ("=" expression)?
```

**v1.10 shared let**:
- `shared let` 声明跨 agent 可见的可变变量
- 模块级 `let` 在 agent main 中不可见（编译时错误）
- 模块级 `const` 自动可见（只读共享）

**v1.12 隔离注解**:
- `@open` / `@strict` / `@sandbox` 修饰 agent 声明
- `@open`: 可访问模块 `let`
- `@strict`: shared let 深拷贝注入
- `@sandbox`: 禁用外部工具，禁止 shared let

### Shared Store (v1.12)

```ebnf
shared_store_decl → "shared" "store" IDENTIFIER "{" store_body "}"
store_body        → (store_field | store_method)*
store_field       → var_decl
store_method      → "fn" IDENTIFIER "(" fn_params? ")" fn_body
```

**语义**:
- `shared store`: 受控的共享可变状态（跨 agent 共享引用类型）
- 运行时复用 `SharedStore` 类（RLock 线程安全）
- `_` 前缀字段/方法为私有，agent 不可直接访问
- **v1.18**: `channel X { fields }` 声明语法已删除，channel 现在通过 `Channel()` 构造函数或 `spawn` 创建

### 函数声明

```ebnf
fn_decl       → "fn" IDENTIFIER "(" fn_params? ")" fn_body
fn_params     → fn_param ("," fn_param)*
fn_param      → IDENTIFIER (":" type)?
fn_body       → "{" statement* "}"
```

### 导入

```ebnf
import_stmt   → "import" string ("as" IDENTIFIER)?
```

### 语句

```ebnf
statement     → var_decl
              | expr_stmt
              | if_stmt
              | for_stmt
              | while_stmt
              | match_stmt
              | try_stmt
              | throw_stmt
              | llm_stmt
              | call_stmt
              | return_stmt
              | break_stmt
              | continue_stmt

var_decl      → ("let" | "const" | "shared" "let") IDENTIFIER ("=" expression)?
expr_stmt     → expression
```

**v1.10 shared let**: 在顶层声明中可用，用于跨 agent 共享可变状态。

### 控制流

```ebnf
if_stmt       → "if" "(" expression ")" "{" statement* "}" ("else" ("if" expression "{" statement* "}")?)?
for_stmt      → "for" IDENTIFIER "in" expression "{" statement* "}"
while_stmt    → "while" "(" expression ")" "{" statement* "}"
break_stmt    → "break"
continue_stmt → "continue"
return_stmt   → "return" expression?
```

### 模式匹配

```ebnf
match_stmt    → "match" expression "{" case+ default? "}"
case          → "case" pattern guard? "{" statement* "}"
pattern       → expression | range_pattern | wildcard_pattern | variable_pattern | type_pattern
range_pattern → expression ".." expression
wildcard_pattern → "_"
variable_pattern → IDENTIFIER
type_pattern  → "is" IDENTIFIER IDENTIFIER?
guard         → "if" expression
default       → "default" "{" statement* "}"
```

**v1.8 模式匹配增强**：
- **通配符模式**: `case _ { }` 匹配任何值（可作为默认分支）
- **变量绑定**: `case x { }` 绑定匹配值到变量
- **类型模式**: `case is Type { }` 检查值的类型
- **类型模式带绑定**: `case is Type name { }` 检查类型并绑定到变量

### 异常处理

```ebnf
try_stmt      → "try" "{" statement* "}" (catch_clause+ catch_all? | catch_all) finally_block?
catch_clause  → "catch" type IDENTIFIER "{" statement* "}"
catch_all     → "catch" "{" statement* "}"
finally_block → "finally" "{" statement* "}"
throw_stmt    → "throw" type ("(" expression ")")? ";"?
```

### LLM 语句

```ebnf
llm_stmt      → llm_act | llm_if

llm_act       → "llm" "act" act_target? act_args? string?
                 ("on_chunk" expression)?
                 ("on_complete" expression)?
act_target    → IDENTIFIER | expression
act_args      → "(" named_arg ("," named_arg)* ")"
named_arg     → IDENTIFIER "=" expression

llm_if        → "llm" "if" expression "{" llm_branch+ "}"
llm_branch    → "branch" string "{" statement* "}"
              | "default" "{" statement* "}"
```

**v1.14 变更**: `llm stream` 已删除，`llm act` 通过可选的 `on_chunk`/`on_complete` 回调支持流式输出。无回调时为同步执行（`act()`），有回调时为流式执行（`act_stream()`）。

### 调用

```ebnf
call_stmt     → "call" IDENTIFIER "(" call_args? ")"
call_args     → expression ("," expression)*
```

### 表达式（Pratt 11 级优先级）

```ebnf
expression    → assignment

assignment    → IDENTIFIER "=" assignment | pipe
pipe          → pipe "|>" equality | equality
equality      → comparison ("==" | "!=") comparison
comparison    → term (">" | ">=" | "<" | "<=") term
term          → factor ("+" | "-") factor
factor        → unary ("*" | "/" | "%") unary
unary         → ("!" | "-") unary | call
call          → primary ("(" args ")")* ("[" expression "]")* ("." IDENTIFIER)*
primary       → NUMBER | STRING | "true" | "false" | "null"
              | IDENTIFIER | "(" expression ")"
              | list_literal | map_literal
              | spawn_expr
list_literal  → "[" (expression ("," expression)*)? "]"
map_literal   → "{" (map_entry ("," map_entry)*)? "}"
map_entry     → expression ":" expression

spawn_expr → "spawn" IDENTIFIER "(" args? ")"
```

**v1.8 管道操作符**：
- `value |> fn` 等价于 `fn(value)`
- 左结合，低优先级（优先级 2）
- 支持链式调用：`value |> fn1 |> fn2`

---

## Pratt Parsing 优先级表

| 优先级 | 运算符 | 结合性 | 示例 |
|---|---|---|---|
| 1 | `=` | Right | `x = y = 0` |
| 2 | `\|>` | Left | `value \|> fn1 \|> fn2` |
| 3 | `\|\|` | Left | `a \|\| b \|\| c` |
| 4 | `&&` | Left | `a && b && c` |
| 5 | `==` `!=` | Left | `a == b != c` |
| 6 | `>` `>=` `<` `<=` | Left | `a > b >= c` |
| 7 | `+` `-` | Left | `a + b - c` |
| 8 | `*` `/` `%` | Left | `a * b / c` |
| 9 | `!` `-` (unary) | Right | `!-x` |
| 10 | `()` `[]` `.` | Left | `f(a)[0].x` |
| 11 | `spawn` | Prefix | `spawn Agent(...)` |

---

## `llm` 上下文关键字消歧

`llm` 既是关键字，又可能作为标识符。Parser 通过 **peek 逻辑** 消歧：

```python
# peek 看到 "llm" 时，检查下一个 token
if peek() == "act":     → parse_llm_act()
elif peek() == "if":    → parse_llm_if()
else:                   → 作为标识符处理
```

---

## `spawn` 前缀处理

`spawn` 是一元前缀表达式，后接 agent 调用：

```python
if peek() == "spawn":
    consume(SPAWN)
    call = parse_call()
    return SpawnExprNode(call=call, span=...)
```

---

## Panic Mode 错误恢复

当 Parser 遇到意外 Token 时，进入 panic mode 并同步到语句边界：

```python
def _synchronize(self):
    self.advance()
    while not self.is_at_end():
        if self.previous().type == SEMICOLON:
            return
        if self.peek().type in (AGENT, FN, LET, CONST, IF, FOR, WHILE, RETURN, IMPORT, LLM):
            return
        self.advance()
```

同步点：分号 `;` 和 语句起始关键字。

---

## 测试覆盖

- ✅ Agent 声明与参数
- ✅ 函数声明与调用
- ✅ 控制流 (if/for/while/match)
- ✅ 异常处理 (try/catch/finally/throw)
- ✅ LLM 语句 (act/if)
- ✅ 并发调用 (spawn)
- ✅ 表达式优先级
- ✅ Panic mode 恢复
- ✅ 类型注解解析

### v1.10 语法更新

#### 1. 子脚本/字段赋值 (v1.10)

赋值语句的左侧现在支持索引访问和字段访问：

```helen
// 数组索引赋值
let arr = [1, 2, 3]
arr[0] = 10  // ✅ 合法

// 对象字段赋值
let obj = { name: "Alice", age: 30 }
obj.name = "Bob"  // ✅ 合法
obj["age"] = 31   // ✅ 也合法
```

**EBNF 更新**:
```ebnf
assignment → (call | IDENTIFIER) "=" assignment | pipe
```

其中 `call` 包含索引访问 (`[i]`) 和字段访问 (`.field`)。

#### 2. 短路求值 (v1.10)

`&&` 和 `||` 运算符现在支持短路求值：

```helen
// && 短路
let x = false && expensiveCall()  // expensiveCall() 不会执行
let y = true && expensiveCall()   // expensiveCall() 会执行

// || 短路
let a = true || expensiveCall()   // expensiveCall() 不会执行
let b = false || expensiveCall()  // expensiveCall() 会执行
```

**优先级表**:
- `||` 优先级 3（左结合）
- `&&` 优先级 4（左结合）
- `&&` 优先级高于 `||`

#### 3. 返回类型注解语法 (v1.10)

仅支持 `:` 语法，`->` 语法已移除：

```helen
// ✅ 正确语法
fn add(a: int, b: int): int {
  return a + b
}

// ❌ 已移除
// fn add(a: int, b: int) -> int { ... }
```

**EBNF 更新**:
```ebnf
fn_decl → "fn" IDENTIFIER "(" fn_params? ")" (":" type)? fn_body
```

### v1.12 语法更新

#### 1. 隔离级别注解 (v1.12)

Agent 声明前可添加 `@open`/`@strict`/`@sandbox` 隔离注解：

```ebnf
declaration → decorator? (agent_decl | ...)
decorator   → "@" IDENTIFIER
```

#### 2. Shared Store 声明 (v1.12)

```ebnf
shared_store_decl → "shared" "store" IDENTIFIER "{" store_body "}"
store_body        → (store_field | store_method)*
```

### v1.13 语法更新

#### 1. Channel 声明 (v1.13, **v1.18 已删除**)

```ebnf
// 已删除：
// channel_decl → "channel" IDENTIFIER "{" store_body "}"
```

v1.18 起 `channel X { fields }` 声明语法已删除。Channel 现在通过 `Channel()` 构造函数或 `spawn` 创建。

### v1.14 语法更新

#### 1. `llm stream` 删除，`llm act` 增加回调

```ebnf
llm_act → "llm" "act" act_target? act_args? string?
           ("on_chunk" expression)?
           ("on_complete" expression)?
```

`llm stream` 已删除（`STREAM` TokenType 移除），`LlmStreamStmtNode` 移除。流式功能通过 `on_chunk`/`on_complete` 回调整合到 `llm act`。

### v1.18 语法更新

#### 1. spawn 并发原语

```ebnf
spawn_expr → "spawn" IDENTIFIER "(" args? ")"
```

`spawn` 是一元前缀表达式，返回 `Channel` 类型。

#### 2. 删除 async/await/detach/channel 声明

- `async_call_stmt` 已删除
- `async_call_expr` 已删除
- `detach_stmt` 已删除
- `channel_decl` 已删除
- `for_await_stmt` 已删除
- 关键字 `async`/`await`/`detach`/`channel`（声明语法）+ 中文 `异步`/`等待`/`分离`/`通道`（声明语法）全部删除


