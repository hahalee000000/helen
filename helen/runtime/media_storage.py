"""Large media external storage for Helen multimodal support.

Phase 3 (v1.17): Handles extraction and restoration of large media content
to/from session media directories, preventing JSONL bloat.

Design:
- When content >= threshold (default 1MB), extract to separate file
- JSONL stores media_ref with path, mime, media_type
- On read, restore original base64 content from file
- Threshold configurable via multimodal.media_external_threshold_mb
"""

from __future__ import annotations

import base64
import hashlib
import logging
import mimetypes
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default threshold: 1MB (base64 encoded size)
DEFAULT_EXTERNAL_THRESHOLD_MB = 1.0

# Media reference type marker in JSONL
MEDIA_REF_TYPE = "media_ref"


def _is_large_base64(content: str, threshold_bytes: int) -> bool:
    """Check if base64 content exceeds threshold.

    Args:
        content: Base64-encoded string
        threshold_bytes: Threshold in bytes

    Returns:
        True if content size >= threshold
    """
    # Base64 encoding adds ~33% overhead, so actual size is ~3/4 of encoded length
    estimated_size = len(content) * 3 // 4
    return estimated_size >= threshold_bytes


def _compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for deduplication.

    Args:
        content: Base64-encoded string

    Returns:
        First 16 chars of hex digest
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _guess_extension(mime: str) -> str:
    """Guess file extension from MIME type.

    Args:
        mime: MIME type (e.g., "image/png")

    Returns:
        File extension (e.g., ".png")
    """
    ext = mimetypes.guess_extension(mime)
    if ext:
        return ext
    # Fallback for common types
    mime_to_ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/ogg": ".ogg",
    }
    return mime_to_ext.get(mime, ".bin")


