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
from unittest.mock import Mock

import omni.kit.app
import omni.kit.clipboard
import omni.kit.test
import omni.kit.ui_test as ui_test
from omni.ui.tests.test_base import OmniUiTest

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")
SETTINGS_PATH = "/persistent/app/stage/instanceableOnCreatingReference"


# pylint: disable=protected-access
class TestAssetBrowser(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._stage_dir = TEST_DATA_PATH.absolute().joinpath("stage").absolute()
        self._browser = omni.kit.browser.asset.get_instance()
        self._window = self._browser._window

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    # async def test_browser_ui(self):
    #     await self.docked_test_window(window=self._window, width=1280, height=720)
    #     await omni.kit.app.get_app().next_update_async()
    #     await self.__wait_collection_loaded()
    #     # Wait for folder and thumbnails load completed
    #     await asyncio.sleep(8)

    #     await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="test_asset.png")

    async def test_drag_and_drop_item(self):
        model = omni.kit.browser.asset.model.AssetBrowserModel()
        delegate = omni.kit.browser.asset.delegate.AssetDetailDelegate(model)
        delegate._instanceable_categories = ["mock"]

        item = Mock()
        item.name = "Mock"
        item.url = "omniverse://mock/mock.usd"
        item.thumbnail = "omniverse:://mock/mock.png"

        url = delegate.on_drag(item)
        self.assertEqual(item.url, url)
        self.assertEqual(delegate._dragging_url, url)
        self.assertTrue(delegate._on_drop_accepted(url))
        old_settings = delegate._settings.get(SETTINGS_PATH)
        delegate._settings.set_bool(SETTINGS_PATH, True)
        self.assertIsNone(delegate._on_drop(url, None, None, None))
        self.assertIsNone(delegate._dragging_url)
        delegate._settings.set_bool(SETTINGS_PATH, False)
        delegate._dragging_url = url
        delegate._on_drop(url, None, None, None)
        self.assertTrue(delegate._settings.get(SETTINGS_PATH))
        delegate._settings.set_bool(SETTINGS_PATH, old_settings)
        delegate.destroy()

    async def test_context_menu(self):
        model = omni.kit.browser.asset.model.AssetBrowserModel()
        delegate = omni.kit.browser.asset.delegate.AssetDetailDelegate(model)
        delegate._instanceable_categories = ["mock"]

        item = Mock()
        item.name = "Mock"
        item.url = self._stage_dir.joinpath("cube.usda").as_posix()

        delegate.on_right_click(item)
        self.assertEqual(item, delegate._action_item)
        self.assertIsNotNone(delegate._context_menu)
        self.assertEqual(delegate._context_menu.url, item.url)
        ref_menu = ui_test.WidgetRef(delegate._context_menu, "")

        async def _find_menu_item(name):
            delegate.on_right_click(item)
            await ui_test.human_delay()
            ref_menu_item = ref_menu.find(f"MenuItem[*].text.endswith('{name}')")
            self.assertIsNotNone(ref_menu_item)
            await ui_test.human_delay()
            return ref_menu_item

        ref_collect = await _find_menu_item("Collect")
        await ui_test.emulate_mouse_move_and_click(ref_collect.center)
        collect_window = ui_test.find("Collection Options")
        await collect_window.focus()
        collect_window_cancel_button = collect_window.find("**/Button[*].text=='Cancel'")
        await collect_window_cancel_button.click()

        ref_add = await _find_menu_item("Add at Current Selection")
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()
        self.assertIsNotNone(stage)
        await ui_test.emulate_mouse_move_and_click(ref_add.center)
        cube = stage.GetPrimAtPath("/cube/Cube")
        self.assertTrue(cube.IsValid(), "Prim from file to be added is invalid")

        item.url = self._stage_dir.joinpath("cylinder.usda").as_posix()
        ref_replace = await _find_menu_item("Replace Current Selection")
        await ui_test.emulate_mouse_move_and_click(ref_replace.center)
        cylinder = stage.GetPrimAtPath("/cylinder/Cylinder")
        self.assertTrue(cylinder.IsValid(), "Prim from file to be added is invalid")

        ref_copy_link = await _find_menu_item("Copy URL Link")
        old_clip = omni.kit.clipboard.paste()
        # Empty string could be converted to nullptr by pybind, which would
        # crash in Windowing::setClipboard on Linux
        omni.kit.clipboard.copy("test")
        await omni.kit.app.get_app().next_update_async()
        await ui_test.emulate_mouse_move_and_click(ref_copy_link.center)
        self.assertEqual(omni.kit.clipboard.paste(), item.url)
        omni.kit.clipboard.copy(old_clip)

        delegate.destroy()

    async def test_execute_item(self):
        model = omni.kit.browser.asset.model.AssetBrowserModel()

        item = Mock()
        item.name_model.as_string = "Mock"
        item.url = self._stage_dir.joinpath("empty_stage.usda").as_posix()

        omni.usd.get_context().new_stage()
        model.execute(item)
        self.assertTrue(omni.usd.get_context().get_stage().GetPrimAtPath("/empty_stage").IsValid())

    async def __wait_collection_loaded(self, collection_index=0):
        browser_widget = self._window._widget._browser_widget
        browser_widget.collection_index = collection_index
        await omni.kit.app.get_app().next_update_async()
        model = self._window._browser_model
        collections = model.get_item_children(None)
        categories = model.get_item_children(collections[collection_index])
        browser_widget.category_selection = [categories[1]]
        while True:
            for category in categories:
                if hasattr(category, "folder") and not category.folder.prepared:
                    await omni.kit.app.get_app().next_update_async()
                    break
            else:
                # Always expand first category
                await omni.kit.app.get_app().next_update_async()
                collections = model.get_item_children(None)
                categories = model.get_item_children(collections[collection_index])
                browser_widget._category_view.set_expanded(categories[1], True, True)
                await omni.kit.app.get_app().next_update_async()
                return model.get_item_children(categories[1])
