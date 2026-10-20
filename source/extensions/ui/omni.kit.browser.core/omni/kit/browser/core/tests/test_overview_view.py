# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from pathlib import Path
from typing import List, Tuple

import carb.input
import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.kit.browser.core import DetailDelegate
from omni.ui.tests.test_base import OmniUiTest

from ..models import ChildrenModelWrapper
from ..widgets.overview_view import OverviewView
from ..widgets.style import UI_STYLES
from .common import TreeBrowserModel

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestOverviewView(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._browser_model = TreeBrowserModel(overview_name="ALL")
        self._overview_model = ChildrenModelWrapper()
        colleciton_items = self._browser_model.get_item_children(None)
        category_items = self._browser_model.get_item_children(colleciton_items[0])
        self._overview_model.set_sources(self._browser_model, category_items[0])

        self._window = await self.create_test_window(width=500, height=600, block_devices=False)
        self._window.frame.set_style(UI_STYLES)
        with self._window.frame:
            self._view = OverviewView(self._overview_model, delegate=DetailDelegate(self._browser_model))

        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()

    # After running each test
    async def tearDown(self):
        self._view.destroy()
        await super().tearDown()

    async def test_general(self):
        """Testing general look of OverviewView"""
        # Wait for icons loaded
        await asyncio.sleep(5)

        self.assertEqual(self._view.thumbnail_size, 128)

        self._view.center(True)
        await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="overview_general.png")

    async def test_thumbnail_size(self):
        """Testing thumbnail size of OverviewView"""
        self._view.thumbnail_size = 64
        # Wait for icons loaded
        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self._view.thumbnail_size, 64)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="overview_thumbnail_size.png")

    async def test_search_filter(self):
        self._view.filter(["5"])
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="overview_filer.png")
