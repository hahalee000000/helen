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

**注意**：三引号字符串（`"""..."""`）会自动去除公共前导空白（auto-dedent），使得在代码中缩进的多行字符串在运行时保持整洁。例如上面的 prompt 在运行时不会包含前导空格。

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

### tools — LLM 可见的工具白名单

`tools = [...]` 是 **LLM 可见性的唯一白名单**（两层授权模型）。

**两层授权：**

- `functions {}` 块声明 agent 的**全部能力**——`main {}` 的 Helen 代码可以调用其中任意函数，但 LLM 默认看不到它们。
- `tools = [...]` 从中挑选**允许 LLM 自主决定调用**的部分。
- **不写 `tools`** 时，LLM 没有任何工具可用（除内置的 `load_skill`）。

```helen
agent Assistant {
    description "Helpful assistant"
    tools = ["web_search", "read_file"]   // LLM 可以自主调用这两个
    functions {
        fn fetch_summary(url: str): str {  // 在 functions 里声明
            let content = read_file(url)
            return summarize(content)
        }
        fn dangerous_op() { ... }          // LLM 看不到
    }
    main {
        // main 可以调用 functions 里任意函数（不受 tools 限制）
        let summary = fetch_summary("http://example.com")
        dangerous_op()                      // ✅ main 可以调
        return llm act "..."                // LLM 只能调 web_search/read_file/fetch_summary
    }
}
```

`tools` 里的名字先查 `functions {}` 块（Helen 函数），再查 Python 工具注册表（`web_search`、`read_file` 等）。同名时 Helen 函数优先。

#### tools = CONST_NAME（复用工具集）

`tools` 可以引用**模块级 const**，减少重复声明，并保持工具集**静态可审计**（安全边界清晰）：

```helen
// 项目顶部定义一次
const FILE_TOOLS = ["read_file", "write_file", "path_exists"]
const RESEARCH_TOOLS = ["web_search", "web_fetch", "read_file"]

agent Contractor {
    tools = FILE_TOOLS                // ✅ 复用 const
    ...
}

agent Researcher {
    tools = RESEARCH_TOOLS            // ✅ 复用 const
    ...
}
```

**严格校验**（编译期）：

| 写法 | 是否允许 | 原因 |
|------|---------|------|
| `tools = CONST_NAME` | ✅ | 模块级 const，静态可追踪 |
| `tools = ["...", ...]` | ✅ | 字面量列表，静态 |
| `tools = my_var` | ❌ | 可变变量，动态 |
| `tools = my_fn` | ❌ | 函数，不是列表 |
| `tools = OtherAgent` | ❌ | agent，不是列表 |
| `tools = UNKNOWN` | ❌ | 未定义 |
| 两次 `tools = ...` | ❌ | 重复声明，语义不明 |

> ⚠️ 不支持 agent 内部 const、不支持表达式拼接（如 `A + B`）——这是**安全设计**，不是缺陷。工具是 LLM 的能力边界，必须静态可审计。

**可用内建工具：**

| 工具 | 功能 | 参数 |
|------|------|------|
| `web_search` | 搜索 Wikipedia | `query: str` |
| `web_fetch` | 获取网页内容 | `url: str` |
| `read_file` | 读取文件 | `path: str` |
| `write_file` | 写入文件 | `path: str, content: str` |
| `shell_exec` | 执行 shell 命令 | `command: str` |
| `calculate` | 数学计算 | `expression: str` |

## Agent main 块

Agent 可以包含 `main` 块作为执行入口，使用 `call` 调用：

```helen
agent Translator(text: str, target: str) {
    description "Translate text"
    model "gpt-4"
    temperature 0.3
    prompt """
    Translate to {{target}}:
    {{text}}
    """
    
    functions {
        let default_format = "formal"
        const MAX_LENGTH = 1000
        
        fn validate_input(s: str): bool {
            return len(s) > 0
        }
        
        fn format_output(text: str): str {
            if default_format == "formal" {
                return text.upper()
            }
            return text
        }
    }
    
    main {
        if validate_input(text) {
            let result = llm act    // bare form：自动使用渲染后的 prompt
            return format_output(result)
        }
        return "输入为空"
    }
}

// 调用方式（推荐函数式调用）：
let translated = Translator(text="Hello", target="French")
// 函数式调用：let translated = Translator(text="Hello", target="French")
```

