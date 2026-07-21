"""Python Import Hook - 支持直接导入 .helen 文件"""

import sys
import importlib.abc
import importlib.util
from pathlib import Path


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
        interpreter = Interpreter(
            errors=errors,
            import_resolver=ImportResolver(base_dir=base_dir),
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
