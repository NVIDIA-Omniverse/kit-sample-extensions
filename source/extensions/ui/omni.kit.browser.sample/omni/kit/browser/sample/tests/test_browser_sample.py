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

import omni.kit.app
import omni.kit.test
import omni.ui as ui
from omni.ui.tests.test_base import OmniUiTest

from ..model import SampleBrowserModel

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestSampleBrowser(OmniUiTest):
    """Test the Samples Browser with a simple golden image test."""

    async def setUp(self):
        """Before running each test."""
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        ui.Workspace.show_window("Examples")

    async def tearDown(self):
        """After running each test."""
        await super().tearDown()

    async def test_browser_ui(self):
        """Test a simple browser window without doing anything after loading."""
        browser = omni.kit.browser.sample.get_instance()
        await self.docked_test_window(window=browser.get_window(), width=1280, height=720)
        model: SampleBrowserModel = browser.get_model()
        # Wait for folder and thumbnails load completed
        for root_folder in model._root_folders:
            model.start_traverse(root_folder)
        for root_folder in model._root_folders:
            while not root_folder.prepared:
                await omni.kit.app.get_app().next_update_async()
        await asyncio.sleep(2)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="test_sample.png")
