# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import os
import pathlib
import shutil
from tempfile import mkdtemp
from typing import Dict, List, Optional

import carb.settings
import omni.kit.test
import omni.kit.undo
import omni.ui as ui
import omni.usd
from omni.simready.explorer import (
    AssetFactory,
    AssetType,
    PropAsset,
    SimreadyAsset,
    SimReadyBrowserExtension,
    SimReadyBrowserModel,
    add_asset_to_stage,
    add_asset_to_stage_using_prims,
    find_assets,
    get_average_position_of_prims,
    get_instance,
    refresh_browser,
)
from omni.simready.explorer.actions import find_inst_prim, is_physics_variant_enabled
from pxr import Gf, Sdf, Usd

TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")


# Declare and register new asset types
@AssetFactory.register(AssetType.GENERIC)
class GenericTestAsset(SimreadyAsset):
    def __init__(self, raw_asset_data: Dict):
        super().__init__(raw_asset_data)
        self._type = AssetType.GENERIC

    @classmethod
    def is_asset_data(cls, raw_asset_data: Dict) -> bool:
        asset_type: str = raw_asset_data.get("Asset Type", AssetType.UNKNOWN.name)
        return asset_type.upper() == AssetType.GENERIC.name


@AssetFactory.register(AssetType.VEHICLE)
class VehicleTestAsset(SimreadyAsset):
    def __init__(self, raw_asset_data: Dict):
        super().__init__(raw_asset_data)
        self._type = AssetType.VEHICLE

    @classmethod
    def is_asset_data(cls, raw_asset_data: Dict) -> bool:
        asset_type: str = raw_asset_data.get("Asset Type", AssetType.UNKNOWN.name)
        return asset_type.upper() == AssetType.VEHICLE.name


