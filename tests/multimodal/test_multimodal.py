"""Tests for multimodal support (v1.17).

Tests for MediaPart, stdlib media functions, parser extensions,
semantic analysis, and interpreter multimodal handling.
"""

import os
import tempfile
import base64
import pytest

from helen.runtime.media import MediaPart
from helen.stdlib.media import (
    _media, _media_base64, _is_media, _media_type_fn,
    _guess_media_type, _guess_mime_from_url,
)


class TestMediaPart:
    """Tests for the MediaPart dataclass."""

    def test_create_image_from_file(self):
        """Test creating an image MediaPart from a file path."""
        part = MediaPart(
            source="file",
            content="/path/to/image.png",
            mime="image/png",
            media_type="image",
        )
        assert part.source == "file"
        assert part.content == "/path/to/image.png"
        assert part.mime == "image/png"
        assert part.media_type == "image"
        assert part.metadata == {}

    def test_create_video_from_url(self):
        """Test creating a video MediaPart from a URL."""
        part = MediaPart(
            source="url",
            content="https://example.com/video.mp4",
            mime="video/mp4",
            media_type="video",
        )
        assert part.source == "url"
        assert part.media_type == "video"

    def test_create_audio_from_base64(self):
        """Test creating an audio MediaPart from base64."""
        part = MediaPart(
            source="base64",
            content="SGVsbG8gV29ybGQ=",  # "Hello World" in base64
            mime="audio/mp3",
            media_type="audio",
            metadata={"duration": 10},
        )
        assert part.source == "base64"
        assert part.media_type == "audio"
        assert part.metadata == {"duration": 10}

    def test_invalid_source_raises_error(self):
        """Test that invalid source raises ValueError."""
        with pytest.raises(ValueError, match="Invalid source"):
            MediaPart(
                source="invalid",
                content="test",
                mime="image/png",
                media_type="image",
            )

    def test_invalid_media_type_raises_error(self):
        """Test that invalid media_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid media_type"):
            MediaPart(
                source="file",
                content="test",
                mime="image/png",
                media_type="invalid",
            )

    def test_empty_mime_raises_error(self):
        """Test that empty mime raises ValueError."""
        with pytest.raises(ValueError, match="mime type cannot be empty"):
            MediaPart(
                source="file",
                content="test",
                mime="",
                media_type="image",
            )

    def test_frozen_dataclass(self):
        """Test that MediaPart is frozen (immutable)."""
        part = MediaPart("file", "test.png", "image/png", "image")
        with pytest.raises(AttributeError):
            part.source = "url"

    def test_repr(self):
        """Test __repr__ output."""
        part = MediaPart("file", "test.png", "image/png", "image")
        assert "MediaPart" in repr(part)
        assert "image" in repr(part)
        assert "image/png" in repr(part)

    def test_str(self):
        """Test __str__ output."""
        part = MediaPart("file", "test.png", "image/png", "image")
        s = str(part)
        assert "Media" in s
        assert "image" in s


class TestMediaStdlibFunctions:
    """Tests for stdlib media functions."""

    def test_media_from_file_png(self):
        """Test media() with a PNG file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            f.flush()
            try:
                part = _media(f.name)
                assert part.source == "file"
                assert part.mime == "image/png"
                assert part.media_type == "image"
                assert part.content == f.name
            finally:
                os.unlink(f.name)

    def test_media_from_file_jpg(self):
        """Test media() with a JPG file."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            f.flush()
            try:
                part = _media(f.name)
                assert part.source == "file"
                assert part.mime in ("image/jpeg", "image/jpg")
                assert part.media_type == "image"
            finally:
                os.unlink(f.name)

    def test_media_from_file_video(self):
        """Test media() with a video file."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"\x00\x00\x00\x00" + b"\x00" * 100)
            f.flush()
            try:
                part = _media(f.name)
                assert part.source == "file"
                assert part.mime == "video/mp4"
                assert part.media_type == "video"
            finally:
                os.unlink(f.name)

    def test_media_from_file_audio(self):
        """Test media() with an audio file."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"\xff\xfb\x90\x00" + b"\x00" * 100)
            f.flush()
            try:
                part = _media(f.name)
                assert part.source == "file"
                assert part.mime == "audio/mpeg"
                assert part.media_type == "audio"
            finally:
                os.unlink(f.name)

    def test_media_from_url(self):
        """Test media() with a URL."""
        part = _media("https://example.com/image.png")
        assert part.source == "url"
        assert part.content == "https://example.com/image.png"
        assert part.mime == "image/png"
        assert part.media_type == "image"

    def test_media_from_url_video(self):
        """Test media() with a video URL."""
        part = _media("https://example.com/video.mp4")
        assert part.source == "url"
        assert part.mime == "video/mp4"
        assert part.media_type == "video"

    def test_media_explicit_type(self):
        """Test media() with explicit type parameter."""
        part = _media("https://example.com/file.dat", media_type="video")
        assert part.media_type == "video"

    def test_media_file_not_found(self):
        """Test media() with non-existent file."""
        with pytest.raises(ValueError, match="not found"):
            _media("/nonexistent/path/image.png")

    def test_media_base64(self):
        """Test media_base64() function."""
        data = base64.b64encode(b"test data").decode("utf-8")
        part = _media_base64(data, "image/png")
        assert part.source == "base64"
        assert part.content == data
        assert part.mime == "image/png"
        assert part.media_type == "image"

    def test_media_base64_with_explicit_type(self):
        """Test media_base64() with explicit type."""
        data = base64.b64encode(b"test data").decode("utf-8")
        part = _media_base64(data, "video/mp4", media_type="video")
        assert part.media_type == "video"

    def test_is_media_true(self):
        """Test is_media() returns True for MediaPart."""
        part = MediaPart("file", "test.png", "image/png", "image")
        assert _is_media(part) is True

    def test_is_media_false_string(self):
        """Test is_media() returns False for string."""
        assert _is_media("not a media") is False

    def test_is_media_false_none(self):
        """Test is_media() returns False for None."""
        assert _is_media(None) is False

    def test_is_media_false_dict(self):
        """Test is_media() returns False for dict."""
        assert _is_media({"type": "image"}) is False

    def test_media_type_image(self):
        """Test media_type() returns 'image' for image MediaPart."""
        part = MediaPart("file", "test.png", "image/png", "image")
        assert _media_type_fn(part) == "image"

    def test_media_type_video(self):
        """Test media_type() returns 'video' for video MediaPart."""
        part = MediaPart("file", "test.mp4", "video/mp4", "video")
        assert _media_type_fn(part) == "video"

    def test_media_type_audio(self):
        """Test media_type() returns 'audio' for audio MediaPart."""
        part = MediaPart("file", "test.mp3", "audio/mp3", "audio")
        assert _media_type_fn(part) == "audio"

    def test_media_type_non_media(self):
        """Test media_type() returns None for non-MediaPart."""
        assert _media_type_fn("not a media") is None
        assert _media_type_fn(42) is None
        assert _media_type_fn(None) is None


class TestGuessMediaType:
    """Tests for _guess_media_type helper."""

    def test_guess_image_png(self):
        assert _guess_media_type("image/png") == "image"

    def test_guess_image_jpeg(self):
        assert _guess_media_type("image/jpeg") == "image"

    def test_guess_video_mp4(self):
        assert _guess_media_type("video/mp4") == "video"

    def test_guess_audio_mp3(self):
        assert _guess_media_type("audio/mpeg") == "audio"

    def test_guess_unknown_defaults_to_image(self):
        assert _guess_media_type("application/octet-stream") == "image"

    def test_guess_none_defaults_to_image(self):
        assert _guess_media_type(None) == "image"


class TestGuessMimeFromUrl:
    """Tests for _guess_mime_from_url helper."""

    def test_guess_png(self):
        assert _guess_mime_from_url("https://example.com/image.png") == "image/png"

    def test_guess_jpg(self):
        assert _guess_mime_from_url("https://example.com/photo.jpg") == "image/jpeg"

    def test_guess_mp4(self):
        assert _guess_mime_from_url("https://example.com/video.mp4") == "video/mp4"

    def test_guess_with_query_string(self):
        assert _guess_mime_from_url("https://example.com/image.png?v=123") == "image/png"

    def test_guess_with_fragment(self):
        assert _guess_mime_from_url("https://example.com/image.png#section") == "image/png"

    def test_guess_unknown(self):
        assert _guess_mime_from_url("https://example.com/unknown") is None



class TestParserMultimodal:
    """Tests for parser multimodal extensions."""

    def _parse(self, source: str):
        """Helper to parse source code."""
        from helen.core.parser import Parser
        from helen.core.lexer import Scanner
        from helen.core.errors import ErrorReporter

        scanner = Scanner(source=source, file='<test>')
        tokens = scanner.scan_all()
        errors = ErrorReporter()
        parser = Parser(tokens, errors)
        program = parser.parse()
        return program.statements

    def test_parse_llm_act_with_media(self):
        """Test parsing llm act with media() call."""
        from helen.core.ast import LlmActExprNode

        source = 'llm act "describe this image" media("./photo.png")'
        stmts = self._parse(source)

        assert len(stmts) == 1
        expr_stmt = stmts[0]
        assert hasattr(expr_stmt, 'expression')
        llm_act = expr_stmt.expression
        assert isinstance(llm_act, LlmActExprNode)
        assert len(llm_act.media) == 1

    def test_parse_llm_act_with_multiple_media(self):
        """Test parsing llm act with multiple media() calls."""
        from helen.core.ast import LlmActExprNode

        source = 'llm act "compare" media("./a.png") media("./b.png")'
        stmts = self._parse(source)

        llm_act = stmts[0].expression
        assert isinstance(llm_act, LlmActExprNode)
        assert len(llm_act.media) == 2

    def test_parse_llm_act_with_on_media(self):
        """Test parsing llm act with on_media callback."""
        from helen.core.ast import LlmActExprNode

        source = '''llm act "describe" media("./photo.png")
            on_media fn(parts, provider) { parts }'''
        stmts = self._parse(source)

        llm_act = stmts[0].expression
        assert isinstance(llm_act, LlmActExprNode)
        assert llm_act.on_media is not None

    def test_parse_llm_act_with_on_generate(self):
        """Test parsing llm act with on_generate callback."""
        from helen.core.ast import LlmActExprNode

        source = '''llm act "generate an image"
            on_generate fn(params) { params.prompt }'''
        stmts = self._parse(source)

        llm_act = stmts[0].expression
        assert isinstance(llm_act, LlmActExprNode)
        assert len(llm_act.on_generate) == 1

    def test_parse_llm_act_with_multiple_on_generate(self):
        """Test parsing llm act with multiple on_generate callbacks."""
        from helen.core.ast import LlmActExprNode

        source = '''llm act "generate"
            on_generate fn(params) { "image" }
            on_generate fn(params) { "video" }'''
        stmts = self._parse(source)

        llm_act = stmts[0].expression
        assert isinstance(llm_act, LlmActExprNode)
        assert len(llm_act.on_generate) == 2

    def test_parse_llm_act_with_provider(self):
        """Test parsing llm act with provider() hint."""
        from helen.core.ast import LlmActExprNode

        source = 'llm act "describe" media("./photo.png") provider("anthropic")'
        stmts = self._parse(source)

        llm_act = stmts[0].expression
        assert isinstance(llm_act, LlmActExprNode)
        assert llm_act.provider is not None

    def test_parse_llm_act_full_multimodal(self):
        """Test parsing llm act with all multimodal features."""
        from helen.core.ast import LlmActExprNode

        source = '''llm act "analyze"
            media("./photo.png")
            provider("openai")
            on_media fn(parts, provider) { parts }
            on_generate fn(params) { "generated" }
            on_chunk fn(chunk) { print(chunk) }'''
        stmts = self._parse(source)

        llm_act = stmts[0].expression
        assert isinstance(llm_act, LlmActExprNode)
        assert len(llm_act.media) == 1
        assert llm_act.provider is not None
        assert llm_act.on_media is not None
        assert len(llm_act.on_generate) == 1
        assert llm_act.on_chunk is not None


class TestInterpreterMultimodal:
    """Tests for interpreter multimodal handling."""

    def test_build_user_message_text_only(self):
        """Test _build_user_message with text only."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime

        interp = Interpreter(HttpLLMRuntime())
        msg = interp._build_user_message("Hello", [], None, None)
        assert msg["role"] == "user"
        assert msg["content"] == "Hello"

    def test_build_user_message_with_media(self):
        """Test _build_user_message with media parts."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime
        from helen.runtime.media import MediaPart

        interp = Interpreter(HttpLLMRuntime())
        media_parts = [
            MediaPart("url", "https://example.com/image.png", "image/png", "image"),
        ]
        msg = interp._build_user_message("Describe this", media_parts, None, None)
        assert msg["role"] == "user"
        assert isinstance(msg["content"], list)
        assert len(msg["content"]) == 2
        assert msg["content"][0]["type"] == "text"
        assert msg["content"][0]["text"] == "Describe this"
        assert msg["content"][1]["type"] == "image_url"

    def test_default_media_adapter_image_url(self):
        """Test default media adapter with image URL."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime
        from helen.runtime.media import MediaPart

        interp = Interpreter(HttpLLMRuntime())
        media_parts = [
            MediaPart("url", "https://example.com/image.png", "image/png", "image"),
        ]
        parts = interp._default_media_adapter(media_parts, None)
        assert len(parts) == 1
        assert parts[0]["type"] == "image_url"
        assert parts[0]["image_url"]["url"] == "https://example.com/image.png"

    def test_default_media_adapter_image_base64(self):
        """Test default media adapter with base64 image."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime
        from helen.runtime.media import MediaPart

        interp = Interpreter(HttpLLMRuntime())
        b64_data = base64.b64encode(b"test").decode("utf-8")
        media_parts = [
            MediaPart("base64", b64_data, "image/png", "image"),
        ]
        parts = interp._default_media_adapter(media_parts, None)
        assert len(parts) == 1
        assert parts[0]["type"] == "image_url"
        assert f"data:image/png;base64,{b64_data}" in parts[0]["image_url"]["url"]

    def test_default_media_adapter_image_file(self):
        """Test default media adapter with file image."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime
        from helen.runtime.media import MediaPart

        interp = Interpreter(HttpLLMRuntime())
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
            f.flush()
            try:
                media_parts = [
                    MediaPart("file", f.name, "image/png", "image"),
                ]
                parts = interp._default_media_adapter(media_parts, None)
                assert len(parts) == 1
                assert parts[0]["type"] == "image_url"
                assert "data:image/png;base64," in parts[0]["image_url"]["url"]
            finally:
                os.unlink(f.name)

    def test_default_media_adapter_video_url(self):
        """Test default media adapter with video URL (fallback to text)."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime
        from helen.runtime.media import MediaPart

        interp = Interpreter(HttpLLMRuntime())
        media_parts = [
            MediaPart("url", "https://example.com/video.mp4", "video/mp4", "video"),
        ]
        parts = interp._default_media_adapter(media_parts, None)
        assert len(parts) == 1
        # Video falls back to text placeholder since most providers don't support native video
        assert parts[0]["type"] == "text"
        assert "视频" in parts[0]["text"]

    def test_default_media_adapter_audio(self):
        """Test default media adapter with audio."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime
        from helen.runtime.media import MediaPart

        interp = Interpreter(HttpLLMRuntime())
        b64_data = base64.b64encode(b"audio data").decode("utf-8")
        media_parts = [
            MediaPart("base64", b64_data, "audio/mp3", "audio"),
        ]
        parts = interp._default_media_adapter(media_parts, None)
        assert len(parts) == 1
        assert parts[0]["type"] == "input_audio"

    def test_build_generate_tools_single(self):
        """Test building a single generate tool."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime

        interp = Interpreter(HttpLLMRuntime())
        gen_fn = lambda params: "generated"
        tools = interp._build_generate_tools([gen_fn], "openai")
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "generate_media"
        assert "prompt" in tools[0]["function"]["parameters"]["properties"]
        assert tools[0]["_helen_generate_fn"] == gen_fn

    def test_build_generate_tools_multiple(self):
        """Test building multiple generate tools."""
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime

        interp = Interpreter(HttpLLMRuntime())
        gen_fn1 = lambda params: "image"
        gen_fn2 = lambda params: "video"
        tools = interp._build_generate_tools([gen_fn1, gen_fn2], None)
        assert len(tools) == 2
        assert tools[0]["function"]["name"] == "generate_media_1"
        assert tools[1]["function"]["name"] == "generate_media_2"


class TestTranscriptStoreIntegration:
    """Tests for multimodal + TranscriptStore SSOT integration (v1.17)."""

    def test_message_multimodal_content_type(self):
        """Test that Message supports multimodal content type."""
        from helen.runtime.history import Message

        # String content (traditional)
        msg_str = Message(role="user", content="Hello")
        assert msg_str.content == "Hello"

        # Multimodal content (v1.17)
        msg_multi = Message(role="user", content=[
            {"type": "text", "text": "Describe this"},
            {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
        ])
        assert isinstance(msg_multi.content, list)
        assert len(msg_multi.content) == 2

    def test_message_text_extraction(self):
        """Test _message_text helper extracts text from multimodal content."""
        from helen.runtime.history import _message_text

        # Plain string
        assert _message_text("Hello") == "Hello"

        # Multimodal list
        content = [
            {"type": "text", "text": "Describe this"},
            {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
            {"type": "text", "text": "in detail"},
        ]
        assert _message_text(content) == "Describe this\nin detail"

        # Empty content
        assert _message_text("") == ""
        assert _message_text([]) == ""
        assert _message_text(None) == ""

    def test_message_token_count_multimodal(self):
        """Test token counting for multimodal messages."""
        from helen.runtime.history import Message

        # Multimodal message: text parts + media parts
        msg = Message(role="user", content=[
            {"type": "text", "text": "Hello world"},
            {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
        ])
        # Text tokens + 85 for each non-text part
        tokens = msg.token_count
        assert tokens > 0
        assert tokens >= 85  # At least 1 media part

    def test_transcript_store_multimodal_roundtrip(self):
        """Test that TranscriptStore preserves multimodal content through save/load."""
        from helen.runtime.transcript_store import TranscriptStore, JSONLBackend
        from helen.runtime.history import Message
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"
            backend = JSONLBackend(path)
            store = TranscriptStore(backend=backend)

            # Add multimodal message
            multi_content = [
                {"type": "text", "text": "Describe this image"},
                {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
            ]
            msg = Message(role="user", content=multi_content)
            store.append(msg)
            backend.close()

            # Read back
            messages = store.read_view()
            assert len(messages) == 1
            assert isinstance(messages[0].content, list)
            assert len(messages[0].content) == 2
            assert messages[0].content[0]["type"] == "text"
            assert messages[0].content[1]["type"] == "image_url"

    def test_transcript_store_multimodal_persistence(self):
        """Test multimodal content persists across session reloads."""
        from helen.runtime.transcript_store import TranscriptStore, JSONLBackend
        from helen.runtime.history import Message
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"

            # Create and populate
            backend1 = JSONLBackend(path)
            store1 = TranscriptStore(backend=backend1)
            multi_content = [
                {"type": "text", "text": "Look at this"},
                {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
            ]
            store1.append(Message(role="user", content=multi_content))
            store1.append(Message(role="assistant", content="It's a cat"))
            backend1.close()

            # Reload via classmethod
            backend2 = JSONLBackend(path)
            store2 = TranscriptStore.load_from_backend(backend2)
            messages = store2.read_view()

            assert len(messages) == 2
            assert isinstance(messages[0].content, list)
            assert messages[0].content[0]["text"] == "Look at this"
            assert messages[1].content == "It's a cat"
            backend2.close()

    def test_compression_handles_multimodal(self):
        """Test that graduated compression doesn't crash on multimodal content."""
        from helen.runtime.graduated_compression import (
            _budget_reduction, _extract_global_stats,
        )
        from helen.runtime.history import Message

        # Create history with multimodal messages
        history = [
            Message(role="user", content=[
                {"type": "text", "text": "Describe this"},
                {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
            ]),
            Message(role="assistant", content="It's a cat"),
            Message(role="tool", content="Error: file not found"),
            Message(role="user", content="Try again"),
        ]

        # Layer 1: Budget reduction - should not crash
        result = _budget_reduction(history)
        assert len(result) == 4

        # Layer 4: Extract global stats - should not crash
        stats = _extract_global_stats(history)
        assert stats is not None

    def test_message_text_for_all_content_types(self):
        """Test _message_text handles all content type variations."""
        from helen.runtime.history import _message_text

        # String
        assert _message_text("hello") == "hello"

        # List with only text parts
        assert _message_text([{"type": "text", "text": "hello"}]) == "hello"

        # List with mixed parts
        assert _message_text([
            {"type": "text", "text": "hello"},
            {"type": "image_url", "image_url": {"url": "..."}},
            {"type": "text", "text": "world"},
        ]) == "hello\nworld"

        # List with only non-text parts (no text to extract)
        assert _message_text([
            {"type": "image_url", "image_url": {"url": "..."}},
        ]) == ""

        # Edge cases
        assert _message_text([]) == ""
        assert _message_text(None) == ""
        assert _message_text(42) == "42"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
