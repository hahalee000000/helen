"""
流式事件发射器 - 连接 Helen 和 Python TUI

Helen 端通过 Python FFI 调用 emit_stream_event()，
将流式事件实时传递到 Python TUI 的回调函数。
"""

import sys
from typing import Callable, Optional

# 全局回调函数（由 chat_actor.helen 注册）
_stream_callback: Optional[Callable[[str, str], None]] = None


def register_stream_callback(callback: Callable[[str, str], None]):
    """
    注册流式事件回调函数

    Args:
        callback: 回调函数，签名 callback(event_type: str, data: str)
                  event_type 可以是：
                  - "llm_chunk": LLM 流式输出片段
                  - "llm_complete": LLM 输出完成
                  - "agent_start": Agent 开始执行
                  - "agent_end": Agent 执行完成
                  - "phase_start": 阶段开始
                  - "status": 状态消息
    """
    global _stream_callback
    _stream_callback = callback


def emit_stream_event(event_type: str, data: str):
    """
    发射流式事件到 Python TUI

    由 Helen 端通过 Python FFI 调用

    Args:
        event_type: 事件类型
        data: 事件数据
    """
    global _stream_callback
    if _stream_callback:
        try:
            _stream_callback(event_type, data)
        except Exception as e:
            print(f"⚠ 流式事件处理失败: {e}", file=sys.stderr)
    else:
        # 无回调注册时静默忽略（斜杠命令、热重载期间正常）
        pass


def clear_stream_callback():
    """清除流式事件回调"""
    global _stream_callback
    _stream_callback = None


# ── 中断支持（cancel flag）──────────────────────────────────────
# 用于从 Python 端（Web UI / TUI）请求中断正在进行的 Helen LLM 流
# Helen 端通过 FFI 调用 is_cancel_requested() 检查此 flag，
# 若被设置则调用 Helen stdlib cancel_all_llm_calls() 中断流式 LLM
#
# ── 生命周期约定 ──
# 1. request_cancel() 由 Python 端（WebUI cancel handler）设置
# 2. clear_cancel() 由以下位置清理（至少一个必须触发）：
#    a. Helen actor 的 _actor_chunks_cb / _actor_tool_end_cb 回调
#    b. do_streaming() / do_goal_streaming() 的 finally 块
#    c. WebUI cancel handler 中 stream_task.cancel() 之后
#    d. /compress 命令执行前
# 3. v1.46.12: 自动超时——如果 flag 设置后 30s 内未被处理（actor 崩溃导致
#    所有清理路径都未触发），is_cancel_requested() 会自动清除 flag。
#    这修复了 v1.45 的已知 bug：flag 永远卡在 True 导致后续 LLM 调用被静默取消。

import time as _time

_cancel_requested: bool = False
_cancel_requested_at: float = 0.0
_CANCEL_FLAG_TIMEOUT: float = 30.0  # 自动清除超时（秒）


def is_cancel_requested() -> bool:
    """检查是否已请求中断（由 Helen 端通过 FFI 调用）

    v1.46.12: 自动超时——如果 flag 设置超过 _CANCEL_FLAG_TIMEOUT 秒，
    自动清除并返回 False。
    """
    global _cancel_requested, _cancel_requested_at
    if _cancel_requested and (_time.monotonic() - _cancel_requested_at) > _CANCEL_FLAG_TIMEOUT:
        _cancel_requested = False
        _cancel_requested_at = 0.0
    return _cancel_requested


def request_cancel():
    """请求中断当前 LLM 流（由 Python 端调用，如 Web UI 的 cancel 处理）"""
    global _cancel_requested, _cancel_requested_at
    _cancel_requested = True
    _cancel_requested_at = _time.monotonic()


def clear_cancel():
    """清除中断标志。

    调用时机：
    - do_streaming / do_goal_streaming finally 块（兜底）
    - WebUI cancel handler（cancel 后立即清理）
    - /compress 命令执行前（防御性清理）
    - Actor llm act 完成/出错后（防御性清理）
    """
    global _cancel_requested, _cancel_requested_at
    _cancel_requested = False
    _cancel_requested_at = 0.0
