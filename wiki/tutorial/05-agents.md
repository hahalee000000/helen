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
        working-memory-tokens 5000   // 工作记忆令牌预算
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
| `working-memory-tokens` | int | `5000` | 工作记忆令牌预算 |

#### 压缩策略详解

**1. `"none"` — 不压缩**

适合短对话或需要完整历史的场景。

```helen
context {
    compression "none"
}
```

**2. `"graduated"` — 渐进压缩（默认）**

五层渐进策略，自动根据上下文使用率应用：

| 层级 | 使用率阈值 | 策略 | 说明 |
|------|-----------|------|------|
| Layer 1 | 60% | Budget Reduction | 替换大工具输出为引用指针 |
| Layer 2 | 70% | Snip | 丢弃过时轮次 |
| Layer 3 | 80% | Microcompact | 清除旧工具结果，保留决策 |
| Layer 4 | 90% | Context Collapse | 归档并投射折叠视图 |
| Layer 5 | 95% | Auto-Compact | LLM 语义压缩 |

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

启用 `cache-aware` 后，压缩算法会考虑 prompt cache，提高缓存命中率：

- **稳定前缀**：保留前 30% 消息不变（缓存友好区）
- **批量阈值**：使用率达到 75% 才触发压缩
- **仅后缀修改**：只在缓存区域外进行修改

```helen
context {
    compression "graduated"
    cache-aware true  // 提高缓存命中率 70-80%
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
        工作记忆令牌 5000
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

#### 三通道上下文

启用工作记忆后，LLM 看到的上下文分为三个通道：

1. **系统指令（15%）**：框架指令、语言规范、agent 描述
2. **工作记忆（50%）**：活跃文件、最近决策、待办事项、错误历史
3. **对话历史（35%）**：压缩后的对话消息

这种结构确保 LLM 始终了解当前上下文，同时保持历史连贯性。

#### Transcript 会话记录（v1.16+）

Helen v1.16 引入了 TranscriptStore，自动保存所有对话历史。可以在 agent 中通过 stdlib 函数访问和管理会话：

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
  max_memory_items: 1000     # LRU 缓存大小
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

## Agent 系统提示词架构（v1.15+）

Helen v1.15 引入了清晰的 System/User 角色分离，使 agent 的提示词架构符合 LLM 最佳实践。

### System Prompt（行为规则层）

System prompt 自动注入以下内容，定义 agent 的行为规则和能力边界：

```
1. Framework Instructions (P0+P1 框架指令)
   - Tool Use (CRITICAL): MUST use tools, not describe
   - Skills (CRITICAL): MUST load relevant skills
   - Parallel Tool Calls: batch independent calls
   - Completion Criteria: working artifact, not description
   - Memory Management: save durable facts, skip trivial

2. Helen Language Conventions (语言规范)
   - Core Principles (agent-centric design)
   - Skill-Driven Development (load skills before coding)
   - Code Generation Best Practices
   - Common Pitfalls to Avoid
   - Quick Reference (testing syntax, agent structure)

3. Agent Description (角色定义)
   - 来自 agent 的 description 字段

4. Skill Index (技能索引)
   - <available_skills> 列表
   - MUST load 指令
```

### User Prompt（任务层）

User prompt 包含具体的任务描述和查询：

```
1. Rendered Agent Prompt (任务描述)
   - 来自 agent 的 prompt 字段（渲染后）
   - 如果 prompt 包含 {{var}}，会被替换为实际值

2. LLM Act Expression (实际查询)
   - 来自 llm act 后面的表达式
   - 例如：llm act "How do I sort a list?"
```

### 示例

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

**LLM 看到的消息结构**：

```
System: <framework_instructions>
        You MUST use your tools to take action...
        You MUST load relevant skills...
        </framework_instructions>
        
        <helen_conventions>
        Helen language rules and best practices...
        </helen_conventions>
        
        A coding assistant                    ← description
        
        <available_skills>
        Before replying, scan skills below...
        You MUST load relevant skills...
        </available_skills>

