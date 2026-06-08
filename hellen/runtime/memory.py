"""Memory Provider interface and implementations (HLD 3.8.2).

Memory is a language-level declaration + Runtime interface abstraction.
Language only provides the `memory "path"` reference syntax; the actual
persistence and retrieval is handled by pluggable MemoryProvider implementations.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any


class MemoryProvider(ABC):
    """Abstract interface for memory storage (HLD 3.8.2).

    Language-layer declaration: `memory "path"` references a memory store.
    Concrete implementations handle persistence:
    - FileMemoryProvider: JSON file storage (default)
    - InMemoryProvider: Python dict (testing)
    - User-defined: vector DB, Redis, etc.
    """

    @abstractmethod
    def load(self, path: str) -> dict[str, Any]:
        """Load all memory data from the given path.

        Returns a KV dict for injection into {{_memory_content}} template.
        """
        ...

    @abstractmethod
    def save(self, path: str, data: dict[str, Any]) -> None:
        """Save memory data to the given path.

        Called after agent execution completes for persistence.
        """
        ...

    @abstractmethod
    def get(self, path: str, key: str) -> str | None:
        """Exact key-value lookup.

        Args:
            path: Memory store path.
            key: Exact key to look up.

        Returns:
            Value as string, or None if key not found.
        """
        ...

    @abstractmethod
    def set(self, path: str, key: str, value: str) -> None:
        """Exact key-value write.

        Args:
            path: Memory store path.
            key: Key to set.
            value: Value string.
        """
        ...

    def search(self, path: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Semantic/fuzzy search for memory entries.

        Default fallback: iterate all keys, do text containment match.
        Override in subclasses for embedding-based similarity search.

        Args:
            path: Memory store path.
            query: Search query string.
            top_k: Maximum number of results.

        Returns:
            List of {"key": ..., "value": ..., "score": ...} dicts.
        """
        data = self.load(path)
        results = []
        for k, v in data.items():
            if query.lower() in str(v).lower():
                results.append({"key": k, "value": str(v), "score": 1.0})
        return results[:top_k]


class FileMemoryProvider(MemoryProvider):
    """JSON file-based memory storage (HLD 3.8.2 default).

    Stores memory as a JSON file. Creates parent directories automatically.
    """

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, path: str) -> dict[str, Any]:
        if path in self._cache:
            return self._cache[path]
        if not os.path.exists(path):
            self._cache[path] = {}
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache[path] = data
            return data
        except (json.JSONDecodeError, OSError):
            self._cache[path] = {}
            return {}

    def save(self, path: str, data: dict[str, Any]) -> None:
        # Create parent directories if needed
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self._cache[path] = data

    def get(self, path: str, key: str) -> str | None:
        data = self.load(path)
        value = data.get(key)
        if value is not None:
            return str(value)
        return None

    def set(self, path: str, key: str, value: str) -> None:
        data = self.load(path)
        data[key] = value
        self._cache[path] = data


class InMemoryProvider(MemoryProvider):
    """In-memory dict storage for testing.

    Does not persist to disk. Supports all operations including
    search fallback.
    """

    def __init__(self) -> None:
        self._stores: dict[str, dict[str, Any]] = {}

    def load(self, path: str) -> dict[str, Any]:
        return dict(self._stores.get(path, {}))

    def save(self, path: str, data: dict[str, Any]) -> None:
        # Store in-memory only — no disk persistence
        self._stores[path] = dict(data)

    def get(self, path: str, key: str) -> str | None:
        store = self._stores.get(path, {})
        value = store.get(key)
        if value is not None:
            return str(value)
        return None

    def set(self, path: str, key: str, value: str) -> None:
        if path not in self._stores:
            self._stores[path] = {}
        self._stores[path][key] = value
