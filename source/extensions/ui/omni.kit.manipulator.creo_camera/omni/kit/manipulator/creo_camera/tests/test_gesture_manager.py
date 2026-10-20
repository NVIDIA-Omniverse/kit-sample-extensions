## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
"""Tests for CreoGestureManager.

Tests gesture prevention logic between perspective and orthographic gestures.
"""

from __future__ import annotations

from types import SimpleNamespace

import omni.kit.test
from omni.kit.manipulator.creo_camera.creo_gesture_manager import CreoGestureManager
from omni.ui import scene as sc


class TestCreoGestureManagerCanBePrevented(omni.kit.test.AsyncTestCase):
    async def test_can_be_prevented_false_for_changed_state(self):
        g = SimpleNamespace()
        g.viewport_api = SimpleNamespace(projection=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]])

        gesture = SimpleNamespace()
        gesture.state = sc.GestureState.CHANGED

        result = CreoGestureManager.can_be_prevented(g, gesture)
        self.assertFalse(result)

    async def test_can_be_prevented_false_for_ended_state(self):
        g = SimpleNamespace()
        g.viewport_api = SimpleNamespace(projection=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]])

        gesture = SimpleNamespace()
        gesture.state = sc.GestureState.ENDED

        result = CreoGestureManager.can_be_prevented(g, gesture)
        self.assertFalse(result)

    async def test_can_be_prevented_false_for_canceled_state(self):
        g = SimpleNamespace()
        g.viewport_api = SimpleNamespace(projection=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]])

        gesture = SimpleNamespace()
        gesture.state = sc.GestureState.CANCELED

        result = CreoGestureManager.can_be_prevented(g, gesture)
        self.assertFalse(result)

    async def test_can_be_prevented_true_for_began_state(self):
        g = SimpleNamespace()
        g.viewport_api = SimpleNamespace(projection=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]])

        gesture = SimpleNamespace()
        gesture.state = sc.GestureState.BEGAN

        result = CreoGestureManager.can_be_prevented(g, gesture)
        self.assertTrue(result)
