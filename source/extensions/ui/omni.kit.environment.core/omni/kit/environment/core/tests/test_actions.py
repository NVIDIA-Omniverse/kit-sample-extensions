# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

import carb
import carb.input
import carb.settings
import carb.tokens
import omni.client
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.environment.core import EnvironmentSettings, SkyHelper, SkyType
from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport
from omni.ui.tests.compare_utils import CompareError, compare
from omni.ui.tests.test_base import OmniUiTest
from pxr import UsdLux

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
GOLDEN_IMAGE_PATH = TEST_DATA_PATH.joinpath("golden_img")
SKIES_PATH = f"{TEST_DATA_PATH}/Skies"
DEFAULT_CAMPOSY_PATH = "/app/viewport/defaultCamPos/y"
OUTPUTS_DIR = Path(omni.kit.test.get_test_output_path())


def _golden_name(golden_img_dir: Path, name: str) -> str:
    """Golden image for this Kit: '<name>-111.0.png' where Kit 111 renders differently, else '<name>.png'."""
    import omni.kit.app

    stem = name[: -len(".png")]
    kit_version = float(omni.kit.app.get_app().get_kit_version_short())
    if kit_version >= 111.0 and golden_img_dir.joinpath(f"{stem}-111.0.png").exists():
        return f"{stem}-111.0.png"
    return name


class TestActions(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        carb.settings.get_settings().set(DEFAULT_CAMPOSY_PATH, 25)

        try:
            from omni.kit.actions.core import get_action_registry

            self.__action_registry = get_action_registry()
            self.__action = self.__action_registry.get_action("omni.kit.environment.core", "import")
            self.assertIsNotNone(self.__action)
        except ImportError:
            self.__action = None
            self.__action_registry = None

        self.__settings = carb.settings.get_settings()
        self.__saved_ground = self.__settings.get(EnvironmentSettings.GROUND_ENABLE)
        self.__settings.set(EnvironmentSettings.GROUND_ENABLE, False)

        self.__saved_check_light = self.__settings.get(EnvironmentSettings.SHOW_LIGHT_WARNING)
        self.__settings.set(EnvironmentSettings.SHOW_LIGHT_WARNING, True)

        self.usd_context = omni.usd.get_context()
        await self.usd_context.new_stage_async()

    # After running each test
    async def tearDown(self):
        self._stage_sub = None
        self.__action_registry = None
        self.__settings.set(EnvironmentSettings.GROUND_ENABLE, self.__saved_ground)
        self.__settings.set(EnvironmentSettings.SHOW_LIGHT_WARNING, self.__saved_check_light)
        await super().tearDown()

    async def test_dynamic_sky(self):
        sky_url = f"{SKIES_PATH}/Dynamic/simple.usd"
        sky_type = SkyHelper.get_env_file_type(sky_url)
        self.assertEqual(sky_type, SkyType.DYNAMIC)

        omni.kit.commands.execute(
            "CreatePrim",
            prim_path="/Environment/defaultLight",
            prim_type="DistantLight",
            select_new_prim=False,
            # https://github.com/PixarAnimationStudios/USD/commit/b5d3809c943950cd3ff6be0467858a3297df0bb7
            attributes=(
                {UsdLux.Tokens.inputsAngle: 1.0, UsdLux.Tokens.inputsIntensity: 3000}
                if hasattr(UsdLux.Tokens, "inputsIntensity")
                else {UsdLux.Tokens.angle: 1.0, UsdLux.Tokens.intensity: 3000}
            ),
            create_default_xform=True,
        )
        self.__execute_action(sky_type, sky_url)

        # Wait for sky loaded
        await self.wait_n_updates(10)

        warning_window = ui.Workspace.get_window("###WARNING_Extra Lights Warning")
        self.assertIsNotNone(warning_window)
        window_ref = ui_test.WindowRef(warning_window, "")
        delete_btn_ref = window_ref.find_all("**/Button[*].text=='Delete'")[0]
        await delete_btn_ref.click()

        await self.finalize_test(
            golden_img_dir=GOLDEN_IMAGE_PATH,
            golden_img_name=_golden_name(GOLDEN_IMAGE_PATH, "dynamic.png"),
            # Kit 111 path-traces the lit cone: renderer updates move its shading by a few levels on ~1 % of the
            # pixels (mean error 0.0135 at Kit 31838cd2 against the 1 Oct golden). An unlit or missing cone is 2.1.
            threshold=0.05,
        )

    async def test_hdr_sky(self):
        sky_url = f"{SKIES_PATH}/Hdr/CarLight_512x256.hdr"
        sky_type = SkyHelper.get_env_file_type(sky_url)
        self.assertEqual(sky_type, SkyType.HDRI)

        self.__execute_action(sky_type, sky_url)

        # Wait for sky loaded
        await self.wait_n_updates(10)

        stage = self.usd_context.get_stage()
        sky_prim = stage.GetPrimAtPath("/Environment/sky")
        self.assertIsNotNone(sky_prim)
        self.assertTrue(sky_prim.IsA(UsdLux.DomeLight))
        sky_attr = sky_prim.GetAttribute("inputs:texture:file")
        self.assertIsNotNone(sky_attr)
        sky_value = sky_attr.Get()
        self.assertIsNotNone(sky_value)
        self.assertEqual(sky_value.path, sky_url)

    async def test_scene_template(self):
        sky_url = f"{SKIES_PATH}/Template/template.usd"
        sky_type = SkyHelper.get_env_file_type(sky_url)
        self.assertEqual(sky_type, SkyType.SCENE)

        self.__execute_action(sky_type, sky_url)

        # Wait for sky loaded
        await self.wait_n_updates(10)

        await self.finalize_test(
            golden_img_dir=GOLDEN_IMAGE_PATH,
            golden_img_name=_golden_name(GOLDEN_IMAGE_PATH, "scene.png"),
        )

    def __execute_action(self, sky_type, sky_url):
        if self.__action:
            self.__action.execute(sky_type, sky_url)
        else:
            from omni.kit.environment.core import import_environment

            import_environment(sky_type, sky_url)
