# Helen 上下文管理增强实施方案

> 使用契约-测试-实现模式，按顺序实施 5 个 Phase

**日期**：2026-07-06
**状态**：实施中
**模式**：Contract → Test (RED) → Implementation (GREEN) → Refactor

---

## 实施顺序（按依赖关系）

| 顺序 | Phase | 优先级 | 依赖 | 预计工作量 |
|------|-------|--------|------|-----------|
| 1 | Phase 5: Bug 修复 | P0 | 无 | 0.5 天 |
| 2 | Phase 1: 消息分类 | P0 | Phase 5 | 2 天 |
| 3 | Phase 2: 渐进压缩 | P0 | Phase 1 | 2 天 |
| 4 | Phase 3: LLM 压缩 | P1 | Phase 2 | 3 天 |
| 5 | Phase 4: 工作记忆 | P1 | Phase 2 | 3 天 |

---

## Phase 5: Bug 修复（基础）

### 契约（Contract）

#### Bug 1: `clear_context()` token 估算错误

**当前实现（错误）**：
```python
# context.py:67
total_chars = sum(len(msg.get("content", "")) for msg in _interpreter_history if isinstance(msg, dict))
```

**问题**：
- `_interpreter_history` 是 `list[Message]`，不是 `list[dict]`
- `Message` 是 dataclass，没有 `.get()` 方法
- 导致 `total_chars` 始终为 0

**契约（修复后）**：
```python
def _clear_context() -> dict:
    """清除对话上下文，返回清除的消息数和 token 数"""
    # 返回格式：
    # {
    #     "status": "ok" | "error",
    #     "cleared_messages": int,      # 清除的消息数
    #     "cleared_tokens": int,        # 清除的 token 数（使用 Message.token_count）
    #     "warning": str,               # 警告信息
    # }
```

#### Bug 2: `compress_context()` 类型错误

**当前实现（错误）**：
```python
# context.py:143
original_tokens = _interpreter_history_manager.estimate_tokens(_interpreter_history)
```

**问题**：
- `estimate_tokens()` 接受 `str` 参数，不是 `list[Message]`
- 导致类型错误或错误的 token 估算

**契约（修复后）**：
```python
def _compress_context(strategy: str = "auto") -> dict:
    """压缩对话上下文，返回压缩前后的统计信息"""
    # 返回格式：
    # {
    #     "status": "ok" | "error",
    #     "original_messages": int,     # 压缩前的消息数
    #     "compressed_messages": int,   # 压缩后的消息数
    #     "original_tokens": int,       # 压缩前的 token 数（sum of Message.token_count）
    #     "compressed_tokens": int,     # 压缩后的 token 数
    #     "strategy": str,              # 使用的压缩策略
    # }
```

### 测试（Test - RED 阶段）

**测试文件**：`tests/stdlib/test_context_bug_fixes.py`

**测试用例**：
1. `test_clear_context_returns_correct_token_count` - 验证 clear_context 返回正确的 token 数
2. `test_compress_context_returns_correct_token_count` - 验证 compress_context 返回正确的 token 数
3. `test_clear_context_with_message_objects` - 验证处理 Message 对象（不是 dict）
4. `test_compress_context_with_empty_history` - 验证空历史的行为

### 实现（Implementation - GREEN 阶段）

**修改文件**：`helen/stdlib/context.py`

**修复方案**：
1. Bug 1: 使用 `msg.token_count` 代替 `msg.get("content", "")`
2. Bug 2: 使用 `sum(msg.token_count for msg in history)` 计算总 token 数

---

## Phase 1: 消息分类与选择性清除

### 契约（Contract）

#### 消息类型扩展

**当前消息类型**：
```python
# history.py
@dataclass
class Message:
    role: str             # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: list[dict]
    tool_call_id: str | None
    _token_count: int
    _model: str | None
```