User:   You are a Python expert.             ← prompt (任务描述)
        Help me with coding.
        
        How do I sort a list?                ← llm act expression (查询)
```

### 设计原则

| 原则 | 说明 |
|------|------|
| **角色清晰** | System = 行为规则，User = 具体任务 |
| **自动注入** | Framework 和 Conventions 对所有 agent 自动生效 |
| **技能驱动** | 强制要求加载相关技能再生成代码 |
| **执行导向** | 强制要求使用工具执行，而不是描述 |
| **向后兼容** | 所有现有 agent 定义继续工作 |

### Token 预算

系统提示词约占 1300 tokens（~13%），在典型 32k-128k 上下文窗口中完全可接受。

### 深入阅读

本节覆盖了 Helen 提示词架构的"形式"（System 和 User 分别装什么）。关于如何**写好** `prompt` 和 `description` 的内容——结构布局、写作原则、反模式、Token 预算分配、缓存友好设计、中途注入机制——请参阅 [[../reference/agent-system-prompt-guide|Agent 提示词工程完全指南]]。那份指南来自对 Claude Code 系统提示词的逆向工程，是把 agent 质量从"能跑"提升到"可靠"的关键知识。

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

## Agent 上下文管理 (v1.15)

Helen v1.15 引入了完整的上下文管理增强，让 Agent 在长时间运行中保持高效和稳定。

### 概述

上下文管理系统包含三层：

| 组件 | 作用 | 说明 |
|------|------|------|
| **工作记忆** | 自动跟踪关键信息 | 活跃文件、最近决策、待办事项、错误历史 |
| **渐进压缩** | 五层压缩管线 | 从 60% 到 95% 使用率，逐层升级 |
| **缓存感知压缩** | 优化缓存命中 | 保留前缀不变，仅修改后缀 |

### `context {}` 配置块

在 Agent 声明中使用 `context {}` 配置上下文策略：

```helen
agent ResearchAssistant {
    description "Long-running research agent"
    
    // v1.15: 上下文配置
    context {
        compression "graduated"      // "none" | "graduated" | "traditional"
        cache-aware true             // 启用缓存感知压缩
        working-memory true          // 启用工作记忆
        working-memory-tokens 8000   // 工作记忆令牌预算
    }
    
    tools ["read_file", "write_file", "web_search"]
    
    prompt "You are a research assistant. Help the user find and summarize information."
}

// 中文关键字等价
agent 研究助手 {
    上下文 {
        压缩 "graduated"
        缓存感知 true
        工作记忆 true
        工作记忆令牌 8000
    }
}
```

**配置选项**：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `compression` | str | `"graduated"` | 压缩策略 |
| `cache-aware` | bool | `true` | 缓存感知压缩 |
| `working-memory` | bool | `true` | 工作记忆开关 |
| `working-memory-tokens` | int | `5000` | 工作记忆预算 |

### 工作记忆

启用 `working-memory true` 后，Agent 自动跟踪：

- **活跃文件** — 通过 `read_file`、`write_file` 操作的文件
- **最近决策** — Assistant 做出的关键选择（如 "Modified src/main.py"）
- **待办事项** — 从 TODO/FIXME/`[ ]` 注释中提取
- **错误历史** — shell 命令失败记录

```helen
// 辅助函数：修复代码
fn fix_code(code: str): str {
    // 实际的代码修复逻辑
    return code  // 简化示例
}

