"""聊天相关 API 路由"""
import asyncio
import json
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Body, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.message import Message
from app.services.helen_bridge import helen_bridge
from app.services import hint_injector
from app.services import directory_manager

router = APIRouter()

# ── 文件上传常量 ──────────────────────────────────────────
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_MIME_TYPES = {
    # 图片
    "image/jpeg", "image/png", "image/gif", "image/webp",
    # 音频
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/m4a",
    # 视频
    "video/mp4", "video/webm", "video/quicktime",
}


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"


# === 目录管理 API（单会话模式） ===

@router.get("/dir")
async def get_directory(db: Session = Depends(get_db)):
    """获取当前工作目录信息

    v6.0 单会话架构：目录 = 会话边界。
    返回的 session_id 是 cwd 的确定性 hash（URL 安全），
    首次访问某目录时自动在 per-project DB 中 upsert 一条 SessionModel，
    保证前端拿到 session_id 后立刻能收发消息。
    """
    cwd = directory_manager.get_current_cwd()
    display_name = directory_manager.get_display_name(cwd)
    session_id = directory_manager.cwd_to_session_id(cwd)

    # 获取 Helen session ID（如果可用）
    helen_session_id = None
    try:
        helen_session_id = await helen_bridge.get_session_id()
    except Exception:
        pass  # Helen 可能未初始化

    # v6.0: 确保 SessionModel 行存在（upsert），前端用它建立 WebSocket。
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        session = SessionModel(id=session_id, title=display_name)
        db.add(session)
        db.commit()
        db.refresh(session)
    else:
        # 同步显示名（目录可能被重命名）
        if session.title != display_name:
            session.title = display_name
            db.commit()

    return {
        "cwd": cwd,
        "display_name": display_name,
        "session_id": session_id,
        "helen_session_id": helen_session_id,
    }


@router.post("/dir")
async def change_directory(body: dict = Body(...)):
    """切换工作目录

    切换后，所有后续请求将使用新目录的数据库和 session。

    Request body:
        {"path": "/path/to/project"}

    Returns:
        {
            "status": "ok",
            "cwd": "/absolute/path",
            "display_name": "project-name",
            "session_id": "<hash>",
            "helen_session_id": "xxx"
        }
    """
    path = body.get("path", "")
    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    result = directory_manager.set_current_cwd(path)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    new_cwd = result["cwd"]
    display_name = result["display_name"]
    new_session_id = directory_manager.cwd_to_session_id(new_cwd)

    # 获取新目录的 Helen session ID
    helen_session_id = None
    try:
        helen_session_id = await helen_bridge.get_session_id()
    except Exception:
        pass

    # upsert SessionModel（注意：必须在 get_db 已指向新 cwd 之后调用）
    new_db = next(get_db())
    try:
        session = new_db.query(SessionModel).filter(SessionModel.id == new_session_id).first()
        if not session:
            session = SessionModel(id=new_session_id, title=display_name)
            new_db.add(session)
            new_db.commit()
    finally:
        new_db.close()

    result["session_id"] = new_session_id
    result["helen_session_id"] = helen_session_id
    return result


