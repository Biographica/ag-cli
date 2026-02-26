"""
Tests for the shared disk TTL cache helper (_api_cache.py).

All tests use pytest's tmp_path fixture and patch _CACHE_BASE to avoid
writing to the real ~/.ct/cache directory.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from ct.tools._api_cache import _cache_path, get_cached, set_cached


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_envelope(path: Path, value: dict, cached_at: float) -> None:
    """Write a raw cache envelope to *path* for test setup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"_cached_at": cached_at, "value": value}, fh)


# ---------------------------------------------------------------------------
# _cache_path
# ---------------------------------------------------------------------------


def test_cache_path_deterministic(tmp_path: Path) -> None:
    """_cache_path returns the same Path for the same inputs, different for different keys."""
    with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
        p1 = _cache_path("ns", "key_a")
        p2 = _cache_path("ns", "key_a")
        p3 = _cache_path("ns", "key_b")

    assert p1 == p2, "Same namespace+key must produce the same path"
    assert p1 != p3, "Different keys must produce different paths"


# ---------------------------------------------------------------------------
# get_cached / set_cached round-trip
# ---------------------------------------------------------------------------


def test_set_and_get_cached(tmp_path: Path) -> None:
    """set_cached persists a value and get_cached retrieves it correctly."""
    with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
        set_cached("test_ns", "key1", {"foo": "bar"})
        result = get_cached("test_ns", "key1")

    assert result == {"foo": "bar"}


def test_get_cached_missing(tmp_path: Path) -> None:
    """get_cached returns None when no cache file exists."""
    with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
        result = get_cached("nonexistent_ns", "missing_key")

    assert result is None


# ---------------------------------------------------------------------------
# TTL / expiry
# ---------------------------------------------------------------------------


def test_get_cached_expired(tmp_path: Path) -> None:
    """get_cached returns None when the cache entry is older than ttl_seconds."""
    with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
        # Write a cache file whose _cached_at is 100 seconds in the past
        path = _cache_path("test_ns", "stale_key")
        _write_envelope(path, {"data": "old"}, cached_at=time.time() - 100)

        result = get_cached("test_ns", "stale_key", ttl_seconds=50)

    assert result is None, "Expired entry must return None"


def test_get_cached_not_expired(tmp_path: Path) -> None:
    """get_cached returns the value when the entry is younger than ttl_seconds."""
    with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
        path = _cache_path("test_ns", "fresh_key")
        _write_envelope(path, {"data": "fresh"}, cached_at=time.time() - 10)

        result = get_cached("test_ns", "fresh_key", ttl_seconds=3600)

    assert result == {"data": "fresh"}


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------


def test_set_cached_creates_directories(tmp_path: Path) -> None:
    """set_cached creates parent directories that do not yet exist."""
    deep_base = tmp_path / "deep" / "nested"
    with patch("ct.tools._api_cache._CACHE_BASE", deep_base):
        # Directory does not exist yet — set_cached must create it
        set_cached("myns", "mykey", {"hello": "world"})
        result = get_cached("myns", "mykey")

    assert result == {"hello": "world"}
    # The namespace sub-directory should have been created
    assert (deep_base / "myns").is_dir()
