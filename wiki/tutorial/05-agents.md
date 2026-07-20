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

## 核心设计原则：调用者决定上下文

> **"调用 agent 前先问：它需要知道什么？"**

Helen 的 agent 是**严格隔离**的——每次 agent 调用（无论是同步 `call Agent(...)` 还是 `spawn Agent(...)`）都会创建一个全新的、独立的执行环境。**Agent 不会自动继承调用者的任何变量、历史、或上下文**。

这是 Helen "显式优于隐式" 哲学的核心体现，与 Python/JS 等语言中"函数自然看到外层作用域"的行为完全不同。

### 为什么这样设计？

1. **可预测性**：agent 看到什么完全由参数决定，不会被外层状态污染
2. **可复用性**：同一个 agent 在不同调用点可以用不同上下文工作
3. **可测试性**：测试 agent 不需要构造完整的外层环境
4. **安全性**：敏感数据不会被意外泄漏给不需要的 agent

### 调用 agent 前的思考清单

每次调用 agent 之前，请明确回答：

- [ ] **这个 agent 完成任务需要哪些信息？**（输入参数）
- [ ] **这些信息是否都通过参数显式传入了？**
- [ ] **agent 是否需要访问跨 agent 共享的状态？**（如果是，用 `shared store` 或 `shared let`）
- [ ] **agent 的输出如何被调用者或其他 agent 使用？**（返回值 / Channel / SharedStore）

### ❌ 错误示例：假设上下文自动继承

```helen
let user_name = "Alice"       // 模块级变量
let user_id = 42              // 模块级变量

agent Greeter {
    main {
        // ❌ 错误：user_name 和 user_id 在 agent 内不可见
        // 编译会报错 "undefined variable"
        print("Hello " + user_name + ", your id is " + str(user_id))
    }
}
```

### ✅ 正确示例：通过参数显式传递

```helen
agent Greeter(user_name: str, user_id: int) {
    main {
        // ✅ 所有信息都通过参数进入 agent
        print("Hello " + user_name + ", your id is " + str(user_id))
    }
}

main {
    let user_name = "Alice"
    let user_id = 42
    // ✅ 调用时显式传入所需上下文
    Greeter(user_name, user_id)
}
```

### 不同场景的上下文传递方式

| 场景 | 推荐方式 | 示例 |
|------|---------|------|
| 一次性输入 | 参数传递 | `Agent(data, config)` |
| 只读配置 | `const` 模块常量 | 自动可见 |
| 跨 agent 共享可变状态 | `shared store` | `Store.field = value` |
| spawn 子 agent 的输出 | Channel 消息 | `ch.send(result)` |
| 跨进程恢复对话 | `resume_session(sid)` | 显式继承 transcript |
| LLM 看到的上下文 | agent 的 `prompt` 模板 | `{{var}}` 占位符 |

> 💡 详细示例见 `helen-programming-methodology` §5 "上下文接力模式"

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

### context {} — 上下文管理配置（v1.15+）

`context {}` 块允许为每个 agent 自定义上下文管理策略，包括压缩算法、工作记忆等。

#### 基本语法

```helen
agent SmartAssistant {
    description "Smart assistant with custom context config"
    
    context {
        compression "graduated"      // 压缩策略
        cache-aware true             // 缓存感知
        working-memory true          // 工作记忆
        working-memory-tokens 5000   // 工作记忆词元预算
    }
    
    tools ["read_file", "web_search"]
    prompt "You are a helpful assistant."
    
    main {
        return llm act "..."
    }
}
```

#### 配置选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `compression` | str | `"graduated"` | 压缩策略：`"none"` / `"graduated"` / `"traditional"` |
| `cache-aware` | bool | `true` | 启用缓存感知压缩（提高缓存命中率） |
| `working-memory` | bool | `true` | 启用工作记忆（跟踪活跃文件、决策、错误） |
| `working-memory-tokens` | int | `5000` | 工作记忆词元预算 |

#### 压缩策略详解

**1. `"none"` — 不压缩**

适合短对话或需要完整历史的场景。

```helen
context {
    compression "none"
}
```

**2. `"graduated"` — 渐进压缩（默认）**

多层渐进策略，随上下文使用率自动升级压缩强度。大多数场景用默认值即可。

```helen
context {
    compression "graduated"  // 推荐用于长对话
}
```