@router.get("/dir/messages")
async def get_directory_messages(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取当前工作目录的消息历史

    从当前项目的 SQLite 数据库读取消息。session_id 使用 cwd 的 hash 标识。
    """
    cwd = directory_manager.get_current_cwd()
    session_id = directory_manager.cwd_to_session_id(cwd)

    # 查询当前目录的消息（session_id 使用 cwd hash 作为标识）
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.timestamp.asc()).offset(offset).limit(limit).all()

    return [m.to_dict() for m in messages]


# === 会话管理 API（已废弃，使用 /dir API 替代） ===
# TODO: 阶段 4 前端改造完成后删除这些端点

@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest = Body(default=CreateSessionRequest()),
    db: Session = Depends(get_db)
):
    """创建新会话"""
    session_id = str(uuid.uuid4())
    title = request.title or "New Chat"
    session = SessionModel(id=session_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session_id, "title": title}

@router.get("/sessions")
async def list_sessions(db: Session = Depends(get_db)):
    """获取会话列表

    v6.0 单会话架构：session_id 应是 16 字符 hex（cwd 的 SHA256 前缀）或 UUID。
    防御性过滤掉含 / 等非法字符的旧数据（早期版本曾错误地用 raw cwd 作为 ID）。
    """
    sessions = db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
    valid = []
    for s in sessions:
        # 跳过包含路径分隔符的非法 ID（这些 ID 无法通过 URL path 传递）
        if "/" in s.id or "\\" in s.id:
            continue
        valid.append(s.to_dict())
    return valid

@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: Session = Depends(get_db)):
    """获取单个会话"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()

@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """更新会话（重命名/描述）"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if "name" in body:
        session.name = body["name"]
    if "description" in body:
        session.description = body["description"]
    if "title" in body:
        session.title = body["title"]
    db.commit()
    db.refresh(session)
    return session.to_dict()

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    helen_session_id: Optional[str] = Query(None, description="Helen transcript session ID for cascade deletion"),
    db: Session = Depends(get_db)
):
    """删除会话（Web UI DB + Helen transcript 级联）

    v2.1 架构（见 reports/context-and-transcript-architecture.md §反馈 2）：
    通过 /clear-session 斜杠命令触发 Helen 侧的 transcript 级联删除
    （delete_session(cascade=true)），避免孤儿 spawn transcripts。
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # ① 若有 helen_session_id，先触发 Helen 侧 transcript 级联删除
    if helen_session_id:
        try:
            response = await helen_bridge.run_silent("/clear-session " + helen_session_id)
            if not response or "__HELEN_CLEAR_SESSION_OK__" not in response:
                # transcript 清理失败，仍继续删除 DB（避免 DB 残留），但记录告警
                import logging
                logging.getLogger(__name__).warning(
                    "Helen transcript 清理失败 (helen_sid=%s, response=%r)",
                    helen_session_id, response
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "Helen transcript 清理异常 (helen_sid=%s): %s", helen_session_id, e
            )

    # ② 删除 DB 中该会话的消息和会话实体
    db.query(Message).filter(Message.session_id == session_id).delete()
    db.delete(session)
    db.commit()

    # 删除 side-channel 索引（如有）
    from app.services.session_index import delete_session_index
    delete_session_index(session_id)

    return {
        "status": "ok",
        "message": "Session deleted",
    }

@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, db: Session = Depends(get_db)):
    """获取会话消息"""
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.timestamp.asc()).all()
    return [_resolve_attachments(m.to_dict()) for m in messages]


def _resolve_attachments(msg_dict: dict) -> dict:
    """将消息中的 attachment IDs 转换为完整的 Attachment 对象

    DB 存储的是 JSON 字符串形式的 upload_id 列表，
    前端需要完整的 Attachment 对象（包含 filename, mime_type, size, url）。
    """
    attachments_str = msg_dict.get("attachments")
    if not attachments_str:
        return msg_dict

    try:
        upload_ids = json.loads(attachments_str)
    except (json.JSONDecodeError, TypeError):
        return msg_dict

    if not isinstance(upload_ids, list):
        return msg_dict

    cwd = directory_manager.get_current_cwd()
    resolved = []
    for upload_id in upload_ids:
        metadata_path = Path(cwd) / ".helen" / "uploads" / upload_id / "metadata.json"
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text())
                resolved.append({
                    "id": upload_id,
                    "filename": metadata.get("filename", "unknown"),
                    "mime_type": metadata.get("mime_type", "application/octet-stream"),
                    "size": metadata.get("size", 0),
                    "url": f"/api/chat/uploads/{upload_id}/file"
                })
            except (json.JSONDecodeError, OSError):
                # metadata 损坏，跳过
                pass

    msg_dict["attachments"] = resolved
    return msg_dict

