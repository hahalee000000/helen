"""Crypto module for Helen stdlib.

Provides cryptographic hash and random operations.
"""

from __future__ import annotations

import hashlib
import hmac
import random
from typing import Any


# ── Hash operations ────────────────────────────────────────────


def _md5(text: str) -> str:
    """Calculate MD5 hash.

    Args:
        text: Input text

    Returns:
        MD5 hash as hex string
    """
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _sha1(text: str) -> str:
    """Calculate SHA1 hash.

    Args:
        text: Input text

    Returns:
        SHA1 hash as hex string
    """
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _sha256(text: str) -> str:
    """Calculate SHA256 hash.

    Args:
        text: Input text

    Returns:
        SHA256 hash as hex string
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha512(text: str) -> str:
    """Calculate SHA512 hash.

    Args:
        text: Input text

    Returns:
        SHA512 hash as hex string
    """
    return hashlib.sha512(text.encode("utf-8")).hexdigest()


def _hmac_sha256(key: str, message: str) -> str:
    """Calculate HMAC-SHA256.

    Args:
        key: Secret key
        message: Message to authenticate

    Returns:
        HMAC as hex string
    """
    return hmac.new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _hash_file(path: str, algorithm: str = "sha256") -> str:
    """Calculate hash of file contents.

    Args:
        path: File path
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)

    Returns:
        Hash as hex string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If algorithm is not supported
    """
    algorithm_map = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }

    if algorithm not in algorithm_map:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Must be one of {list(algorithm_map.keys())}")

    try:
        hasher = algorithm_map[algorithm]()
        with open(path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")


# ── Random operations ──────────────────────────────────────────


def _random() -> float:
    """Generate random float between 0 and 1.

    Returns:
        Random float
    """
    return random.random()


def _randint(min_val: int, max_val: int) -> int:
    """Generate random integer in range.

    Args:
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)

    Returns:
        Random integer
    """
    return random.randint(min_val, max_val)


def _choice(items: list[Any]) -> Any:
    """Choose random item from list.

    Args:
        items: List of items

    Returns:
        Random item

    Raises:
        ValueError: If list is empty
    """
    if not items:
        raise ValueError("Cannot choose from empty list")
    return random.choice(items)


def _shuffle(items: list[Any]) -> list[Any]:
    """Shuffle list randomly.

    Args:
        items: List to shuffle

    Returns:
        New shuffled list
    """
    result = items.copy()
    random.shuffle(result)
    return result


def _sample(items: list[Any], k: int) -> list[Any]:
    """Sample k items from list without replacement.

    Args:
        items: List of items
        k: Number of items to sample

    Returns:
        List of sampled items

    Raises:
        ValueError: If k > len(items) or list is empty
    """
    if not items:
        raise ValueError("Cannot sample from empty list")
    if k > len(items):
        raise ValueError(f"Cannot sample {k} items from list of length {len(items)}")
    return random.sample(items, k)


# ── UUID operations ─────────────────────────────────────────────


def _uuid_generate() -> str:
    """Generate a UUID (Universally Unique Identifier).

    Returns:
        UUID string in format "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    Example:
        let id = uuid_generate()
        // "550e8400-e29b-41d4-a716-446655440000"
    """
    import uuid as uuid_module
    return str(uuid_module.uuid4())


def _uuid_from_string(s: str) -> str:
    """Parse a string as UUID and return normalized form.

    Args:
        s: UUID string

    Returns:
        Normalized UUID string

    Raises:
        ValueError: If string is not a valid UUID
    """
    import uuid as uuid_module
    return str(uuid_module.UUID(s))


def _uuid_nil() -> str:
    """Return nil UUID (all zeros).

    Returns:
        "00000000-0000-0000-0000-000000000000"
    """
    import uuid as uuid_module
    return str(uuid_module.UUID(int=0))


# ── Random bytes operations ─────────────────────────────────────


def _random_bytes(n: int) -> str:
    """Generate n random bytes as hex string.

    Args:
        n: Number of bytes to generate

    Returns:
        Hex string of n bytes (2*n characters)

    Example:
        let bytes = random_bytes(16)
        // "a1b2c3d4e5f6..." (32 hex chars)
    """
    if n <= 0:
        raise ValueError("Number of bytes must be positive")
    import os
    return os.urandom(n).hex()


def _random_hex(n: int) -> str:
    """Generate random hex string of n characters.

    Args:
        n: Number of hex characters

    Returns:
        Random hex string
    """
    import os
    byte_count = (n + 1) // 2
    return os.urandom(byte_count).hex()[:n]


def _random_base64(n: int) -> str:
    """Generate n random bytes as base64 string.

    Args:
        n: Number of bytes to generate

    Returns:
        Base64 encoded string
    """
    import os
    import base64
    if n <= 0:
        raise ValueError("Number of bytes must be positive")
    return base64.b64encode(os.urandom(n)).decode("ascii")
