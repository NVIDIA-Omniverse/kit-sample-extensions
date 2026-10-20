# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.ui_test as ui_test
from pxr import Gf

from ..common import LabelSize, MeasureMode, Precision, UnitType
from ..manager import MeasurementManager
from ..system import MeasurePayload
from .test_util import PRIM_PATHS, TestMeasureBase, prim_path_world_pos


class TestMeasureModes(TestMeasureBase):
    async def setUp(self):
        await super().setUp()

    async def tearDown(self):
        await super().tearDown()

    async def move_a_cube(self):
        import omni.kit.commands

        omni.kit.commands.execute(
            "TransformPrimSRTCommand",
            path="/test_cubeA",
            new_translation=Gf.Vec3d(500, 0, 0),
        )
        await ui_test.human_delay(5)

    async def test_measure_mode_area(self):
        world_pos = [prim_path_world_pos(path) for path in PRIM_PATHS]

        offset = Gf.Vec3d(0.0, 100.0, 0.0)
        prim_paths = [PRIM_PATHS[0], PRIM_PATHS[1], PRIM_PATHS[1], PRIM_PATHS[0]]
        points = [world_pos[0] - offset, world_pos[1] - offset, world_pos[1] + offset, world_pos[0] + offset]

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = prim_paths
        payload.points = MeasurePayload.world_to_local_points(points, prim_paths)
        payload.tool_mode = MeasureMode.AREA
        payload.unit_type = UnitType.CENTIMETERS
        payload.precision = Precision.HUNDRETH
        payload.label_size = LabelSize.MEDIUM
        MeasurementManager().create(payload)

        await ui_test.wait_n_updates(3)

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0].payload.primary_value, 70710.678, 3)
        await self.move_a_cube()
        self.assertAlmostEqual(items[0].payload.primary_value, 111803.399, 3)

    async def test_measure_mode_point_to_point(self):
        world_pos = [prim_path_world_pos(path) for path in PRIM_PATHS]

        prim_paths = [PRIM_PATHS[0], PRIM_PATHS[1]]
        points = [world_pos[0], world_pos[1]]

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = prim_paths
        payload.points = MeasurePayload.world_to_local_points(points, prim_paths)
        payload.tool_mode = MeasureMode.POINT_TO_POINT
        payload.unit_type = UnitType.CENTIMETERS
        payload.precision = Precision.HUNDRETH
        payload.label_size = LabelSize.MEDIUM
        MeasurementManager().create(payload)

        await ui_test.wait_n_updates(3)

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0].payload.primary_value, 353.553, 3)
        await self.move_a_cube()
        self.assertAlmostEqual(items[0].payload.primary_value, 559.017, 3)

    async def test_measure_multi_point(self):
        world_pos = [prim_path_world_pos(path) for path in PRIM_PATHS]

        offset = Gf.Vec3d(0.0, 100.0, 0.0)
        prim_paths = [PRIM_PATHS[0], PRIM_PATHS[1], PRIM_PATHS[1], PRIM_PATHS[0]]
        points = [world_pos[0] - offset, world_pos[1] - offset, world_pos[1] + offset, world_pos[0] + offset]

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = prim_paths
        payload.points = MeasurePayload.world_to_local_points(points, prim_paths)
        payload.tool_mode = MeasureMode.MULTI_POINT
        payload.unit_type = UnitType.CENTIMETERS
        payload.precision = Precision.HUNDRETH
        payload.label_size = LabelSize.MEDIUM
        MeasurementManager().create(payload)

        await ui_test.wait_n_updates(3)

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0].payload.primary_value, 907.107, 3)
        await self.move_a_cube()
        self.assertAlmostEqual(items[0].payload.primary_value, 1318.034, 3)

    async def test_measure_angle(self):
        world_pos = [prim_path_world_pos(path) for path in PRIM_PATHS]

        offset = Gf.Vec3d(0.0, 100.0, 0.0)
        prim_paths = [PRIM_PATHS[0], PRIM_PATHS[1], PRIM_PATHS[1]]
        points = [world_pos[0] - offset, world_pos[1] - offset, world_pos[1] + offset]

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = prim_paths
        payload.points = MeasurePayload.world_to_local_points(points, prim_paths)
        payload.tool_mode = MeasureMode.ANGLE
        payload.unit_type = UnitType.CENTIMETERS
        payload.precision = Precision.HUNDRETH
        payload.label_size = LabelSize.MEDIUM
        MeasurementManager().create(payload)

        await ui_test.wait_n_updates(3)

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0].payload.primary_value, 90.0, 3)

    async def test_measure_diameter(self):
        world_pos = [prim_path_world_pos(path) for path in PRIM_PATHS]

        offset = Gf.Vec3d(0.0, 100.0, 0.0)
        prim_paths = [PRIM_PATHS[0], PRIM_PATHS[1], PRIM_PATHS[1]]
        points = [world_pos[0] - offset, world_pos[1] - offset, world_pos[1] + offset]

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = prim_paths
        payload.points = MeasurePayload.world_to_local_points(points, prim_paths)
        payload.tool_mode = MeasureMode.DIAMETER
        payload.unit_type = UnitType.CENTIMETERS
        payload.precision = Precision.HUNDRETH
        payload.label_size = LabelSize.MEDIUM
        MeasurementManager().create(payload)

        await ui_test.wait_n_updates(3)

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0].payload.primary_value, 406.202, 3)
