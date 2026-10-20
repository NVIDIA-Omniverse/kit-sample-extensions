## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Behavioral tests for small, API-sensitive pieces of logic.

These intentionally avoid building a real viewport/manipulator; they focus on
stable call patterns and deterministic computations that should not regress.
"""

from __future__ import annotations

from types import SimpleNamespace

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_gesture_base import CreoGestureBase, is_orthographic
from omni.kit.manipulator.creo_camera.creo_scroll_zoom_gesture import CreoScrollZoomGesture


class _DummyModel:
    def __init__(self, projection=None):
        self._projection = projection

    def get_as_floats(self, item):
        if item == "projection":
            return self._projection
        return None


class TestCreoGestureBaseBehavior(omni.kit.test.AsyncTestCase):
    async def test_is_orthographic_true_when_projection_15_is_1(self):
        model = _DummyModel(projection=[0.0] * 15 + [1.0])
        self.assertTrue(is_orthographic(model))

    async def test_is_orthographic_false_when_projection_15_is_0(self):
        model = _DummyModel(projection=[0.0] * 16)
        self.assertFalse(is_orthographic(model))

    async def test_is_orthographic_false_when_projection_missing_or_too_short(self):
        self.assertFalse(is_orthographic(_DummyModel(projection=None)))
        self.assertFalse(is_orthographic(_DummyModel(projection=[0.0] * 10)))

    async def test_on_mouse_move_accumulates_until_world_position_is_ready(self):
        calls = []

        class _DummyGesture:
            def __init__(self):
                self._accumulated_movement = [0.0, 0.0]
                self._world_position = None

            def _perform_gesture(self, mouse_moved, world_position):
                calls.append((list(mouse_moved), world_position))

        g = _DummyGesture()

        # While raycast is pending, it should only accumulate.
        CreoGestureBase.on_mouse_move(g, (0.25, -0.5))
        self.assertEqual(g._accumulated_movement, [0.25, -0.5])
        self.assertEqual(calls, [])

        # Once world position is ready, it should apply ALL accumulated movement and reset.
        g._world_position = "WORLD"
        CreoGestureBase.on_mouse_move(g, (0.75, 0.25))
        self.assertEqual(calls, [([1.0, -0.25], "WORLD")])
        self.assertEqual(g._accumulated_movement, [0.0, 0.0])

    async def test_raycast_query_name_contains_extension_prefix_and_class_name(self):
        captured = {}

        class _ViewportApi:
            def map_ndc_to_texture_pixel(self, mouse_ndc):
                return (123, 456), self

            def request_query(self, mouse_pixel, callback, *, query_name=None, **kwargs):
                captured["mouse_pixel"] = mouse_pixel
                captured["query_name"] = query_name
                captured["callback"] = callback

        class MyGesture:
            pass

        gesture = MyGesture()
        gesture._viewport_api = _ViewportApi()
        gesture.model = _DummyModel(projection=[0.0] * 16)
        gesture.sender = SimpleNamespace(gesture_payload=SimpleNamespace(mouse=(0.0, 0.0)))

        # Call unbound method; we only validate the request_query(...) call contract.
        CreoGestureBase._perform_raycast(gesture, (0.1, 0.2))
        self.assertEqual(captured["mouse_pixel"], (123, 456))
        self.assertEqual(captured["query_name"], "omni.kit.manipulator.creo_camera.MyGesture")
        self.assertTrue(callable(captured["callback"]))

    async def test_scroll_zoom_raycast_query_name_is_stable(self):
        captured = {}

        class _ViewportApi:
            def map_ndc_to_texture_pixel(self, mouse_ndc):
                return (12, 34), self

            def request_query(self, mouse_pixel, callback, *, query_name=None, **kwargs):
                captured["mouse_pixel"] = mouse_pixel
                captured["query_name"] = query_name
                captured["callback"] = callback

        sender = SimpleNamespace(gesture_payload=SimpleNamespace(mouse=(0.0, 0.0)))

        # Call unbound method with a minimal dummy object that has required fields.
        dummy = SimpleNamespace()
        dummy.sender = sender
        dummy.viewport_api = _ViewportApi()
        dummy._raycast_in_progress = False
        dummy._accumulated_scroll = 1.0

        # Methods/fields referenced by _start_raycast but not executed in this test
        dummy.model = SimpleNamespace(get_as_floats=lambda _k: [0.0] * 16)
        dummy._compute_world_position_at_distance = lambda _mouse: None
        dummy._perform_zoom = lambda *_args, **_kwargs: None

        CreoScrollZoomGesture._start_raycast(dummy)

        self.assertEqual(captured["mouse_pixel"], (12, 34))
        self.assertEqual(captured["query_name"], "omni.kit.manipulator.creo_camera.ScrollZoom")
        self.assertTrue(callable(captured["callback"]))
