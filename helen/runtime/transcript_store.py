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

import asyncio
import json
import logging
import time
import uuid as uuid_module
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

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
# Transcript Store Backend (Persistence Abstraction)
# ---------------------------------------------------------------------------

class TranscriptStoreBackend(ABC):
    """Abstract backend for transcript persistence.

    Backends are responsible for durably storing transcript items
    (messages and boundary markers) so they can survive process restarts.
    """

    @abstractmethod
    def append(self, item: Message | BoundaryMarker) -> None:
        """Append item to persistent storage (sync).

        Implementations should be fast (<1ms per call on SSD).
        Failures should be logged but not raised — the in-memory
        transcript is the primary data structure.
        """
        pass

    @abstractmethod
    def load_all(self) -> list[Message | BoundaryMarker]:
        """Load all items from persistent storage.

        Returns:
            List of Message and BoundaryMarker objects in order.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close backend resources (file handles, connections)."""
        pass


class JSONLBackend(TranscriptStoreBackend):
    """JSONL file backend for transcript persistence.

    Each item is stored as a single JSON line, making the format:
    - Append-only (fast writes, no seeks)
    - Human-readable (one JSON object per line)
    - Crash-safe (only the last line may be corrupted)
    - Easy to tail/grep for debugging

    Format:
        {"type": "message", "role": "user", "content": "...", "uuid": "...", ...}
        {"type": "boundary_marker", "uuid": "...", "layer": "...", ...}

    Thread safety: Each append opens/flushes the file independently,
    so concurrent appends are safe (though not recommended).
    """

    def __init__(self, path: Path | str):
        """Initialize JSONL backend.

        Args:
            path: Path to the JSONL file. Parent directories will be created.
        """
        self.path = Path(path) if isinstance(path, str) else path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None  # Lazy-open on first append

    def append(self, item: Message | BoundaryMarker) -> None:
        """Append item as a JSON line."""
        try:
            if self._file is None:
                self._file = open(self.path, "a", encoding="utf-8")

            line = json.dumps(_item_to_dict(item), ensure_ascii=False)
            self._file.write(line + "\n")
            self._file.flush()
        except OSError as e:
            logger.warning("JSONLBackend: failed to append to %s: %s", self.path, e)

    def load_all(self) -> list[Message | BoundaryMarker]:
        """Load all items from the JSONL file."""
        if not self.path.exists():
            return []

        items: list[Message | BoundaryMarker] = []
        try:
            with open(self.path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        item = _item_from_dict(data)
                        if item is not None:
                            items.append(item)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "JSONLBackend: corrupted line %d in %s: %s",
                            line_num, self.path, e,
                        )
                        # Continue reading — only the last line is expected to corrupt
        except OSError as e:
            logger.warning("JSONLBackend: failed to load from %s: %s", self.path, e)

        return items

    def close(self) -> None:
        """Close the file handle."""
        if self._file is not None:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None


