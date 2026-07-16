# LLM 集成

> 模块 M5 (Interpreter + LlmMixin) + M6 (PromptBuilder) + M7 (LLMRuntime) + M16 (HistoryManager) + M17 (StructuredOutput)

---

## 架构说明

LLM 相关的解释器方法已拆分为 `LlmMixin` 类（`helen/interpreter/llm_mixin.py`，502 行），通过多重继承与 `Interpreter` 组合：

```python
class LlmMixin:
    """LLM 语句执行 mixin — 从 Interpreter 拆分的 LLM 相关方法。"""
    def visit_llm_act_expr(node)    # llm act 执行（含流式 on_chunk/on_complete + v1.21 on_tool_end）
    def visit_llm_if_stmt(node)     # llm if 路由
    def _build_tools_list()         # 构建工具列表（含 load_skill）
    def _render_prompt_template()   # {{var}} 模板渲染
    def _get_context()              # 对话历史摘要（4096 token 预算）
    def _add_to_history()           # 记录对话历史
    def clear_history()             # 清除对话历史

class Interpreter(LlmMixin):
    """主解释器 — 继承 LlmMixin 获得 LLM 能力。"""
```

拆分原因：原 `interpreter.py` 达 1630 行（上帝类），拆分后降至 ~1100 行，LLM 逻辑独立维护。

---

## 两种 LLM 语句

### 1. `llm act` — 自主执行

```helen
agent Translator {
    description "Translate text between languages"
    prompt """You are a professional translator."""
    tools = ["web_search"]
    main {
        return llm act "Translate: Hello"
    }
}
```

**执行流程**：
1. 渲染 Agent `prompt` 模板（`{{var}}` 替换为 Environment 中的变量值）
2. 构建 System Prompt：`description` + `Skill Index (Tier 1)` + `渲染后的 prompt`
3. 构建工具列表（两层授权）：只包含 `tools = [...]` 中列出的名字（先查 `functions {}` 块，再查 Python 工具注册表）+ 始终包含的 `load_skill`。不写 `tools` 则 LLM 无工具可用。
4. 调用 `runtime.act(user_prompt, tools, model, temperature, max_turns, system_prompt=渲染后的prompt)`
5. **Function Calling 循环**：
   - LLM 返回工具调用 → 执行工具 → 结果返回 LLM → 循环
   - 达到 `max_turns - 1` 时注入 nudge 提示，强制最终文本输出
6. 记录到对话历史
7. 返回 LLM 最终响应文本

**消息结构**：
```json
[
  {"role": "system", "content": "<description>\n<skills>\n<rendered prompt>"},
  {"role": "user", "content": "llm act 表达式值"},
  {"role": "assistant", "content": null, "tool_calls": [...]},
  {"role": "tool", "content": "工具返回结果"},
  ...
  {"role": "assistant", "content": "最终文本响应"}
]
```

### 2. `llm if` — 分类路由

```helen
llm if "Classify the email priority" {
    case "urgent":
        call UrgentHandler(email)
    case "normal":
        call NormalHandler(email)
    default:
        print("Unknown priority")
}
```

**执行流程**：
1. 提取所有分支名：`["urgent", "normal", "default"]`
2. 获取对话历史上下文（`_get_context()`）
3. 调用 `runtime.route(description, branches, context)`
4. 验证返回值必须在预定义分支中
5. 执行匹配分支，无匹配则执行 default
6. 记录路由结果到历史

---

## 对话历史系统

### 自动记录

每次 LLM 交互自动记录到 `_history`：

```python
# llm act
self._add_to_history("user", prompt)
self._add_to_history("assistant", response.text)

# llm if
self._add_to_history("user", f"[route] {description}")
self._add_to_history("assistant", f"[routed to: {selected}]")
```

### `_get_context()` → conversation_summary

```python
def _get_context(self) -> str | None:
    if not self._history:
        return None
    return self._history_manager.build_conversation_summary(self._history)
```

- 调用 `HistoryManager.build_conversation_summary()` 生成摘要
- 摘要上限 **4096 tokens**（HLD 3.6.6）
- 格式：`[role] content` 每行
- 包含最新消息，截断最旧消息

### 手动操作

```python
interp.history           # 获取历史副本
interp.clear_history()   # 清空历史
interp._add_to_history("user", "custom message")  # 手动添加
```

---

## PromptBuilder 两层渐进式披露

### Tier 1: Skill Index

```
<available_skills>
  web-search: Search the web for information. Category: research
  code-review: Review code for quality and security. Category: dev
</available_skills>
```

- 轻量级：仅名称 + 描述 + 分类
- 注入到 System Prompt
- 让 LLM 知道有哪些技能可用

### Tier 2: 按需加载

当 LLM 需要某个技能的详细信息时，通过 `load_skill` 工具调用：

```json
{
  "name": "load_skill",
  "arguments": {"name": "web-search"}
}
```

返回完整的 SKILL.md 内容。

### 模板渲染

```python
def render(self, template: str, variables: dict[str, str]) -> str:
    """单次正则替换 {{var}}，防递归注入。"""
    # 仅替换 prompt 块中的模板
    # 变量值中包含 {{y}} 时不二次渲染
```

---

## StructuredOutput (M17)

LLM 路由使用 function calling schema 确保返回值合法：

```python
class StructuredOutput(Enum):
    """LLM 路由 function calling 枚举。"""
```

- LLM 返回必须匹配预定义的分支/选项 schema
- 解析失败 → 回退到 default
- 防止 LLM 返回意外值
