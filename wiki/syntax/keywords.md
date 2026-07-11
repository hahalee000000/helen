# 关键字参考

> 97 关键字 (48.5 英文 + 48.5 中文) | 按功能分类 | 另见 `@` 隔离注解运算符 (v1.12)

---

## 中文关键字 (v1.10)

Helen 支持中英双语关键字，中文关键字与英文关键字映射到相同的 TokenType，可以自由混用。

| 英文 | 中文 | 说明 |
|------|------|------|
| `let` | `设` | 可变变量（legacy: 让、定义）|
| `const` | `常量` | 常量 |
| `shared` | `共享` | 跨 agent 可见变量 (v1.10) |
| `store` | `仓库` | Shared Store 声明 (v1.12) |
| `channel` | `通道` | Channel 声明 (v1.13) |
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
| `main` | `主函` | 入口 |
| `import` / `as` | `导入` / `作为` | 模块导入 |
| `protocol` / `impl` | `协议` / `实现` | 协议声明 |
| `call` | `调用` | 调用 |
| `branch` | `分支` | 分支 |
| `alias` | `别名` | 函数/变量别名 (v1.10) |
| `context` | `上下文` | 上下文配置块 (v1.15) |
| `compression` | `压缩` | 压缩策略 (v1.15) |
| `cache-aware` | `缓存感知` | 缓存感知开关 (v1.15) |
| `working-memory` | `工作记忆` | 工作记忆开关 (v1.15) |
| `working-memory-tokens` | `工作记忆词元` | 工作记忆预算 (v1.15) |

中文标识符（变量名、函数名）也完全支持，CJK 统一表意文字均可作为标识符字符。

```helen
// 纯中文编程
函数 斐波那契(n: int): int {
    如果 n <= 1 {
        返回 n
    } 否则 {
        返回 斐波那契(n - 1) + 斐波那契(n - 2)
    }
}

设 结果 = 斐波那契(10)

// 中英混合
常量 LIMIT = 100
如果 结果 < LIMIT {
    print("OK")
}

// v1.10: 共享变量
共享 let counter = 0
```

---

## Agent 声明 (10)

### `agent`
声明一个 Agent。

```helen
agent Translator {
    description "Translate text"
    prompt "You are a translator."
}

// v1.12: 隔离级别注解
@open agent Permissive { main { ... } }      // 可访问模块 let
@strict agent Strict { main { ... } }        // shared let 深拷贝
@sandbox agent Sandbox { main { ... } }      // 禁用外部工具
```

**`@` 运算符 (v1.12)**: `@` 是单字符 Token（`TokenType.AT`），用于 agent 声明前的隔离级别注解。支持 `@open`/`@strict`/`@sandbox` 三种隔离级别。

### `description`
Agent 的人类可读描述，注入 System Prompt。

```helen
description "Translate between English and French"
```

### `model`
指定 LLM 模型。

```helen
model "gpt-4"
```

### `tools`
Agent 可用的工具列表。

```helen
tools [web_search, calculator]
```

### `sub-agents`
子 Agent 声明。

```helen
sub-agents {
    Translator: translate text
    Summarizer: summarize content
}
```

### `memory`
持久记忆配置。

```helen
memory "file://memories/translator.json"
```

### `temperature`
LLM 采样温度 (0.0-2.0)。

```helen
temperature 0.7
```

### `max-turns`
最大交互轮数。

```helen
max-turns 3
```

### `prompt`
Agent 提示词。

```helen
prompt """
You are a helpful assistant.
Follow these instructions carefully.
"""
```

---

## LLM 语句 (3)

### `llm`
LLM 上下文关键字，与 `act`/`if` 组合使用。

### `act`
让 LLM 自主执行任务（v1.14+ 支持流式回调）。

```helen
// 同步执行
llm act Translator(text) "Translate to French"

// 流式执行（v1.14+，替代旧 llm stream 语法）
fn handle_chunk(chunk) { print(chunk) }
fn handle_complete(final) { print("Done: " + final) }
llm act "Write a long essay" on_chunk handle_chunk on_complete handle_complete
```

**v1.14 变更**: `llm stream` 已删除，流式功能通过 `on_chunk`/`on_complete` 回调整合到 `llm act`。

---

## 上下文配置 (v1.15+)

### `context`

配置 agent 的上下文管理策略。

```helen
agent SmartAssistant {
    context {
        compression "graduated"      // 压缩策略
        cache-aware true             // 缓存感知
        working-memory true          // 工作记忆
        working-memory-tokens 5000   // 工作记忆预算
    }
}
```

