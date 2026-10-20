# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
from pathlib import Path
from tempfile import TemporaryDirectory

import carb
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.kit.undo
import omni.ui as ui
import omni.usd
from omni.kit.test import AsyncTestCase
from pxr import UsdGeom

from ..scene_template import SceneTemplateHelper

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
SCENE_PATH = f"{TEST_DATA_PATH}/Skies/Template/template_with_render_settings.usd"


class TestSceneTemplate(AsyncTestCase):
    async def setUp(self):
        self.usd_context_name = ""
        self.usd_context = omni.usd.get_context(self.usd_context_name)
        await self.usd_context.new_stage_async()
        self.stage = self.usd_context.get_stage()

        self.stage.SetDefaultPrim(UsdGeom.Xform.Define(self.stage, "/World").GetPrim())

        self._helper = SceneTemplateHelper()

    async def tearDown(self):
        self._helper = None
        self.usd_context = None
        self.stage = None

    async def test_apply_with_render_settings(self):
        def __on_apply(url):
            self.__apply_url = url

        self._helper.add_on_apply_scene_template_fn(__on_apply)
        self._helper.apply_scene_template(SCENE_PATH)

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        render_settings = self._helper._get_render_settings(SCENE_PATH)

        if render_settings:
            # For rt2.0, no render settings for this scene template now
            # For such case, do not need to confirm the warning window and render settings
            warning_window = ui.Workspace.get_window("###WARNING_Apply Scene Template")
            self.assertIsNotNone(warning_window)
            window_ref = ui_test.WindowRef(warning_window, "")
            confirm_btn_ref = window_ref.find_all("**/Button[*].text=='Yes'")[0]
            await confirm_btn_ref.click()

            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()

            settings = carb.settings.get_settings()
            for key, value in render_settings.items():
                key = "/" + key.replace(":", "/")
                self.assertEqual(settings.get(key), value)

        self.assertEqual(self.__apply_url, SCENE_PATH)

        # save
        self.__saved = False

        def __saved():
            self.__saved = True

        with TemporaryDirectory() as temp_dir_name:
            save_url = f"{temp_dir_name}/save_template.usd"
            save_as_filename = "save_as_template.usd"
            save_as_url = f"{temp_dir_name}/{save_as_filename}"

            try:
                result = self._helper.save(save_url, on_save_done=__saved)
                self.assertTrue(result)
                while not self.__saved:
                    await omni.kit.app.get_app().next_update_async()

                result, _ = await omni.client.stat_async(save_url)
                self.assertEqual(result, omni.client.Result.OK)

                # Save as
                def __saved_as(path):
                    self.__saved = True

                result, _ = await omni.client.stat_async(save_as_url)
                if result == omni.client.Result.OK:
                    await omni.client.delete_async(save_as_url)
                self.__saved = False
                dialog = self._helper.save_as(on_save_done=__saved_as)
                self.assertIsNotNone(dialog)

                for _ in range(2):
                    await omni.kit.app.get_app().next_update_async()
                dialog.set_current_directory(str(temp_dir_name))
                dialog.set_filename(save_as_filename)
                for _ in range(2):
                    await omni.kit.app.get_app().next_update_async()
                dialog.navigate_to(str(temp_dir_name))
                for _ in range(2):
                    await omni.kit.app.get_app().next_update_async()

                await self.wait_n_updates(10)

                window = ui.Workspace.get_window("Save Environment As New Scene Template")
                window_ref = ui_test.WindowRef(window, "")
                apply_btn_ref = window_ref.find_all("**/Button[*].text=='Save'")[0]
                await apply_btn_ref.click()

                while not self.__saved:
                    await omni.kit.app.get_app().next_update_async()

                result, _ = await omni.client.stat_async(save_as_url)
                self.assertEqual(result, omni.client.Result.OK)
            finally:
                result, _ = await omni.client.stat_async(save_url)
                if result == omni.client.Result.OK:
                    await omni.client.delete_async(save_url)

                result, _ = await omni.client.stat_async(save_as_url)
                if result == omni.client.Result.OK:
                    await omni.client.delete_async(save_as_url)

    async def test_edit_context(self):
        edit_context = self._helper.get_edit_context()
        self.assertIsNotNone(edit_context)
