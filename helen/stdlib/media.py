"""Media stdlib functions for multimodal support.

This module provides stdlib functions for creating and inspecting MediaPart objects:
- media(source, type?): Create a MediaPart from a file path or URL
- media_base64(data, mime, type?): Create a MediaPart from base64 data
- is_media(value): Check if a value is a MediaPart
- media_type(value): Get the media type of a MediaPart
"""

from __future__ import annotations

import base64
import mimetypes
import os
from typing import Any

from helen.runtime.media import MediaPart


def _media(source: str, media_type: str | None = None) -> MediaPart:
    """Create a MediaPart from a file path or URL.

    Args:
        source: File path or URL
        media_type: Optional explicit media type ("image", "video", "audio")

    Returns:
        MediaPart object

    Raises:
        ValueError: If the file doesn't exist or type cannot be determined
    """
    # Determine source type
    if source.startswith(("http://", "https://", "//")):
        source_type = "url"
        content = source
        mime = _guess_mime_from_url(source)
    else:
        # File path
        source_type = "file"
        if not os.path.exists(source):
            raise ValueError(f"Media file not found: {source}")
        if not os.path.isfile(source):
            raise ValueError(f"Media path is not a file: {source}")
        content = source
        mime = mimetypes.guess_type(source)[0]

    # Determine media type
    if media_type is None:
        media_type = _guess_media_type(mime)

    # If mime is unknown but media_type is explicit, use a default mime
    if mime is None:
        if media_type == "video":
            mime = "video/mp4"
        elif media_type == "audio":
            mime = "audio/mp3"
        else:
            mime = "image/png"  # Default to PNG for images

    return MediaPart(
        source=source_type,
        content=content,
        mime=mime,
        media_type=media_type,
    )


def _media_base64(data: str, mime: str, media_type: str | None = None) -> MediaPart:
    """Create a MediaPart from base64-encoded data.

    Args:
        data: Base64-encoded string
        mime: MIME type (e.g., "image/png", "video/mp4")
        media_type: Optional explicit media type ("image", "video", "audio")

    Returns:
        MediaPart object
    """
    if media_type is None:
        media_type = _guess_media_type(mime)

    return MediaPart(
        source="base64",
        content=data,
        mime=mime,
        media_type=media_type,
    )


def _is_media(value: Any) -> bool:
    """Check if a value is a MediaPart.

    Args:
        value: Any value to check

    Returns:
        True if value is a MediaPart, False otherwise
    """
    return isinstance(value, MediaPart)


def _media_type_fn(value: Any) -> str | None:
    """Get the media type of a MediaPart.

    Args:
        value: Value to check

    Returns:
        Media type ("image", "video", "audio") if value is a MediaPart, None otherwise
    """
    if isinstance(value, MediaPart):
        return value.media_type
    return None


def _guess_media_type(mime: str | None) -> str:
    """Guess the high-level media type from a MIME type.

    Args:
        mime: MIME type string (e.g., "image/png")

    Returns:
        High-level type: "image", "video", or "audio"
    """
    if mime is None:
        return "image"  # Default to image

    if mime.startswith("image/"):
        return "image"
    elif mime.startswith("video/"):
        return "video"
    elif mime.startswith("audio/"):
        return "audio"
    else:
        # Default to image for unknown types
        return "image"


def _guess_mime_from_url(url: str) -> str | None:
    """Guess MIME type from a URL.

    Args:
        url: URL string

    Returns:
        Guessed MIME type or None
    """
    # Remove query string and fragment
    path = url.split("?")[0].split("#")[0]
    return mimetypes.guess_type(path)[0]
