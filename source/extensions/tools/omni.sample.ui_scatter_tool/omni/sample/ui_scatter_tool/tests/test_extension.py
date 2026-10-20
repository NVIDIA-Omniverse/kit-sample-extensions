# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Unit tests for ScatterWindowExtension lifecycle and menu integration."""

from unittest.mock import Mock, patch

import omni.kit.test
from omni.sample.ui_scatter_tool.extension import ScatterWindowExtension


class TestScatterExtension(omni.kit.test.AsyncTestCase):
    """Basic tests for Scatter tool extension lifecycle."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        self.extension = ScatterWindowExtension()

    @patch("omni.ui.Workspace.set_show_window_fn")
    @patch("omni.kit.menu.utils.add_menu_items")
    @patch("omni.ui.Workspace.show_window")
    async def test_extension_startup_and_shutdown(self, mock_show, mock_add_menu, mock_set_fn):
        """Test that extension can start up and shut down properly."""
        # Start the extension
        self.extension.on_startup()

        # Verify UI components were set up
        mock_set_fn.assert_called()
        mock_show.assert_called_with(ScatterWindowExtension.WINDOW_NAME)
        mock_add_menu.assert_called()

        # Shutdown the extension (window might not exist)
        self.extension.on_shutdown()

        # Test shutdown with window
        mock_window = Mock()
        self.extension._window = mock_window
        self.extension.on_shutdown()

        # Verify window was destroyed
        mock_window.destroy.assert_called_once()

    def test_show_window_toggle(self):
        """Test window visibility toggle functionality."""
        # Test showing window (window doesn't exist yet)
        self.extension.show_window(None, True)
        # In real scenario, window would be created here

        # Mock an existing window
        self.extension._window = Mock()

        # Test hiding window
        self.extension.show_window(None, False)
        self.assertFalse(self.extension._window.visible)

    @patch("omni.ui.Workspace.set_show_window_fn")
    @patch("omni.kit.menu.utils.add_menu_items")
    async def test_extension_menu_registration(self, mock_add_menu, mock_set_fn):
        """Test that extension registers menu items correctly."""
        self.extension.on_startup()

        # Verify menu setup was called
        mock_add_menu.assert_called()
        mock_set_fn.assert_called()

        # Verify menu items were added with correct parameters
        call_args = mock_add_menu.call_args
        self.assertIsNotNone(call_args)
        # First argument should be list of menu items
        menu_items = call_args[0][0]
        self.assertIsInstance(menu_items, list)
        # Second argument should be "Window"
        self.assertEqual(call_args[0][1], "Window")

    def test_extension_shutdown_without_window(self):
        """Test shutdown when window was never created."""
        # Don't create window
        self.extension._window = None

        # Should not raise error
        self.extension.on_shutdown()

    def test_show_window_with_existing_visible_window(self):
        """Test showing already visible window."""
        mock_window = Mock()
        mock_window.visible = True
        self.extension._window = mock_window

        # Try to show again
        self.extension.show_window(None, True)

        # Window should remain visible
        self.assertTrue(mock_window.visible)
