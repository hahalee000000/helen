"""Side-channel 索引：web_ui_session_id → [transcript message_uuid, ...]

多个 Web UI 会话共享一个 Helen transcript，此模块维护独立的索引文件，
记录每个 Web UI session 产生的 transcript 消息 UUID，用于按会话分组显示。

索引文件格式（.helen/session_index/<web_ui_session_id>.json）：
{
    "web_ui_session_id": "uuid-string",
    "message_uuids": ["msg_uuid_1", "msg_uuid_2", ...]
}
"""

import json
import os
from pathlib import Path
from typing import Optional

# 项目根目录（从 webui/backend/app/services/ 向上 5 层到 helenagent 根）
_AGENT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
_INDEX_DIR = _AGENT_DIR / ".helen" / "session_index"


def _ensure_dir():
    """确保索引目录存在"""
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)


def read_index(web_ui_session_id: str) -> list[str]:
    """读取指定 Web UI session 的 message UUID 列表"""
    path = _INDEX_DIR / f"{web_ui_session_id}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data.get("message_uuids", [])
    except (json.JSONDecodeError, KeyError):
        return []


def write_index(web_ui_session_id: str, uuids: list[str]):
    """写入（覆盖）指定 Web UI session 的索引"""
    _ensure_dir()
    path = _INDEX_DIR / f"{web_ui_session_id}.json"
    data = {
        "web_ui_session_id": web_ui_session_id,
        "message_uuids": uuids,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def append_to_index(web_ui_session_id: str, new_uuids: list[str]):
    """追加新 UUID 到索引（去重）"""
    if not new_uuids:
        return
    existing = read_index(web_ui_session_id)
    existing_set = set(existing)
    for uuid in new_uuids:
        if uuid and uuid not in existing_set:
            existing.append(uuid)
            existing_set.add(uuid)
    if len(existing) > len(existing_set) - len(new_uuids):
        # 有新元素加入才写入
        write_index(web_ui_session_id, existing)


def delete_session_index(web_ui_session_id: str):
    """删除指定 Web UI session 的索引文件"""
    path = _INDEX_DIR / f"{web_ui_session_id}.json"
    if path.exists():
        path.unlink()


def list_indexes() -> dict[str, list[str]]:
    """列出所有索引（web_ui_session_id → uuids）"""
    if not _INDEX_DIR.exists():
        return {}
    result = {}
    for f in sorted(_INDEX_DIR.glob("*.json")):
        sid = f.stem
        result[sid] = read_index(sid)
    return result


def get_transcript_path(helen_session_id: str) -> Optional[Path]:
    """获取 transcript.jsonl 路径（优先项目目录，回退 ~/.helen/）"""
    project_path = _AGENT_DIR / ".helen" / "sessions" / helen_session_id / "transcript.jsonl"
    if project_path.exists():
        return project_path
    global_path = Path.home() / ".helen" / "sessions" / helen_session_id / "transcript.jsonl"
    if global_path.exists():
        return global_path
    return None


def read_transcript_entries(helen_session_id: str) -> list[dict]:
    """读取 transcript.jsonl 全部条目"""
    path = get_transcript_path(helen_session_id)
    if not path:
        return []
    entries = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return entries


def count_transcript_lines(helen_session_id: str) -> int:
    """计算 transcript 文件行数（用于增量追踪）"""
    path = get_transcript_path(helen_session_id)
    if not path:
        return 0
    try:
        with open(path) as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_new_message_uuids(helen_session_id: str, from_line: int) -> list[str]:
    """读取 transcript 从 from_line 行开始的新消息 UUID

    from_line: 0-based 行号，只读取该行及之后的内容
    """
    path = get_transcript_path(helen_session_id)
    if not path:
        return []
    uuids = []
    try:
        with open(path) as f:
            for i, line in enumerate(f):
                if i < from_line:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "message" and entry.get("uuid"):
                        uuids.append(entry["uuid"])
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return uuids


def get_current_helen_session_id() -> str:
    """获取当前 Helen session ID

    v6.0 单会话架构：通过 helen_bridge 从 Helen runtime 获取当前 session ID。
    不再读 .tui_session_id 文件（该文件已不再写入）。

    如果 bridge 返回的 session 没有 transcript，回退到最新的有 transcript 的 session。
    """
    # 通过 helen_bridge 获取（同步方式：直接调用 Python FFI）
    try:
        from app.services.helen_bridge import helen_bridge
        bridge_sid = helen_bridge.get_session_id_sync()
        if bridge_sid:
            # 验证该 session 的 transcript 存在
            if get_transcript_path(bridge_sid) is not None:
                return bridge_sid
            # transcript 不存在，回退到最新 session
    except Exception:
        pass

    # 回退：找最新的有 transcript.jsonl 的 session 目录
    for sessions_dir in [
        _AGENT_DIR / ".helen" / "sessions",
        Path.home() / ".helen" / "sessions",
    ]:
        if not sessions_dir.exists():
            continue
        try:
            # 只考虑有 transcript.jsonl 的目录
            candidates = [
                p for p in sessions_dir.iterdir()
                if p.is_dir() and (p / "transcript.jsonl").exists()
            ]
            if candidates:
                latest = max(candidates, key=lambda p: p.stat().st_mtime)
                return latest.name
        except Exception:
            pass

    return ""


# ── 测试消息过滤 ──────────────────────────────────────────────

TEST_MESSAGE_PREFIX = "[TEST]"


def is_test_message(entry: dict) -> bool:
    """检测 transcript 条目是否为测试消息（以 [TEST] 开头）

    集成测试发送的消息会污染 transcript，通过此前缀标记过滤。
    """
    content = entry.get("content", "")
    if isinstance(content, str):
        return content.strip().startswith(TEST_MESSAGE_PREFIX)
    return False


def filter_test_messages(entries: list[dict]) -> list[dict]:
    """过滤掉测试消息，返回干净的消息列表"""
    return [e for e in entries if not is_test_message(e)]
