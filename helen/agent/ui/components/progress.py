"""进度指示器"""

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text


class ProgressIndicator:
    """任务进度指示器"""

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        self.tasks = {}

    def add_task(self, task_id: str, description: str, total: int = 100) -> int:
        """添加任务"""
        task = self.progress.add_task(description, total=total)
        self.tasks[task_id] = task
        return task

    def update_task(self, task_id: str, completed: int = None, advance: int = None):
        """更新任务进度"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if completed is not None:
                self.progress.update(task, completed=completed)
            elif advance is not None:
                self.progress.update(task, advance=advance)

    def finish_task(self, task_id: str):
        """完成任务"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            self.progress.update(task, completed=100)

    def render(self) -> Progress:
        """渲染进度条"""
        return self.progress

    def render_simple(self, description: str, current: int, total: int) -> Text:
        """渲染简单进度（不使用 Progress 组件）"""
        text = Text()
        percentage = (current / total * 100) if total > 0 else 0

        text.append(f"{description}: ", style="bold")
        text.append(f"{current}/{total}", style="cyan")
        text.append(f" ({percentage:.1f}%)", style="dim")

        return text
