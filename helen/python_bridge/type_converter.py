"""类型转换器 - Python 和 Helen 类型之间的自动转换"""

from typing import Any

from helen.runtime.media import MediaPart


def python_to_helen(value: Any) -> Any:
    """
    将 Python 值转换为 Helen 值

    Args:
        value: Python 值

    Returns:
        Helen 兼容的值
    """
    # 基本类型直接返回
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value

    # MediaPart 直接传递（v1.17 多模态支持）
    if isinstance(value, MediaPart):
        return value

    # 列表转换
    if isinstance(value, (list, tuple)):
        return [python_to_helen(item) for item in value]

    # 字典转换
    if isinstance(value, dict):
        return {str(k): python_to_helen(v) for k, v in value.items()}

    # 集合转换为列表
    if isinstance(value, set):
        return [python_to_helen(item) for item in sorted(value)]

    # 其他类型尝试转换为字符串
    return str(value)


def helen_to_python(value: Any) -> Any:
    """
    将 Helen 值转换为 Python 值

    Args:
        value: Helen 值

    Returns:
        Python 值
    """
    # 基本类型直接返回
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value

    # MediaPart 直接传递（v1.17 多模态支持）
    if isinstance(value, MediaPart):
        return value

    # 列表转换
    if isinstance(value, list):
        return [helen_to_python(item) for item in value]

    # 字典转换
    if isinstance(value, dict):
        return {k: helen_to_python(v) for k, v in value.items()}

    # 其他类型返回原始值
    return value


def convert_args(args: dict) -> dict:
    """
    转换参数字典
    
    Args:
        args: 参数字典
    
    Returns:
        转换后的参数字典
    """
    return {k: python_to_helen(v) for k, v in args.items()}