**扩展后（契约）**：
```python
@dataclass
class Message:
    role: str             # 保持原有 4 种
    content: str
    tool_calls: list[dict]
    tool_call_id: str | None
    _token_count: int
    _model: str | None
    
    # 新增：消息优先级分类
    _priority: int = 0    # 100=永不删除, 20=可清除
    _compressed: bool = False  # 是否已被压缩
    
    # 新增：消息子类型（用于选择性清除）
    @property
    def message_type(self) -> str:
        """推断消息子类型"""
        # "system", "user", "assistant_text", "assistant_tools", "tool_result"
        ...

# 优先级常量
ROLE_PRIORITY = {
    "system": 100,          # 永不删除
    "user": 90,             # 高优先级保留
    "assistant_text": 80,   # 助手文本回复
    "assistant_tools": 70,  # 工具调用决策（tool_use）
    "tool_result": 20,      # 工具返回数据（可清除）
}
```

#### 选择性清除 API

**新增 stdlib 函数**：
```helen
// 清除旧工具结果，保留动作历史
let status = compress_context(target="tool_results")
// 返回：{"status": "ok", "compressed": 8, "saved_tokens": 12000}

// 清除过时轮次
let status = compress_context(target="stale_turns", keep_recent=8)
// 返回：{"status": "ok", "removed_turns": 5, "saved_tokens": 8000}
```

**Python 实现契约**：
```python
def _compress_context_target(target: str, **kwargs) -> dict:
    """按目标类型压缩上下文"""
    # target 可选值：
    # - "tool_results": 清除旧工具结果，保留 tool_use 决策
    # - "stale_turns": 丢弃过时轮次
    # - "all": 传统压缩（保持兼容）
    #
    # 返回格式：
    # {
    #     "status": "ok" | "error",
    #     "target": str,
    #     "compressed": int,       # 压缩的消息数
    #     "saved_tokens": int,     # 节省的 token 数
    # }
```

### 测试（Test - RED 阶段）

**测试文件**：`tests/stdlib/test_context_message_classification.py`

**测试用例**：
1. `test_message_type_inference` - 验证消息类型推断
2. `test_message_priority_assignment` - 验证优先级分配
3. `test_compress_tool_results_preserves_tool_use` - 验证清除工具结果保留 tool_use
4. `test_compress_stale_turns_keeps_recent` - 验证丢弃过时轮次保留最近
5. `test_backward_compatibility_with_traditional_compress` - 验证向后兼容

### 实现（Implementation - GREEN 阶段）

**修改文件**：
- `helen/runtime/history.py` - 扩展 Message 类
- `helen/stdlib/context.py` - 新增按目标压缩函数
- `helen/stdlib/__init__.py` - 注册新函数

---

## Phase 2: 渐进式压缩管线

### 契约（Contract）

#### 五级压缩管线

**压缩阈值常量**：
```python
# history.py
COMPRESSION_THRESHOLDS = {
    "budget_reduction": 0.60,   # 60% - 替换大工具输出
    "snip": 0.70,               # 70% - 丢弃过时轮次
    "microcompact": 0.80,       # 80% - 清除旧工具结果
    "context_collapse": 0.90,   # 90% - 归档折叠
    "auto_compact": 0.95,       # 95% - LLM 语义压缩
}
```

**压缩管线 API**：
```python
def graduated_compress(history: list[Message], usage_ratio: float) -> tuple[list[Message], str]:
    """渐进式压缩 - cheapest move first
    
    Args:
        history: 对话历史
        usage_ratio: 当前使用率 (0.0 - 1.0)
    
    Returns:
        (compressed_history, layer_used)
        - compressed_history: 压缩后的历史
        - layer_used: 使用的压缩层
          "none" | "budget_reduction" | "snip" | "microcompact" | 
          "context_collapse" | "auto_compact"
    
    保证：
        - 每层只在更便宜的层不够用时才触发
        - 零成本层（Layer 1-4）不会调用 LLM
        - Layer 5 只在前面四层都不够时才调用 LLM
    """
```

