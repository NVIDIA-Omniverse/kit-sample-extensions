# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""
Matching a listing against the folder's cached files.

The match used to scan every cached file per listed file, so one folder of n files cost n^2/2
comparisons on the main thread - 67 s at 40,000 files. It is indexed by url now.

``equals`` still decides, because subclasses widen it. These pin that down: an index keyed on what
the base class compares would pass every other test in the suite and silently merge files a
subclass considers different.
"""

import tempfile
from pathlib import Path

import omni.kit.app
import omni.kit.test

from ..models import FileSystemFile, FileSystemFolder

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/cache_root"


def _usd_only(url: str) -> bool:
    return url.endswith(".usd")


class TypedFile(FileSystemFile):
    """A file whose identity includes more than the base class compares - like EnvFile's type."""

    def __init__(self, url, **kwargs):
        super().__init__(url, **kwargs)
        self.kind = "first"

    def equals(self, other: "TypedFile") -> bool:
        return super().equals(other) and self.kind == getattr(other, "kind", None)


class TypedFolder(FileSystemFolder):
    async def _on_file_found_async(self, url, entry=None):
        return TypedFile(url, list_entry=entry)


class TestTraverseCache(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = Path(self._tmp.name)
        for name in ("a.usd", "b.usd", "c.usd"):
            (self._dir / name).write_text("x", encoding="utf-8")
        self._root = self._dir.as_posix()

    async def tearDown(self):
        self._tmp.cleanup()

    async def _traverse(self, folder):
        await folder.start_traverse()
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

    async def test_a_second_traverse_reuses_the_cached_files(self):
        """The point of the match: unchanged files keep their objects instead of piling up."""
        folder = FileSystemFolder("root", self._root, filter_file_fn=_usd_only)
        await self._traverse(folder)
        first = list(folder.files)
        self.assertEqual(sorted(f.url.split("/")[-1] for f in first), ["a.usd", "b.usd", "c.usd"])

        await self._traverse(folder)
        self.assertEqual(len(folder.files), 3, "the second traverse duplicated the cache")
        # Matched by url, not by position: the point is that each file object was reused for the
        # same file, and a list that happened to keep its order would hide a mismatch.
        by_url = {f.url: f for f in folder.files}
        for before in first:
            after = by_url.get(before.url)
            self.assertIsNotNone(after, f"{before.url} is not in the second traverse's files")
            self.assertIs(before, after, "a cached file object was replaced, not reused")

    async def test_a_new_file_is_added_without_disturbing_the_others(self):
        folder = FileSystemFolder("root", self._root, filter_file_fn=_usd_only)
        await self._traverse(folder)
        kept = folder.files[0]

        (self._dir / "d.usd").write_text("x", encoding="utf-8")
        await self._traverse(folder)

        self.assertEqual(len(folder.files), 4)
        self.assertIn(kept, folder.files, "adding a file disturbed one already cached")

    async def test_equals_still_decides_when_a_subclass_widens_it(self):
        """
        Same url, different identity: the url only narrows the candidates.

        An index keyed on url and thumbnail - what the base class compares - would call these the
        same file and skip the update. equals() has to be the one that answers.
        """
        folder = TypedFolder("root", self._root, filter_file_fn=_usd_only)
        await self._traverse(folder)
        self.assertEqual(len(folder.files), 3)

        # The files on disk are unchanged, but the cached ones no longer describe them.
        for cached in folder.files:
            cached.kind = "second"
        await self._traverse(folder)

        for cached in folder.files:
            self.assertEqual(cached.kind, "first", "a re-listed file kept its stale identity")

    async def test_a_folder_of_many_files_does_not_scan_the_cache_per_file(self):
        """
        The stall itself, counted rather than timed.

        The old match compared each listed file against every file cached before it, so a folder of
        n files cost n^2/2 comparisons - the shape that made 40,000 files take over a minute.
        Counting the comparisons says exactly that, where a wall clock budget loose enough to be
        stable on any machine is also loose enough for the quadratic scan to pass it.
        """
        count = 500
        many = self._dir / "many"
        many.mkdir()
        for i in range(count):
            (many / f"asset_{i:05d}.usd").write_text("x", encoding="utf-8")

        folder = FileSystemFolder("many", many.as_posix(), filter_file_fn=_usd_only)
        await self._traverse(folder)
        self.assertEqual(len(folder.files), count)

        # The second traverse is the one that matches a full listing against a full cache.
        calls = 0
        real_equals = FileSystemFile.equals

        def counting_equals(self, other):
            nonlocal calls
            calls += 1
            return real_equals(self, other)

        FileSystemFile.equals = counting_equals
        try:
            await self._traverse(folder)
        finally:
            FileSystemFile.equals = real_equals

        self.assertEqual(len(folder.files), count)
        # The index narrows to the one candidate that shares the url, so this is about one call per
        # file. The scan it replaced would be around n^2/2 - 125,000 of them at this size.
        self.assertLessEqual(calls, count * 2, f"{calls} comparisons for {count} files - the cache is being scanned")