**functions 块中的变量定义**：

`functions {}` 块现在支持 `let` 和 `const` 声明，这些变量在 agent 的所有函数中可见：

```helen
agent MyAgent {
    description "Example agent"
    prompt "..."
    
    functions {
        let config = "default"
        const MAX_RETRIES = 3
        
        fn get_config() -> str {
            return config  // ✅ 可以访问
        }
        
        fn retry() {
            for i in range(MAX_RETRIES) {
                print("Retry " + str(i))
            }
        }
    }
}
```

**执行流程：**
1. `Translator(text="Hello", target="French")` 创建隔离 Environment
2. 绑定参数：`text="Hello"`, `target="French"`
3. 执行 `main` 块
4. `main` 中的 `llm act`（bare form）触发 LLM 调用：
   - `prompt` 模板渲染 → `system_prompt` + `user` 消息
   - 工具调用循环（如果有 `tools`）
5. 返回结果

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
    let result = Translator("Hello", "French")
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
    let summary = Summarizer(text)
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
                UrgentResponder(email)
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

> llm act / llm if 实战

## LLM 语句概述

Helen 有两个关键字级 LLM 语句：

| 语句 | 用途 | 返回值 |
|---|---|---|
| `llm act` | 让 LLM 执行任务 | 响应文本 |
| `llm if` | 让 LLM 分类路由 | 执行匹配分支或返回值 |

## llm act

### 基本用法

`llm act` 用于直接调用 LLM，传入 prompt 字符串：

```helen
main {
    let result = llm act "Translate 'Hello, world!' to French"
    print(result)
    // Bonjour, le monde!
}
```

### 在 agent 中使用

在 agent 的 `main` 块中，`llm act` 会自动使用 agent 的配置（model、temperature 等）：

```helen
agent Translator(text: str, target: str) {
    description "Translate text"
    model "qwen-plus"
    temperature 0.3
    prompt """
    Translate to {{target}}:
    {{text}}
    """

    main {
        // bare form：自动使用渲染后的 prompt
        let result = llm act
        return result
    }
}

main {
    let translated = Translator(text="Hello", target="French")
    print(translated)
}
```

### 带动态 prompt

可以在 `llm act` 后传入表达式，动态构建 prompt：

```helen
main {
    let review = "This product is amazing!"
    let result = llm act "Analyze sentiment of: " + review
    print(result)
}
```

### Bare form（在 agent 内无参数调用）

当 `llm act` 在 agent 的 `main` 块中使用时，可以省略参数。此时会自动使用 agent 的 `prompt` 模板渲染后的内容作为 user 消息：

```helen
agent Translator(text: str, target: str) {
    description "Translate text"
    temperature 0.3
    prompt """
    Translate to {{target}}:
    {{text}}
    """

    main {
        // bare form：自动使用渲染后的 prompt
        let result = llm act
        return result
    }
}

main {
    let translated = Translator(text="Hello", target="French")
    print(translated)
    // Bonjour
}
```

