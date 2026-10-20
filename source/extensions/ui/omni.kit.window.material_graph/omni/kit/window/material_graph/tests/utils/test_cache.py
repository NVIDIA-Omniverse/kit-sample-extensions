import os
import tempfile

import omni.kit.test

from ...scripts.utils.file_timestamp_cache import FileTimestampCache


class TestFileTimestampCache(omni.kit.test.AsyncTestCase):
    """FileTimestampCache keys values by path and invalidates when file mtime changes; it is used to
    avoid re-reading unchanged files. We test get/set, mtime invalidation, LRU eviction when
    max_entries is reached, disabled storage when max_entries is zero, and missing file returning None."""

    async def test_cache_hit_and_miss(self) -> None:
        """Cache returns value for unchanged file."""
        cache = FileTimestampCache()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name

        try:
            self.assertIsNone(cache.get(path))
            cache.set(path, "value")
            self.assertEqual(cache.get(path), "value")
        finally:
            os.remove(path)

    async def test_cache_invalidates_on_mtime_change(self) -> None:
        """Cache misses after mtime change."""
        cache = FileTimestampCache()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name

        try:
            cache.set(path, "value")
            self.assertEqual(cache.get(path), "value")
            # Explicitly bump mtime beyond coarse filesystem timestamp
            # resolution (seen on CI) so invalidation is deterministic.
            stat = os.stat(path)
            bumped_mtime = float(stat.st_mtime) + 2.0
            os.utime(path, (bumped_mtime, bumped_mtime))
            self.assertIsNone(cache.get(path))
        finally:
            os.remove(path)

    async def test_cache_eviction_clears(self) -> None:
        """Eviction clears LRU entry."""
        cache = FileTimestampCache(max_entries=1)
        with tempfile.NamedTemporaryFile(delete=False) as tmp_a:
            path_a = tmp_a.name
        with tempfile.NamedTemporaryFile(delete=False) as tmp_b:
            path_b = tmp_b.name

        try:
            cache.set(path_a, "a")
            self.assertEqual(cache.get(path_a), "a")
            cache.set(path_b, "b")
            self.assertIsNone(cache.get(path_a))
            self.assertEqual(cache.get(path_b), "b")
        finally:
            os.remove(path_a)
            os.remove(path_b)

    async def test_cache_disabled_when_zero_entries(self) -> None:
        """max_entries=0: no storage."""
        cache = FileTimestampCache(max_entries=0)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name
        try:
            cache.set(path, "value")
            self.assertIsNone(cache.get(path))
        finally:
            os.remove(path)

    async def test_cache_missing_file_returns_none(self) -> None:
        """Missing file returns None."""
        cache = FileTimestampCache()
        self.assertIsNone(cache.get("missing-file-does-not-exist.tmp"))
