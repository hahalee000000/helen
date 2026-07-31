"""
Tests for transcript=memory and transcript=none modes with llm act media history.

Verifies that when an agent has transcript="memory" (in-memory only) or
transcript="none" (fallback to _interpreter_history), the following work correctly:
1. Media messages are correctly stored (memory→TranscriptStore, none→_interpreter_history)
2. Working memory is updated from messages (Phase 7)
3. _history property correctly returns messages with multimodal content
4. _prepare_history_for_llm preserves multimodal content format
5. enforce_limit and compression handle multimodal messages
"""
import unittest

from helen.interpreter.interpreter import Interpreter
from helen.runtime.history import Message, HistoryManager
from helen.runtime.transcript_store import TranscriptStore
from helen.interpreter.agent_context import AgentContextManager
from helen.runtime.working_memory import WorkingMemory


def _make_agent_context_with_memory_transcript():
    """Create an AgentContextManager with transcript_level='memory' configured."""
    agent_ctx = AgentContextManager.__new__(AgentContextManager)
    agent_ctx.working_memory_enabled = True
    agent_ctx._transcript_store_initialized = True
    agent_ctx._transcript_store_enabled = True
    agent_ctx.compression_enabled = False
    agent_ctx.cache_aware_enabled = False
    agent_ctx._compression_strategy = "none"
    agent_ctx.llm_client = None
    agent_ctx.working_memory = WorkingMemory(max_tokens=1000)
    agent_ctx._transcript_store = TranscriptStore()
    return agent_ctx


