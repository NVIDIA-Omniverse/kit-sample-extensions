## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Contract tests for visualizer models.

These models sit on top of omni.ui.scene AbstractManipulatorModel APIs.
If upstream changes any of those contracts, these tests should trip quickly.
"""

from __future__ import annotations

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_ortho_visualizer import CreoOrthoVisualizerModel
from omni.kit.manipulator.creo_camera.creo_pan_visualizer import CreoPanVisualizerModel
from omni.kit.manipulator.creo_camera.creo_visualizer_base import CreoVisualizerModelBase
from omni.kit.manipulator.creo_camera.creo_zoom_visualizer import CreoZoomVisualizerModel


class _CaptureChangedMixin:
    def __init__(self):
        super().__init__()
        self.changed_items = []

    def _item_changed(self, item):
        # Override to capture notifications without relying on upstream implementation details.
        self.changed_items.append(item)


class _CaptureBaseModel(_CaptureChangedMixin, CreoVisualizerModelBase):
    pass


class _CapturePanModel(_CaptureChangedMixin, CreoPanVisualizerModel):
    pass


class _CaptureZoomModel(_CaptureChangedMixin, CreoZoomVisualizerModel):
    pass


class _CaptureOrthoModel(_CaptureChangedMixin, CreoOrthoVisualizerModel):
    pass


class TestCreoVisualizerModels(omni.kit.test.AsyncTestCase):
    async def test_base_model_exposes_expected_items(self):
        m = _CaptureBaseModel()
        self.assertIsNotNone(m.get_item("world_position"))
        self.assertIsNotNone(m.get_item("has_moved"))

    async def test_base_model_set_world_position_triggers_item_changed(self):
        m = _CaptureBaseModel()
        m.set_world_position((1.0, 2.0, 3.0))
        self.assertIn(m.world_position, m.changed_items)
        self.assertEqual(m.get_as_floats(m.world_position), [1.0, 2.0, 3.0])

    async def test_base_model_set_has_moved_is_edge_triggered(self):
        m = _CaptureBaseModel()
        m.set_has_moved(False)
        self.assertEqual(m.changed_items, [])  # no change
        m.set_has_moved(True)
        self.assertIn(m.has_moved, m.changed_items)
        changed_count = len(m.changed_items)
        m.set_has_moved(True)
        self.assertEqual(len(m.changed_items), changed_count)  # no extra notify

    async def test_pan_model_screen_ndc_item_exists(self):
        m = _CapturePanModel()
        self.assertIsNotNone(m.get_item("screen_ndc"))

    async def test_pan_model_set_screen_ndc_triggers_item_changed(self):
        m = _CapturePanModel()
        m.set_screen_ndc((0.1, 0.2, 1.0))
        self.assertIn(m.screen_ndc, m.changed_items)
        self.assertEqual(m.get_as_floats(m.screen_ndc), [0.1, 0.2, 1.0])

    async def test_zoom_model_screen_ndc_item_exists(self):
        m = _CaptureZoomModel()
        self.assertIsNotNone(m.get_item("screen_ndc"))

    async def test_zoom_model_set_screen_ndc_triggers_item_changed(self):
        m = _CaptureZoomModel()
        m.set_screen_ndc((0.3, -0.4, 1.0))
        self.assertIn(m.screen_ndc, m.changed_items)
        self.assertEqual(m.get_as_floats(m.screen_ndc), [0.3, -0.4, 1.0])

    async def test_ortho_model_items_exist(self):
        m = _CaptureOrthoModel()
        self.assertIsNotNone(m.get_item("fixed_ndc"))
        self.assertIsNotNone(m.get_item("moving_ndc"))

    async def test_ortho_model_setters_trigger_item_changed(self):
        m = _CaptureOrthoModel()
        m.set_fixed_ndc((0.0, 0.0, 1.0))
        m.set_moving_ndc((0.5, 0.25, 1.0))
        self.assertIn(m.fixed_ndc, m.changed_items)
        self.assertIn(m.moving_ndc, m.changed_items)
        self.assertEqual(m.get_as_floats(m.fixed_ndc), [0.0, 0.0, 1.0])
        self.assertEqual(m.get_as_floats(m.moving_ndc), [0.5, 0.25, 1.0])
