"""装饰器 - 提供 Pythonic 的 Helen 集成方式"""

from typing import Callable, Any
from functools import wraps


def helen_agent(helen_file: str, agent_name: str = None):
    """
    装饰器：将 Python 函数包装为 Helen agent 调用
    
    Args:
        helen_file: Helen 文件路径
        agent_name: Agent 名称（默认使用函数名）
    
    Returns:
        装饰后的函数
    
    Example:
        @helen_agent("translator.helen", "TranslatorAgent")
        def translate(text: str, target: str) -> str:
            pass
        
        result = translate("Hello", "French")
    """
    def decorator(func: Callable) -> Callable:
        # 获取 agent 名称
        name = agent_name or func.__name__
        
        # 延迟加载 agent
        agent_wrapper = None
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal agent_wrapper
            
            # 首次调用时加载 agent
            if agent_wrapper is None:
                from .agent_wrapper import HelenAgentWrapper
                agent_wrapper = HelenAgentWrapper(name, helen_file)
            
            # 调用 agent
            return agent_wrapper(*args, **kwargs)
        
        # 添加元数据
        wrapper.__helen_file__ = helen_file
        wrapper.__helen_agent__ = name
        
        return wrapper
    
    return decorator


def helen_module(helen_file: str):
    """
    装饰器：将整个模块包装为 Helen agents 集合
    
    Args:
        helen_file: Helen 文件路径
    
    Returns:
        模块装饰器
    
    Example:
        @helen_module("agents.helen")
        class Agents:
            pass
        
        agents = Agents()
        result = agents.TranslatorAgent("Hello", "French")
    """
    def decorator(cls):
        # 延迟加载 agents
        _agents_cache = {}
        
        def __init__(self):
            from .agent_wrapper import generate_python_classes
            agents = generate_python_classes(helen_file)
            _agents_cache.update(agents)
        
        def __getattr__(self, name):
            if name in _agents_cache:
                return _agents_cache[name]()
            raise AttributeError(f"Module has no agent '{name}'")
        
        cls.__init__ = __init__
        cls.__getattr__ = __getattr__
        cls.__helen_file__ = helen_file
        
        return cls
    
    return decorator
