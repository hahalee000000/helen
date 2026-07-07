"""Mostly-append transcript storage for Helen.

Phase 10: Append-only transcript storage with compression boundary markers.

Design Philosophy:
- Messages are append-only (never modified/deleted in the transcript)
- Each message gets a UUID on first append
- Compression adds BoundaryMarker entries (not modifications)
- read_view() reconstructs the compressed view via boundary metadata

This provides:
- Full audit trail of all messages ever received
- Ability to reconstruct any historical view
- Compression events are recorded, not destructive

Usage:
    store = TranscriptStore()

    # Append messages
    msg = store.append(Message(role="user", content="Hello"))

    # Record a compression event
    store.record_compression(
        compressed_messages=compressed,
        summary="Earlier conversation...",
        layer="context_collapse",
    )

    # Get current view (with compression applied)
    view = store.read_view()
"""

from __future__ import annotations

import logging
import time
import uuid as uuid_module
from dataclasses import dataclass, field
from typing import Any

from helen.runtime.history import Message

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Boundary Marker
# ---------------------------------------------------------------------------

@dataclass
class BoundaryMarker:
    """Marks a compression boundary in the transcript.

    When compression occurs, we don't modify or delete existing messages.
    Instead, we add a BoundaryMarker that references the compressed region.

    Attributes:
        uuid: Unique identifier for this boundary marker
        anchor_uuid: UUID of the anchor message (first message after compressed region)
        head_uuid: UUID of the first message in the compressed region
        tail_uuid: UUID of the last message in the compressed region
        summary: Summary text of the compressed region
        layer: Which compression layer created this boundary
        timestamp: When the compression occurred
        original_token_count: Estimated tokens before compression
        compressed_token_count: Estimated tokens after compression
    """

    uuid: str = ""
    anchor_uuid: str = ""
    head_uuid: str = ""
    tail_uuid: str = ""
    summary: str = ""
    layer: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    original_token_count: int = 0
    compressed_token_count: int = 0

    def __post_init__(self):
        if not self.uuid:
            self.uuid = _generate_uuid()

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "type": "boundary_marker",
            "uuid": self.uuid,
            "anchor_uuid": self.anchor_uuid,
            "head_uuid": self.head_uuid,
            "tail_uuid": self.tail_uuid,
            "summary": self.summary,
            "layer": self.layer,
            "timestamp": self.timestamp,
            "original_token_count": self.original_token_count,
            "compressed_token_count": self.compressed_token_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoundaryMarker":
        """Reconstruct from dict."""
        return cls(
            uuid=data.get("uuid", ""),
            anchor_uuid=data.get("anchor_uuid", ""),
            head_uuid=data.get("head_uuid", ""),
            tail_uuid=data.get("tail_uuid", ""),
            summary=data.get("summary", ""),
            layer=data.get("layer", "unknown"),
            timestamp=data.get("timestamp", 0.0),
            original_token_count=data.get("original_token_count", 0),
            compressed_token_count=data.get("compressed_token_count", 0),
        )


# ---------------------------------------------------------------------------
# Transcript Store
# ---------------------------------------------------------------------------

