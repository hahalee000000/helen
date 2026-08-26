#!/usr/bin/env python3
"""
修复 Helen session transcript 中的消息序列违规。

OpenAI API 要求：
- tool 结果后必须有 assistant 消息（有 tool_calls 或 content）
- 不能有 user → user 连续出现

此脚本在违规位置插入占位 assistant 消息。

用法：
    python fix_message_sequence.py <session_dir>
"""

import json
import sys
import uuid
from pathlib import Path


def generate_uuid():
    """生成 UUID"""
    return uuid.uuid4().hex[:12]


def fix_message_sequence(messages: list) -> tuple[list, int]:
    """修复消息序列违规。

    Returns:
        (fixed_messages, fix_count) - 修复后的消息列表和修复次数
    """
    fixed = []
    fix_count = 0

    for i, msg in enumerate(messages):
        if msg.get('type') != 'message':
            fixed.append(msg)
            continue

        # 检查是否需要在前一条消息后插入 assistant
        if fixed and fixed[-1].get('type') == 'message':
            prev_role = fixed[-1].get('role')
            curr_role = msg.get('role')

            # 规则 1: tool 后必须有 assistant
            if prev_role == 'tool' and curr_role != 'assistant':
                # 插入占位 assistant 消息
                placeholder = {
                    'type': 'message',
                    'role': 'assistant',
                    'content': '[继续处理...]',
                    'uuid': generate_uuid(),
                    'message_type': None,
                    'priority': 50,
                    'compressed': False,
                    'pinned': False,
                    'agent_name': msg.get('agent_name'),
                    'invocation_id': msg.get('invocation_id'),
                    'parent_invocation_id': msg.get('parent_invocation_id'),
                    'visible_to_invocation_ids': []
                }
                fixed.append(placeholder)
                fix_count += 1

            # 规则 2: user 后不能有 user
            elif prev_role == 'user' and curr_role == 'user':
                # 插入空 assistant 消息作为分隔
                placeholder = {
                    'type': 'message',
                    'role': 'assistant',
                    'content': '',
                    'uuid': generate_uuid(),
                    'message_type': None,
                    'priority': 50,
                    'compressed': False,
                    'pinned': False,
                    'agent_name': msg.get('agent_name'),
                    'invocation_id': msg.get('invocation_id'),
                    'parent_invocation_id': msg.get('parent_invocation_id'),
                    'visible_to_invocation_ids': []
                }
                fixed.append(placeholder)
                fix_count += 1

        fixed.append(msg)

    # 检查结尾：如果最后是 tool，需要添加 assistant
    if fixed and fixed[-1].get('type') == 'message' and fixed[-1].get('role') == 'tool':
        last_msg = fixed[-1]
        placeholder = {
            'type': 'message',
            'role': 'assistant',
            'content': '[继续处理...]',
            'uuid': generate_uuid(),
            'message_type': None,
            'priority': 50,
            'compressed': False,
            'pinned': False,
            'agent_name': last_msg.get('agent_name'),
            'invocation_id': last_msg.get('invocation_id'),
            'parent_invocation_id': last_msg.get('parent_invocation_id'),
            'visible_to_invocation_ids': []
        }
        fixed.append(placeholder)
        fix_count += 1

    return fixed, fix_count


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    session_dir = Path(sys.argv[1]).expanduser()

    if not session_dir.is_dir():
        print(f"错误: 不是有效的目录 {session_dir}")
        sys.exit(1)

    transcript_path = session_dir / 'transcript.jsonl'

    if not transcript_path.exists():
        print(f"错误: 找不到 transcript.jsonl 在 {session_dir}")
        sys.exit(1)

    print(f"正在修复 {transcript_path} ...")

    # 读取消息
    with open(transcript_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    messages = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"警告: 跳过无效的 JSON 行: {e}")

    # 修复序列
    fixed_messages, fix_count = fix_message_sequence(messages)

    if fix_count == 0:
        print("✓ 消息序列已经正确，无需修复")
        return

    # 备份原文件
    backup_path = transcript_path.with_suffix('.jsonl.sequence-backup')
    transcript_path.rename(backup_path)
    print(f"✓ 已备份原文件到 {backup_path}")

    # 写入修复后的消息
    with open(transcript_path, 'w', encoding='utf-8') as f:
        for msg in fixed_messages:
            f.write(json.dumps(msg, ensure_ascii=False) + '\n')

    print(f"✓ 已修复 {fix_count} 处消息序列违规")
    print(f"✓ 原始消息: {len(messages)}, 修复后: {len(fixed_messages)}")
    print("\n✓ 修复完成！可以重启 helen agent 继续使用此 session。")


if __name__ == '__main__':
    main()
