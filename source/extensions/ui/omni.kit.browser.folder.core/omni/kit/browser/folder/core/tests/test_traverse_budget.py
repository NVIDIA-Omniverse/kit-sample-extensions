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
What a traverse may cost the app.

Every responsiveness regression in this ticket was found by hand with a profiler after a user
reported a frozen window, because nothing asserted what a scan is allowed to cost.

These assert shape rather than time - frames per unit of work, filesystem calls per directory,
folders in flight at once - so they hold on any machine. Wall-clock thresholds belong to the
advisory performance lane.
"""

import tempfile
import time
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test

from ..models import TreeFolderBrowserModel
from ..models import folder_browser_data as fbd
from ..models import folder_identity

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/budget_root"
# A deep tree, not a wide one. The existing per-level batch caps eight children at a time, so a
# flat tree stays bounded no matter what - it is nesting that multiplies, and nesting is what put
# 740 folder traversals in flight during a C: scan.
DEPTH = 4
BRANCHING = 3
FILES_PER_FOLDER = 3
FOLDERS = sum(BRANCHING**d for d in range(1, DEPTH + 1))


class TestTraverseBudget(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)

        def build(parent, depth):
            for b in range(BRANCHING):
                sub = parent / f"d{depth}_{b}"
                sub.mkdir()
                for f in range(FILES_PER_FOLDER):
                    (sub / f"mat_{f}.usd").write_text("x", encoding="utf-8")
                if depth < DEPTH:
                    build(sub, depth + 1)

        build(root, 1)
        self._root = root.as_posix()

    async def tearDown(self):
        self._tmp.cleanup()

    def _model(self):
        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        return TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])

    async def _scan(self, model, ticks, worst=None):
        """Run one traverse to completion, counting app frames and the longest gap between them."""
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        folder = model.get_root_folder(self._root)
        model.start_traverse(folder)
        deadline = time.time() + 120
        last = time.perf_counter()
        while time.time() < deadline:
            await omni.kit.app.get_app().next_update_async()
            now = time.perf_counter()
            if worst is not None:
                worst[0] = max(worst[0], now - last)
            last = now
            ticks[0] += 1
            if folder.prepared and not model.active_folders:
                break
        return folder

    async def test_the_app_gets_frames_while_a_scan_runs(self):
        """
        The app must keep drawing during a traverse.

        A double blocks a worker for a fixed time per file, which is what a real USD read does, so
        the scan lasts long enough to mean something without depending on how fast this machine
        opens stages. What is asserted is the longest gap between frames: starvation produced nine
        second gaps on a real drive, and a healthy scan stays in the tens of milliseconds. The bound
        below sits far above the healthy figure and far below the broken one, so it holds on a
        loaded box and still fails if a traverse stops yielding.
        """
        import asyncio

        model = self._model()
        real = fbd.FileSystemFolder._on_file_found_async

        async def slow(inner_self, url):
            # Blocks a worker thread, never the loop - exactly as reading a USD file does.
            await asyncio.get_event_loop().run_in_executor(None, time.sleep, 0.02)
            return await real(inner_self, url)

        fbd.FileSystemFolder._on_file_found_async = slow
        try:
            ticks, worst = [0], [0.0]
            folder = await self._scan(model, ticks, worst)
        finally:
            fbd.FileSystemFolder._on_file_found_async = real

        resolved = folder.traverse_ctx.files_resolved
        self.assertEqual(resolved, FOLDERS * FILES_PER_FOLDER, "the whole tree should have been walked")
        self.assertGreater(ticks[0], 0, "the app never drew at all")
        # A guard against gross starvation - the customer symptom - not a fine-grained one. On a
        # tree this size a healthy scan gaps around 0.03 s and removing the pacing entirely only
        # reaches 0.1 s; the nine second gaps that prompted this work need a drive to reproduce.
        # The bound is set where it fails on a freeze and never on a slow machine.
        self.assertLess(
            worst[0],
            2.0,
            f"the app went {worst[0]:.2f}s without a frame while scanning {resolved} files",
        )

        model.destroy()

    async def test_the_walk_does_not_touch_the_filesystem_per_directory(self):
        """
        Identity comes from the parent, not from a syscall.

        Resolving every directory put os.path.realpath on the event loop once per folder - measured
        at 0.155 ms each, which over a drive is around 47 seconds of frozen UI. Only entries that
        really are links may be resolved.
        """
        model = self._model()
        calls = []
        real = folder_identity.resolve_folder_key

        def counting(url):
            calls.append(url)
            return real(url)

        fbd.resolve_folder_key = counting
        try:
            ticks = [0]
            folder = await self._scan(model, ticks)
        finally:
            fbd.resolve_folder_key = real

        self.assertEqual(len(folder.sub_folders), BRANCHING, "the tree should be complete")
        # The root resolves itself; nothing in this tree is a link, so nothing else may.
        self.assertLessEqual(
            len(calls),
            2,
            f"resolved {len(calls)} folders through the filesystem for a tree of {FOLDERS} with no links",
        )

        model.destroy()

    async def test_listings_in_flight_obey_the_cap(self):
        """
        The cap on folders doing their own work is real.

        Asserted by lowering it below what this tree would otherwise use. That matters: on a small
        tree the existing per-level batch of eight already bounds things - removing the cap
        entirely changes the peak here from 16 to 15 - so a test that merely watched the default
        would prove nothing. What broke on a real drive was nesting, which multiplies levels until
        740 traversals are in flight; a cap that is ignored fails this test at any tree size.
        """
        from ..models.traverse_context import SETTING_MAX_CONCURRENT_FOLDERS

        settings = carb.settings.get_settings()

        # Put back whatever was set, not the default: a test that restores a literal quietly
        # rewrites the setting for everything that runs after it.
        was = settings.get(SETTING_MAX_CONCURRENT_FOLDERS)
        settings.set(SETTING_MAX_CONCURRENT_FOLDERS, 4)
        try:
            model = self._model()
            live = {"now": 0, "peak": 0}
            real = fbd.FileSystemFolder._list_folder_async

            async def counted(inner_self, url):
                live["now"] += 1
                live["peak"] = max(live["peak"], live["now"])
                try:
                    return await real(inner_self, url)
                finally:
                    live["now"] -= 1

            fbd.FileSystemFolder._list_folder_async = counted
            try:
                ticks = [0]
                await self._scan(model, ticks)
            finally:
                fbd.FileSystemFolder._list_folder_async = real

            self.assertGreater(live["peak"], 0, "nothing was listed at all")
            # A folder can hold its slot across two listings - the folder and its thumbnails - so
            # the slack is one doubling, not an open door.
            self.assertLessEqual(
                live["peak"], 8, f"{live['peak']} listings were outstanding at once against a cap of 4"
            )
            model.destroy()
        finally:
            if was is None:
                settings.destroy_item(SETTING_MAX_CONCURRENT_FOLDERS)
            else:
                settings.set(SETTING_MAX_CONCURRENT_FOLDERS, was)


class TestCacheWrite(omni.kit.test.AsyncTestCase):
    """The cache file is shared by every collection, so a partial write loses all of them."""

    async def test_an_unreadable_cache_is_replaced_rather_than_fatal(self):
        """
        A cache that cannot be parsed must not stop the next one being written.

        The read of the existing file used to return on any parse failure, so a single truncated
        file - a write interrupted before the rename landed, or anything else that leaves half a
        file - meant nothing could be cached again, for any collection, until someone deleted it by
        hand. It is a cache: the right answer is to start it again.
        """
        import json
        import os

        from ..models.folder_browser_model import FolderBrowserModel

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cache.json"
            target.write_text('{"Existing": {"url": "C:/old", "trunc', encoding="utf-8")

            model = FolderBrowserModel()
            model._json_file = target.as_posix()
            model._save_folder_to_json = lambda folder, parent: {"url": folder.url}

            class _Folder:
                name = "New"
                url = "C:/new"

            model._save_data_to_json(_Folder())

            written = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn("New", written, "the collection was not cached after an unreadable file")
            self.assertNotIn("Existing", written, "half a collection survived into the new cache")
            self.assertEqual([p for p in os.listdir(tmp) if p.startswith(".cache-")], [])
            model.destroy()

    async def test_the_cache_is_replaced_atomically(self):
        import json
        import os

        from ..models.folder_browser_model import FolderBrowserModel

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cache.json"
            target.write_text(json.dumps({"Existing": {"kept": True}}), encoding="utf-8")
            before = target.read_text(encoding="utf-8")

            model = FolderBrowserModel()
            model._json_file = target.as_posix()

            class _Folder:
                name = "New"
                url = "C:/new"

            model._save_folder_to_json = lambda folder, parent: {"url": folder.url}

            # Fail inside the write itself, after the temp file exists: injecting any earlier only
            # proves that an exception before any writing leaves the file alone, which is not what
            # the temp-file-and-rename is for.
            real_dump = json.dump

            def exploding_dump(data, handle, **kwargs):
                handle.write('{"New": {"url": "C:/new"')  # a plausible half a file
                raise RuntimeError("interrupted mid-write")

            json.dump = exploding_dump
            try:
                model._save_data_to_json(_Folder())
            finally:
                json.dump = real_dump

            self.assertEqual(target.read_text(encoding="utf-8"), before, "a failed write damaged the existing cache")
            leftovers = [p for p in os.listdir(tmp) if p.startswith(".cache-")]
            self.assertEqual(leftovers, [], f"temp files were left behind: {leftovers}")
            model.destroy()