**Agent 声明扩展**：
```helen
agent CodeReviewer {
    description "代码审查"
    model "qwen3.7-plus"
    max-turns 20
    
    // 新增：上下文配置块
    context {
        strategy "graduated"              // "traditional" | "graduated"
        budget-ratio 0.80                 // 历史占上下文窗口的比例
        preserve-actions true             // 保留 tool_use 决策
        max-tool-results 5                // 保留最近 N 个工具结果
        microcompact-threshold 0.80       // 80% 时开始清除旧结果
        auto-compact-threshold 0.95       // 95% 时 LLM 压缩
    }
    
    tools ["read_file", "shell_exec"]
    main {
        let review = llm act "审查这段代码"
        return review
    }
}
```

### 测试（Test - RED 阶段）

**测试文件**：`tests/runtime/test_graduated_compression.py`

**测试用例**：
1. `test_budget_reduction_replaces_large_outputs` - 验证 Layer 1 替换大输出
2. `test_snip_removes_stale_turns` - 验证 Layer 2 丢弃过时轮次
3. `test_microcompact_clears_old_tool_results` - 验证 Layer 3 清除旧工具结果
4. `test_context_collapse_creates_projection` - 验证 Layer 4 创建折叠视图
5. `test_auto_compact_uses_llm` - 验证 Layer 5 调用 LLM
6. `test_graduated_compress_escalates_correctly` - 验证渐进式升级
7. `test_zero_cost_layers_no_llm_call` - 验证零成本层不调用 LLM
8. `test_backward_compatibility_with_traditional_mode` - 验证向后兼容

### 实现（Implementation - GREEN 阶段）

**新增文件**：
- `helen/runtime/graduated_compression.py` - 压缩管线实现

**修改文件**：
- `helen/runtime/history.py` - 集成压缩管线
- `helen/interpreter/llm_mixin.py` - 在 `_add_to_history()` 后触发压缩
- `helen/core/ast.py` - 扩展 Agent 节点支持 context 配置

---

## Phase 3: LLM 语义压缩

### 契约（Contract）

#### LLM 摘要生成器

**API 契约**：
```python
class LLMSummarizer:
    """使用 LLM 生成对话摘要"""
    
    async def summarize(self, history: list[Message], target_tokens: int = 2000) -> str:
        """生成对话摘要
        
        Args:
            history: 对话历史
            target_tokens: 目标 token 数
        
        Returns:
            结构化摘要文本
        
        摘要格式：
            ## 任务目标
            [用户想要做什么]
            
            ## 关键决策
            [做出的重要选择和原因]
            
            ## 文件变更
            - path/to/file.py: [修改了什么]
            
            ## 已完成
            - [完成了什么]
            
            ## 待完成
            - [还需要做什么]
            
            ## 注意事项
            - [重要的约束、偏好、错误模式]
        
        保证：
            - 使用低温度（0.3）确保忠实摘要
            - 保留关键决策和文件修改
            - 丢弃重复试探和过时临时数据
        """
```

**stdlib 函数扩展**：
```helen
// 手动触发 LLM 压缩
let result = compress_context("llm_summarize")
// 返回：{
//     "status": "ok",
//     "original_tokens": 50000,
//     "compressed_tokens": 8000,
//     "strategy": "llm_summarize",
//     "summary_preview": "## 任务目标\n用户要求修复 auth.test.ts..."
// }
```

#### 60% 规则

**压缩后触发阈值**：
```
压缩后上下文 = 30% 容量
下次压缩触发 = 30% + 60% × 70% = 72% 容量
```

### 测试（Test - RED 阶段）

**测试文件**：`tests/runtime/test_llm_summarization.py`

**测试用例**：
1. `test_llm_summarizer_generates_structured_summary` - 验证生成结构化摘要
2. `test_llm_summarizer_preserves_key_decisions` - 验证保留关键决策
3. `test_llm_summarizer_uses_low_temperature` - 验证使用低温度
4. `test_60_percent_rule_triggers_correctly` - 验证 60% 规则
5. `test_compress_context_llm_summarize_strategy` - 验证 stdlib 函数

