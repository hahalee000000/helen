"""Crypto module contracts for Helen stdlib.

Defines interfaces for cryptographic hash operations.
"""

from typing import Any


class HashContract:
    """Contract for hash operations."""

    @staticmethod
    def md5(text: str) -> str:
        """Calculate MD5 hash.

        Args:
            text: Input text

        Returns:
            MD5 hash as hex string
        """
        ...

    @staticmethod
    def sha1(text: str) -> str:
        """Calculate SHA1 hash.

        Args:
            text: Input text

        Returns:
            SHA1 hash as hex string
        """
        ...

    @staticmethod
    def sha256(text: str) -> str:
        """Calculate SHA256 hash.

        Args:
            text: Input text

        Returns:
            SHA256 hash as hex string
        """
        ...

    @staticmethod
    def sha512(text: str) -> str:
        """Calculate SHA512 hash.

        Args:
            text: Input text

        Returns:
            SHA512 hash as hex string
        """
        ...

    @staticmethod
    def hmac_sha256(key: str, message: str) -> str:
        """Calculate HMAC-SHA256.

        Args:
            key: Secret key
            message: Message to authenticate

        Returns:
            HMAC as hex string
        """
        ...

    @staticmethod
    def hash_file(path: str, algorithm: str = "sha256") -> str:
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
        ...


class RandomContract:
    """Contract for random operations."""

    @staticmethod
    def random() -> float:
        """Generate random float between 0 and 1.

        Returns:
            Random float
        """
        ...

    @staticmethod
    def randint(min_val: int, max_val: int) -> int:
        """Generate random integer in range.

        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)

        Returns:
            Random integer
        """
        ...

    @staticmethod
    def choice(items: list[Any]) -> Any:
        """Choose random item from list.

        Args:
            items: List of items

        Returns:
            Random item

        Raises:
            ValueError: If list is empty
        """
        ...

    @staticmethod
    def shuffle(items: list[Any]) -> list[Any]:
        """Shuffle list randomly.

        Args:
            items: List to shuffle

        Returns:
            New shuffled list
        """
        ...

    @staticmethod
    def sample(items: list[Any], k: int) -> list[Any]:
        """Sample k items from list without replacement.

        Args:
            items: List of items
            k: Number of items to sample

        Returns:
            List of sampled items

        Raises:
            ValueError: If k > len(items) or list is empty
        """
        ...
