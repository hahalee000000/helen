#!/usr/bin/env python3
"""
清理 Helen session transcript 中的孤立 tool 消息。

孤立 tool 消息：没有对应 assistant tool_calls 的 tool 消息，
会导致 API 返回 HTTP 400。

用法：
    python clean_transcript.py <session_dir>
    python clean_transcript.py ~/helen-rust/.helen/sessions/session_xxx
"""

import json
import sys
from pathlib import Path


def clean_transcript(transcript_path: Path) -> int:
    """清理 transcript 文件中的孤立 tool 消息。

    Returns:
        清理的消息数量
    """
    if not transcript_path.exists():
        print(f"错误: 文件不存在 {transcript_path}")
        return -1

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

    # 第一轮：收集所有 tool_call_id
    tool_call_ids = set()
    for msg in messages:
        if msg.get('type') == 'message' and msg.get('role') == 'assistant':
            if 'tool_calls' in msg and msg['tool_calls']:
                for tc in msg['tool_calls']:
                    if 'id' in tc:
                        tool_call_ids.add(tc['id'])

    # 第二轮：标记孤立的 tool 消息
    orphaned_count = 0
    cleaned_messages = []
    for msg in messages:
        if msg.get('type') == 'message' and msg.get('role') == 'tool':
            tool_call_id = msg.get('tool_call_id')
            if tool_call_id and tool_call_id not in tool_call_ids:
                # 孤立的 tool 消息
                orphaned_count += 1
                continue  # 跳过这个消息
        cleaned_messages.append(msg)

    if orphaned_count == 0:
        print("✓ 没有发现孤立 tool 消息，transcript 已经是干净的")
        return 0

    # 备份原文件
    backup_path = transcript_path.with_suffix('.jsonl.backup')
    transcript_path.rename(backup_path)
    print(f"✓ 已备份原文件到 {backup_path}")

    # 写入清理后的消息
    with open(transcript_path, 'w', encoding='utf-8') as f:
        for msg in cleaned_messages:
            f.write(json.dumps(msg, ensure_ascii=False) + '\n')

    print(f"✓ 已清理 {orphaned_count} 条孤立 tool 消息")
    print(f"✓ 原始消息: {len(messages)}, 清理后: {len(cleaned_messages)}")

    return orphaned_count


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
    count = clean_transcript(transcript_path)

    if count > 0:
        print("\n✓ 清理完成！可以重启 helen agent 继续使用此 session。")
    elif count == 0:
        print("\n✓ transcript 已经是干净的。")
    else:
        print("\n✗ 清理失败。")
        sys.exit(1)


if __name__ == '__main__':
    main()
