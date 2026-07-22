"""Python Import Hook - 支持直接导入 .helen 文件

Session ID 解析优先级（v1.24.1，Issue #16）：
    1. 显式 set_session_id() 设置的值（进程内动态控制，最高优先级）
    2. 环境变量 HELEN_SESSION_ID（跨进程重启恢复）
    3. memento 文件 .helen/current_session_id（相对 cwd，自动持久化）
    4. None（默认，创建新 session）

这确保 import hook 场景（隐式创建 Interpreter）也能复用历史 session，
保持 transcript 跨进程重启的连续性。
"""

import os
import sys
import importlib.abc
import importlib.util
from pathlib import Path


# 进程内显式设置的 session_id（由 set_session_id() 设置，优先级最高）
# 用 None 表示"未设置"，区别于空字符串（空字符串表示"强制新建 session"）
_session_id_override: str | None = None


def set_session_id(session_id: str | None) -> None:
    """显式设置 Python Bridge 使用的 session_id（v1.24.1，Issue #16）。

    优先级最高，覆盖环境变量和 memento 文件。必须在 import .helen 文件
    之前调用，因为 import hook 在那一刻创建 Interpreter。

    适用场景：一个进程同时服务多个用户/会话，每个用不同 session_id。
    环境变量（进程级单一值）无法满足这种动态多 session 需求。

    Args:
        session_id: 要复用的 session_id，或 None 清除覆盖（回退到环境变量/memento）

    Example:
        from helen.python_bridge import set_session_id
        set_session_id("session_1784706227_daa6c8d4")
        from chat_tui import TUIChatAgent  # 复用指定 session
    """
    global _session_id_override
    _session_id_override = session_id


def get_session_id() -> str | None:
    """获取当前会生效的 session_id（按优先级解析）。

    Returns:
        解析后的 session_id，或 None（将创建新 session）
    """
    return _detect_session_id()


def _detect_session_id() -> str | None:
    """按优先级检测 session_id（v1.24.1，Issue #16）。

    优先级：
        1. set_session_id() 显式设置（_session_id_override）
        2. 环境变量 HELEN_SESSION_ID
        3. memento 文件 .helen/current_session_id（相对 cwd）
        4. None

    Returns:
        session_id 字符串，或 None
    """
    # 1. 显式 set_session_id()（最高优先级）
    if _session_id_override is not None:
        return _session_id_override

    # 2. 环境变量
    env_sid = os.environ.get("HELEN_SESSION_ID")
    if env_sid:
        return env_sid

    # 3. memento 文件（相对 cwd）
    memento = Path.cwd() / ".helen" / "current_session_id"
    if memento.exists():
        sid = memento.read_text(encoding="utf-8").strip()
        if sid:
            return sid

    # 4. 默认：None（创建新 session）
    return None


class HelenMetaPathFinder(importlib.abc.MetaPathFinder):
    """查找 .helen 文件的 meta path finder"""
    
    def find_spec(self, fullname, path, target=None):
        """查找模块规范"""
        # 只处理模块名（不包含包路径）
        module_name = fullname.split('.')[-1]
        
        # 搜索路径
        search_paths = path if path else sys.path
        
        for search_path in search_paths:
            try:
                search_path = Path(search_path)
                helen_file = search_path / f"{module_name}.helen"
                
                if helen_file.exists():
                    # 创建模块规范
                    loader = HelenLoader(str(helen_file))
                    return importlib.util.spec_from_loader(
                        fullname, 
                        loader,
                        origin=str(helen_file)
                    )
            except Exception:
                continue
        
        return None


class HelenLoader(importlib.abc.Loader):
    """加载 .helen 文件的 loader"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def create_module(self, spec):
        """创建模块对象"""
        return None  # 使用默认模块创建
    
    def exec_module(self, module):
        """执行模块（加载 Helen agent 和 function）"""
        from helen.core.errors import ErrorReporter
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.core.ast import AgentDeclNode, FunctionDeclNode
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.interpreter import Interpreter
        from helen.runtime.import_resolver import ImportResolver
        from .agent_wrapper import HelenAgentWrapper
        from .function_wrapper import HelenFunctionWrapper

        # 1. 解析 Helen 文件
        with open(self.file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        helen_file = str(Path(self.file_path).resolve())
        errors = ErrorReporter()
        base_dir = str(Path(helen_file).parent)

        scanner = Scanner(source=code, file=helen_file)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()

        if errors.has_errors:
            raise RuntimeError(
                f"Failed to parse '{helen_file}': "
                + "; ".join(e.message for e in errors.errors)
            )

        analyzer = SemanticAnalyzer(errors, base_dir=base_dir)
        analyzer.analyze(program)

        if errors.has_errors:
            raise RuntimeError(
                f"Failed to analyze '{helen_file}': "
                + "; ".join(e.message for e in errors.errors)
            )

        # 2. 创建共享解释器并执行（注册所有 agent 和 function）
        # v1.24.1 (Issue #16): 支持复用历史 session，保持 transcript 跨重启连续性
        session_id = _detect_session_id()
        interpreter = Interpreter(
            errors=errors,
            import_resolver=ImportResolver(base_dir=base_dir),
            session_id=session_id,
        )
        interpreter.interpret(program)

        if errors.has_errors:
            raise RuntimeError(
                f"Failed to execute '{helen_file}': "
                + "; ".join(e.message for e in errors.errors)
            )

        # 3. 提取并暴露所有 agent
        for stmt in program.statements:
            if isinstance(stmt, AgentDeclNode):
                agent_name = stmt.name

                # 动态创建 Python 类（共享解释器）
                def make_init(name, file, interp):
                    def __init__(self, interpreter=interp):
                        HelenAgentWrapper.__init__(self, name, file, interpreter)
                    return __init__

                agent_class = type(
                    agent_name,
                    (HelenAgentWrapper,),
                    {
                        '__init__': make_init(agent_name, helen_file, interpreter),
                        '__module__': __name__,
                        '__doc__': getattr(stmt, 'description', f"Helen agent: {agent_name}"),
                    }
                )
                setattr(module, agent_name, agent_class)

        # 4. 提取并暴露所有顶层 function（v1.23.6+）
        for func_name, func_decl in interpreter._functions.items():
            # 包装为 Python 可调用对象（共享解释器）
            wrapper = HelenFunctionWrapper(func_name, helen_file, interpreter=interpreter)
            setattr(module, func_name, wrapper)

        # 添加模块元数据
        module.__file__ = helen_file
        module.__loader__ = self
        module.__helen_file__ = helen_file
        module.__interpreter__ = interpreter  # 暴露解释器供高级用法使用


def install_import_hook():
    """安装 Helen import hook"""
    # 检查是否已安装
    for finder in sys.meta_path:
        if isinstance(finder, HelenMetaPathFinder):
            return  # 已安装
    
    # 安装 hook
    sys.meta_path.insert(0, HelenMetaPathFinder())


def uninstall_import_hook():
    """卸载 Helen import hook"""
    sys.meta_path[:] = [
        finder for finder in sys.meta_path 
        if not isinstance(finder, HelenMetaPathFinder)
    ]
