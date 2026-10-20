## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Unit tests for shared zoom math.

These are heavy on coverage because the zoom code is both user-facing and
relies on very specific upstream math APIs (pxr.Gf).
"""

from __future__ import annotations

import math

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_zoom_math import (
    adjust_coi_for_zoom,
    apply_zoom_with_pan_compensation,
    calculate_percentage_zoom_distance,
    get_coi_distance_from_model,
)
from pxr import Gf


class _DictModel:
    def __init__(self, floats=None):
        self._floats = dict(floats or {})
        self._ints = {}

    def get_as_floats(self, key):
        v = self._floats.get(key)
        if v is None:
            return None
        return list(v)

    def set_floats(self, key, value):
        self._floats[key] = list(value)

    def set_ints(self, key, value):
        self._ints[key] = list(value)


class TestCreoZoomMath(omni.kit.test.AsyncTestCase):
    async def test_get_coi_distance_from_model_default(self):
        model = _DictModel(floats={})
        self.assertEqual(get_coi_distance_from_model(model), 100.0)

    async def test_get_coi_distance_from_model_uses_abs_z(self):
        model = _DictModel(floats={"center_of_interest": [1.0, 2.0, -123.0]})
        self.assertEqual(get_coi_distance_from_model(model), 123.0)

    async def test_calculate_percentage_zoom_distance_uses_min_reference_distance(self):
        camera = Gf.Matrix4d(1.0)
        camera.SetTranslateOnly(Gf.Vec3d(0, 0, 0))
        target = Gf.Vec3d(0, 0, -10)  # distance 10

        # COI larger -> reference should be target distance (10)
        d = calculate_percentage_zoom_distance(1.0, camera, target, coi_distance=100.0, zoom_percent=0.1)
        self.assertAlmostEqual(d, 1.0, places=6)

        # COI smaller -> reference should be COI (5)
        d = calculate_percentage_zoom_distance(1.0, camera, target, coi_distance=5.0, zoom_percent=0.1)
        self.assertAlmostEqual(d, 0.5, places=6)

    async def test_calculate_percentage_zoom_distance_clamps_reference_distance_min_1(self):
        camera = Gf.Matrix4d(1.0)
        camera.SetTranslateOnly(Gf.Vec3d(0, 0, 0))
        target = Gf.Vec3d(0, 0, 0)  # distance 0, will clamp

        d = calculate_percentage_zoom_distance(1.0, camera, target, coi_distance=0.0, zoom_percent=0.25)
        self.assertAlmostEqual(d, 0.25, places=6)  # 1.0 * 0.25 * 1.0

    async def test_calculate_percentage_zoom_distance_zero_is_zero(self):
        camera = Gf.Matrix4d(1.0)
        target = Gf.Vec3d(0, 0, -10)
        d = calculate_percentage_zoom_distance(0.0, camera, target, coi_distance=10.0, zoom_percent=0.2)
        self.assertEqual(d, 0.0)

    async def test_calculate_percentage_zoom_distance_negative_uses_inverse_formula(self):
        camera = Gf.Matrix4d(1.0)
        target = Gf.Vec3d(0, 0, -100)
        # reference distance = min(coi, dist_to_target) -> use coi=100
        d = calculate_percentage_zoom_distance(-1.0, camera, target, coi_distance=100.0, zoom_percent=0.15)
        expected_factor = 1.0 / (1.0 - 0.15) - 1.0
        self.assertAlmostEqual(d, 100.0 * expected_factor * -1.0, places=5)

    async def test_calculate_percentage_zoom_distance_scales_with_zoom_amount(self):
        camera = Gf.Matrix4d(1.0)
        target = Gf.Vec3d(0, 0, -100)
        d1 = calculate_percentage_zoom_distance(1.0, camera, target, coi_distance=100.0, zoom_percent=0.1)
        d2 = calculate_percentage_zoom_distance(2.0, camera, target, coi_distance=100.0, zoom_percent=0.1)
        self.assertAlmostEqual(d2, 2.0 * d1, places=6)

    async def test_apply_zoom_with_pan_compensation_center_mouse_does_not_introduce_xy_pan(self):
        # Identity projection makes math deterministic for this unit test.
        projection = Gf.Matrix4d(1.0)
        current = Gf.Matrix4d(1.0)
        current.SetTranslateOnly(Gf.Vec3d(0, 0, 0))

        target = Gf.Vec3d(0, 0, -10)
        out = apply_zoom_with_pan_compensation(
            current, projection, zoom_distance=5.0, mouse_ndc=(0.0, 0.0), target_world_pos=target
        )

        t = out.ExtractTranslation()
        self.assertAlmostEqual(t[0], 0.0, places=6)
        self.assertAlmostEqual(t[1], 0.0, places=6)
        self.assertAlmostEqual(t[2], -5.0, places=6)

    async def test_apply_zoom_with_pan_compensation_target_behind_camera_skips_pan(self):
        projection = Gf.Matrix4d(1.0)
        current = Gf.Matrix4d(1.0)
        current.SetTranslateOnly(Gf.Vec3d(0, 0, 0))

        target = Gf.Vec3d(0, 0, 10)  # behind camera looking -Z
        out = apply_zoom_with_pan_compensation(
            current, projection, zoom_distance=5.0, mouse_ndc=(0.5, 0.25), target_world_pos=target
        )

        # Should still zoom forward (negative Z), but not try to pan to match mouse.
        t = out.ExtractTranslation()
        self.assertAlmostEqual(t[2], -5.0, places=6)

    async def test_adjust_coi_for_zoom_sets_required_model_items(self):
        model = _DictModel(
            floats={
                "center_of_interest": [0.0, 0.0, 10.0],
            }
        )
        adjust_coi_for_zoom(model, Gf.Vec3d(1.0, 2.0, 3.0))

        self.assertEqual(model.get_as_floats("center_of_interest_picked"), [1.0, 2.0, 3.0])
        self.assertEqual(model.get_as_floats("center_of_interest_start"), [0.0, 0.0, 10.0])
        self.assertEqual(model._ints.get("object_centric_movement"), [1])

    async def test_adjust_coi_for_zoom_accepts_sequence_like_input(self):
        model = _DictModel(floats={"center_of_interest": [0.0, 0.0, 10.0]})
        adjust_coi_for_zoom(model, (9.0, 8.0, 7.0))
        self.assertEqual(model.get_as_floats("center_of_interest_picked"), [9.0, 8.0, 7.0])

    async def test_apply_zoom_with_pan_compensation_is_stable_for_small_zoom(self):
        projection = Gf.Matrix4d(1.0)
        current = Gf.Matrix4d(1.0)
        current.SetTranslateOnly(Gf.Vec3d(10, 0, 0))
        target = Gf.Vec3d(10, 0, -10)

        out = apply_zoom_with_pan_compensation(
            current, projection, zoom_distance=0.0001, mouse_ndc=(0.0, 0.0), target_world_pos=target
        )
        t = out.ExtractTranslation()
        self.assertTrue(all(math.isfinite(v) for v in (t[0], t[1], t[2])))
