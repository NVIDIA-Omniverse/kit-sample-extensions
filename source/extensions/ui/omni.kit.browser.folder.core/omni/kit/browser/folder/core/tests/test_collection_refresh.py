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
Coalescing the collection notification during a scan.

Notifying the collection item is the heaviest notification the model makes - it evicts the cached
children of the whole tree - and a traverse raises one per folder that ends with changes.

What these really guard is the other half: collapsing them must not make the browser feel slow when
nothing is scanning, so an idle model notifies straight through.
"""

import asyncio
import tempfile
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test

from ..models import TreeFolderBrowserModel
from ..models.tree_folder_browser_model import COLLECTION_REFRESH_INTERVAL_SCANNING

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/collection_refresh_root"


class TestCollectionRefresh(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "a.usd").write_text("x", encoding="utf-8")
        self._root = root.as_posix()

        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        self._model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        # The collection item is built on demand, and the coalescer notifies whatever
        # _root_collection_item holds - which is None until something asks for the children.
        self._model.get_item_children(None)
        self.assertIsNotNone(self._model._root_collection_item, "no collection item to notify")

        self._notified = []
        self._real_item_changed = self._model._item_changed
        self._model._item_changed = lambda item: (self._notified.append(item), self._real_item_changed(item))[1]

    async def tearDown(self):
        self._model._item_changed = self._real_item_changed
        self._model.destroy()
        self._tmp.cleanup()

    def _request(self):
        # Called directly rather than through a traverse, which would make these tests about
        # traversal timing instead of about the coalescing.
        self._model._request_collection_refresh()

    async def test_an_idle_model_notifies_straight_away(self):
        """No scan means no flood, and a change the user just made must not be held back."""
        self._model.active_folders = []
        self._request()
        self.assertEqual(len(self._notified), 1, "an idle refresh should not be deferred")

    async def test_a_scan_collapses_many_requests_into_one(self):
        """The point of the change: a traverse raises one of these per folder it finishes."""
        self._model.active_folders = [self._model.get_root_folder(self._root)]
        for _ in range(25):
            self._request()
        self.assertEqual(self._notified, [], "a scanning refresh should not fire synchronously")

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        await asyncio.sleep(COLLECTION_REFRESH_INTERVAL_SCANNING * 1.2)
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(len(self._notified), 1, f"25 requests became {len(self._notified)} notifications")

    async def test_the_next_request_after_one_lands_is_scheduled_again(self):
        """Collapsing must not latch: the view still has to keep up with a long scan."""
        self._model.active_folders = [self._model.get_root_folder(self._root)]
        self._request()
        await asyncio.sleep(COLLECTION_REFRESH_INTERVAL_SCANNING * 1.2)
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(len(self._notified), 1)

        self._request()
        await asyncio.sleep(COLLECTION_REFRESH_INTERVAL_SCANNING * 1.2)
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(len(self._notified), 2, "the coalescer stopped delivering after the first")
