## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Extended tests for visualizers.

Tests for visualizer models behavior.
"""

from __future__ import annotations

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_ortho_visualizer import CreoOrthoVisualizerModel
from omni.kit.manipulator.creo_camera.creo_pan_visualizer import CreoPanVisualizerModel
from omni.kit.manipulator.creo_camera.creo_visualizer_base import CreoVisualizerModelBase
from omni.kit.manipulator.creo_camera.creo_zoom_visualizer import CreoZoomVisualizerModel


class TestCreoVisualizerModelBaseItems(omni.kit.test.AsyncTestCase):
    async def test_position_item_default_value(self):
        item = CreoVisualizerModelBase.PositionItem()
        self.assertEqual(item.value, [0, 0, 0])

    async def test_position_item_custom_value(self):
        item = CreoVisualizerModelBase.PositionItem([1.0, 2.0, 3.0])
        self.assertEqual(item.value, [1.0, 2.0, 3.0])

    async def test_bool_item_default_value(self):
        item = CreoVisualizerModelBase.BoolItem()
        self.assertFalse(item.value)

    async def test_bool_item_custom_value(self):
        item = CreoVisualizerModelBase.BoolItem(True)
        self.assertTrue(item.value)


class TestCreoVisualizerModelBase(omni.kit.test.AsyncTestCase):
    async def test_model_has_world_position_item(self):
        model = CreoVisualizerModelBase()
        self.assertIsNotNone(model.get_item("world_position"))

    async def test_model_has_has_moved_item(self):
        model = CreoVisualizerModelBase()
        self.assertIsNotNone(model.get_item("has_moved"))

    async def test_get_item_unknown_returns_none(self):
        model = CreoVisualizerModelBase()
        self.assertIsNone(model.get_item("unknown_item"))

    async def test_get_as_floats_wrong_item_returns_zeros(self):
        model = CreoVisualizerModelBase()
        wrong_item = object()
        result = model.get_as_floats(wrong_item)
        self.assertEqual(result, [0.0, 0.0, 0.0])

    async def test_get_as_bool_wrong_item_returns_false(self):
        model = CreoVisualizerModelBase()
        wrong_item = object()
        result = model.get_as_bool(wrong_item)
        self.assertFalse(result)

    async def test_set_world_position(self):
        model = CreoVisualizerModelBase()
        model.set_world_position([1.0, 2.0, 3.0])
        self.assertEqual(model.get_as_floats(model.world_position), [1.0, 2.0, 3.0])

    async def test_set_has_moved(self):
        model = CreoVisualizerModelBase()
        model.set_has_moved(True)
        self.assertTrue(model.get_as_bool(model.has_moved))

    async def test_set_floats_ignores_short_values(self):
        model = CreoVisualizerModelBase()
        model.set_floats(model.world_position, [1.0, 2.0])  # Only 2 values
        self.assertEqual(model.world_position.value, [0, 0, 0])

    async def test_set_floats_ignores_none_values(self):
        model = CreoVisualizerModelBase()
        model.set_floats(model.world_position, None)
        self.assertEqual(model.world_position.value, [0, 0, 0])

    async def test_destroy_clears_items(self):
        model = CreoVisualizerModelBase()
        model.destroy()
        self.assertIsNone(model.world_position)
        self.assertIsNone(model.has_moved)


class TestCreoPanVisualizerModel(omni.kit.test.AsyncTestCase):
    async def test_screen_ndc_item_exists(self):
        model = CreoPanVisualizerModel()
        self.assertIsNotNone(model.get_item("screen_ndc"))

    async def test_set_screen_ndc(self):
        model = CreoPanVisualizerModel()
        model.set_screen_ndc([0.5, -0.3, 1.0])
        self.assertEqual(model.get_as_floats(model.screen_ndc), [0.5, -0.3, 1.0])

    async def test_get_as_floats_screen_ndc(self):
        model = CreoPanVisualizerModel()
        model.screen_ndc.value = [0.1, 0.2, 0.3]
        result = model.get_as_floats(model.screen_ndc)
        self.assertEqual(result, [0.1, 0.2, 0.3])

    async def test_set_floats_screen_ndc(self):
        model = CreoPanVisualizerModel()
        model.set_floats(model.screen_ndc, [0.5, 0.6, 0.7])
        self.assertEqual(model.screen_ndc.value, [0.5, 0.6, 0.7])

    async def test_destroy_clears_screen_ndc(self):
        model = CreoPanVisualizerModel()
        model.destroy()
        self.assertIsNone(model.screen_ndc)


class TestCreoZoomVisualizerModel(omni.kit.test.AsyncTestCase):
    async def test_screen_ndc_item_exists(self):
        model = CreoZoomVisualizerModel()
        self.assertIsNotNone(model.get_item("screen_ndc"))

    async def test_set_screen_ndc(self):
        model = CreoZoomVisualizerModel()
        model.set_screen_ndc([0.5, -0.3, 1.0])
        self.assertEqual(model.get_as_floats(model.screen_ndc), [0.5, -0.3, 1.0])


class TestCreoOrthoVisualizerModel(omni.kit.test.AsyncTestCase):
    async def test_fixed_ndc_item_exists(self):
        model = CreoOrthoVisualizerModel()
        self.assertIsNotNone(model.get_item("fixed_ndc"))

    async def test_moving_ndc_item_exists(self):
        model = CreoOrthoVisualizerModel()
        self.assertIsNotNone(model.get_item("moving_ndc"))

    async def test_set_fixed_ndc(self):
        model = CreoOrthoVisualizerModel()
        model.set_fixed_ndc([0.1, 0.2, 1.0])
        self.assertEqual(model.get_as_floats(model.fixed_ndc), [0.1, 0.2, 1.0])

    async def test_set_moving_ndc(self):
        model = CreoOrthoVisualizerModel()
        model.set_moving_ndc([0.3, 0.4, 1.0])
        self.assertEqual(model.get_as_floats(model.moving_ndc), [0.3, 0.4, 1.0])

    async def test_destroy_clears_ndc_items(self):
        model = CreoOrthoVisualizerModel()
        model.destroy()
        self.assertIsNone(model.fixed_ndc)
        self.assertIsNone(model.moving_ndc)
