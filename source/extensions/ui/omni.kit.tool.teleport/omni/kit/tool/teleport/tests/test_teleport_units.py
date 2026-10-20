# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.viewport.utility.camera_state import ViewportCameraState
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf, UsdGeom

from ..teleport_manipulator import (
    POINT_COUNT,
    Bezier4,
    get_bezier_offset,
    get_label_offset,
    get_ring_probe_offset,
    get_ring_scale,
    world_coord_to_screen_pos,
)
from ..teleport_widget import get_raycast_offset, get_widget_world_scale
from ..widget_geometry import RingGeometry
from .utils import TestTeleportBase, is_viewport_legacy

# Radius of the gizmo disk in the asset, which is authored in centimeters.
RING_RADIUS_CM = 46.294466
RING_SCALE = 0.85
RING_MIN_SIZE = 25
RING_MAX_SIZE = 100


class TestTeleportUnitsMath(OmniUiTest):
    """Pure geometry math: no stage, no viewport, no teleport tool.

    Deliberately not a TestTeleportBase - its setUp activates the tool and waits 300 updates,
    which is pure overhead for arithmetic.
    """

    async def test_gizmo_scale_math_is_unit_correct(self):
        """The world probe scales with stage units; the screen-space divisor must not (OMPE-12345)."""
        # The probe is a physical length, so the same gizmo is 100x smaller on a meters stage.
        probe_cm = get_ring_probe_offset(RING_RADIUS_CM, RING_SCALE, 1.0)
        probe_m = get_ring_probe_offset(RING_RADIUS_CM, RING_SCALE, 0.01)
        self.assertAlmostEqual(probe_cm * 0.01, probe_m, places=9)

        # get_ring_scale converts pixels into a scale for the asset-unit mesh drawn inside
        # sc.Space.SCREEN. Same pixels in -> same drawn pixel size out, whatever the stage units.
        # This pins the semantics: multiplying the divisor by units_scale breaks it immediately.
        for screen_size in (10.0, 50.0, 500.0):
            scale = get_ring_scale(RING_SCALE, screen_size, RING_RADIUS_CM, False, RING_MIN_SIZE, RING_MAX_SIZE)
            expected_px = RING_SCALE * min(max(screen_size, RING_MIN_SIZE), RING_MAX_SIZE)
            self.assertAlmostEqual(RING_RADIUS_CM * scale, expected_px, places=6)

        # ringManipulatorFixedSize ignores the measurement entirely, in every unit system.
        self.assertEqual(
            get_ring_scale(RING_SCALE, 5000.0, RING_RADIUS_CM, True, RING_MIN_SIZE, RING_MAX_SIZE),
            RING_SCALE,
        )

    async def test_beam_arc_bulge_scales_with_stage_units(self):
        """The beam arc is the same physical shape on a centimeters and a meters stage."""
        up = Gf.Vec3d(0, 1, 0)
        bezier_cm = Bezier4(Gf.Vec3d(0, 0, 0), Gf.Vec3d(0, 0, 900), up, 900.0, units_scale=1.0)
        bezier_m = Bezier4(Gf.Vec3d(0, 0, 0), Gf.Vec3d(0, 0, 9), up, 9.0, units_scale=0.01)

        self.assertAlmostEqual(bezier_cm.p2[1], 7.5)  # sqrt(900) / 4
        self.assertAlmostEqual(bezier_m.p2[1], 0.075)  # the same 7.5cm bulge, in meters

        # The whole curve is the same shape, 100x smaller.
        for i in range(POINT_COUNT + 1):
            point_cm = bezier_cm.get_point(i)
            point_m = bezier_m.get_point(i)
            for axis in range(3):
                self.assertAlmostEqual(point_cm[axis] * 0.01, point_m[axis], places=9)

        # The >= 3600cm branch is converted too.
        self.assertAlmostEqual(get_bezier_offset(10000.0, 1.0), 15.0)
        self.assertAlmostEqual(get_bezier_offset(100.0, 0.01), 0.15)

    async def test_label_offset_scales_with_stage_units(self):
        """The position label sits the same physical height above the target on any stage."""
        # 240 + 1000/1000*50 = 290cm
        self.assertAlmostEqual(get_label_offset(1000.0, 1.0), 290.0)
        self.assertAlmostEqual(get_label_offset(10.0, 0.01), 2.90)

    async def test_widget_world_scale_is_unit_correct(self):
        """The referenced (USD-prim) gizmo renders at the same physical size on any stage (OMPE-12345).

        A USD reference keeps the referenced centimeter coordinates as-is and renders them at the
        HOST stage's metersPerUnit, so on a meters stage the gizmo was ~100x too large. Folding
        units_scale into the applied world scale fixes it.
        """
        widget_scale = 1.3
        # units_scale is 1.0 on a centimeter stage and 0.01 on a meters stage.
        scale_cm = get_widget_world_scale(widget_scale, 1.0)
        scale_m = get_widget_world_scale(widget_scale, 0.01)
        # A world scale renders in host units, so physical size = scale * metersPerUnit must match.
        self.assertAlmostEqual(scale_cm * 0.01, scale_m * 1.0, places=9)
        # The user-facing widgetScale is preserved untouched on a centimeter stage (units_scale == 1.0).
        self.assertAlmostEqual(get_widget_world_scale(widget_scale, 1.0), widget_scale)

    async def test_raycast_offset_scales_with_stage_units(self):
        """The pick lift-off is a fixed 1cm physical distance on any stage."""
        self.assertAlmostEqual(get_raycast_offset(1.0), 1e-2)  # 1cm on a centimeter stage
        self.assertAlmostEqual(get_raycast_offset(0.01), 1e-4)  # the same 1cm, in meters
        self.assertAlmostEqual(get_raycast_offset(1.0) * 0.01, get_raycast_offset(0.01) * 1.0, places=12)


