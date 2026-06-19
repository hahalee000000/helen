"""Memory providers for the Helen runtime (HLD §3.8.2).

Three implementations:
- MemoryProvider: Abstract base class (contract)
- InMemoryProvider: Pure in-memory store (for testing)
- FileMemoryProvider: JSON file persistence (for production)
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path


class MemoryProvider(ABC):
    """Abstract interface for Helen memory backends (HLD §3.8.2).

    All memory providers must implement these four methods.
    The Helen runtime delegates get_memory/set_memory calls to the
    registered provider for the matching URI protocol.
    """

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Get a value by key. Returns None if not found."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Set a key-value pair."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key. No-op if key doesn't exist."""
        ...

    @abstractmethod
    def list_keys(self) -> list[str]:
        """List all keys in this memory store."""
        ...


class InMemoryProvider(MemoryProvider):
    """Pure in-memory memory provider (HLD §3.8.2).

    Used for testing and ephemeral agents.
    Data is lost when the process exits.
    """

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        """Get a value by key."""
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        """Set a key-value pair."""
        self._data[key] = value

    def delete(self, key: str) -> None:
        """Delete a key."""
        self._data.pop(key, None)

    def list_keys(self) -> list[str]:
        """List all keys."""
        return list(self._data.keys())


class FileMemoryProvider(MemoryProvider):
    """JSON file-backed memory provider (HLD §3.8.2).

    Persists all key-value pairs to a JSON file on every write.
    Loads existing data on construction.

    Args:
        path: Path to the JSON file. Parent directories are created
            automatically if they don't exist.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._data: dict[str, str] = self._load()

    # ── Internal ───────────────────────────────────────────────

    def _load(self) -> dict[str, str]:
        """Load data from the JSON file. Returns empty dict on corruption."""
        if os.path.exists(self._path):
            try:
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
                    return {k: str(v) for k, v in data.items()}
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self) -> None:
        """Persist data to the JSON file."""
        parent = Path(self._path).parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    # ── MemoryProvider interface ───────────────────────────────

    def get(self, key: str) -> str | None:
        """Get a value by key."""
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        """Set a key-value pair and persist."""
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        """Delete a key and persist."""
        if key in self._data:
            del self._data[key]
            self._save()

    def list_keys(self) -> list[str]:
        """List all keys."""
        return list(self._data.keys())

    # ── Utilities ──────────────────────────────────────────────

    def clear(self) -> None:
        """Clear all data and persist empty state."""
        self._data.clear()
        self._save()

    @property
    def path(self) -> str:
        """The file path used for persistence."""
        return self._path

    def size(self) -> int:
        """Number of key-value pairs stored."""
        return len(self._data)