class TestTranscriptMemoryModeWithMedia(unittest.TestCase):
    """Test transcript=memory mode with multimodal (media) content."""

    def setUp(self):
        self.interp = Interpreter()
        self.agent_ctx = _make_agent_context_with_memory_transcript()
        self.store = self.agent_ctx._transcript_store
        self.interp._agent_context = self.agent_ctx
        self.interp._history_manager = HistoryManager()
        self.interp._current_invocation_id = "inv_test_123"
        self.interp._invocation_index = {
            "inv_test_123": {
                "transcript_level": "memory",
                "agent_name": "TestAgent",
            }
        }

    def test_media_message_written_to_transcript_store(self):
        """Media content (list[dict]) is correctly stored in transcript store."""
        media_content = [
            {"type": "text", "text": "请分析这张图片"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ]
        self.interp._add_to_history("user", media_content)

        self.assertEqual(len(self.store.transcript), 1)
        msg = self.store.transcript[0]
        self.assertEqual(msg.role, "user")
        self.assertIsInstance(msg.content, list)
        self.assertEqual(len(msg.content), 2)
        self.assertEqual(msg.content[0]["type"], "text")
        self.assertEqual(msg.content[1]["type"], "image_url")

    def test_working_memory_updated_in_memory_mode(self):
        """Working memory is updated even when transcript_level='memory'.

        Regression test: _add_to_history used to early-return after writing to
        TranscriptStore, skipping the working memory update (Phase 7).
        """
        media_content = [
            {"type": "text", "text": "请分析 /path/to/image.png"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ]
        self.interp._add_to_history("user", media_content)

        wm = self.agent_ctx.working_memory
        self.assertIn("/path/to/image.png", wm.active_files)

    def test_working_memory_updated_for_assistant_messages(self):
        """Working memory receives assistant messages in memory mode."""
        self.interp._add_to_history("user", "hello")
        self.interp._add_to_history("assistant", "I'll work on /src/main.py next.")

        wm = self.agent_ctx.working_memory
        self.assertIn("/src/main.py", wm.active_files)

    def test_history_property_returns_media_messages(self):
        """_history property returns messages with multimodal content intact."""
        media_content = [
            {"type": "text", "text": "看这张图"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,xyz"}},
        ]
        self.interp._add_to_history("user", media_content)
        self.interp._add_to_history("assistant", "这是一只猫")

        history = self.interp._history
        self.assertEqual(len(history), 2)
        self.assertIsInstance(history[0].content, list)
        self.assertEqual(history[1].content, "这是一只猫")

    def test_prepare_history_preserves_multimodal_content(self):
        """_prepare_history_for_llm preserves list[dict] multimodal content."""
        media_content = [
            {"type": "text", "text": "分析图片"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ]
        self.interp._add_to_history("user", media_content)
        self.interp._add_to_history("assistant", "好的")

        prepared = self.interp._prepare_history_for_llm(
            system_prompt="You are helpful.",
            current_prompt="分析图片",
        )
        self.assertIsNotNone(prepared)
        user_msgs = [m for m in prepared if m.get("role") == "user"]
        self.assertTrue(len(user_msgs) >= 1)
        last_user = user_msgs[-1]
        self.assertIsInstance(last_user["content"], list)
        types = [p["type"] for p in last_user["content"] if isinstance(p, dict)]
        self.assertIn("text", types)
        self.assertIn("image_url", types)

    def test_memory_mode_does_not_crash_without_backend(self):
        """Memory mode with no backend should not crash (persist=False path)."""
        self.assertIsNone(self.store._backend)
        self.interp._add_to_history("user", "hello")
        self.interp._add_to_history("assistant", "hi")
        self.assertEqual(len(self.store.transcript), 2)


class TestTranscriptMemoryModePlainText(unittest.TestCase):
    """Test transcript=memory mode with plain text (no media)."""

    def setUp(self):
        self.interp = Interpreter()
        self.agent_ctx = _make_agent_context_with_memory_transcript()
        self.store = self.agent_ctx._transcript_store
        self.interp._agent_context = self.agent_ctx
        self.interp._history_manager = HistoryManager()
        self.interp._current_invocation_id = "inv_test_456"
        self.interp._invocation_index = {
            "inv_test_456": {
                "transcript_level": "memory",
                "agent_name": "TestAgent",
            }
        }

    def test_plain_text_messages_stored_correctly(self):
        """Plain text messages work correctly in memory mode."""
        self.interp._add_to_history("user", "hello world")
        self.interp._add_to_history("assistant", "hi there")

        self.assertEqual(len(self.store.transcript), 2)
        self.assertEqual(self.store.transcript[0].content, "hello world")
        self.assertEqual(self.store.transcript[1].content, "hi there")

    def test_working_memory_updated_for_plain_text(self):
        """Working memory is updated for plain text messages in memory mode."""
        self.interp._add_to_history("user", "check /etc/config.yaml")
        wm = self.agent_ctx.working_memory
        self.assertIn("/etc/config.yaml", wm.active_files)


class TestTranscriptNoneModeWithMedia(unittest.TestCase):
    """Test transcript=none mode with multimodal (media) content.

    In 'none' mode, messages go to _interpreter_history (fallback path),
    not to TranscriptStore. Working memory must still be updated.
    """

    def setUp(self):
        self.interp = Interpreter()
        self.agent_ctx = _make_agent_context_with_memory_transcript()
        self.store = self.agent_ctx._transcript_store
        self.interp._agent_context = self.agent_ctx
        self.interp._history_manager = HistoryManager()
        self.interp._current_invocation_id = "inv_none_123"
        self.interp._invocation_index = {
            "inv_none_123": {
                "transcript_level": "none",
                "agent_name": "NoneTranscriptAgent",
            }
        }

    def _media_content(self, text="分析 /img/photo.png"):
        return [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgo="}},
        ]

    def test_messages_go_to_fallback_not_transcript_store(self):
        """In 'none' mode, messages go to _interpreter_history, not TranscriptStore."""
        self.interp._add_to_history("user", self._media_content())

        self.assertEqual(len(self.store.transcript), 0, "TranscriptStore should be empty")
        self.assertEqual(len(self.interp._interpreter_history), 1)
        msg = self.interp._interpreter_history[0]
        self.assertIsInstance(msg.content, list)
        self.assertEqual(msg.content[0]["type"], "text")
        self.assertEqual(msg.content[1]["type"], "image_url")

    def test_working_memory_updated_in_none_mode(self):
        """Working memory is updated in 'none' mode (same regression as memory mode)."""
        self.interp._add_to_history("user", self._media_content("看 /src/app.py"))

        wm = self.agent_ctx.working_memory
        self.assertIn("/src/app.py", wm.active_files)

    def test_history_property_reads_from_fallback(self):
        """_history reads from _interpreter_history in 'none' mode."""
        self.interp._add_to_history("user", self._media_content())
        self.interp._add_to_history("assistant", "好的")

        history = self.interp._history
        self.assertEqual(len(history), 2)
        self.assertIsInstance(history[0].content, list)
        self.assertEqual(history[1].content, "好的")

    def test_prepare_history_preserves_multimodal(self):
        """_prepare_history_for_llm preserves multimodal content in 'none' mode."""
        self.interp._add_to_history("user", self._media_content())
        self.interp._add_to_history("assistant", "看到了")

        prepared = self.interp._prepare_history_for_llm(
            system_prompt="help",
            current_prompt="分析图片",
        )
        self.assertIsNotNone(prepared)
        user_msgs = [m for m in prepared if m.get("role") == "user"]
        self.assertTrue(len(user_msgs) >= 1)
        self.assertIsInstance(user_msgs[-1]["content"], list)

    def test_enforce_limit_handles_multimodal(self):
        """enforce_limit correctly handles multimodal messages in fallback storage."""
        hm = self.interp._history_manager
        hm.MAX_TOKENS = 200
        hm.context_window = 400

        for i in range(5):
            mc = [
                {"type": "text", "text": f"图 {i}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{'a' * 500}"}},
            ]
            self.interp._add_to_history("user", mc)
            self.interp._add_to_history("assistant", f"结果 {i}")

        trimmed = hm.enforce_limit(self.interp._interpreter_history)
        # Multimodal messages that survive should be intact
        for m in trimmed:
            if isinstance(m.content, list):
                types = [p.get("type") for p in m.content if isinstance(p, dict)]
                self.assertIn("text", types)
                self.assertIn("image_url", types)

    def test_no_agent_ctx_fallback(self):
        """Without agent_ctx, messages go to _interpreter_history with multimodal intact."""
        interp2 = Interpreter()
        interp2._agent_context = None
        interp2._current_invocation_id = ""

        interp2._add_to_history("user", self._media_content())
        self.assertEqual(len(interp2._interpreter_history), 1)
        self.assertIsInstance(interp2._interpreter_history[0].content, list)


class TestMultimodalHistoryCompression(unittest.TestCase):
    """Test that compression (trim/summarize) correctly handles multimodal content."""

    def test_trim_preserves_multimodal_structure(self):
        """trim_history preserves multimodal messages (drops or keeps as whole)."""
        hm = HistoryManager()
        msgs = []
        for i in range(5):
            msgs.append(Message(role="user", content=[
                {"type": "text", "text": f"图 {i}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{'x' * 100}"}},
            ]))

        # High budget — all kept
        trimmed = hm.trim_history(msgs, budget=10000)
        self.assertEqual(len(trimmed), 5)
        self.assertTrue(all(isinstance(m.content, list) for m in trimmed))

        # Low budget — some dropped, survivors intact
        trimmed = hm.trim_history(msgs, budget=200)
        self.assertLess(len(trimmed), 5)
        for m in trimmed:
            self.assertIsInstance(m.content, list)

    def test_summarize_extracts_text_from_multimodal(self):
        """_summarize_compress extracts text from multimodal messages via _message_text."""
        hm = HistoryManager()
        hm.MAX_TOKENS = 100
        hm.context_window = 200

        msgs = []
        for i in range(10):
            if i % 2 == 0:
                content = [
                    {"type": "text", "text": f"看图 {i} /file{i}.png"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{'a' * 200}"}},
                ]
            else:
                content = f"回复 {i}"
            msgs.append(Message(role="user" if i % 2 == 0 else "assistant", content=content))

        trimmed = hm.enforce_limit(msgs)
        # If there's a summary system message, it should contain extracted text
        sys_msgs = [m for m in trimmed if m.role == "system"]
        if sys_msgs:
            summary = sys_msgs[0].content
            # The summary should contain text extracted from multimodal messages
            self.assertIn("[Previous conversation summary]", summary)
        # Surviving multimodal messages should be intact
        for m in trimmed:
            if isinstance(m.content, list):
                types = [p.get("type") for p in m.content if isinstance(p, dict)]
                self.assertIn("text", types)
                self.assertIn("image_url", types)

    def test_prepare_for_llm_preserves_multimodal(self):
        """HistoryManager.prepare_for_llm passes multimodal content through to API format."""
        hm = HistoryManager()
        msgs = [
            Message(role="user", content=[
                {"type": "text", "text": "看图"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            ]),
            Message(role="assistant", content="好的"),
        ]
        result = hm.prepare_for_llm(msgs, system_prompt="help", current_prompt="看图")
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0]["content"], list)
        self.assertEqual(result[0]["content"][0]["type"], "text")
        self.assertEqual(result[0]["content"][1]["type"], "image_url")
        self.assertEqual(result[1]["content"], "好的")


if __name__ == "__main__":
    unittest.main()