**Bare form 检测规则：**
- 语句结束符：`}`、`;`、EOF
- 语句关键字：`return`、`let`、`if`、`for` 等
- 换行边界：下一个 token 在不同行

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
                TechSupport(query)
            }
            branch "billing" {
                BillingSupport(query)
            }
            default {
                GeneralSupport(query)
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

### 支持表达式作为描述

`llm if` 的描述支持表达式，可以动态构建：

```helen
let text = "今天天气真好！"
let mood = llm if text + "反映的情绪" {
    branch "正面" { "happy" }
    branch "负面" { "sad" }
    default { "neutral" }
}
print("Mood: " + mood)
```

## llm stream — 流式输出

### 基本用法

`llm stream` 逐 chunk 流式输出 LLM 响应，适用于长文本生成场景：

```helen
main {
    llm stream "Write a short poem about programming"
}
```

默认行为：每个 chunk 到达时立即打印到终端（使用 `stream_print`），无需等待完整响应。

### 带回调函数

使用 `on_chunk` 指定回调函数，自定义处理每个 chunk：

```helen
fn handle_chunk(chunk) {
    stream_print("[" + chunk + "]")
}

main {
    llm stream "Explain recursion in one paragraph" on_chunk handle_chunk
}
```

使用 `on_complete` 指定流式传输完成后的回调：

```helen
fn handle_chunk(chunk) {
    print(chunk, end="")
}

fn on_done() {
    print("\n\n✅ 流式传输完成")
}

main {
    llm stream "Write a short story" on_chunk handle_chunk on_complete on_done
}
```

`on_complete` 回调在流式传输完成后调用，适合用于：
- 显示完成提示
- 记录统计信息（如总 token 数）
- 触发后续操作

### 在 agent 中使用

`llm stream` 在 agent 内自动使用 agent 的配置（model、temperature、prompt）：

```helen
agent Poet(topic: str) {
    description "Write poetry"
    temperature 0.9
    prompt """
    Write a poem about: {{topic}}
    """

    main {
        llm stream    // bare form：使用渲染后的 prompt
    }
}
```

### 动态 prompt

```helen
main {
    let topic = "the beauty of recursion"
    llm stream "Write a haiku about " + topic
}
```

### 与其他 LLM 语句对比

| 语句 | 用途 | 输出方式 |
|------|------|----------|
| `llm act` | 获取完整响应文本 | 等待完成后返回 |
| `llm if` | LLM 分类路由 | 等待完成后执行分支 |
| `llm stream` | 流式输出生成内容 | 逐 chunk 实时输出 |

## 对比：何时使用哪个？

| 场景 | 使用 |
|---|---|
| 需要 LLM 返回文本 | `llm act` |
| 需要 LLM 做分类决策 | `llm if` |
| 需要 LLM 从选项中选择并执行代码 | `llm if` + `branch` |
| 需要实时输出生成过程 | `llm stream` |
| 多步骤决策 | 嵌套 `llm if` |
| 需要结果变量 | `llm if` 或 `llm act` |

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
    llm act "Draft response for the email"
}
```

### 上下文窗口保护 (HLD 3.12)

对话历史**会自动裁剪后传给 LLM**，所以多轮 `llm act` 能看到之前的上下文。保护机制：

| 保护 | 行为 |
|---|---|
| Model-aware context window | 根据模型自动选择 context window 大小（如 qwen3.7-plus = 131072 tokens）|
| 自动裁剪 | 每次 LLM 调用前计算预算，删除最旧的非系统消息 |
| 自动压缩 | 历史超过 context window 80% 时，旧消息压缩成 `[Previous conversation summary]` |
| 工具结果上限 | 单次工具循环最多 10 个结果（`MAX_TOOL_RESULTS_PER_TURN`）|
| 上下文超限恢复 | API 返回 context-too-large 错误时，自动删除最老消息并重试 |

```helen
// 多轮对话 LLM 能看到之前的上下文
agent Chat {
    main {
        llm act "记住：我的名字是 Alice"   // 写入 history
        llm act "我叫什么名字？"           // LLM 能看到上一轮，回答 "Alice"
    }
}
```

Token 估算使用字符类型感知（CJK 字符 1.2 字符/token，拉丁字符 4 字符/token），比简单的 `len(text)//4` 准确得多。

## Function Calling（工具调用）

当 Agent 配置了 `tools` 时，`llm act` 会自动进入 function calling 循环：

```helen
agent Researcher(topic) {
    description "Research assistant"
    tools = ["web_search", "read_file"]
    main {
        return llm act "Research about: " + topic
    }
}
```

**执行流程：**

1. LLM 收到 prompt + 工具 schema
2. LLM 返回工具调用请求 → Helen 执行工具 → 结果返回 LLM
3. 循环直到 LLM 输出最终文本响应
4. 达到 `max_turns - 1` 时自动注入 nudge 提示，强制 LLM 输出最终答案

**内置工具列表：**

| 工具 | 功能 |
|------|------|
| `web_search` | Wikipedia 搜索 |
| `web_fetch` | 获取网页内容 |
| `read_file` | 读取文件 |
| `write_file` | 写入文件（覆盖） |
| `patch_file` | 精确修改文件（9 种模糊匹配策略） |
| `shell_exec` | 执行 shell 命令 |
| `calculate` | 数学计算 |

### patch_file 模糊匹配

`patch_file` 使用 `old_string` → `new_string` 模式精确修改文件，内置 9 种匹配策略处理 LLM 生成代码的常见差异：

```helen
// 修改文件中的特定函数
llm act "Read /tmp/main.py and change the function name from 'foo' to 'bar'"
```

