# WebUI /goal 命令实现总结

## 概述

在 Helen agent WebUI 中实现了 `/goal` 命令，让 agent 可以突破单次 `max_turns` 限制，持续工作直到目标完成。采用 A+B 方案：Python 端 auto-continue 循环 + LLM 自报告完成状态。

## 核心特性

### 1. 自动续传循环
- 最多 10 轮迭代（可配置）
- 每轮使用 actor 的 `max-turns 100`
- 总工具调用上限：10 × 100 = 1000 轮

### 2. LLM 自报告完成状态
在 goal 模式的 system prompt 中注入指令，要求 LLM 在每次回复末尾标注：
- `[GOAL_COMPLETE] 最终总结：...` — 目标完成
- `[GOAL_IN_PROGRESS] 还需要做什么：...` — 继续工作

后端解析这些标记决定是否续传。

### 3. 进度展示
- 前端实时显示 "🎯 目标 Pursue 中... 第 N/10 轮"
- 完成时显示 "✅ 目标完成" + 总结
- 达到最大迭代时显示 "⚠️ 达到最大迭代次数"

## 文件改动

### 新增文件

1. **`helen/agent/webui/backend/app/goal_handler.py`** (160 行)
   - `parse_goal_status()`: 解析 LLM 回复中的完成标记
   - `goal_appears_complete()`: 判断目标是否完成（标记优先 + 启发式回退）
   - `build_goal_prompt()`: 构建初始 goal prompt
   - `build_continuation_prompt()`: 构建续传 prompt
   - `GOAL_SYSTEM_PROMPT_INJECTION`: 系统指令模板

2. **`tests/agent/webui/test_goal_handler.py`** (120 行)
   - 19 个测试用例，覆盖所有核心函数
   - 测试标记解析、完成检测、prompt 构建

3. **`tests/integration/test_goal_integration.md`**
   - 集成测试计划和手动测试步骤

### 修改文件

1. **`helen/agent/webui/backend/app/routers/chat.py`** (+110 行)
   - 导入 `goal_handler` 模块
   - 添加 `do_goal_streaming()` 函数：goal 循环的核心实现
   - 在 WebSocket handler 中拦截 `/goal` 命令（在通用斜杠命令之前）
   - 启动 `do_goal_streaming` 作为后台任务

2. **`helen/agent/webui/frontend/src/hooks/useChat.ts`** (+50 行)
   - 添加 `goal_progress` 事件处理：显示轮次进度
   - 添加 `goal_complete` 事件处理：显示完成消息和总结

## 架构设计

```
用户输入: /goal 实现 HTTP 服务器
    ↓
前端 WebSocket: {type: "message", content: "/goal ..."}
    ↓
后端 chat.py: 拦截 /goal，启动 do_goal_streaming()
    ↓
do_goal_streaming() 循环:
    for iteration in range(10):
        1. 发送 goal_progress 事件（显示进度）
        2. 调用 helen_bridge.run_chat_streaming()
        3. 收集响应文本 + 转发 llm_chunk 到前端
        4. 解析响应中的 [GOAL_COMPLETE] / [GOAL_IN_PROGRESS]
        5. 如果完成 → 发送 goal_complete 事件，break
        6. 如果未完成 → 构建续传 prompt，继续下一轮
    ↓
前端显示完成消息和总结
```

## 关键设计决策

### 1. 完成检测：LLM 自报告 vs 启发式
**选择**: LLM 自报告优先，启发式回退

**原因**:
- 更可靠：LLM 自己判断比关键词匹配准确
- 强制反思：要求 LLM 判断"完成了吗"会迫使它评估实际进展
- 自然产生总结：完成声明本身包含总结
- 回退机制：如果 LLM 没有按指示输出标记，使用简单启发式

### 2. 上下文管理
**选择**: 依赖 actor 的 graduated compression，不手动压缩

**原因**:
- actor 已配置 `context { compression "graduated" }`
- 每次迭代后 transcript 自动增长，compression 自动触发
- goal 文本在每次续传 prompt 中重复，确保不会被压缩掉

### 3. 迭代上限
**选择**: 10 轮（可配置）

**原因**:
- 10 × 100 = 1000 轮工具调用，足够大多数任务
- 避免无限循环
- 每轮都有明确的进度提示，用户可以看到进展

### 4. 实现位置
**选择**: WebUI 后端（Python 端），不改 Helen 语言

**原因**:
- 最小改动：不需要新关键字、新 AST、新 parser
- 快速验证：可以立即测试和使用
- 灵活调整：迭代上限、完成检测逻辑都容易修改

## 使用方法

### 基本用法
```
/goal 写一个 Python 计算器
```

### 复杂任务
```
/goal 实现一个完整的 HTTP 服务器，包含：
- 路由系统
- 中间件支持
- 错误处理
- 单元测试
- 文档
```

### 中断
在 goal 循环进行中，点击前端的"停止"按钮即可中断。

## 测试

### 单元测试
```bash
python -m pytest tests/agent/webui/test_goal_handler.py -v
```
19 个测试全部通过 ✓

### 集成测试
参考 `tests/integration/test_goal_integration.md` 进行手动测试。

## 未来增强

### 1. 可配置迭代上限
```python
/goal --max-iterations 20 实现复杂的微服务架构
```

### 2. 进度可视化
在前端显示进度条，每轮迭代更新。

### 3. 目标分解
让 LLM 在开始时分解目标为子任务，逐个完成。

### 4. 用户确认
在每轮迭代后询问用户："目标完成了吗？继续/停止"

### 5. 成本估算
显示每轮迭代的 token 消耗和总成本。

## 技术细节

### WebSocket 事件

**goal_progress**:
```json
{
  "type": "goal_progress",
  "data": {
    "iteration": 3,
    "max_iterations": 10,
    "goal": "实现 HTTP 服务器"
  }
}
```

**goal_complete**:
```json
{
  "type": "goal_complete",
  "data": {
    "status": "complete",  // or "max_iterations"
    "message": "✅ 目标完成",
    "summary": "已实现路由、中间件和测试",
    "iterations": 5
  }
}
```

### 完成标记正则
```python
_GOAL_COMPLETE_RE = re.compile(
    r"\[GOAL_COMPLETE\]\s*(?:最终总结[：:])?\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)
_GOAL_IN_PROGRESS_RE = re.compile(
    r"\[GOAL_IN_PROGRESS\]\s*(?:还需要做什么[：:])?\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)
```

## 限制和注意事项

1. **上下文窗口**: 虽然使用 graduated compression，但长任务仍可能遇到上下文限制
2. **成本控制**: 多轮迭代会消耗大量 token，用户应注意成本
3. **完成检测**: 依赖 LLM 自报告，可能不准确（但比启发式好）
4. **中断恢复**: 目前中断后无法从断点恢复，需要重新开始

## 总结

`/goal` 命令是 Helen WebUI 的重要增强，让 agent 能够自主完成复杂的多步骤任务。通过 LLM 自报告机制，实现了可靠的完成检测和自动续传。实现简洁（~340 行代码），易于理解和维护。
