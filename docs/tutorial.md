# Helen 语言完整教程

> **Helen** — A Prompt-first Agent Programming Language
> 版本: v1.2 | 状态: Phase 0-7 全部实现 | 测试: 886 passed

---

<!-- TABLE OF CONTENTS -->

| 章节 | 主题 |
|------|------|
| [01](#教程-01-入门指南) | 安装、Hello World、REPL、代码验证、文档生成 |
| [02](#教程-02-变量与类型) | let/const、数据类型、类型注解、运算、集合操作 |
| [03](#教程-03-函数) | fn 声明、参数、返回值、递归、Agent 内部函数、作用域 |
| [04](#教程-04-控制流) | if/for/while/match、break/continue、try-catch |
| [05](#教程-05-agent-编程) | agent 声明、配置、参数、调用 |
| [06](#教程-06-llm-语句) | llm act/if/choose、对话历史 |
| [07](#教程-07-异步编程) | async call、await、并发 Agent 调用 |
| [08](#教程-08-模块与导入) | import、多格式、跨文件复用、路径安全 |
| [09](#教程-09-标准库使用) | 24 内置函数 core/string/math |
| [10](#教程-10-构建多-agent-系统) | 完整案例：智能客服系统 |

---

# 教程 01: 入门指南

> 安装 Helen、编写第一个程序、使用 REPL

## 安装

```bash
# 克隆仓库
git clone https://github.com/hahalee000000/helen.git
cd helen

# 安装
pip install -e .

# 验证
$ helen --help
Usage: helen {run, check, repl, doc}
```

## Hello, World!

创建 `hello.helen`:

```helen
main {
    print("Hello, World!")
}
```

运行:

```bash
$ helen run hello.helen
Hello, World!
```

## 代码验证

在不执行的情况下检查语法和语义:

```bash
$ helen check hello.helen
✓ hello.helen: OK
```

如果有错误:

```bash
$ helen check broken.helen
Error: [E0311] at broken.helen:2:9
  2 | let x = y
    |         ^
Undefined variable 'y'

Code: E0311 — UNDEFINED_VARIABLE

1 error found.
```

## 使用 REPL

```bash
$ helen repl
helen> print("Hello!")
Hello!
helen> let x = 42
helen> x
42
helen> let y = x * 2
helen> y
84
helen>
```

### 多行输入

当括号或引号未闭合时，REPL 自动等待更多输入:

```
helen> for i in [1, 2, 3] {
...     print(i)
... }
1
2
3
```

### 退出 REPL

按 `Ctrl+D` 或输入 `exit`。

## 生成文档

```bash
$ helen doc hello.helen
# Helen Program Documentation

## Agents

(No agents defined)

## Functions

(No functions defined)

## Built-in Functions
- print(*args) → str — 打印值
- len(value) → int — 长度
...
```

JSON 输出:

```bash
$ helen doc hello.helen --format json
{"agents": [], "functions": [], "builtins": [...]}
```

## 练习

1. 创建一个打印你名字的 Helen 程序
2. 在 REPL 中计算 `1 + 2 * 3`
3. 故意写一个有语法错误的程序，观察错误输出

---

# 教程 02: 变量与类型

> let / const / 类型注解 / 基本运算

## 变量声明

### `let` — 可变变量

```helen
let x = 42
x = 100       // ✅ 可以修改
print(x)      // 100
```

### `const` — 不可变常量

```helen
const PI = 3.14159
PI = 3        // ❌ E0346 CONST_ASSIGNMENT
```

## 数据类型

### 基本类型

```helen
let number = 42         // int
let float_num = 3.14    // float
let text = "hello"      // str
let flag = true         // bool
let nothing = null      // null
```

### 集合类型

```helen
let numbers = [1, 2, 3]                     // list<int>
let mixed = [1, "two", true]                // list<any>
let person = {"name": "Alice", "age": 30}   // map<str, any>
```

## 类型注解

```helen
let name: str = "Alice"
let age: int = 30
let score: float = 95.5
let active: bool = true
```

### 可选类型

```helen
let email: str? = null      // 可以为空
email = "alice@example.com" // ✅
email = null                // ✅

let name: str = null        // ❌ str 不接受 null
```

### 联合类型

```helen
let id: int | str = 42      // 可以是 int 或 str
id = "ABC-123"              // ✅
id = true                   // ❌
```

## 运算

### 算术运算

```helen
let a = 10 + 3      // 13
let b = 10 - 3      // 7
let c = 10 * 3      // 30
let d = 10 / 3      // 3.333...
let e = 10 % 3      // 1
```

### 比较运算

```helen
let eq = 5 == 5     // true
let ne = 5 != 3     // true
let gt = 5 > 3      // true
let ge = 5 >= 5     // true
let lt = 3 < 5      // true
let le = 5 <= 5     // true
```

### 逻辑运算

```helen
let and = true && false   // false
let or = true || false    // true
let not = !true           // false
```

### 字符串连接

```helen
let greeting = "Hello, " + "World!"    // "Hello, World!"
let message = "Score: " + 42           // "Score: 42"
```

## 列表操作

```helen
let nums = [1, 2, 3]
let first = nums[0]        // 1
let len = len(nums)        // 3
let range_nums = range(5)  // [0, 1, 2, 3, 4]
```

## 映射操作

```helen
let person = {"name": "Alice", "age": 30}
let name = person["name"]  // "Alice"
```

## 类型检查

```helen
let x = 42
let t = type(x)            // "int"
let is_int = isinstance(x, "int")    // true
let is_str = isinstance(x, "str")    // false
```

## 练习

1. 声明一个 `const` 常量保存你的出生年份
2. 创建一个包含你信息的 map (name, age, city)
3. 计算圆的面积 (PI * r * r)，r = 5
4. 使用类型注解声明一个可选字符串变量

---

# 教程 03: 函数

> fn 声明 / 参数 / 返回值 / 函数调用

## 基本函数

```helen
fn greet(name) {
    print("Hello, " + name + "!")
}

main {
    greet("Alice")    // Hello, Alice!
}
```

## 返回值

```helen
fn add(a, b) {
    return a + b
}

main {
    let result = add(3, 5)
    print(result)    // 8
}
```

### 无返回值

```helen
fn say_hello() {
    print("Hello!")
    // 隐式返回 null
}
```

## 参数类型注解

```helen
fn add(a: int, b: int): int {
    return a + b
}

fn greet(name: str): str {
    return "Hello, " + name
}
```

## 递归

```helen
fn factorial(n: int): int {
    if n <= 1 {
        return 1
    }
    return n * factorial(n - 1)
}

main {
    print(factorial(5))    // 120
}
```

## 函数作为值

```helen
fn double(x) {
    return x * 2
}

fn apply(op, value) {
    // 在 v1 中，函数通过名称引用
    // 注意：不能用 'fn' 作为参数名（它是关键字）
    print(double(value))
}
```

## Agent 内部函数

Agent 可以在 `functions` 块中定义内部函数:

```helen
agent DataProcessor {
    description "Process and analyze data"

    functions {
        fn validate(data) {
            if len(data) == 0 {
                return false
            }
            return true
        }

        fn transform(data) {
            // 数据转换逻辑
            return data
        }
    }

    prompt """
    Process the given data after validation.
    """
}
```

## 作用域

```helen
let global_x = 100

fn test() {
    let local_x = 200
    print(global_x)    // ✅ 可以访问全局变量
    print(local_x)     // ✅ 可以访问局部变量
}

main {
    print(global_x)    // ✅ 100
    test()
}
```

**注意**: `local_x` 只在 `test()` 函数内部可见，在 `main` 中无法访问。

## 练习

1. 编写一个计算斐波那契数列的递归函数
2. 编写一个函数，接受列表并返回最大值
3. 编写一个函数，判断一个字符串是否为回文

---

# 教程 04: 控制流

> if / for / while / match / try-catch

## 条件分支

### if / else

```helen
let score = 85

if (score >= 90) {
    print("A")
} else if (score >= 80) {
    print("B")
} else if (score >= 70) {
    print("C")
} else {
    print("F")
}
```

**注意**: `if` 条件必须用括号包裹：`if (cond) { ... }`。

### Truthy 规则

```helen
if 0 { print("不会执行") }        // 0 → false
if "" { print("不会执行") }       // 空字符串 → false
if [] { print("不会执行") }       // 空列表 → false
if null { print("不会执行") }     // null → false
if 1 { print("会执行") }          // 非零 → true
if "hello" { print("会执行") }    // 非空字符串 → true
if [1] { print("会执行") }        // 非空列表 → true
```

## 循环

### for ... in

```helen
for item in ["apple", "banana", "cherry"] {
    print(item)
}
// apple
// banana
// cherry
```

### 带索引遍历

```helen
let fruits = ["apple", "banana", "cherry"]
for fruit in fruits {
    print(fruit)
}
```

### range 遍历

```helen
for i in range(5) {
    print(i)    // 0, 1, 2, 3, 4
}

for i in range(1, 6) {
    print(i)    // 1, 2, 3, 4, 5
}

for i in range(0, 10, 2) {
    print(i)    // 0, 2, 4, 6, 8
}
```

### while

```helen
let count = 0
while (count < 5) {
    print(count)
    count = count + 1
}
```

**注意**: `while` 条件必须用括号包裹：`while (cond) { ... }`。使用 `count = count + 1`（赋值）而非 `let count = count + 1`（新声明），后者会创建局部变量导致死循环。

### break / continue

```helen
for i in range(10) {
    if i == 3 {
        continue    // 跳过 3
    }
    if i == 7 {
        break       // 在 7 退出
    }
    print(i)
}
// 0, 1, 2, 4, 5, 6
```

## 模式匹配

```helen
let status = "success"

match status {
    case "success" { print("OK") }
    case "error" { print("Failed") }
    default { print("Unknown") }
}
```

**注意**: `case` 和 `default` 后面使用 `{ }` 包裹代码块，不是 `:`。

### 数字匹配

```helen
let code = 404

match code {
    case 200 { print("OK") }
    case 404 { print("Not Found") }
    case 500 { print("Server Error") }
    default { print("Other") }
}
```

## 异常处理

### try / catch

```helen
try {
    let result = call RiskyAgent()
    print(result)
} catch RuntimeError err {
    print("Runtime error: " + str(err))
} catch TimeoutError err {
    print("Timeout: " + str(err))
}
```

**语法**: `catch Type varname { ... }`，类型名后直接跟变量名，不需要 `as` 关键字。

### catch-all

```helen
try {
    risky_operation()
} catch {
    // 捕获任何未匹配的错误
    print("Something went wrong")
}
```

### finally

```helen
try {
    open_file()
    process_data()
} catch RuntimeError err {
    print("Error: " + str(err))
} finally {
    close_file()    // 始终执行
}
```

### catch 顺序

```helen
// ✅ 具体类型在前，catch-all 在后
try {
    ...
} catch TypeError err {
    ...
} catch RuntimeError err {
    ...
} catch {
    ...
}

// ❌ catch-all 必须在最后
try {
    ...
} catch {
    ...
} catch TypeError err {    // E0343
    ...
}
```

## 综合示例：FizzBuzz

```helen
main {
    for i in range(1, 101) {
        if (i % 15 == 0) {
            print("FizzBuzz")
        } else if (i % 3 == 0) {
            print("Fizz")
        } else if (i % 5 == 0) {
            print("Buzz")
        } else {
            print(i)
        }
    }
}
```

**注意**: 上面的 `main { }` 需要在 `agent` 内部使用。顶层程序直接写 `for`/`if` 等语句即可。

## 练习

1. 使用 for 循环计算 1 到 100 的和
2. 使用 while 循环实现二分查找
3. 编写一个函数，使用 match 判断星期几 (1-7)
4. 编写 try-catch 处理除零错误

---

# 教程 05: Agent 编程

> agent 声明 / description / prompt / 配置

## 什么是 Agent？

在 Helen 中，Agent 是**一等公民**——不是库对象，而是语言级别的结构。

传统方式（Python):

```python
class Translator:
    def __init__(self):
        self.description = "Translate text"
        self.prompt = "You are a translator..."
```

Helen 方式:

```helen
agent Translator {
    description "Translate text"
    prompt "You are a translator..."
}
```

编译器理解 Agent 的语义，可以在 LSP 中补全、在文档中自动提取。

## 基本 Agent

```helen
agent Translator {
    description "Translate text between languages"
    prompt """
    You are a professional translator.
    Translate the given text accurately.
    """
}
```

## Agent 配置

### model — 指定模型

```helen
agent SmartTranslator {
    description "High-quality translation"
    model "gpt-4"
    prompt "Translate carefully..."
}
```

### temperature — 控制随机性

```helen
agent CreativeWriter {
    description "Write creative stories"
    temperature 0.9    // 高创造性
    prompt "Write a story..."
}

agent DataExtractor {
    description "Extract structured data"
    temperature 0.1    // 低随机性，精确输出
    prompt "Extract data..."
}
```

### max-turns — 多轮对话

```helen
agent Interviewer {
    description "Conduct an interview"
    max-turns 5    // 最多 5 轮对话
    prompt "Ask follow-up questions..."
}
```

## Agent 参数

```helen
agent Translator {
    description "Translate text"

    // 参数声明 (未来版本支持类型检查)
    // text: str — 要翻译的文本
    // target_lang: str — 目标语言

    prompt """
    Translate: {{text}}
    Target language: {{target_lang}}
    """
}

main {
    let result = call Translator("Hello", "French")
}
```

## 调用 Agent

```helen
agent Summarizer {
    description "Summarize text"
    prompt "Summarize the following:"
}

main {
    let text = "Long article content here..."
    let summary = call Summarizer(text)
    print(summary)
}
```

## 完整示例：邮件分类系统

```helen
agent EmailClassifier {
    description "Classify emails into categories"
    model "gpt-4"
    temperature 0.1
    prompt """
    Classify the email into one of:
    - urgent: Requires immediate attention
    - meeting: Calendar-related
    - informational: FYI only
    - spam: Unwanted email
    """
}

agent UrgentResponder {
    description "Draft response to urgent emails"
    prompt "Draft a professional response..."
}

agent EmailClassifier {
    description "Classify emails"
    prompt "Classify this email..."
    main {
        let email = "URGENT: Server down in production!"

        llm if "Classify this email" {
            branch "urgent" {
                print("🚨 URGENT email detected!")
                call UrgentResponder(email)
            }
            branch "meeting" {
                print("📅 Meeting request")
            }
            branch "informational" {
                print("📧 FYI email")
            }
            branch "spam" {
                print("🗑️ Spam, ignoring")
            }
            default {
                print("📬 Uncategorized")
            }
        }
    }
}
```

## 练习

1. 创建一个 Agent，描述为"判断文本情感"，测试不同输入
2. 创建一个 Agent 配置 temperature 为 0，观察输出稳定性
3. 创建一个多 Agent 系统：分类器 + 响应器 + 总结器

---

# 教程 06: LLM 语句

> llm act / llm if / llm choose 实战

## LLM 语句概述

Helen 有三个关键字级 LLM 语句：

| 语句 | 用途 | 返回值 |
|---|---|---|
| `llm act` | 让 LLM 执行任务 | 响应文本 |
| `llm if` | 让 LLM 分类路由 | 执行匹配分支 |
| `llm choose` | 让 LLM 选择选项 | 选项名称 |

## llm act

### 基本用法

```helen
agent Translator {
    description "Translate text"
    prompt "Translate to French:"
}

main {
    let text = "Hello, world!"
    let result = llm act Translator(text) "Translate to French"
    print(result)
    // Bonjour, le monde!
}
```

### 带参数

```helen
agent Analyzer {
    description "Analyze text sentiment"
    prompt "Analyze sentiment of: {{text}}"
}

main {
    let review = "This product is amazing!"
    llm act Analyzer(text=review) "Analyze sentiment"
}
```

### 返回处理

```helen
agent Summarizer {
    description "Summarize text"
    prompt "Summarize in one sentence:"
}

main {
    let article = "Long article content..."
    let summary = llm act Summarizer(article) "Summarize"
    print("Summary: " + summary)
}
```

## llm if

### 基本用法

```helen
llm if "Classify email priority" {
    branch "urgent" {
        print("🚨 URGENT — notify on-call immediately")
    }
    branch "high" {
        print("🔴 HIGH — address within 1 hour")
    }
    branch "normal" {
        print("🟢 NORMAL — handle in next sprint")
    }
    branch "low" {
        print("⚪ LOW — handle when convenient")
    }
    default {
        print("❓ Unknown priority")
    }
}
```

**注意**: `llm if` 使用 `branch` 关键字定义分支，不是 `case`。每个分支用 `{ }` 包裹代码块。

### 嵌套使用

```helen
let query = "How do I reset my password?"

llm if "Classify query type" {
    branch "question" {
        llm if "Identify question category" {
            branch "technical" {
                call TechSupport(query)
            }
            branch "billing" {
                call BillingSupport(query)
            }
            default {
                call GeneralSupport(query)
            }
        }
    }
    branch "command" {
        execute_command(query)
    }
    default {
        print("I don't understand")
    }
}
```

## llm choose

### 基本用法

```helen
llm choose "Select the best response style" {
    option "formal" {
        let style = "professional"
        print("Using formal tone")
    }
    option "casual" {
        let style = "friendly"
        print("Using casual tone")
    }
    option "humorous" {
        let style = "witty"
        print("Using humorous tone")
    }
}
```

### 与变量结合

```helen
let topic = "climate change"

llm choose "Select analysis approach" {
    option "statistical" {
        let approach = "data-driven"
    }
    option "narrative" {
        let approach = "story-based"
    }
    option "comparative" {
        let approach = "before-after"
    }
}

print("Analyzing " + topic + " with " + approach + " approach")
```

## 对比：何时使用哪个？

| 场景 | 使用 |
|---|---|
| 需要 LLM 返回文本 | `llm act` |
| 需要 LLM 做分类决策 | `llm if` |
| 需要 LLM 从选项中选择 | `llm choose` |
| 多步骤决策 | 嵌套 `llm if` |
| 需要结果变量 | `llm act` |

## 对话历史自动记录

每次 LLM 交互自动记录到对话历史：

```helen
main {
    // 自动记录: [user] "Classify email priority"
    llm if "Classify email priority" {
        branch "urgent" { print("Urgent!") }
        default { print("Other") }
    }
    // 自动记录: [assistant] "[routed to: urgent]"

    // 下次 LLM 调用会包含上面的历史作为上下文
    llm act Responder(email) "Draft response"
}
```

历史上限 **4096 tokens**，自动截断最旧消息。

## 练习

1. 创建一个 llm if 三层嵌套的分类系统
2. 使用 llm choose 让 LLM 选择算法策略
3. 使用 llm act 实现一个翻译管道
4. 观察多次 LLM 调用后的对话历史

---

# 教程 07: 异步编程

> async call / await / AggregateError / 并发 Agent 调用

## 概述

Helen 支持 `async call` 实现并发 Agent 调用，通过 `await [list]` 等待全部完成。

## 基本用法

```helen
agent Researcher {
    description "Research a topic"
    prompt "Research and summarize:"
    main {
        let topic = "AI in healthcare"
        let research_task = async call Researcher(topic)
        let data_task = async call Analyst(topic)
        let results = await [research_task, data_task]
        let research = results[0]
        let analysis = results[1]
        print("Research: " + research)
        print("Analysis: " + analysis)
    }
}

agent Analyst {
    description "Analyze data"
    prompt "Analyze the following data:"
}
```

## Task 对象

`async call` 返回 `Task` 对象：

```helen
let task = async call MyAgent(input)

// Task 方法 (未来版本支持)
// task.is_success() → bool
// task.get_result() → Any
// task.get_error() → Exception
```

## await 行为

### 全部成功

```helen
let results = await [task1, task2, task3]
// results = [result1, result2, result3]
```

### 部分失败

```helen
try {
    let results = await [task1, task2, task3]
} catch AggregateError(err) {
    // err.errors = [(index, exception), ...]
    for error_info in err.errors {
        print("Task " + str(error_info[0]) + " failed: " + str(error_info[1]))
    }
}
```

## 实际示例：多源信息聚合

```helen
agent NewsSearcher {
    description "Search latest news"
    prompt "Search for news about:"
}

agent AcademicSearcher {
    description "Search academic papers"
    prompt "Find papers about:"
}

agent SocialSearcher {
    description "Search social media"
    prompt "Find social media posts about:"
}

agent Synthesizer {
    description "Synthesize information from multiple sources"
    prompt "Synthesize the following sources into a coherent report:"
}

main {
    let topic = "quantum computing breakthroughs"

    // 并发搜索三个源
    let news_task = async call NewsSearcher(topic)
    let academic_task = async call AcademicSearcher(topic)
    let social_task = async call SocialSearcher(topic)

    // 等待全部结果
    try {
        let sources = await [news_task, academic_task, social_task]

        // 综合所有结果
        let report = call Synthesizer(sources[0] + "\n" + sources[1] + "\n" + sources[2])
        print(report)
    } catch AggregateError(err) {
        print("Some sources failed to load")
        // 仍然可以使用成功的结果
    }
}
```

## 注意事项

| 规则 | 说明 |
|---|---|
| `async` 仅修饰 `call` | `async call Agent()` ✅，`async fn x()` ❌ |
| `await` 参数必须是列表 | `await [task]` ✅，`await task` ❌ |
| v1 同步执行 | 当前版本立即执行，未来版本改为真正异步 |
| 错误聚合 | 多个失败 → `AggregateError` |

## 练习

1. 创建三个并发 Agent 调用，处理同一输入的不同方面
2. 模拟一个失败的任务，使用 try-catch 处理 AggregateError
3. 比较串行调用和 async/await 的执行顺序

---

# 教程 08: 模块与导入

> import / 多格式 / 跨文件复用 / 路径安全

## 基本导入

```helen
// utils.helen
fn double(x) {
    return x * 2
}

agent Helper {
    description "A helper agent"
    prompt "Help the user."
}

// main.helen
import "./utils.helen"

main {
    let result = double(21)    // 42
    call Helper()              // 使用导入的 Agent
}
```

## 导入别名

```helen
import "./math_utils.helen" as math

main {
    let result = math.add(1, 2)
}
```

## 多格式导入

### 导入 .json

```helen
// config.json
{
    "model": "gpt-4",
    "temperature": 0.7,
    "max_turns": 3
}

// main.helen
import "./config.json" as cfg

main {
    // cfg 包含解析后的 JSON 数据
    // (在 v1 中通过环境变量或运行时访问)
}
```

### 导入 .md

```helen
// prompt.md
You are a helpful assistant.
Always respond in a friendly tone.
Be concise but thorough.

// main.helen
import "./prompt.md" as system_prompt

main {
    // system_prompt 包含纯文本内容
}
```

## import 不执行 main

被导入文件的 `main` 块**不会**自动执行：

```helen
// lib.helen
fn utility() {
    return "useful"
}

main {
    print("This will NOT run when imported!")
}

// main.helen
import "./lib.helen"

main {
    utility()    // ✅ 可以使用函数
    // lib.helen 的 main 不会执行
}
```

## 路径安全

### 允许的导入

```helen
import "./utils.helen"          // ✅ 当前目录
import "./lib/helpers.helen"    // ✅ 子目录
import "../sibling/utils.helen" // ✅ 同级目录（在安全范围内）
```

### 拦截的导入

```helen
import "../../secrets.helen"    // ❌ 路径越界
import "/etc/passwd"             // ❌ 绝对路径
```

路径安全检查确保导入文件在项目目录内。

## 循环导入检测

```helen
// a.helen
import "./b.helen"
fn from_a() { return "A" }

// b.helen
import "./a.helen"    // 循环导入，静默跳过
fn from_b() { return "B" }

// main.helen
import "./a.helen"

main {
    from_a()    // ✅
    from_b()    // ✅ (b.helen 从 main 导入)
}
```

## 项目结构示例

```
my-project/
├── main.helen
├── agents/
│   ├── translator.helen
│   ├── summarizer.helen
│   └── classifier.helen
├── utils/
│   ├── text.helen
│   └── validation.helen
├── config.json
└── prompts/
    ├── translator.md
    └── summarizer.md
```

```helen
// main.helen
import "./agents/translator.helen"
import "./agents/summarizer.helen"
import "./agents/classifier.helen"
import "./utils/text.helen" as text_utils
import "./config.json" as config

main {
    // 使用所有导入的 Agent 和工具
}
```

## 练习

1. 创建一个 utils.helen 文件，包含常用函数
2. 在 main.helen 中导入并使用这些函数
3. 创建一个 config.json 并导入
4. 尝试循环导入，观察行为

---

# 教程 09: 标准库使用

> 24 内置函数 / core / string / math

## Core 函数 (11)

### print — 打印

```helen
print("Hello")                // Hello
print(42)                     // 42
print("Score:", 42)           // Score: 42
```

### len — 长度

```helen
len("hello")                  // 5
len([1, 2, 3])               // 3
```

### 类型转换

```helen
str(42)                       // "42"
str(3.14)                     // "3.14"
int("42")                     // 42
int(3.14)                     // 3
float("3.14")                 // 3.14
float(42)                     // 42.0
```

### 数学函数

```helen
abs(-42)                      // 42
abs(3.14)                     // 3.14
min(3, 1, 4, 1, 5)           // 1
max(3, 1, 4, 1, 5)           // 5
```

### range — 生成列表

```helen
range(5)                      // [0, 1, 2, 3, 4]
range(1, 6)                   // [1, 2, 3, 4, 5]
range(0, 10, 2)               // [0, 2, 4, 6, 8]
```

### 类型检查

```helen
type(42)                      // "int"
type("hello")                 // "str"
type(3.14)                    // "float"
type(true)                    // "bool"
type(null)                    // "null"
type([1, 2])                  // "list"

isinstance(42, "int")         // true
isinstance("hi", "str")       // true
isinstance(42, "str")         // false
```

## String 函数 (9)

```helen
// 大小写
upper("hello")                // "HELLO"
lower("HELLO")                // "hello"

// 修剪
strip("  hello  ")            // "hello"

// 分割与连接
split("a,b,c", ",")           // ["a", "b", "c"]
join("-", ["a", "b", "c"])    // "a-b-c"

// 检查
startswith("hello", "hel")    // true
endswith("hello", "lo")       // true

// 查找与替换
find("hello", "ell")          // 1
replace("hello", "l", "L")    // "heLLo"
```

## Math 函数 (4)

```helen
round(3.14159)                // 3
round(3.14159, 2)             // 3.14
round(3.5)                    // 4

sqrt(16)                      // 4.0
sqrt(2)                       // 1.4142...

floor(3.9)                    // 3
ceil(3.1)                     // 4
```

## 综合示例：文本处理管道

```helen
main {
    let text = "  Hello, World!  "

    // 清理
    let cleaned = strip(text)
    print(cleaned)                    // "Hello, World!"

    // 转换
    let upper = upper(cleaned)
    print(upper)                      // "HELLO, WORLD!"

    // 分析
    let words = split(cleaned, " ")
    print(len(words))                 // 2
    print(type(words))                // "list"

    // 检查
    if startswith(cleaned, "Hello") {
        print("Starts with Hello!")
    }

    // 替换
    let replaced = replace(cleaned, "World", "Helen")
    print(replaced)                   // "Hello, Helen!"
}
```

## LSP 补全

在 VS Code 中，输入标准库函数名时会自动补全：

```
pri...  → print
len...  → len
upp...  → upper
rou...  → round
```

## 练习

1. 使用 `range` 和 `join` 生成 "0-1-2-3-4"
2. 使用 `split` 和 `len` 统计一段文本的单词数
3. 使用 `isinstance` 编写一个类型安全的加法函数
4. 使用 `sqrt` 和 `round` 计算并四舍五入平方根

---

# 教程 10: 构建多 Agent 系统

> 完整案例：从需求到实现

## 案例：智能客服系统

### 需求

构建一个智能客服系统，能够：
1. 理解用户问题
2. 分类问题类型
3. 根据类型调用不同专业 Agent
4. 生成满意回复

## 第一步：定义 Agent

```helen
// 问题分类器
agent QuestionClassifier {
    description "Classify customer questions into categories"
    model "gpt-4"
    temperature 0.1
    prompt """
    Classify the question into one of:
    - product: Questions about products or features
    - billing: Questions about pricing, invoices, payments
    - technical: Technical issues, bugs, errors
    - account: Account management, login, settings
    - general: Everything else
    """
}

// 产品专家
agent ProductExpert {
    description "Answer product-related questions"
    model "gpt-4"
    temperature 0.3
    prompt """
    You are a product expert. Answer questions about our products
    clearly and helpfully. If unsure, say so honestly.
    """
}

// 账单专家
agent BillingExpert {
    description "Handle billing inquiries"
    model "gpt-4"
    temperature 0.1
    prompt """
    You are a billing expert. Help customers with pricing, invoices,
    and payment issues. Be precise with numbers.
    """
}

// 技术支持
agent TechSupport {
    description "Provide technical support"
    model "gpt-4"
    temperature 0.2
    prompt """
    You are a technical support engineer. Help users resolve technical
    issues step by step. Ask clarifying questions if needed.
    """
}

// 回复润色器
agent ResponsePolisher {
    description "Polish responses to be friendly and professional"
    temperature 0.5
    prompt """
    Rewrite the response to be warm, professional, and helpful.
    Keep the technical accuracy but improve the tone.
    """
}
```

## 第二步：实现路由逻辑

```helen
main {
    let customer_question = "How do I reset my password?"

    // 第一步：分类
    llm if "Classify customer question" {
        branch "product" {
            print("📦 Product question")
            let answer = call ProductExpert(customer_question)
        }
        branch "billing" {
            print("💰 Billing question")
            let answer = call BillingExpert(customer_question)
        }
        branch "technical" {
            print("🔧 Technical question")
            let answer = call TechSupport(customer_question)
        }
        branch "account" {
            print("👤 Account question")
            let answer = call TechSupport(customer_question)
        }
        default {
            print("📋 General question")
            let answer = "Thank you for your question. Let me help you."
        }
    }

    // 第三步：润色回复
    let polished = call ResponsePolisher(answer)

    // 第四步：输出
    print("\n--- Response to Customer ---")
    print(polished)
}
```

## 第三步：添加并发优化

```helen
// 优化的版本：并发查询知识库
main {
    let question = "How do I reset my password?"

    // 并发获取上下文
    let kb_task = async call KnowledgeBase(question)
    let history_task = async call HistoryLookup("password reset")

    // 先分类（串行，需要结果路由）
    llm if "Classify customer question" {
        branch "technical" {
            // 等待上下文
            let context = await [kb_task, history_task]
            let full_context = context[0] + "\n" + context[1]
            let answer = call TechSupport(question + "\nContext: " + full_context)
        }
        default {
            let answer = "I'll help you with that."
        }
    }

    let polished = call ResponsePolisher(answer)
    print(polished)
}
```

## 第四步：添加错误处理

```helen
main {
    let question = "How do I reset my password?"

    try {
        llm if "Classify customer question" {
            branch "technical" {
                let answer = call TechSupport(question)
                let polished = call ResponsePolisher(answer)
                print(polished)
            }
            default {
                print("I'll help you with that.")
            }
        }
    } catch TimeoutError err {
        print("⏱️ The service is taking too long. Please try again.")
    } catch RuntimeError err {
        print("⚠️ Something went wrong: " + str(err))
        print("A human agent will contact you shortly.")
    } catch {
        print("❌ An unexpected error occurred.")
        print("Please try again or contact support@company.com")
    }
}
```

## 项目结构

```
customer-service/
├── main.helen
├── agents/
│   ├── classifier.helen
│   ├── product_expert.helen
│   ├── billing_expert.helen
│   ├── tech_support.helen
│   └── polisher.helen
├── utils/
│   └── formatting.helen
└── config.json
```

## 运行与验证

```bash
# 验证
$ helen check customer-service/main.helen
✓ customer-service/main.helen: OK

# 运行
$ helen run customer-service/main.helen
🔧 Technical question


--- Response to Customer ---
To reset your password, please follow these steps...

# 生成文档
$ helen doc customer-service/main.helen --format markdown
```

## 总结

通过这个案例，你学会了：
1. ✅ 声明多个 Agent 及其配置
2. ✅ 使用 `llm if` 进行智能路由
3. ✅ 使用 `async call` + `await` 并发获取上下文
4. ✅ 使用 `try-catch` 处理 LLM 异常
5. ✅ 组织多文件项目结构

## 下一步

- 探索 LSP 在 IDE 中的补全和诊断功能
- 使用 `helen repl` 快速原型
- 阅读设计哲学深入了解语言理念
- 查看错误码参考排查问题
