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
        """执行模块（加载 Helen agent）"""
        from .agent_wrapper import generate_python_classes
        
        # 解析 Helen 文件并生成 Python 类
        classes = generate_python_classes(self.file_path)
        
        # 将类添加到模块
        for class_name, agent_class in classes.items():
            setattr(module, class_name, agent_class)
        
        # 添加模块元数据
        module.__file__ = self.file_path
        module.__loader__ = self
        module.__helen_file__ = self.file_path


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