class MediaStorage:
    """Manages external storage of large media content.

    Attributes:
        session_dir: Session directory path
        media_dir: Media storage directory (session_dir/media)
        threshold_bytes: Size threshold for external storage
    """

    def __init__(
        self,
        session_dir: Path | str,
        threshold_mb: float = DEFAULT_EXTERNAL_THRESHOLD_MB,
    ):
        """Initialize media storage.

        Args:
            session_dir: Session directory path
            threshold_mb: Threshold in MB for external storage (default: 1.0)
        """
        self.session_dir = Path(session_dir)
        self.media_dir = self.session_dir / "media"
        self.threshold_bytes = int(threshold_mb * 1024 * 1024)

    def _ensure_media_dir(self) -> None:
        """Ensure media directory exists."""
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def extract_media(
        self,
        content: str,
        mime: str,
        media_type: str,
        content_hash: str | None = None,
    ) -> dict[str, Any]:
        """Extract large media to external file.

        Args:
            content: Base64-encoded content
            mime: MIME type (e.g., "image/png")
            media_type: Media type ("image", "video", "audio")
            content_hash: Optional pre-computed hash for filename

        Returns:
            Media reference dict with path, mime, media_type, size
        """
        self._ensure_media_dir()

        # Compute hash if not provided
        if content_hash is None:
            content_hash = _compute_content_hash(content)

        # Generate filename: <hash><extension>
        ext = _guess_extension(mime)
        filename = f"{content_hash}{ext}"
        filepath = self.media_dir / filename

        # Write content to file
        try:
            # Decode base64 and write binary
            binary_data = base64.b64decode(content)
            filepath.write_bytes(binary_data)
            logger.debug(
                "Extracted large media to %s (%d bytes)",
                filepath,
                len(binary_data),
            )
        except Exception as e:
            logger.error("Failed to extract media to %s: %s", filepath, e)
            raise

        # Return media reference
        return {
            "type": MEDIA_REF_TYPE,
            "path": str(filepath),
            "mime": mime,
            "media_type": media_type,
            "size": len(content),  # Base64 encoded size
        }

    def restore_media(self, media_ref: dict[str, Any]) -> str:
        """Restore media from external file.

        Args:
            media_ref: Media reference dict with path

        Returns:
            Base64-encoded content

        Raises:
            FileNotFoundError: If media file doesn't exist
        """
        filepath = Path(media_ref["path"])

        if not filepath.exists():
            raise FileNotFoundError(f"Media file not found: {filepath}")

        try:
            # Read binary and encode to base64
            binary_data = filepath.read_bytes()
            content = base64.b64encode(binary_data).decode("utf-8")
            logger.debug(
                "Restored media from %s (%d bytes)",
                filepath,
                len(binary_data),
            )
            return content
        except Exception as e:
            logger.error("Failed to restore media from %s: %s", filepath, e)
            raise

    def process_content_parts(
        self,
        content_parts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Process content parts, extracting large media.

        Scans content parts for large base64 data and extracts to external files.
        Returns modified content parts with media_ref for large content.

        Args:
            content_parts: List of content part dicts

        Returns:
            Modified content parts with media_ref for large content
        """
        processed = []

        for part in content_parts:
            if not isinstance(part, dict):
                processed.append(part)
                continue

            part_type = part.get("type")

            # Handle image_url with data URI
            if part_type == "image_url":
                image_url = part.get("image_url", {})
                url = image_url.get("url", "")
                if url.startswith("data:"):
                    # Parse data URI: data:<mime>;base64,<data>
                    try:
                        header, data = url.split(",", 1)
                        mime = header.split(":")[1].split(";")[0]
                        if _is_large_base64(data, self.threshold_bytes):
                            # Extract to external file
                            media_ref = self.extract_media(data, mime, "image")
                            processed.append({
                                "type": MEDIA_REF_TYPE,
                                **media_ref,
                            })
                            continue
                    except (ValueError, IndexError):
                        pass  # Not a valid data URI, keep as-is

            # Handle input_audio with base64 data
            elif part_type == "input_audio":
                audio_data = part.get("input_audio", {})
                data = audio_data.get("data", "")
                mime = audio_data.get("format", "audio/mp3")
                if data and _is_large_base64(data, self.threshold_bytes):
                    # Extract to external file
                    media_ref = self.extract_media(data, mime, "audio")
                    processed.append({
                        "type": MEDIA_REF_TYPE,
                        **media_ref,
                    })
                    continue

            # Keep other parts as-is
            processed.append(part)

        return processed

    def restore_content_parts(
        self,
        content_parts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Restore content parts, replacing media_ref with original data.

        Args:
            content_parts: List of content part dicts (may contain media_ref)

        Returns:
            Content parts with media_ref restored to original format
        """
        restored = []

        for part in content_parts:
            if not isinstance(part, dict):
                restored.append(part)
                continue

            part_type = part.get("type")

            # Handle media_ref
            if part_type == MEDIA_REF_TYPE:
                try:
                    # Restore original content
                    content = self.restore_media(part)
                    mime = part.get("mime", "application/octet-stream")
                    media_type = part.get("media_type", "image")

                    # Reconstruct original format based on media_type
                    if media_type == "image":
                        restored.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{content}",
                            },
                        })
                    elif media_type == "audio":
                        restored.append({
                            "type": "input_audio",
                            "input_audio": {
                                "data": content,
                                "format": mime,
                            },
                        })
                    elif media_type == "video":
                        # Video handling (future)
                        restored.append({
                            "type": "video_url",
                            "video_url": {
                                "url": f"data:{mime};base64,{content}",
                            },
                        })
                    else:
                        # Unknown media type, keep as media_ref
                        restored.append(part)
                except Exception as e:
                    logger.error("Failed to restore media_ref: %s", e)
                    # Keep media_ref as-is on error
                    restored.append(part)
                continue

            # Keep other parts as-is
            restored.append(part)

        return restored

    def cleanup(self) -> int:
        """Clean up media directory.

        Returns:
            Number of files deleted
        """
        if not self.media_dir.exists():
            return 0

        deleted = 0
        for filepath in self.media_dir.iterdir():
            if filepath.is_file():
                try:
                    filepath.unlink()
                    deleted += 1
                except Exception as e:
                    logger.error("Failed to delete %s: %s", filepath, e)

        # Try to remove empty media directory
        try:
            self.media_dir.rmdir()
        except OSError:
            pass  # Directory not empty or other error

        return deleted
