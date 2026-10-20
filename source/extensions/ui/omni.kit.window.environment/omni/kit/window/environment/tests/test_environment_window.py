# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

import carb.tokens
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
from omni.ui.tests.test_base import OmniUiTest

from ..models import EnvType

TEST_WINDOW_WIDTH = 1280
TEST_PROPERTY_WIDTH = 450
GOLDEN_IMG_DIR = Path(
    carb.tokens.get_tokens_interface().resolve("${omni.kit.window.environment}/data/tests/golden_img")
)


class TestEnviromentWindow(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = GOLDEN_IMG_DIR.absolute()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_browser_ui(self):
        browser = omni.kit.window.environment.get_instance()
        await self.docked_test_window(window=browser._window, width=TEST_WINDOW_WIDTH, height=720)

        # Make search bar has correct width
        browser._window.width = 1200
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()
        browser._window.width = 1280
        await omni.kit.app.get_app().next_update_async()

        browser._window._widget._h_splitter.offset_x = TEST_WINDOW_WIDTH - TEST_PROPERTY_WIDTH

        # Wait for folder and thumbnails load completed
        await self.__wait_collection_loaded(browser._window)
        await asyncio.sleep(10)

        await self.finalize_test(
            golden_img_dir=self._golden_img_dir,
            golden_img_name="test_enviroment_window.png",
        )

    async def test_navigate_to_dynamic_skies(self):
        omni.usd.get_context().new_stage()
        browser = omni.kit.window.environment.get_instance()
        await self.docked_test_window(window=browser._window, width=1280, height=720, block_devices=False)

        # Wait for folder and thumbnails load completed
        await self.__wait_collection_loaded(browser._window)
        await asyncio.sleep(10)
        await omni.kit.app.get_app().next_update_async()

        browser._window.navigate_to_dynamic_skies()

        await ui_test.wait_n_updates(5)

        browser_widget = browser._window._widget._browser_widget
        model = browser._window._model
        self.assertTrue(len(browser_widget.category_selection) > 0)
        for category in browser_widget.category_selection:
            details = model.get_item_children(category)
            for detail in details:
                self.assertEqual(detail.type, EnvType.USD)

    async def __wait_collection_loaded(self, window, collection_index=0):
        browser_widget = window._widget._browser_widget
        browser_widget.collection_index = collection_index
        await omni.kit.app.get_app().next_update_async()
        model = window._model
        collections = model.get_item_children(None)
        categories = model.get_item_children(collections[collection_index])
        browser_widget.category_selection = [categories[1]]
        await omni.kit.app.get_app().next_update_async()
        browser_widget.category_selection = [categories[2]]
        while True:
            for category in categories:
                if hasattr(category, "folder") and not category.folder.prepared:
                    await omni.kit.app.get_app().next_update_async()
                    break
            else:
                await omni.kit.app.get_app().next_update_async()  # OMPE-32822
                browser_widget.category_selection = [categories[0]]
                return
