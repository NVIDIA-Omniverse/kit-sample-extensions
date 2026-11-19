# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Tests for MinimapExt extension lifecycle (startup, shutdown, toggle, stage events)."""

from unittest.mock import MagicMock, Mock, PropertyMock, patch

import omni.kit.test
import omni.usd
from omni.sample.minimap.extension import MinimapExt
from omni.sample.minimap.settings import S_PATH


class TestMinimapExtLifecycle(omni.kit.test.AsyncTestCase):
    """Tests for the MinimapExt extension startup, shutdown, and window management."""

    async def setUp(self):
        self.extension = MinimapExt.__new__(MinimapExt)

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    @patch("omni.sample.minimap.extension.WaypointsLayer")
    @patch("omni.sample.minimap.extension.MinimapWindow")
    @patch("omni.sample.minimap.extension.ui.Workspace")
    @patch("omni.sample.minimap.extension.omni.usd.get_context")
    @patch("omni.sample.minimap.extension.omni.kit.app.get_app")
    @patch("omni.sample.minimap.extension.omni.ext.get_extension_name", return_value="omni.sample.minimap")
    @patch("omni.sample.minimap.extension.carb.settings.get_settings")
    @patch("omni.sample.minimap.extension.carb.eventdispatcher.get_eventdispatcher")
    @patch.object(MinimapExt, "menu_startup")
    async def test_startup_initializes_components(
        self,
        mock_menu_startup,
        mock_get_eventdispatcher,
        mock_get_settings,
        mock_get_ext_name,
        mock_get_app,
        mock_get_context,
        mock_workspace,
        mock_window_cls,
        mock_waypoints_cls,
    ):
        """on_startup creates WaypointsLayer, registers workspace fn, and subscribes to events."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.get.return_value = False
        mock_get_settings.return_value = mock_settings

        mock_dispatcher = MagicMock()
        mock_dispatcher.observe_event.return_value = Mock()
        mock_get_eventdispatcher.return_value = mock_dispatcher

        mock_app = MagicMock()
        mock_app.get_extension_manager.return_value.get_extension_path.return_value = "/fake/path"
        mock_get_app.return_value = mock_app

        mock_ctx = MagicMock()
        mock_ctx.get_stage.return_value = None
        mock_get_context.return_value = mock_ctx

        # Act
        self.extension.on_startup("omni.sample.minimap-1.0.0")

        # Assert
        mock_waypoints_cls.assert_called_once()
        mock_workspace.set_show_window_fn.assert_called_once_with("Minimap", self.extension.toggle_window)
        mock_menu_startup.assert_called_once()
        self.assertIsNotNone(self.extension._stage_event_sub)
        self.assertIsNotNone(self.extension._app_ready_sub)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    @patch("omni.sample.minimap.extension.ui.Workspace")
    @patch.object(MinimapExt, "menu_shutdown")
    async def test_shutdown_cleans_up_resources(self, mock_menu_shutdown, mock_workspace):
        """on_shutdown nullifies window, waypoints, settings and unregisters workspace fn."""
        mock_window = MagicMock()
        mock_waypoints = MagicMock()

        self.extension._window = mock_window
        self.extension._waypoints = mock_waypoints
        self.extension._settings = MagicMock()
        self.extension._app_ready_sub = Mock()
        self.extension._stage_event_sub = Mock()

        self.extension.on_shutdown()

        self.assertIsNone(self.extension._window)
        self.assertIsNone(self.extension._waypoints)
        self.assertIsNone(self.extension._settings)
        mock_window.destroy.assert_called_once()
        mock_waypoints.destroy.assert_called_once()
        mock_menu_shutdown.assert_called_once()
        mock_workspace.set_show_window_fn.assert_called_once_with("Minimap", None)

    @patch("omni.sample.minimap.extension.ui.Workspace")
    @patch.object(MinimapExt, "menu_shutdown")
    async def test_shutdown_without_startup(self, mock_menu_shutdown, mock_workspace):
        """on_shutdown does not raise when called before on_startup."""
        # MinimapExt.__new__ does not run on_startup, so no attributes are set.
        # Provide the minimal attributes that on_shutdown expects.
        self.extension._app_ready_sub = None
        self.extension._stage_event_sub = None
        self.extension._window = None
        self.extension._waypoints = None
        self.extension._settings = None

        # Should not raise
        self.extension.on_shutdown()

    # ------------------------------------------------------------------
    # toggle_window
    # ------------------------------------------------------------------

    @patch("omni.sample.minimap.extension.MinimapWindow")
    @patch.object(MinimapExt, "menu_refresh")
    async def test_toggle_window_creates_window(self, mock_menu_refresh, mock_window_cls):
        """First call to toggle_window(True) creates a MinimapWindow."""
        mock_window_instance = MagicMock()
        mock_window_cls.return_value = mock_window_instance
        self.extension._window = None
        self.extension._settings = MagicMock()

        self.extension.toggle_window(True)

        mock_window_cls.assert_called_once_with("Minimap")
        self.assertEqual(self.extension._window, mock_window_instance)

    @patch("omni.sample.minimap.extension.MinimapWindow")
    @patch.object(MinimapExt, "menu_refresh")
    async def test_toggle_window_reuses_existing(self, mock_menu_refresh, mock_window_cls):
        """Second call reuses existing window instead of creating a new one."""
        mock_window_instance = MagicMock()
        mock_window_cls.return_value = mock_window_instance
        self.extension._window = None
        self.extension._settings = MagicMock()

        # First call creates the window
        self.extension.toggle_window(True)
        mock_window_cls.assert_called_once()

        # Second call reuses it
        self.extension.toggle_window(False)
        mock_window_cls.assert_called_once()  # Still only one call
        mock_window_instance.set_visible.assert_called_with(False)

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    @patch("omni.sample.minimap.extension.carb.settings.get_settings")
    @patch.object(MinimapExt, "menu_refresh")
    async def test_visibility_changed_updates_setting(self, mock_menu_refresh, mock_get_settings):
        """_visibility_changed_fn persists the new visibility to OPEN_ON_STARTUP."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings
        self.extension._open = True

        self.extension._visibility_changed_fn(False)

        self.assertFalse(self.extension._open)
        mock_settings.set.assert_called_with(S_PATH.OPEN_ON_STARTUP, False)

    # ------------------------------------------------------------------
    # Stage events
    # ------------------------------------------------------------------

    async def test_stage_event_rebuilds_ui_on_open(self):
        """OPENED stage event triggers rebuild_ui when window is visible."""
        mock_window = MagicMock()
        mock_window.visible = True
        self.extension._window = mock_window

        self.extension._on_stage_opened()

        mock_window.rebuild_ui.assert_called_once()

    async def test_stage_event_ignores_when_hidden(self):
        """OPENED stage event does NOT rebuild when window is hidden."""
        mock_window = MagicMock()
        mock_window.visible = False
        self.extension._window = mock_window

        self.extension._on_stage_opened()

        mock_window.rebuild_ui.assert_not_called()