### 实现（Implementation - GREEN 阶段）

**新增文件**：
- `helen/runtime/llm_summarizer.py` - LLM 摘要生成器

**修改文件**：
- `helen/runtime/graduated_compression.py` - 集成 LLM 压缩
- `helen/stdlib/context.py` - 扩展 compress_context 支持 "llm_summarize"

---

## Phase 4: 上下文有效性提取（工作记忆）

### 契约（Contract）

#### 工作记忆数据结构

```python
@dataclass
class WorkingMemory:
    """工作记忆 - 当前任务的核心上下文"""
    
    task_description: str              # 当前任务描述
    active_files: list[str]            # 当前操作的文件（最近 10 个）
    recent_decisions: list[str]        # 最近的关键决策（最近 5 个）
    pending_todos: list[str]           # 待完成项
    error_history: list[dict]          # 最近的错误和修复
    
    # Token 预算
    max_tokens: int = 5000
    
    def to_context(self) -> str:
        """将工作记忆格式化为上下文"""
        # 输出格式：
        # ## 当前任务
        # [任务描述]
        #
        # ## 当前文件
        # - src/main.py
        # - src/utils.py
        #
        # ## 关键决策
        # - 使用渐进式压缩策略
        # - 保留 tool_use 决策
        #
        # ## 待完成
        # - [ ] 实现 Layer 3
        # - [ ] 编写测试
        #
        # ## 最近错误
        # - shell_exec 超时：修复了 timeout 参数
    
    def update(self, tool_call: dict, tool_result: dict) -> None:
        """根据工具调用更新工作记忆"""
        # 自动更新规则：
        # - read_file → 添加到 active_files
        # - write_file/patch_file → 添加到 recent_decisions
        # - shell_exec 失败 → 添加到 error_history
```

#### 三通道上下文构建

```python
def build_context(
    system_prompt: str,
    working_memory: WorkingMemory,
    history: list[Message],
    budget: dict  # {"system": 0.15, "working": 0.50, "history": 0.35}
) -> list[dict]:
    """构建三通道上下文
    
    通道 1 (15%): 系统指令
    通道 2 (50%): 工作记忆
    通道 3 (35%): 长期记忆（压缩后的历史）
    
    Returns:
        OpenAI 格式的消息列表
    """
```

**Agent 声明扩展**：
```helen
agent LongRunningCoder {
    description "长时间运行的编码 Agent"
    model "qwen3.7-plus"
    max-turns 50
    
    context {
        strategy "graduated"
        working-memory true             // 启用工作记忆
        working-memory-tokens 5000      // 工作记忆 token 预算
    }
    
    tools ["read_file", "write_file"]
    main {
        let result = llm act "实现这个功能"
        return result
    }
}
```

### 测试（Test - RED 阶段）

**测试文件**：`tests/runtime/test_working_memory.py`

**测试用例**：
1. `test_working_memory_tracks_active_files` - 验证跟踪活跃文件
2. `test_working_memory_tracks_recent_decisions` - 验证跟踪关键决策
3. `test_working_memory_tracks_errors` - 验证跟踪错误
4. `test_three_channel_context_building` - 验证三通道构建
5. `test_working_memory_token_budget` - 验证 token 预算控制
6. `test_working_memory_integration_with_agent` - 验证与 Agent 集成

### 实现（Implementation - GREEN 阶段）

**新增文件**：
- `helen/runtime/working_memory.py` - 工作记忆实现

**修改文件**：
- `helen/interpreter/llm_mixin.py` - 在工具调用后更新工作记忆
- `helen/interpreter/llm_mixin.py` - 在构建上下文时包含工作记忆
- `helen/core/ast.py` - 扩展 Agent 节点支持 working-memory 配置

---

## 实施检查清单

### Phase 5: Bug 修复 ✅
- [x] 修复 `clear_context()` token 估算（使用 Message._token_count）
- [x] 修复 `compress_context()` 类型错误（使用 Message._token_count 求和）
- [x] 编写测试验证修复（9 个测试）
- [x] 运行现有测试确保无回归

