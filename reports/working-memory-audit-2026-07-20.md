# Working Memory 推理链路审计报告

**审计日期**：2026-07-20
**审计范围**：Helen v1.23.1 中 working memory 在 LLM 推理过程中的保存与利用情况
**审计方法**：源码追踪 + Python 实测验证

---

## 📊 总体结论

**推理链路在"主路径"上是完整且工作的**，但存在 4 个实际影响有效性的 bug 和 1 个文档错误。

| 类别 | 数量 | 严重性 |
|------|------|--------|
| ✅ 工作正常的链路 | 2 | — |
| ❌ 实际 bug | 3 | 高/中 |
| ⚠️ 设计缺陷 | 1 | 中 |
| 📝 文档错误 | 1 | 高（误导用户） |

---

## ✅ 工作正常的链路

### 链路 1：工具调用后自动更新 working memory

**调用路径**：
```
LLM 返回 tool_calls
  → http_llm.py:629-633 构造 tool_calls_log（包含 name/args/result）
  → llm_mixin.py:1266 _agent_context.update_from_tool_call(name, args_raw, result, exit_code)
  → agent_context.py:336 内部按工具名分发：
      - read_file  → working_memory._add_active_file(path)
      - write_file → _add_active_file + _add_decision("Modified ...")
      - patch_file → _add_active_file + _add_decision("Patched ...")
      - shell_exec → 条件判断后 _add_error
      - glob_files/grep_files → _add_decision("Searched for: ...")
```

**实测验证**（Python 脚本）：
```
=== After read_file('main.py') ===
Active files: ['main.py']

=== After write_file('out.py') ===
Active files: ['main.py', 'out.py']
Recent decisions: ['Modified out.py']
```
✅ **链路 1 有效**。

### 链路 2：LLM 调用前注入 working memory 到 context

**调用路径**：
```
visit_llm_act_expr
  → _prepare_history_for_llm(system_prompt, user_prompt)
  → llm_mixin.py:1344 agent_ctx.prepare_context(...)
  → agent_context.py:434 build_three_channel_context(system, wm, history, max_tokens)
  → working_memory.py:395-400 把 wm.to_context() 作为系统消息注入：
      messages.append({"role": "system", "content": f"[Working Memory]\n{working_context}"})
```

**实测验证**：
```
=== Full prepared context ===
[system] <budget:token_budget>8000</budget:token_budget>
You are a helper
---
[system] [Working Memory]
## Recent Errors
- Command: bad cmd
  Error: some error occurred
...
---
[user] hello
---
[assistant] hi
```
✅ **链路 2 有效**，三通道结构（system / working memory / history）正确构建。

---

## ❌ Bug 1：`shell_exec` 错误跟踪几乎失效（高严重性）

### 现象

`update_from_tool_call` 的 shell_exec 分支：

```python
# agent_context.py:388-395
elif tool_name == "shell_exec":
    command = tool_args.get("command", "")
    if exit_code is not None and exit_code != 0:           # 分支 A
        error_msg = str(tool_result)[:200] if tool_result else "Unknown error"
        self.working_memory._add_error(command, error_msg)
    elif isinstance(tool_result, str) and "error" in tool_result.lower():  # 分支 B
        error_msg = tool_result[:200]
        self.working_memory._add_error(command, error_msg)
```

### 根因

`http_llm.py:629-633` 构造 `tool_calls_log` 时**没有写入 `exit_code` 字段**：
```python
tool_calls_log.append({
    "name": tc["function"]["name"],
    "args": tc["function"].get("arguments", "{}"),
    "result": result[:500] if len(result) > 500 else result,
    # ❌ 没有 "exit_code": ...
})
```

因此 `llm_mixin.py:1265` 取到的 `exit_code = tc.get("exit_code")` **永远是 None**。

**分支 A 永远不会触发**。错误跟踪完全依赖分支 B 的字符串包含 "error" 启发式。

### 影响

- ❌ 中文错误信息（"失败"、"出错"、"异常"）全部漏掉
- ❌ 非 error 字样的英文错误（"failed"、"denied"、"not found" 等）部分漏掉
- ❌ 误报：包含 "error" 字样的成功输出会被误判为错误

### 修复建议

1. `http_llm.py` 在 `tool_calls_log` 中加入 `exit_code` 字段（需要从 shell_exec 工具的返回值中提取）
2. 分支 B 的字符串匹配扩展为多语言关键字：`{"error", "failed", "failure", "失败", "出错", "异常", "denied"}`
3. 或者让 shell_exec 工具返回结构化结果（dict with `exit_code` field）

---

