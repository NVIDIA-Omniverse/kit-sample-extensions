# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import csv
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import omni.kit.test
from omni.sample.csv_reader.models import CSVReaderModel
from omni.sample.csv_reader.views import STATUS_COLORS, CSVReaderView


class TestCSVReaderView(omni.kit.test.AsyncTestCase):
    """Unit tests for CSVReaderView class."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        self.model = CSVReaderModel()
        self.temp_dir = tempfile.mkdtemp()
        self.test_csv_path = Path(self.temp_dir) / "test.csv"

        # Create a sample CSV file for testing
        self._create_sample_csv()

    async def tearDown(self):
        """Clean up after each test method."""
        if self.test_csv_path.exists():
            self.test_csv_path.unlink()
        if self.temp_dir and Path(self.temp_dir).exists():
            Path(self.temp_dir).rmdir()

    def _create_sample_csv(self):
        """Create a sample CSV file for testing."""
        rows = [
            ["name", "x", "y", "z", "cluster"],
            ["point1", "1.0", "2.0", "3.0", "0"],
            ["point2", "4.0", "5.0", "6.0", "1"],
            ["point3", "7.0", "8.0", "9.0", "2"],
        ]

        with open(self.test_csv_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

    @patch("omni.sample.csv_reader.views.ui")
    def test_view_initialization(self, mock_ui):
        """Test that the view initializes correctly."""
        # Simple mock setup
        mock_window = Mock()
        mock_ui.Window.return_value = mock_window

        # Mock context managers
        mock_ui.VStack.return_value.__enter__.return_value = Mock()
        mock_ui.VStack.return_value.__exit__.return_value = None
        mock_ui.HStack.return_value.__enter__.return_value = Mock()
        mock_ui.HStack.return_value.__exit__.return_value = None

        # Mock frame as context manager
        mock_frame = Mock()
        mock_frame.__enter__ = Mock(return_value=Mock())
        mock_frame.__exit__ = Mock(return_value=None)
        mock_window.frame = mock_frame

        # Mock UI components
        mock_ui.StringField.return_value = Mock()
        mock_ui.Button.return_value = Mock()
        mock_ui.ComboBox.return_value = Mock()
        mock_ui.CheckBox.return_value = Mock()
        mock_ui.Label.return_value = Mock()
        mock_ui.ProgressBar.return_value = Mock()
        mock_ui.Line.return_value = Mock()

        # Create the view
        view = CSVReaderView(self.model)

        # Verify basic initialization
        self.assertEqual(view._csvmodel, self.model)
        mock_ui.Window.assert_called_once()

    def test_set_status(self):
        """Test status setting functionality."""
        # Create view without UI mocking for this simple test
        view = CSVReaderView.__new__(CSVReaderView)
        view.status_label = Mock()
        view.status_label.style = {}

        # Test status setting
        view._set_status("Test message", "ready")

        self.assertEqual(view.status_label.text, "Test message")
        self.assertEqual(view.status_label.style["color"], STATUS_COLORS["ready"])

    def test_validate_csv_file_valid(self):
        """Test CSV validation with a valid file."""
        self.model.csv_file_path = self.test_csv_path

        # Create view without UI mocking
        view = CSVReaderView.__new__(CSVReaderView)
        view._csvmodel = self.model
        view.status_label = Mock()
        view.status_label.style = {}
        view.generate_button = Mock()

        # Call validation
        view._validate_csv_file()

        # Verify status was updated correctly
        self.assertIn("3 rows", view.status_label.text)
        self.assertEqual(view.status_label.style["color"], STATUS_COLORS["ready"])
        self.assertTrue(view.generate_button.enabled)

    def test_validate_csv_file_invalid(self):
        """Test CSV validation with an invalid file."""
        self.model.csv_file_path = Path(self.temp_dir) / "nonexistent.csv"

        # Create view without UI mocking
        view = CSVReaderView.__new__(CSVReaderView)
        view._csvmodel = self.model
        view.status_label = Mock()
        view.status_label.style = {}
        view.generate_button = Mock()

        # Call validation
        view._validate_csv_file()

        # Verify status was updated correctly
        self.assertIn("Warning:", view.status_label.text)
        self.assertEqual(view.status_label.style["color"], STATUS_COLORS["warning"])
        self.assertFalse(view.generate_button.enabled)

    @patch("omni.sample.csv_reader.views.asyncio")
    def test_on_generate(self, mock_asyncio):
        """Test generate button click handling."""
        self.model.csv_file_path = self.test_csv_path

        # Create view without UI mocking
        view = CSVReaderView.__new__(CSVReaderView)
        view._csvmodel = self.model
        view.generate_button = Mock()
        view.progress_bar = Mock()
        view.progress_bar.model = Mock()
        view.status_label = Mock()
        view.status_label.style = {}

        # Mock the generate method
        self.model.generate = Mock()

        # Call generate
        view._on_generate()

        # Verify basic behavior
        self.assertFalse(view.generate_button.enabled)
        self.assertTrue(view.progress_bar.visible)
        mock_asyncio.ensure_future.assert_called_once()

    def test_on_progress_update(self):
        """Test progress update handling."""
        # Create view without UI mocking
        view = CSVReaderView.__new__(CSVReaderView)
        view.progress_bar = Mock()
        view.progress_bar.model = Mock()
        view.status_label = Mock()
        view.status_label.style = {}

        # Test progress update
        view._on_progress_update(0.5)

        # Verify progress was updated (check method was called with correct value)
        view.progress_bar.model.set_value.assert_called_with(0.5)
        self.assertIn("50%", view.status_label.text)

    def test_on_generation_complete_success(self):
        """Test generation completion handling with success."""
        # Create view without UI mocking
        view = CSVReaderView.__new__(CSVReaderView)
        view.generate_button = Mock()
        view.progress_bar = Mock()
        view.status_label = Mock()
        view.status_label.style = {}

        # Simulate completion with success
        success_message = "Generated 3 shapes from CSV file"
        view._on_generation_complete(True, success_message)

        # Verify UI state was restored
        self.assertTrue(view.generate_button.enabled)
        self.assertFalse(view.progress_bar.visible)
        self.assertIn("Success:", view.status_label.text)

    def test_on_generation_complete_error(self):
        """Test generation completion handling with error."""
        # Create view without UI mocking
        view = CSVReaderView.__new__(CSVReaderView)
        view.generate_button = Mock()
        view.progress_bar = Mock()
        view.status_label = Mock()
        view.status_label.style = {}

        # Simulate completion with error
        error_message = "Failed to read CSV file"
        view._on_generation_complete(False, error_message)

        # Verify UI state was restored
        self.assertTrue(view.generate_button.enabled)
        self.assertFalse(view.progress_bar.visible)
        self.assertIn("Error:", view.status_label.text)

    def test_destroy(self):
        """Test view cleanup on destroy."""
        # Create view without UI mocking
        view = CSVReaderView.__new__(CSVReaderView)
        mock_window = Mock()
        view._window = mock_window

        # Call destroy
        view.destroy()

        # Verify window was destroyed
        mock_window.destroy.assert_called_once()
        self.assertIsNone(view._window)

    def test_set_status_different_types(self):
        """Test setting status with different status types."""
        view = CSVReaderView.__new__(CSVReaderView)
        view.status_label = Mock()
        view.status_label.style = {}

        # Test all status types
        status_types = ["ready", "processing", "success", "warning", "error"]

        for status_type in status_types:
            view._set_status(f"Test {status_type}", status_type)
            self.assertEqual(view.status_label.text, f"Test {status_type}")
            self.assertEqual(view.status_label.style["color"], STATUS_COLORS[status_type])

    def test_on_progress_update_zero(self):
        """Test progress update with zero progress."""
        view = CSVReaderView.__new__(CSVReaderView)
        view.progress_bar = Mock()
        view.progress_bar.model = Mock()
        view.status_label = Mock()
        view.status_label.style = {}

        view._on_progress_update(0.0)

        view.progress_bar.model.set_value.assert_called_with(0.0)
        self.assertIn("0%", view.status_label.text)

    def test_on_progress_update_complete(self):
        """Test progress update with 100% completion."""
        view = CSVReaderView.__new__(CSVReaderView)
        view.progress_bar = Mock()
        view.progress_bar.model = Mock()
        view.status_label = Mock()
        view.status_label.style = {}

        view._on_progress_update(1.0)

        view.progress_bar.model.set_value.assert_called_with(1.0)
        self.assertIn("100%", view.status_label.text)

    def test_validate_csv_file_updates_button_state(self):
        """Test that CSV validation properly updates button enabled state."""
        self.model.csv_file_path = self.test_csv_path

        view = CSVReaderView.__new__(CSVReaderView)
        view._csvmodel = self.model
        view.status_label = Mock()
        view.status_label.style = {}
        view.generate_button = Mock()

        # Initially disabled
        view.generate_button.enabled = False

        # Validate valid CSV
        view._validate_csv_file()

        # Should be enabled now
        self.assertTrue(view.generate_button.enabled)

    def test_validate_csv_multiple_calls(self):
        """Test that multiple CSV validation calls work correctly."""
        view = CSVReaderView.__new__(CSVReaderView)
        view._csvmodel = self.model
        view.status_label = Mock()
        view.status_label.style = {}
        view.generate_button = Mock()

        # First validation - invalid file
        self.model.csv_file_path = Path(self.temp_dir) / "nonexistent.csv"
        view._validate_csv_file()
        self.assertFalse(view.generate_button.enabled)

        # Second validation - valid file
        self.model.csv_file_path = self.test_csv_path
        view._validate_csv_file()
        self.assertTrue(view.generate_button.enabled)