### 配置选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `compression` | str | `"graduated"` | `"none"` / `"graduated"` / `"traditional"` |
| `cache-aware` | bool | `true` | 启用缓存感知压缩 |
| `working-memory` | bool | `true` | 启用工作记忆 |
| `working-memory-tokens` | int | `5000` | 工作记忆词元预算 |

### 中文关键字

```helen
agent 智能助手 {
    上下文 {
        压缩 "graduated"
        缓存感知 true
        工作记忆 true
        工作记忆词元 5000
    }
}
```

---

## 控制流 (16)

### `if` / `else`
条件分支。

```helen
if x > 0 {
    print("positive")
} else {
    print("non-positive")
}
```

### `for` / `in`
遍历循环。

```helen
for item in [1, 2, 3] {
    print(item)
}
```

### `while`
条件循环。

```helen
while x < 10 {
    let x = x + 1
}
```

### `break`
退出当前循环。

### `continue`
跳过当前迭代。

### `match` / `case` / `default`
模式匹配。

```helen
// 基本模式匹配
match status {
    case "ok": print("Success")
    case "error": print("Failed")
    default: print("Unknown")
}

// v1.5: 范围匹配
match score {
    case 90..100 { print("A") }
    case 80..89 { print("B") }
    default { print("F") }
}

// v1.5: 守卫条件
match x {
    case 1..100 if x == 42 { print("the answer") }
    case 1..100 { print("in range") }
    default { print("out of range") }
}

// v1.8: 通配符模式（可作为默认分支）
match value {
    case 1 { print("one") }
    case _ { print("other") }  // 匹配任何值
}

// v1.8: 变量绑定
match value {
    case n if n > 0 { print("positive: " + str(n)) }
    case n if n < 0 { print("negative: " + str(n)) }
    case _ { print("zero") }
}

// v1.8: 类型模式
match value {
    case is String { print("it's a string") }
    case is Int { print("it's an int") }
    case _ { print("unknown type") }
}

// v1.8: 类型模式带绑定
match value {
    case is String s { print("string: " + s) }
    case _ { print("not a string") }
}
```

### `try` / `catch` / `finally` / `throw`
异常处理与抛出。

```helen
// 抛出异常
throw RuntimeError("something went wrong")
throw LLMError  // 使用默认消息

// 捕获异常
try {
    risky()
} catch RuntimeError err {
    print("Error: " + err.message)
} catch LLMError err {
    print("LLM Error: " + err.message)
} catch {
    print("Unknown error")
} finally {
    cleanup()
}
```

**预定义异常类型**：
- `RuntimeError` - 运行时错误
- `LLMError` - LLM相关错误（基类）
  - `TimeoutError` - LLM调用超时
  - `ModelError` - 模型不可用或配额耗尽
- `ToolError` - 工具调用失败
- `AssertionError` - assert 语句失败 (Phase 10)
- `AnyError` - 任意错误（ catch-all 内部使用）

### `assert`
运行时断言验证。条件为 false 时抛出 `AssertionError`。

```helen
assert x > 0
assert x > 0, "x must be positive"

// 可捕获
try {
    assert false, "test"
} catch AssertionError e {
    print("Caught: " + e.message)
}
```

---

## 函数与调用 (4)

### `fn`
函数声明。

```helen
fn add(a, b) {
    return a + b
}
```

### `call`
调用 Agent。

```helen
call Translator(text)
```

### `async` / `await`
异步调用与等待。

```helen
async call AgentA(x)
let results = await [task1, task2]
```

---

## 变量与类型 (4)

### `let`
可变变量声明。

```helen
let x = 42
x = 100  // ✅ 可修改
```

### `const`
不可变常量声明。

```helen
const PI = 3.14
PI = 3   // ❌ E0346 CONST_ASSIGNMENT
```

### `shared` (v1.10)
跨 agent 可见变量声明。

```helen
shared let counter = 0

agent Worker {
  main {
    counter += 1  // ✅ 可以访问和修改 shared let
  }
}
```

**作用域规则** (v1.10):
- 模块级 `let` 在 agent main 中**不可见**（编译时错误）
- 模块级 `const` 自动可见（只读共享）
- `shared let` 显式声明跨 agent 可见的可变变量
- 导入的 `shared let` 被正确跟踪
- 导入模块的函数可访问其自身模块的 `const` 和 `shared let`（无论别名或非别名导入）

