"""交互式输入处理 - 支持 ESC 中止和斜杠命令"""

from typing import Callable, Optional

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.filters import Condition
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False


class InputHandler:
    """交互式输入处理器"""

    def __init__(self, abort_callback: Optional[Callable] = None):
        """
        初始化输入处理器

        Args:
            abort_callback: ESC 键触发时的回调函数
        """
        self.abort_callback = abort_callback
        self.history = []

        if PROMPT_TOOLKIT_AVAILABLE:
            self.session = PromptSession()
            self.kb = KeyBindings()
            self._setup_keybindings()
        else:
            self.session = None
            self.kb = None

    def _setup_keybindings(self):
        """设置快捷键绑定"""
        if not self.kb:
            return

        @self.kb.add('escape')
        def _(event):
            """ESC 键中止 — 取消输入并触发回调"""
            if self.abort_callback:
                self.abort_callback()
            # 退出输入，返回 None 表示 ESC 取消
            event.app.exit(result=None)

    def get_input(self, prompt: str = "❯ ") -> Optional[str]:
        """
        获取用户输入

        Args:
            prompt: 输入提示符

        Returns:
            用户输入的文本，如果取消则返回 None
        """
        if PROMPT_TOOLKIT_AVAILABLE and self.session:
            try:
                user_input = self.session.prompt(
                    prompt,
                    key_bindings=self.kb
                )
                # 添加到历史（检查 None）
                if user_input is not None and user_input.strip():
                    self.history.append(user_input)
                return user_input
            except (EOFError, KeyboardInterrupt):
                return None
        else:
            # 回退到标准 input
            try:
                user_input = input(prompt)
                if user_input is not None and user_input.strip():
                    self.history.append(user_input)
                return user_input
            except (EOFError, KeyboardInterrupt):
                return None

    def get_confirmation(self, prompt: str = "确认？(y/n) ") -> bool:
        """
        获取用户确认

        Args:
            prompt: 确认提示

        Returns:
            用户是否确认
        """
        response = self.get_input(prompt)
        if response is None:
            return False
        return response.strip().lower() in ('y', 'yes', '是')

    def get_history(self):
        """获取输入历史"""
        return self.history.copy()

    def clear_history(self):
        """清空历史"""
        self.history.clear()


# ── Helen FFI 入口 ──────────────────────────────────────────────
# 供 Helen ui_bridge.helen 调用的顶层辅助函数

# 模块级 abort 标志（ESC 触发）
_esc_abort_flag = False


def _on_esc_abort():
    """ESC 回调：设置模块级 abort 标志"""
    global _esc_abort_flag
    _esc_abort_flag = True


def helen_get_input(prompt: str) -> dict:
    """供 Helen 调用的输入函数。

    Returns:
        dict: {"text": str, "aborted": bool}
        - text: 用户输入的文本（ESC 取消时为空字符串）
        - aborted: 是否因 ESC 而取消
    """
    global _esc_abort_flag
    _esc_abort_flag = False  # 每次调用前重置

    handler = InputHandler(abort_callback=_on_esc_abort)
    text = handler.get_input(prompt)

    result = {
        "text": text if text is not None else "",
        "aborted": _esc_abort_flag or (text is None)
    }
    return result


def helen_check_esc_abort() -> bool:
    """检查 ESC abort 标志（供 Helen 查询）"""
    return _esc_abort_flag


def helen_clear_esc_abort():
    """清除 ESC abort 标志"""
    global _esc_abort_flag
    _esc_abort_flag = False
