#!/usr/bin/env python3
"""
清理 Helen session transcript 中的错误消息。

修复以下问题：
1. 移除空的 assistant 消息（content 为空且无 tool_calls）
2. 移除孤立的 tool 消息（没有对应的 assistant tool_calls）

用法：
    python clean_session_errors.py <session_dir>
    python clean_session_errors.py ~/helen-rust/.helen/sessions/session_xxx
"""

import json
import sys
from pathlib import Path


def clean_session(transcript_path: Path) -> tuple[int, int]:
    """清理 transcript 文件中的错误消息。

    Returns:
        (empty_assistant_count, orphaned_tool_count) - 移除的消息数量
    """
    if not transcript_path.exists():
        print(f"错误: 文件不存在 {transcript_path}")
        return -1, -1

    # 读取所有消息
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

    # 第一轮：收集所有 assistant 消息的 tool_call_ids
    assistant_tool_call_ids = set()
    for msg in messages:
        if msg.get('type') == 'message' and msg.get('role') == 'assistant':
            for tc in msg.get('tool_calls', []):
                if 'id' in tc:
                    assistant_tool_call_ids.add(tc['id'])

    # 第二轮：标记需要移除的消息
    empty_assistant_count = 0
    orphaned_tool_count = 0
    cleaned_messages = []

    for msg in messages:
        if msg.get('type') != 'message':
            cleaned_messages.append(msg)
            continue

        role = msg.get('role')
        content = msg.get('content', '')
        tool_calls = msg.get('tool_calls', [])
        tool_call_id = msg.get('tool_call_id')

        # 检查是否是空的 assistant 消息
        if role == 'assistant' and not tool_calls:
            if not content or content == '' or content is None:
                empty_assistant_count += 1
                continue  # 跳过这个消息

        # 检查是否是孤立的 tool 消息
        if role == 'tool' and tool_call_id:
            if tool_call_id not in assistant_tool_call_ids:
                orphaned_tool_count += 1
                continue  # 跳过这个消息

        cleaned_messages.append(msg)

    # 备份原文件
    backup_path = transcript_path.with_suffix('.jsonl.backup')
    transcript_path.rename(backup_path)
    print(f"✓ 已备份原文件到 {backup_path}")

    # 写入清理后的消息
    with open(transcript_path, 'w', encoding='utf-8') as f:
        for msg in cleaned_messages:
            f.write(json.dumps(msg, ensure_ascii=False) + '\n')

    print(f"✓ 已清理 {empty_assistant_count} 个空 assistant 消息")
    print(f"✓ 已清理 {orphaned_tool_count} 个孤立 tool 消息")
    print(f"✓ 原始消息: {len(messages)}, 清理后: {len(cleaned_messages)}")

    return empty_assistant_count, orphaned_tool_count


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

    print(f"正在清理 {transcript_path} ...")
    empty_count, orphaned_count = clean_session(transcript_path)

    if empty_count < 0:
        print("\n✗ 清理失败。")
        sys.exit(1)

    total_removed = empty_count + orphaned_count
    if total_removed > 0:
        print(f"\n✓ 清理完成！共移除 {total_removed} 条错误消息。")
        print("✓ 可以重启 helen agent 继续使用此 session。")
    else:
        print("\n✓ transcript 已经是干净的，无需清理。")


if __name__ == '__main__':
    main()