agent CodeReviewer {
    context {
        working-memory true
        working-memory-tokens 6000
    }
    
    tools ["read_file", "write_file", "patch_file"]
    
    functions {
        fn fix_code(code: str): str {
            // 实际的代码修复逻辑
            return code  // 简化示例
        }
    }
    
    main {
        // 自动跟踪：这些操作会更新工作记忆
        let code = read_file("src/main.py")
        let fixed = fix_code(code)
        write_file("src/main.py", fixed)
        
        // LLM 现在知道哪些文件被修改了
        return llm act "Review the changes"
    }
}
```

### 渐进压缩 (五层管线)

当上下文使用率增长时，自动应用逐层压缩：

| 层级 | 阈值 | 策略 | 成本 |
|------|:----:|------|:----:|
| Layer 1: Budget Reduction | 60% | 替换大工具输出为引用 | 零 |
| Layer 2: Snip | 70% | 丢弃旧的对话轮次 | 零 |
| Layer 3: Microcompact | 80% | 清除旧工具结果，保留决策 | 零 |
| Layer 4: Context Collapse | 90% | 归档并生成结构摘要 | 零 |
| Layer 5: Auto-Compact | 95% | 激进压缩（最后手段） | 零 |

所有层都是零推理成本（不调用 LLM）。

### 缓存感知压缩

启用 `cache-aware true` 后，压缩策略变为缓存友好：

- **稳定前缀**（30%）— 前 N 条消息完全不变，最大化缓存命中
- **可压缩后缀**（70%）— 仅在后缀区域应用压缩
- **批量阈值**（75%）— 使用率低于 75% 时不触发压缩

预期效果：
- 缓存命中率：10-20% → **70-80%**
- 成本降低：**50-70%**
- 延迟降低：**30-50%**

### 三通道上下文

启用工作记忆后，LLM 看到的上下文分为三个通道：

| 通道 | 比例 | 内容 |
|------|:----:|------|
| 系统指令 | 15% | 框架指令、Agent 描述、技能索引 |
| 工作记忆 | 50% | 活跃文件、决策、待办、错误 |
| 对话历史 | 35% | 压缩后的对话消息 |

### 最佳实践

| Agent 类型 | 推荐配置 | 说明 |
|-----------|---------|------|
| 研究型 Agent | `compression "graduated"` + `working-memory true` | 长对话，需跟踪文件 |
| 快速响应 | `compression "none"` + `working-memory false` | 短对话，低延迟 |
| 多轮对话 | `cache-aware true` + `working-memory-tokens 8000` | 高缓存命中率 |

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

### Channel：Agent 间通信端点

`channel` 用于 Agent 间的**消息传递**，语法和 shared store 相同，但语义不同。

```helen
channel MessageQueue {
    let messages: list = []
    
    fn send(msg: str) {
        messages.append(msg)
    }
    
    fn receive(): str {
        if (len(messages) == 0) {
            return ""
        }
        return messages.shift()
    }
    
    fn pending(): int {
        return len(messages)
    }
}

// 生产者
agent Producer() {
    main {
        MessageQueue.send("task-1")
        MessageQueue.send("task-2")
    }
}

// 消费者
agent Consumer() {
    main {
        let msg = MessageQueue.receive()
        if (msg != "") {
            print("Processing: " + msg)
        }
    }
}
```

**Shared Store vs Channel**：

| 特性 | Shared Store | Channel |
|------|--------------|---------|
| 语义 | 共享状态容器 | 消息传递端点 |
| 典型用途 | Counter、Cache、Config | Queue、EventBus、Signal |
| 运行时 | 相同（SharedStore 类） | 相同（SharedStore 类） |
| 线程安全 | ✅ RLock | ✅ RLock |

选择建议：
- 需要**共享引用类型**（list/dict）+ 方法封装 → `shared store`
- 构建**消息/事件系统** → `channel`

### Detach 与共享状态（v1.17+）

`detach` 语句可以在后台执行任务，同时访问 shared store 和 channel：

```helen
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
}

agent Worker() {
    main {
        // 启动 3 个后台任务，共享同一个 Counter
        detach Counter.increment()
        detach Counter.increment()
        detach Counter.increment()
    }
}

Worker()
sleep(100)  // 等待后台任务
print(Counter.count)  // 输出: 3
```

**线程安全保证**：
- SharedStore 内部使用 RLock 保护所有字段访问
- 多个 detached agent 并发调用方法时，自动序列化执行
- 主线程和 detached agent 可以同时访问同一个 SharedStore

---

> **下一步**: [[tutorial/06-llm-statements|LLM 语句实战]]