```helen
// 示例：模块级变量作用域
let moduleVar = "模块级"
const MODULE_CONST = "常量"
shared let sharedVar = "共享"

agent MyAgent {
  main {
    // moduleVar    // ❌ 编译错误：模块级 let 不可见
    MODULE_CONST   // ✅ 只读访问
    sharedVar = "新值"  // ✅ 可读写
  }
}
```

**跨模块访问** (v1.10):
```helen
// output.helen
const LEVEL = 1
shared let _use_colors = true
fn colorize(t: str): str {
    if _use_colors { return "[C]" + t }
    return t
}

// main.helen — 别名导入
import "output.helen" as output
main {
    output.LEVEL            // ✅ const 通过别名访问
    output._use_colors      // ✅ shared let 通过别名访问
    output.colorize("hi")   // ✅ 函数可见模块的 const 和 shared let
}

// main2.helen — 非别名导入
import "output.helen"
main {
    LEVEL              // ✅ const 直接可见
    _use_colors        // ✅ shared let 直接可见
    colorize("hi")     // ✅ 函数可见模块变量
}
```

### `store` (v1.12)

`shared store` 声明受控的共享可变状态。

```helen
shared store Counter {
    count: int = 0
    fn increment() { count += 1 }
    fn get(): int { return count }
}
```

- 字段和方法组成结构化状态
- 运行时线程安全（RLock）
- `_` 前缀字段为私有字段，agent 不可直接访问
- 中文关键字 `仓库`

### `channel` (v1.13)

`channel` 声明类型安全的 agent 间通信端点。

```helen
channel TaskQueue {
    pending: list = []
    fn enqueue(task) { pending.append(task) }
    fn dequeue(): any { return pending.shift() }
    fn size(): int { return len(pending) }
}
```

- 语法与 shared store 一致，运行时复用 `SharedStore` 类
- 语义上表示通信端点，而非共享状态容器
- 中文关键字 `通道`

### `true` / `false`
布尔字面量。

---

## 其他 (5)

### `import`
模块导入。

```helen
import "./utils.helen"
import "./config.json" as cfg
```

### `return`
从函数返回值。

```helen
fn double(x) {
    return x * 2
}
```

### `as`
导入别名。

```helen
import "./lib" as utils
```

### `alias` (v1.10)
函数/变量别名。为现有函数或 stdlib 函数创建额外的名字。

```helen
// 给 stdlib 函数起别名
alias len as 长度
alias print as 打印

// 给用户函数起别名
函数 greet(name: str): str { 返回 "Hello, " + name }
alias greet as 打招呼
```

中文关键字 `别名` 等价：

```helen
别名 len as 我的长度
主函 { 我的长度([1, 2, 3]) }
```

Helen 的 stdlib 内置 255 个中文别名，启动时自动加载，不需要手动 alias：

```helen
// 直接用中文 stdlib 函数名
函数 测试() {
    设 数据 = [3, 1, 4, 1, 5]
    返回 长度(排序(数据))   // 长度 = len, 排序 = sort
}
```

所有 locale 的别名表启动时全量加载，无论 locale 设置是什么。locale 配置只影响 docs/LSP/错误消息的展示语言，不影响可用的名字。

### `functions`
Agent 内部函数块。

```helen
agent MyAgent {
    functions {
        fn helper() { ... }
    }
}
```

### `main`
主程序块。

```helen
main {
    print("Hello, Helen!")
}
```

### `null`
空值字面量。

```helen
let x: str? = null
```

### `is` (v1.8)
类型模式匹配关键字，用于 `match` 语句中检查值的类型。

```helen
match value {
    case is String { print("it's a string") }
    case is Int { print("it's an int") }
    case is String s { print("string: " + s) }  // 类型检查并绑定
    case _ { print("unknown") }
}
```

支持的类型：`String`, `Int`, `Float`, `Bool`, `List`, `Map`, `Null`

---

## 运算符 (v1.8)

### `|>` (管道操作符)
将左侧值作为参数传递给右侧函数。

```helen
// 基本用法
let result = 5 |> double  // 等价于 double(5)

// 链式调用
let result = "hello" |> upper |> strip  // 等价于 strip(upper("hello"))

// 与内置函数
let len = [1, 2, 3] |> len  // 3

// 与自定义函数
fn add_one(x) { return x + 1 }
let result = 10 |> add_one  // 11
```

**优先级**：低优先级（优先级 2），左结合