## ❌ Bug 2：`task_description` 永远不会自动设置（中严重性）

### 现象

`WorkingMemory.task_description` 是 working memory 中**最高优先级**的部分（在 `to_context` 中首先输出，最后被驱逐）。

但**没有任何代码自动设置它**。

### 影响

- Working memory 注入 LLM 时，永远没有 "Current Task" 段
- LLM 失去对当前任务的高优先级感知
- 用户必须手动调用 `working_memory_set("task", ...)`，但实际中几乎没人这么做

### 修复建议

方案 A：在 `visit_llm_act_expr` 中从 prompt 自动提取：
```python
if not self._agent_context.working_memory.task_description:
    self._agent_context.working_memory.task_description = prompt[:200]
```

方案 B：在 `agent_context.py:336` `update_from_tool_call` 中，首次调用时自动设置 task_description 为 agent 的 description 或第一个 prompt。

方案 C：在 `_enter_invocation(agent_name)` 中注入当前 agent 描述。

---

## ❌ Bug 3：中文工具名在 `update_from_tool_call` 中匹配不到（中严重性）

### 现象

`agent_context.py` 中 `update_from_tool_call` 的工具名匹配是**硬编码英文 canonical 名**：
```python
if tool_name == "read_file":      # ❌ 中文 "读文件" 匹配不上
elif tool_name == "write_file":   # ❌ 中文 "写文件" 匹配不上
...
```

### 触发条件

当用户在 `functions {}` 中定义中文函数名并暴露给 LLM：
```helen
agent MyAgent {
    functions {
        fn 读文件(path: str): str { ... }
    }
    tools = ["读文件"]
}
```

LLM 返回 `tool_call.name = "读文件"`，`update_from_tool_call("读文件", ...)` 匹配不到任何分支，working memory 不更新。

### 实测验证

```
=== Chinese tool name '读文件' ===
Active files after Chinese name: ['main.py', 'out.py']  # 没有变化！
```

### 影响

- 用户自定义中文工具的调用不会被 working memory 跟踪
- **但注意**：Python 工具（如 read_file）的中文别名（"读文件"）在 `get_tool_schemas` 阶段就不被识别（实测验证），所以 LLM 端看到的永远是英文 canonical 名，不影响内置工具

### 修复建议

方案 A：在 `update_from_tool_call` 中先做别名→canonical 翻译：
```python
from helen.stdlib.locales.zh import ZH_TO_EN
tool_name = ZH_TO_EN.get(tool_name, tool_name)
```

方案 B：用反向映射表，运行时从 stdlib 构建。

---

## ⚠️ 设计缺陷：用户 API 不是通用 key-value 存储

### 现象

`working_memory_set(key, value)` 只接受 5 个固定 key：
```python
_WORKING_MEMORY_KEYS = frozenset({"task", "active_files", "decisions", "todos", "errors"})
```

任意 key 会返回 error：
```
>>> working_memory_set("analysis_main", "found 3 bugs")
{'status': 'error', 'error': "Unknown working memory key: analysis_main. Valid keys: ['active_files', 'decisions', 'errors', 'task', 'todos']"}
```

### 影响

- 不适合用作 agent 之间的通用数据交换媒介
- 用户在 `helen-programming-methodology` 模式 B 中看到的"任意 key-value"示例**是错的**（见下方文档错误）

### 修复建议

方案 A：**增强 API** — 增加 `custom_data: dict` 字段到 WorkingMemory，允许任意 key-value
方案 B：**文档修正** — 明确说明只有 5 个固定 key，模式 B 改用 SharedStore 或 Channel 传参

---

## 📝 文档错误：`helen-programming-methodology` §5 模式 B 示例代码错误

### 位置

`helen/skills/software-development/helen-programming-methodology/SKILL.md` 第 249-265 行。

### 错误示例

```helen
// 模式 B：working_memory 显式保存（适用于跨 agent 数据交换）
agent Analyzer(file: str, ch: Channel) {
    main {
        let result = llm act "分析文件 " + file + " 的 bug"
        working_memory_set("analysis_" + file, result)  // ❌ 错误！key 必须是固定 5 个之一
        ch.send({"status": "ok", "key": "analysis_" + file})
    }
}

main {
    let m = spawn Analyzer("main.py")
    let msg = m.receive()
    if msg["status"] == "ok" {
        let data = working_memory_get(msg["key"])  // ❌ 错误！
        ...
    }
}
```

### 修正方案

模式 B 应该用 `decisions` 或 `todos` 等合法 key，或者直接改用 **SharedStore**（更符合跨 agent 数据交换场景）：

