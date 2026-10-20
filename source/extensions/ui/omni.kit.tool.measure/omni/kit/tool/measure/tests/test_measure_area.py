# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES

import omni.kit.commands
import omni.kit.ui_test as ui_test
from pxr import Gf, UsdGeom

from ..common import LabelSize, MeasureMode, Precision, UnitType
from ..manager import MeasurementManager
from ..system import MeasurePayload
from .test_util import TestMeasureBase


class TestMeasureArea(TestMeasureBase):
    """Area mode must report non-zero area on non-centimeter stages (OMPE-101826)."""

    async def setUp(self):
        await super().setUp()

    async def tearDown(self):
        await super().tearDown()

    async def _measure_unit_square(self, unit_type: UnitType) -> float:
        omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Xform", prim_path="/area_anchor")

        # Anchor every point to the identity Xform so local == world and the quad is exact.
        prim_paths = ["/area_anchor", "/area_anchor", "/area_anchor", "/area_anchor"]
        points = [Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 0, 0), Gf.Vec3d(1, 1, 0), Gf.Vec3d(0, 1, 0)]

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = prim_paths
        payload.points = MeasurePayload.world_to_local_points(points, prim_paths)
        payload.tool_mode = MeasureMode.AREA
        payload.unit_type = unit_type
        payload.precision = Precision.HUNDRETH
        payload.label_size = LabelSize.MEDIUM
        MeasurementManager().create(payload)

        await ui_test.wait_n_updates(3)

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
        return items[0].payload.primary_value

    async def test_measure_mode_area_meters_stage_nonzero(self):
        # A meters stage, like a USD Explorer / Warehouse scene; the 1m x 1m quad is 1.0 m^2.
        UsdGeom.SetStageMetersPerUnit(self.context.get_stage(), 1.0)

        area = await self._measure_unit_square(UnitType.METERS)

        # Before the fix this was divided by 10000 (0.0001) and rendered as "0.00 m^2".
        self.assertGreater(area, 0.01, f"Area measurement must be non-zero m^2, got {area}")
        self.assertAlmostEqual(area, 1.0, places=4)

    async def test_measure_mode_area_centimeter_stage_regression(self):
        # A centimeter stage must keep working: a 1cm x 1cm quad stays 1.0 cm^2.
        UsdGeom.SetStageMetersPerUnit(self.context.get_stage(), 0.01)

        area = await self._measure_unit_square(UnitType.CENTIMETERS)

        self.assertAlmostEqual(area, 1.0, places=4)
