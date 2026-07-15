---
name: debugging
description: "Debugging methodology and language-specific debugger tools. Covers systematic root-cause investigation, Python (pdb/debugpy), Node.js (--inspect/CDP), and Helen AI-native observability (debug/trace_on/:last_error/:llm_log) with cookbook workflows for Helen application development."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, root-cause, python, pdb, debugpy, nodejs, inspect, CDP, helen, observability, debug, trace, llm_log]
---

# Debugging — Methodology & Tools

Umbrella skill for all debugging work. Covers the systematic investigation methodology plus language-specific debugger tools, including Helen's AI-native observability with a cookbook of 10 common debugging scenarios for Helen application development.

---

## 1. Systematic Debugging Methodology

**Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

### Phase 1: Root Cause Investigation
1. **Read error messages carefully** — stack traces contain the solution
2. **Reproduce consistently** — `pytest tests/test_module.py::test_name -v`
3. **Check recent changes** — `git log --oneline -10`, `git diff`
4. **Gather evidence in multi-component systems** — instrument at each boundary
5. **Trace data flow** — where does the bad value originate?

### Phase 2: Pattern Analysis
- Find working examples in the same codebase
- Compare against references (read COMPLETELY, don't skim)
- Identify every difference, however small

### Phase 3: Hypothesis and Testing
- Form ONE hypothesis: "I think X is the root cause because Y"
- Make the SMALLEST possible change to test it
- One variable at a time

### Phase 4: Implementation
- Create failing test case FIRST
- Implement single fix addressing root cause
- Verify: `pytest tests/test_regression -v && pytest tests/ -q`
- **Rule of Three**: If 3+ fixes failed, STOP and question the architecture

### Red Flags — STOP and Return to Phase 1
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "I don't fully understand but this might work"
- "One more fix attempt" (when already tried 2+)

---

## 2. Python Debugging (pdb + debugpy)

### Tool Selection

| Tool | When |
|------|------|
| `breakpoint()` + pdb | Local, interactive, simplest |
| `python -m pdb script.py` | Launch under pdb without source edits |
| `debugpy` | Remote/headless/attach to running process |

### pdb Quick Reference

| Command | Action |
|---------|--------|
| `n` | next line (step over) |
| `s` | step into |
| `r` | return from function |
| `c` | continue |
| `l` / `ll` | list source / full function |
| `w` | where (stack trace) |
| `u` / `d` | up / down in stack |
| `p expr` | print expression |
| `b file:line` | set breakpoint |
| `!stmt` | execute arbitrary Python |
| `interact` | full Python REPL in current scope |

### Recipe: Local breakpoint
```python
def compute(x, y):
    breakpoint()  # drops into pdb here
    return result
```
Remember to remove before committing: `rg -n 'breakpoint\(\)' --type py`

### Recipe: pytest debugging
```bash
pytest tests/foo.py::test_bar --pdb -p no:xdist  # xdist breaks pdb!
pytest tests/foo.py::test_bar --showlocals --tb=long  # without pdb
```

### Recipe: Remote debug with debugpy
```bash
# Launch with debugpy
python -m debugpy --listen 127.0.0.1:5678 --wait-for-client script.py

# Or attach to running process
python -m debugpy --listen 127.0.0.1:5678 --pid <PID>
```

### Recipe: remote-pdb (simplest for terminal agents)
```bash
pip install remote-pdb
```
```python
from remote_pdb import set_trace
set_trace(host="127.0.0.1", port=4444)  # blocks until connection
```
Then: `nc 127.0.0.1 4444` → get a (Pdb) prompt

### Common Pitfalls
- pdb under pytest-xdist silently does nothing → use `-p no:xdist`
- `breakpoint()` in CI/non-TTY hangs → never commit it
- `PYTHONBREAKPOINT=0` disables all breakpoints
- `debugpy.listen` doesn't block without `wait_for_client()`
- ptrace may fail on hardened kernels → `echo 0 > /proc/sys/kernel/yama/ptrace_scope`
- **Stale `.pyc` cache**: Code changes don't seem to take effect → `find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -exec rm -rf {} +`. Always clear cache after modifying source if behavior seems unchanged.
- **`asyncio.get_running_loop()` is unreliable for "am I in a loop?" checks**: It raises `RuntimeError` when no loop is running, but in some contexts (mixed sync/async code, REPL environments, nested interpreters) the `except RuntimeError` clause may not catch it as expected — the exception propagates despite the try/except. **Use `asyncio.get_event_loop()` + `.is_running()` instead**, which is safer across all contexts:
  ```python
  # ❌ Unreliable — may not catch properly in all contexts
  try:
      asyncio.get_running_loop()
      in_event_loop = True
  except RuntimeError:
      in_event_loop = False
  
  # ✅ Reliable — works in REPL, scripts, tests, nested contexts
  in_event_loop = False
  try:
      _loop = asyncio.get_event_loop()
      if _loop.is_running():
          in_event_loop = True
  except Exception:
      in_event_loop = False
  ```
  **Symptom**: Code works in standalone scripts but fails in REPL/interactive environments with `RuntimeError: no running event loop` even though you have a try/except around `get_running_loop()`.

---

## 3. Node.js Debugging (--inspect + CDP)

### Tool Selection
- **`node inspect`** — built-in, zero install, CLI REPL. Best for quick poking.
- **CDP via `chrome-remote-interface`** — scriptable, automate many breakpoints.

### Launch with Inspector
```bash
node --inspect script.js           # listen on 127.0.0.1:9229
node --inspect-brk script.js       # listen AND pause on first line
node --inspect=0.0.0.0:9230 script.js  # custom port
```

### Attach to Running Process
```bash
kill -SIGUSR1 <pid>    # enables inspector on existing process
node inspect -p <pid>  # attach debugger CLI
```

### `node inspect` REPL Commands

| Command | Action |
|---------|--------|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `o` / `out` | step out |
| `sb('file.js', 42)` | set breakpoint |
| `cb('file.js', 42)` | clear breakpoint |
| `bt` | backtrace |
| `repl` | drop into REPL in current scope |
| `watch('expr')` | evaluate on every pause |

### Programmatic CDP (automation)
```javascript
const CDP = require('chrome-remote-interface');
const client = await CDP({ port: 9229 });
const { Debugger, Runtime } = client;
// Set breakpoints, capture scope, evaluate expressions...
```

### Common Pitfalls
- Wrong line numbers in TS → break in built `dist/*.js` or enable sourcemaps
- `--inspect` vs `--inspect-brk` — the latter pauses on first line
- Port collisions → use `--inspect=0` (random port), check `/json/list`
- Child processes not inherited → use `NODE_OPTIONS='--inspect-brk'`
- Background kills: `Ctrl+C` out of inspect leaves target paused → `cont` first
- Always bind to `127.0.0.1` (security)

### Heap Snapshots & CPU Profiles
```javascript
// CPU profile
await client.Profiler.enable();
await client.Profiler.start();
await new Promise(r => setTimeout(r, 5000));
const { profile } = await client.Profiler.stop();
```

---

## 4. Helen AI-Native Observability

Helen provides **AI-native observability** instead of traditional interactive debuggers. AI agents need structured, machine-consumable context — not breakpoints and single-stepping.

### Core Concepts

| Traditional Debugger | Helen Observability |
|---------------------|---------------------|
| Breakpoints | `assert` statements |
| Single-step execution | Execution tracing (`trace_on/off`) |
| Variable watch | `debug()` structured output |
| Call stack panel | Programmatic call stack tracking |
| No LLM logging | LLM call audit log |

### assert Statement

```helen
// Runtime assertion with optional message
assert x > 0, "x must be positive"

// Catchable — throws AssertionError
try {
    assert false, "test"
} catch AssertionError e {
    print("Caught: " + e.message)
}
```

### debug() Function

```helen
// Structured debug output to stderr (JSON format)
let x = 42
debug("variable value", x)
// Output: [DEBUG] variable value {"value": 42}
```

### Execution Tracing

```helen
// Programmatic control
trace_on()
let result = compute()
trace_off()
let trace = get_trace(10)
```

**REPL commands**:
```
:trace on          # Enable tracing
:trace off         # Disable tracing
:trace show [n]    # Show last n trace entries
:last_error        # Show structured error context (human-readable)
:last_error -v     # Verbose: includes execution trace
:llm_log [n]       # Show LLM call audit log (compact)
:llm_log [n] -v    # Verbose: shows all audit fields
```

> **Note**: Call stack and execution tracing are enabled by default in REPL — no need for `:trace on`.

### Error Snapshot Format (JSON)

```json
{
  "error": {"type": "RuntimeError", "message": "...", "location": "..."},
  "call_stack": [{"function": "...", "args": {...}}],
  "scope": {"var": "value"},
  "trace": [...],
  "timestamp": 1718812800.0
}
```

### LLM Audit Log

All `llm act` calls are automatically logged:
- timestamp, call_type, agent_name, model
- prompt, response, tokens_in/out, duration_ms
- tool_calls list (for stream mode)
- error (if any)

Compact mode shows one-line summary with model name and tool call count. Verbose mode (`-v`) shows all fields.

### Key Design Decisions

1. **Zero overhead when disabled**: Tracing is opt-in (but enabled by default in REPL)
2. **Ring buffers**: Trace (10000), LLM log (1000), call stack (100)
3. **JSON structured**: AI can parse directly
4. **Auto-capture**: Errors/assertions capture full context

---

## 5. Helen 应用开发调试工作流（Cookbook）

> **给 Helen 应用开发者的实战指南**：什么时候用什么工具，怎么写可观测的 Agent 代码。
>
> **核心心智模型**：`helen check` + `pytest` 是**质量门禁**，`debug()` / `trace_on` / `:last_error` / `:llm_log` 是**手术刀**。前者告诉你"坏没坏"，后者告诉你"坏在哪里、为什么"。

### 5.1 决策树：遇到问题先用哪个工具

```
Helen 程序出问题了吗？
│
├─ 没运行就跑不起来 → helen check <file.helen>
│     └─ 看错误位置，修复语法/语义错误
│
├─ 运行起来但结果错 → 用哪个工具取决于症状
│     │
│     ├─ 报错/异常 → REPL 中跑 → :last_error
│     │     └─ 看 error/call_stack/scope
│     │           ├─ scope 里变量值不对 → 在赋值前加 debug()
│     │           └─ call_stack 太深 → 看哪个函数出问题
│     │
│     ├─ 没报错但 LLM 行为奇怪 → :llm_log -v
│     │     └─ 看 prompt/response/tokens/duration
│     │           ├─ prompt 不对 → 检查 prompt 模板
│     │           ├─ response 被截断 → 看 max_tokens/timeout
│     │           └─ tool_calls 异常 → 看 tools 注册
│     │
│     ├─ 流程看不懂 → 在可疑块外 trace_on()/trace_off()
│     │     └─ get_trace(50) 看执行轨迹
│     │
│     └─ 变量值不符合预期 → 在关键点加 debug()
│           └─ debug("label", {"x": x, "state": state})
│
└─ 性能问题 → context_usage() + context_stats()
      └─ 看 token 占用和压缩情况
```

### 5.2 在 Agent 代码中布局可观测性

**❌ 无可观测性的 Agent**（出问题时无从下手）：

```helen
agent Researcher(topic: str) {
    main {
        let plan = llm act "Plan research on " + topic
        let results = web_search(plan)
        let report = llm act "Write report from " + results
        return report
    }
}
```

**✅ 带可观测性的 Agent**（出问题时有迹可循）：

```helen
agent Researcher(topic: str) {
    main {
        debug("Researcher 启动", {"topic": topic})
        
        let plan = llm act "Plan research on " + topic
        debug("计划阶段完成", {"plan_length": len(plan)})
        
        trace_on()
        let results = web_search(plan)
        trace_off()
        debug("搜索完成", {"results_count": len(results)})
        
        assert len(results) > 0, "搜索没有返回结果"
        
        let report = llm act "Write report from " + results
        debug("报告生成完成", {"report_length": len(report)})
        
        return report
    }
}
```

**布局原则**：

| 位置 | 用什么 | 目的 |
|------|--------|------|
| Agent 入口 | `debug("agent-name", {"arg": arg})` | 记录输入参数 |
| 每次 `llm act` 后 | `debug("llm 结果", {"len": len(result)})` | 追踪 LLM 行为 |
| 工具调用前后 | `trace_on()` / `trace_off()` | 追踪工具执行流程 |
| 分支/循环入口 | `debug("branch", {"i": i})` | 追踪控制流 |
| 关键断言 | `assert cond, "msg"` | 提前捕获错误 |
| Agent 出口 | `debug("agent-name 完成", {...})` | 记录输出 |

### 5.3 常见调试场景 Cookbook（10 例）

#### 场景 1：Agent 给出错误答案

**症状**：用户问 A，Agent 回答 B。

```bash
# 在 REPL 中运行同一程序
helen repl
> :llm_log -v
```

看 LLM 实际收到的 prompt 和返回的 response，定位是 prompt 问题还是模型问题。

#### 场景 2：工具调用死循环

**症状**：Agent 反复调用同一个工具不前进。

```helen
main {
    debug("tool loop iter", {"i": i, "history_len": len(history)})
    llm act "continue task"
}
```

看每次迭代的 `history_len` 是否增长。如果不增长，说明 LLM 没把历史带进来。

#### 场景 3：上下文被意外压缩

**症状**：Agent 突然"忘记"之前的对话。

```helen
main {
    let stats = context_stats()
    debug("上下文状态", {
        "usage_ratio": stats["usage_ratio"],
        "compressed_count": stats["compressed_count"]
    })
    if stats["usage_ratio"] > 0.8 {
        debug("⚠️ 上下文快满了", {})
    }
}
```

或者直接 `pin_message(uuid)` 钉住关键消息。

#### 场景 4：spawn 后子 agent 行为异常

**症状**：主 Agent 正常，spawn 的子 Agent 出错。

```helen
agent Worker(task: str) {
    main {
        debug("Worker 启动", {"task": task, "spawned_from": "MainAgent"})
        // ... 子 Agent 逻辑
        debug("Worker 完成", {})
    }
}

main {
    let ch = spawn Worker("do task")
    debug("spawn 返回 channel", {"channel": str(ch)})
}
```

子 Agent 入口的 debug 能告诉你它收到了什么参数。

#### 场景 5：闭包捕获到意外的值

**症状**：闭包里的变量值和预期不一样。

```helen
let callbacks = []
for i in range(5) {
    callbacks.append(fn() {
        debug("闭包执行", {"i": i})   // 看捕获到的 i 是什么
        return i * 2
    })
}
```

Helen 的闭包是**值捕获**（深拷贝），所以 i 应该都是不同值。如果都是同一个值，就是 bug。

#### 场景 6：LLM 流式输出中断

**症状**：`llm act ... on_chunk fn(c) { print(c) }` 流式输出中途停了。

```helen
let chunks = []
llm act "long response" on_chunk fn(c: str) {
    chunks.append(c)
    debug("chunk 收到", {"len": len(c), "total": len(chunks)})
    return true   // 注意：返回 false 会停止流式
}
debug("流式结束", {"total_chunks": len(chunks)})
```

看是 LLM 没继续返回，还是 callback 返回了 false 主动停止。

#### 场景 7：多 Agent 协作数据错乱

**症状**：Agent A 把数据发给 Agent B，B 收到的数据不对。

```helen
// 发送端
let payload = {"key": "value"}
debug("发送 payload", payload)
channel.send(payload)

// 接收端（在另一个 agent 里）
let received = channel.receive()
debug("收到 payload", received)
assert received["key"] == "value", "数据错乱"
```

两端加 debug 对比，看数据在哪一步被篡改。

#### 场景 8：import 失败

**症状**：`import "other.helen"` 报错。

```helen
debug("当前工作目录", {"cwd": env_get("PWD")})
try {
    import "other.helen"
} catch e {
    debug("import 失败", {"error": str(e), "type": type(e)})
    throw e
}
```

#### 场景 9：stdlib 函数返回值不符合预期

**症状**：`json_parse(text)` 解析失败。

```helen
let text = response_body
debug("要解析的文本", {"text": text, "len": len(text)})
assert text[0] == "{", "不是 JSON 对象"
let parsed = json_parse(text)
debug("解析结果", parsed)
```

#### 场景 10：性能分析——为什么这么慢

**症状**：Agent 响应时间长。

```helen
let t0 = stopwatch_start()
let r1 = llm act "step 1"
debug("step 1 耗时", {"ms": stopwatch_elapsed(t0)})

let t1 = stopwatch_start()
let r2 = llm act "step 2"
debug("step 2 耗时", {"ms": stopwatch_elapsed(t1)})

// 或者看 :llm_log 的 duration_ms 字段
```

### 5.4 与 pytest 的协作

**什么时候用 pytest，什么时候用 Helen 自带工具？**

| 场景 | 用什么 | 理由 |
|------|--------|------|
| 回归测试（改动是否破坏旧功能） | `pytest` | 自动化、可重复、CI 友好 |
| 验证 stdlib 函数行为 | `pytest`（Python 单元测试） | Python 层可以直接 assert |
| 验证新 agent 行为 | `helen <agent.helen>` + `:llm_log` | 需要真实 LLM 调用链路 |
| 复现用户报告的 bug | REPL + `:last_error` | 需要交互式调试 |
| 追踪解释器执行流程 | `trace_on()` + `get_trace()` | 能看到 Python 单元测试看不到的 |
| LLM 集成测试 | `helen <file.helen>` + `debug()` | 验证真实 LLM 行为 |

**最佳实践**：先用 pytest 保证基本正确性，再用 Helen 自带工具验证 LLM 集成和运行时行为。

### 5.5 一个完整的带可观测性的 Agent 示例

```helen
// translator.helen — 带完整可观测性的翻译 Agent
agent Translator(text: str, target: str) {
    description "Translate text with observability"
    
    main {
        // 入口打桩：记录输入
        debug("Translator 启动", {
            "text_len": len(text),
            "text_preview": substring(text, 0, 50),
            "target": target
        })
        
        // 前置断言
        assert len(text) > 0, "text 不能为空"
        assert len(target) > 0, "target 不能为空"
        
        // LLM 调用 + 追踪
        trace_on()
        let prompt = "Translate to " + target + ":\n\n" + text
        let translated = llm act prompt
        trace_off()
        
        // 出口打桩：记录输出
        debug("Translator 完成", {
            "translated_len": len(translated),
            "translated_preview": substring(translated, 0, 50)
        })
        
        // 结果验证（可选）
        assert len(translated) > 0, "翻译结果为空"
        
        return translated
    }
}

// 使用方法：
//   helen translator.helen
//   如果出错，进 REPL 用 :last_error 看结构化错误
//   想看 LLM 调用，用 :llm_log -v
//   想看执行流程，看 debug 输出
```

---

## Quick Decision Guide

| Situation | Use |
|-----------|-----|
| Test fails, need to see intermediate state | `breakpoint()` (Python) or `--inspect-brk` (Node) |
| Long-running process misbehaving | `remote-pdb` (Python) or `kill -SIGUSR1` (Node) |
| Need to understand WHY something fails | Systematic debugging Phase 1-3 first |
| 3+ fixes failed | Question the architecture (Phase 4, step 5) |
| Need to automate many breakpoints | CDP driver (Node) or debugpy (Python) |