匹配策略（按优先级）：
1. **Exact** — 精确字符串匹配
2. **Line-trimmed** — 行首尾空格差异
3. **Whitespace-normalized** — 多个空格/tab 归一化
4. **Indentation-flexible** — 缩进完全忽略
5. **Escape-normalized** — `\n` `\t` 转义差异
6. **Trimmed-boundary** — 首尾行空白修剪
7. **Unicode-normalized** — 智能引号、破折号等
8. **Block-anchor** — SequenceMatcher 相似度 (50%/70%)
9. **Context-aware** — 逐行相似度 (80% 阈值，50% 行匹配)

## Agent prompt 与 system_prompt

Agent 的 `prompt` 字段在 `llm act` 时作为 **system_prompt** 注入 LLM 调用：

```helen
agent Translator(text) {
    description "Professional translator"
    prompt """
    Translate the following text to {{target}}:
    {{text}}
    """
    main {
        // prompt 渲染后 → system_prompt ({"role": "system"})
        return llm act "Please translate accurately"
        // → user 消息 ({"role": "user"})
    }
}
```

**消息结构：**
```json
[
  {"role": "system", "content": "<description>\n<skills>\n<rendered prompt>"},
  {"role": "user", "content": "llm act 的表达式值"}
]
```

## 练习

1. 创建一个 llm if 三层嵌套的分类系统
2. 使用 llm if 让 LLM 选择算法策略并返回结果
3. 使用 llm act 实现一个翻译管道
4. 观察多次 LLM 调用后的对话历史

---

# 教程 07: 异步编程

> async / await / AggregateError / 并发 Agent 调用

## 概述

Helen 支持 `async` 启动并发 Agent 调用，通过 `await [list]` 等待全部完成。
`async Agent(...)` 是表达式，返回 `Task` 对象，可存入变量。

**真正的异步并发**：使用纯 `asyncio` 单线程并发，LLM 调用非阻塞执行，内存开销接近零。

## 基本用法

```helen
agent Researcher(topic: str) {
    description "Research a topic"
    prompt "Research and summarize:"
    main {
        return "Research result for: " + topic
    }
}

agent Analyst(topic: str) {
    description "Analyze data"
    prompt "Analyze the following data:"
    main {
        return "Analysis result for: " + topic
    }
}

main {
    let topic = "AI in healthcare"

    // 启动两个并发任务
    let research_task = async Researcher(topic)
    let data_task = async Analyst(topic)

    // 等待全部完成
    let results = await [research_task, data_task]
    let research = results[0]
    let analysis = results[1]
    print("Research: " + research)
    print("Analysis: " + analysis)
}
```

## 两种 async 形式

### 1. 表达式形式（延迟执行）

```helen
let task = async MyAgent(input)
// 创建 pending Task，不立即执行
// 在 await 时并发执行
```

**特点**：
- 返回 `Task.pending` 对象
- 延迟到 `await` 时执行
- 多个 pending Task 在 `await` 时并发执行

### 2. 语句形式（立即执行）

```helen
async MyAgent(input)
// 立即执行，返回 Task.completed
```

**特点**：
- 立即同步执行
- 返回 `Task.completed` 或 `Task.failed`
- 适用于不需要并发的场景

## Task 对象

`async Agent(...)` 返回 `Task` 对象，可存入变量：

```helen
let task = async MyAgent(input)
// task 是 Task 对象，包含结果或异常
```

`await` 支持列表和单个 Task：

```helen
// 列表形式：返回结果列表
let results = await [task1, task2, task3]

// 单个 Task 放在列表中
let result = await [task]
let value = result[0]
```

## await 行为

### 全部成功

```helen
let results = await [task1, task2, task3]
// results = [result1, result2, result3]
```

### 部分失败

当多个任务失败时，`await` 抛出 `AggregateError`：

```helen
try {
    let results = await [task1, task2, task3]
} catch AggregateError err {
    print("Multiple tasks failed: " + err.message)
    // err.errors 包含所有失败的异常列表
    print(err.errors)
}
```

## 实际示例：多源信息聚合

