# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Tests for minimap window, utility functions, gestures, and UI properties.

MinimapWindow extends omni.ui.Window (a C++ type), so it cannot be
instantiated with object.__new__().  Instead, tests use a plain MagicMock
as ``self`` and call unbound methods / property descriptors from the real
MinimapWindow class.
"""

import time
from unittest.mock import MagicMock, Mock, patch

import omni.kit.test
from omni.sample.minimap.settings import S_PATH
from omni.sample.minimap.window import (
    MinimapWindow,
    WindowEventTypes,
    flatten,
    get_stage_axis_info,
)
from pxr import Gf, UsdGeom


# ===========================================================================
# Utility function tests
# ===========================================================================
class TestWindowUtilities(omni.kit.test.AsyncTestCase):
    """Tests for module-level utility functions in window.py."""

    async def test_flatten_identity_matrix(self):
        """flatten() on an identity-like 4x4 list produces 16-element identity array."""
        identity = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        result = flatten(identity)
        self.assertEqual(len(result), 16)
        self.assertEqual(result, [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])

    async def test_flatten_custom_matrix(self):
        """flatten() on a non-identity matrix produces the correct flat ordering."""
        matrix = [
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, 16],
        ]
        result = flatten(matrix)
        self.assertEqual(result, list(range(1, 17)))

    async def test_flatten_gf_matrix4d(self):
        """flatten() works with Gf.Matrix4d (indexable rows)."""
        m = Gf.Matrix4d()
        m.SetIdentity()
        result = flatten(m)
        self.assertEqual(len(result), 16)
        # Diagonal elements should be 1
        self.assertEqual(result[0], 1.0)
        self.assertEqual(result[5], 1.0)
        self.assertEqual(result[10], 1.0)
        self.assertEqual(result[15], 1.0)

    async def test_get_stage_axis_info_y_up(self):
        """Y-up stage returns (Tokens.y, 1, [0, 2])."""
        mock_stage = MagicMock()
        with patch("omni.sample.minimap.window.UsdGeom.GetStageUpAxis", return_value=UsdGeom.Tokens.y):
            up_axis, up_index, horizontal_indices = get_stage_axis_info(mock_stage)
        self.assertEqual(up_axis, UsdGeom.Tokens.y)
        self.assertEqual(up_index, 1)
        self.assertEqual(horizontal_indices, [0, 2])

    async def test_get_stage_axis_info_z_up(self):
        """Z-up stage returns (Tokens.z, 2, [0, 1])."""
        mock_stage = MagicMock()
        with patch("omni.sample.minimap.window.UsdGeom.GetStageUpAxis", return_value=UsdGeom.Tokens.z):
            up_axis, up_index, horizontal_indices = get_stage_axis_info(mock_stage)
        self.assertEqual(up_axis, UsdGeom.Tokens.z)
        self.assertEqual(up_index, 2)
        self.assertEqual(horizontal_indices, [0, 1])

    async def test_window_event_types_distinct(self):
        """SHOW_SETTINGS and HIDE_SETTINGS are distinct values."""
        self.assertNotEqual(int(WindowEventTypes.SHOW_SETTINGS), int(WindowEventTypes.HIDE_SETTINGS))


# ===========================================================================
# MinimapWindow property and method tests
# ===========================================================================
class TestMinimapWindow(omni.kit.test.AsyncTestCase):
    """Tests for MinimapWindow properties and methods.

    MinimapWindow extends omni.ui.Window (C++ type) so it cannot be
    instantiated via object.__new__().  We use a plain MagicMock as the
    ``self`` argument and call the real unbound methods / property
    descriptors from MinimapWindow.
    """

    def _create_mock_self(self):
        """Create a MagicMock with the attributes that MinimapWindow methods rely on."""
        win = MagicMock()
        win._cam_zoom = 700
        win._cam_size = 0.5
        win._show_settings = None
        win._settings = MagicMock()
        win._event_stream = MagicMock()
        win._simple_model = MagicMock()
        win._actor_world_pos = Gf.Vec3d(0, 0, 0)
        win._image_layer = None
        win._provider = None
        win.arc = MagicMock()
        win.interaction_arc = MagicMock()
        win.center_dot = MagicMock()
        win.frame = MagicMock()
        win._camera_scene_view = MagicMock()
        return win

    # ------------------------------------------------------------------
    # cam_zoom  (property defined on MinimapWindow)
    # ------------------------------------------------------------------

    async def test_cam_zoom_getter_setter(self):
        """Setting cam_zoom updates internal state."""
        win = self._create_mock_self()
        with patch("omni.sample.minimap.window.carb.settings.get_settings") as mock_gs:
            mock_gs.return_value = MagicMock()
            # Use the real setter from MinimapWindow
            MinimapWindow.cam_zoom.fset(win, 1200)
        self.assertEqual(win._cam_zoom, 1200)
        # The getter should return the cached value
        result = MinimapWindow.cam_zoom.fget(win)
        self.assertEqual(result, 1200)

    # ------------------------------------------------------------------
    # cam_size  (property with clamping)
    # ------------------------------------------------------------------

    async def test_cam_size_clamped_high(self):
        """Setting cam_size > 1.0 clamps to 1.0."""
        win = self._create_mock_self()
        win._cam_size = 0.5  # Different so setter runs

        with patch("omni.sample.minimap.window.carb.settings.get_settings") as mock_gs:
            mock_gs.return_value = MagicMock()
            MinimapWindow.cam_size.fset(win, 1.5)

        self.assertEqual(win._cam_size, 1.0)

    async def test_cam_size_clamped_low(self):
        """Setting cam_size < 0.0 clamps to 0.0."""
        win = self._create_mock_self()
        win._cam_size = 0.5

        with patch("omni.sample.minimap.window.carb.settings.get_settings") as mock_gs:
            mock_gs.return_value = MagicMock()
            MinimapWindow.cam_size.fset(win, -0.5)

        self.assertEqual(win._cam_size, 0.0)

    async def test_cam_size_normal_value(self):
        """Setting cam_size to a valid value stores it."""
        win = self._create_mock_self()
        win._cam_size = 0.5

        with patch("omni.sample.minimap.window.carb.settings.get_settings") as mock_gs:
            mock_gs.return_value = MagicMock()
            MinimapWindow.cam_size.fset(win, 0.8)

        self.assertAlmostEqual(win._cam_size, 0.8, places=5)

    # ------------------------------------------------------------------
    # show_settings  (property that dispatches events)
    # ------------------------------------------------------------------

    async def test_show_settings_dispatches_show_event(self):
        """Setting show_settings=True dispatches SHOW_SETTINGS event."""
        win = self._create_mock_self()
        win._show_settings = False

        with patch("omni.sample.minimap.window.carb.settings.get_settings") as mock_gs:
            mock_gs.return_value = MagicMock()
            MinimapWindow.show_settings.fset(win, True)

        self.assertTrue(win._show_settings)
        win._event_stream.dispatch.assert_called_with(WindowEventTypes.SHOW_SETTINGS)

    async def test_show_settings_dispatches_hide_event(self):
        """Setting show_settings=False dispatches HIDE_SETTINGS event."""
        win = self._create_mock_self()
        win._show_settings = True

        with patch("omni.sample.minimap.window.carb.settings.get_settings") as mock_gs:
            mock_gs.return_value = MagicMock()
            MinimapWindow.show_settings.fset(win, False)

        self.assertFalse(win._show_settings)
        win._event_stream.dispatch.assert_called_with(WindowEventTypes.HIDE_SETTINGS)

    async def test_show_settings_no_dispatch_if_unchanged(self):
        """Setting show_settings to same value does not dispatch."""
        win = self._create_mock_self()
        win._show_settings = True

        MinimapWindow.show_settings.fset(win, True)

        win._event_stream.dispatch.assert_not_called()

    # ------------------------------------------------------------------
    # _calculate_arc_radius (regular method)
    # ------------------------------------------------------------------

    async def test_arc_radius_at_min(self):
        """cam_size=0.0 produces 10% of cam_zoom (screen_fraction = 0.1)."""
        win = self._create_mock_self()
        win._cam_zoom = 1000
        radius = MinimapWindow._calculate_arc_radius(win, 0.0)
        self.assertAlmostEqual(radius, 1000 * 0.1, places=2)

    async def test_arc_radius_at_mid(self):
        """cam_size=0.5 produces ~21.5% of cam_zoom."""
        win = self._create_mock_self()
        win._cam_zoom = 1000
        radius = MinimapWindow._calculate_arc_radius(win, 0.5)
        expected = 1000 * (0.1 + 0.5 * 0.23)  # 215
        self.assertAlmostEqual(radius, expected, places=2)

    async def test_arc_radius_at_max(self):
        """cam_size=1.0 produces 33% of cam_zoom."""
        win = self._create_mock_self()
        win._cam_zoom = 1000
        radius = MinimapWindow._calculate_arc_radius(win, 1.0)
        expected = 1000 * (0.1 + 1.0 * 0.23)  # 330
        self.assertAlmostEqual(radius, expected, places=2)

    # ------------------------------------------------------------------
    # set_actor_world_pos threshold (regular method)
    # ------------------------------------------------------------------

    async def test_set_actor_world_pos_significant_move(self):
        """Move > 0.1 units updates the stored position."""
        win = self._create_mock_self()
        win._actor_world_pos = Gf.Vec3d(0, 0, 0)
        win._image_layer = None

        MinimapWindow.set_actor_world_pos(win, Gf.Vec3d(1, 0, 0))
        self.assertEqual(win._actor_world_pos, Gf.Vec3d(1, 0, 0))

    async def test_set_actor_world_pos_micro_move(self):
        """Move < 0.1 units does NOT update the stored position."""
        win = self._create_mock_self()
        original = Gf.Vec3d(100, 200, 300)
        win._actor_world_pos = original

        MinimapWindow.set_actor_world_pos(win, Gf.Vec3d(100.05, 200, 300))
        # Position should remain unchanged
        self.assertEqual(win._actor_world_pos, original)

    # ------------------------------------------------------------------
    # _refresh_ui throttling (regular method)
    # ------------------------------------------------------------------

    async def test_refresh_ui_throttled(self):
        """Rapid calls within 0.1s window are throttled (only the first executes)."""
        win = self._create_mock_self()
        win._last_ui_refresh_time = 0.0
        # Provide _MinimapWindow__scene_views for name-mangled access
        win._MinimapWindow__scene_views = []

        # First call should go through (sets _last_ui_refresh_time)
        MinimapWindow._refresh_ui(win, "test1")
        first_time = win._last_ui_refresh_time

        # Immediate second call should be throttled (< 0.1s elapsed)
        MinimapWindow._refresh_ui(win, "test2")
        # _last_ui_refresh_time should not have changed for the throttled call
        self.assertEqual(win._last_ui_refresh_time, first_time)
