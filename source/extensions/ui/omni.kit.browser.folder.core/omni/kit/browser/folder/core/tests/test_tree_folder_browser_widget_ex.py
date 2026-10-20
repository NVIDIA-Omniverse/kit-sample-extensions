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

import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.browser.folder.core import BrowserPropertyDelegate, FolderBrowserModel, TreeFolderBrowserWidgetEx
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class GeneralPropertyDelegate(BrowserPropertyDelegate):
    def accepted(self, detail_items) -> bool:
        return True

    def build_widgets(self, detail_items) -> None:
        ui.Label("This property delegate always visible, no matter if items selected", height=0, word_wrap=True)


class SinglePropertyDelegate(BrowserPropertyDelegate):
    def accepted(self, detail_items) -> bool:
        return len(detail_items) == 1

    def build_widgets(self, detail_items) -> None:
        ui.Label("This property delegate only visible when only 1 item selected", height=0, word_wrap=True)


class MultiPropertyDelegate(BrowserPropertyDelegate):
    def accepted(self, detail_items) -> bool:
        return len(detail_items) > 1

    def build_widgets(self, detail_items) -> None:
        ui.Label("This property delegate only visible when more than 1 items selected", height=0, word_wrap=True)


class TestFolderBrowserWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._browser_model = FolderBrowserModel()
        self._browser_model.append_root_folder(f"{TEST_DATA_PATH}/test_root/", save=False)
        self._browser_widget = None

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        if self._browser_widget:
            self._browser_widget.destroy()
        if self._browser_model:
            self._browser_model.destroy()

    async def test_property_view(self):
        """Testing general look of TreeFolderBrowserWidgetEx"""
        window = await self.create_test_window(width=500, height=600, block_devices=False)
        with window.frame:
            self._browser_widget = TreeFolderBrowserWidgetEx(
                self._browser_model,
                property_delegates=[GeneralPropertyDelegate(), SinglePropertyDelegate(), MultiPropertyDelegate()],
            )

        await omni.kit.app.get_app().next_update_async()
        # Wait for icons loaded
        await asyncio.sleep(1)

        collections = self._browser_model.get_item_children(None)
        categories = self._browser_model.get_item_children(collections[0])
        details = self._browser_model.get_item_children(categories[0])

        try:
            await self.capture_and_compare(
                golden_img_dir=self._golden_img_dir, golden_img_name="property_no_selection.png"
            )

            self._browser_widget.detail_selection = [details[0]]
            await omni.kit.app.get_app().next_update_async()
            await self.capture_and_compare(
                golden_img_dir=self._golden_img_dir, golden_img_name="property_single_selection.png"
            )

            self._browser_widget.detail_selection = [details[0], details[1]]
            await omni.kit.app.get_app().next_update_async()
            await self.capture_and_compare(
                golden_img_dir=self._golden_img_dir, golden_img_name="property_multi_selection.png"
            )

            ref_property_btn = ui_test.WidgetRef(self._browser_widget._toolbar.btn_property, "", window)
            await ref_property_btn.click()
            await ui_test.emulate_mouse_move(ui_test.Vec2(0, 0))
            await omni.kit.app.get_app().next_update_async()
            await self.capture_and_compare(golden_img_dir=self._golden_img_dir, golden_img_name="no_property.png")
        finally:
            await self.finalize_test_no_image()