class SQLiteBackend(TranscriptStoreBackend):
    """SQLite backend for transcript persistence with WAL mode.

    Uses SQLite with Write-Ahead Logging for:
    - Concurrent reads during writes
    - Better write performance (batched commits)
    - Transaction safety
    - Efficient queries (indexed by UUID)

    Schema:
        CREATE TABLE transcript (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,  -- 'message' or 'boundary_marker'
            data JSON NOT NULL,
            timestamp REAL NOT NULL
        );
        CREATE INDEX idx_uuid ON transcript(uuid);
        CREATE INDEX idx_timestamp ON transcript(timestamp);

    Thread safety: Uses connection per operation (safe for multi-threaded access).
    """

    def __init__(self, path: Path | str):
        """Initialize SQLite backend.

        Args:
            path: Path to the SQLite database file. Parent directories will be created.
        """
        import sqlite3

        self.path = Path(path) if isinstance(path, str) else path
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Create database and enable WAL mode
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")

        # Create schema
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS transcript (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_uuid ON transcript(uuid);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON transcript(timestamp);
        """)
        self.conn.commit()

    def append(self, item: Message | BoundaryMarker) -> None:
        """Append item to SQLite database."""
        try:
            item_dict = _item_to_dict(item)
            self.conn.execute(
                "INSERT OR REPLACE INTO transcript (uuid, type, data, timestamp) VALUES (?, ?, ?, ?)",
                (
                    item.uuid,
                    item_dict["type"],
                    json.dumps(item_dict, ensure_ascii=False),
                    time.time(),
                ),
            )
            self.conn.commit()
        except Exception as e:
            logger.warning("SQLiteBackend: failed to append: %s", e)

    def load_all(self) -> list[Message | BoundaryMarker]:
        """Load all items from SQLite database, ordered by id."""
        items: list[Message | BoundaryMarker] = []
        try:
            cursor = self.conn.execute(
                "SELECT data FROM transcript ORDER BY id ASC"
            )
            for row in cursor:
                try:
                    data = json.loads(row[0])
                    item = _item_from_dict(data)
                    if item is not None:
                        items.append(item)
                except json.JSONDecodeError as e:
                    logger.warning("SQLiteBackend: corrupted data: %s", e)
        except Exception as e:
            logger.warning("SQLiteBackend: failed to load: %s", e)

        return items

    def close(self) -> None:
        """Close the database connection."""
        try:
            self.conn.close()
        except Exception:
            pass


def _item_to_dict(item: Message | BoundaryMarker) -> dict[str, Any]:
    """Convert a Message or BoundaryMarker to a JSON-serializable dict."""
    if isinstance(item, BoundaryMarker):
        return item.to_dict()
    elif isinstance(item, Message):
        return {
            "type": "message",
            "role": item.role,
            "content": item.content,
            "tool_calls": item.tool_calls,
            "tool_call_id": item.tool_call_id,
            "uuid": item.uuid,
            "message_type": item.message_type,
            "priority": item.priority,
            "compressed": item.compressed,
        }
    else:
        raise TypeError(f"Unknown item type: {type(item)}")


def _item_from_dict(data: dict[str, Any]) -> Message | BoundaryMarker | None:
    """Reconstruct a Message or BoundaryMarker from a dict."""
    item_type = data.get("type")
    if item_type == "message":
        return Message(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls", []),
            tool_call_id=data.get("tool_call_id"),
            uuid=data.get("uuid", ""),
            message_type=data.get("message_type"),
            priority=data.get("priority", 50),
            compressed=data.get("compressed", False),
        )
    elif item_type == "boundary_marker":
        return BoundaryMarker.from_dict(data)
    else:
        logger.warning("Unknown item type in transcript: %r", item_type)
        return None


# ---------------------------------------------------------------------------
# Transcript Store
# ---------------------------------------------------------------------------

class TranscriptStore:
    """Mostly-append transcript storage.

    The transcript is an append-only list of either Message or BoundaryMarker
    objects. read_view() returns the current "effective" message list by
    applying all boundary markers.

    Optionally backed by a persistence backend (e.g., JSONLBackend) for
    crash-safe durability and session replay.

    Phase 4: Includes LRU cache for memory efficiency and UUID-based addressing.

    Attributes:
        transcript: Append-only list of Message and BoundaryMarker objects
    """

    def __init__(self, backend: TranscriptStoreBackend | None = None, max_memory_items: int = 1000):
        """Initialize transcript store.

        Args:
            backend: Optional persistence backend. When provided, all appends
                     are also written to the backend for durability.
            max_memory_items: Maximum number of items to keep in memory (LRU cache).
                              Older items are offloaded to backend only. Default: 1000.
        """
        self.transcript: list[Message | BoundaryMarker] = []
        self._uuid_index: dict[str, int] = {}  # UUID -> transcript index
        self._backend = backend
        # View cache (invalidated on append/record_compression)
        self._dirty = True
        self._cached_view: list[Message] | None = None
        # Phase 4: LRU cache for memory efficiency
        self._max_memory_items = max_memory_items
        self._offloaded_count = 0  # Number of items offloaded to backend only

    def append(self, message: Message) -> Message:
        """Append a message to the transcript.

        Assigns a UUID if the message doesn't have one.
        If a backend is configured, also persists the message.
        Phase 4: Implements LRU cache eviction for memory efficiency.

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
        self._dirty = True  # Invalidate view cache

        # Persist to backend
        if self._backend is not None:
            self._backend.append(message)

        # Phase 4: LRU cache eviction - offload old items when over limit
        if len(self.transcript) > self._max_memory_items:
            self._evict_old_items()

        return message

    def _evict_old_items(self) -> None:
        """Evict oldest items from memory, keeping only recent items.

        Phase 4: Memory efficiency - keep only last N items in memory,
        older items remain in backend storage.

        Important: Never evict messages that are referenced by BoundaryMarkers
        still in memory, as this would break read_view() consistency.
        """
        if len(self.transcript) <= self._max_memory_items:
            return

        # Calculate how many items to evict (keep 80% of max to avoid frequent evictions)
        target_size = int(self._max_memory_items * 0.8)
        items_to_evict = len(self.transcript) - target_size

        if items_to_evict <= 0:
            return

        # Find all UUIDs referenced by BoundaryMarkers in memory
        # These messages must NOT be evicted to maintain read_view() consistency
        protected_uuids: set[str] = set()
        for item in self.transcript:
            if isinstance(item, BoundaryMarker):
                protected_uuids.add(item.head_uuid)
                protected_uuids.add(item.tail_uuid)
                protected_uuids.add(item.anchor_uuid)

        # Remove oldest items from memory (they're already in backend)
        # But skip any messages protected by BoundaryMarkers
        evicted = []
        kept = []
        for item in self.transcript[:items_to_evict]:
            if isinstance(item, Message) and item.uuid in protected_uuids:
                # This message is referenced by a BoundaryMarker, keep it
                kept.append(item)
            else:
                evicted.append(item)

        # Rebuild transcript: kept items + remaining items
        self.transcript = kept + self.transcript[items_to_evict:]
        self._offloaded_count += len(evicted)

        # Update UUID index (shift indices)
        self._uuid_index.clear()
        for i, item in enumerate(self.transcript):
            self._uuid_index[item.uuid] = i

        # Invalidate view cache
        self._dirty = True

        logger.debug(
            "TranscriptStore: evicted %d items from memory (%d protected by boundaries), %d offloaded total",
            len(evicted), len(kept), self._offloaded_count,
        )

    def get(self, uuid: str) -> Message | BoundaryMarker | None:
        """Get item by UUID (Phase 4: UUID-based addressing).

        Args:
            uuid: UUID of the item to retrieve

        Returns:
            The item if found, None otherwise
        """
        index = self._uuid_index.get(uuid)
        if index is not None and 0 <= index < len(self.transcript):
            return self.transcript[index]
        return None

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
        self._dirty = True  # Invalidate view cache

        # Persist to backend
        if self._backend is not None:
            self._backend.append(marker)

        logger.info(
            "Transcript compression recorded: layer=%s, head=%s..tail=%s, "
            "tokens: %d -> %d (saved %d)",
            layer, head_uuid[:8], tail_uuid[:8],
            original_token_count, compressed_token_count,
            original_token_count - compressed_token_count,
        )

        return marker

    def read_view(self) -> list[Message]:
        """Reconstruct the current effective message list (cached).

        Applies all boundary markers to produce the compressed view:
        - Messages that fall within compressed regions are replaced by summaries
        - System messages before compressed regions are preserved
        - Messages after all compression boundaries are preserved as-is

        Uses a dirty flag to cache the view, avoiding re-computation
        when no appends have occurred.

        Returns:
            List of Message objects representing the current view
        """
        # Return cached view if no changes
        if not self._dirty and self._cached_view is not None:
            return self._cached_view

        # Collect all compressed UUID ranges
        compressed_ranges: list[tuple[str, str, str, str]] = []  # (head, tail, anchor, summary)
        for item in self.transcript:
            if isinstance(item, BoundaryMarker):
                compressed_ranges.append((
                    item.head_uuid, item.tail_uuid, item.anchor_uuid, item.summary,
                ))

        if not compressed_ranges:
            # No compression — return all messages as-is
            result = [item for item in self.transcript if isinstance(item, Message)]
            self._cached_view = result
            self._dirty = False
            return result

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

        self._cached_view = result
        self._dirty = False
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
        """Serialize transcript to dict for persistence.

        .. deprecated:: v1.16
            Use Backend persistence (JSONLBackend/SQLiteBackend) instead.
            This method is retained for backward compatibility and testing only.
        """
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

    def close(self) -> None:
        """Close the backend (release file handles, connections)."""
        if self._backend is not None:
            self._backend.close()

    @classmethod
    def load_from_backend(
        cls, backend: TranscriptStoreBackend, max_memory_items: int = 1000
    ) -> "TranscriptStore":
        """Load a TranscriptStore from a persistence backend.

        Used for session recovery — reconstructs the in-memory transcript
        from the on-disk JSONL/SQLite log.
        Phase 4: Only loads last N items into memory (LRU cache).

        Args:
            backend: Backend to load from
            max_memory_items: Maximum items to keep in memory (default: 1000)

        Returns:
            A new TranscriptStore populated from the backend
        """
        store = cls(backend=backend, max_memory_items=max_memory_items)
        items = backend.load_all()

        # Phase 4: Only load last N items into memory
        if len(items) > max_memory_items:
            # Calculate how many items to skip (offloaded)
            items_to_skip = len(items) - max_memory_items
            store._offloaded_count = items_to_skip

            # Load only the most recent items
            recent_items = items[items_to_skip:]
            for item in recent_items:
                index = len(store.transcript)
                store.transcript.append(item)
                if item.uuid:
                    store._uuid_index[item.uuid] = index

            logger.info(
                "TranscriptStore: loaded %d items into memory, %d offloaded",
                len(recent_items), items_to_skip,
            )
        else:
            # Load all items
            for item in items:
                index = len(store.transcript)
                store.transcript.append(item)
                if item.uuid:
                    store._uuid_index[item.uuid] = index

        store._dirty = True  # View needs to be computed on first access
        return store


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _generate_uuid() -> str:
    """Generate a short UUID for message identification."""
    return uuid_module.uuid4().hex[:12]
