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
Coalescing of the summary refresh.

The summary item's children are every detail item in every root folder, rebuilt and sorted from
scratch on each notification. A traverse reports a status per folder discovered, so notifying per
folder costs folders x items on the event loop and hangs the app.
"""

import tempfile
import time
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test

from ..models import TreeFolderBrowserModel

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/summary_root"
SETTING_HIDDEN = "/exts/omni.kit.browser.folder.core/test/summary_hidden"
FOLDERS = 30
FILES_PER_FOLDER = 2


class TestSummaryRefresh(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        for d in range(FOLDERS):
            sub = root / f"folder_{d:02d}"
            sub.mkdir()
            for f in range(FILES_PER_FOLDER):
                (sub / f"mat_{f}.usd").write_text("x", encoding="utf-8")
        self._root = root.as_posix()

    async def tearDown(self):
        self._tmp.cleanup()

    async def test_summary_refresh_is_coalesced(self):
        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])

        refreshes = []

        def on_item_changed(_model, item):
            if item is not None and getattr(item, "name", None) == model.SUMMARY_FOLDER_NAME:
                refreshes.append(time.time())

        sub = model.subscribe_item_changed_fn(on_item_changed)  # noqa: F841 - keep the subscription

        # Build the category items so the summary item exists, as opening the browser does.
        for collection in model.get_item_children(None):
            model.get_item_children(collection)

        deadline = time.time() + 60
        folder = model.get_root_folder(self._root)
        while time.time() < deadline:
            await omni.kit.app.get_app().next_update_async()
            if folder is not None and folder.prepared and not model.active_folders:
                break
        # Let any pending coalesced refresh land.
        for _ in range(30):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(len(folder.sub_folders), FOLDERS, "the tree itself must still be complete")
        self.assertTrue(refreshes, "the summary was never refreshed")
        # One per folder is the defect. The exact count depends on how long the scan took, so this
        # asserts the shape - far fewer than one each - rather than a number that would be flaky.
        self.assertLess(
            len(refreshes),
            FOLDERS // 2,
            f"summary refreshed {len(refreshes)} times for {FOLDERS} folders; it is not coalescing",
        )

        summary = next(
            c
            for collection in model.get_item_children(None)
            for c in model.get_item_children(collection)
            if getattr(c, "name", None) == model.SUMMARY_FOLDER_NAME
        )
        self.assertEqual(
            len(model.get_detail_items(summary)),
            FOLDERS * FILES_PER_FOLDER,
            "coalescing must not lose the final state",
        )

        del sub
        model.destroy()


class TestSummaryFollowsContent(omni.kit.test.AsyncTestCase):
    """
    The summary lists the same files as the folders it summarises, so a replaced file has to reach
    it too.

    It does, and the count carries it: a rescan raises TraverseStatus.COMPLETED before it drops the
    files the listing no longer returned, so the folder is momentarily seen holding both the old
    file and the new one. The count moves 2 -> 3 and back, and each move asks for a refresh. Pinned
    here because it is not obvious from the code that it works, and it is the reason no separate
    "content changed" signal is needed.
    """

    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        sub = root / "folder"
        sub.mkdir()
        for f in range(FILES_PER_FOLDER):
            (sub / f"mat_{f}.usd").write_text("x", encoding="utf-8")
        self._root = root.as_posix()
        self._sub = sub

    async def tearDown(self):
        self._tmp.cleanup()

    async def _scanned(self, model, started=False):
        """The root, once its traverse has both begun and finished. `prepared` survives a rescan."""
        deadline = time.time() + 60
        while time.time() < deadline:
            await omni.kit.app.get_app().next_update_async()
            if not started:
                started = bool(model.active_folders)
                continue
            folder = model.get_root_folder(self._root)
            if folder is not None and folder.prepared and not model.active_folders:
                return folder
        self.fail("the root was never scanned")

    def _files_of(self, folder):
        """The scanned files. They live on the sub folder; a root holds only its children."""
        return [f for sub in folder.sub_folders for f in sub.files]

    async def test_a_replaced_file_refreshes_the_summary(self):
        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        try:
            refreshes = []

            def on_item_changed(_model, item):
                if item is not None and getattr(item, "name", None) == model.SUMMARY_FOLDER_NAME:
                    refreshes.append(time.time())

            sub = model.subscribe_item_changed_fn(on_item_changed)  # noqa: F841 - keep the subscription

            for collection in model.get_item_children(None):
                model.get_item_children(collection)
            folder = await self._scanned(model)
            before = sorted(f.url for f in self._files_of(folder))

            # One file for another: the same number of files, a different set of them.
            (self._sub / "mat_0.usd").unlink()
            (self._sub / "mat_replacement.usd").write_text("x", encoding="utf-8")

            refreshes.clear()
            model.start_traverse(folder, force=True)
            folder = await self._scanned(model)
            for _ in range(60):  # let the coalesced refresh land
                await omni.kit.app.get_app().next_update_async()

            after = sorted(f.url for f in self._files_of(folder))
            self.assertTrue(any(u.endswith("mat_replacement.usd") for u in after), "the new file was never picked up")
            self.assertEqual(len(after), len(before), "this test needs the count to stay put")
            self.assertTrue(refreshes, "the summary still lists the file that is gone")
        finally:
            model.destroy()


class TestSummaryFollowsRootContent(omni.kit.test.AsyncTestCase):
    """
    The same replacement, with the files in the root itself.

    A child folder is rescued by its parent: the parent's COMPLETED arrives after the child has
    dropped the files the listing no longer returned, so the parent recounts it correctly. A root
    has no parent, and its own COMPLETED arrives before its own cleanup - so the count it published
    counts a file that is already gone.
    """

    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root_path = Path(self._tmp.name)
        for f in range(FILES_PER_FOLDER):
            (self._root_path / f"mat_{f}.usd").write_text("x", encoding="utf-8")
        self._root = self._root_path.as_posix()

    async def tearDown(self):
        self._tmp.cleanup()

    async def _scanned(self, model, started=False):
        deadline = time.time() + 60
        while time.time() < deadline:
            await omni.kit.app.get_app().next_update_async()
            if not started:
                started = bool(model.active_folders)
                continue
            folder = model.get_root_folder(self._root)
            if folder is not None and folder.prepared and not model.active_folders:
                return folder
        self.fail("the root was never scanned")

    def _summary(self, model):
        for collection in model.get_item_children(None):
            for item in model.get_item_children(collection):
                if item.name == model.SUMMARY_FOLDER_NAME:
                    return item
        self.fail("there is no summary item")

    async def test_a_replaced_root_file_leaves_no_stale_count(self):
        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        try:
            self._summary(model)
            folder = await self._scanned(model)

            (self._root_path / "mat_0.usd").unlink()
            (self._root_path / "mat_replacement.usd").write_text("x", encoding="utf-8")

            model.start_traverse(folder, force=True)
            folder = await self._scanned(model)
            for _ in range(60):  # let the coalesced refresh land
                await omni.kit.app.get_app().next_update_async()

            self.assertEqual(len(folder.files), FILES_PER_FOLDER, "the root itself holds the wrong files")
            summary = self._summary(model)
            self.assertEqual(
                len(model.get_detail_items(summary)), FILES_PER_FOLDER, "the summary lists a file that is gone"
            )
            self.assertEqual(summary.count, FILES_PER_FOLDER, "the summary counts a file that is gone")
        finally:
            model.destroy()


class TestHiddenRootPublishes(omni.kit.test.AsyncTestCase):
    """
    A hidden root - the shape the Materials collection ships in - must not publish twice.

    It has no row of its own to hold a stale count: its sub folders are the categories. The
    recount a visible root needs would take the branch that drops the whole folder cache and
    publishes the collection item on the spot, uncoalesced, on top of the coalesced refresh that
    `folder_changed` already asks for from the same post-cleanup state.
    """

    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root_path = Path(self._tmp.name) / "hidden_root"
        self._root_path.mkdir()
        sub = self._root_path / "category"
        sub.mkdir()
        for f in range(FILES_PER_FOLDER):
            (sub / f"mat_{f}.usd").write_text("x", encoding="utf-8")
        self._sub = sub
        self._root = self._root_path.as_posix()

    async def tearDown(self):
        self._tmp.cleanup()

    async def _scanned(self, model, started=False):
        deadline = time.time() + 60
        while time.time() < deadline:
            await omni.kit.app.get_app().next_update_async()
            if not started:
                started = bool(model.active_folders)
                continue
            folder = model.get_root_folder(self._root)
            if folder is not None and folder.prepared and not model.active_folders:
                return folder
        self.fail("the root was never scanned")

    async def test_a_hidden_root_publishes_its_collection_once(self):
        settings = carb.settings.get_settings()
        settings.set(SETTING_ROOT, [self._root])
        settings.set(SETTING_HIDDEN, [self._root_path.name])
        model = TreeFolderBrowserModel(
            setting_folders=SETTING_ROOT,
            setting_folders_hide_in_category=SETTING_HIDDEN,
            filter_file_suffixes=[".usd"],
        )
        try:
            # Build the category items, as opening the browser does. Nothing is traversed until a
            # view asks for them.
            for collection in model.get_item_children(None):
                model.get_item_children(collection)

            folder = await self._scanned(model)
            self.assertTrue(folder.hide_root_in_category, "this test needs a hidden root")

            published = []

            def on_item_changed(_model, item):
                # The collection item is the whole category tree: publishing it rebuilds every row.
                if item is None or item is model._root_collection_item:
                    published.append(time.time())

            sub = model.subscribe_item_changed_fn(on_item_changed)  # noqa: F841 - keep the subscription

            (self._sub / "mat_0.usd").unlink()
            (self._sub / "mat_replacement.usd").write_text("x", encoding="utf-8")

            model.start_traverse(folder, force=True)
            folder = await self._scanned(model)
            for _ in range(60):  # let the coalesced refresh land
                await omni.kit.app.get_app().next_update_async()

            self.assertTrue(published, "the hidden root never published its collection at all")

            # Rebuild the rows, as the view does when it answers that notification. A hidden root
            # drops them on every publish, so without this there is no cache left to protect.
            for collection in model.get_item_children(None):
                model.get_item_children(collection)
            self.assertTrue(model._folder_cache, "the rescan left no rows to cache")

            # The callback itself, rather than a count across a scan: a hidden root publishes its
            # collection several times a scan already, once per traverse status, and a total would
            # measure that rather than this. Called with the state a finished traverse leaves.
            published.clear()
            cached = dict(model._folder_cache)
            model._on_folder_traversed(folder, updated=True)

            self.assertEqual(published, [], "a finished hidden root rebuilt the whole collection again")
            self.assertEqual(model._folder_cache, cached, "a finished hidden root dropped the row cache")
        finally:
            model.destroy()
