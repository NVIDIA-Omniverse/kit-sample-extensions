# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb.settings
import omni.kit.app
import omni.kit.commands
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf, Sdf

from ..teleport_page import TELE_BEAM_VISIBLE
from ..teleport_scene import SETTING_SECTION_ENABLED, SETTING_SECTION_PLANE
from .utils import SETTING_SHOW_POSITION, TestTeleportBase, create_test_object, is_near_point, is_viewport_legacy

GIZMO_VIS_CHANGED_EVT = "teleport.tool.gizmo_vis.CHANGED"
GIZMO_VIS_EVT_PAYLOAD_KEY = "visibility"

LOOK_SPEED = "/persistent/exts/omni.kit.manipulator.camera/lookSpeed"


class TestTeleportGeneral(TestTeleportBase):
    async def test_teleport_default(self):
        """Basic test that activating the teleport widget with no objects selected."""
        self.assertEqual(self._teleport.get_active(), True)
        if is_viewport_legacy():
            return

        viewport_api = get_active_viewport()

        await viewport_api.wait_for_rendered_frames(5)

        carb.settings.get_settings().set(SETTING_SHOW_POSITION, False)
        await ui_test.wait_n_updates(30)
        self._teleport.unbind_widget_material()
        await ui_test.emulate_mouse_move(ui_test.Vec2(500, 510))
        await ui_test.wait_n_updates(30)
        carb.log_info(self._teleport._widgetPos)
        # Use the pos check istead of the img compare
        self.assertTrue(
            is_near_point(self._teleport._widgetPos, (521.8273103051731, 0, 149.49729065133027))
        )  # (2.779619467050793, 0, 144.4872869621883)))

        # """Test  teleport drag and drop."""
        # await self._dock_viewport()
        # await ui_test.human_delay()
        # self._teleport.set_active(True, test=True)
        # await ui_test.wait_n_updates(30)
        # await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(500, 500), ui_test.Vec2(540, 540))
        # self.assertTrue(is_near_point(self._teleport._widgetPos, (-9.650536176586854, 0, 134.41446581158544)))

        # test teleport move
        await self._dock_viewport()
        await ui_test.human_delay()
        await ui_test.emulate_mouse_move(ui_test.Vec2(500, 510))
        await ui_test.wait_n_updates(30)
        carb.log_info(self._teleport._widgetPos)
        self.assertTrue(is_near_point(self._teleport._widgetPos, (2.7796043039738265, 0, 144.48729776281698)))

        await self._dock_viewport()
        await ui_test.human_delay()
        carb.settings.get_settings().set(SETTING_SHOW_POSITION, True)
        await ui_test.wait_n_updates(30)
        # test show position
        await ui_test.emulate_mouse_move(ui_test.Vec2(600, 450))
        await ui_test.wait_n_updates(30)
        carb.log_info(self._teleport._widgetPos)
        self.assertTrue(is_near_point(self._teleport._widgetPos, (0, 0, 0)))
        await ui_test.emulate_mouse_click()
        await ui_test.wait_n_updates(30)
        carb.log_info(self._teleport._widgetPos)
        self.assertTrue(is_near_point(self._teleport._widgetPos, (-250.0000466244142, 0, -250.0000030491578)))

        # emulate right click holded mouse move
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(500, 500), ui_test.Vec2(540, 540), right_click=True)
        carb.log_info(self._teleport._widgetPos)
        self.assertTrue(is_near_point(self._teleport._widgetPos, (-167.3276079140649, 0, -177.77836683752267)))

        # test switch cameras OMFP-3311
        camera_bcp = viewport_api.get_active_camera()
        create_test_object(prim_path="/World/Camera", prim_type="Camera")
        await ui_test.wait_n_updates(5)
        viewport_api.camera_path = Sdf.Path("/World/Camera")
        await ui_test.wait_n_updates(5)
        viewport_api.camera_path = camera_bcp
        await ui_test.wait_n_updates(5)

        # test teleport move on plane
        create_test_object()
        await ui_test.wait_n_updates(5)
        await ui_test.emulate_mouse_move(ui_test.Vec2(600, 450))
        await ui_test.wait_n_updates(30)
        carb.log_info(self._teleport._widgetPos)
        self.assertTrue(is_near_point(self._teleport._widgetPos, (-184.05186777890341, 0, -244.24501744385037)))

        # show beam test
        carb.settings.get_settings().set(SETTING_SHOW_POSITION, True)
        self._teleport.show_arc(True)
        await ui_test.emulate_mouse_move(ui_test.Vec2(600, 450))
        await ui_test.wait_n_updates(30)
        is_visible = self._settings.get_as_bool(TELE_BEAM_VISIBLE)
        self.assertTrue(is_visible)
        carb.settings.get_settings().set(SETTING_SHOW_POSITION, False)
        self._teleport.show_arc(False)
        await ui_test.emulate_mouse_move(ui_test.Vec2(600, 450))
        await ui_test.wait_n_updates(30)
        is_visible = self._settings.get_as_bool(TELE_BEAM_VISIBLE)
        self.assertTrue(not is_visible)

        settings = carb.settings.get_settings()
        look_speed = settings.get(LOOK_SPEED)
        settings.set(LOOK_SPEED, [90, 45])
        await ui_test.wait_n_updates(30)
        self.assertTrue(settings.get(LOOK_SPEED) == [90, 45])
        settings.set(LOOK_SPEED, look_speed)
        await ui_test.wait_n_updates(30)
        self.assertTrue(settings.get(LOOK_SPEED) == look_speed)

        await self.finalize_test_no_image()

    async def test_teleport_with_section_tool(self):
        """Test if teleport is aware of section plane"""
        # Set up a scene with 2 large flattened cubes as floors, one is 3m higher the other
        cube_bottom_path = "/World/Cube_bottom"
        omni.kit.commands.create(
            "CreatePrim",
            prim_type="Cube",
            prim_path=cube_bottom_path,
            select_new_prim=False,
        ).do()

        omni.kit.commands.create(
            "TransformPrimSRTCommand", path=cube_bottom_path, new_scale=Gf.Vec3d(1000, 1, 1000)
        ).do()

        cube_top_path = "/World/Cube_top"
        cube_top_height = 300.0
        omni.kit.commands.create(
            "CreatePrim",
            prim_type="Cube",
            prim_path=cube_top_path,
            select_new_prim=False,
        ).do()

        omni.kit.commands.create(
            "TransformPrimSRTCommand",
            path=cube_top_path,
            new_scale=Gf.Vec3d(1000, 1, 1000),
            new_translation=Gf.Vec3d(0, cube_top_height, 0),
        ).do()

        await ui_test.wait_n_updates(5)

        self.assertEqual(self._teleport.get_active(), True)
        if is_viewport_legacy():
            return

        viewport_api = get_active_viewport()
        cam_path = viewport_api.camera_path
        cam_mtx_to_restore = viewport_api.transform

        # Teleport and we should land on top floor
        await ui_test.emulate_mouse_move(ui_test.Vec2(250, 250))
        await ui_test.wait_n_updates(30)
        # Cube floor position = height + Cube Size
        # TODO: it's not stable, sometimes failed in CI
        # self.assertAlmostEqual(self._teleport._widgetPos[1], cube_top_height + 1.0, 4)

        # Reset camera
        await self._reset_camera(cam_path, cam_mtx_to_restore)

        # Enable section plane and clip the top floor
        self._settings.set(SETTING_SECTION_ENABLED, True)
        self._settings.set(SETTING_SECTION_PLANE, [0, -1, 0, 150])

        await ui_test.wait_n_updates(5)

        # Teleport and we should land on bottom floor
        await ui_test.emulate_mouse_move(ui_test.Vec2(200, 250))
        await ui_test.wait_n_updates(30)
        # TODO: it's not stable, sometimes failed in gitlab ci
        # self.assertAlmostEqual(self._teleport._widgetPos[1], 1.0, 4)

        self._settings.set(SETTING_SECTION_ENABLED, False)


class TestTeleportToggle(OmniUiTest):
    async def test_teleport_toggle(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.tool.teleport"
        self.assertTrue(ext_id)
        self.assertTrue(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, False)
        await ui_test.wait_n_updates(30)
        self.assertTrue(not manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, True)
        await ui_test.wait_n_updates(30)
        self.assertTrue(manager.is_extension_enabled(ext_id))
        await self.finalize_test_no_image()

    async def test_teleport_prims_hidden(self):
        # This is a test for OMFP-2500
        teleport_prim = omni.usd.get_context().get_stage().GetPrimAtPath("/TeleportTools")
        hidden = teleport_prim.GetMetadata("hide_in_stage_window")
        self.assertTrue(hidden)
