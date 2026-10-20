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
from unittest.mock import MagicMock

import omni.kit.app
from omni.kit.browser.core import TreeCategoryDelegate
from omni.kit.browser.folder.core import (
    FolderBrowserModel,
    FolderBrowserWidget,
    TreeFolderBrowserModel,
    TreeFolderBrowserWidget,
)
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestFolderBrowserWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._browser_model = FolderBrowserModel()
        self._browser_widget = None

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        if self._browser_widget:
            self._browser_widget.destroy()
        if self._browser_model:
            self._browser_model.destroy()

    async def test_general(self):
        """Testing general look of FolderBrowserWidget"""
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = FolderBrowserWidget(self._browser_model)

        await omni.kit.app.get_app().next_update_async()
        # Wait for icons loaded
        await asyncio.sleep(5)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="general.png")

    async def test_root(self):
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = FolderBrowserWidget(self._browser_model)
        # Testing with folder name using a trailing slash, as it should work either way
        result = self._browser_model.append_root_folder(f"{TEST_DATA_PATH}/test_root/", save=False)
        self.assertIsNotNone(result)
        self._browser_model.folder_changed(None)
        self._browser_widget._browser_widget.collection_index = -1
        self._browser_widget._browser_widget.collection_index = 0

        # Wait for folder items loaded
        for _ in range(100):
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="root.png")

    async def test_local_cache(self):
        # there is json file on the disk which has
        # asset_json["root"]["sub_folders"]["icons"]["files"]["icon.png"]["url"] = "error.png"

        local_cache_file_path = str(TEST_DATA_PATH.absolute().joinpath("test.json").absolute())
        self._browser_model = FolderBrowserModel(local_cache_file=local_cache_file_path)
        root_folder = self._browser_model.append_root_folder(f"{TEST_DATA_PATH}/test_root", save=False)
        self.assertIsNotNone(root_folder)
        self.assertEqual(root_folder.name, "test_root")
        await root_folder.start_traverse()

        # check the json file data
        import json

        with open(local_cache_file_path, "r") as json_file:
            asset_json = json.load(json_file)
            for item in asset_json:
                self.assertTrue("sub_folders" in asset_json[item])
                data = asset_json[item]["sub_folders"]
                self.assertTrue("icons" in data)
                self.assertTrue("files" in data["icons"])
                # when we load the file, we updated the error.png to icon.png
                self.assertEqual(data["icons"]["files"]["icon.png"]["url"], "icon.png")

        # modify the json file data back
        asset_json["root"]["sub_folders"]["icons"]["files"]["icon.png"]["url"] = "error.png"
        with open(local_cache_file_path, "w") as json_file:
            json.dump(asset_json, json_file, indent=4)
            if json_file:
                json_file.close()

    async def test_add_remove_collection(self):
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = FolderBrowserWidget(self._browser_model)

        # Add a folder procedurally
        self._browser_widget._on_folder_picked(f"{self._golden_img_dir}/")
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self._browser_widget._browser_widget.collection_index, 0)
        # Add another one
        self._browser_widget._on_folder_picked(f"{TEST_DATA_PATH}/")
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        # Create a mock for self._browser_model.remove_root_folder, so we don't have to actually remove anything
        mock_remove_folder = MagicMock()
        mock_remove_folder.return_value = False
        # Replace the actual self._browser_model.remove_root_folder with the mock
        self._browser_model.remove_root_folder = mock_remove_folder

        self._browser_widget._on_remove_collection()
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self._browser_widget._browser_widget.collection_index, 1)

        await self.finalize_test_no_image()

        mock_remove_folder.reset_mock()

    async def test_filter_files(self):
        self._browser_model._filter_file_suffixes = [".usd", ".usda"]
        self.assertTrue(self._browser_model.filter_file("test.usda"))
        self.assertFalse(self._browser_model.filter_file("test.png"))
        self._browser_model._filter_file_suffixes = None
