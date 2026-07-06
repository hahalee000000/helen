#!/usr/bin/env python3
"""简单测试 - 验证 Helen Python Bridge 是否工作"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 测试 1: Import hook 安装
print("测试 1: Import hook 安装")
from helen.python_bridge import install_import_hook
install_import_hook()
print("✓ Import hook 已安装\n")

# 测试 2: 导入 Helen 文件
print("测试 2: 导入 Helen 文件")
try:
    from translator import SumAgent
    print("✓ 成功导入 SumAgent\n")
except Exception as e:
    print(f"✗ 导入失败: {e}\n")
    sys.exit(1)

# 测试 3: 创建实例
print("测试 3: 创建实例")
try:
    agent = SumAgent()
    print(f"✓ 创建成功: {agent}\n")
except Exception as e:
    print(f"✗ 创建失败: {e}\n")
    sys.exit(1)

# 测试 4: 调用 agent
print("测试 4: 调用 agent")
try:
    result = agent(5, 3)
    print(f"✓ SumAgent(5, 3) = {result}\n")
except Exception as e:
    print(f"✗ 调用失败: {e}\n")
    sys.exit(1)

print("=== 所有测试通过 ===")
