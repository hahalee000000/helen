#!/usr/bin/env python3
"""
从 skill 文档中提取 Helen 代码块并生成测试文件
"""

import re
import sys
from pathlib import Path

def extract_helen_blocks(markdown_file):
    """从 markdown 文件中提取 helen 代码块"""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 ```helen ... ``` 代码块
    pattern = r'```helen\s*\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    blocks = []
    for i, code in enumerate(matches, 1):
        blocks.append({
            'file': str(markdown_file),
            'block_num': i,
            'code': code.strip()
        })

    return blocks

def main():
    skills_dir = Path('skills')

    if not skills_dir.exists():
        print(f"错误: skills 目录不存在")
        sys.exit(1)

    # 查找所有 markdown 文件
    md_files = list(skills_dir.rglob('*.md'))
    print(f"找到 {len(md_files)} 个 markdown 文件")

    # 提取所有代码块
    all_blocks = []
    for md_file in md_files:
        blocks = extract_helen_blocks(md_file)
        all_blocks.extend(blocks)

    print(f"提取到 {len(all_blocks)} 个 Helen 代码块")

    # 创建测试目录
    test_dir = Path('wiki/skill_tests')
    test_dir.mkdir(exist_ok=True)

    # 生成测试文件
    generated = 0
    for block in all_blocks:
        # 创建子目录结构
        rel_path = Path(block['file']).relative_to(skills_dir)
        skill_test_dir = test_dir / rel_path.parent
        skill_test_dir.mkdir(parents=True, exist_ok=True)

        # 生成测试文件名
        test_file = skill_test_dir / f"block_{block['block_num']:03d}.helen"

        # 写入代码
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"// 来源: {block['file']} (代码块 {block['block_num']})\n\n")
            f.write(block['code'])

        generated += 1

    print(f"生成 {generated} 个测试文件到 {test_dir}")

if __name__ == '__main__':
    main()
