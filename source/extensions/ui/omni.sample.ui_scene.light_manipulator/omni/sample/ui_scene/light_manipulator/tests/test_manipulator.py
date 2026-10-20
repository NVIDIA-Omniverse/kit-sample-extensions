## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

from pathlib import Path

import carb
import omni.kit
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit.ui_test import Vec2
from omni.kit.viewport.utility import (
    get_active_viewport_and_window,
    get_active_viewport_window,
    get_ui_position_for_prim,
    next_viewport_frame_async,
)
from omni.sample.ui_scene.light_manipulator import LightManipulator, LightModel
from omni.ui import scene as sc
from omni.ui.tests.test_base import OmniUiTest
from pxr import UsdGeom, UsdLux

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.sample.ui_scene.light_manipulator}/data"))
OUTPUTS_DIR = Path(omni.kit.test.get_test_output_path())
TEST_DATA_PATH = CURRENT_PATH.joinpath("tests")


class TestLightManipulator(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = CURRENT_PATH.absolute().resolve().joinpath("tests")

    # After running each test
    async def tearDown(self):
        self._golden_img_dir = None
        await super().tearDown()

    async def setup_viewport(self, resolution_x: int = 800, resolution_y: int = 600):
        await self.create_test_area(resolution_x, resolution_y)
        return get_active_viewport_window()

    async def test_manipulator_transform(self):
        viewport_window = await self.setup_viewport()

        viewport = viewport_window.viewport_api
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()

        # Wait until the Viewport has delivered some frames
        await next_viewport_frame_async(viewport, 2)

        with viewport_window.get_frame(0):
            # Create a default SceneView (it has a default camera-model)
            scene_view = sc.SceneView()
            model = LightModel()
            # Add the manipulator into the SceneView's scene
            with scene_view.scene:
                LightManipulator(model=model)

        omni.kit.commands.execute(
            "CreatePrim",
            prim_path="/RectLight",
            prim_type="RectLight",
            select_new_prim=True,
            attributes={},
        )

        rect_light = UsdLux.RectLight(stage.GetPrimAtPath("/RectLight"))
        # change light attribute
        rect_light.GetHeightAttr().Set(100)
        rect_light.GetWidthAttr().Set(200)
        rect_light.GetIntensityAttr().Set(10000)
        # rotate the light to have a better angle
        rect_light_x = UsdGeom.Xformable(rect_light)
        rect_light_x.ClearXformOpOrder()
        rect_light_x.AddRotateXOp().Set(30)
        rect_light_x.AddRotateYOp().Set(45)

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(
            threshold=0.1, golden_img_dir=self._golden_img_dir, golden_img_name="test_manipulator_transform.png"
        )

    async def test_drag_gesture(self):
        # get active viewport window
        viewport_api, viewport_window = get_active_viewport_and_window()

        await omni.usd.get_context().new_stage_async()
        # open stage
        test_file_path = TEST_DATA_PATH.joinpath("selection_test.usd")
        await omni.usd.get_context().open_stage_async(str(test_file_path))

        # select rect light in /World/RectLight
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/RectLight"], True)

        # Wait until the Viewport has delivered some frames
        await next_viewport_frame_async(viewport_api, 2)

        ui_position_rect_light = get_ui_position_for_prim(viewport_window, "/World/RectLight")[0]
        rect_light_corner = Vec2(ui_position_rect_light[0] + 30, ui_position_rect_light[1] + 70)
        await ui_test.emulate_mouse_move(rect_light_corner)
        # Click and drag the rect light diagonally down
        await ui_test.input.emulate_mouse_drag_and_drop(rect_light_corner, rect_light_corner + Vec2(100, 100))
        # Deselect the rect light
        omni.usd.get_context().get_selection().set_selected_prim_paths([], True)
        # close the stage
        await omni.usd.get_context().close_stage_async()
