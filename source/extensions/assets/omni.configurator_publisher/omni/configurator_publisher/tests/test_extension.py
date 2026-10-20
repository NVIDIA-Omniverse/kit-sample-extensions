# SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import carb
import omni.client.utils as clientutils
import omni.kit.test
import omni.kit.ui_test
import omni.ui
import omni.usd
from carb.input import KeyboardInput
from omni.kit.test.teamcity import is_running_in_teamcity
from pxr import Sdf, Usd, UsdGeom

from ..asset_publish_options import AssetPublishOptions
from ..enums import CollectorSwitches, Phases
from ..package_utils import (
    EXTENSION_DIR,
    OPTIMIZER_MAX_ERROR_DEFAULT,
    SETTINGS_LAST_PACKAGE_DIR,
    UJITSO_CACHE_FOLDER_NAME,
)
from ..process_utils import run_kit

# from ..extension import wait_process_completed
from ..test_helper import PublisherTestHelper

MAX_CACHE_SIZE_DIFF = 1 << 20


def dump_prims(stage):
    return set([p.GetName() for p in stage.Traverse()])


async def clear_and_input(widget, input_str=""):
    widget.widget.focus_keyboard()
    await omni.kit.ui_test.emulate_keyboard_press(KeyboardInput.DEL, human_delay_speed=30)
    if input_str:
        await widget.input(input_str)


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test
class Test(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        widget_ref = omni.kit.ui_test.find("Configurator Publisher")
        publisher_window = widget_ref.window
        if not publisher_window.visible:
            await omni.kit.ui_test.menu_click("Tools/Product Configurator/Configurator Publisher")
            # TODO: avoid accessing private functions/variables
            publisher_window._phase_settings_ui()
            publisher_window._phase_settings_window.visible = True
            publisher_window._collector_settings_ui()
            publisher_window._collector_settings_window.visible = True
            publisher_window._validator_settings_ui()
            publisher_window._validator_settings_window.visible = True

        self._use_current_stage_button = omni.kit.ui_test.find(
            "Configurator Publisher//Frame/**/Button[*].text=='Set From Current Stage'"
        )
        string_fields = omni.kit.ui_test.find_all("Configurator Publisher//Frame/**/StringField[*]")
        self._temp_dir_field = string_fields[1]
        self._max_mean_error_field = string_fields[2]
        self._optimizer_config_field = string_fields[3]
        self._kit_app_path_field = string_fields[4]
        self._zip_name_field = string_fields[5]
        self._process_button = omni.kit.ui_test.find("Configurator Publisher//Frame/**/Button[*].text=='Run Process'")

        check_boxes = omni.kit.ui_test.find_all("Phase Settings//Frame/**/CheckBox[*]")
        self._collect_check_box = check_boxes[0]
        self._validate_check_box = check_boxes[1]
        self._optimize_check_box = check_boxes[2]
        self._cache_check_box = check_boxes[3]
        self._package_check_box = check_boxes[4]

        check_boxes = omni.kit.ui_test.find_all("Collector Settings//Frame/**/CheckBox[*]")
        self._ascii_to_binary_check_box = check_boxes[0]
        self._default_prim_check_box = check_boxes[1]
        self._flatten_check_box = check_boxes[2]

        self.settings = carb.settings.get_settings()
        self._usd_filepath = ""
        self._asset_temp_folder = ""

        self.__reset_collector_settings()

        self.__test_helper = PublisherTestHelper()

    # After running each test
    async def tearDown(self):
        pass

    def __reset_phase_settings(self):
        for phase in Phases:
            key = f"persistent/configurator_publisher/{phase.value}"
            self.settings.set(key, False)

    def __reset_collector_settings(self):
        self.settings.set("persistent/configurator_publisher/collector/ascii_to_binary", True)
        self.settings.set("persistent/configurator_publisher/collector/default_prim_only", False)
        self.settings.set("persistent/configurator_publisher/collector/flat_collection", False)

    async def __start_processing(self):
        await self._process_button.click()
        await self.__test_helper.wait_process_complete()

    async def __create_stage(self, temp_folder):
        def create_reference_usd(filename):
            sub_folder = os.path.join(temp_folder, filename)
            usd_filepath = os.path.join(sub_folder, f"{filename}.usda")
            os.mkdir(sub_folder)
            stage = Usd.Stage.CreateNew(usd_filepath)
            xform_1 = stage.DefinePrim(f"/{filename}", "Xform")
            cube_prim = UsdGeom.Cube.Define(stage, f"/{filename}/{filename}_cube")
            stage.SetDefaultPrim(xform_1)
            stage.Save()
            return sub_folder, usd_filepath

        sub_folder_1, usd_filepath_1 = create_reference_usd("ref_1")
        sub_folder_2, usd_filepath_2 = create_reference_usd("ref_2")
        self._usd_filepath = os.path.join(temp_folder, "publish_test.usda")
        stage = Usd.Stage.CreateNew(self._usd_filepath)
        xform_1 = stage.DefinePrim("/Xform_1", "Xform")
        xform_2 = stage.DefinePrim("/Xform_2", "Xform")
        xform_3 = stage.DefinePrim("/Xform_3", "Xform")
        xform_4 = stage.DefinePrim("/Xform_4", "Xform")
        xform_5 = stage.DefinePrim("/Xform_5", "Xform")
        cube_prim = UsdGeom.Cube.Define(stage, "/Xform_1/test_cube")
        cylinder_prim = UsdGeom.Cylinder.Define(stage, "/Xform_2/test_cylinder")
        sphere_prim = UsdGeom.Sphere.Define(stage, "/Xform_3/test_sphere")
        xform_4.GetReferences().AddReference(usd_filepath_1, Sdf.Path.emptyPath)
        xform_5.GetReferences().AddReference(usd_filepath_2, Sdf.Path.emptyPath)
        stage.SetDefaultPrim(xform_1)
        stage.Save()

        await omni.usd.get_context().open_stage_async(self._usd_filepath)
        await self._use_current_stage_button.click()
        # create temporarry folder for asset packaging
        self._asset_temp_folder = os.path.join(temp_folder, "assets_temp")
        os.mkdir(self._asset_temp_folder)
        self.assertTrue(os.path.exists(self._asset_temp_folder))
        await clear_and_input(self._temp_dir_field, self._asset_temp_folder)
        await clear_and_input(self._max_mean_error_field, str(OPTIMIZER_MAX_ERROR_DEFAULT))
        await clear_and_input(self._optimizer_config_field)
        await clear_and_input(self._zip_name_field, "test_base")

    async def __start_collecting(self):
        self.__reset_phase_settings()
        self.settings.set("persistent/configurator_publisher/collect", True)
        await self.__start_processing()

    async def __start_validating(self):
        self.__reset_phase_settings()
        await self._validate_check_box.click()
        await self.__start_processing()

    async def __start_optimization(self):
        self.__reset_phase_settings()
        await self._optimize_check_box.click()
        await self.__start_processing()

    async def __start_generating_cache(self):
        self.__reset_phase_settings()

        kit_app_path = EXTENSION_DIR.parent.parent
        if os.name == "nt":
            kit_app_path /= "omni.app.configurator_publisher.bat"
        else:
            kit_app_path /= "omni.app.configurator_publisher.sh"
        if not kit_app_path.exists():
            # raise FileNotFoundError(f"Cannot find {str(kit_app_path)}")
            return False

        await clear_and_input(self._kit_app_path_field, str(kit_app_path))
        await self._cache_check_box.click()
        await self.__start_processing()
        return True

    async def __start_packaging(self):
        self.__reset_phase_settings()
        await self._package_check_box.click()
        await self.__start_processing()

    async def __is_cache_healthy(self, package_folder, cache_folder, usd_filename):
        def caculate_size(input_folder):
            total_size = 0
            for folder_path, _, filenames in os.walk(input_folder):
                for f in filenames:
                    file_path = os.path.join(folder_path, f)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
            return total_size

        def find_folder_for_file(root, filename):
            result = ""
            for folder_path, _, files in os.walk(root):
                for f in files:
                    if f == filename:
                        result = folder_path
                        break
                if result:
                    break
            return result

        # folder paths should not contain '0'~'9'
        digits = set([chr(x) for x in range(ord("0"), ord("9") + 1)])
        for folder_path, folders, files in os.walk(cache_folder):
            if len(set(folders).intersection(digits)) != 0:
                return False

        cache_size = caculate_size(cache_folder)
        with tempfile.TemporaryDirectory() as temp_folder:
            src_folder = find_folder_for_file(package_folder, usd_filename)
            if not src_folder:
                return False
            dest_folder = os.path.join(temp_folder, "cache_validation" + os.path.sep)
            shutil.copytree(src_folder, dest_folder)

            original_package_dir = self.settings.get(SETTINGS_LAST_PACKAGE_DIR)
            self.settings.set(SETTINGS_LAST_PACKAGE_DIR, dest_folder)

            await self.__start_generating_cache()

            self.settings.set(SETTINGS_LAST_PACKAGE_DIR, original_package_dir)
            cache_folder = self.__find_cache_folder(dest_folder)
            cache_size_2nd = caculate_size(cache_folder)

        delta_size = cache_size_2nd - cache_size
        if delta_size > MAX_CACHE_SIZE_DIFF:
            return False
        return True

    def __find_cache_folder(self, root_folder):
        cache_folder = ""
        for folder_path, folder_names, _ in os.walk(root_folder):
            for folder in folder_names:
                if folder == UJITSO_CACHE_FOLDER_NAME:
                    cache_folder = os.path.join(folder_path, folder)
                    break
            if cache_folder:
                break
        return cache_folder

    # @unittest.skipIf(is_running_in_teamcity(), "optimization fails on TeamCity for Windows, cache generation timeouts on TeamCity for Linux")
    # TODO: complete the unit test on TeamCity
    async def test_full_process(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            await self.__create_stage(temp_folder)

            await self.__start_collecting()

            # check: usd file only
            count = 0
            for folder_path, _, filenames in os.walk(self._asset_temp_folder):
                for f in filenames:
                    if os.path.splitext(f)[1].endswith(".usda"):
                        count += 1
            self.assertEqual(count, 0)

            # check: none-flat
            parent_folders = set()
            for folder_path, _, files in os.walk(self._asset_temp_folder):
                for f in files:
                    if "ref_" in f.lower():
                        parent_folders.add(os.path.split(folder_path)[-1])
            self.assertEqual(len(parent_folders), 2)

            # check: all prims
            new_usda_filepath = ""
            for folder_path, _, filenames in os.walk(self._asset_temp_folder):
                if new_usda_filepath:
                    break
                for f in filenames:
                    if os.path.splitext(f)[1].startswith(".usd"):
                        new_usda_filepath = os.path.join(folder_path, f)
                        break
            self.assertNotEqual(new_usda_filepath, "")
            await omni.usd.get_context().open_stage_async(new_usda_filepath)
            stage = omni.usd.get_context().get_stage()
            prim_names = set(
                [
                    "Xform_1",
                    "Xform_2",
                    "Xform_3",
                    "Xform_4",
                    "Xform_5",
                    "test_cube",
                    "test_sphere",
                    "test_cylinder",
                    "ref_1_cube",
                    "ref_2_cube",
                ]
            )
            self.assertEqual(dump_prims(stage), prim_names)
            await omni.usd.get_context().close_stage_async()

            await self.__start_validating()
            # TODO: verify the result of validation

            await self.__start_optimization()
            # TODO: verify the result of optimization

            success = await self.__start_generating_cache()
            if not success:
                return

            derived_cache_folder = self.__find_cache_folder(self._asset_temp_folder)
            self.assertNotEqual(derived_cache_folder, "")
            self.assertTrue(
                await self.__is_cache_healthy(
                    self._asset_temp_folder, derived_cache_folder, f"{AssetPublishOptions.DEFAULT_ASSET_NAME}.usd"
                )
            )

            await self.__start_packaging()

    async def test_ascii_format_collection(self):
        await self._ascii_to_binary_check_box.click()
        with tempfile.TemporaryDirectory() as temp_folder:
            await self.__create_stage(temp_folder)
            await self.__start_collecting()

            count = 0
            for folder_path, _, filenames in os.walk(self._asset_temp_folder):
                for f in filenames:
                    ext = os.path.splitext(f)[1]
                    if ext.endswith(".usd") or ext.endswith(".usdc"):
                        count += 1
            self.assertEqual(count, 0)

    async def test_flat_collection(self):
        self.settings.set(f"persistent/configurator_publisher/{CollectorSwitches.FLAT_COLLECTION.value}", True)
        with tempfile.TemporaryDirectory() as temp_folder:
            await self.__create_stage(temp_folder)
            await self.__start_collecting()

            parent_folders = set()
            for folder_path, _, files in os.walk(self._asset_temp_folder):
                for f in files:
                    if "ref_" in f.lower():
                        parent_folders.add(os.path.split(folder_path)[-1])
            self.assertEqual(len(parent_folders), 1)

    async def test_only_default_prim_collection(self):
        await self._default_prim_check_box.click()
        with tempfile.TemporaryDirectory() as temp_folder:
            await self.__create_stage(temp_folder)
            await self.__start_collecting()
            stage = omni.usd.get_context().get_stage()

            new_usda_filepath = ""
            for folder_path, _, filenames in os.walk(self._asset_temp_folder):
                if new_usda_filepath:
                    break
                for f in filenames:
                    if os.path.splitext(f)[1].startswith(".usd"):
                        new_usda_filepath = os.path.join(folder_path, f)
                        break
            self.assertNotEqual(new_usda_filepath, "")

            await omni.usd.get_context().open_stage_async(new_usda_filepath)
            stage = omni.usd.get_context().get_stage()
            prim_names = set(["Xform_1", "test_cube"])
            self.assertEqual(dump_prims(stage), prim_names)
            await omni.usd.get_context().close_stage_async()
