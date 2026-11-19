# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import unittest
from pathlib import Path

import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.usd

from ..common import MeasureMode, MeasureState, SnapMode
from .test_util import (
    PRIM_PATHS,
    SKIP_GEOMETRY_SNAP,
    TestMeasureBase,
    prim_path_to_mouse_pos,
    prim_path_world_pos,
    world_coord_to_mouse_pos,
)

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH


class TestMeasureSnaps(TestMeasureBase):
    async def setUp(self):
        await super().setUp()

        # Move mouse away from cube to start
        await ui_test.emulate_mouse_move(ui_test.Vec2(10, 10))

    async def tearDown(self):
        self._extension._show_window(None, False)
        await super().tearDown()

    def _pretest_setup(self):
        # enable point to point via StateMachine
        from ..manager import StateMachine

        StateMachine().reset_state_to_default()
        StateMachine().set_creation_state(MeasureMode.POINT_TO_POINT)

        self.assertEqual(StateMachine().tool_mode, MeasureMode.POINT_TO_POINT)
        self.assertEqual(StateMachine().tool_state, MeasureState.CREATE)

        # Set the snap
        panel_ui = self._extension._measure_panel
        self.assertIsNotNone(panel_ui)
        snap_group = panel_ui._pn_placement.snap_group
        snap_group.clear_snaps()

        return snap_group

    async def move_mouse_from_to(self, start: ui_test.Vec2, end: ui_test.Vec2, steps=25):
        app = omni.kit.app.get_app()
        x_off, y_off = (end.x - start.x) / steps, (end.y - start.y) / steps

        for step in range(steps):
            step = step + 1
            await ui_test.emulate_mouse_move(ui_test.Vec2(start.x + (x_off * step), start.y + (y_off * step)))
            await app.next_update_async()

    @unittest.skip(SKIP_GEOMETRY_SNAP)
    async def test_vertex_snap(self):
        """
        Test enabling the vertex snap and moving the mouse to a snappable region
        """
        snap_group = self._pretest_setup()

        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.VERTEX)
        self.assertEqual(snap_group._snaps.vertex, SnapMode.VERTEX)
        await ui_test.human_delay(100)

        world_pos = prim_path_world_pos(PRIM_PATHS[0])
        world_pos = [world_pos[0] + 50, world_pos[1] + 50, world_pos[2] + 50]
        mouse_pos = world_coord_to_mouse_pos(world_pos)

        await ui_test.emulate_mouse_move(mouse_pos)
        await ui_test.human_delay(10)

        # Reset snap back to False
        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.SURFACE)
        self.assertIsNone(snap_group._snaps.vertex)

    @unittest.skip(SKIP_GEOMETRY_SNAP)
    async def test_edge_snap(self):
        """
        Test enabling the edge snap and moving the mouse to a snappable region
        """
        snap_group = self._pretest_setup()

        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.EDGE)
        self.assertEqual(snap_group._snaps.edge, SnapMode.EDGE)
        await ui_test.human_delay(100)

        world_pos = prim_path_world_pos(PRIM_PATHS[0])
        world_pos = [world_pos[0] + 50, world_pos[1], world_pos[2] + 50]
        mouse_pos = world_coord_to_mouse_pos(world_pos)

        await ui_test.emulate_mouse_move(mouse_pos)
        await ui_test.human_delay(10)

        # Reset snap back to False
        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.SURFACE)
        self.assertIsNone(snap_group._snaps.edge)

    async def test_pivot_snap(self):
        """
        Test enabling the pivot snap and moving the mouse to a snappable region
        """
        snap_group = self._pretest_setup()

        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.PIVOT)
        self.assertEqual(snap_group._snaps.pivot, SnapMode.PIVOT)
        await ui_test.human_delay(10)

        mouse_pos = prim_path_to_mouse_pos(PRIM_PATHS[0])

        await ui_test.emulate_mouse_move(mouse_pos)
        await ui_test.human_delay(10)

        # Reset snap back to False
        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.SURFACE)
        self.assertIsNone(snap_group._snaps.pivot)

    @unittest.skip(SKIP_GEOMETRY_SNAP)
    async def test_midpoint_snap(self):
        """
        Test enabling the midpoint snap and moving the mouse to a snappable region
        """
        snap_group = self._pretest_setup()

        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.MIDPOINT)
        self.assertEqual(snap_group._snaps.mid, SnapMode.MIDPOINT)
        await ui_test.human_delay(100)

        world_pos = prim_path_world_pos(PRIM_PATHS[0])
        world_pos = [world_pos[0] + 50, world_pos[1], world_pos[2] + 50]
        mouse_pos = world_coord_to_mouse_pos(world_pos)

        await ui_test.emulate_mouse_move(mouse_pos)
        await ui_test.human_delay(10)

        # Reset snap back to False
        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.SURFACE)
        self.assertIsNone(snap_group._snaps.mid)

    async def test_center_snap(self):
        """
        Test enabling the center snap and moving the mouse to a snappable region
        """
        snap_group = self._pretest_setup()

        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.CENTER)
        self.assertEqual(snap_group._snaps.center, SnapMode.CENTER)
        await ui_test.human_delay(10)

        mouse_pos = prim_path_to_mouse_pos(PRIM_PATHS[0])

        await ui_test.emulate_mouse_move(mouse_pos)
        await ui_test.human_delay(10)

        # Reset snap back to False
        snap_group._snap_collection.model.as_int = snap_group._display_order.index(SnapMode.SURFACE)
        self.assertIsNone(snap_group._snaps.center)
