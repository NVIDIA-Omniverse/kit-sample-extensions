# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path

import omni.kit.app
import omni.kit.window.preferences
import omni.ui as ui
from omni.kit.viewport.utility import get_active_viewport
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 1280, 600


class TestPreference(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        await self.create_test_area(width=TEST_WIDTH, height=TEST_HEIGHT)

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_viewport_preference(self):
        await self._test_preference_page("Environment")

    async def _test_preference_page(self, title: str):
        # hack to remove other pages and only keep the current page being tested, to avoid image difference in page
        # order
        _original_pages = omni.kit.window.preferences.get_page_list()
        original_pages_copy = _original_pages.copy()

        for page in original_pages_copy:
            if page.get_title() == title:
                omni.kit.window.preferences.select_page(page)
            else:
                omni.kit.window.preferences.unregister_page(page)
        # hack to replace the created preferences records in ext instance so it won't error on shutdown
        omni.kit.window.preferences.get_instance()._created_preferences = _original_pages

        omni.kit.window.preferences.rebuild_pages()
        omni.kit.window.preferences.show_preferences_window()
        await omni.kit.app.get_app().next_update_async()

        w = ui.Workspace.get_window("Preferences")
        await self.docked_test_window(window=w, width=1280, height=600, block_devices=False)
        await omni.kit.app.get_app().next_update_async()

        # Wait for a few frames for ETM failure with kit 105
        for _ in range(40):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=f"{title}.png")
