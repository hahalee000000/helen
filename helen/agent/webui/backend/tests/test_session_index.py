"""session_index 模块单元测试

v6.1:transcript 唯一数据源。覆盖 transcript_to_messages / read_session_preview /
_parse_user_content / _extract_from_boilerplate(prompt boilerplate 过滤)。

运行: cd webui/backend && pytest tests/test_session_index.py -v
"""

import json
import pytest


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def temp_agent_dir(tmp_path):
    """临时 agent 根目录"""
    agent_dir = tmp_path / "helenagent"
    agent_dir.mkdir()
    (agent_dir / ".helen").mkdir()
    return agent_dir


@pytest.fixture
def session_index(temp_agent_dir):
    """带临时目录的 session_index 模块"""
    from app.services import session_index, directory_manager
    from unittest.mock import patch
    original_agent_dir = session_index._AGENT_DIR
    session_index._AGENT_DIR = temp_agent_dir
    with patch.object(directory_manager, "get_current_cwd", return_value=str(temp_agent_dir)):
        yield session_index
    session_index._AGENT_DIR = original_agent_dir


def _write_transcript(agent_dir, sid, lines):
    """在 temp_agent_dir 下创建 transcript 文件"""
    sessions_dir = agent_dir / ".helen" / "sessions" / sid
    sessions_dir.mkdir(parents=True, exist_ok=True)
    (sessions_dir / "transcript.jsonl").write_text("".join(l + "\n" for l in lines))


# ── prompt boilerplate 过滤 ────────────────────────────────────

class TestExtractFromBoilerplate:
    def test_no_boilerplate(self, session_index):
        """无 prompt boilerplate -> 原样返回"""
        text, boilerplate = session_index._extract_from_boilerplate("你好")
        assert text == "你好"
        assert boilerplate == ""

    def test_with_boilerplate(self, session_index):
        """含 prompt boilerplate -> 分离用户输入"""
        content = "## Identity\nYou are HelenAgent\n## Reminders\nIMPORTANT: ...\n\n用户实际输入"
        text, boilerplate = session_index._extract_from_boilerplate(content)
        assert text == "用户实际输入"
        assert "## Identity" in boilerplate

    def test_pure_boilerplate_no_user_input(self, session_index):
        """纯 boilerplate 无用户输入 -> user_text 为空"""
        content = "## Identity\nYou are HelenAgent\n## Reminders\nIMPORTANT: ..."
        text, _ = session_index._extract_from_boilerplate(content)
        assert text == ""

    def test_no_identity_marker(self, session_index):
        """不以 ## Identity 开头 -> 不识别为 boilerplate"""
        content = "## 其他标题\n\n用户输入"
        text, boilerplate = session_index._extract_from_boilerplate(content)
        assert text == content
        assert boilerplate == ""


# ── _parse_user_content ─────────────────────────────────────────