class BrowserApiTest(omni.kit.test.AsyncTestCase):
    async def setUp(self) -> None:
        super().setUp()
        # Create a browser model with the test data directory as the only folder
        # class FolderBrowserModel insists on prefixing the setting_folders with "persistent"
        settings_asset_folder_roots = "/persistent/exts/omni.simready.explorer.tests/folders"
        carb.settings.get_settings().set(settings_asset_folder_roots, [str(TEST_DATA_DIR)])
        ui.Workspace.show_window("SimReady Explorer")
        await omni.kit.app.get_app().next_update_async()

        self._browser_model: SimReadyBrowserModel = SimReadyBrowserModel(setting_folders=settings_asset_folder_roots)
        self._browser_model.folder_changed(None)
        self._explorer: Optional[SimReadyBrowserExtension] = get_instance()
        if self._explorer:
            # Set the browser model on the SimReadyBrowserExtension instance
            # so the SimReadyBrowserExtension.find_assets() API uses it.
            self._original_browser_model = self._explorer.browser_model
            self._explorer.window._browser_model = self._browser_model
        else:
            self._original_browser_model = None

    def tearDown(self) -> None:
        super().tearDown()
        if self._original_browser_model and self._explorer:
            # Restore original browser model
            self._explorer.window._browser_model = self._original_browser_model
            self._explorer = None
        self._browser_model.destroy()

    ################################
    # Tests for the find_assets() API
    ################################
    async def test_filter_all_assets(self):
        """Test getting all assets through the SimReadyBrowserExtension.find_assets() API"""
        self.assertIsNotNone(self._explorer)
        assets: List[SimreadyAsset] = await find_assets()
        self.assertEqual(len(assets), 6)
        simready_assets: List[SimreadyAsset] = await find_assets(search_words=["SimReady"])
        self.assertEqual(len(assets), len(simready_assets))
        generic_asset_count = 0
        vehicle_asset_count = 0
        prop_asset_count = 0
        # Verify the type and number of assets created
        for a in assets:
            self.assertIsNotNone(a)
            if isinstance(a, GenericTestAsset):
                generic_asset_count += 1
            elif isinstance(a, VehicleTestAsset):
                vehicle_asset_count += 1
            elif isinstance(a, PropAsset):
                # PropAsset is a type defined in the SimReady Explorer extension;
                # the test data contains PropAssets, so we can verify that they work
                prop_asset_count += 1
            else:
                self.fail("Unknown asset type")
        self.assertEqual(prop_asset_count, 3)
        self.assertEqual(vehicle_asset_count, 2)
        self.assertEqual(generic_asset_count, 1)

    async def test_filter_tool_assets(self):
        """Test looking for tools"""
        assets = await find_assets(search_words=["tool"])
        self.assertEqual(len(assets), 2)

    async def test_filter_vehicles_assets(self):
        """Test looking for vehicles"""
        assets = await find_assets(search_words=["truck"])
        self.assertEqual(len(assets), 2)
        for a in assets:
            self.assertIsInstance(a, VehicleTestAsset)
        # Test looking for vehicles differently
        assets = await find_assets(search_words=["truck", "vehicle"])
        self.assertEqual(len(assets), 2)
        for a in assets:
            self.assertIsInstance(a, VehicleTestAsset)

    async def test_filter_partial_asset_tag_match(self):
        """Tests that search words are matched on partial asset tags"""
        assets = await find_assets(search_words=["ti-tool"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], GenericTestAsset)
        # Test looking for vehicles differently
        assets = await find_assets(search_words=["motor", "vehicle"])
        self.assertEqual(len(assets), 2)
        for a in assets:
            self.assertIsInstance(a, VehicleTestAsset)

    async def test_filter_partial_asset_name_match(self):
        """Test that search words are matched on partial asset names"""
        assets = await find_assets(search_words=["tool1"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], GenericTestAsset)

    async def test_filter_case_insensitive_match(self):
        """Test that search words are case insensitive"""
        assets = await find_assets(search_words=["ToOl1"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], GenericTestAsset)
        assets = await find_assets(search_words=["PORT Unit"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], PropAsset)

    async def test_filter_no_assets(self):
        """Test search that should return no assets"""
        assets = await find_assets(search_words=["equipment", "vehicle"])
        self.assertEqual(len(assets), 0)
        # Test a filter that contains tags not in the database
        assets = await find_assets(search_words=["this_tag_is_not_used", "neither_is_this_one"])
        self.assertEqual(len(assets), 0)

    #################################################
    # Tests for accessing behavior list of assets API
    #################################################
    async def test_asset_behavior(self):
        """Test getting the behaviors of an asset"""
        assets = await find_assets(search_words=["multi-tool"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], GenericTestAsset)
        # omni.kit.debug.python.wait_for_client()
        self.assertEqual(len(assets[0].behaviors), 2)
        self.assertTrue("Features" in assets[0].behaviors)
        self.assertEqual(assets[0].behaviors["Features"], ["Five", "Seven", "Nine"])
        self.assertTrue("Colors" in assets[0].behaviors)
        self.assertEqual(assets[0].behaviors["Colors"], ["Black", "Red", "Blue"])

    ###########################################
    # Tests for the def add_asset_to_stage() API
    ###########################################

    def check_variant(self, prim: Usd.Prim, variantset_name: str, variant_name: str) -> None:
        """Helper function to check the variant value of a prim"""
        self.assertIsNotNone(prim)
        vsets: Usd.VariantSet = prim.GetVariantSets()
        vset: Usd.VariantSet = vsets.GetVariantSet(variantset_name)
        self.assertIsNotNone(vset)
        self.assertEqual(vset.GetVariantSelection(), variant_name)

    def check_instanceable(self, prim: Usd.Prim, variants: Dict[str, str]) -> None:
        """Helper function to check the instanceable value of the 'inst' prim"""
        self.assertIsNotNone(prim)
        inst_prim: Usd.Prim = find_inst_prim(prim)
        self.assertIsNotNone(inst_prim)
        self.assertTrue(inst_prim.IsInstanceable())

    def check_added_asset(self, stage: Usd.Stage, asset_prim_path: str, parent_prim: Usd.Prim):
        """Helper function to check that an asset was added to a stage"""
        self.assertIsNotNone(stage)
        self.assertIsNotNone(parent_prim)
        self.assertTrue(asset_prim_path)
        prim: Usd.Prim = stage.GetPrimAtPath(asset_prim_path)
        self.assertIsNotNone(prim)
        self.assertEqual(prim.GetParent(), parent_prim)

    async def test_add_asset_to_stage(self):
        """Test adding an asset to a stage and setting its variant value"""
        assets = await find_assets(search_words=["box_a01"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], PropAsset)

        # No undo needed in a unit test
        omni.kit.undo.begin_disabled()

        # Create a test stage with a default prim called "World"
        usd_context: omni.usd.UsdContext = omni.usd.get_context()
        usd_context.new_stage()
        stage: Usd.Stage = usd_context.get_stage()
        self.assertIsNotNone(stage)
        omni.kit.commands.execute("CreatePrim", prim_type="XFom", prim_path="/World", create_default_xform=True)
        world: Usd.Prim = stage.GetPrimAtPath("/World")
        stage.SetDefaultPrim(world)
        res, cube = omni.kit.commands.execute("CreatePrim", prim_type="Cube", prim_path="/World/Cube")
        cube: Usd.Prim = stage.GetPrimAtPath("/World/Cube")
        self.assertIsNotNone(cube)

        # Create the variant to set on the asset when adding it to the stage
        variantset_name = "PhysicsVariant"
        self.assertTrue(variantset_name in assets[0].behaviors)
        variants: Dict[str, str] = {variantset_name: assets[0].behaviors[variantset_name][0]}

        # Add the asset to the stage, under a specific prim
        res, asset_prim_path = add_asset_to_stage(assets[0].url, parent_path=Sdf.Path("/World/Cube"), variants=variants)
        self.assertTrue(res)

        # Verify that the asset was added to the stage as expected
        self.check_added_asset(stage, asset_prim_path, cube)

        # Check that the asset has the correct variant set
        self.check_variant(
            stage.GetPrimAtPath(asset_prim_path), variantset_name, assets[0].behaviors[variantset_name][0]
        )

        # Check that the asset has the correct instanceable attribute set
        self.check_instanceable(stage.GetPrimAtPath(asset_prim_path), variants)

        usd_context.close_stage()
        omni.kit.undo.end_disabled()

    async def test_add_asset_to_stage_using_prims(self):
        """Test adding an asset to a stage using some existent prims, and setting its variant value"""
        assets = await find_assets(search_words=["box_a01"])
        self.assertEqual(len(assets), 1)
        self.assertIsInstance(assets[0], PropAsset)

        # No undo needed in a unit test
        omni.kit.undo.begin_disabled()

        # Create a test stage with a default prim called "World" and some cubes
        usd_context: omni.usd.UsdContext = omni.usd.get_context()
        usd_context.new_stage()
        stage: Usd.Stage = usd_context.get_stage()
        self.assertIsNotNone(stage)
        omni.kit.commands.execute("CreatePrim", prim_type="XFom", prim_path="/World", create_default_xform=True)
        world: Usd.Prim = stage.GetPrimAtPath("/World")
        stage.SetDefaultPrim(world)
        prim_paths: List[Sdf.Path] = []
        for i in range(3):
            prim_path: str = f"/World/Cube{i}"
            prim_paths.append(Sdf.Path(prim_path))
            omni.kit.commands.execute("CreatePrim", prim_type="Cube", prim_path=prim_path)
            omni.kit.commands.execute("TransformPrimSRTCommand", path=prim_path, new_translation=Gf.Vec3d(0, 0, i * 20))

        # Create the variant to set on the asset when adding it to the stage
        variantset_name = "PhysicsVariant"
        self.assertTrue(variantset_name in assets[0].behaviors)
        variants: Dict[str, str] = {variantset_name: assets[0].behaviors[variantset_name][0]}

        # Add the asset to the stage, using the prims created above, without replacing them
        res, asset_prim_path = add_asset_to_stage_using_prims(
            usd_context, stage, assets[0].url, variants=variants, replace_prims=False, prim_paths=prim_paths
        )
        self.assertTrue(res)

        # Verify that the asset was added to the stage as expected
        self.check_added_asset(stage, asset_prim_path, world)

        # Check that the asset has the correct variant set
        self.check_variant(
            stage.GetPrimAtPath(asset_prim_path), variantset_name, assets[0].behaviors[variantset_name][0]
        )

        # Check that the asset has the correct instanceable attribute set
        self.check_instanceable(stage.GetPrimAtPath(asset_prim_path), variants)

        # Verify that the cubes were not replaced
        for i in range(3):
            prim_path: str = f"/World/Cube{i}"
            prim: Usd.Prim = stage.GetPrimAtPath(prim_path)
            self.assertIsNotNone(prim)
            self.assertTrue(prim.IsValid())
            self.assertEqual(prim.GetTypeName(), "Cube")
            self.assertEqual(prim.GetParent(), world)
            self.assertEqual(prim.GetAttribute("xformOp:translate").Get(), Gf.Vec3d(0, 0, i * 20))

        # Verify that the newly added asset is at the correct position
        position: Gf.Vec3d = get_average_position_of_prims([stage.GetPrimAtPath(path) for path in prim_paths])
        self.assertEqual(stage.GetPrimAtPath(asset_prim_path).GetAttribute("xformOp:translate").Get(), position)

        # Add the asset to the stage, using the prims created above, replacing them
        res, asset_prim_path = add_asset_to_stage_using_prims(
            usd_context, stage, assets[0].url, variants=variants, replace_prims=True, prim_paths=prim_paths
        )

        # Verify that the asset was added to the stage as expected
        self.assertTrue(res)
        self.check_added_asset(stage, asset_prim_path, world)

        # Check that the asset has the correct variant set
        self.check_variant(
            stage.GetPrimAtPath(asset_prim_path), variantset_name, assets[0].behaviors[variantset_name][0]
        )

        # Check that the asset has the correct instanceable attribute set
        self.check_instanceable(stage.GetPrimAtPath(asset_prim_path), variants)

        # Verify that the newly added asset's position is the average of the replaced cubes
        self.assertEqual(stage.GetPrimAtPath(asset_prim_path).GetAttribute("xformOp:translate").Get(), position)

        # Verify that the cubes are not in the stage
        for i in range(3):
            self.assertFalse(stage.GetPrimAtPath(f"/World/Cube{i}").IsValid())

        usd_context.close_stage()
        omni.kit.undo.end_disabled()

    ################################
    # Tests for refresh_browser() API
    ################################
    async def test_refresh_browser(self):
        """Tests that refreshing the browser pulls in updated asset info, but not more."""

        # Use temp directory for DGXC test
        test_temp = mkdtemp(dir=omni.kit.test.get_test_output_path())
        test_root = test_temp + "/data"
        shutil.copytree(str(TEST_DATA_DIR), test_root)
        settings_asset_folder_roots = "/persistent/exts/omni.simready.explorer.tests/new_folders"
        carb.settings.get_settings().set(settings_asset_folder_roots, [test_root])

        new_browser_model: SimReadyBrowserModel = SimReadyBrowserModel(setting_folders=settings_asset_folder_roots)
        explorer: Optional[SimReadyBrowserExtension] = get_instance()
        if explorer:
            # Set the browser model on the SimReadyBrowserExtension instance
            # so the SimReadyBrowserExtension.find_assets() API uses it.
            original_browser_model = explorer.browser_model
            explorer.window._browser_model = new_browser_model
        else:
            original_browser_model = None

        # Refershing the browser should not add any new assets if the asset database was not changed
        old_assets: List[SimreadyAsset] = await find_assets()
        old_asset_count = len(old_assets)
        refresh_browser()
        # Wait for new assets loaded
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        new_asset_count = len(await find_assets())
        self.assertEqual(old_asset_count, new_asset_count)

        # Refreshing the browser should pull in new data if the asset database was changed
        # Make the modified asset database the current one
        TEST_ASSETS_FILE = test_root + "/asset_info.json"
        BACKUP_TEST_ASSETS_FILE = test_root + "/asset_info.backup"
        os.rename(TEST_ASSETS_FILE, BACKUP_TEST_ASSETS_FILE)
        MODIFIED_TEST_ASSETS_FILE = test_root + "/asset_info_modified.json"
        os.rename(MODIFIED_TEST_ASSETS_FILE, TEST_ASSETS_FILE)

        refresh_browser()
        # Wait for new assets loaded
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        modified_assets: List[SimreadyAsset] = await find_assets()

        try:
            self.assertEqual(len(modified_assets), 3)
            # Check that the modified assets are in the list of assets
            self.assertTrue("modified" in modified_assets[0].tags)
            self.assertTrue("modified" in modified_assets[0].labels_as_str)
            self.assertTrue("modified" in modified_assets[0].name)
            # Check that new assets are in the list of assets
            self.assertTrue(modified_assets[2] not in old_assets)
            # Check that removed assets are not in the list of assets
            self.assertTrue(old_assets[1] not in modified_assets)
        finally:
            if explorer:
                explorer.window._browser_model = original_browser_model
            shutil.rmtree(test_temp)
