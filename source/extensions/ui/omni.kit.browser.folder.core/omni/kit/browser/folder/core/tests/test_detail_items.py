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
Assembling the detail items of a folder.

Sub folder results are assembled with ``extend`` rather than ``detail_items + ...``, which
allocated a fresh list per sub folder - O(n * k) copying for k sub folders holding n items between
them. This pins what comes back, since the rewrite must not change it.

A companion change that kept the per-file detail items across a traverse was reverted: it was never
measured, it appeared in none of the sixteen stack captures taken while the app was frozen, and the
run carrying it grew to 15 GB against 5.7 GB without it.
"""

import tempfile
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test

from ..models import TreeFolderBrowserModel

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/detail_root"


class TestDetailItems(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        for name in ("a.usd", "b.usd"):
            (root / name).write_text("x", encoding="utf-8")
        sub = root / "sub"
        sub.mkdir()
        for name in ("c.usd", "d.usd"):
            (sub / name).write_text("x", encoding="utf-8")
        self._root = root.as_posix()

    async def tearDown(self):
        self._tmp.cleanup()

    async def _model(self):
        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        folder = model.get_root_folder(self._root)
        await folder.start_traverse()
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        return model, folder

    async def test_sub_folder_items_are_still_gathered(self):
        """The extend() rewrite must not change what comes back."""
        model, folder = await self._model()
        model._show_category_subfolders = True
        items = model._get_folder_detail_items(folder)
        names = sorted(i.name for i in items)
        self.assertEqual(
            names, ["a.usd", "b.usd", "c.usd", "d.usd"], "gathering sub folder items dropped or duplicated something"
        )
        model.destroy()