class TestParseUserContent:
    def test_plain_string(self, session_index):
        """纯文本 user message"""
        text, hints, media, has_cmd = session_index._parse_user_content("你好")
        assert text == "你好"
        assert hints == []
        assert media == []
        assert has_cmd is False

    def test_internal_command(self, session_index):
        """内部协议命令 __helen_xxx__ -> has_internal_command"""
        text, _, _, has_cmd = session_index._parse_user_content("__helen_resume__abc")
        assert has_cmd is True
        assert text == ""

    def test_multimodal_with_image(self, session_index):
        """多模态:image_url part 提取为 Attachment"""
        content = [
            {"type": "text", "text": "这是什么?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ]
        text, _, attachments, has_cmd = session_index._parse_user_content(content)
        assert text == "这是什么?"
        assert len(attachments) == 1
        assert attachments[0]["mime_type"] == "image/png"
        assert attachments[0]["url"].startswith("data:image/png;base64,")
        assert has_cmd is False

    def test_media_ref_attachment(self, session_index):
        """media_ref:Helen 的 session media 引用转 HTTP URL"""
        content = [
            {"type": "text", "text": "描述图片"},
            {"type": "media_ref", "path": "/home/x/p/.helen/sessions/sid-1/media/img.png",
             "mime": "image/png", "size": 1234},
        ]
        text, _, attachments, _ = session_index._parse_user_content(content)
        assert text == "描述图片"
        assert len(attachments) == 1
        assert attachments[0]["filename"] == "img.png"
        assert attachments[0]["mime_type"] == "image/png"
        assert attachments[0]["size"] == 1234
        assert attachments[0]["url"] == "/api/chat/sessions/sid-1/media/img.png"

    def test_system_hint_filtered(self, session_index):
        """[System Hint] 行被过滤到 hints"""
        text, hints, _, _ = session_index._parse_user_content("[System Hint] 提示内容\n用户输入")
        assert "用户输入" in text
        assert "[System Hint]" not in text
        assert hints == ["提示内容"]


# ── transcript_to_messages ─────────────────────────────────────

class TestTranscriptToMessages:
    def test_filters_session_meta_and_boundary(self, session_index, temp_agent_dir):
        """跳过 session_meta / boundary_marker"""
        sid = "test-session"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 123.0}),
            json.dumps({"type": "message", "role": "user", "content": "你好", "uuid": "u1"}),
            json.dumps({"type": "boundary_marker"}),
            json.dumps({"type": "message", "role": "assistant", "content": "你好!", "uuid": "a1"}),
        ])
        msgs = session_index.transcript_to_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "你好"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "你好!"

    def test_filters_prompt_boilerplate(self, session_index, temp_agent_dir):
        """user message 含 prompt boilerplate -> 只保留用户输入"""
        sid = "test-session"
        boilerplate = "## Identity\nYou are HelenAgent\n## Reminders\nIMPORTANT: ...\n\n用户实际输入"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 123.0}),
            json.dumps({"type": "message", "role": "user", "content": boilerplate, "uuid": "u1"}),
            json.dumps({"type": "message", "role": "assistant", "content": "收到", "uuid": "a1"}),
        ])
        msgs = session_index.transcript_to_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["content"] == "用户实际输入"
        assert msgs[1]["content"] == "收到"

    def test_pure_boilerplate_skipped(self, session_index, temp_agent_dir):
        """纯 boilerplate 无用户输入的 user message -> 跳过"""
        sid = "test-session"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 123.0}),
            json.dumps({"type": "message", "role": "user", "content": "## Identity\nYou are HelenAgent\n## Reminders\nIMPORTANT: ...", "uuid": "u1"}),
            json.dumps({"type": "message", "role": "user", "content": "真实输入", "uuid": "u2"}),
        ])
        msgs = session_index.transcript_to_messages(sid)
        assert len(msgs) == 1
        assert msgs[0]["content"] == "真实输入"

    def test_multimodal_attachments(self, session_index, temp_agent_dir):
        """多模态 user message -> 附件提取为 Attachment"""
        sid = "test-session"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 123.0}),
            json.dumps({"type": "message", "role": "user", "content": [
                {"type": "text", "text": "看图"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            ], "uuid": "u1"}),
        ])
        msgs = session_index.transcript_to_messages(sid)
        assert len(msgs) == 1
        assert msgs[0]["content"] == "看图"
        assert len(msgs[0]["attachments"]) == 1
        assert msgs[0]["attachments"][0]["mime_type"] == "image/png"

    def test_test_messages_filtered(self, session_index, temp_agent_dir):
        """[TEST] 消息被过滤"""
        sid = "test-session"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 123.0}),
            json.dumps({"type": "message", "role": "user", "content": "[TEST] 测试消息", "uuid": "u1"}),
            json.dumps({"type": "message", "role": "user", "content": "真实输入", "uuid": "u2"}),
        ])
        msgs = session_index.transcript_to_messages(sid)
        assert len(msgs) == 1
        assert msgs[0]["content"] == "真实输入"

    def test_timestamp_from_session_meta(self, session_index, temp_agent_dir):
        """timestamp 取自 session_meta"""
        sid = "test-session"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 999.0}),
            json.dumps({"type": "message", "role": "user", "content": "你好", "uuid": "u1"}),
        ])
        msgs = session_index.transcript_to_messages(sid)
        assert msgs[0]["timestamp"] == 999.0


# ── read_session_preview ───────────────────────────────────────

class TestReadSessionPreview:
    def test_preview_first_user_message(self, session_index, temp_agent_dir):
        """预览取首条 user 消息"""
        sid = "test-session"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 123.0}),
            json.dumps({"type": "message", "role": "user", "content": "这是首条消息", "uuid": "u1"}),
            json.dumps({"type": "message", "role": "assistant", "content": "回复", "uuid": "a1"}),
        ])
        preview = session_index.read_session_preview(sid)
        assert preview == "这是首条消息"

    def test_preview_filters_boilerplate(self, session_index, temp_agent_dir):
        """预览过滤 prompt boilerplate"""
        sid = "test-session"
        boilerplate = "## Identity\nYou are HelenAgent\n## Reminders\nIMPORTANT: ...\n\n用户实际输入"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 123.0}),
            json.dumps({"type": "message", "role": "user", "content": boilerplate, "uuid": "u1"}),
        ])
        preview = session_index.read_session_preview(sid)
        assert preview == "用户实际输入"

    def test_preview_empty_session(self, session_index, temp_agent_dir):
        """空 session -> 空预览"""
        sid = "test-session"
        _write_transcript(temp_agent_dir, sid, [
            json.dumps({"type": "session_meta", "timestamp": 123.0}),
        ])
        preview = session_index.read_session_preview(sid)
        assert preview == ""
