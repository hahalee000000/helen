"""Tests for multimodal Phase 3: Large media external storage.

Tests MediaStorage, TranscriptStore integration, and configuration support.
"""

import base64
import tempfile
from pathlib import Path

import pytest

from helen.runtime.config import get_multimodal_config
from helen.runtime.history import Message
from helen.runtime.media_storage import (
    MediaStorage,
    _compute_content_hash,
    _guess_extension,
    _is_large_base64,
)
from helen.runtime.transcript_store import JSONLBackend, TranscriptStore


class TestMediaStorageHelpers:
    """Test MediaStorage helper functions."""

    def test_is_large_base64_threshold(self):
        """Test threshold detection for base64 content."""
        # 1MB = 1024 * 1024 bytes = 1048576 bytes
        # Base64 encoding adds ~33% overhead, so 1MB becomes ~1.33MB encoded
        # Threshold is on decoded size, so we need ~1.33MB encoded to represent 1MB decoded

        # Just under threshold (0.5MB decoded)
        small_content = base64.b64encode(b"x" * (512 * 1024)).decode("utf-8")
        assert not _is_large_base64(small_content, 1024 * 1024)

        # Just over threshold (1.5MB decoded)
        large_content = base64.b64encode(b"x" * int(1.5 * 1024 * 1024)).decode("utf-8")
        assert _is_large_base64(large_content, 1024 * 1024)

    def test_compute_content_hash(self):
        """Test content hash computation."""
        content1 = "test content 1"
        content2 = "test content 2"

        hash1 = _compute_content_hash(content1)
        hash2 = _compute_content_hash(content2)

        assert isinstance(hash1, str)
        assert len(hash1) == 16  # First 16 chars of hex digest
        assert hash1 != hash2

        # Same content should produce same hash
        hash1_again = _compute_content_hash(content1)
        assert hash1 == hash1_again

    def test_guess_extension(self):
        """Test MIME to extension mapping."""
        assert _guess_extension("image/png") == ".png"
        assert _guess_extension("image/jpeg") == ".jpg"
        assert _guess_extension("video/mp4") == ".mp4"
        assert _guess_extension("audio/mp3") == ".mp3"

        # Unknown MIME should return .bin
        assert _guess_extension("unknown/type") == ".bin"


