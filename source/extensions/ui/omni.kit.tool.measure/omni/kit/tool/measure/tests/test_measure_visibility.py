# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.ui_test as ui_test
from carb.settings import get_settings
from pxr import Gf

from ..common import VISIBILITY_PATH, LabelSize, MeasureMode, Precision, UnitType
from ..manager import MeasurementManager
from ..system import MeasurePayload
from .test_util import PRIM_PATHS, TestMeasureBase, prim_path_world_pos


class TestMeasureVisibility(TestMeasureBase):
    async def setUp(self):
        await super().setUp()

    async def tearDown(self):
        await super().tearDown()

    async def _create_measurement(self):
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

    async def test_set_measurements_visible_toggles_transiently(self):
        """The public visibility API hides/shows completed measurements without
        persisting anything or mutating the per-measurement payloads."""
        await self._create_measurement()

        items = MeasurementManager()._model.get_items()
        self.assertEqual(len(items), 1)
        payload_visible = items[0].payload.visible

        # Visible by default (no behavior change unless a caller opts in).
        self.assertTrue(self._extension.measurements_visible)

        # Hide transiently: the manipulator gate flips, the payload does not.
        self._extension.set_measurements_visible(False)
        await ui_test.wait_n_updates(3)
        self.assertFalse(self._extension.measurements_visible)
        self.assertEqual(items[0].payload.visible, payload_visible)

        # Restore.
        self._extension.set_measurements_visible(True)
        await ui_test.wait_n_updates(3)
        self.assertTrue(self._extension.measurements_visible)
        self.assertEqual(items[0].payload.visible, payload_visible)

    async def _create_hidden_measurement(self):
        await self._create_measurement()
        measure_prim = MeasurementManager()._model.get_items()[0]
        MeasurementManager().set_visibility(measure_prim.uuid, False)
        await ui_test.wait_n_updates(3)
        return measure_prim

    async def _move_measured_prim(self):
        prim = self._ctx.get_stage().GetPrimAtPath(PRIM_PATHS[0])
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.wait_n_updates(5)

    async def test_hidden_measurement_stays_hidden_after_measured_prim_moves(self):
        """Moving a measured prim refreshes the payload from USD; the hidden state must survive it."""
        measure_prim = await self._create_hidden_measurement()

        await self._move_measured_prim()

        self.assertFalse(measure_prim.payload.visible)

    async def test_hiding_measurement_does_not_edit_stage(self):
        """Visibility is in-memory view state; neither hiding nor a later refresh may write it to USD."""
        measure_prim = await self._create_hidden_measurement()

        await self._move_measured_prim()

        self.assertTrue(measure_prim.get_attribute("measure:prop:visible"))

    async def test_display_menu_toggle_keeps_per_measurement_visibility(self):
        """The Display-menu toggle is a global view filter and must not overwrite each measurement's own choice."""
        measure_prim = await self._create_hidden_measurement()
        settings = get_settings()
        original_visibility = settings.get(VISIBILITY_PATH)

        try:
            settings.set_bool(VISIBILITY_PATH, False)
            await ui_test.wait_n_updates(3)
            settings.set_bool(VISIBILITY_PATH, True)
            await ui_test.wait_n_updates(3)
        finally:
            settings.set(VISIBILITY_PATH, original_visibility)

        self.assertFalse(measure_prim.payload.visible)
