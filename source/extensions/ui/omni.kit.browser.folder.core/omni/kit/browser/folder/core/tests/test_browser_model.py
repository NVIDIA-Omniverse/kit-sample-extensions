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

import carb.settings
import omni.kit.test

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
from ..models import FolderCategoryItem, TreeFolderBrowserModel

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
ENV_ROOT_FOLDER = f"{TEST_DATA_PATH}/env_filter"
SETTING_ENV_ROOT = "/exts/omni.kit.browser.folder.core/test/env_root"
ROOT_FOLDER = f"{TEST_DATA_PATH}/test_root"
NEW_SUB_FOLDER = f"{ROOT_FOLDER}/new_sub"
NEW_ROOT_FOLDER = f"{TEST_DATA_PATH}/new_root"


# Having a test class derived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test
class TestTreeFolderBrowserModel(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        pass

    # After running each test
    async def tearDown(self):
        pass

    async def test_filter_folder(self):
        settings = carb.settings.get_settings()
        settings.set(SETTING_ENV_ROOT, [ENV_ROOT_FOLDER])
        browser_model = TreeFolderBrowserModel(
            setting_folders=SETTING_ENV_ROOT,
            ignore_folder_names=["*props*", "SubUSDs"],
        )
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        folder = browser_model.get_root_folder(ENV_ROOT_FOLDER)
        await folder.start_traverse()
        collection_items = browser_model.get_item_children(None)
        category_items = browser_model.get_item_children(collection_items[0])
        detail_items = browser_model.get_item_children(category_items[0])
        self.assertEqual(len(detail_items), 1)
        self.assertEqual(detail_items[0].name, "b.usd")

        browser_model.destroy()
        browser_model = None

    async def test_refresh_category_only(self):
        """Test traverse folder without changes, only refresh category item to change load status"""
        settings = carb.settings.get_settings()
        setting_folders = "/persistent/exts/omni.kit.browser.folder.core.test/tree_folders"
        settings.set(setting_folders, [ROOT_FOLDER, NEW_ROOT_FOLDER])
        setting_folders_hide_in_category = "/exts/omni.kit.browser.folder.core/tree_folders_hide_in_category"
        settings.set(setting_folders_hide_in_category, ["new_root"])

        model = TreeFolderBrowserModel(
            setting_folders=setting_folders,
            setting_folders_hide_in_category=setting_folders_hide_in_category,
        )

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        first_folder = model.get_root_folder(ROOT_FOLDER)
        model.start_traverse(first_folder)
        second_folder = model.get_root_folder(NEW_ROOT_FOLDER)
        model.start_traverse(second_folder)
        while not first_folder.prepared or not second_folder.prepared:
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        # Generate category items
        collection_items = model.get_item_children(None)
        model.get_item_children(collection_items[0])

        changed_items = []
        # Total 9 _item_changed events to traverse first folder again
        # 1. set category item loading=True (test_root)
        # 2. start traversing test_root (test_root)
        # 3. sub folders found in test_root (test_root)
        # 4. start traversing icons (icons)
        # 5. traverse icons completed (icons)
        # 6. start traversing txts (txts)
        # 7. traverse txts completed (txts)
        # 8. traversing test_root completed (test_root)
        # 9. set category item loading=False (test_root)
        # test_root lost one notification when category rows stopped being rebuilt for refreshes
        # that change nothing. This traverse finds no changes, so the refresh of
        # test_root's own row while it was still loading left its count and children identical and
        # is no longer published - on a drive-sized tree that class of rebuild was 56% of them. The
        # transitions that matter are unchanged: every row still reports loading, then not.
        expected_changes = {
            "test_root": [True, True, False, False],
            "icons": [True, False],
            "txts": [True, False],
        }
        index_changes = {"test_root": 0, "icons": 0, "txts": 0}

        def __on_item_changed(m, item):
            self.assertTrue(item.name in expected_changes)
            index = index_changes[item.name]
            if isinstance(item, FolderCategoryItem):
                self.assertEqual(
                    item.loading,
                    expected_changes[item.name][index],
                    f"index: {index} loading status error: {item.loading} != {expected_changes[item.name][index]}",
                )
            index_changes[item.name] += 1
            changed_items.append(item)

        sub = model.subscribe_item_changed_fn(__on_item_changed)
        # Traverse again, only refresh category items twice for loading status changed
        await self._traverse_folder(model, first_folder)
        self.assertEqual(len(changed_items), 8)

        # Total 6 _item_changed events to traverse first folder again
        # 1. set category item loading=True (new_root)
        # 2. start traversing new_root (new_root)
        # 3. sub folders found in new_root (since hide root, should update collection item instead))
        # 4. start traversing new_folder (new_folder)
        # 5. traverse new_folder completed (new_folder)
        # 6. traversing new_root completed (TreeRoot)
        changed_items = []
        expected_changes = {
            "new_root": [True, True],
            "new_folder": [True, False],
            "TreeRoot": [],
        }
        index_changes = {"new_root": 0, "new_folder": 0, "TreeRoot": 0}
        # Traverse again, only refresh category items twice for loading status changed
        await self._traverse_folder(model, second_folder)
        self.assertEqual(len(changed_items), 6)

        sub = None
        model.destroy()

    async def test_custom_folder(self):
        settings = carb.settings.get_settings()
        setting_folders = "/persistent/exts/omni.kit.browser.folder.core.test/tree_folders"
        settings.set(setting_folders, [ROOT_FOLDER])
        setting_custom_folders = "/persistent/exts/omni.kit.browser.folder.core.test/custom_folders"
        settings.set(setting_custom_folders, [NEW_ROOT_FOLDER])

        model = TreeFolderBrowserModel(
            setting_folders=setting_folders,
            custom_folders_setting=setting_custom_folders,
        )

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        collection_items = model.get_item_children(None)
        category_items = model.get_item_children(collection_items[0])
        self.assertEqual(len(category_items), 3)
        self.assertEqual(category_items[1].name, "new_root")
        self.assertEqual(category_items[2].name, "test_root")

        # Add a new custom folder
        settings.set(setting_custom_folders, [NEW_ROOT_FOLDER, ENV_ROOT_FOLDER])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        category_items = model.get_item_children(collection_items[0])
        self.assertEqual(len(category_items), 4)
        self.assertEqual(category_items[1].name, "env_filter")
        self.assertEqual(category_items[2].name, "new_root")
        self.assertEqual(category_items[3].name, "test_root")

        # Remove a custom folder
        settings.set(setting_custom_folders, [ENV_ROOT_FOLDER])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        category_items = model.get_item_children(collection_items[0])
        self.assertEqual(len(category_items), 3)
        self.assertEqual(category_items[1].name, "env_filter")
        self.assertEqual(category_items[2].name, "test_root")

    async def _traverse_folder(self, model: TreeFolderBrowserModel, folder) -> None:
        model.start_traverse(folder, force=True)
        await omni.kit.app.get_app().next_update_async()
        while not folder.prepared:
            await omni.kit.app.get_app().next_update_async()
