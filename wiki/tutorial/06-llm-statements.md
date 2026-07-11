# 教程 06: LLM 语句

> llm act / llm if 实战

---

## LLM 语句概述

Helen 有两个关键字级 LLM 语句：

| 语句 | 用途 | 返回值 |
|---|---|---|
| `llm act` | 让 LLM 执行任务（支持可选流式回调） | 响应文本 |
| `llm if` | 让 LLM 分类路由 | 执行匹配分支或返回值 |

---

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

---

`llm act` 也可以作为表达式直接使用，不需要 agent 上下文：

```helen
// 顶层直接调用
llm act "translate hello to chinese."

// 在函数中使用
fn translate(text, target) {
    return llm act "translate " + text + " to " + target
}

// 赋值给变量
let result = llm act "summarize this article"

// 字符串拼接构建 prompt
let topic = "climate change"
let analysis = llm act "analyze the impact of " + topic
```

**语法对比：**

| 形式 | 语法 | 用途 |
|------|------|------|
| 表达式形式 | `llm act <expr>` | 直接调用 LLM，expr 的值作为 prompt |
| Bare form | `llm act` | 在 agent main 中省略参数，自动使用渲染后的 prompt |

**注意：** 语句形式 `llm act Agent(args) "desc"` 已废弃，请使用 `Agent(args)` 调用 agent。

**何时使用表达式形式：**
- 快速原型测试，不想定义 agent
- 动态构建 prompt
- 在 REPL 中直接调用 LLM
- 简单的 LLM 调用场景

---

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

---

## llm act 流式输出（on_chunk / on_complete）

`llm act` 支持可选的 `on_chunk` 和 `on_complete` 回调，用于逐 chunk 流式输出 LLM 响应，适用于长文本生成场景。

### 基本用法

使用 `on_chunk` 指定回调函数，自定义处理每个 chunk：

```helen
fn handle_chunk(chunk) {
    stream_print("[" + chunk + "]")
}

main {
    llm act "Explain recursion in one paragraph" on_chunk handle_chunk
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
    llm act "Write a short story" on_chunk handle_chunk on_complete on_done
}
```

`on_complete` 回调在流式传输完成后调用，适合用于：
- 显示完成提示
- 记录统计信息（如总 token 数）
- 触发后续操作

### 在 agent 中使用

`llm act` 的流式回调在 agent 内自动使用 agent 的配置（model、temperature、prompt）：

```helen
agent Poet(topic: str) {
    description "Write poetry"
    temperature 0.9
    prompt """
    Write a poem about: {{topic}}
    """

    main {
        fn print_chunk(chunk: str) { stream_print(chunk) }
        llm act on_chunk print_chunk    // bare form：使用渲染后的 prompt
    }
}
```

### 动态 prompt

```helen
fn print_chunk(chunk: str) {
    stream_print(chunk)
}

main {
    let topic = "the beauty of recursion"
    llm act "Write a haiku about " + topic on_chunk print_chunk
}
```

### 与其他 LLM 语句对比

| 语句 | 用途 | 输出方式 |
|------|------|----------|
| `llm act` | 获取完整响应文本（可选流式回调） | 等待完成后返回，或通过 on_chunk 逐 chunk 输出 |
| `llm if` | LLM 分类路由 | 等待完成后执行分支 |

---

## 对比：何时使用哪个？

| 场景 | 使用 |
|---|---|
| 需要 LLM 返回文本 | `llm act` |
| 需要 LLM 做分类决策 | `llm if` |
| 需要 LLM 从选项中选择并执行代码 | `llm if` + `branch` |
| 需要实时输出生成过程 | `llm act` + `on_chunk` 回调 |
| 多步骤决策 | 嵌套 `llm if` |
| 需要结果变量 | `llm if` 或 `llm act` |

---

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

### 上下文窗口保护

对话历史会自动裁剪后传给 LLM，你不需要手动管理上下文长度：

- **自动裁剪**：每次 LLM 调用前，根据上下文窗口大小自动删除最旧消息
- **自动压缩**：历史过长时，旧消息会被压缩成摘要
- **工具结果上限**：单次工具循环的结果数量有上限，避免上下文爆炸
- **上下文超限恢复**：API 返回 context-too-large 错误时，自动重试

---

## REPL 中的 LLM 调用

在 REPL 中，`llm act` 表达式会调用真实的 LLM（通过 HTTP API）：

```bash
$ helen repl
>>> llm act "translate hello to chinese"
'hello → 你好 (nǐ hǎo)'
>>> let result = llm act "what is 2+2?"
>>> result
'4'
```

**说明：**
- REPL 和脚本模式都直接调用 LLM API
- 响应时间：7-11 秒（取决于网络和模型）
- 自动从 `~/.helen/config.yaml` 或 `~/.helen/.env` 读取配置
- 向后兼容 `~/.hermes/.env` 配置

**配置：**
确保 `~/.helen/config.yaml` 包含：
```yaml
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-api-key-here"
  model: "qwen3.7-plus"
```

或使用 `~/.helen/.env`：
```
HELEN_API_KEY=***
HELEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

---

## Function Calling（工具调用）

当 Agent 配置了 `tools = [...]` 时，`llm act` 会自动进入 function calling 循环：

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

**内置工具列表（10 个）：**

| 工具 | 功能 | 参数 |
|------|------|------|
| `web_search` | 搜索网页（Bing） | `query: str` |
| `web_fetch` | 获取网页内容 | `url: str` |
| `read_file` | 读取文件 | `path: str` |
| `write_file` | 写入文件（覆盖） | `path: str, content: str` |
| `patch_file` | 精确修改文件（自动处理空白/缩进等差异） | `path: str, old_string: str, new_string: str` |
| `shell_exec` | 执行 shell 命令 | `command: str` |
| `calculate` | 数学计算 | `expression: str` |
| `find_files` | 按 glob 模式查找文件 | `path: str, pattern: str = "**/*", max_results: int = 200` |
| `search_files` | 按内容搜索文件（文本/正则） | `path: str, pattern: str, regex: bool = false, case_sensitive: bool = true, max_results: int = 100` |
| `load_skill` | 加载技能文档（总是可用） | `name: str` |

### patch_file 模糊匹配

`patch_file` 使用 `old_string` → `new_string` 模式精确修改文件，内置多种匹配策略处理 LLM 生成代码的常见差异（空白、缩进、转义、Unicode 等）：

```helen
// 修改文件中的特定函数
llm act "Read /tmp/main.py and change the function name from 'foo' to 'bar'"
```

通常你不需要关心匹配细节——LLM 生成的代码即使和原文有细微差异，`patch_file` 也能正确处理。

---

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
        // prompt 渲染后 → system_prompt
        // "Translate the following text to French:\nHello"
        // → 作为 {"role": "system"} 注入
        return llm act "Please translate accurately"
        // → 作为 {"role": "user"} 注入
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

---

## 练习

1. 创建一个 llm if 三层嵌套的分类系统
2. 使用 llm if 让 LLM 选择算法策略并返回结果
3. 使用 llm act 实现一个翻译管道
4. 观察多次 LLM 调用后的对话历史