```helen
agent NewsSearcher(topic: str) {
    description "Search latest news"
    prompt "Search for news about:"
    main {
        return "News about " + topic
    }
}

agent AcademicSearcher(topic: str) {
    description "Search academic papers"
    prompt "Find papers about:"
    main {
        return "Papers about " + topic
    }
}

agent SocialSearcher(topic: str) {
    description "Search social media"
    prompt "Find social media posts about:"
    main {
        return "Social posts about " + topic
    }
}

main {
    let topic = "quantum computing breakthroughs"

    // 并发搜索三个源
    let news_task = async NewsSearcher(topic)
    let academic_task = async AcademicSearcher(topic)
    let social_task = async SocialSearcher(topic)

    // 等待全部结果
    try {
        let sources = await [news_task, academic_task, social_task]
        print("News: " + sources[0])
        print("Academic: " + sources[1])
        print("Social: " + sources[2])
    } catch AggregateError err {
        print("Some sources failed: " + err.message)
    }
}
```

## 普通函数异步调用

`async` 也可用于普通函数：

```helen
fn compute(x: num) {
    return x * x
}

fn cube(x: num) {
    return x * x * x
}

main {
    let t1 = async compute(3)
    let t2 = async cube(2)
    let results = await [t1, t2]
    print(results[0] + results[1])  // 9 + 8 = 17
}
```

## 性能特性

**真正的异步并发**：使用纯 `asyncio` 单线程并发

- **LLM 调用**：通过 `asyncio` 非阻塞执行
- **内存开销**：接近零（无额外线程）
- **并发效率**：3 个 1 秒的 LLM 调用 → ~1 秒完成（并发）

**对比传统线程池**：
- 线程池：3 个线程 × 8MB = 24MB
- asyncio：0 个线程 = ~0MB
- **内存节省**：100%

## 流式迭代（for await）

Helen 支持 `for await` 语法异步迭代流式响应。Agent 声明 `streaming true` 后，调用返回 `StreamingResponse` 对象，可在 `for await` 中逐 chunk 处理：

```helen
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}

main {
    let response = async Streamer("the history of computing")
    for await chunk in response {
        stream_print(chunk)
    }
}
```

### 流式过滤与转换

`for await` 支持在循环体中对 chunk 进行自定义处理：

```helen
main {
    let response = async Streamer("long essay")
    
    // 过滤：只处理长 chunk
    for await chunk in response {
        if len(chunk) > 10 {
            stream_print(chunk)
        }
    }
}
```

### 流式聚合

```helen
main {
    let response = async Streamer("essay")
    let total_length = 0
    for await chunk in response {
        total_length = total_length + len(chunk)
    }
    print("Total length: " + total_length)
}
```

`for await` 适用于：
- 流式 LLM 响应（`streaming true` agent）
- 异步数据源
- 大文件逐行处理

**注意**：`for await` 只能在 `async` 上下文中使用。Agent 必须声明 `streaming true` 才能返回可迭代的流式响应。

## 注意事项

| 规则 | 说明 |
|---|---|
| `async` 可用于表达式 | `let task = async Agent()` ✅ |
| `async` 也可作为语句 | `async Agent()` ✅（立即执行） |
| `await` 参数必须是列表 | `await [task]` ✅，`await task` ❌ |
| 真正异步并发 | LLM 调用通过 asyncio 非阻塞执行 |
| 错误聚合 | 多个失败 → `AggregateError`（可被 try-catch 捕获） |
| 环境隔离 | 每个 Task 有独立的环境快照 |

## 练习

1. 创建三个并发 Agent 调用，处理同一输入的不同方面
2. 模拟一个失败的任务，使用 try-catch 处理 AggregateError
3. 比较串行调用和 async/await 的执行时间
4. 尝试用 `async` 调用普通函数，观察并发效果

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
    Helper()              // 使用导入的 Agent
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

# 教程 09: Python FFI

> 导入 Python 库 / 调用 Python 函数 / 类型自动转换

## 概述

Helen 支持通过 Python FFI（外部函数接口）直接导入和使用 Python 库。这让 Helen 可以访问 Python 的整个生态系统（40 万+ 包），包括数值计算、网络请求、数据处理等。

**核心特性：**
- ✅ 使用 `import` 语法导入 Python 模块
- ✅ 自动类型转换（Helen ↔ Python）
- ✅ 调用 Python 函数、访问属性和常量
- ✅ 支持嵌套模块（如 `os.path`）
- ✅ 复杂对象自动包装

## 基本用法

### 导入 Python 模块

```helen
import "math" as math
import "json" as json
import "os.path" as path
```

**语法规则：**
- 无文件扩展名 → Python 模块
- `.py` 扩展名 → Python 模块
- `.helen` → Helen 文件
- `.json`/`.md`/`.yaml` → 数据文件

