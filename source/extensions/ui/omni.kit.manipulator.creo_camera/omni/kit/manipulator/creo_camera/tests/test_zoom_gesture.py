## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Tests for CreoZoomGesture behavior.

Tests zoom gesture logic using unbound method calls on minimal objects.
"""

from __future__ import annotations

from types import SimpleNamespace

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_zoom_gesture import CreoZoomGesture
from pxr import Gf


class _Model:
    def __init__(self):
        self._floats = {
            "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "projection": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "center_of_interest": [0.0, 0.0, 100.0],
        }
        self._ints = {}
        self.changed_items = []

    def get_as_floats(self, key):
        return list(self._floats.get(key, []))

    def set_floats(self, key, value):
        self._floats[key] = list(value)

    def set_ints(self, key, value):
        self._ints[key] = list(value)

    def _item_changed(self, item):
        self.changed_items.append(item)


class _VisualizerModel:
    def __init__(self):
        self.screen_ndc = None
        self.world_position = None
        self.has_moved = False

    def set_screen_ndc(self, ndc):
        self.screen_ndc = ndc

    def set_world_position(self, pos):
        self.world_position = pos

    def set_has_moved(self, moved):
        self.has_moved = moved


class _Visualizer:
    def __init__(self):
        self.model = _VisualizerModel()
        self.visible = False
        self.shown = False
        self.hidden = False

    def show(self):
        self.shown = True
        self.visible = True

    def hide(self):
        self.hidden = True
        self.visible = False


class TestCreoZoomGesturePerformGesture(omni.kit.test.AsyncTestCase):
    async def test_perform_gesture_does_nothing_when_disabled(self):
        g = SimpleNamespace()
        g.disable_zoom = True
        g.model = _Model()
        g._total_movement_y = 0.0
        g._initial_mouse_ndc = (0.0, 0.0)
        g._visualizer = None
        g._visualizer_initialized = False
        g._last_has_moved_state = False

        initial_transform = g.model.get_as_floats("transform")
        CreoZoomGesture._perform_gesture(g, [0.0, 0.5], Gf.Vec3d(0, 0, -10))
        final_transform = g.model.get_as_floats("transform")

        self.assertEqual(initial_transform, final_transform)

    async def test_perform_gesture_changes_transform_when_enabled(self):
        g = SimpleNamespace()
        g.disable_zoom = False
        g.model = _Model()
        g._total_movement_y = 0.0
        g._initial_mouse_ndc = (0.0, 0.0)
        g._initial_camera_transform = Gf.Matrix4d(*[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        g._initial_camera_position = Gf.Vec3d(0, 0, 0)
        g._accumulated_zoom = 0.0
        g._last_camera_position = Gf.Vec3d(0, 0, 0)
        g._visualizer = None
        g._visualizer_initialized = False
        g._last_has_moved_state = False

        CreoZoomGesture._perform_gesture(g, [0.0, 0.5], Gf.Vec3d(0, 0, -10))
        final_transform = g.model.get_as_floats("transform")

        # Zoom moves camera along Z axis - index 14 is Z translation
        self.assertAlmostEqual(final_transform[14], 3.529411764705883, places=6)
        self.assertIn("transform", g.model.changed_items)

    async def test_perform_gesture_accumulates_vertical_movement(self):
        g = SimpleNamespace()
        g.disable_zoom = False
        g.model = _Model()
        g._total_movement_y = 0.0
        g._initial_mouse_ndc = (0.0, 0.0)
        g._initial_camera_transform = Gf.Matrix4d(*[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        g._initial_camera_position = Gf.Vec3d(0, 0, 0)
        g._accumulated_zoom = 0.0
        g._last_camera_position = Gf.Vec3d(0, 0, 0)
        g._visualizer = None
        g._visualizer_initialized = False
        g._last_has_moved_state = False

        CreoZoomGesture._perform_gesture(g, [0.1, 0.2], Gf.Vec3d(0, 0, -10))

        self.assertAlmostEqual(g._total_movement_y, 0.2, places=6)

    async def test_perform_gesture_sets_world_position_on_first_frame(self):
        vis = _Visualizer()
        g = SimpleNamespace()
        g.disable_zoom = False
        g.model = _Model()
        g._total_movement_y = 0.0
        g._initial_mouse_ndc = (0.0, 0.0)
        g._initial_camera_transform = Gf.Matrix4d(*[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        g._initial_camera_position = Gf.Vec3d(0, 0, 0)
        g._accumulated_zoom = 0.0
        g._last_camera_position = Gf.Vec3d(0, 0, 0)  # Must match _initial_camera_position
        g._visualizer = vis
        g._visualizer_initialized = False
        g._last_has_moved_state = False

        target = Gf.Vec3d(1.0, 2.0, 3.0)
        CreoZoomGesture._perform_gesture(g, [0.0, 0.1], target)

        self.assertEqual(vis.model.world_position, target)
        self.assertTrue(g._visualizer_initialized)

    async def test_perform_gesture_updates_screen_ndc_y(self):
        vis = _Visualizer()
        vis.visible = True
        g = SimpleNamespace()
        g.disable_zoom = False
        g.model = _Model()
        g._total_movement_y = 0.0
        g._initial_mouse_ndc = (0.5, 0.0)
        g._initial_camera_transform = Gf.Matrix4d(*[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        g._initial_camera_position = Gf.Vec3d(0, 0, 0)
        g._accumulated_zoom = 0.0
        g._last_camera_position = Gf.Vec3d(0, 0, 0)
        g._visualizer = vis
        g._visualizer_initialized = True
        g._last_has_moved_state = False

        CreoZoomGesture._perform_gesture(g, [0.0, 0.2], Gf.Vec3d(0, 0, -10))

        # Screen NDC should have X from initial, Y updated
        self.assertEqual(vis.model.screen_ndc[0], 0.5)
        self.assertAlmostEqual(vis.model.screen_ndc[1], 0.2, places=6)

    async def test_perform_gesture_updates_has_moved(self):
        vis = _Visualizer()
        vis.visible = True
        g = SimpleNamespace()
        g.disable_zoom = False
        g.model = _Model()
        g._total_movement_y = 0.0
        g._initial_mouse_ndc = (0.0, 0.0)
        g._initial_camera_transform = Gf.Matrix4d(*[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        g._initial_camera_position = Gf.Vec3d(0, 0, 0)
        g._accumulated_zoom = 0.0
        g._last_camera_position = Gf.Vec3d(0, 0, 0)
        g._visualizer = vis
        g._visualizer_initialized = True
        g._last_has_moved_state = False

        CreoZoomGesture._perform_gesture(g, [0.0, 0.02], Gf.Vec3d(0, 0, -10))
        self.assertTrue(vis.model.has_moved)
