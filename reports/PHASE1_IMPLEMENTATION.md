# Phase 1: 消息分类与选择性清除

**状态**: 实施中
**优先级**: P0

## 契约设计

### 1. 扩展 Message 类

在 `helen/runtime/history.py` 中扩展 `Message` dataclass：

```python
@dataclass
class Message:
    role: str
    content: str | list
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    
    # 新增字段：消息分类
    message_type: str | None = None  # 自动推断的消息类型
    priority: int = 50               # 优先级 (1-100, 越高越重要)
    compressed: bool = False         # 是否已被压缩
    _token_count: int | None = None  # token 数缓存
    _model: str | None = None        # 模型名称
```

### 2. 消息类型常量

```python
# 消息类型
MSG_SYSTEM = "system"
MSG_USER = "user"
MSG_ASSISTANT = "assistant"
MSG_ASSISTANT_TOOL_CALL = "assistant_tool_call"
MSG_TOOL = "tool"

# 优先级常量
PRIORITY_CRITICAL = 100  # 系统提示、用户请求
PRIORITY_HIGH = 80       # 助手回复、工具调用
PRIORITY_MEDIUM = 50     # 工具结果
PRIORITY_LOW = 20        # 旧的、可压缩的消息
```

### 3. 新增 API

在 `helen/stdlib/context.py` 中添加：

```python
def _classify_message(message: dict) -> dict:
    """
    为消息添加分类元数据
    
    Args:
        message: 消息字典
    
    Returns:
        带有 message_type 和 priority 的消息字典
    """

def _compress_context_target(target: str, keep_recent: int = 5) -> dict:
    """
    按目标类型压缩上下文
    
    Args:
        target: 压缩目标
            - "tool_results": 清除旧的工具结果
            - "stale_turns": 丢弃过时的轮次
        keep_recent: 保留最近 N 条消息
    
    Returns:
        压缩结果统计
    """
```

### 4. 测试文件

创建 `tests/stdlib/test_context_phase1.py`，包含：

1. `test_classify_system_message` - 系统消息分类
2. `test_classify_user_message` - 用户消息分类
3. `test_classify_assistant_message` - 助手消息分类
4. `test_classify_assistant_tool_call` - 助手工具调用分类
5. `test_classify_tool_result` - 工具结果分类
6. `test_compress_tool_results` - 压缩工具结果
7. `test_compress_stale_turns` - 压缩过时轮次
8. `test_compress_keeps_recent` - 保留最近消息

## 实施步骤

1. 扩展 Message 类（添加字段）
2. 实现消息分类函数
3. 实现选择性压缩函数
4. 编写测试
5. 验证通过