class TestMediaStorage:
    """Test MediaStorage class."""

    def test_init_creates_media_dir(self, tmp_path):
        """Test that initialization creates media directory."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)
        assert storage.session_dir == tmp_path
        assert storage.media_dir == tmp_path / "media"
        assert storage.threshold_bytes == 1024 * 1024

        # Media dir is created on first use
        content = base64.b64encode(b"x" * int(1.5 * 1024 * 1024)).decode("utf-8")
        storage.extract_media(content, "image/png", "image")
        assert storage.media_dir.exists()

    def test_extract_media_creates_file(self, tmp_path):
        """Test that extract_media creates a file."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)

        # Create large content (1.5MB)
        original_data = b"x" * int(1.5 * 1024 * 1024)
        content = base64.b64encode(original_data).decode("utf-8")

        # Extract to external storage
        media_ref = storage.extract_media(content, "image/png", "image")

        # Check media_ref structure
        assert media_ref["type"] == "media_ref"
        assert "path" in media_ref
        assert media_ref["mime"] == "image/png"
        assert media_ref["media_type"] == "image"
        assert "size" in media_ref

        # Check file exists
        file_path = Path(media_ref["path"])
        assert file_path.exists()

        # Check file content matches original
        with open(file_path, "rb") as f:
            stored_data = f.read()
        assert stored_data == original_data

    def test_extract_media_with_custom_hash(self, tmp_path):
        """Test that extract_media uses custom hash if provided."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)

        content = base64.b64encode(b"test data").decode("utf-8")
        custom_hash = "abcdef1234567890"

        media_ref = storage.extract_media(
            content, "image/png", "image", content_hash=custom_hash
        )

        file_path = Path(media_ref["path"])
        assert custom_hash in file_path.name

    def test_restore_media_from_file(self, tmp_path):
        """Test that restore_media restores content from file."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)

        # Create and extract content
        original_data = b"test data for restoration"
        content = base64.b64encode(original_data).decode("utf-8")
        media_ref = storage.extract_media(content, "image/png", "image")

        # Restore content
        restored_content = storage.restore_media(media_ref)

        # Check restored content matches original
        assert restored_content == content

    def test_restore_media_file_not_found(self, tmp_path):
        """Test that restore_media raises error if file not found."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)

        media_ref = {
            "type": "media_ref",
            "path": str(tmp_path / "nonexistent.png"),
            "mime": "image/png",
            "media_type": "image",
        }

        with pytest.raises(FileNotFoundError):
            storage.restore_media(media_ref)

    def test_process_content_parts_extracts_large_media(self, tmp_path):
        """Test that process_content_parts extracts large media."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)

        # Create content parts with large image
        large_data = b"x" * int(1.5 * 1024 * 1024)
        large_b64 = base64.b64encode(large_data).decode("utf-8")

        content_parts = [
            {"type": "text", "text": "Look at this image"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{large_b64}"},
            },
        ]

        # Process content parts
        processed = storage.process_content_parts(content_parts)

        # Check that text part is unchanged
        assert processed[0] == content_parts[0]

        # Check that image part was replaced with media_ref
        assert processed[1]["type"] == "media_ref"
        assert processed[1]["mime"] == "image/png"
        assert processed[1]["media_type"] == "image"

        # Check that file was created
        file_path = Path(processed[1]["path"])
        assert file_path.exists()

    def test_process_content_parts_keeps_small_media(self, tmp_path):
        """Test that process_content_parts keeps small media inline."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)

        # Create content parts with small image
        small_data = b"small image"
        small_b64 = base64.b64encode(small_data).decode("utf-8")

        content_parts = [
            {"type": "text", "text": "Look at this image"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{small_b64}"},
            },
        ]

        # Process content parts
        processed = storage.process_content_parts(content_parts)

        # Check that both parts are unchanged (small media stays inline)
        assert processed == content_parts

    def test_restore_content_parts(self, tmp_path):
        """Test that restore_content_parts restores media_ref."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)

        # Create and extract large content
        large_data = b"x" * int(1.5 * 1024 * 1024)
        large_b64 = base64.b64encode(large_data).decode("utf-8")

        content_parts = [
            {"type": "text", "text": "Look at this image"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{large_b64}"},
            },
        ]

        # Process and then restore
        processed = storage.process_content_parts(content_parts)
        restored = storage.restore_content_parts(processed)

        # Check that content is restored to original format
        assert restored[0] == content_parts[0]
        assert restored[1]["type"] == "image_url"
        assert restored[1]["image_url"]["url"] == content_parts[1]["image_url"]["url"]

    def test_cleanup_removes_media_files(self, tmp_path):
        """Test that cleanup removes media files."""
        storage = MediaStorage(tmp_path, threshold_mb=1.0)

        # Create multiple media files
        for i in range(3):
            content = base64.b64encode(f"data {i}".encode()).decode("utf-8")
            storage.extract_media(content, "image/png", "image")

        # Check files exist
        media_files = list(storage.media_dir.glob("*"))
        assert len(media_files) == 3

        # Cleanup
        deleted_count = storage.cleanup()
        assert deleted_count == 3

        # Check files are removed
        media_files = list(storage.media_dir.glob("*"))
        assert len(media_files) == 0