### 调用 Python 函数

```helen
import "math" as math

main {
    let sqrt_result = math.sqrt(16)
    print(sqrt_result)    // 4.0
    
    let power = math.pow(2, 10)
    print(power)          // 1024.0
}
```

### 访问 Python 常量

```helen
import "math" as math

main {
    let pi = math.pi
    print(pi)             // 3.141592653589793
    
    let e = math.e
    print(e)              // 2.718281828459045
}
```

## 类型转换

### Helen → Python（自动）

| Helen 类型 | Python 类型 |
|-----------|------------|
| `int` | `int` |
| `float` | `float` |
| `str` | `str` |
| `bool` | `bool` |
| `null` | `None` |
| `list` | `list`（递归转换） |
| `map` | `dict`（递归转换） |

### Python → Helen（自动）

| Python 类型 | Helen 类型 |
|------------|-----------|
| `int` | `int` |
| `float` | `float` |
| `str` | `str` |
| `bool` | `bool` |
| `None` | `null` |
| `list` | `list`（递归转换） |
| `dict` | `map`（递归转换） |
| `tuple` | `list` |
| 复杂对象 | 包装为 `PythonObject` |

### 示例：JSON 处理

```helen
import "json" as json

main {
    // Helen map → Python dict → JSON string
    let data = {"name": "Alice", "age": 30, "active": true}
    let json_str = json.dumps(data)
    print(json_str)
    // {"name": "Alice", "age": 30, "active": true}
    
    // JSON string → Python dict → Helen map
    let parsed = json.loads(json_str)
    print(parsed["name"])    // Alice
}
```

## 嵌套模块

支持导入嵌套模块（如 `os.path`）：

```helen
import "os.path" as path

main {
    let joined = path.join("home", "user", "docs")
    print(joined)    // home/user/docs
    
    let ext = path.splitext("file.txt")
    print(ext)       // ["file", ".txt"]
}
```

## 实际示例

### 示例 1：数学计算

```helen
import "math" as math

main {
    // 三角函数
    let angle = math.pi / 4
    let sin_val = math.sin(angle)
    let cos_val = math.cos(angle)
    print("sin(π/4) = " + str(sin_val))
    print("cos(π/4) = " + str(cos_val))
    
    // 对数
    let log_val = math.log(100, 10)
    print("log₁₀(100) = " + str(log_val))
    
    // 取整
    print(math.floor(3.7))    // 3
    print(math.ceil(3.2))     // 4
}
```

### 示例 2：文件路径操作

```helen
import "os.path" as path

main {
    let filepath = "/home/user/documents/report.txt"
    
    // 提取文件名
    let basename = path.basename(filepath)
    print(basename)    // report.txt
    
    // 提取目录
    let dirname = path.dirname(filepath)
    print(dirname)     // /home/user/documents
    
    // 分离扩展名
    let parts = path.splitext(filepath)
    print(parts[0])    // /home/user/documents/report
    print(parts[1])    // .txt
}
```

### 示例 3：数据处理

```helen
import "json" as json

main {
    // 创建数据
    let users = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35}
    ]
    
    // 序列化为 JSON
    let json_data = json.dumps(users)
    print(json_data)
    
    // 解析 JSON
    let parsed = json.loads(json_data)
    for user in parsed {
        print(user["name"] + " is " + str(user["age"]) + " years old")
    }
}
```

### 示例 4：在 Agent 中使用 Python 库

```helen
import "math" as math

agent DataAnalyzer(data: list) {
    description "Analyze numerical data"
    prompt """
    Analyze the following data: {{data}}
    """
    
    functions {
        fn calculate_stats() -> map {
            let n = len(data)
            let sum = 0
            for value in data {
                sum = sum + value
            }
            let mean = sum / n
            
            // 使用 Python 的 math.sqrt
            let variance = 0
            for value in data {
                let diff = value - mean
                variance = variance + diff * diff
            }
            variance = variance / n
            let std_dev = math.sqrt(variance)
            
            return {
                "mean": mean,
                "std_dev": std_dev,
                "min": min(data),
                "max": max(data)
            }
        }
    }
    
    main {
        let stats = calculate_stats()
        return "Mean: " + str(stats["mean"]) + 
               ", Std Dev: " + str(stats["std_dev"])
    }
}

main {
    let data = [10, 20, 30, 40, 50]
    let analyzer = DataAnalyzer(data)
    let result = analyzer()
    print(result)
}
```

