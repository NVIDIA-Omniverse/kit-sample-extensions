# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from unittest.mock import Mock, patch

import omni.kit.test
from omni.sample.csv_reader.extension import CSVReaderExtension


class TestCSVReaderExtension(omni.kit.test.AsyncTestCase):
    """Basic tests for CSV Reader extension lifecycle."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        self.extension = CSVReaderExtension()

    async def test_extension_startup_and_shutdown(self):
        """Test that extension can start up and shut down properly."""
        # Mock the model and view to avoid real initialization
        with patch("omni.sample.csv_reader.extension.CSVReaderModel") as mock_model:
            with patch("omni.sample.csv_reader.extension.CSVReaderView") as mock_view:
                # Create mock instances
                model_instance = Mock()
                view_instance = Mock()
                mock_model.return_value = model_instance
                mock_view.return_value = view_instance

                # Start the extension
                self.extension.on_startup("test_ext_id")

                # Check that model and view were created
                mock_model.assert_called_once()
                mock_view.assert_called_once_with(model_instance)
                self.assertEqual(self.extension._main_window, view_instance)

                # Shutdown the extension
                self.extension.on_shutdown()

                # Check that window was destroyed
                view_instance.destroy.assert_called_once()

    async def test_extension_shutdown_without_startup(self):
        """Test that extension can handle shutdown without startup."""
        # Create a fresh extension instance
        ext = CSVReaderExtension()

        # Should handle shutdown gracefully even if never started
        ext.on_shutdown()  # Should not raise any exception

    async def test_extension_multiple_startups(self):
        """Test extension behavior with multiple startup calls."""
        with patch("omni.sample.csv_reader.extension.CSVReaderModel") as mock_model:
            with patch("omni.sample.csv_reader.extension.CSVReaderView") as mock_view:
                model_instance = Mock()
                view_instance = Mock()
                mock_model.return_value = model_instance
                mock_view.return_value = view_instance

                # First startup
                self.extension.on_startup("test_ext_id_1")
                self.assertIsNotNone(self.extension._main_window)

                # Second startup (simulating re-enable)
                self.extension.on_startup("test_ext_id_2")

                # Should have created model and view twice
                self.assertEqual(mock_model.call_count, 2)
                self.assertEqual(mock_view.call_count, 2)

    async def test_extension_shutdown_clears_window_reference(self):
        """Test that shutdown properly clears window reference."""
        with patch("omni.sample.csv_reader.extension.CSVReaderModel") as mock_model:
            with patch("omni.sample.csv_reader.extension.CSVReaderView") as mock_view:
                mock_model.return_value = Mock()
                view_instance = Mock()
                mock_view.return_value = view_instance

                # Start and verify window exists
                self.extension.on_startup("test_ext_id")
                self.assertIsNotNone(self.extension._main_window)

                # Shutdown and verify window is cleared
                self.extension.on_shutdown()
                self.assertIsNone(self.extension._main_window)
