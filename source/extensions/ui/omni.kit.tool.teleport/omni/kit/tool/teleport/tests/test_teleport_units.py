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
    ARC_REFERENCE_DISTANCE_CM,
    ARC_REFERENCE_TAN_HALF_FOV,
    BEAM_FADE_MIN_ALPHA,
    BEAM_FADE_SEGMENTS,
    BEAM_RGB,
    POINT_COUNT,
    Bezier4,
    build_beam_fade_ribbon,
    get_arc_frustum_scale,
    get_beam_fade_alpha,
    get_beam_start,
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

    async def test_arc_frustum_scale(self):
        """The arc is drawn for its reference frustum and scaled up about the eye when the frustum is larger."""
        ref_tan = ARC_REFERENCE_TAN_HALF_FOV
        # Up to the reference frustum the arc is unchanged.
        self.assertEqual(get_arc_frustum_scale(100.0, ref_tan), 1.0)
        self.assertEqual(get_arc_frustum_scale(ARC_REFERENCE_DISTANCE_CM, ref_tan), 1.0)
        # Zoomed out: the frustum at the target grows with the distance.
        self.assertAlmostEqual(get_arc_frustum_scale(4 * ARC_REFERENCE_DISTANCE_CM, ref_tan), 4.0)
        # A wider lens grows the frustum too; a narrower one at the reference distance never shrinks the arc.
        self.assertAlmostEqual(get_arc_frustum_scale(ARC_REFERENCE_DISTANCE_CM, 2 * ref_tan), 2.0)
        self.assertEqual(get_arc_frustum_scale(ARC_REFERENCE_DISTANCE_CM, 0.5 * ref_tan), 1.0)
        # Unknown field of view (orthographic, no camera): unscaled.
        self.assertEqual(get_arc_frustum_scale(10 * ARC_REFERENCE_DISTANCE_CM, 0.0), 1.0)

    async def test_beam_start_stays_at_the_bottom_of_the_screen(self):
        """The beam starts 5cm ahead and 2cm screen-down of the eye, whichever way the camera looks."""
        eye = Gf.Vec3d(10.0, 170.0, -3.0)

        # Level view (Y up): screen-down is world-down, as the beam always assumed.
        start = get_beam_start(eye, Gf.Vec3d(0, 0, -1), Gf.Vec3d(0, 1, 0), 1.0)
        self.assertTrue(Gf.IsClose(start, eye + Gf.Vec3d(0.0, -2.0, -5.0), 1e-9))

        # Looking straight down, the camera's up is world -Z. The start stays 2cm screen-down of the view axis
        # (below the screen center) instead of moving onto the view axis, as a world-down offset did.
        start = get_beam_start(eye, Gf.Vec3d(0, -1, 0), Gf.Vec3d(0, 0, -1), 1.0)
        self.assertTrue(Gf.IsClose(start, eye + Gf.Vec3d(0.0, -5.0, 2.0), 1e-9))

        # Scaled with the stage units.
        start = get_beam_start(eye, Gf.Vec3d(0, -1, 0), Gf.Vec3d(0, 0, -1), 0.01)
        self.assertTrue(Gf.IsClose(start, eye + Gf.Vec3d(0.0, -0.05, 0.02), 1e-12))

    async def test_facing_from_above_follows_the_camera_heading(self):
        """The target's facing is the camera-to-target direction, nudged toward the camera's heading."""
        from ..teleport import FACING_HEADING_BIAS, get_facing_origin

        world_up = Gf.Vec3d(0, 1, 0)
        target = Gf.Vec3d(0, 0, 0)

        def facing(cam_pos, cam_forward, cam_up):
            origin = get_facing_origin(cam_pos, cam_forward, cam_up, world_up, (cam_pos - target).GetLength())
            away = target - origin  # the target faces away from the origin
            return (away - world_up * Gf.Dot(away, world_up)).GetNormalized()

        # Level view toward a target straight ahead: unchanged, it faces along the view.
        self.assertTrue(Gf.IsClose(facing(Gf.Vec3d(0, 0, 1000), Gf.Vec3d(0, 0, -1), world_up), Gf.Vec3d(0, 0, -1), 1e-9))

        # Level view toward a target off to the side: still essentially the camera-to-target direction.
        cam_pos = Gf.Vec3d(1000, 0, 1000)
        to_target = (target - cam_pos).GetNormalized()
        self.assertGreater(Gf.Dot(facing(cam_pos, Gf.Vec3d(0, 0, -1), world_up), to_target), 0.99)

        # Straight above the target looking down, top of the screen toward -Z: the camera-to-target direction has
        # no ground component, so the facing is the camera's heading (the top of the screen).
        down = facing(Gf.Vec3d(0, 1000, 0), Gf.Vec3d(0, -1, 0), Gf.Vec3d(0, 0, -1))
        self.assertTrue(Gf.IsClose(down, Gf.Vec3d(0, 0, -1), 1e-9))
        self.assertGreater(FACING_HEADING_BIAS, 0.0)

    async def test_beam_fade_ribbon(self):
        """The fading beam start is one eye-facing ribbon whose alpha ramps smoothly along the curve."""
        from omni.ui import color as cl

        # Smoothstep over the fade: the minimum alpha at the start, 1 at the end and beyond, always rising.
        self.assertAlmostEqual(get_beam_fade_alpha(0), BEAM_FADE_MIN_ALPHA)
        self.assertAlmostEqual(get_beam_fade_alpha(BEAM_FADE_SEGMENTS), 1.0)
        self.assertAlmostEqual(get_beam_fade_alpha(4 * BEAM_FADE_SEGMENTS), 1.0)
        alphas = [get_beam_fade_alpha(k) for k in range(BEAM_FADE_SEGMENTS + 1)]
        self.assertEqual(alphas, sorted(alphas))
        # Gentle at both ends (no corner where the beam turns opaque): the end steps are far smaller than the middle.
        middle_step = alphas[BEAM_FADE_SEGMENTS // 2 + 1] - alphas[BEAM_FADE_SEGMENTS // 2]
        self.assertLess(alphas[1] - alphas[0], middle_step / 10)
        self.assertLess(alphas[-1] - alphas[-2], middle_step / 10)

        # The real beam path, eye-relative (the eye is the origin): a level camera 2.5m above the ground and a
        # target 36m ahead. Its on-screen direction reverses inside the ribbon section, where the raw cross
        # product changes sign.
        bezier = Bezier4(get_beam_start(Gf.Vec3d(0.0), Gf.Vec3d(0, 0, -1), Gf.Vec3d(0, 1, 0)),
                         Gf.Vec3d(0.0, -250.0, -3600.0), Gf.Vec3d(0, 1, 0), 3600.0)
        curve = [bezier.get_point_more(j) for j in range(41)]
        half_width = 0.06
        positions, colors, counts, indices = build_beam_fade_ribbon(curve, half_width)

        self.assertEqual(len(positions), 2 * len(curve))
        self.assertEqual(counts, [4] * (len(curve) - 1))
        self.assertEqual(len(indices), 4 * (len(curve) - 1))
        self.assertEqual(len(colors), len(indices))  # one color per face-vertex
        previous_side = None
        for k, point in enumerate(curve):
            left, right = Gf.Vec3d(*positions[2 * k]), Gf.Vec3d(*positions[2 * k + 1])
            side = left - right
            # Centered on the curve, the tube's width, and perpendicular to the view ray (faces the eye).
            self.assertTrue(Gf.IsClose((left + right) / 2, point, 1e-9))
            self.assertAlmostEqual(side.GetLength(), 2 * half_width)
            self.assertAlmostEqual(Gf.Dot(side.GetNormalized(), point.GetNormalized()), 0.0)
            # Left and right never swap between samples, so no quad twists into a bow-tie.
            if previous_side is not None:
                self.assertGreater(Gf.Dot(side, previous_side), 0.0)
            previous_side = side
        # Each face-vertex takes the alpha of its curve point, so adjacent quads share colors at the seam.
        for color, index in zip(colors, indices):
            self.assertEqual(color, cl(*BEAM_RGB, get_beam_fade_alpha(index // 2)))

        # Orthographic camera: the ribbon faces the fixed view direction, not the ray from the eye.
        view = Gf.Vec3d(0, 0, -1)
        positions, _, _, _ = build_beam_fade_ribbon(curve, half_width, view)
        for k in range(len(curve)):
            side = Gf.Vec3d(*positions[2 * k]) - Gf.Vec3d(*positions[2 * k + 1])
            self.assertAlmostEqual(Gf.Dot(side, view), 0.0)
            self.assertAlmostEqual(side.GetLength(), 2 * half_width)

    async def test_facing_holds_where_its_ground_direction_vanishes(self):
        """Near the point below the camera the facing has no ground direction: the previous facing is kept."""
        from types import SimpleNamespace

        from ..teleport import Teleport, get_facing_origin

        up = Gf.Vec3d(0, 1, 0)
        cam_pos = Gf.Vec3d(0, 1000, 0)
        state = SimpleNamespace(_widgetPos=None, _last_facing_ground=None)
        angles = []
        # Sweep the target toward the bottom of the screen (+Z) through the point where the nudged facing cancels.
        for z in [5.0 * k for k in range(0, 41)]:
            state._widgetPos = Gf.Vec3d(0, 0, z)
            origin = get_facing_origin(cam_pos, Gf.Vec3d(0, -1, 0), Gf.Vec3d(0, 0, -1), up, (cam_pos - state._widgetPos).GetLength())
            origin = Teleport._stabilize_facing_origin(state, origin, up)
            away = state._widgetPos - origin
            ground = away - up * Gf.Dot(away, up)
            # Always a usable ground direction: never the arbitrary zero-length fallback.
            self.assertGreater(ground.GetLength(), 0.0)
            angles.append(ground.GetNormalized())
        # It faces the top of the screen (-Z) before the cancellation point and turns around after it.
        self.assertTrue(Gf.IsClose(angles[0], Gf.Vec3d(0, 0, -1), 1e-9))
        self.assertTrue(Gf.IsClose(angles[-1], Gf.Vec3d(0, 0, 1), 1e-9))

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

    async def test_z_up_top_down_target_and_beam(self):
        """Exercise the Z-up angle branch and real beam construction in centimeters and meters."""
        import math
        from types import SimpleNamespace
        from unittest.mock import patch

        from omni.ui import scene as sc
        from pxr import Sdf

        from .. import teleport_manipulator as beam
        from ..teleport_page import TELE_BEAM_VISIBLE

        if is_viewport_legacy():
            self.skipTest("Requires the modern viewport camera")

        viewport = get_active_viewport()
        old_camera = viewport.camera_path
        stage = omni.usd.get_context().get_stage()
        old_up = UsdGeom.GetStageUpAxis(stage)
        old_units = UsdGeom.GetStageMetersPerUnit(stage)
        camera_path = "/TeleportZUpTestCamera"
        self.assertFalse(stage.GetPrimAtPath(camera_path))
        camera = UsdGeom.Camera.Define(stage, camera_path)
        # Identity rotation: looks down -Z, with screen-up along +Y. No look-at pole ambiguity.
        translation = camera.AddTranslateOp()
        model = self._teleport.get_model()
        old_beam = self._settings.get(TELE_BEAM_VISIBLE)
        state_names = ("_widgetPos", "_widgetUp", "_current_angle", "_last_facing_ground",
                       "_need_skip_teleport_frame", "_draging")
        old_state = {name: getattr(self._teleport, name) for name in state_names}
        scene = sc.SceneView()
        try:
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
            viewport.camera_path = camera_path
            self._settings.set(TELE_BEAM_VISIBLE, True)
            with scene.scene:
                manipulator = beam.TeleportManipulator(model=model)
            for meters_per_unit in (0.01, 1.0):
                with self.subTest(meters_per_unit=meters_per_unit):
                    UsdGeom.SetStageMetersPerUnit(stage, meters_per_unit)
                    translation.Set(Gf.Vec3d(0, 0, 10 / meters_per_unit))
                    camera.GetPrim().CreateAttribute("omni:kit:centerOfInterest", Sdf.ValueTypeNames.Vector3d).Set(
                        Gf.Vec3d(0, 0, -10 / meters_per_unit)
                    )
                    await ui_test.wait_n_updates(5)
                    self._teleport._need_skip_teleport_frame = False
                    self._teleport._draging = False
                    self._teleport._last_facing_ground = None
                    # Only the viewport pick is supplied; camera reads, axis selection, widget and model are real.
                    hit = SimpleNamespace(valid=True, hit_position=(0, 0, 0), normal=(0, 0, 1))
                    self._teleport.on_moved((0.0, 0.0), hit)
                    self.assertTrue(Gf.IsClose(model.world_up, Gf.Vec3d.ZAxis(), 1e-9))
                    self.assertTrue(Gf.IsClose(model.visual_up, Gf.Vec3d.ZAxis(), 1e-9))
                    ground_front = Gf.Vec3d(model.visual_front[0], model.visual_front[1], 0).GetNormalized()
                    self.assertTrue(Gf.IsClose(ground_front, -Gf.Vec3d.YAxis(), 1e-9))
                    self.assertAlmostEqual(math.cos(model.angle), 0.0, places=6)
                    self.assertAlmostEqual(math.sin(model.angle), -1.0, places=6)
                    self.assertTrue(self._teleport._widget.can_teleport())

                    # Observe the curve produced by draw(), including its real camera-up and unit conversions.
                    model.visible = True
                    with patch.object(beam, "Bezier4", wraps=Bezier4) as curve:
                        manipulator.on_build()
                    curve.assert_called_once()
                    start, end, up, distance = curve.call_args.args
                    self.assertTrue(Gf.IsClose(start * meters_per_unit, Gf.Vec3d(0, -0.02, -0.05), 1e-9))
                    self.assertTrue(Gf.IsClose(end * meters_per_unit, Gf.Vec3d(0, 0, -10), 1e-9))
                    self.assertTrue(Gf.IsClose(up, Gf.Vec3d.ZAxis(), 1e-9))
                    arc = Bezier4(*curve.call_args.args, **curve.call_args.kwargs)
                    chord_control = start + (end - start) / 200.0
                    bulge = (arc.p2 - chord_control) * meters_per_unit
                    self.assertAlmostEqual(bulge[0], 0.0)
                    self.assertAlmostEqual(bulge[1], 0.0)
                    self.assertGreater(bulge[2], 0.0)
        finally:
            scene.scene.clear()
            model.visible = False
            for name, value in old_state.items():
                setattr(self._teleport, name, value)
            if old_beam is None:
                self._settings.destroy_item(TELE_BEAM_VISIBLE)
            else:
                self._settings.set(TELE_BEAM_VISIBLE, old_beam)
            viewport.camera_path = old_camera
            stage.RemovePrim(camera_path)
            UsdGeom.SetStageUpAxis(stage, old_up)
            UsdGeom.SetStageMetersPerUnit(stage, old_units)
            await ui_test.wait_n_updates(5)

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