### Phase 1: 消息分类 ✅
- [x] 扩展 Message 类（添加 message_type、priority、compressed 字段）
- [x] 实现 `infer_message_type()` 方法
- [x] 实现 `assign_priority()` 方法
- [x] 实现 `classify_message()` stdlib 函数
- [x] 实现 `compress_context_target()` stdlib 函数
- [x] 编写测试验证分类和清除（12 个测试）
- [x] 确保向后兼容

### Phase 2: 渐进压缩 ✅
- [x] 实现五级压缩管线（graduated_compression.py）
- [x] 实现 Layer 1: Budget Reduction（替换大工具输出）
- [x] 实现 Layer 2: Snip（丢弃过时轮次）
- [x] 实现 Layer 3: Microcompact（清除旧工具结果）
- [x] 实现 Layer 4: Context Collapse（归档折叠）
- [x] 实现 Layer 5: Auto-Compact（LLM 压缩，Phase 3 完成）
- [x] 实现"cheapest move first"策略
- [x] 编写测试验证渐进式升级（16 个测试）
- [x] 确保零成本层不调用 LLM

### Phase 3: LLM 压缩 ✅
- [x] 实现 LLMSummarizer 类（llm_summarizer.py）
- [x] 实现结构化摘要生成
- [x] 实现 60% 规则（避免压缩后立即又触发）
- [x] 实现 auto_compact() 函数
- [x] 实现 fallback 摘要（LLM 失败时）
- [x] 编写测试验证摘要质量（9 个测试）

### Phase 4: 工作记忆 ✅
- [x] 实现 WorkingMemory 类（working_memory.py）
- [x] 实现自动更新规则（从工具调用推断）
- [x] 实现三通道上下文构建
- [x] 实现 token 估算
- [x] 实现列表限制（active_files: 10, decisions: 10, errors: 5）
- [x] 编写测试验证集成（17 个测试）
- [ ] 实现五级压缩管线
- [ ] 实现每层压缩逻辑
- [ ] 集成到 `_add_to_history()` 后触发
- [ ] 扩展 Agent 声明支持 context 配置
- [ ] 编写测试验证渐进式升级
- [ ] 确保零成本层不调用 LLM

### Phase 3: LLM 压缩
- [ ] 实现 LLMSummarizer 类
- [ ] 实现结构化摘要生成
- [ ] 实现 60% 规则
- [ ] 扩展 compress_context 支持 "llm_summarize"
- [ ] 编写测试验证摘要质量

### Phase 4: 工作记忆
- [ ] 实现 WorkingMemory 类
- [ ] 实现自动更新规则
- [ ] 实现三通道上下文构建
- [ ] 集成到 Agent 执行流程
- [ ] 扩展 Agent 声明支持 working-memory
- [ ] 编写测试验证集成

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Phase 2 复杂度高 | 高 | 先实现 Phase 1 和 Phase 5，验证基础 |
| LLM 摘要质量不稳定 | 中 | 使用低温度（0.3），多次测试 |
| 向后兼容问题 | 高 | 保留传统模式作为 fallback |
| 性能开销 | 中 | 监控每层压缩的耗时和 token 节省 |
| 测试覆盖不足 | 中 | 为每个 Phase 编写充分的单元测试 |

---

## 下一步行动

1. **立即开始 Phase 5**（Bug 修复）
   - 创建测试文件 `tests/stdlib/test_context_bug_fixes.py`
   - 编写 4 个测试用例（RED 阶段）
   - 修复 `context.py` 中的两个 bug（GREEN 阶段）
   - 运行测试验证通过

2. **然后依次实施 Phase 1-4**
   - 每个 Phase 都遵循契约-测试-实现模式
   - 每完成一个 Phase，运行全量测试确保无回归

3. **最后集成测试**
   - 编写端到端测试验证整个压缩管线
   - 测试长时间运行的 Agent 场景
   - 验证性能指标（压缩率、token 节省、信息损失）
