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
Removing a collection whose scan was cancelled.

Reported: add `C:`, cancel the scan, select it, remove the collection - and nothing happens.

The model removes it; the view is never told. `remove_root_folder` pops the row from the browser
item cache and calls `folder_changed`, which chose between "refresh this row" and "a root was
removed" on prepared and has_update - and a cancelled collection satisfies the first, so it
refreshed a row that had just been popped.

These assert the notification, not the model state, which was right all along.
"""

import tempfile
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test

from ..models import TreeFolderBrowserModel
from ..models.traverse_context import TraverseState

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/remove_after_cancel"


class TestRemoveAfterCancel(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "sub").mkdir()
        (root / "sub" / "a.usd").write_text("x", encoding="utf-8")
        self._root = root.as_posix()

        carb.settings.get_settings().set(SETTING_ROOT, [])
        self._model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

    async def tearDown(self):
        self._model.destroy()
        self._tmp.cleanup()

    async def _settle(self, frames=10):
        for _ in range(frames):
            await omni.kit.app.get_app().next_update_async()

    async def _root_rows(self):
        collections = self._model.get_item_children(None)
        return self._model.get_item_children(collections[0]) if collections else []

    async def test_removing_a_cancelled_collection_refreshes_the_tree(self):
        """
        The reported bug, isolated to the branch that decides it.

        Driven through folder_changed rather than remove_root_folder: removal notifies the tree by
        several routes - the ancestor walk, the settings write - and any of them can mask the one
        under test. What broke was the choice folder_changed makes for a collection that is gone but
        was left prepared with no updates, which is precisely what cancelling leaves behind.
        """
        folder = self._model.append_root_folder(self._root, save=False)
        await self._settle()
        self._model.start_traverse(folder)
        await self._settle()
        self._model._cancel_traverse(self._root)
        await self._settle()
        await self._root_rows()

        # The state an interrupted scan leaves, set rather than raced for. A cancel only lands in
        # this state if it interrupts a scan still running; with a fixture small enough to be
        # deterministic the traverse always finishes first and has_update stays True. Measured in a
        # running app against a real drive: prepared True, has_update False.
        folder.prepared = True
        folder.has_update = False

        # The state remove_root_folder leaves before it calls folder_changed.
        self._model._root_folders.remove(folder)
        self._model._folder_cache.pop(folder, None)

        notified = []
        real = self._model._item_changed
        self._model._item_changed = lambda item: (notified.append(item), real(item))[1]
        try:
            self._model.folder_changed(folder)
        finally:
            self._model._item_changed = real

        self.assertIn(
            self._model._root_collection_item,
            notified,
            "a removed collection that was cancelled never told the tree, so the row stays on "
            "screen and the delete looks like it failed",
        )

    async def test_a_cancelled_collection_can_still_be_removed(self):
        """
        The reported sequence, at the model level.

        The cancel is asserted rather than assumed: a fixture this small can finish its traverse
        first, and then this would be a test about removing an ordinary collection - which works,
        and is not what was reported.
        """
        # Enough folders that there is still a scan to cancel. The setUp tree is two entries and
        # finishes within a frame, so cancelling it would report nothing was running - and this
        # would quietly become a test about removing an ordinary collection, which always worked.
        root = Path(self._tmp.name)
        for d in range(60):
            sub = root / f"folder_{d:02d}"
            sub.mkdir()
            for f in range(10):
                (sub / f"mat_{f}.usd").write_text("x", encoding="utf-8")

        folder = self._model.append_root_folder(self._root, save=False)
        await self._settle()
        self._model.start_traverse(folder)
        self.assertTrue(self._model._cancel_traverse(self._root), "there was no scan left to cancel")
        self.assertIs(folder.traverse_ctx.state, TraverseState.CANCELLED, "the collection was not cancelled")
        await self._settle()

        rows = await self._root_rows()
        self.assertTrue(rows, "a cancelled collection left no row to select")

        self.assertTrue(self._model.remove_root_folder(self._root), "removal reported failure")
        self.assertIsNone(self._model.get_root_folder(self._root), "the collection is still registered")

    async def test_a_drive_root_url_round_trips(self):
        """
        `C:` is the url in the report, and the one whose derived name ends in a colon - saved as
        "{name}::{url}", a trailing colon would split into three fields and be unreadable.
        """
        folder = self._model.append_root_folder("C:", save=False, sync=False)
        self.assertIsNotNone(folder, "a drive root could not be added")
        try:
            self.assertEqual(folder.url, "C:")
            self.assertEqual(folder.name, "C", "the colon must be dropped from the name")
            self.assertEqual(f"{folder.name}::{folder.url}".split("::"), ["C", "C:"])
            self.assertIsNotNone(self._model.get_root_folder("C:"), "a drive root cannot be found by url")
        finally:
            self._model.remove_root_folder("C:")
