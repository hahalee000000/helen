"""MediaPart dataclass for multimodal content in Helen.

This module defines the MediaPart type, which represents multimodal content
(images, video, audio) that can be passed to llm act expressions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MediaPart:
    """Represents a piece of multimodal content.

    MediaPart is a first-class citizen in Helen - it can be assigned to variables,
    passed as function arguments, stored in lists, etc.

    Attributes:
        source: Where the content comes from - "file", "url", or "base64"
        content: The actual content - file path, URL, or base64-encoded string
        mime: MIME type - "image/png", "video/mp4", "audio/mp3", etc.
        media_type: High-level type - "image", "video", or "audio"
        metadata: Additional parameters (detail, alt, etc.)
    """
    source: str          # "file" | "url" | "base64"
    content: str         # file path / URL / base64 string
    mime: str            # "image/png", "video/mp4", "audio/mp3" etc.
    media_type: str      # "image" | "video" | "audio"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate field values."""
        valid_sources = {"file", "url", "base64"}
        if self.source not in valid_sources:
            raise ValueError(f"Invalid source: {self.source}. Must be one of {valid_sources}")

        valid_media_types = {"image", "video", "audio"}
        if self.media_type not in valid_media_types:
            raise ValueError(f"Invalid media_type: {self.media_type}. Must be one of {valid_media_types}")

        if not self.mime:
            raise ValueError("mime type cannot be empty")

    def __repr__(self) -> str:
        """Return a readable representation."""
        return f"MediaPart(source={self.source!r}, media_type={self.media_type!r}, mime={self.mime!r})"

    def __str__(self) -> str:
        """Return a string representation for display."""
        return f"<Media:{self.media_type} {self.source}:{self.content[:50]}{'...' if len(self.content) > 50 else ''}>"
