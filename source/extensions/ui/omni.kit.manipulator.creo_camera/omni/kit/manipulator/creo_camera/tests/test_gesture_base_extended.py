## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Extended tests for CreoGestureBase.

Tests for raycast handling, world position computation, and gesture accumulation.
"""

from __future__ import annotations

from types import SimpleNamespace

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_gesture_base import CreoGestureBase, is_orthographic
from pxr import Gf


class _Model:
    def __init__(self, is_ortho=False):
        self._floats = {
            "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "projection": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1.0 if is_ortho else 0.0],
            "center_of_interest": [0.0, 0.0, 100.0],
        }

    def get_as_floats(self, key):
        value = self._floats.get(key, [])
        if value is None:
            return None
        return list(value)


class TestIsOrthographic(omni.kit.test.AsyncTestCase):
    async def test_is_orthographic_true_for_ortho_projection(self):
        model = _Model(is_ortho=True)
        self.assertTrue(is_orthographic(model))

    async def test_is_orthographic_false_for_perspective_projection(self):
        model = _Model(is_ortho=False)
        self.assertFalse(is_orthographic(model))

    async def test_is_orthographic_false_for_none_projection(self):
        model = _Model()
        model._floats["projection"] = None
        self.assertFalse(is_orthographic(model))

    async def test_is_orthographic_false_for_short_projection(self):
        model = _Model()
        model._floats["projection"] = [1, 0, 0, 0, 0, 1, 0, 0]  # Only 8 elements
        self.assertFalse(is_orthographic(model))

    async def test_is_orthographic_checks_element_15(self):
        model = _Model()
        # Element 15 is 1.0 for ortho, 0.0 for perspective
        model._floats["projection"] = [0] * 15 + [1.0]
        self.assertTrue(is_orthographic(model))

        model._floats["projection"] = [0] * 15 + [0.0]
        self.assertFalse(is_orthographic(model))

    async def test_is_orthographic_false_for_empty_projection(self):
        model = _Model()
        model._floats["projection"] = []
        self.assertFalse(is_orthographic(model))


class TestCreoGestureBaseOnMouseMove(omni.kit.test.AsyncTestCase):
    async def test_on_mouse_move_accumulates_before_raycast_complete(self):
        g = SimpleNamespace()
        g._accumulated_movement = [0.0, 0.0]
        g._world_position = None

        CreoGestureBase.on_mouse_move(g, (0.1, 0.2))

        self.assertEqual(g._accumulated_movement, [0.1, 0.2])

    async def test_on_mouse_move_accumulates_multiple_times(self):
        g = SimpleNamespace()
        g._accumulated_movement = [0.0, 0.0]
        g._world_position = None

        CreoGestureBase.on_mouse_move(g, (0.1, 0.2))
        CreoGestureBase.on_mouse_move(g, (0.3, -0.1))

        self.assertAlmostEqual(g._accumulated_movement[0], 0.4, places=6)
        self.assertAlmostEqual(g._accumulated_movement[1], 0.1, places=6)

    async def test_on_mouse_move_calls_perform_gesture_after_raycast(self):
        calls = []

        def perform_gesture(mouse_moved, world_pos):
            calls.append((list(mouse_moved), world_pos))

        g = SimpleNamespace()
        g._accumulated_movement = [0.1, 0.2]
        g._world_position = Gf.Vec3d(1, 2, 3)
        g._perform_gesture = perform_gesture

        CreoGestureBase.on_mouse_move(g, (0.3, 0.4))

        # Should have called _perform_gesture with total accumulated movement
        self.assertEqual(len(calls), 1)
        self.assertAlmostEqual(calls[0][0][0], 0.4, places=6)
        self.assertAlmostEqual(calls[0][0][1], 0.6, places=6)

    async def test_on_mouse_move_resets_accumulation_after_perform(self):
        g = SimpleNamespace()
        g._accumulated_movement = [0.1, 0.2]
        g._world_position = Gf.Vec3d(1, 2, 3)
        g._perform_gesture = lambda *args: None

        CreoGestureBase.on_mouse_move(g, (0.3, 0.4))

        self.assertEqual(g._accumulated_movement, [0.0, 0.0])


class TestCreoGestureBasePerformRaycast(omni.kit.test.AsyncTestCase):
    async def test_perform_raycast_handles_no_viewport_api(self):
        g = SimpleNamespace()
        g._viewport_api = None

        # Should not raise
        CreoGestureBase._perform_raycast(g, (0.0, 0.0))

    async def test_perform_raycast_uses_correct_query_name(self):
        captured = {}

        class ViewportAPI:
            def map_ndc_to_texture_pixel(self, mouse_ndc):
                return (100, 100), self

            def request_query(self, mouse_pixel, callback, *, query_name=None, **kwargs):
                captured["query_name"] = query_name

        class MyGesture:
            pass

        g = MyGesture()
        g._viewport_api = ViewportAPI()
        g.model = _Model()
        g.sender = SimpleNamespace(gesture_payload=SimpleNamespace(mouse=(0.0, 0.0)))

        CreoGestureBase._perform_raycast(g, (0.0, 0.0))

        self.assertEqual(captured["query_name"], "omni.kit.manipulator.creo_camera.MyGesture")


class TestCreoGestureBaseComputeWorldPosition(omni.kit.test.AsyncTestCase):
    async def test_compute_world_position_at_distance_returns_vec3d(self):
        g = SimpleNamespace()
        g.model = _Model()

        result = CreoGestureBase._compute_world_position_at_distance(g, (0.0, 0.0))

        self.assertIsInstance(result, Gf.Vec3d)

    async def test_compute_ortho_world_plane_intersection_returns_vec3d(self):
        g = SimpleNamespace()
        g.model = _Model()

        result = CreoGestureBase._compute_ortho_world_plane_intersection(g, (0.0, 0.0))

        self.assertIsInstance(result, Gf.Vec3d)

    async def test_compute_world_position_uses_center_of_interest_distance(self):
        g = SimpleNamespace()
        g.model = _Model()
        g.model._floats["center_of_interest"] = [0.0, 0.0, 50.0]

        result1 = CreoGestureBase._compute_world_position_at_distance(g, (0.0, 0.0))

        g.model._floats["center_of_interest"] = [0.0, 0.0, 100.0]
        result2 = CreoGestureBase._compute_world_position_at_distance(g, (0.0, 0.0))

        # Different COI distances should give different results
        self.assertNotEqual(result1, result2)
