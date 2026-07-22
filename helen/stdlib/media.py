"""Media stdlib functions for multimodal support.

This module provides stdlib functions for creating and inspecting MediaPart objects:
- media(source, type?): Create a MediaPart from a file path or URL
- media_base64(data, mime, type?): Create a MediaPart from base64 data
- is_media(value): Check if a value is a MediaPart
- media_type(value): Get the media type of a MediaPart
"""

from __future__ import annotations

import base64
import hashlib
import mimetypes
import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any

from helen.runtime.media import MediaPart


def _media(*args, media_type: str | None = None) -> MediaPart | list[MediaPart]:
    """Create a MediaPart from a file path, URL, or passthrough existing MediaParts.

    v1.25: Supports MediaPart passthrough and multi-argument form (Issue #17):
    - ``media("path.png")`` -> single MediaPart (backward compatible)
    - ``media(img1)`` -> passthrough (img1 is MediaPart, returned as-is)
    - ``media(img1, img2)`` -> list[MediaPart] (multi-arg, all passthrough/created)
    - ``media("path.png", "image")`` -> single MediaPart (legacy positional type)
    - ``media("url", media_type="video")`` -> single MediaPart (keyword type)

    v1.25.1: Supports dynamic list flattening (no spread syntax needed):
    - ``media(images)`` -> list[MediaPart] (images is list[MediaPart|str])
    - Enables ``llm act "..." media(images)`` for dynamic-length lists

    Args:
        *args: One or more sources (file path/URL strings, MediaPart objects,
            or a single list of the same).
        media_type: Optional explicit media type ("image", "video", "audio").
            Only applies when a single string source is given.

    Returns:
        MediaPart for single str/MediaPart arg, list[MediaPart] for multi-arg
        or single list arg.

    Raises:
        ValueError: If the file doesn't exist or type cannot be determined.
        TypeError: If an argument is neither str, MediaPart, nor list.
    """
    if len(args) == 0:
        raise ValueError("media() requires at least one argument")

    # Legacy positional form: media(source, type) where the second positional
    # arg is a valid media_type string ("image"/"video"/"audio"). Disambiguated
    # from multi-source form (e.g. media("a.png", "b.png")) by checking validity.
    _VALID_MEDIA_TYPES = {"image", "video", "audio"}
    if (len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], str)
            and args[1] in _VALID_MEDIA_TYPES and media_type is None):
        return _create_media_part(args[0], media_type=args[1])

    # Single argument: passthrough MediaPart, create from string, or flatten list.
    if len(args) == 1:
        source = args[0]
        if isinstance(source, MediaPart):
            return source
        if isinstance(source, str):
            return _create_media_part(source, media_type=media_type)
        if isinstance(source, list):
            # Flatten list of MediaPart/str into list[MediaPart].
            return _flatten_media_list(source, media_type=media_type)
        raise TypeError(
            f"media() argument must be str, MediaPart, or list, got {type(source).__name__}"
        )

    # Multiple arguments: return list of MediaParts (each passthrough or created).
    parts: list[MediaPart] = []
    for arg in args:
        if isinstance(arg, MediaPart):
            parts.append(arg)
        elif isinstance(arg, str):
            parts.append(_create_media_part(arg, media_type=media_type))
        elif isinstance(arg, list):
            parts.extend(_flatten_media_list(arg, media_type=media_type))
        else:
            raise TypeError(
                f"media() argument must be str, MediaPart, or list, got {type(arg).__name__}"
            )
    return parts


def _flatten_media_list(items: list, media_type: str | None = None) -> list[MediaPart]:
    """Flatten a list of MediaPart/str into list[MediaPart].

    Args:
        items: List of MediaPart objects and/or file path/URL strings.
        media_type: Optional explicit media type for string items.

    Returns:
        list[MediaPart]

    Raises:
        TypeError: If an item is neither str nor MediaPart.
    """
    parts: list[MediaPart] = []
    for item in items:
        if isinstance(item, MediaPart):
            parts.append(item)
        elif isinstance(item, str):
            parts.append(_create_media_part(item, media_type=media_type))
        else:
            raise TypeError(
                f"media() list item must be str or MediaPart, got {type(item).__name__}"
            )
    return parts


