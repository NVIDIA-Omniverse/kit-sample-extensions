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
from typing import List

import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.kit.browser.core import (
    AbstractBrowserModel,
    BrowserSearchBar,
    BrowserWidget,
    CategoryItem,
    CollectionItem,
    DetailItem,
    OptionMenuDescription,
)
from omni.ui.tests.test_base import OmniUiTest

from ..widgets.style import UI_STYLES
from .common import SimpleBrowserModel

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestBrowserSearchBar(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._browser_model = SimpleBrowserModel()
        self._browser_widget = BrowserWidget(self._browser_model)

    # After running each test
    async def tearDown(self):
        self._search_bar.destroy()
        await super().tearDown()

    async def test_general(self):
        """Testing general look of TreeBrowserWidget"""
        window = await self.create_test_window(width=500, height=600, block_devices=False)
        with window.frame:
            self._search_bar = BrowserSearchBar(style=UI_STYLES)

        def __on_search(words) -> None:
            self.__search_words = words

        def __on_additional_search(words) -> None:
            pass

        self._search_bar.bind_browser_widget(self._browser_widget)
        self._search_bar.add_on_search_fn(__on_search)
        self._search_bar.set_navigation_clicked_fn(None)
        self._search_bar.clear_search()
        self.assertIsNone(self.__search_words)
        await omni.kit.app.get_app().next_update_async()
        self._search_bar._options_menu.append_menu_item(OptionMenuDescription(""))
        self._search_bar._options_menu.append_menu_item(OptionMenuDescription("Disabled", enabled_fn=lambda: False))
        self._search_bar._options_menu.append_menu_item(
            OptionMenuDescription("Get Text", get_text_fn=lambda: "New Text")
        )
        self._search_bar._options_menu.append_menu_item(OptionMenuDescription("invisible", visible_fn=lambda: False))

        window_ref = ui_test.WindowRef(window, "")
        navigation_ref = window_ref.find_all(f"**/Button[*].name=='navigation'")[0]
        self.assertEqual(self._search_bar.navigation_button, navigation_ref.widget)
        await navigation_ref.click()
        options_ref = window_ref.find_all(f"**/Button[*].name=='options'")[0]
        await options_ref.click()
        await omni.kit.app.get_app().next_update_async()

        ret = self._search_bar.remove_on_search_fn(__on_search)
        self.assertTrue(ret)
        ret = self._search_bar.remove_on_search_fn(__on_additional_search)
        self.assertFalse(ret)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="search_bar.png")
