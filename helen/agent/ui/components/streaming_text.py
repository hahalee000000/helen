"""流式文本显示 - 支持 Markdown 渲染"""

import time
from rich.markdown import Markdown
from rich.text import Text


class StreamingText:
    """流式文本缓冲区，支持 Markdown 渲染"""

    def __init__(self, debounce_ms: int = 200):
        self.buffer = []
        self.last_render_time = 0
        self.debounce_ms = debounce_ms
        self._cached_render = None
        self._dirty = True

    def append(self, text: str):
        """追加文本"""
        self.buffer.append(text)
        self._dirty = True

    def reset(self):
        """清空缓冲区"""
        self.buffer.clear()
        self._cached_render = None
        self._dirty = True

    def get_full_text(self) -> str:
        """获取完整文本"""
        return "".join(self.buffer)

    def render(self, force: bool = False):
        """
        渲染为 Rich 可渲染对象

        使用 debounce 避免频繁重新解析 Markdown
        """
        current_time = time.time() * 1000  # 转为毫秒

        # 如果没有变化且未强制刷新，返回缓存
        if not self._dirty and not force and self._cached_render is not None:
            if current_time - self.last_render_time < self.debounce_ms:
                return self._cached_render

        full_text = self.get_full_text()

        # 尝试渲染为 Markdown
        try:
            if full_text.strip():
                rendered = Markdown(full_text)
            else:
                rendered = Text("")
        except Exception:
            # 如果 Markdown 解析失败，回退到纯文本
            rendered = Text(full_text)

        self._cached_render = rendered
        self.last_render_time = current_time
        self._dirty = False

        return rendered

    def append_line(self, line: str):
        """追加一行（自动添加换行）"""
        self.append(line + "\n")

    def append_code_block(self, code: str, language: str = ""):
        """追加代码块"""
        self.append(f"\n```{language}\n{code}\n```\n")
