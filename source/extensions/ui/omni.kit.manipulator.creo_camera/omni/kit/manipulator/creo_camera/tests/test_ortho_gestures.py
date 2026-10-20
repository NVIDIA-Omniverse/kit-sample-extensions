## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Tests for orthographic camera gestures behavior.

Tests CreoOrthoPanGesture and CreoOrthoZoomGesture logic.
"""

from __future__ import annotations

from types import SimpleNamespace

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_ortho_pan_gesture import CreoOrthoPanGesture
from omni.kit.manipulator.creo_camera.creo_ortho_zoom_gesture import CreoOrthoZoomGesture
from pxr import Gf


class _Model:
    def __init__(self):
        self._floats = {
            "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "initial_transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "projection": [0.1, 0, 0, 0, 0, 0.1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "initial_aperture": [100.0, 100.0],
            "current_aperture": [100.0, 100.0],
        }
        self.changed_items = []

    def get_as_floats(self, key):
        return list(self._floats.get(key, []))

    def set_floats(self, key, value):
        self._floats[key] = list(value)

    def _item_changed(self, item):
        self.changed_items.append(item)

    def get_item(self, key):
        return key


class _VisualizerModel:
    def __init__(self):
        self.fixed_ndc = None
        self.moving_ndc = None
        self.has_moved = False

    def set_fixed_ndc(self, ndc):
        self.fixed_ndc = ndc

    def set_moving_ndc(self, ndc):
        self.moving_ndc = ndc

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


class TestCreoOrthoPanGestureOnMouseMove(omni.kit.test.AsyncTestCase):
    async def test_on_mouse_move_respects_disable_pan(self):
        g = SimpleNamespace()
        g.disable_pan = True
        g.model = _Model()
        g._initial_transform = None
        g._accumulated_mouse = [0.0, 0.0]
        g._visualizer = None

        initial_transform = g.model.get_as_floats("transform")
        CreoOrthoPanGesture.on_mouse_move(g, [0.1, 0.2])
        final_transform = g.model.get_as_floats("transform")

        self.assertEqual(initial_transform, final_transform)

    async def test_on_mouse_move_requires_initial_transform(self):
        g = SimpleNamespace()
        g.disable_pan = False
        g._initial_transform = None
        g.model = _Model()
        g._accumulated_mouse = [0.0, 0.0]
        g._visualizer = None

        initial_transform = g.model.get_as_floats("transform")
        CreoOrthoPanGesture.on_mouse_move(g, [0.1, 0.2])
        final_transform = g.model.get_as_floats("transform")

        self.assertEqual(initial_transform, final_transform)

    async def test_on_mouse_move_updates_transform(self):
        g = SimpleNamespace()
        g.disable_pan = False
        g.model = _Model()
        g._initial_transform = Gf.Matrix4d(*[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        g._accumulated_mouse = [0.0, 0.0]
        g._initial_mouse_ndc = (0.0, 0.0)
        g._visualizer = None
        g._last_has_moved_state = False

        CreoOrthoPanGesture.on_mouse_move(g, [0.1, 0.2])
        final_transform = g.model.get_as_floats("transform")

        # Translation is at indices 12, 13
        self.assertAlmostEqual(final_transform[12], -1.0, places=6)
        self.assertAlmostEqual(final_transform[13], -2.0, places=6)

    async def test_on_mouse_move_accumulates_movement(self):
        g = SimpleNamespace()
        g.disable_pan = False
        g.model = _Model()
        g._initial_transform = Gf.Matrix4d(*[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        g._accumulated_mouse = [0.0, 0.0]
        g._initial_mouse_ndc = (0.0, 0.0)
        g._visualizer = None
        g._last_has_moved_state = False

        CreoOrthoPanGesture.on_mouse_move(g, [0.1, 0.2])

        self.assertAlmostEqual(g._accumulated_mouse[0], 0.1, places=6)
        self.assertAlmostEqual(g._accumulated_mouse[1], 0.2, places=6)


class TestCreoOrthoZoomGestureOnMouseMove(omni.kit.test.AsyncTestCase):
    async def test_on_mouse_move_respects_disable_zoom(self):
        g = SimpleNamespace()
        g.disable_zoom = True
        g.model = _Model()
        g._initial_apertures = [100.0, 100.0]
        g._accumulated_mouse_y = 0.0
        g._visualizer = None

        initial_aperture = g.model.get_as_floats("current_aperture")
        CreoOrthoZoomGesture.on_mouse_move(g, [0.1, 0.2])
        final_aperture = g.model.get_as_floats("current_aperture")

        self.assertEqual(initial_aperture, final_aperture)

    async def test_on_mouse_move_requires_initial_apertures(self):
        g = SimpleNamespace()
        g.disable_zoom = False
        g._initial_apertures = None
        g.model = _Model()
        g._accumulated_mouse_y = 0.0
        g._visualizer = None

        initial_aperture = g.model.get_as_floats("current_aperture")
        CreoOrthoZoomGesture.on_mouse_move(g, [0.1, 0.2])
        final_aperture = g.model.get_as_floats("current_aperture")

        self.assertEqual(initial_aperture, final_aperture)
