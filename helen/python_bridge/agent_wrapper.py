"""Helen Agent 包装器 - 将 Helen agent 包装为 Python 类"""

from typing import Any, Dict, List
from pathlib import Path


class HelenAgentWrapper:
    """Helen Agent 的 Python 包装器"""
    
    def __init__(self, agent_name: str, helen_file: str, interpreter=None):
        """
        初始化包装器
        
        Args:
            agent_name: Agent 名称
            helen_file: Helen 文件路径
            interpreter: 可选的解释器实例（用于共享）
        """
        self.agent_name = agent_name
        self.helen_file = str(Path(helen_file).resolve())
        
        # 初始化或复用解释器
        if interpreter is None:
            from helen.interpreter import Interpreter
            self.interpreter = Interpreter()
            self._load_agent()
        else:
            self.interpreter = interpreter
        
        # 获取 agent 声明
        self.agent_decl = self._get_agent_decl()
        
        # 缓存参数信息
        self._params = self._extract_params()
    
    def _load_agent(self):
        """加载 Helen agent"""
        # 读取文件
        with open(self.helen_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 词法分析
        from helen.core.lexer import Scanner
        scanner = Scanner(code)
        tokens = scanner.scan_all()
        
        # 语法分析
        from helen.core.parser import Parser
        parser = Parser(tokens)
        program = parser.parse()
        
        # 执行
        self.interpreter.interpret(program)
    
    def _get_agent_decl(self):
        """获取 agent 声明"""
        # 从解释器的 _agents 字典中获取
        if hasattr(self.interpreter, '_agents') and self.agent_name in self.interpreter._agents:
            return self.interpreter._agents[self.agent_name]
        raise ValueError(f"Agent '{self.agent_name}' not found")
    
    def _extract_params(self) -> List[Dict[str, Any]]:
        """提取参数信息"""
        params = []
        for param in self.agent_decl.params:
            params.append({
                'name': param.name,
                'type': getattr(param, 'type_annotation', None),
                'default': getattr(param, 'default_value', None),
            })
        return params
    
    def __call__(self, *args, **kwargs) -> Any:
        """
        调用 agent
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Agent 执行结果
        """
        # 构建参数映射
        helen_args = {}
        
        # 处理位置参数
        for i, arg in enumerate(args):
            if i >= len(self._params):
                raise TypeError(
                    f"{self.agent_name}() takes {len(self._params)} "
                    f"positional arguments but {len(args)} were given"
                )
            param_name = self._params[i]['name']
            helen_args[param_name] = arg
        
        # 处理关键字参数
        helen_args.update(kwargs)
        
        # 验证参数
        self._validate_args(helen_args)
        
        # 调用 agent
        result = self.interpreter._call_agent(self.agent_decl, helen_args)
        
        # 转换返回值
        return self._convert_result(result)
    
    async def async_call(self, *args, **kwargs) -> Any:
        """
        异步调用 agent
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Agent 执行结果
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self, *args, **kwargs)
    
    def _validate_args(self, args: Dict[str, Any]):
        """验证参数"""
        param_names = {p['name'] for p in self._params}
        
        # 检查未知参数
        for arg_name in args:
            if arg_name not in param_names:
                raise TypeError(
                    f"{self.agent_name}() got an unexpected keyword argument '{arg_name}'"
                )
        
        # 检查必需参数
        for param in self._params:
            if param['name'] not in args and param['default'] is None:
                raise TypeError(
                    f"{self.agent_name}() missing required argument: '{param['name']}'"
                )
    
    def _convert_result(self, result: Any) -> Any:
        """转换 Helen 结果到 Python"""
        from .type_converter import helen_to_python
        return helen_to_python(result)
    
    def __repr__(self) -> str:
        return f"<HelenAgent '{self.agent_name}' from {self.helen_file}>"


def generate_python_classes(helen_file: str, interpreter=None) -> Dict[str, type]:
    """
    从 Helen 文件生成 Python 类
    
    Args:
        helen_file: Helen 文件路径
        interpreter: 可选的解释器实例
    
    Returns:
        类名字典 {agent_name: agent_class}
    """
    # 解析 Helen 文件
    with open(helen_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # 词法分析
    from helen.core.lexer import Scanner
    scanner = Scanner(code)
    tokens = scanner.scan_all()
    
    # 语法分析
    from helen.core.parser import Parser
    from helen.core.ast import AgentDeclNode
    parser = Parser(tokens)
    program = parser.parse()
    
    # 提取所有 agent 声明
    agents = {}
    for stmt in program.statements:
        # 检查是否是 AgentDeclNode
        if isinstance(stmt, AgentDeclNode):
            agent_name = stmt.name
            
            # 动态创建 Python 类
            def make_init(agent_name, helen_file, interpreter):
                def __init__(self, interpreter=interpreter):
                    HelenAgentWrapper.__init__(
                        self, 
                        agent_name, 
                        helen_file,
                        interpreter
                    )
                return __init__
            
            # 创建类
            agent_class = type(
                agent_name,
                (HelenAgentWrapper,),
                {
                    '__init__': make_init(agent_name, helen_file, interpreter),
                    '__module__': __name__,
                    '__doc__': getattr(stmt, 'description', f"Helen agent: {agent_name}"),
                }
            )
            
            agents[agent_name] = agent_class
    
    return agents