```helen
// 模式 B（修正）：SharedStore 显式保存（适用于跨 agent 数据交换）
shared store AnalysisStore {
    results: dict = {}
}

agent Analyzer(file: str, ch: Channel) {
    main {
        let result = llm act "分析文件 " + file + " 的 bug"
        AnalysisStore.results[file] = result   // ✅ 用 SharedStore
        ch.send({"status": "ok", "file": file})
    }
}

main {
    let m = spawn Analyzer("main.py")
    let msg = m.receive()
    if msg["status"] == "ok" {
        let data = AnalysisStore.results[msg["file"]]  // ✅ 直接取
        print("分析结果: " + data)
    }
}
```

---

## 📈 完整调用链路图

```
┌─────────────────────────────────────────────────────────────┐
│ LLM 调用前（读取路径）                                         │
├─────────────────────────────────────────────────────────────┤
│ visit_llm_act_expr                                          │
│   └─ _prepare_history_for_llm(system_prompt, user_prompt)  │
│       └─ agent_ctx.prepare_context(...)                     │
│           └─ build_three_channel_context(system, wm, hist) │
│               └─ wm.to_context() → "[Working Memory]\n..." │
│                                                             │
│ 注入到 LLM 请求：                                            │
│   messages = [                                              │
│     {role: "system", content: budget_tag + system_prompt}, │
│     {role: "system", content: "[Working Memory]\n..."},    │  ← 这里
│     {role: "user", content: "..."},                         │
│     {role: "assistant", content: "..."},                    │
│     ...                                                     │
│   ]                                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 工具调用后（写入路径）                                         │
├─────────────────────────────────────────────────────────────┤
│ http_llm.py: act() 执行工具循环                              │
│   └─ 每个工具执行完后，记录到 tool_calls_log                  │
│       ⚠️ 缺少 exit_code 字段                                │
│                                                             │
│ llm_mixin.py: _process_tool_calls_for_display()            │
│   └─ self._agent_context.update_from_tool_call(...)        │
│       └─ working_memory._add_active_file / _add_decision   │
│          / _add_error / _add_todo                           │
│                                                             │
│ 下一次 LLM 调用前会看到这些更新 ✅                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 用户手动 API（部分工作）                                      │
├─────────────────────────────────────────────────────────────┤
│ working_memory_set("task", "...")           ✅ 工作         │
│ working_memory_set("active_files", "x.py")  ✅ 工作（append）│
│ working_memory_set("active_files", [...])   ✅ 工作（replace）│
│ working_memory_set("decisions", "...")      ✅ 工作         │
│ working_memory_set("todos", "...")          ✅ 工作         │
│ working_memory_set("errors", {...})         ✅ 工作         │
│ working_memory_set("任意key", "...")        ❌ 返回 error    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 修复优先级

| 优先级 | 问题 | 修复成本 | 影响范围 |
|--------|------|---------|---------|
| **P0** | 文档错误（模式 B 示例） | 低（只改文档） | 用户立即受影响 |
| **P1** | `shell_exec` 缺 exit_code | 中（需改 http_llm.py + tools.py） | 错误跟踪基本失效 |
| **P1** | `task_description` 永不自动设置 | 低（加几行代码） | 最高优先级区永远空 |
| **P2** | 中文工具名匹配 | 低（加翻译步骤） | 仅影响自定义中文工具 |
| **P3** | 用户 API 不支持任意 key | 中（设计决策） | 看是否扩展 API |

---

## 🔍 测试建议

修复后应添加的测试：

1. `tests/runtime/test_working_memory.py`：
   - `test_shell_exec_error_tracked_with_exit_code`
   - `test_shell_exec_error_tracked_with_chinese_error_message`
   - `test_task_description_auto_set_on_first_llm_act`
   - `test_chinese_tool_name_maps_to_canonical`

2. `tests/execution/test_working_memory_integration.py`：
   - 端到端测试：执行 Helen 程序，验证 LLM 请求中包含 `[Working Memory]` 段
   - 验证工具调用后下一次 LLM 调用能看到 working memory 更新

---

## 📚 相关文件

- `helen/runtime/working_memory.py` — WorkingMemory 类 + build_three_channel_context
- `helen/interpreter/agent_context.py` — AgentContextManager.update_from_tool_call + prepare_context
- `helen/interpreter/llm_mixin.py` — 工具调用处理 + LLM 调用链
- `helen/runtime/http_llm.py` — tool_calls_log 构造（缺 exit_code）
- `helen/stdlib/context.py` — working_memory_set/get 用户 API
- `helen/skills/software-development/helen-programming-methodology/SKILL.md` — 模式 B 错误示例