class TestTranscriptStoreIntegration:
    """Test TranscriptStore integration with MediaStorage."""

    def test_transcript_store_with_session_dir(self, tmp_path):
        """Test that TranscriptStore initializes MediaStorage when session_dir provided."""
        store = TranscriptStore(session_dir=tmp_path)
        assert store._media_storage is not None
        assert store._media_storage.session_dir == tmp_path

    def test_transcript_store_without_session_dir(self, tmp_path):
        """Test that TranscriptStore works without session_dir."""
        store = TranscriptStore()
        assert store._media_storage is None

    def test_append_extracts_large_media(self, tmp_path):
        """Test that append extracts large media to external storage."""
        store = TranscriptStore(session_dir=tmp_path)

        # Create message with large media
        large_data = b"x" * int(1.5 * 1024 * 1024)
        large_b64 = base64.b64encode(large_data).decode("utf-8")

        message = Message(
            role="user",
            content=[
                {"type": "text", "text": "Look at this"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{large_b64}"},
                },
            ],
        )

        # Append message
        store.append(message)

        # Check that content was replaced with media_ref
        assert isinstance(message.content, list)
        assert message.content[0]["type"] == "text"
        assert message.content[1]["type"] == "media_ref"

        # Check that file was created
        file_path = Path(message.content[1]["path"])
        assert file_path.exists()

    def test_read_view_restores_media(self, tmp_path):
        """Test that read_view restores media references."""
        store = TranscriptStore(session_dir=tmp_path)

        # Create message with large media
        large_data = b"x" * int(1.5 * 1024 * 1024)
        large_b64 = base64.b64encode(large_data).decode("utf-8")

        original_content = [
            {"type": "text", "text": "Look at this"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{large_b64}"},
            },
        ]

        message = Message(role="user", content=original_content)
        store.append(message)

        # Read view
        view = store.read_view()

        # Check that media was restored
        assert len(view) == 1
        assert isinstance(view[0].content, list)
        assert view[0].content[0]["type"] == "text"
        assert view[0].content[1]["type"] == "image_url"
        assert view[0].content[1]["image_url"]["url"] == original_content[1]["image_url"]["url"]

    def test_persistence_with_media(self, tmp_path):
        """Test that media persists across store reloads."""
        # Create store and add message with large media
        backend_path = tmp_path / "transcript.jsonl"
        backend = JSONLBackend(backend_path)

        store1 = TranscriptStore(backend=backend, session_dir=tmp_path)

        large_data = b"x" * int(1.5 * 1024 * 1024)
        large_b64 = base64.b64encode(large_data).decode("utf-8")

        original_content = [
            {"type": "text", "text": "Persistent media"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{large_b64}"},
            },
        ]

        message = Message(role="user", content=original_content)
        store1.append(message)
        backend.close()

        # Reload store from backend
        backend2 = JSONLBackend(backend_path)
        store2 = TranscriptStore.load_from_backend(backend2, session_dir=tmp_path)

        # Read view
        view = store2.read_view()

        # Check that media was restored
        assert len(view) == 1
        assert isinstance(view[0].content, list)
        assert view[0].content[0]["type"] == "text"
        assert view[0].content[0]["text"] == "Persistent media"
        assert view[0].content[1]["type"] == "image_url"
        assert view[0].content[1]["image_url"]["url"] == original_content[1]["image_url"]["url"]

        backend2.close()


class TestMultimodalConfig:
    """Test multimodal configuration support."""

    def test_get_multimodal_config_defaults(self):
        """Test that get_multimodal_config returns defaults."""
        config = get_multimodal_config()

        assert config["max_media_size_mb"] == 20.0
        assert config["max_media_per_request"] == 10
        assert config["media_external_threshold_mb"] == 1.0
        assert "media_cache_dir" in config
        assert config["video_frame_interval"] == 1.0

    def test_threshold_affects_extraction(self, tmp_path):
        """Test that threshold configuration affects extraction."""
        # Create storage with 2MB threshold
        storage = MediaStorage(tmp_path, threshold_mb=2.0)

        # Create content just over 1MB but under 2MB
        data = b"x" * int(1.5 * 1024 * 1024)
        content = base64.b64encode(data).decode("utf-8")

        content_parts = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{content}"},
            }
        ]

        # Process - should NOT extract (under 2MB threshold)
        processed = storage.process_content_parts(content_parts)
        assert processed[0]["type"] == "image_url"

        # Create storage with 1MB threshold
        storage_small = MediaStorage(tmp_path, threshold_mb=1.0)

        # Process - should extract (over 1MB threshold)
        processed_small = storage_small.process_content_parts(content_parts)
        assert processed_small[0]["type"] == "media_ref"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