**3. `"traditional"` — 传统压缩**

简单的截断策略，适合快速场景。

```helen
context {
    compression "traditional"
}
```

#### 缓存感知压缩

启用 `cache-aware` 后，压缩算法会配合 LLM 提供方的 prompt cache，减少重复 token 的成本和延迟：

```helen
context {
    compression "graduated"
    cache-aware true  // 配合 provider 缓存，降低成本
}
```

#### 工作记忆

启用 `working-memory` 后，agent 会自动跟踪：

- **活跃文件**：最近读写的文件路径
- **最近决策**：assistant 的关键决策
- **待办事项**：从注释中提取的 TODO
- **错误历史**：工具调用的错误记录

```helen
context {
    working-memory true
    working-memory-tokens 5000  // 工作记忆预算
}
```

#### 中文关键字

支持中文关键字配置：

```helen
agent 智能助手 {
    描述 "智能助手"
    
    上下文 {
        压缩 "graduated"
        缓存感知 true
        工作记忆 true
        工作记忆词元 5000
    }
    
    主逻辑 {
        返回 llm act "..."
    }
}
```

#### 完整示例：高性能研究 Agent

```helen
agent Researcher(topic: str) {
    description "Research assistant with optimized context"
    
    // 优化上下文管理
    context {
        compression "graduated"      // 渐进压缩
        cache-aware true             // 缓存感知
        working-memory true          // 跟踪研究文件
        working-memory-tokens 8000   // 更大的工作记忆
    }
    
    tools ["web_search", "web_fetch", "read_file", "write_file"]
    
    prompt """
    你是研究助手。
    研究主题：{{topic}}
    
    使用工具搜索和整理信息。
    """
    
    main {
        let result = llm act "开始研究"
        return result
    }
}
```

#### 默认行为

如果不指定 `context {}`，agent 使用默认配置：

```helen
// 等同于：
agent DefaultAgent {
    context {
        compression "graduated"
        cache-aware true
        working-memory true
        working-memory-tokens 5000
    }
}
```

#### Transcript 会话记录（v1.16+）

Helen 自动保存所有对话历史。可以在 agent 中通过 stdlib 函数访问和管理会话：

```helen
agent ChatBot {
    description "Chat bot with transcript management"
    prompt "You are a helpful chat assistant."
    
    main {
        // 获取当前会话 ID
        let session_id = get_session_id()
        print("当前会话: " + session_id)
        
        // 列出所有会话
        let sessions = list_sessions()
        for s in sessions {
            print("{s.session_id}: {s.message_count} 条消息")
        }
        
        // 回放当前会话
        let messages = replay_transcript()
        for msg in messages {
            print("{msg.role}: {msg.content}")
        }
        
        // 导出会话到文件
        export_transcript("chat_log.json", "json")
        
        // 获取压缩审计（分析压缩效率）
        let audit = get_compression_audit()
        for event in audit {
            print("{event.layer}: {event.original_token_count} -> {event.compressed_token_count}")
        }
        
        // 恢复到之前的会话
        let success = resume_session("session_1783492628_d9d9c0aa")
        if success {
            print("会话已恢复")
        }
        
        return llm act "Hello!"
    }
}
```

**使用场景**：
- **会话恢复**: 使用 `resume_session(session_id)` 恢复之前的对话
- **审计追踪**: 使用 `get_compression_audit()` 分析压缩效率
- **会话导出**: 使用 `export_transcript()` 保存对话记录
- **多会话管理**: 使用 `list_sessions()` 管理多个会话

**配置**：在 `~/.helen/config.yaml` 中配置 transcript：

```yaml
transcript:
  enabled: true              # 默认启用
  backend: "jsonl"           # 或 "sqlite"
  session_dir: "~/.helen/sessions"
```

**CLI 参数**：使用 `--transcript-log` 自定义输出路径：

```bash
$ helen chat.helen --transcript-log=/tmp/my_chat.jsonl
```

**REPL 命令**：在 REPL 中使用 transcript 命令：

```
>>> :sessions              # 列出所有会话
>>> :session_id            # 显示当前会话 ID
>>> :transcript            # 显示当前 transcript
>>> :resume <session_id>   # 恢复到指定会话
```