class TestTeleportUnits(TestTeleportBase):
    """Stage- and viewport-dependent units behavior."""

    async def test_units_scale_property(self):
        """TeleportModel.units_scale converts centimeters to stage units for any stage."""
        stage = omni.usd.get_context().get_stage()
        model = self._teleport.get_model()
        try:
            for meters_per_unit, expected in (
                (UsdGeom.LinearUnits.centimeters, 1.0),
                (UsdGeom.LinearUnits.meters, 0.01),
                (UsdGeom.LinearUnits.millimeters, 10.0),
                (UsdGeom.LinearUnits.kilometers, 0.00001),
            ):
                UsdGeom.SetStageMetersPerUnit(stage, meters_per_unit)
                self.assertAlmostEqual(model.meters_per_unit, meters_per_unit)
                self.assertAlmostEqual(model.units_scale, expected)

            # An invalid metersPerUnit must fall back rather than raise ZeroDivisionError.
            UsdGeom.SetStageMetersPerUnit(stage, 0.0)
            self.assertAlmostEqual(model.units_scale, 1.0)
        finally:
            # The stage is shared with the other tests in this process.
            await omni.usd.get_context().new_stage_async()
            await ui_test.wait_n_updates(5)

    async def test_ring_screen_size_is_invariant_across_stage_units(self):
        """The gizmo projects to the same pixel size for the same physical scene (OMPE-12345).

        Before the fix the asset radius was used as a raw stage-unit offset, so on a meters stage
        the projected size was ~100x too large and permanently saturated ringManipulatorMaxSize.
        """
        if is_viewport_legacy():
            return

        # Pin the viewport size: world_coord_to_screen_pos scales by window.width, and the other
        # tests in this process re-dock the shared viewport.
        await self._dock_viewport(width=1200, height=900)

        viewport_api = get_active_viewport()
        cam_path = viewport_api.camera_path
        cam_mtx_to_restore = viewport_api.transform

        try:
            screen_size_cm = await self._measure_ring_screen_size(UsdGeom.LinearUnits.centimeters, 1.0)
            screen_size_m = await self._measure_ring_screen_size(UsdGeom.LinearUnits.meters, 0.01)

            # The same physical scene in two unit systems must project to the same pixels.
            self.assertAlmostEqual(screen_size_cm, screen_size_m, delta=1.0)

            # The consumed result is identical, so the gizmo renders at the same size.
            model = self._teleport.get_model()
            self.assertAlmostEqual(
                get_ring_scale(model.ring_scale, screen_size_cm, RING_RADIUS_CM, False, RING_MIN_SIZE, RING_MAX_SIZE),
                get_ring_scale(model.ring_scale, screen_size_m, RING_RADIUS_CM, False, RING_MIN_SIZE, RING_MAX_SIZE),
                places=6,
            )

            # Documents why the bug showed up as "always max size": the unconverted meters-stage
            # probe was 100x larger and blew past the max clamp.
            self.assertGreater(screen_size_cm * 100.0, RING_MAX_SIZE)
        finally:
            await self._reset_camera(cam_path, cam_mtx_to_restore)
            await omni.usd.get_context().new_stage_async()
            await ui_test.wait_n_updates(5)

    async def _measure_ring_screen_size(self, meters_per_unit, world_scale):
        """Project the gizmo probe at the origin and return its size in pixels.

        `world_scale` scales the camera placement so the same physical scene is described in the
        given units.
        """
        stage = omni.usd.get_context().get_stage()
        UsdGeom.SetStageMetersPerUnit(stage, meters_per_unit)

        camera_state = ViewportCameraState()
        camera_state.set_position_world(Gf.Vec3d(0, 200, 1200) * world_scale, True)
        camera_state.set_target_world(Gf.Vec3d(0, 0, 0), True)
        await ui_test.wait_n_updates(5)

        model = self._teleport.get_model()
        probe = get_ring_probe_offset(RingGeometry.get_instance().radius, model.ring_scale, model.units_scale)
        target = Gf.Vec3d(0, 0, 0)
        screen_left = world_coord_to_screen_pos(target - probe * Gf.Vec3d.XAxis())
        screen_right = world_coord_to_screen_pos(target + probe * Gf.Vec3d.XAxis())
        return (screen_right - screen_left).GetLength()
