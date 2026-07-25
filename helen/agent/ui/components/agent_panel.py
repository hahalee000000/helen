"""Agent 状态面板 - 显示 Agent 执行状态"""

import time
from rich.text import Text
from rich.spinner import Spinner


class AgentPanel:
    """Agent 执行状态面板"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.start_time = None
        self.end_time = None
        self.status = "pending"  # "pending" | "running" | "finished" | "error"
        self.result = None

    def start(self):
        """标记 Agent 开始执行"""
        self.start_time = time.time()
        self.status = "running"

    def finish(self, duration_ms: int = None):
        """标记 Agent 执行完成"""
        self.end_time = time.time()
        self.status = "finished"
        if duration_ms is not None:
            self._duration_ms = duration_ms
        else:
            self._duration_ms = int((self.end_time - self.start_time) * 1000)

    def error(self, error_msg: str):
        """标记 Agent 执行出错"""
        self.end_time = time.time()
        self.status = "error"
        self.result = error_msg

    def is_finished(self) -> bool:
        """检查是否已完成"""
        return self.status in ("finished", "error")

    def get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        if self.start_time is None:
            return 0.0
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def render(self) -> Text:
        """渲染为 Rich Text"""
        text = Text()

        # 状态图标
        if self.status == "pending":
            text.append("⎿  ", style="dim")
            text.append(self.agent_name, style="bold")
            text.append(" 等待中", style="dim")
        elif self.status == "running":
            text.append("⎿  ", style="bold blue")
            text.append(self.agent_name, style="bold blue")
            text.append(" 执行中", style="blue")
            # 显示时间
            elapsed = self.get_elapsed_time()
            text.append(f" ({elapsed:.1f}s)", style="dim blue")
        elif self.status == "finished":
            text.append("⎿  ", style="bold green")
            text.append("✓ ", style="bold green")
            text.append(self.agent_name, style="green")
            # 显示总时间
            if hasattr(self, '_duration_ms'):
                duration_s = self._duration_ms / 1000.0
                text.append(f" ({duration_s:.1f}s)", style="dim green")
        elif self.status == "error":
            text.append("⎿  ", style="bold red")
            text.append("✗ ", style="bold red")
            text.append(self.agent_name, style="red")
            if self.result:
                text.append(f": {self.result}", style="dim red")

        return text
