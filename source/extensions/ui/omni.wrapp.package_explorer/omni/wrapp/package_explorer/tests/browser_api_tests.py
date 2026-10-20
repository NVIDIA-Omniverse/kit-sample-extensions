# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import json
import os
import pathlib
import tempfile
from typing import List, Optional

import omni.kit.test
import omni.kit.undo
import omni.ui as ui
import omni.usd
from omni.wrapp.package_explorer import (
    WrappAsset,
    WrappBrowserExtension,
    WrappBrowserModel,
    add_wrapp_asset_to_stage,
    find_assets,
    get_instance,
)
from pxr import Usd

TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")

REPO_CONFIG_JSON = {
    "asset_repos": [
        [
            "publish",
            TEST_DATA_DIR.joinpath("assets").joinpath("props").joinpath(".wrapp_publish").as_posix(),
            "./publish/",
        ],
        [
            "working",
            TEST_DATA_DIR.joinpath("assets").joinpath("props").joinpath(".wrapp_working").as_posix(),
            "./working/",
        ],
    ],
}

NEW_REPO_CONFIG_JSON = {
    "assets": {
        "publish": {
            "display_name": "PUBLISH_DISPLAY_NAME",
            "publish_uri": TEST_DATA_DIR.joinpath("assets").joinpath("props").joinpath(".wrapp_publish").as_posix(),
            "working_uri": TEST_DATA_DIR.joinpath("assets").joinpath("props").joinpath(".wrapp_working").as_posix(),
            "install_path": "./publish/",
        },
        "working": {
            "display_name": "WORKING_DISPLAY_NAME",
            "publish_uri": TEST_DATA_DIR.joinpath("assets").joinpath("props").joinpath(".wrapp_publish").as_posix(),
            "working_uri": TEST_DATA_DIR.joinpath("assets").joinpath("props").joinpath(".wrapp_working").as_posix(),
            "install_path": "./working/",
        },
    }
}


class BrowserApiTest(omni.kit.test.AsyncTestCase):
    async def setUp(self, config=REPO_CONFIG_JSON) -> None:
        super().setUp()
        ui.Workspace.show_window("Package Explorer")

        # Save the repo config to a temporary file. clean up at tearDown()
        self.temp_dir = tempfile.TemporaryDirectory()
        repo_config_file = os.path.join(self.temp_dir.name, ".wrapp_repo.config")
        with open(repo_config_file, "w") as f:
            json.dump(config, f)

        self._browser_model: WrappBrowserModel = WrappBrowserModel()
        self._browser_model.refresh_asset_folders(wrapp_repo_config=repo_config_file)
        self._explorer: Optional[WrappBrowserExtension] = get_instance()
        if self._explorer:
            # Set the browser model on the WrappBrowserExtension instance
            # so the WrappBrowserExtension.find_assets() API uses it.
            self._original_browser_model = self._explorer.browser_model
            self._explorer.window._browser_model = self._browser_model
        else:
            self._original_browser_model = None

    def tearDown(self) -> None:
        super().tearDown()
        self.temp_dir.cleanup()
        if self._original_browser_model and self._explorer:
            # Restore original browser model
            self._explorer.window._browser_model = self._original_browser_model
            self._explorer = None
        self._browser_model.destroy()

    ################################
    # Tests for the find_assets() API
    ################################
    async def test_filter_all_assets(self):
        """Test getting all assets through the WrappBrowserExtension.find_assets() API"""
        self.assertIsNotNone(self._explorer)
        assets: List[WrappAsset] = await find_assets()
        self.assertEqual(len(assets), 3)
        wrapp_assets: List[WrappAsset] = await find_assets(search_words=["sm_"])
        self.assertEqual(len(assets), len(wrapp_assets))
        packages_asset_count = 0
        # Verify the type and number of assets created
        for a in assets:
            self.assertIsNotNone(a)
            if isinstance(a, WrappAsset):
                packages_asset_count += 1
            else:
                self.fail("Unknown asset type")
        self.assertEqual(packages_asset_count, 3)

    async def test_filter_working_assets(self):
        """Test looking for working assets"""
        assets = await find_assets(search_words=["working"])
        self.assertEqual(len(assets), 1)

    async def test_filter_publish_assets(self):
        """Test looking for publish assets"""
        assets = await find_assets(search_words=["publish"])
        self.assertEqual(len(assets), 2)

    async def test_filter_partial_asset_tag_match(self):
        """Tests that search words are matched on partial asset tags"""
        assets = await find_assets(search_words=["work"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], WrappAsset)

    async def test_filter_partial_asset_name_match(self):
        """Test that search words are matched on partial asset names"""
        assets = await find_assets(search_words=["box"])
        self.assertEqual(len(assets), 2)
        self.assertIsInstance(assets[0], WrappAsset)
        self.assertIsInstance(assets[1], WrappAsset)

    async def test_filter_case_insensitive_match(self):
        """Test that search words are case insensitive"""
        assets = await find_assets(search_words=["PubLiSh"])
        self.assertEqual(len(assets), 2)
        self.assertIsInstance(assets[0], WrappAsset)
        self.assertIsInstance(assets[1], WrappAsset)

    async def test_filter_no_assets(self):
        """Test search that should return no assets"""
        assets = await find_assets(search_words=["this_tag_is_not_used", "neither_is_this_one"])
        self.assertEqual(len(assets), 0)

    ###########################################
    # Tests for the add_wrapp_asset_to_stage() API
    ###########################################
    async def test_add_wrapp_asset_to_stage(self):
        """Test adding a wrapp asset to a stage"""
        assets = await find_assets(search_words=["crate"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], WrappAsset)

        # No undo needed in a unit test
        omni.kit.undo.begin_disabled()

        # Create a test stage with a default prim called "World"
        usd_context: omni.usd.UsdContext = omni.usd.get_context()
        usd_context.new_stage()
        stage: Usd.Stage = usd_context.get_stage()
        self.assertIsNotNone(stage)
        omni.kit.commands.execute("CreatePrim", prim_type="XForm", prim_path="/World", create_default_xform=True)
        world: Usd.Prim = stage.GetPrimAtPath("/World")
        stage.SetDefaultPrim(world)
        _, crate = omni.kit.commands.execute("CreatePrim", prim_type="XForm", prim_path="/World/crate")
        crate: Usd.Prim = stage.GetPrimAtPath("/World/crate")
        self.assertIsNotNone(crate)
        with tempfile.TemporaryDirectory() as temp_dir:
            packages_dir = os.path.join(temp_dir, ".packages")
            os.makedirs(packages_dir)  # Creates the subdirectory
            temp_stage_path = os.path.join(temp_dir, "test.usd")
            stage.GetRootLayer().identifier = temp_stage_path
            # Save the stage to the temporary directory so wrapp can install the asset properly with dependency tracking
            stage.GetRootLayer().Save()
            asset = assets[0]
            # Add the asset to the stage, under a specific prim
            asset_prim_path = await add_wrapp_asset_to_stage(stage, asset, "/World/crate", False)
            # Verify that the asset was added to the stage as expected
            prim: Usd.Prim = stage.GetPrimAtPath(asset_prim_path)
            self.assertIsNotNone(prim)
            self.assertEqual(prim.GetParent(), crate)

            # Test asset installed
            asset_filename = os.path.basename(asset.url)
            installed_path = os.path.join(temp_dir, asset.relative_destination, asset_filename)
            self.assertTrue(
                os.path.exists(installed_path),
                f"Expected installed asset at {installed_path}",
            )

            # Test reference updated
            # Retrieve the prim's composition stack
            prim_stack = prim.GetPrimStack()

            # Iterate over each PrimSpec in the stack
            for prim_spec in prim_stack:
                # Check if the PrimSpec has a reference list
                if prim_spec.referenceList:
                    # Iterate over each reference in the list
                    for reference in prim_spec.referenceList.GetAddedOrExplicitItems():
                        self.assertEqual(f"./working/{asset.name}/{asset.name}.usd", reference.assetPath)

            usd_context.close_stage()
            del stage
            omni.kit.undo.end_disabled()