## 错误处理

### 导入不存在的模块

```helen
import "nonexistent_module" as bad

main {
    // 运行时错误：Cannot import Python module 'nonexistent_module'
}
```

### 访问不存在的属性

```helen
import "math" as math

main {
    let value = math.nonexistent_function()
    // 运行时错误：'math' has no property 'nonexistent_function'
}
```

### 使用 try-catch 处理

```helen
import "math" as math

main {
    try {
        let result = math.sqrt(-1)
        print(result)
    } catch RuntimeError err {
        print("Error: " + err.message)
    }
}
```

### Agent 调用失败 — AgentError

Agent 调用失败时抛出 `AgentError`，携带 agent 名称、调用参数和原始异常：

```helen
agent Contractor(req: str, dir: str) {
    main {
        // 如果 LLM 调用失败，或内部逻辑抛出异常，
        // 都会被包装为 AgentError 抛给调用方
        ...
    }
}

main {
    try {
        let result = Contractor("build auth module", "/tmp/project")
        // 这里 result 一定是成功值
    } catch AgentError err {
        // err.message    — "Agent 'Contractor' failed: ..."
        // err.agent_name — "Contractor"
        // err.agent_args — {"req": "build auth module", "dir": "/tmp/project"}
        // err.cause      — 底层异常
        error("契约设计失败: " + err.message)
    }
}
```

**继承关系**：`AgentError` 继承 `LLMError`，因此 `catch LLMError` 能同时捕获 LLM 直调和 agent 调用的失败。

**嵌套 agent 调用**：如果 agent A 调用 agent B，B 失败抛出的 `AgentError` 会被 A 透传（不双层包装），保留最内层的完整上下文。

```helen
try {
    Planner("design system")   // 内部调用 Contractor 失败
} catch AgentError err {
    // err.agent_name 是失败的最内层 agent 名称
    print(err.agent_name + " failed: " + err.message)
}
```

## 性能注意事项

- **类型转换**：简单类型（int/float/str）转换开销极低
- **复杂对象**：大型 list/dict 转换有一定开销，建议批量处理
- **函数调用**：每次调用都有跨语言开销，避免在紧密循环中频繁调用

## 与 Helen 原生功能的对比

| 功能 | Helen 原生 | Python FFI |
|------|-----------|-----------|
| 字符串处理 | ✅ 36 个 string 函数 | ✅ 可用 Python re 等 |
| 数学计算 | ✅ 15 个 math 函数 | ✅ 可用 numpy/scipy |
| 文件操作 | ✅ 16 个 file 函数 | ✅ 可用 os/pathlib |
| 网络请求 | ✅ 9 个 network 函数 | ✅ 可用 requests（高级场景） |
| 数据处理 | ✅ 25 个 data 函数（JSON/CSV/HTML/XML） | ✅ 可用 pandas（大数据集） |
| 机器学习 | ❌ 无 | ✅ 可用 torch/tensorflow |

**建议**：优先使用 Helen 原生功能（185 个内置函数覆盖常见需求），需要高级功能（如大数据处理、机器学习）时使用 Python FFI。

## 练习

1. 导入 `math` 模块，计算圆的面积（半径 = 5）
2. 导入 `json` 模块，将 map 转换为 JSON 字符串并解析回来
3. 导入 `os.path` 模块，提取文件路径的目录和文件名
4. 创建一个 Agent，使用 Python 的 `math` 模块进行复杂计算


---

## v1.10 Agent 作用域隔离

### 概述

v1.10 引入了 **Agent 作用域隔离**，`agent main {}` 在完全隔离的环境中运行，模块级变量的可见性受到严格控制。

### 可见性规则

| 变量类型 | 在 agent main 中可见？ | 可修改？ | 说明 |
|---------|---------------------|---------|------|
| 模块级 `let` | ❌ 不可见 | - | 编译时错误 |
| 模块级 `const` | ✅ 可见 | ❌ 只读 | 自动可见 |
| `shared let` | ✅ 可见 | ✅ 可读写 | 显式声明 |
| agent 局部变量 | ✅ 可见 | ✅ 可读写 | agent 作用域 |
| main 局部变量 | ✅ 可见 | ✅ 可读写 | main 作用域 |

### 示例

