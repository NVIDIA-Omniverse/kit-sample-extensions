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
The spinner that disappears while a collection is still scanning.

Nothing clears the loading flag. A ``hide_root_in_category`` collection finishing with updates makes
``folder_changed`` empty the whole browser item cache, which is where the category rows live -
including the rows of collections still scanning. A row that no longer exists draws nothing, so the
spinner vanishes with the flag still set on an object the tree has discarded.

These assert the row's survival rather than the flag, which is why an earlier attempt watching the
flag found nothing.
"""

import tempfile
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test

from ..models import TreeFolderBrowserModel

SETTING_ROOTS = "/exts/omni.kit.browser.folder.core/test/spinner_roots"
SETTING_HIDDEN = "/exts/omni.kit.browser.folder.core/test/spinner_hidden"


def _usd_only(url: str) -> bool:
    return url.endswith(".usd")


class TestSpinnerRow(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)

        # Two collections. "hidden" is the one that finishes and triggers the cache wipe; it needs a
        # sub folder because a hidden root shows its children in the category tree rather than
        # itself. "scanning" stands in for the collection the user is watching.
        self._hidden = root / "hidden"
        (self._hidden / "sub").mkdir(parents=True)
        (self._hidden / "sub" / "a.usd").write_text("x", encoding="utf-8")

        self._scanning = root / "scanning"
        (self._scanning / "sub").mkdir(parents=True)
        (self._scanning / "sub" / "b.usd").write_text("x", encoding="utf-8")

        settings = carb.settings.get_settings()
        settings.set(SETTING_ROOTS, [self._hidden.as_posix(), self._scanning.as_posix()])
        settings.set(SETTING_HIDDEN, ["hidden"])

        self._model = TreeFolderBrowserModel(
            setting_folders=SETTING_ROOTS,
            setting_folders_hide_in_category=SETTING_HIDDEN,
            filter_file_suffixes=[".usd"],
        )
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

    async def tearDown(self):
        self._model.destroy()
        self._tmp.cleanup()

    async def _build_rows(self):
        """Ask for the tree the user sees, which is what puts the category rows in the cache."""
        rows = {}
        for collection in self._model.get_item_children(None):
            for category in self._model.get_item_children(collection):
                rows[category.name] = category
        return rows

    def _row_for(self, folder):
        return self._model._folder_cache.get(folder, None)

    async def test_a_finishing_collection_discards_a_scanning_collection_row(self):
        """
        The hypothesis, stated as an assertion.

        A row that is gone cannot spin, however the flag on it is set. If this fails, the reported
        disappearance is something else and the search moves elsewhere.
        """
        hidden = self._model.get_root_folder(self._hidden.as_posix())
        scanning = self._model.get_root_folder(self._scanning.as_posix())
        self.assertIsNotNone(hidden)
        self.assertIsNotNone(scanning)

        await scanning.start_traverse()
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        await self._build_rows()

        sub = scanning.sub_folders[0] if scanning.sub_folders else None
        self.assertIsNotNone(sub, "the scanning collection has no sub folder, so it has no row")
        self.assertIsNotNone(self._row_for(sub), "no row was built for the scanning collection")

        # Mark it as the user would see it: still working.
        self._row_for(sub).loading = True
        if scanning not in self._model.active_folders:
            self._model.active_folders.append(scanning)

        # Now the other collection finishes with updates, which is the path that empties the cache.
        hidden.prepared = True
        hidden.has_update = True
        self._model.folder_changed(hidden)

        row_after = self._row_for(sub)
        self.assertIsNotNone(
            row_after,
            "a collection finishing threw away the row of one still scanning - the spinner has "
            "nothing left to draw, which is the reported disappearance",
        )
        self.assertTrue(
            row_after.loading,
            "the scanning collection's row stopped reporting itself as loading",
        )

    async def test_the_loading_flag_itself_is_never_cleared(self):
        """
        Separates the two explanations.

        If the flag survives while the row does not, the fault is the cache wipe. If the flag is
        cleared, it is something in the traverse lifecycle instead, and this test says so.
        """
        hidden = self._model.get_root_folder(self._hidden.as_posix())
        scanning = self._model.get_root_folder(self._scanning.as_posix())

        await scanning.start_traverse()
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        await self._build_rows()

        sub = scanning.sub_folders[0]
        row = self._row_for(sub)
        self.assertIsNotNone(row)
        row.loading = True
        if scanning not in self._model.active_folders:
            self._model.active_folders.append(scanning)

        hidden.prepared = True
        hidden.has_update = True
        self._model.folder_changed(hidden)

        # Held deliberately: the object the tree was drawing, whether or not the model still knows
        # about it. Its flag surviving is what points at the cache rather than the lifecycle.
        self.assertTrue(row.loading, "something cleared the loading flag on the row being drawn")