详见 [TranscriptStore 文档](../runtime/transcript-store.md) 和 [标准库参考](10-stdlib.md#transcript-函数-6-v116)。

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

**可用内建工具（10 个）：**

| 工具 | 功能 | 参数 |
|------|------|------|
| `web_search` | 搜索网页（Bing） | `query: str` |
| `web_fetch` | 获取网页内容 | `url: str` |
| `read_file` | 读取文件 | `path: str` |
| `write_file` | 写入文件 | `path: str, content: str` |
| `patch_file` | 精确修改文件（9 种模糊匹配策略） | `path: str, old_string: str, new_string: str` |
| `shell_exec` | 执行 shell 命令 | `command: str` |
| `calculate` | 数学计算 | `expression: str` |
| `find_files` | 按 glob 模式查找文件（`**` 递归） | `path: str, pattern: str = "**/*", max_results: int = 200` |
| `search_files` | 按内容搜索文件（文本/正则） | `path: str, pattern: str, regex: bool = false, case_sensitive: bool = true, max_results: int = 100` |
| `load_skill` | 加载技能文档 | `name: str` |

> **注意**：`load_skill` 总是可用（即使不在 `tools` 列表中），用于加载技能文档。

### 文件搜索工具使用示例（v1.15+）

`find_files` 和 `search_files` 让 LLM 能够探索代码库结构：

```helen
agent CodeExplorer {
    description "Explore and understand codebases"
    tools = ["find_files", "search_files", "read_file"]
    prompt "Explore the codebase to answer the user's question."
}

// LLM 可以自主决定：
// 1. find_files("src/", "**/*.py")  → 列出所有 Python 文件
// 2. search_files("src/", "def process", regex=false)  → 搜索函数定义
// 3. read_file("src/processor.py")  → 读取相关文件
```

**`find_files` — 按模式查找文件**

```helen
// 查找所有 Python 文件
find_files("src/", "**/*.py")

// 查找所有测试文件
find_files("tests/", "**/test_*.py")

// 查找配置文件
find_files(".", "**/*.{json,yaml,toml}")
```

**`search_files` — 按内容搜索**

```helen
// 文本搜索（默认）
search_files("src/", "TODO")

// 正则搜索
search_files("src/", "def \\w+Handler", regex=true)

// 大小写不敏感
search_files("docs/", "warning", case_sensitive=false)
```

**中文别名**：stdlib 中对应函数为 `查找文件()` 和 `搜索内容()`。

## Agent 提示词结构（v1.15+）

Helen 自动把 agent 的 `description` 和 `prompt` 放到 LLM 消息的正确位置：

- **`description`** → 系统级行为规则（角色、能力边界）
- **`prompt`** → 任务级上下文（具体指示、`{{}}` 渲染后的内容）
- **`llm act "..."`** → 实际查询（用户当前的问题）

```helen
agent CodingAgent {
    description "A coding assistant"
    prompt "You are a Python expert. Help me with coding."
    tools ["read_file", "write_file"]

    main {
        llm act "How do I sort a list?"
    }
}
```

LLM 收到的消息大致是：

```
System: <自动注入的框架指令> + description ("A coding assistant")
User:   prompt ("You are a Python expert...") + llm act 查询
```

你不需要关心框架指令的具体内容——它们对所有 agent 自动生效，保证工具使用、技能加载等基础行为正确。你只需要写好 `description` 和 `prompt`。

### 深入阅读

关于如何**写好** `prompt` 和 `description`——结构布局、写作原则、反模式、Token 预算分配、缓存友好设计、中途注入机制——请参阅 [[../reference/agent-system-prompt-guide|Agent 提示词工程完全指南]]。那份指南来自对 Claude Code 系统提示词的逆向工程，是把 agent 质量从"能跑"提升到"可靠"的关键知识。

---

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
        
        fn get_config(): str {
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

## 共享状态与通信（v1.12 / v1.13）

多 Agent 系统经常需要共享状态或相互通信。Helen 提供两种机制：**shared store**（共享仓库）和 **channel**（通道）。

### Shared Store：结构化共享状态

`shared store` 用于跨 Agent 共享**可变状态**，特别是引用类型（list、dict）。

```helen
shared store TaskRegistry {
    let tasks: list = []
    let counter: int = 0
    
    fn register(task_name: str) {
        counter = counter + 1
        tasks.append(task_name)
    }
    
    fn count(): int { return counter }
    
    fn getTask(index: int): str { return tasks[index] }
}

// 所有 Agent 都能访问
agent Worker() {
    main {
        TaskRegistry.register("my-task")
        print("Total tasks: " + str(TaskRegistry.count()))
    }
}
```

**关键特性**：
- ✅ 线程安全：所有方法调用自动加锁（RLock）
- ✅ 所有 Agent 默认可见
- ✅ 支持 list、dict 等引用类型
- ❌ 不能直接访问 `_` 前缀的私有字段

**私有字段**（`_` 前缀）：

```helen
shared store BankAccount {
    let balance: int = 1000
    _transactionLog: list = []  // 私有：外部不可见
    
    fn withdraw(amount: int) {
        balance -= amount
        _transactionLog.append("withdraw: " + str(amount))
    }
    
    fn getHistory(): list {
        return _transactionLog  // 方法内可访问
    }
}

// ✅ 公开接口
BankAccount.withdraw(100)
print(BankAccount.balance)  // 输出: 900

// ❌ 私有字段
print(BankAccount._transactionLog)  // 错误！
```

### Channel：Agent 间消息通信（v1.18+）

`spawn` 返回一个 **Channel**（邮箱），用于与分生的 Agent 进行双向通信。Channel 提供 `send`/`receive`/`try_receive`/`cancel`/`close` 方法。

```helen
// Worker Agent 接收一个 Channel 参数用于回复结果
agent Worker(task: str, reply: Channel) {
    main {
        let result = "完成: " + task
        reply.send(result)
    }
}

// spawn 返回 Channel，自动注入为 Agent 的最后一个参数
let mailbox = spawn Worker("任务A")
print(mailbox.receive())  // "完成: 任务A"
```

**Channel API：**

| 方法 | 说明 |
|------|------|
| `channel.send(value)` | 发送消息到 Channel |
| `channel.receive()` | 阻塞接收消息 |
| `channel.try_receive()` | 非阻塞接收，无消息返回 null |
| `channel.cancel()` | 取消 Channel 对应的 Agent |
| `channel.close()` | 关闭 Channel |

**中文别名**：`发送()`、`接收()`、`尝试接收()`、`取消()`、`关闭()`。

#### 多通道选择：mailbox_select

当同时监听多个 Channel 时，使用 `mailbox_select` 进行多路复用：

```helen
agent Fetcher(url: str, reply: Channel) {
    main {
        let data = web_fetch(url)
        reply.send(data)
    }
}

let mb1 = spawn Fetcher("https://api.example.com/a")
let mb2 = spawn Fetcher("https://api.example.com/b")

// 等待任意一个 Channel 返回结果
let result = mailbox_select([mb1, mb2])
print("最先返回: " + result)
```

**中文别名**：`邮箱选择([mb1, mb2])`。

#### 并发模式示例

```helen
// 生产者 Agent：向 Channel 发送多条消息
agent Producer(items: list, reply: Channel) {
    main {
        for item in items {
            reply.send("处理: " + item)
        }
        reply.send("done")  // 完成信号
    }
}

// 消费者：从 Channel 接收消息
let mailbox = spawn Producer(["苹果", "香蕉", "樱桃"])
let msg = mailbox.receive()
while (msg != "done") {
    print(msg)
    msg = mailbox.receive()
}
mailbox.close()
```

### spawn 与共享状态（v1.18+）

`spawn` 可以在后台启动 Agent，通过 Channel 进行通信。多个 spawn 可以同时访问 shared store：

```helen
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
}

agent Worker(reply: Channel) {
    main {
        Counter.increment()
        reply.send("done")
    }
}

// 启动 3 个并发 Agent，共享同一个 Counter
let mb1 = spawn Worker()
let mb2 = spawn Worker()
let mb3 = spawn Worker()

// 等待所有 Agent 完成
print(mb1.receive())  // "done"
print(mb2.receive())  // "done"
print(mb3.receive())  // "done"

print(Counter.count)  // 输出: 3
```

**线程安全保证**：
- SharedStore 内部使用 RLock 保护所有字段访问
- 多个 spawn 并发调用方法时，自动序列化执行
- 主线程和 spawn 可以同时访问同一个 SharedStore
- Channel 的 `send`/`receive` 操作也是线程安全的

---

> **下一步**: [[tutorial/06-llm-statements|LLM 语句实战]]
