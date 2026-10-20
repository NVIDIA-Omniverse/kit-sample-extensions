## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Tests for scroll zoom gestures behavior.

Tests CreoScrollZoomGesture and CreoOrthoScrollZoomGesture logic.
"""

from __future__ import annotations

from types import SimpleNamespace

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_ortho_scroll_zoom_gesture import CreoOrthoScrollZoomGesture
from omni.kit.manipulator.creo_camera.creo_scroll_zoom_gesture import CreoScrollZoomGesture


class _Model:
    def __init__(self):
        self._floats = {
            "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "initial_transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "projection": [0.1, 0, 0, 0, 0, 0.1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "center_of_interest": [0.0, 0.0, 100.0],
            "initial_aperture": [100.0, 100.0],
            "current_aperture": [100.0, 100.0],
        }
        self._ints = {}
        self.changed_items = []

    def get_as_floats(self, key):
        result = self._floats.get(key, [])
        return list(result) if result else []

    def set_floats(self, key, value):
        self._floats[key] = list(value)

    def set_ints(self, key, value):
        self._ints[key] = list(value)

    def _item_changed(self, item):
        self.changed_items.append(item)


class _ViewportAPI:
    def __init__(self):
        self.projection = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        self.query_callback = None
        self.captured_query_name = None

    def map_ndc_to_texture_pixel(self, mouse_ndc):
        return (100, 100), self

    def request_query(self, mouse_pixel, callback, *, query_name=None, **kwargs):
        self.query_callback = callback
        self.captured_query_name = query_name


class TestCreoScrollZoomGestureStartRaycast(omni.kit.test.AsyncTestCase):
    async def test_start_raycast_sets_raycast_in_progress(self):
        model = _Model()
        viewport_api = _ViewportAPI()

        g = SimpleNamespace()
        g.model = model
        g.viewport_api = viewport_api
        g._raycast_in_progress = False
        g._accumulated_scroll = 1.0
        g.sender = SimpleNamespace(gesture_payload=SimpleNamespace(mouse=(0.0, 0.0)))

        CreoScrollZoomGesture._start_raycast(g)

        self.assertTrue(g._raycast_in_progress)

    async def test_start_raycast_uses_correct_query_name(self):
        model = _Model()
        viewport_api = _ViewportAPI()

        g = SimpleNamespace()
        g.model = model
        g.viewport_api = viewport_api
        g._raycast_in_progress = False
        g._accumulated_scroll = 1.0
        g.sender = SimpleNamespace(gesture_payload=SimpleNamespace(mouse=(0.0, 0.0)))

        CreoScrollZoomGesture._start_raycast(g)

        self.assertEqual(viewport_api.captured_query_name, "omni.kit.manipulator.creo_camera.ScrollZoom")


class TestCreoOrthoScrollZoomGesturePerformZoom(omni.kit.test.AsyncTestCase):
    async def test_perform_zoom_updates_apertures(self):
        model = _Model()

        g = SimpleNamespace()
        g.model = model
        g.viewport_api = _ViewportAPI()

        CreoOrthoScrollZoomGesture._perform_zoom(g, 1.0, (0.0, 0.0))
        final_aperture = model.get_as_floats("current_aperture")

        self.assertEqual(final_aperture, [1100.0, 1100.0])

    async def test_perform_zoom_updates_transform(self):
        model = _Model()

        g = SimpleNamespace()
        g.model = model
        g.viewport_api = _ViewportAPI()

        CreoOrthoScrollZoomGesture._perform_zoom(g, 1.0, (0.5, 0.5))
        final_transform = model.get_as_floats("transform")

        # Translation at indices 12, 13
        self.assertAlmostEqual(final_transform[12], -50.0, places=6)
        self.assertAlmostEqual(final_transform[13], -50.0, places=6)

    async def test_perform_zoom_triggers_item_changed(self):
        model = _Model()

        g = SimpleNamespace()
        g.model = model
        g.viewport_api = _ViewportAPI()

        CreoOrthoScrollZoomGesture._perform_zoom(g, 1.0, (0.0, 0.0))

        self.assertIn("transform", model.changed_items)
        self.assertIn("current_aperture", model.changed_items)

    async def test_perform_zoom_scroll_direction_inverted(self):
        model1 = _Model()
        model2 = _Model()

        g1 = SimpleNamespace()
        g1.model = model1
        g1.viewport_api = _ViewportAPI()

        g2 = SimpleNamespace()
        g2.model = model2
        g2.viewport_api = _ViewportAPI()

        CreoOrthoScrollZoomGesture._perform_zoom(g1, 1.0, (0.0, 0.0))
        CreoOrthoScrollZoomGesture._perform_zoom(g2, -1.0, (0.0, 0.0))

        aperture1 = model1.get_as_floats("current_aperture")
        aperture2 = model2.get_as_floats("current_aperture")

        # Positive scroll zooms out (larger aperture), negative zooms in (smaller)
        self.assertEqual(aperture1, [1100.0, 1100.0])
        self.assertEqual(aperture2, [100.0, 100.0])
