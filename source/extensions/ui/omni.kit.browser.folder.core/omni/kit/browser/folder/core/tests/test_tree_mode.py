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
import os
import shutil
import stat
from pathlib import Path
from tempfile import TemporaryDirectory

import carb.settings
import omni.kit.app
import omni.kit.ui_test as ui_test
from carb.input import KeyboardInput
from omni.kit.browser.core import TreeCategoryDelegate
from omni.kit.browser.folder.core import (
    FolderBrowserModel,
    FolderBrowserWidget,
    TreeFolderBrowserModel,
    TreeFolderBrowserWidget,
)
from omni.ui.tests.test_base import OmniUiTest

from ..widgets.predownload import PredownloadHelper

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
ROOT_FOLDER = f"{TEST_DATA_PATH}/test_root"
NEW_ROOT_FOLDER = f"{TEST_DATA_PATH}/new_root"


class TestTreeFolderBrowserWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        self._temp_dir = TemporaryDirectory()
        self._cache_file = f"{self._temp_dir.name}/tree.cache.json"
        self._root_folder = f"{self._temp_dir.name}/test_root"
        self._copy_tree(ROOT_FOLDER, self._root_folder)
        self._new_root_folder = f"{self._temp_dir.name}/new_root"
        self._copy_tree(NEW_ROOT_FOLDER, self._new_root_folder)
        self._new_file = f"{self._root_folder}/txts/NEW_FILE.txt".replace("\\", "/")
        self._new_sub_folder = f"{self._root_folder}/new_sub"

        self._window = await self.create_test_window(width=500, height=600, block_devices=False)
        settings = carb.settings.get_settings()
        setting_folders = "/persistent/exts/omni.kit.browser.folder.core.test/folders"
        settings.set(setting_folders, [self._root_folder])
        setting_folders_hide_in_category = "/exts/omni.kit.browser.folder.core/folders_hide_in_category"
        settings.set(setting_folders_hide_in_category, ["new_root"])

        # Let's create cache file first to used for tests later
        model = TreeFolderBrowserModel(
            setting_folders=setting_folders,
            local_cache_file=self._cache_file,
            setting_folders_hide_in_category=setting_folders_hide_in_category,
        )
        collections = model.get_item_children(None)
        categories = model.get_item_children(collections[0])
        root_folder = model.get_root_folder(self._root_folder)
        while not root_folder.prepared:
            await omni.kit.app.get_app().next_update_async()

        # Model for test
        self._browser_model = TreeFolderBrowserModel(
            setting_folders=setting_folders,
            local_cache_file=self._cache_file,
            setting_folders_hide_in_category=setting_folders_hide_in_category,
        )
        with self._window.frame:
            self._browser_widget = TreeFolderBrowserWidget(
                self._browser_model,
            )
        await self.docked_test_window(window=self._window, width=500, height=600, block_devices=False)
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

    # After running each test
    async def tearDown(self):
        self._temp_dir.cleanup()
        self._browser_widget.destroy()
        self._browser_model.destroy()
        self._window.destroy()
        await super().tearDown()

    async def test_1_general(self):
        # Wait for folder items loaded
        root_folder = self._browser_model.get_root_folder(self._root_folder)
        self._browser_widget.select_folder(root_folder, expand=True)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_1_general.png")

    async def test_2_add_remove_root(self):
        folder = self._browser_model.process_root_folder(self._new_root_folder, sync=False)
        self._browser_model.start_traverse(folder)
        await omni.kit.app.get_app().next_update_async()
        while not folder.prepared:
            await omni.kit.app.get_app().next_update_async()
        self._browser_widget.select_folder(folder, expand=True)
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_2_add_root.png")

        # finalize_test restored the main window; capture the second image in the same test area.
        await self.docked_test_window(window=self._window, width=500, height=600, block_devices=False)
        self._browser_model.remove_root_folder(self._new_root_folder)
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_3_remove_root.png")

    async def test_4_add_file(self):
        # Create new file
        shutil.copy(f"{TEST_DATA_PATH}/new_sub/NEW_FILE.txt", self._new_file)
        # Select root folder to check changed from cache
        root_folder = self._browser_model.get_root_folder(self._root_folder)
        self._browser_widget.select_folder(root_folder, expand=True)
        while not root_folder.prepared:
            await omni.kit.app.get_app().next_update_async()
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_4_add_file.png")

    async def test_5_del_file(self):
        # Move file
        shutil.move(f"{self._root_folder}/txts/text.txt", f"{self._temp_dir.name}/text_moved.txt")
        # Select root foler to check changed from cache
        root_folder = self._browser_model.get_root_folder(self._root_folder)
        self._browser_widget.select_folder(root_folder, expand=True)
        while not root_folder.prepared:
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_5_del_file.png")

    async def test_6_add_folder(self):
        # Create new folder
        shutil.copytree(f"{TEST_DATA_PATH}/new_sub", self._new_sub_folder)

        # Select root foler to check changed from cache
        root_folder = self._browser_model.get_root_folder(self._root_folder)
        self._browser_widget.select_folder(root_folder, expand=True)
        while not root_folder.prepared:
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_6_add_folder.png")

    async def test_7_del_folder(self):
        shutil.rmtree(f"{self._root_folder}/icons")
        root_folder = self._browser_model.get_root_folder(self._root_folder)
        self._browser_widget.select_folder(root_folder, expand=True)
        while not root_folder.prepared:
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_7_del_folder.png")

    async def test_8_options_menu(self):
        # Rt-click to show context menu
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(485, 15), human_delay_speed=2)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        # Click on Add Collection
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(485, 25), human_delay_speed=2)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        # Click in Open File Path field
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 580), human_delay_speed=2)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        # Type a file path into the field
        await ui_test.emulate_char_press(str(self._golden_img_dir), human_delay_speed=2)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        # Close the filepicker dialog by pressing Enter
        await ui_test.emulate_keyboard_press(KeyboardInput.ESCAPE)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        # Do it procedurally instead
        self._browser_widget._on_folder_picked(str(self._golden_img_dir))
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        self._browser_model.folder_changed(None)

        # Select Current collection
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(50, 75), human_delay_speed=2)
        # Rt-click to show context menu
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        self.assertIsNotNone(self._browser_widget.category_selection)

        # Click on gear menu
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(485, 15), human_delay_speed=2)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        # Click on Remove Collection
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(485, 50), human_delay_speed=2)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_8_options_menu.png")

    async def test_8a_options_menu(self):

        self.assertFalse(self._browser_widget._options_menu._is_download_collection_enable())

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        # Click on a category
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(50, 75), human_delay_speed=2)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self._browser_widget._options_menu._get_menu_item_text(), "Download Current Collection")

        self._browser_widget._options_menu._on_refresh_collection()

        self.assertListEqual(self._browser_widget.detail_selection, [])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        # Select a Detail Item
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(255, 140), human_delay_speed=2)
        # Rt-click to show context menu
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        self.assertGreater(len(self._browser_widget.detail_selection), 0)

        await self.finalize_test_no_image()

    async def test_9_thumbnail_size(self):
        start_pos = ui_test.Vec2(340, 580)
        end_pos = ui_test.Vec2(360, 580)
        # drag thumbnail slider bigger
        await ui_test.emulate_mouse_drag_and_drop(start_pos, end_pos, human_delay_speed=2)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_9_thumbnail_size.png")

    async def test_10_predownload(self):
        folder_name = "test_dir2"

        pdh = PredownloadHelper("test_dir")
        pdh.append_folder(folder_name)
        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(pdh.get_download_state(folder_name), "Done")
        self.assertIsNone(pdh.get_download_state("fake_folder"))
        pdh.destroy()

    async def test_11_add_remove_root_hierarchy(self):
        folder = self._browser_model.process_root_folder(f"test1/test2::{self._new_root_folder}", sync=False)
        self._browser_model.start_traverse(folder)
        await omni.kit.app.get_app().next_update_async()
        while not folder.prepared:
            await omni.kit.app.get_app().next_update_async()
        self._browser_widget.select_folder(folder, expand=True)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_11_add_root_hierarchy.png")
        self._browser_model.remove_root_folder(self._new_root_folder)
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test_no_image()

    def _copy_tree(self, src, dst):
        shutil.copytree(src, dst)
        os.chmod(dst, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
        for root, dirs, files in os.walk(dst):
            for dir in dirs:
                os.chmod(os.path.join(root, dir), stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
            for file in files:
                os.chmod(os.path.join(root, file), stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
