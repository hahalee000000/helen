# 教程 08: 模块与导入

> import / 多格式 / 跨文件复用 / 路径安全

---

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

---

## 导入别名

```helen
import "./math_utils.helen" as math

main {
    let result = math.add(1, 2)
}
```

---

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

---

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

---

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

---

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

---

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

---

## 练习

1. 创建一个 utils.helen 文件，包含常用函数
2. 在 main.helen 中导入并使用这些函数
3. 创建一个 config.json 并导入
4. 尝试循环导入，观察行为

---

## ⚠️ 开发时的重要提示：模块缓存

### 问题：修改 .helen 文件后不生效？

Helen 的 `ImportResolver` 使用**内存级缓存**来加速重复导入。这意味着：

- ✅ **CLI 模式**（`helen main.helen`）：每次都重新加载，无需担心
- ❌ **REPL / 长时间运行的服务**：修改文件后不会自动重新加载

### 示例场景

```python
# 场景 1: Python REPL 中开发
from helen.interpreter import Interpreter

interp = Interpreter()
interp.execute_file("agent.helen")  # 加载 v1

# 修改 agent.helen（添加新功能）...

interp.execute_file("agent.helen")  # ❌ 仍然是 v1！
```

### 解决方案

#### 方案 1: 使用 CLI（推荐用于开发）

```bash
# 每次执行都是新进程，自动重新加载
helen main.helen
```

#### 方案 2: 在代码中创建新实例

```python
def run_agent():
    # 每次创建新的 Interpreter，缓存自动清空
    interp = Interpreter()
    return interp.execute_file("agent.helen")
```

#### 方案 3: 手动清除缓存

```python
interp = Interpreter()
interp.execute_file("agent.helen")

# 修改文件后，手动清除缓存
interp.import_resolver._cached_results.clear()
interp.import_resolver._loaded.clear()

# 重新执行
interp.execute_file("agent.helen")  # ✅ 使用新代码
```

### 深入理解

详见 [runtime/import.md - 缓存机制](../runtime/import.md#缓存机制开发者必读)

---
