"""Helen Function Wrapper - 从 Python 调用 Helen 函数"""

from typing import Any, List
from pathlib import Path


class HelenFunctionWrapper:
    """Helen 函数的 Python 包装器"""

    def __init__(self, func_name: str, helen_file: str, interpreter=None):
        """
        初始化包装器

        Args:
            func_name: 函数名称
            helen_file: Helen 文件路径
            interpreter: 可选的解释器实例（用于共享）
        """
        self.func_name = func_name
        self.helen_file = str(Path(helen_file).resolve())

        if interpreter is None:
            self.interpreter = None
            self._load_helen_file()
        else:
            self.interpreter = interpreter

        # 获取函数声明
        self.func_decl = self._get_func_decl()

    def _load_helen_file(self):
        """加载 Helen 文件"""
        from helen.core.errors import ErrorReporter
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.interpreter import Interpreter
        from helen.runtime.import_resolver import ImportResolver

        with open(self.helen_file, 'r', encoding='utf-8') as f:
            code = f.read()

        errors = ErrorReporter()
        base_dir = str(Path(self.helen_file).parent)

        scanner = Scanner(source=code, file=self.helen_file)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()

        if errors.has_errors:
            raise RuntimeError(
                f"Failed to parse '{self.helen_file}': "
                + "; ".join(e.message for e in errors.errors)
            )

        analyzer = SemanticAnalyzer(errors, base_dir=base_dir)
        analyzer.analyze(program)

        if errors.has_errors:
            raise RuntimeError(
                f"Failed to analyze '{self.helen_file}': "
                + "; ".join(e.message for e in errors.errors)
            )

        self.interpreter = Interpreter(
            errors=errors,
            import_resolver=ImportResolver(base_dir=base_dir),
        )
        self.interpreter.interpret(program)

        if errors.has_errors:
            raise RuntimeError(
                f"Failed to execute '{self.helen_file}': "
                + "; ".join(e.message for e in errors.errors)
            )

    def _get_func_decl(self):
        """获取函数声明"""
        if self.func_name in self.interpreter._functions:
            return self.interpreter._functions[self.func_name]
        raise ValueError(f"Function '{self.func_name}' not found in {self.helen_file}")

    def __call__(self, *args, **kwargs) -> Any:
        """
        调用函数

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        from .type_converter import helen_to_python

        # 构建完整参数列表
        param_names = [param.name for param in self.func_decl.params]
        call_args = []

        # 处理位置参数
        for i, arg in enumerate(args):
            if i >= len(param_names):
                raise TypeError(
                    f"{self.func_name}() takes {len(param_names)} positional arguments "
                    f"but {len(args)} were given"
                )
            call_args.append(arg)

        # 处理关键字参数
        for param_name, value in kwargs.items():
            if param_name not in param_names:
                raise TypeError(
                    f"{self.func_name}() got an unexpected keyword argument '{param_name}'"
                )
            param_index = param_names.index(param_name)
            if param_index < len(call_args):
                raise TypeError(
                    f"{self.func_name}() got multiple values for argument '{param_name}'"
                )
            # 扩展参数列表到足够长度
            while len(call_args) <= param_index:
                call_args.append(None)
            call_args[param_index] = value

        result = self.interpreter._call_function(self.func_decl, call_args)
        return helen_to_python(result)

    def __repr__(self) -> str:
        return f"<HelenFunction '{self.func_name}' from {self.helen_file}>"


def load_helen_functions(helen_file: str, interpreter=None) -> dict:
    """
    从 Helen 文件加载所有函数

    Args:
        helen_file: Helen 文件路径
        interpreter: 可选的解释器实例

    Returns:
        函数字典 {func_name: HelenFunctionWrapper}
    """
    from helen.core.errors import ErrorReporter
    from helen.core.lexer import Scanner
    from helen.core.parser import Parser
    from helen.semantic.analyzer import SemanticAnalyzer
    from helen.interpreter import Interpreter
    from helen.runtime.import_resolver import ImportResolver

    helen_file = str(Path(helen_file).resolve())

    with open(helen_file, 'r', encoding='utf-8') as f:
        code = f.read()

    errors = ErrorReporter()
    base_dir = str(Path(helen_file).parent)

    scanner = Scanner(source=code, file=helen_file)
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()

    analyzer = SemanticAnalyzer(errors, base_dir=base_dir)
    analyzer.analyze(program)

    if interpreter is None:
        interpreter = Interpreter(
            errors=errors,
            import_resolver=ImportResolver(base_dir=base_dir),
        )
        interpreter.interpret(program)

    # 提取所有函数
    functions = {}
    for name, func_decl in interpreter._functions.items():
        wrapper = HelenFunctionWrapper(name, helen_file, interpreter=interpreter)
        functions[name] = wrapper

    return functions