def _create_media_part(source: str, media_type: str | None = None) -> MediaPart:
    """Create a MediaPart from a file path or URL (original _media logic).

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


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read_media_as_base64(part: MediaPart) -> str:
    """Resolve any MediaPart source to a raw base64 string.

    Args:
        part: A MediaPart object

    Returns:
        Raw base64-encoded string (no ``data:`` prefix)

    Raises:
        TypeError: If part is not a MediaPart
        ValueError: If file not found or URL download fails
    """
    if not isinstance(part, MediaPart):
        raise TypeError(f"Expected MediaPart, got {type(part).__name__}")

    if part.source == "base64":
        return part.content

    if part.source == "file":
        if not os.path.exists(part.content):
            raise ValueError(f"Media file not found: {part.content}")
        if not os.path.isfile(part.content):
            raise ValueError(f"Media path is not a file: {part.content}")
        with open(part.content, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    if part.source == "url":
        try:
            req = urllib.request.Request(part.content)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            return base64.b64encode(data).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to download media from URL: {part.content}: {e}")

    raise ValueError(f"Unknown MediaPart source: {part.source!r}")


# ── Format adapters ───────────────────────────────────────────────────────────

def _to_openai_parts(parts: list) -> list[dict]:
    """Convert MediaPart list to OpenAI-compatible content parts.

    Produces the content array format used by OpenAI Chat Completions API
    and most compatible providers (Azure, OpenRouter, etc.).

    Args:
        parts: List of MediaPart objects (non-MediaPart items are skipped)

    Returns:
        List of content part dicts in OpenAI format

    Note:
        - Images: ``{type: "image_url", image_url: {url: ...}}``
        - Audio URL: ``{type: "audio_url", audio_url: {url: ...}}``
        - Audio inline: ``{type: "input_audio", input_audio: {data, format}}``
        - Video: falls back to text placeholder ``[视频: ...]``
        - File read errors are silently skipped
    """
    result = []
    for m in parts:
        if not isinstance(m, MediaPart):
            continue

        if m.media_type == "image":
            if m.source == "url":
                result.append({
                    "type": "image_url",
                    "image_url": {"url": m.content},
                })
            elif m.source == "base64":
                result.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{m.mime};base64,{m.content}"},
                })
            elif m.source == "file":
                try:
                    b64 = _read_media_as_base64(m)
                    result.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{m.mime};base64,{b64}"},
                    })
                except (ValueError, OSError):
                    continue

        elif m.media_type == "video":
            # Most LLM providers don't support native video input.
            video_desc = f"[视频: {m.content if m.source == 'url' else m.media_type}]"
            result.append({"type": "text", "text": video_desc})

        elif m.media_type == "audio":
            if m.source == "url":
                result.append({
                    "type": "audio_url",
                    "audio_url": {"url": m.content},
                })
            elif m.source in ("base64", "file"):
                data = m.content
                if m.source == "file":
                    try:
                        data = _read_media_as_base64(m)
                    except (ValueError, OSError):
                        continue
                result.append({
                    "type": "input_audio",
                    "input_audio": {"data": data, "format": m.mime},
                })

    return result


def _to_claude_parts(parts: list) -> list[dict]:
    """Convert MediaPart list to Anthropic Claude content blocks.

    Produces the content block format used by the Anthropic Messages API.

    Args:
        parts: List of MediaPart objects (non-MediaPart items are skipped)

    Returns:
        List of content block dicts in Claude format

    Raises:
        ValueError: If any part is a video or audio (not supported by Claude Messages API)

    Note:
        - Image URL: ``{type: "image", source: {type: "url", url: ...}}``
        - Image inline: ``{type: "image", source: {type: "base64", media_type, data}}``
        - Claude Messages API does not support video or audio input
    """
    # Validate: Claude doesn't support video or audio
    for m in parts:
        if not isinstance(m, MediaPart):
            continue
        if m.media_type == "video":
            raise ValueError(
                "Claude Messages API does not support video input. "
                "Consider extracting key frames as images instead."
            )
        if m.media_type == "audio":
            raise ValueError(
                "Claude Messages API does not support audio input. "
                "Consider transcribing the audio first."
            )

    result = []
    for m in parts:
        if not isinstance(m, MediaPart):
            continue
        if m.media_type != "image":
            continue

        if m.source == "url":
            result.append({
                "type": "image",
                "source": {"type": "url", "url": m.content},
            })
        else:
            # base64 or file → both resolve to base64
            try:
                b64 = _read_media_as_base64(m)
            except (ValueError, OSError):
                continue
            result.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": m.mime,
                    "data": b64,
                },
            })

    return result


def _to_gemini_parts(parts: list) -> list[dict]:
    """Convert MediaPart list to Google Gemini inline_data parts.

    Produces the inline_data format used by the Gemini API.
    All media types (image, video, audio) use the same ``inline_data`` structure.

    Args:
        parts: List of MediaPart objects (non-MediaPart items are skipped)

    Returns:
        List of content part dicts in Gemini format

    Note:
        - All types: ``{inline_data: {mime_type, data}}``
        - All data is base64-encoded (files read, URLs downloaded)
        - File/URL errors are silently skipped
    """
    result = []
    for m in parts:
        if not isinstance(m, MediaPart):
            continue
        try:
            b64 = _read_media_as_base64(m)
        except (ValueError, OSError):
            continue
        result.append({
            "inline_data": {
                "mime_type": m.mime,
                "data": b64,
            },
        })

    return result


# ── Media utility functions ───────────────────────────────────────────────────

def _media_to_base64(part: MediaPart) -> str:
    """Convert any MediaPart content to a raw base64 string.

    Regardless of the source type (file, URL, or base64), returns
    the raw base64-encoded content without a ``data:`` prefix.

    Args:
        part: A MediaPart object

    Returns:
        Raw base64 string

    Raises:
        TypeError: If part is not a MediaPart
        ValueError: If file not found or URL download fails
    """
    return _read_media_as_base64(part)


def _save_media(part: MediaPart, path: str | None = None) -> str:
    """Save a MediaPart to a file.

    Args:
        part: A MediaPart object to save
        path: Destination file path. If None, saves to
              ``~/.helen/generated_media/{media_type}_{hash}.{ext}``

    Returns:
        The actual file path where the media was saved

    Raises:
        TypeError: If part is not a MediaPart
    """
    if not isinstance(part, MediaPart):
        raise TypeError(f"Expected MediaPart, got {type(part).__name__}")

    # Determine output path
    if path is None:
        output_dir = Path.home() / ".helen" / "generated_media"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename from content hash
        content_hash = hashlib.md5(part.content.encode()).hexdigest()[:8]
        ext_map = {
            "image/png": "png", "image/jpeg": "jpg", "image/gif": "gif",
            "image/webp": "webp", "video/mp4": "mp4",
            "audio/mp3": "mp3", "audio/wav": "wav", "audio/mpeg": "mp3",
        }
        ext = ext_map.get(part.mime, part.media_type)
        filename = f"{part.media_type}_{content_hash}.{ext}"
        output_path = output_dir / filename
    else:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save based on source type
    if part.source == "url":
        try:
            urllib.request.urlretrieve(part.content, str(output_path))
        except Exception:
            # If download fails, save the URL as text
            output_path.write_text(part.content)
    elif part.source == "base64":
        data = base64.b64decode(part.content)
        output_path.write_bytes(data)
    elif part.source == "file":
        if os.path.exists(part.content):
            shutil.copy2(part.content, str(output_path))
        else:
            output_path.write_text(part.content)

    return str(output_path)


# ── Media type predicates ─────────────────────────────────────────────────────

def _is_image(value: Any) -> bool:
    """Check if a value is an image MediaPart.

    Args:
        value: Any value to check

    Returns:
        True if value is a MediaPart with media_type "image", False otherwise
    """
    return isinstance(value, MediaPart) and value.media_type == "image"


def _is_video(value: Any) -> bool:
    """Check if a value is a video MediaPart.

    Args:
        value: Any value to check

    Returns:
        True if value is a MediaPart with media_type "video", False otherwise
    """
    return isinstance(value, MediaPart) and value.media_type == "video"


def _is_audio(value: Any) -> bool:
    """Check if a value is an audio MediaPart.

    Args:
        value: Any value to check

    Returns:
        True if value is a MediaPart with media_type "audio", False otherwise
    """
    return isinstance(value, MediaPart) and value.media_type == "audio"
