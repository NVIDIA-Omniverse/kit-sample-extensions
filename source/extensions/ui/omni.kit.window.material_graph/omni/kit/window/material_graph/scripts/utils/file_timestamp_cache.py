"""Implement material graph extension logic for `utils/file_timestamp_cache.py`."""

import os
from collections import OrderedDict
from typing import Any, Optional, Tuple


class FileTimestampCache:
    """Cache values keyed by file path and mtime.

    Eviction policy is LRU: the oldest accessed entries are removed once the
    cache exceeds max_entries. Keys combine the file path and its current mtime,
    so updates to a file automatically invalidate stale entries.
    """

    def __init__(self, max_entries: int = 256) -> None:
        """Initialize cache capacity and internal LRU storage."""
        self._max_entries = max(0, max_entries)
        self._cache: "OrderedDict[Tuple[str, float], Any]" = OrderedDict()

    def get(self, file_path: str) -> Optional[Any]:
        """Return cached value for a file path if present."""
        key = self._get_key(file_path)
        if key is None:
            return None
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache.get(key)

    def set(self, file_path: str, value: Any) -> None:
        """Store a cached value for a file path."""
        if self._max_entries <= 0:
            return
        key = self._get_key(file_path)
        if key is None:
            return
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._max_entries:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Remove all cached entries and reset LRU ordering state."""
        self._cache.clear()

    @staticmethod
    def _get_key(file_path: str) -> Optional[Tuple[str, float]]:
        """Build a cache key from file path and timestamp."""
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            # Missing/inaccessible files are treated as cache misses.
            return None
        return (file_path, mtime)