class TranscriptStore:
    """Mostly-append transcript storage.

    The transcript is an append-only list of either Message or BoundaryMarker
    objects. read_view() returns the current "effective" message list by
    applying all boundary markers.

    Attributes:
        transcript: Append-only list of Message and BoundaryMarker objects
    """

    def __init__(self):
        """Initialize transcript store."""
        self.transcript: list[Message | BoundaryMarker] = []
        self._uuid_index: dict[str, int] = {}  # UUID -> transcript index

    def append(self, message: Message) -> Message:
        """Append a message to the transcript.

        Assigns a UUID if the message doesn't have one.

        Args:
            message: Message to append

        Returns:
            The same message (with UUID assigned if needed)
        """
        if not message.uuid:
            message.uuid = _generate_uuid()

        index = len(self.transcript)
        self.transcript.append(message)
        self._uuid_index[message.uuid] = index

        return message

    def append_many(self, messages: list[Message]) -> list[Message]:
        """Append multiple messages.

        Args:
            messages: Messages to append

        Returns:
            The same messages (with UUIDs assigned)
        """
        for msg in messages:
            self.append(msg)
        return messages

    def record_compression(
        self,
        head_uuid: str,
        tail_uuid: str,
        anchor_uuid: str,
        summary: str,
        layer: str = "unknown",
        original_token_count: int = 0,
        compressed_token_count: int = 0,
    ) -> BoundaryMarker:
        """Record a compression event as a boundary marker.

        This does NOT modify existing messages in the transcript.
        The boundary marker is appended to the transcript.

        Args:
            head_uuid: UUID of the first compressed message
            tail_uuid: UUID of the last compressed message
            anchor_uuid: UUID of the anchor (first message after compressed region)
            summary: Summary of the compressed region
            layer: Which compression layer created this boundary
            original_token_count: Tokens before compression
            compressed_token_count: Tokens after compression

        Returns:
            The created BoundaryMarker
        """
        marker = BoundaryMarker(
            anchor_uuid=anchor_uuid,
            head_uuid=head_uuid,
            tail_uuid=tail_uuid,
            summary=summary,
            layer=layer,
            original_token_count=original_token_count,
            compressed_token_count=compressed_token_count,
        )

        index = len(self.transcript)
        self.transcript.append(marker)
        self._uuid_index[marker.uuid] = index

        logger.info(
            "Transcript compression recorded: layer=%s, head=%s..tail=%s, "
            "tokens: %d -> %d (saved %d)",
            layer, head_uuid[:8], tail_uuid[:8],
            original_token_count, compressed_token_count,
            original_token_count - compressed_token_count,
        )

        return marker

    def read_view(self) -> list[Message]:
        """Reconstruct the current effective message list.

        Applies all boundary markers to produce the compressed view:
        - Messages that fall within compressed regions are replaced by summaries
        - System messages before compressed regions are preserved
        - Messages after all compression boundaries are preserved as-is

        Returns:
            List of Message objects representing the current view
        """
        # Collect all compressed UUID ranges
        compressed_ranges: list[tuple[str, str, str, str]] = []  # (head, tail, anchor, summary)
        for item in self.transcript:
            if isinstance(item, BoundaryMarker):
                compressed_ranges.append((
                    item.head_uuid, item.tail_uuid, item.anchor_uuid, item.summary,
                ))

        if not compressed_ranges:
            # No compression — return all messages as-is
            return [item for item in self.transcript if isinstance(item, Message)]

        # Build set of compressed UUIDs
        compressed_uuids: set[str] = set()
        summaries: list[tuple[str, str]] = []  # (anchor_uuid, summary)

        for head_uuid, tail_uuid, anchor_uuid, summary in compressed_ranges:
            head_idx = self._uuid_index.get(head_uuid)
            tail_idx = self._uuid_index.get(tail_uuid)

            if head_idx is not None and tail_idx is not None:
                # Mark all messages in range as compressed
                for i in range(head_idx, tail_idx + 1):
                    item = self.transcript[i]
                    if isinstance(item, Message):
                        compressed_uuids.add(item.uuid)
                summaries.append((anchor_uuid, summary))

        # Build the effective view
        result: list[Message] = []
        added_summaries: set[str] = set()

        for item in self.transcript:
            if isinstance(item, BoundaryMarker):
                continue
            if isinstance(item, Message):
                if item.uuid in compressed_uuids:
                    continue  # Skip compressed messages
                # Check if we need to insert a summary before this message
                for anchor_uuid, summary in summaries:
                    if anchor_uuid == item.uuid and anchor_uuid not in added_summaries:
                        summary_msg = Message(
                            role="system",
                            content=f"[Compressed: {summary}]",
                            uuid=_generate_uuid(),
                        )
                        result.append(summary_msg)
                        added_summaries.add(anchor_uuid)
                result.append(item)

        return result

    def get_transcript_size(self) -> int:
        """Get the total number of items in the transcript."""
        return len(self.transcript)

    def get_message_count(self) -> int:
        """Get the number of messages (excluding boundary markers)."""
        return sum(1 for item in self.transcript if isinstance(item, Message))

    def get_boundary_count(self) -> int:
        """Get the number of boundary markers (compression events)."""
        return sum(1 for item in self.transcript if isinstance(item, BoundaryMarker))

    def get_compression_audit(self) -> list[dict[str, Any]]:
        """Get audit trail of all compression events.

        Returns:
            List of dicts with compression event details
        """
        return [
            item.to_dict()
            for item in self.transcript
            if isinstance(item, BoundaryMarker)
        ]

    def to_dict(self) -> dict[str, Any]:
        """Serialize transcript to dict for persistence."""
        items = []
        for item in self.transcript:
            if isinstance(item, Message):
                items.append({
                    "type": "message",
                    "role": item.role,
                    "content": item.content,
                    "tool_calls": item.tool_calls,
                    "tool_call_id": item.tool_call_id,
                    "uuid": item.uuid,
                    "message_type": item.message_type,
                    "priority": item.priority,
                    "compressed": item.compressed,
                })
            elif isinstance(item, BoundaryMarker):
                items.append(item.to_dict())

        return {
            "version": 1,
            "items": items,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptStore":
        """Deserialize transcript from dict."""
        store = cls()
        for item_data in data.get("items", []):
            item_type = item_data.get("type")
            if item_type == "message":
                msg = Message(
                    role=item_data.get("role", "user"),
                    content=item_data.get("content", ""),
                    tool_calls=item_data.get("tool_calls", []),
                    tool_call_id=item_data.get("tool_call_id"),
                    uuid=item_data.get("uuid", ""),
                    message_type=item_data.get("message_type"),
                    priority=item_data.get("priority", 50),
                    compressed=item_data.get("compressed", False),
                )
                index = len(store.transcript)
                store.transcript.append(msg)
                if msg.uuid:
                    store._uuid_index[msg.uuid] = index
            elif item_type == "boundary_marker":
                marker = BoundaryMarker.from_dict(item_data)
                index = len(store.transcript)
                store.transcript.append(marker)
                store._uuid_index[marker.uuid] = index

        return store


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _generate_uuid() -> str:
    """Generate a short UUID for message identification."""
    return uuid_module.uuid4().hex[:12]
