#!/usr/bin/env python3
"""Helen Python Bridge 使用示例"""

import sys
from pathlib import Path

# 添加当前目录到路径，以便导入 translator.helen
sys.path.insert(0, str(Path(__file__).parent))

# 安装 import hook
from helen.python_bridge import install_import_hook
install_import_hook()

# 直接导入 Helen agent
from translator import SumAgent

def main():
    print("=== Helen Python Bridge 示例 ===\n")
    
    # 1. 基本调用
    print("1. 基本调用")
    agent = SumAgent()
    result = agent(10, 20)
    print(f"   SumAgent(10, 20) = {result}\n")
    
    # 2. 关键字参数
    print("2. 关键字参数")
    result = agent(a=15, b=25)
    print(f"   SumAgent(a=15, b=25) = {result}\n")
    
    # 3. 混合参数
    print("3. 混合参数")
    result = agent(30, b=40)
    print(f"   SumAgent(30, b=40) = {result}\n")
    
    # 4. 错误处理
    print("4. 错误处理")
    try:
        result = agent(10)  # 缺少参数
    except TypeError as e:
        print(f"   ✓ 捕获到预期错误: {e}\n")
    
    # 5. 多次调用
    print("5. 多次调用")
    results = [agent(i, i*2) for i in range(5)]
    print(f"   结果: {results}\n")
    
    print("=== 示例完成 ===")

if __name__ == "__main__":
    main()
