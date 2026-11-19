# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import os
import unittest
from pathlib import Path

import omni.kit.app
import omni.kit.ui_test as ui_test
from carb.input import KeyboardInput
from pxr import Gf

from ..common import (
    MeasureMode,
    MeasureState,
)
from .test_util import (
    PRIM_PATHS,
    TestMeasureBase,
    prim_path_to_mouse_pos,
    prim_path_world_pos,
    world_coord_to_mouse_pos,
)

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH


class TestMeasureTools(TestMeasureBase):
    async def setUp(self):
        await super().setUp()
        await ui_test.human_delay(8)

    async def tearDown(self):
        self._extension._show_window(None, False)
        await super().tearDown()
        await ui_test.human_delay(8)

    async def test_00_point_to_point(self):
        """
        Test enabling and making a point to point via viewport
        """
        # enable point to point via StateMachine
        from ..manager import StateMachine

        StateMachine().set_creation_state(MeasureMode.POINT_TO_POINT)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.POINT_TO_POINT)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)

        # Set World XYZ
        panel_ui = self._extension._measure_panel
        self.assertIsNotNone(panel_ui)
        panel_ui._pn_display._cb_display_axis.model.get_item_value_model().as_int = 1

        prim_positions = [prim_path_to_mouse_pos(path) for path in PRIM_PATHS]

        # Make First point-to-point
        for point in prim_positions:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(5)
        await ui_test.human_delay(5)

        # Set to Local XYZ
        panel_ui._pn_display._cb_display_axis.model.get_item_value_model().as_int = 2

        for point in prim_positions:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(5)
        await ui_test.human_delay(5)

        # Move a prim
        prim = self._ctx.get_stage().GetPrimAtPath("/test_cubeA")
        self.assertTrue(prim.IsValid())
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.human_delay(5)

    async def test_01_multi_point(self):
        """
        Test enabling and making a multi point via viewport
        """
        # enable point to point via StateMachine
        from ..manager import StateMachine

        StateMachine().set_creation_state(MeasureMode.MULTI_POINT)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.MULTI_POINT)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)

        prim_positions = [prim_path_to_mouse_pos(path) for path in PRIM_PATHS]
        prim_positions.extend([ui_test.Vec2(pos.x, pos.y + 50.0) for pos in prim_positions])

        for point in prim_positions[:3]:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(5)

        # finalize click
        await ui_test.human_delay(5)
        await ui_test.emulate_mouse_click(right_click=True)
        await ui_test.human_delay(5)
        await ui_test.emulate_mouse_click(right_click=True)
        await ui_test.human_delay(5)

        # Move a prim
        prim = self._ctx.get_stage().GetPrimAtPath("/test_cubeA")
        self.assertTrue(prim.IsValid())
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.human_delay(5)

    async def test_02_angle(self):
        """
        Test enabling and making a multi point via viewport
        """
        # enable point to point via StateMachine
        from ..manager import StateMachine

        StateMachine().set_creation_state(MeasureMode.ANGLE)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.ANGLE)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)
        await ui_test.human_delay(5)

        prim_positions = [prim_path_to_mouse_pos(path) for path in PRIM_PATHS]
        prim_positions.extend([ui_test.Vec2(pos.x, pos.y + 50.0) for pos in prim_positions])

        for point in prim_positions[:3]:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(5)
        await ui_test.human_delay(5)

        # Move a prim
        prim = self._ctx.get_stage().GetPrimAtPath("/test_cubeA")
        self.assertTrue(prim.IsValid())
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.human_delay(5)

    async def test_03_diameter(self):
        """
        Test enabling and making a Diameter measurement via viewport
        """
        # enable point to point via StateMachine
        from ..manager import StateMachine

        StateMachine().set_creation_state(MeasureMode.DIAMETER)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.DIAMETER)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)

        prim_positions = [prim_path_to_mouse_pos(path) for path in PRIM_PATHS]
        prim_positions.extend([ui_test.Vec2(pos.x, pos.y + 50.0) for pos in prim_positions])

        for point in prim_positions[:3]:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(5)
        await ui_test.human_delay(5)

        # Move a prim
        prim = self._ctx.get_stage().GetPrimAtPath("/test_cubeA")
        self.assertTrue(prim.IsValid())
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.human_delay(5)

    async def test_04_area(self):
        """
        Test enabling and making a Area measurement via viewport
        """
        # enable point to point via StateMachine
        from ..common import ConstrainAxis
        from ..manager import StateMachine

        StateMachine().set_creation_state(MeasureMode.AREA)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.AREA)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)

        prim_positions = [prim_path_to_mouse_pos(path) for path in PRIM_PATHS]
        prim_positions.extend([ui_test.Vec2(pos.x, pos.y + 50.0) for pos in prim_positions])
        # sort for visual sake
        prim_positions = [prim_positions[0], prim_positions[2], prim_positions[3], prim_positions[1]]

        placement_panel = self._rm.ui_placement_panel
        self.assertIsNotNone(placement_panel)
        constrain_model = placement_panel._constrain_combo.model
        self.assertIsNotNone(constrain_model)

        # Test normal area, and all axis constraints [xyz]
        for axis in range(len(ConstrainAxis)):
            # Set Axis
            if axis == 3:  # Stage up, already represented by X,Y, or Z
                continue

            constrain_model.get_item_value_model().as_int = axis
            await ui_test.human_delay(5)

            for point in prim_positions:
                await ui_test.emulate_mouse_move(point)
                await ui_test.human_delay(5)
                await ui_test.emulate_mouse_click()
                await ui_test.human_delay(5)

            # finalize click
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click(right_click=True)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click(right_click=True)
            await ui_test.human_delay(60)

        # Move a prim
        prim = self._ctx.get_stage().GetPrimAtPath("/test_cubeA")
        self.assertTrue(prim.IsValid())
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.human_delay(5)

    async def test_05_multi_point_keyboard_complete(self):
        """
        Test enabling and making a multi point via viewport
        """
        # enable point to point via StateMachine
        from ..manager import StateMachine

        StateMachine().set_creation_state(MeasureMode.MULTI_POINT)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.MULTI_POINT)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)

        prim_positions = [prim_path_to_mouse_pos(path) for path in PRIM_PATHS]
        prim_positions.extend([ui_test.Vec2(pos.x, pos.y + 50.0) for pos in prim_positions])

        for point in prim_positions[:3]:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(5)

        # finalize via keyboard
        await ui_test.human_delay(5)
        await ui_test.emulate_keyboard_press(KeyboardInput.ENTER)
        await ui_test.human_delay(5)

        # Move a prim
        prim = self._ctx.get_stage().GetPrimAtPath("/test_cubeA")
        self.assertTrue(prim.IsValid())
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.human_delay(5)

    async def test_07_area_button_complete(self):
        """
        Test enabling and making a Area measurement via viewport
        """
        # enable point to point via StateMachine
        from ..common import ConstrainAxis
        from ..manager import StateMachine

        StateMachine().set_creation_state(MeasureMode.AREA)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.AREA)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)

        prim_positions = [prim_path_to_mouse_pos(path) for path in PRIM_PATHS]
        prim_positions.extend([ui_test.Vec2(pos.x, pos.y + 50.0) for pos in prim_positions])
        # sort for visual sake
        prim_positions = [prim_positions[0], prim_positions[2], prim_positions[3], prim_positions[1]]

        placement_panel = self._rm.ui_placement_panel
        self.assertIsNotNone(placement_panel)
        constrain_model = placement_panel._constrain_combo.model
        self.assertIsNotNone(constrain_model)

        # Test normal area, and all axis constraints [xyz]

        constrain_model.get_item_value_model().as_int = 3
        await ui_test.human_delay(5)

        for point in prim_positions:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(5)

        # finalize via simulated viewport button press
        await ui_test.human_delay(5)
        if not self._rm.measure_scene:
            return

        self._rm.measure_scene._scene_overlay._on_complete_clicked()
        await ui_test.human_delay(5)

        # Move a prim
        prim = self._ctx.get_stage().GetPrimAtPath("/test_cubeA")
        self.assertTrue(prim.IsValid())
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.human_delay(5)

    async def test_08_command_create_measure_point_to_point(self):
        """Create a point-to-point measurement via command"""
        from omni.kit import commands

        from ..manager import MeasurementManager

        world_pos = [prim_path_world_pos(path) for path in PRIM_PATHS]

        prim_paths = [PRIM_PATHS[0], PRIM_PATHS[1]]
        points = [world_pos[0], world_pos[1]]
        commands.execute(
            "CreateMeasurementPointToPointCommand",
            prim_paths=prim_paths,
            points=points,
        )
        await ui_test.human_delay(5)

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0].payload.primary_value, 353.553, 3)

    # NOTE: This test is generally skipped, but given the proper set up so it can validate Potree functionality
    # locally if desired. This test mirrors Point Cloud Managers implementation, and at some point will be removed from
    # Measure Tool tests once stable.
    # NOTE: To run this test, simply remove the underscore from the function name and ensure that the extension
    # "omni.pointcloud.streaming.potree" is uncommented in the extension.toml file.
    @unittest.skipIf(os.getenv("ETM_ACTIVE"), "Skipping Potree test in ETM")
    async def _test_09_potree_create_measure_point_to_point(self):
        """
        Test enabling and making a point to point via viewport against a potree point cloud
        """
        import carb
        from carb.settings import get_settings
        from omni.kit.app import get_app
        from omni.rtx.tests.test_common import wait_for_streaming

        from ..manager import MeasurementManager

        # POTREE Test setup
        root_path = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.tool.measure}"))
        pot_test_usd = root_path / "data" / "potree" / "lion" / "lion_potree2_test.usda"

        # set this potree setting
        get_settings().set_string("/exts/omni.pointcloud.streaming.potree/fileStreamerBasePath", str(root_path))
        await ui_test.human_delay(5)

        # Load in the potree point cloud stage
        path = str(pot_test_usd)
        self.assertTrue(self._ctx.open_stage(path), f"Failed to open stage '{path}'")

        await wait_for_streaming()

        # enable point to point via StateMachine
        from ..common import SnapMode
        from ..manager import StateMachine

        StateMachine().set_creation_state(MeasureMode.POINT_TO_POINT)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.POINT_TO_POINT)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)
        start_pos = world_coord_to_mouse_pos(Gf.Vec3d((-320.0, 130.0, -450.0)))
        prim_positions = [start_pos, ui_test.Vec2(start_pos.x + 100, start_pos.y)]

        # Set the snap
        panel_ui = self._extension._measure_panel
        self.assertIsNotNone(panel_ui)
        snap_group = panel_ui._pn_placement.snap_group
        snap_group.clear_snaps()

        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.SURFACE)
        self.assertEqual(snap_group._snaps.surface, SnapMode.SURFACE)

        # Make First point-to-point
        for point in prim_positions:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(5)
        await ui_test.human_delay(5)

        # Reset snap back to Surface
        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.SURFACE)
        self.assertEqual(snap_group._snaps.surface, SnapMode.SURFACE)

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