class BrowserApiNewConfigTest(omni.kit.test.AsyncTestCase):
    async def setUp(self, config=NEW_REPO_CONFIG_JSON) -> None:
        super().setUp()
        ui.Workspace.show_window("Package Explorer")

        # Save the repo config to a temporary file. clean up at tearDown()
        self.temp_dir = tempfile.TemporaryDirectory()
        repo_config_file = os.path.join(self.temp_dir.name, ".wrapp_repo.config")
        with open(repo_config_file, "w") as f:
            json.dump(config, f)

        self._browser_model: WrappBrowserModel = WrappBrowserModel()
        self._browser_model.refresh_asset_folders(wrapp_repo_config=repo_config_file)
        self._explorer: Optional[WrappBrowserExtension] = get_instance()
        if self._explorer:
            # Set the browser model on the WrappBrowserExtension instance
            # so the WrappBrowserExtension.find_assets() API uses it.
            self._original_browser_model = self._explorer.browser_model
            self._explorer.window._browser_model = self._browser_model
        else:
            self._original_browser_model = None

    def tearDown(self) -> None:
        super().tearDown()
        self.temp_dir.cleanup()
        if self._original_browser_model and self._explorer:
            # Restore original browser model
            self._explorer.window._browser_model = self._original_browser_model
            self._explorer = None
        self._browser_model.destroy()

    ################################
    # Tests for the find_assets() API
    ################################
    async def test_filter_all_assets(self):
        """Test getting all assets through the WrappBrowserExtension.find_assets() API"""
        self.assertIsNotNone(self._explorer)
        assets: List[WrappAsset] = await find_assets()
        self.assertEqual(len(assets), 4)
        wrapp_assets: List[WrappAsset] = await find_assets(search_words=["sm_"])
        self.assertEqual(len(assets), len(wrapp_assets))
        packages_asset_count = 0
        # Verify the type and number of assets created
        for a in assets:
            self.assertIsNotNone(a)
            if isinstance(a, WrappAsset):
                packages_asset_count += 1
            else:
                self.fail("Unknown asset type")
        self.assertEqual(packages_asset_count, 4)

    async def test_filter_working_assets(self):
        """Test looking for working assets"""
        assets = await find_assets()
        working_assets = list(filter(lambda asset: asset.hierarchy.startswith("WORKING_DISPLAY_NAME"), assets))
        self.assertEqual(len(list(working_assets)), 2)

    async def test_filter_publish_assets(self):
        """Test looking for publish assets"""
        assets = await find_assets()
        publish_assets = list(filter(lambda asset: asset.hierarchy.startswith("PUBLISH_DISPLAY_NAME"), assets))
        self.assertEqual(len(publish_assets), 2)

    async def test_filter_partial_asset_tag_match(self):
        """Tests that search words are matched on partial asset tags"""
        assets = await find_assets()
        display_name_assets = list(filter(lambda asset: "DISPLAY_NAME" in asset.hierarchy, assets))
        self.assertEqual(len(display_name_assets), 4)
        self.assertIsInstance(assets[0], WrappAsset)