```helen
// 模块级变量
let moduleVar = "模块级"      // ❌ agent main 中不可见
const MODULE_CONST = "常量"   // ✅ 只读可见
shared let sharedVar = 0      // ✅ 可读写

agent MyAgent {
  main {
    // moduleVar              // ❌ E0350 SCOPE_VIOLATION
    let x = MODULE_CONST      // ✅ "常量"（只读）
    sharedVar += 1            // ✅ 1（可修改）
    
    let localVar = "局部"     // ✅ main 作用域
    print(localVar)
  }
}
```

### 为什么需要作用域隔离？

**问题**: 在没有隔离的情况下，agent 可以随意访问和修改模块级变量，导致：

1. **难以追踪的副作用**: agent 修改了全局状态，其他地方难以发现
2. **并发问题**: 多个 agent 同时修改同一个变量
3. **测试困难**: agent 的行为依赖于外部状态

**解决方案**: 强制使用 `shared let` 显式声明共享变量

```helen
// ❌ 旧方式：隐式共享
let counter = 0
agent Worker {
  main {
    counter += 1  // 难以追踪谁修改了 counter
  }
}

// ✅ 新方式：显式共享
shared let counter = 0
agent Worker {
  main {
    counter += 1  // 明确知道这是共享状态
  }
}
```

### shared let 最佳实践

#### 1. 命名约定

```helen
// 使用 SHARED_ 前缀表示共享变量
shared let SHARED_COUNTER = 0
shared let SHARED_CONFIG = { "debug": true }
```

#### 2. 线程安全

多个 agent 同时修改 shared let 时需要小心：

```helen
shared let counter = 0

agent Worker {
  main {
    // 简单递增是安全的（GIL 保护）
    counter += 1
  }
}

// 复杂操作需要额外同步
agent SafeWorker {
  main {
    // 读取-修改-写入可能不安全
    let temp = counter
    // ... 复杂计算 ...
    counter = temp + 1
  }
}
```

#### 3. 最小化共享状态

```helen
// ❌ 共享过多状态
shared let user_data = {}
shared let session_id = ""
shared let config = {}

// ✅ 只共享必要的状态
shared let SHARED_COUNTER = 0
// 其他状态通过参数传递
```

### 闭包捕获

Agent main 中的闭包可以捕获局部变量：

```helen
agent MyAgent {
  main {
    let localVar = "局部"
    
    fn closure() {
      print(localVar)  // ✅ 可以捕获局部变量
    }
    
    closure()
  }
}
```

### 错误示例

```helen
let moduleVar = "模块级"

agent MyAgent {
  main {
    // ❌ 错误：模块级 let 不可见
    print(moduleVar)  // E0350 SCOPE_VIOLATION
  }
}

// ✅ 修正：使用 shared let
shared let moduleVar = "模块级"

agent MyAgent {
  main {
    print(moduleVar)  // ✅ 可以访问
  }
}
```

---

## v1.10 shared let 完整示例

### 计数器示例

```helen
// 共享计数器
shared let SHARED_COUNTER = 0

agent Counter {
  main {
    SHARED_COUNTER += 1
    print("Count: " + str(SHARED_COUNTER))
  }
}

// 主程序
main {
  async call Counter()
  async call Counter()
  async call Counter()
  
  // 等待所有 agent 完成
  // SHARED_COUNTER 现在是 3
}
```

### 配置共享示例

```helen
// 共享配置
shared let SHARED_CONFIG = {
  "max_retries": 3,
  "timeout": 5000,
  "debug": true
}

agent Worker {
  main {
    let retries = SHARED_CONFIG["max_retries"]
    let timeout = SHARED_CONFIG["timeout"]
    
    // 使用配置执行任务
    print("Retries: " + str(retries))
    print("Timeout: " + str(timeout))
  }
}
```

### 状态聚合示例

```helen
// 共享结果收集器
shared let SHARED_RESULTS = []

agent DataProcessor {
  main {
    // 处理数据
    let result = process_data()
    
    // 添加到共享列表
    SHARED_RESULTS.push(result)
  }
}

main {
  // 并发处理多个数据源
  async call DataProcessor()
  async call DataProcessor()
  async call DataProcessor()
  
  // SHARED_RESULTS 现在包含所有结果
  print("Total results: " + str(len(SHARED_RESULTS)))
}
```

---

**最后更新**: 2026-07-01  
**版本**: v1.10
