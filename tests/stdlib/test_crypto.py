"""Tests for Crypto stdlib module.

Tests hash and random operations.
"""

import pytest
import tempfile
import os
from helen.stdlib.crypto import (
    # Hash
    _md5, _sha1, _sha256, _sha512, _hmac_sha256, _hash_file,
    # Random
    _random, _randint, _choice, _shuffle, _sample,
)


# ── Hash Tests ─────────────────────────────────────────────────


class TestMd5:
    """Tests for md5."""

    def test_basic(self):
        result = _md5("hello")
        assert result == "5d41402abc4b2a76b9719d911017c592"

    def test_empty(self):
        result = _md5("")
        assert result == "d41d8cd98f00b204e9800998ecf8427e"

    def test_unicode(self):
        result = _md5("你好")
        assert len(result) == 32


class TestSha1:
    """Tests for sha1."""

    def test_basic(self):
        result = _sha1("hello")
        assert result == "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"

    def test_empty(self):
        result = _sha1("")
        assert result == "da39a3ee5e6b4b0d3255bfef95601890afd80709"


class TestSha256:
    """Tests for sha256."""

    def test_basic(self):
        result = _sha256("hello")
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_empty(self):
        result = _sha256("")
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TestSha512:
    """Tests for sha512."""

    def test_basic(self):
        result = _sha512("hello")
        assert len(result) == 128

    def test_empty(self):
        result = _sha512("")
        assert len(result) == 128


class TestHmacSha256:
    """Tests for hmac_sha256."""

    def test_basic(self):
        result = _hmac_sha256("secret", "message")
        assert len(result) == 64

    def test_different_keys(self):
        result1 = _hmac_sha256("key1", "message")
        result2 = _hmac_sha256("key2", "message")
        assert result1 != result2


class TestHashFile:
    """Tests for hash_file."""

    def test_sha256(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("hello")
            f.flush()
            path = f.name
        
        try:
            result = _hash_file(path, "sha256")
            assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        finally:
            os.unlink(path)

    def test_md5(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("hello")
            f.flush()
            path = f.name
        
        try:
            result = _hash_file(path, "md5")
            assert result == "5d41402abc4b2a76b9719d911017c592"
        finally:
            os.unlink(path)

    def test_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _hash_file("/nonexistent/file.txt")

    def test_invalid_algorithm(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("hello")
            f.flush()
            path = f.name
        
        try:
            with pytest.raises(ValueError):
                _hash_file(path, "invalid")
        finally:
            os.unlink(path)


# ── Random Tests ───────────────────────────────────────────────


class TestRandom:
    """Tests for random."""

    def test_basic(self):
        result = _random()
        assert 0 <= result < 1

    def test_multiple_calls(self):
        results = [_random() for _ in range(100)]
        assert all(0 <= r < 1 for r in results)
        # Should have some variation
        assert len(set(results)) > 1


class TestRandint:
    """Tests for randint."""

    def test_basic(self):
        result = _randint(1, 10)
        assert 1 <= result <= 10

    def test_same_min_max(self):
        result = _randint(5, 5)
        assert result == 5

    def test_multiple_calls(self):
        results = [_randint(1, 100) for _ in range(100)]
        assert all(1 <= r <= 100 for r in results)


class TestChoice:
    """Tests for choice."""

    def test_basic(self):
        items = [1, 2, 3, 4, 5]
        result = _choice(items)
        assert result in items

    def test_single_item(self):
        result = _choice([42])
        assert result == 42

    def test_empty(self):
        with pytest.raises(ValueError):
            _choice([])


class TestShuffle:
    """Tests for shuffle."""

    def test_basic(self):
        items = [1, 2, 3, 4, 5]
        result = _shuffle(items)
        assert sorted(result) == sorted(items)
        # Original should be unchanged
        assert items == [1, 2, 3, 4, 5]

    def test_empty(self):
        result = _shuffle([])
        assert result == []

    def test_single(self):
        result = _shuffle([1])
        assert result == [1]


class TestSample:
    """Tests for sample."""

    def test_basic(self):
        items = [1, 2, 3, 4, 5]
        result = _sample(items, 3)
        assert len(result) == 3
        assert all(item in items for item in result)
        # No duplicates
        assert len(set(result)) == 3

    def test_sample_all(self):
        items = [1, 2, 3]
        result = _sample(items, 3)
        assert sorted(result) == sorted(items)

    def test_sample_too_many(self):
        with pytest.raises(ValueError):
            _sample([1, 2, 3], 5)

    def test_empty(self):
        with pytest.raises(ValueError):
            _sample([], 1)
