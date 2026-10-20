## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Tests for CreoRotateGesture behavior.

Tests rotation gesture logic using unbound method calls on minimal objects.
"""

from __future__ import annotations

from types import SimpleNamespace

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_rotate_gesture import CreoRotateGesture
from pxr import Gf


class _Model:
    def __init__(self):
        self._floats = {
            "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "projection": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        }
        self.changed_items = []

    def get_as_floats(self, key):
        return list(self._floats.get(key, []))

    def set_floats(self, key, value):
        self._floats[key] = list(value)

    def _item_changed(self, item):
        self.changed_items.append(item)


class _VisualizerModel:
    def __init__(self):
        self.world_position = None
        self.has_moved = False

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


class TestCreoRotateGesturePerformGesture(omni.kit.test.AsyncTestCase):
    async def test_perform_gesture_accumulates_total_movement(self):
        g = SimpleNamespace()
        g.model = _Model()
        g.tumble_speed = (1.0, 1.0)
        g._total_movement = [0.0, 0.0]
        g._visualizer = None
        g._visualizer_initialized = False
        g._last_has_moved_state = False

        CreoRotateGesture._perform_gesture(g, [0.1, 0.2], Gf.Vec3d(0, 0, -10))
        self.assertAlmostEqual(g._total_movement[0], 0.1, places=6)
        self.assertAlmostEqual(g._total_movement[1], 0.2, places=6)

    async def test_perform_gesture_shows_visualizer_on_first_frame(self):
        vis = _Visualizer()
        g = SimpleNamespace()
        g.model = _Model()
        g.tumble_speed = (1.0, 1.0)
        g._total_movement = [0.0, 0.0]
        g._visualizer = vis
        g._visualizer_initialized = False
        g._last_has_moved_state = False

        target = Gf.Vec3d(1.0, 2.0, 3.0)
        CreoRotateGesture._perform_gesture(g, [0.1, 0.1], target)

        self.assertTrue(vis.shown)
        self.assertEqual(vis.model.world_position, target)
        self.assertTrue(g._visualizer_initialized)

    async def test_perform_gesture_updates_transform(self):
        g = SimpleNamespace()
        g.model = _Model()
        g.tumble_speed = (1.0, 1.0)
        g._total_movement = [0.0, 0.0]
        g._visualizer = None
        g._visualizer_initialized = False
        g._last_has_moved_state = False

        CreoRotateGesture._perform_gesture(g, [0.1, 0.1], Gf.Vec3d(0, 0, -10))
        final_transform = g.model.get_as_floats("transform")

        # Rotation changes the matrix - check rotation element changed from identity
        self.assertAlmostEqual(final_transform[0], 0.9876883405951378, places=6)
        self.assertAlmostEqual(final_transform[2], 0.15643446504023087, places=6)
        self.assertIn("transform", g.model.changed_items)

    async def test_perform_gesture_uses_tumble_speed(self):
        g1 = SimpleNamespace()
        g1.model = _Model()
        g1.tumble_speed = (1.0, 1.0)
        g1._total_movement = [0.0, 0.0]
        g1._visualizer = None
        g1._visualizer_initialized = False
        g1._last_has_moved_state = False

        g2 = SimpleNamespace()
        g2.model = _Model()
        g2.tumble_speed = (2.0, 2.0)  # Double speed
        g2._total_movement = [0.0, 0.0]
        g2._visualizer = None
        g2._visualizer_initialized = False
        g2._last_has_moved_state = False

        CreoRotateGesture._perform_gesture(g1, [0.1, 0.0], Gf.Vec3d(0, 0, -10))
        CreoRotateGesture._perform_gesture(g2, [0.1, 0.0], Gf.Vec3d(0, 0, -10))

        t1 = g1.model.get_as_floats("transform")
        t2 = g2.model.get_as_floats("transform")

        # Speed 1x: element [0] = 0.9876883405951378
        # Speed 2x: element [0] = 0.9510565162951535 (more rotation)
        self.assertAlmostEqual(t1[0], 0.9876883405951378, places=6)
        self.assertAlmostEqual(t2[0], 0.9510565162951535, places=6)

    async def test_perform_gesture_updates_has_moved(self):
        vis = _Visualizer()
        vis.visible = True
        g = SimpleNamespace()
        g.model = _Model()
        g.tumble_speed = (1.0, 1.0)
        g._total_movement = [0.0, 0.0]
        g._visualizer = vis
        g._visualizer_initialized = True
        g._last_has_moved_state = False

        CreoRotateGesture._perform_gesture(g, [0.01, 0.01], Gf.Vec3d(0, 0, -10))
        self.assertTrue(vis.model.has_moved)
