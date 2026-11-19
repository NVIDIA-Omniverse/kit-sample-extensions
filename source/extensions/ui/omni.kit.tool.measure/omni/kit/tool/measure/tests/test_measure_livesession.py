# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import sys
from pathlib import Path

import omni.kit.app
import omni.usd
from omni.kit import commands, ui_test
from omni.kit.test import get_test_output_path
from omni.kit.usd.layers import LiveSessionUser, get_layers
from omni.kit.usd.layers.tests.mock_utils import MockLiveSyncingApi, _mock_logged_user_id, _mock_logged_user_name
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

from ..common import MeasureMode
from .test_measure_modes import TestMeasureModes
from .test_util import PRIM_PATHS, TestMeasureBase, prim_path_world_pos

# CURRENT_PATH = Path(__file__).parent
# TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests").absolute()
# GOLDEN_IMG_PATH = TEST_DATA_PATH.joinpath("golden_img").absolute()


class TestMeasureLivesession(TestMeasureBase):

    # for creating measure tests
    move_a_cube = TestMeasureModes.move_a_cube

    async def setUp(self):
        from omni.kit.collaboration.presence_layer import get_presence_layer_interface

        await super().setUp()

        self._context = omni.usd.get_context()
        self._layers = get_layers(self._context)
        self._live_syncing = self._layers.get_live_syncing()
        self._presence_layer = get_presence_layer_interface(self._context)

        await ui_test.wait_n_updates()

    async def tearDown(self):
        await super().tearDown()
        # self._extension._show_window(None, False)

        self._live_syncing.stop_all_live_sessions()
        self._live_syncing = None
        self._layers = None
        self._presence_layer = None

        if self._context.get_stage():
            await self._context.close_stage_async()

    def create_measurement_point_to_point(self):
        world_pos = [prim_path_world_pos(path) for path in PRIM_PATHS]

        prim_paths = [PRIM_PATHS[0], PRIM_PATHS[1]]
        points = [world_pos[0], world_pos[1]]
        commands.execute(
            "CreateMeasurementPointToPointCommand",
            prim_paths=prim_paths,
            points=points,
        )

    def get_measurements(self):
        from ..manager import MeasurementManager

        return MeasurementManager()._model.get_items()

    async def _wait(self, frames=10):
        for _ in range(frames):
            await omni.kit.app.get_app().next_update_async()

    async def _join_fake_session(self, name="test"):
        stage_url = f"omniverse://__faked_omniverse_server__/test/{name}.usd"
        self._fake_layer = Sdf.Layer.New(Sdf.FileFormat.FindByExtension(".usd"), stage_url)
        self._stage = Usd.Stage.Open(self._fake_layer)
        self._context = omni.usd.get_context()
        await self._context.attach_stage_async(self._stage)

        session = self._live_syncing.find_live_session_by_name(stage_url, f"{name}")
        if not session:
            session = self._live_syncing.create_live_session(f"{name}", stage_url)
        self._live_session = session

        self.assertTrue(session, "Failed to create live session.")
        self.assertTrue(self._live_syncing.join_live_session(session))
        await self._wait()
        self.assertTrue(self._live_syncing.is_in_live_session())

        self.assertIsNotNone(self._presence_layer)
        self.assertIsNotNone(self._presence_layer.get_shared_data_stage())
        await self._wait()

    @MockLiveSyncingApi
    async def test_live_session_join_and_create(self):
        """Join live session and create a measurement."""
        # enable live session
        await self._join_fake_session("test_basic")

        # setup test stage
        self.create_test_cubes()
        self.create_test_light()
        await ui_test.human_delay()
        self.create_measurement_point_to_point()
        await ui_test.human_delay()

        await self._wait()

        items = self.get_measurements()
        self.assertTrue(len(items) == 1)
        self.assertTrue(items[0].payload.tool_mode == MeasureMode.POINT_TO_POINT)

    @MockLiveSyncingApi
    async def test_live_session_area(self):
        """Create an area measurement during a live session"""
        # setup test stage
        await self._join_fake_session("test_area")
        self.create_test_cubes()
        self.create_test_light()
        await ui_test.human_delay()

        # create and test area measurement
        await TestMeasureModes.test_measure_mode_area(self)

        items = self.get_measurements()
        self.assertTrue(len(items) == 1)
        self.assertTrue(items[0].payload.tool_mode == MeasureMode.AREA)

    @MockLiveSyncingApi
    async def test_live_session_point_to_point(self):
        """Create a point to point measurement during a live session"""
        # setup test stage
        await self._join_fake_session("test_point_to_point")
        self.create_test_cubes()
        self.create_test_light()
        await ui_test.human_delay()

        # create and test point-to-point measurement
        await TestMeasureModes.test_measure_mode_point_to_point(self)

        items = self.get_measurements()
        self.assertTrue(len(items) == 1)
        self.assertTrue(items[0].payload.tool_mode == MeasureMode.POINT_TO_POINT)

    @MockLiveSyncingApi
    async def test_live_session_multi_point(self):
        """Create a multi-point measurement during a live session"""
        # setup test stage
        await self._join_fake_session("test_multipoint")
        self.create_test_cubes()
        self.create_test_light()
        await ui_test.human_delay()

        # create and test multi-point measurement
        await TestMeasureModes.test_measure_multi_point(self)

        items = self.get_measurements()
        self.assertTrue(len(items) == 1)
        self.assertTrue(items[0].payload.tool_mode == MeasureMode.MULTI_POINT)

    @MockLiveSyncingApi
    async def test_live_session_angle(self):
        """Create an angle measurement during a live session"""
        # setup test stage
        await self._join_fake_session("test_angle")
        self.create_test_cubes()
        self.create_test_light()
        await ui_test.human_delay()

        # create and test angle measurement
        await TestMeasureModes.test_measure_angle(self)

        items = self.get_measurements()
        self.assertTrue(len(items) == 1)
        self.assertTrue(items[0].payload.tool_mode == MeasureMode.ANGLE)

    @MockLiveSyncingApi
    async def test_live_session_diameter(self):
        """Create a diameter measurement during a live session"""
        # setup test stage
        await self._join_fake_session("test_diameter")
        self.create_test_cubes()
        self.create_test_light()
        await ui_test.human_delay()

        # create and test diameter measurement
        await TestMeasureModes.test_measure_diameter(self)

        items = self.get_measurements()
        self.assertTrue(len(items) == 1)
        self.assertTrue(items[0].payload.tool_mode == MeasureMode.DIAMETER)
