"""
Shared disk TTL cache helper for ag-cli API connector tools.

Provides persistent caching across sessions using JSON files stored at
~/.ct/cache/<namespace>/<hash>.json. Cache entries expire after a configurable
TTL (default 24h). All functions are non-raising — failures silently return
None or pass so that a cache miss never blocks an API call.
"""

import hashlib
import json
import time
from pathlib import Path

_CACHE_BASE = Path.home() / ".ct" / "cache"


def _cache_path(namespace: str, key: str) -> Path:
    """Derive a stable cache file path from namespace + key.

    Uses the first 16 hex digits of the SHA-256 hash of the key as the
    filename so that long or unusual cache keys are safely represented on disk.

    Args:
        namespace: Logical group for the cached data (e.g. "string_ppi").
        key: Unique string identifying the specific cache entry.

    Returns:
        Path to the cache JSON file (may not exist yet).
    """
    filename = hashlib.sha256(key.encode()).hexdigest()[:16]
    return _CACHE_BASE / namespace / f"{filename}.json"


def get_cached(namespace: str, key: str, ttl_seconds: int = 86400) -> dict | None:
    """Return the cached value if present and unexpired, otherwise None.

    Reads a JSON file written by :func:`set_cached`. The file must contain a
    ``_cached_at`` float timestamp. If the entry is older than *ttl_seconds*
    the function treats it as a miss and returns ``None``.

    Args:
        namespace: Logical group for the cached data.
        key: Cache key identifying the specific entry.
        ttl_seconds: Maximum age in seconds (default 86400 = 24h).

    Returns:
        The cached ``value`` dict, or ``None`` on miss / expiry / error.
    """
    try:
        path = _cache_path(namespace, key)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        cached_at = envelope["_cached_at"]
        if time.time() - cached_at > ttl_seconds:
            return None
        return envelope["value"]
    except Exception:
        return None


def set_cached(namespace: str, key: str, value: dict) -> None:
    """Persist *value* to disk under the given namespace and key.

    Writes a JSON envelope containing the value and the current timestamp.
    Creates parent directories as needed. Cache write failures are silently
    swallowed so that a disk problem never causes a tool to fail.

    Args:
        namespace: Logical group for the cached data.
        key: Cache key identifying the specific entry.
        value: Dict to persist. Must be JSON-serialisable.
    """
    try:
        path = _cache_path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {"_cached_at": time.time(), "value": value}
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope))
    except Exception:
        pass