@router.get("/sessions/{session_id}/transcript")
async def get_transcript(session_id: str):
    """获取 Helen transcript（LLM 上下文的完整记录）

    从 .helen/sessions/<sid>/transcript.jsonl 读取，返回结构化的消息列表。
    用于调试和查看 Agent 执行过程。
    """
    import os
    from pathlib import Path
    from app.services import directory_manager

    # v6.0 单会话架构：通过 helen_bridge 获取当前 Helen session ID
    # （不再读 .tui_session_id 文件，该文件已不再写入）
    helen_sid = session_id  # 默认用前端传入的
    try:
        bridge_sid = await helen_bridge.get_session_id()
        if bridge_sid:
            helen_sid = bridge_sid
    except Exception:
        pass

    # 查找 transcript 文件（在当前工作目录，不是 helenagent 目录）
    cwd = directory_manager.get_current_cwd()
    transcript_path = Path(cwd) / ".helen" / "sessions" / helen_sid / "transcript.jsonl"
    if not transcript_path.exists():
        # 也尝试全局 sessions 目录
        global_path = Path.home() / ".helen" / "sessions" / helen_sid / "transcript.jsonl"
        if global_path.exists():
            transcript_path = global_path
        else:
            raise HTTPException(status_code=404, detail=f"Transcript not found for session {helen_sid}")

    # 解析 transcript.jsonl
    entries = []
    try:
        with open(transcript_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entry["_line"] = line_num  # 加行号便于调试
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    entries.append({
                        "type": "parse_error",
                        "line": line_num,
                        "error": str(e),
                        "raw": line[:200]
                    })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取 transcript 失败: {e}")

    # 过滤测试消息（以 [TEST] 开头的集成测试消息）
    from app.services.session_index import filter_test_messages
    entries = filter_test_messages(entries)

    # 过滤元数据条目（session_meta 等，不是实际对话内容）
    entries = [e for e in entries if e.get("type") != "session_meta"]

    # 统计信息
    roles = {}
    tool_calls_count = 0
    for e in entries:
        if e.get("type") == "message":
            role = e.get("role", "unknown")
            roles[role] = roles.get(role, 0) + 1
            # Helen runtime 不填充结构化 tool_calls，从 content 文本中提取
            if e.get("tool_calls"):
                tool_calls_count += len(e["tool_calls"])
            else:
                content = str(e.get("content", ""))
                # 匹配 "Tool calls: [func1(...) → ..., func2(...) → ...]" 格式
                if content.startswith("Tool calls:"):
                    import re
                    tool_calls_count += len(re.findall(r'\w+\(', content))

    return {
        "session_id": helen_sid,
        "file": str(transcript_path),
        "total_entries": len(entries),
        "roles": roles,
        "tool_calls_count": tool_calls_count,
        "entries": entries,
    }

@router.get("/sessions/{session_id}/transcript/messages")
async def get_transcript_by_session(session_id: str):
    """按 side-channel 索引过滤 transcript，返回属于指定 Web UI session 的消息"""
    from app.services.session_index import (
        read_index, read_transcript_entries, get_current_helen_session_id
    )
    helen_sid = get_current_helen_session_id()
    if not helen_sid:
        raise HTTPException(status_code=404, detail="No active Helen session")

    # 读取索引
    indexed_uuids = set(read_index(session_id))
    if not indexed_uuids:
        return {"session_id": session_id, "helen_session_id": helen_sid,
                "total": 0, "messages": []}

    # 读取 transcript 并按索引过滤（排除测试消息）
    from app.services.session_index import filter_test_messages
    all_entries = filter_test_messages(read_transcript_entries(helen_sid))
    filtered = [
        e for e in all_entries
        if e.get("type") == "message" and e.get("uuid") in indexed_uuids
    ]

    return {
        "session_id": session_id,
        "helen_session_id": helen_sid,
        "total": len(filtered),
        "messages": filtered,
    }

@router.get("/transcript/all")
async def get_all_transcript():
    """返回完整 transcript 的所有消息（不按 session 过滤）"""
    from app.services.session_index import (
        read_transcript_entries, get_current_helen_session_id
    )
    helen_sid = get_current_helen_session_id()
    if not helen_sid:
        raise HTTPException(status_code=404, detail="No active Helen session")

    entries = read_transcript_entries(helen_sid)
    from app.services.session_index import filter_test_messages
    messages = [e for e in filter_test_messages(entries) if e.get("type") == "message"]
    return {
        "helen_session_id": helen_sid,
        "total": len(messages),
        "messages": messages,
    }

@router.get("/transcript/unmapped")
async def get_unmapped_transcript():
    """返回未映射到任何 Web UI session 的 transcript 消息（如 CLI 会话消息）"""
    from app.services.session_index import (
        read_transcript_entries, get_current_helen_session_id, list_indexes,
        filter_test_messages
    )
    helen_sid = get_current_helen_session_id()
    if not helen_sid:
        raise HTTPException(status_code=404, detail="No active Helen session")

    # 收集所有已索引的 UUID
    all_indexes = list_indexes()
    indexed_uuids = set()
    for uuids in all_indexes.values():
        indexed_uuids.update(uuids)

    # 过滤出未映射的消息（排除测试消息）
    entries = filter_test_messages(read_transcript_entries(helen_sid))
    unmapped = [
        e for e in entries
        if e.get("type") == "message"
        and e.get("uuid")
        and e["uuid"] not in indexed_uuids
    ]
    return {
        "helen_session_id": helen_sid,
        "total": len(unmapped),
        "messages": unmapped,
    }

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    session_id: str,
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """WebSocket 聊天接口"""
    manager = websocket.app.state.websocket_manager
    await manager.connect(session_id, websocket)

    # 跟踪当前正在进行的流式任务，以便 cancel 消息能中断它
    stream_task: Optional[asyncio.Task] = None

    async def do_streaming(user_message: str, file_paths: Optional[List[str]] = None):
        """后台执行 Helen 流式调用（独立于 WebSocket 连接）

        即使 WebSocket 断开，推理也会继续，结果保存到 transcript 和 DB。
        使用 handler 注入的 db session（handler 会等待本 task 完成后再返回，
        从而保证 db session 在整个 task 生命周期内有效）。
        """
        full_response = ""

        # Side-channel 索引追踪
        from app.services.session_index import (
            count_transcript_lines, get_new_message_uuids,
            append_to_index, get_current_helen_session_id
        )
        # 初始 helen_sid 从文件读取（可能是过时的）
        helen_sid = get_current_helen_session_id()
        pre_line_count = count_transcript_lines(helen_sid) if helen_sid else 0

        async def save_assistant_message(content: str, interrupted: bool = False):
            """保存 assistant 消息到 DB（保持与 TranscriptStore SSOT 一致）"""
            if not content:
                return
            display_content = content + ("\n\n— ⚠️ 输出被用户中断" if interrupted else "")
            assistant_msg = Message(
                session_id=session_id, role="assistant", content=display_content
            )
            db.add(assistant_msg)
            db.commit()

        async def update_session_index():
            """将本次 streaming 新增的 transcript 消息 UUID 追加到 side-channel 索引

            使用 streaming 事件捕获的 helen_sid（权威值），而不是从文件读取（可能过时）。
            """
            nonlocal helen_sid, pre_line_count
            if not helen_sid:
                return
            new_uuids = get_new_message_uuids(helen_sid, pre_line_count)
            if new_uuids:
                append_to_index(session_id, new_uuids)

        try:
            async for chunk in helen_bridge.run_chat_streaming(
                user_message, session_id, file_paths=file_paths or []
            ):
                chunk_type = chunk.get("type")
                content = chunk.get("content", "")

                if chunk_type == "llm_chunk":
                    full_response += content
                    # 发送 chunk（WebSocket 可能已断开，捕获异常）
                    try:
                        await manager.send_to_session(session_id, {
                            "type": "llm_chunk",
                            "data": {"content": content}
                        })
                    except Exception:
                        pass  # WebSocket 断开，继续累积 full_response
                elif chunk_type == "status_update":
                    # status_update 的 content 是 JSON 字符串（Helen FFI json.dumps），
                    # 解析后平铺发送，避免前端多包一层 {content: json_string}
                    try:
                        parsed = json.loads(content) if isinstance(content, str) else content
                    except (json.JSONDecodeError, TypeError):
                        parsed = {}
                    try:
                        await manager.send_to_session(session_id, {
                            "type": "status_update",
                            "data": parsed
                        })
                    except Exception:
                        pass
                elif chunk_type in ("agent_start", "agent_end", "phase_start",
                                   "processing_start", "processing_complete",
                                   "hint_injected"):
                    try:
                        await manager.send_to_session(session_id, {
                            "type": chunk_type,
                            "data": {"content": content}
                        })
                    except Exception:
                        pass
                elif chunk_type == "helen_session_id":
                    # Helen 会话 ID：这是真实的 session ID（权威值）
                    # 如果和之前记录的不同，说明 session 已变更，需要重置 pre_line_count
                    new_sid = content
                    if new_sid != helen_sid:
                        # Session 变更：新 session 是全新的，从头开始索引
                        helen_sid = new_sid
                        pre_line_count = 0
                    try:
                        await manager.send_to_session(session_id, {
                            "type": "helen_session_id",
                            "data": {"session_id": content}
                        })
                    except Exception:
                        pass
                elif chunk_type == "error":
                    try:
                        await manager.send_to_session(session_id, {
                            "type": "error",
                            "data": {"content": content}
                        })
                    except Exception:
                        pass

            # 正常完成（未被取消）：发送完成信号 + 保存消息 + 更新索引
            try:
                await manager.send_to_session(session_id, {"type": "llm_complete"})
            except Exception:
                pass
            await save_assistant_message(full_response, interrupted=False)
            await update_session_index()

        except asyncio.CancelledError:
            # 被 cancel 打断：partial response 也要保存，与 TranscriptStore SSOT 对齐
            # （Helen 的 llm_mixin.py:586-594 在 interrupted 时仍会把 partial 写入 transcript）
            await save_assistant_message(full_response, interrupted=True)
            await update_session_index()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                # 流正在跑 → 拒绝（提示用户改用 💡 提示功能）
                if stream_task and not stream_task.done():
                    await manager.send_to_session(session_id, {
                        "type": "error",
                        "data": {"content": "LLM 正在处理中，请使用 💡 提示 功能追加指令"}
                    })
                    continue

                user_message = data.get("content", "")

                # v6.0 单会话架构：移除了 __helen_resume__ / __helen_init__ 协议
                # 会话恢复现在由 ChatSession.main 内部直接使用 get_session_id() resume
                # 前端不再需要发送静默命令或维护 localStorage 中的 session ID

                # ── 斜杠命令：同步执行，响应作为用户气泡返回 ──
                # 斜杠命令（/help /compress /context 等）只修改 Helen 内部状态，
                # 不产生对 LLM 的可见对话。chat.py 直接 run_silent 执行。
                # /dir 命令特殊处理：切换工作目录
                if user_message.startswith("/dir "):
                    path = user_message[5:].strip()
                    result = directory_manager.set_current_cwd(path)

                    if result["status"] == "ok":
                        new_cwd = result["cwd"]
                        new_session_id = directory_manager.cwd_to_session_id(new_cwd)

                        # ── Actor 模式：目录切换 = session 切换，重启 actor ──
                        # actor 在 spawn 时绑定了旧 session_id，切目录后必须重启，
                        # 否则新目录的消息会写入旧 session 的 transcript。
                        try:
                            from app.services.channel_actor_manager import channel_actor_manager
                            if channel_actor_manager._actor_spawned:
                                channel_actor_manager.exit_actor()
                        except Exception:
                            pass

                        # 在新目录的 per-project DB 中 upsert SessionModel
                        new_db = next(get_db())
                        try:
                            sess = new_db.query(SessionModel).filter(SessionModel.id == new_session_id).first()
                            if not sess:
                                sess = SessionModel(id=new_session_id, title=result["display_name"])
                                new_db.add(sess)
                                new_db.commit()
                        finally:
                            new_db.close()

                        # 获取新目录的 Helen session ID
                        helen_sid = None
                        try:
                            helen_sid = await helen_bridge.get_session_id()
                        except Exception:
                            pass

                        # 通知前端目录已切换（含新 session_id，前端据此重建 WebSocket）
                        await manager.send_to_session(session_id, {
                            "type": "directory_changed",
                            "data": {
                                "cwd": new_cwd,
                                "display_name": result["display_name"],
                                "session_id": new_session_id,
                                "helen_session_id": helen_sid,
                            }
                        })

                        # 加载新目录的消息历史
                        # 注意：此时 get_db() 会返回新目录的数据库
                        new_db2 = next(get_db())
                        try:
                            messages = new_db2.query(Message).filter(
                                Message.session_id == new_session_id
                            ).order_by(Message.timestamp.asc()).all()
                            await manager.send_to_session(session_id, {
                                "type": "load_messages",
                                "data": [m.to_dict() for m in messages]
                            })
                        finally:
                            new_db2.close()

                        # 发送成功响应
                        await manager.send_to_session(session_id, {
                            "type": "processing_complete",
                            "data": {
                                "content": f"✅ 已切换到: {result['display_name']}",
                                "is_slash_response": True
                            }
                        })
                    else:
                        # 切换失败
                        await manager.send_to_session(session_id, {
                            "type": "processing_complete",
                            "data": {
                                "content": f"❌ {result['message']}",
                                "is_slash_response": True
                            }
                        })
                    continue

                # 命令和响应都会保存到 DB（斜杠命令持久化）。
                if user_message.startswith("/"):
                    # 保存用户的斜杠命令到 DB
                    slash_user_msg = Message(
                        session_id=session_id,
                        role="user",
                        content=user_message
                    )
                    db.add(slash_user_msg)
                    db.commit()

                    response = await helen_bridge.run_silent(user_message)

                    # /clear 的响应中嵌入静默标记 __HELEN_CLEAR_OK__，
                    # 用于告知前端同步清空显示消息 + localStorage 会话 ID
                    is_clear = response and "__HELEN_CLEAR_OK__" in response
                    if is_clear:
                        response = response.replace("__HELEN_CLEAR_OK__", "").strip()

                    # /clear-session 后 actor 退出，需要重启
                    is_restart = response and "__HELEN_RESTART_ACTOR__" in response
                    if is_restart:
                        response = response.replace("__HELEN_RESTART_ACTOR__", "").strip()

                    # 保存系统响应到 DB（如有）
                    if response:
                        slash_resp_msg = Message(
                            session_id=session_id,
                            role="assistant",
                            content=response
                        )
                        db.add(slash_resp_msg)
                        db.commit()

                    if is_clear:
                        # /clear：删除所有 DB 消息（包括刚保存的命令和响应）
                        # 然后发 reload_messages 事件，前端清空显示 + localStorage
                        db.query(Message).filter(Message.session_id == session_id).delete()
                        db.commit()
                        await manager.send_to_session(session_id, {
                            "type": "reload_messages", "data": {}
                        })
                    elif response:
                        await manager.send_to_session(session_id, {
                            "type": "processing_complete",
                            "data": {"content": response, "is_slash_response": True}
                        })
                    else:
                        # 空响应（如 /quit /exit）：发完成信号即可
                        await manager.send_to_session(session_id, {
                            "type": "processing_complete",
                            "data": {}
                        })

                    # /clear-session 后重启 actor
                    if is_restart:
                        try:
                            from app.services.channel_actor_manager import channel_actor_manager
                            channel_actor_manager.restart_actor()
                        except Exception:
                            pass

                    continue

                # 提取附件（多模态支持）
                attachment_ids = data.get("attachments") or []
                file_paths = []
                if attachment_ids:
                    cwd = directory_manager.get_current_cwd()
                    for upload_id in attachment_ids:
                        # 防御：upload_id 必须是合法 UUID 格式，防止路径遍历
                        if not upload_id or "/" in upload_id or "\\" in upload_id or ".." in upload_id:
                            continue
                        file_path = Path(cwd) / ".helen" / "uploads" / upload_id / "file"
                        if file_path.exists():
                            file_paths.append(str(file_path))

                # 保存用户消息（含附件引用）
                user_msg = Message(
                    session_id=session_id,
                    role="user",
                    content=user_message,
                    attachments=json.dumps(attachment_ids) if attachment_ids else None,
                )
                db.add(user_msg)
                db.commit()

                # 更新会话时间
                session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
                if session:
                    session.updated_at = datetime.now()
                    db.commit()

                # 启动后台流式任务（不阻塞 WS 接收循环）
                stream_task = asyncio.create_task(do_streaming(user_message, file_paths))

            elif data.get("type") == "hint":
                # 推理中追加提示：入队，不取消当前流。
                # Helen 的 on_tool_end 回调会在下一个工具结束后读取并注入。
                hint_text = data.get("content", "")
                client_id = data.get("client_id", "")
                if not hint_text or not hint_text.strip():
                    continue
                hint_injector.enqueue_hint(session_id, hint_text.strip(), client_id)
                await manager.send_to_session(session_id, {
                    "type": "hint_queued",
                    "data": {"content": hint_text, "client_id": client_id}
                })

            elif data.get("type") == "cancel":
                # 用户请求中断当前 LLM 流
                if stream_task and not stream_task.done():
                    helen_bridge.cancel_session(session_id)
                    stream_task.cancel()
                    try:
                        await stream_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    stream_task = None
                    await manager.send_to_session(session_id, {
                        "type": "cancelled",
                        "data": {"content": ""}
                    })

    except WebSocketDisconnect:
        # v6.0 单会话架构：不再取消 stream_task。
        # 推理继续运行，结果保存到 per-project DB 和 transcript。
        # 用户返回聊天页面时会从 DB 加载完整响应。
        #
        # 关键：await stream_task 让它跑完，handler 再返回。
        # 这样 FastAPI 的 db 依赖在 task 完成前不会被 cleanup，
        # do_streaming 内的 db.commit() 始终有效。
        hint_injector.clear_session(session_id)
        manager.disconnect(session_id, websocket)
        if stream_task and not stream_task.done():
            try:
                await stream_task
            except (asyncio.CancelledError, Exception):
                pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        hint_injector.clear_session(session_id)
        manager.disconnect(session_id, websocket)
        if stream_task and not stream_task.done():
            try:
                await stream_task
            except (asyncio.CancelledError, Exception):
                pass


@router.post("/reload")
async def reload_helen():
    """手动触发 Helen 代码热重载

    清除缓存的 agent 实例和 Python 模块，下次请求将使用最新代码。
    """
    helen_bridge.force_reload()
    return {
        "status": "ok",
        "message": "Helen 代码已重新加载",
        "reload_count": helen_bridge._reload_count
    }


# === 文件上传 API（多模态支持） ===

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(None),
):
    """上传文件用于多模态交互

    接收 multipart/form-data 文件，保存到 .helen/uploads/<upload_id>/。
    返回 upload_id 和 metadata，前端在发送消息时携带 upload_id 列表。

    支持的 MIME 类型：
    - 图片：image/jpeg, image/png, image/gif, image/webp
    - 音频：audio/mpeg, audio/wav, audio/ogg, audio/mp4, audio/m4a
    - 视频：video/mp4, video/webm, video/quicktime

    文件大小限制：50MB
    """
    # 验证 MIME 类型
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            400,
            f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )

    # 读取文件内容并验证大小
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            413,
            f"File too large ({len(contents)} bytes). Max: {MAX_FILE_SIZE} bytes (50MB)"
        )

    # 生成 upload_id 并保存文件
    cwd = directory_manager.get_current_cwd()
    upload_id = str(uuid.uuid4())
    upload_dir = Path(cwd) / ".helen" / "uploads" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 保存元数据
    metadata = {
        "upload_id": upload_id,
        "filename": file.filename,
        "mime_type": file.content_type,
        "size": len(contents),
        "created_at": datetime.now().isoformat(),
    }
    (upload_dir / "metadata.json").write_text(json.dumps(metadata))

    # 保存文件内容
    (upload_dir / "file").write_bytes(contents)

    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "mime_type": file.content_type,
        "size": len(contents),
        "url": f"/api/chat/uploads/{upload_id}/file",
    }


@router.get("/uploads/{upload_id}/file")
async def get_upload_file(upload_id: str):
    """获取已上传的文件

    通过 upload_id 访问已上传的文件，返回文件内容和正确的 MIME 类型。
    """
    # 验证 upload_id 格式（防止路径遍历）
    if not upload_id or "/" in upload_id or "\\" in upload_id or ".." in upload_id:
        raise HTTPException(400, "Invalid upload_id")

    cwd = directory_manager.get_current_cwd()
    upload_dir = Path(cwd) / ".helen" / "uploads" / upload_id
    file_path = upload_dir / "file"

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    # 读取 metadata 获取 MIME 类型
    metadata_path = upload_dir / "metadata.json"
    if not metadata_path.exists():
        raise HTTPException(404, "File metadata not found")

    metadata = json.loads(metadata_path.read_text())
    return FileResponse(file_path, media_type=metadata["mime_type"])
