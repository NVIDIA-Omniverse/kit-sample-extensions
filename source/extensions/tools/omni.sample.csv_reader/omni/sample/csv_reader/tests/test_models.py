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

import omni.kit.test
from omni.sample.csv_reader.models import CSVReaderModel


class TestCSVReaderModel(omni.kit.test.AsyncTestCase):
    """Unit tests for CSVReaderModel class."""

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
        # Clean up any remaining files in temp directory
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir)

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

    def test_initialization(self):
        """Test that the model initializes with correct default values."""
        model = CSVReaderModel()

        self.assertEqual(model.root_path, "/World")
        self.assertEqual(model.scale_factor, 100.0)
        self.assertEqual(model.max_elements, 5000)
        self.assertFalse(model.group_by_cluster)

    def test_shape_changed(self):
        """Test shape selection change functionality."""
        self.model.shape_changed(1)  # Change to sphere
        self.assertEqual(self.model.shape_file_name, "BasicSphereAsRef.usda")

        self.model.shape_changed(0)  # Change back to cube
        self.assertEqual(self.model.shape_file_name, "BasicCubeAsRef.usda")

    def test_group_by_cluster_changed(self):
        """Test cluster grouping toggle functionality."""
        self.assertFalse(self.model.group_by_cluster)

        self.model.group_by_cluster_changed(True)
        self.assertTrue(self.model.group_by_cluster)

        self.model.group_by_cluster_changed(False)
        self.assertFalse(self.model.group_by_cluster)

    def test_count_csv_rows(self):
        """Test CSV row counting."""
        self.model.csv_file_path = self.test_csv_path
        row_count = self.model._count_csv_rows()
        self.assertEqual(row_count, 3)  # 3 data rows (excluding header)

    def test_validate_current_csv_valid(self):
        """Test CSV validation with a valid file."""
        self.model.csv_file_path = self.test_csv_path

        success, message, row_count = self.model.validate_current_csv()

        self.assertTrue(success)
        self.assertIn("3 rows", message)
        self.assertEqual(row_count, 3)

    def test_validate_current_csv_invalid(self):
        """Test CSV validation with an invalid file."""
        nonexistent_path = Path(self.temp_dir) / "nonexistent.csv"
        self.model.csv_file_path = nonexistent_path

        success, message, row_count = self.model.validate_current_csv()

        self.assertFalse(success)
        self.assertIn("not found", message)
        self.assertEqual(row_count, 0)

    def test_validate_current_csv_wrong_format(self):
        """Test CSV validation with wrong format."""
        # Create CSV with insufficient columns
        invalid_csv = Path(self.temp_dir) / "invalid.csv"
        with open(invalid_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["name", "x", "y"])  # Only 3 columns
            writer.writerow(["point1", "1.0", "2.0"])

        self.model.csv_file_path = invalid_csv

        success, message, row_count = self.model.validate_current_csv()

        self.assertFalse(success)
        self.assertIn("5 columns", message)
        self.assertEqual(row_count, 0)

    async def test_generate_with_callbacks(self):
        """Test the async generate method with progress tracking."""
        # Track progress and completion
        progress_values = []
        completion_result = None

        def progress_callback(progress):
            progress_values.append(progress)

        def completion_callback(success, message):
            nonlocal completion_result
            completion_result = (success, message)

        # Set up model with test CSV file
        self.model.csv_file_path = self.test_csv_path

        # Call the async method
        await self.model.generate(progress_callback=progress_callback, completion_callback=completion_callback)

        # Verify results - in test environment, no stage is available
        self.assertIsNotNone(completion_result)
        self.assertFalse(completion_result[0])  # expected to fail due to no stage
        self.assertIn("No stage available", completion_result[1])

    async def test_generate_with_invalid_csv(self):
        """Test error handling with invalid CSV file."""
        # Set invalid CSV path
        self.model.csv_file_path = Path(self.temp_dir) / "nonexistent.csv"

        completion_result = None

        def completion_callback(success, message):
            nonlocal completion_result
            completion_result = (success, message)

        # Call the async method
        await self.model.generate(completion_callback=completion_callback)

        # Verify error was handled - in test environment, no stage is available first
        self.assertIsNotNone(completion_result)
        self.assertFalse(completion_result[0])  # failed
        self.assertIn("No stage available", completion_result[1])

    def test_on_filter_item_valid_csv(self):
        """Test file filtering accepts CSV files."""
        result = self.model._on_filter_item("test.csv", "CSV", ".csv")
        self.assertTrue(result)

    def test_on_filter_item_invalid_extension(self):
        """Test file filtering rejects non-CSV files."""
        result = self.model._on_filter_item("test.txt", "CSV", ".csv")
        self.assertFalse(result)

    def test_on_filter_item_empty_filename(self):
        """Test file filtering with empty filename."""
        result = self.model._on_filter_item("", "CSV", ".csv")
        self.assertTrue(result)  # Empty filename returns True

    def test_on_filter_item_multiple_extensions(self):
        """Test file filtering with file having multiple extensions."""
        result = self.model._on_filter_item("data.backup.csv", "CSV", ".csv")
        self.assertTrue(result)

    def test_count_csv_rows_with_max_elements(self):
        """Test CSV row counting respects max_elements limit."""
        # Create a larger CSV file
        large_csv = Path(self.temp_dir) / "large.csv"
        with open(large_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["name", "x", "y", "z", "cluster"])
            for i in range(100):
                writer.writerow([f"point{i}", str(i), str(i), str(i), "0"])

        self.model.csv_file_path = large_csv
        self.model.max_elements = 50

        row_count = self.model._count_csv_rows()
        self.assertEqual(row_count, 50)  # Should be limited to max_elements

    def test_count_csv_rows_file_not_found(self):
        """Test CSV row counting with non-existent file."""
        self.model.csv_file_path = Path(self.temp_dir) / "nonexistent.csv"
        row_count = self.model._count_csv_rows()
        self.assertEqual(row_count, 0)

    def test_validate_csv_empty_file(self):
        """Test CSV validation with empty file."""
        empty_csv = Path(self.temp_dir) / "empty.csv"
        with open(empty_csv, "w", newline="") as csvfile:
            pass  # Create empty file

        self.model.csv_file_path = empty_csv
        success, message, row_count = self.model.validate_current_csv()

        self.assertFalse(success)
        self.assertIn("empty", message.lower())
        self.assertEqual(row_count, 0)

    def test_validate_csv_only_header(self):
        """Test CSV validation with only header row."""
        header_only_csv = Path(self.temp_dir) / "header_only.csv"
        with open(header_only_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["name", "x", "y", "z", "cluster"])

        self.model.csv_file_path = header_only_csv
        success, message, row_count = self.model.validate_current_csv()

        self.assertFalse(success)
        self.assertIn("empty", message.lower())
        self.assertEqual(row_count, 0)

    def test_validate_csv_invalid_numeric_data(self):
        """Test CSV validation with non-numeric coordinates."""
        invalid_csv = Path(self.temp_dir) / "invalid_nums.csv"
        with open(invalid_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["name", "x", "y", "z", "cluster"])
            writer.writerow(["point1", "not_a_number", "2.0", "3.0", "0"])

        self.model.csv_file_path = invalid_csv
        success, message, row_count = self.model.validate_current_csv()

        self.assertFalse(success)
        self.assertIn("invalid data format", message.lower())
        self.assertEqual(row_count, 0)

    def test_validate_csv_with_max_elements_warning(self):
        """Test CSV validation shows warning when file exceeds max_elements."""
        large_csv = Path(self.temp_dir) / "large.csv"
        with open(large_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["name", "x", "y", "z", "cluster"])
            for i in range(100):
                writer.writerow([f"point{i}", str(i), str(i), str(i), "0"])

        self.model.csv_file_path = large_csv
        self.model.max_elements = 50

        success, message, row_count = self.model.validate_current_csv()

        self.assertTrue(success)
        self.assertIn("Will process 50 of 100 rows", message)
        self.assertEqual(row_count, 50)

    def test_shape_changed_out_of_range(self):
        """Test shape_changed with out of range index handles gracefully."""
        # This should handle gracefully or raise appropriate error
        try:
            self.model.shape_changed(999)
            # If it doesn't raise an error, it should default to some shape
            self.assertIsNotNone(self.model.shape_file_name)
        except (IndexError, KeyError):
            # Expected behavior for out of range
            pass

    def test_set_ui_callbacks(self):
        """Test setting UI callbacks."""
        callback_called = False

        def test_callback():
            nonlocal callback_called
            callback_called = True

        self.model.set_ui_callbacks(test_callback)
        self.assertEqual(self.model._validation_callback, test_callback)

        # Verify callback can be called
        if self.model._validation_callback:
            self.model._validation_callback()
        self.assertTrue(callback_called)

    def test_on_click_open_with_dirname(self):
        """Test file selection callback with directory and filename."""
        validation_called = False

        def validation_callback():
            nonlocal validation_called
            validation_called = True

        self.model.set_ui_callbacks(validation_callback)

        # Mock the csv_field_model
        from unittest.mock import Mock

        self.model.csv_field_model = Mock()

        # Call with directory and filename
        self.model._on_click_open("test.csv", "/data/", None)

        self.assertEqual(self.model.csv_file_path, "/data/test.csv")
        self.model.csv_field_model.set_value.assert_called_with("/data/test.csv")
        self.assertTrue(validation_called)

    def test_on_click_open_without_dirname(self):
        """Test file selection callback with full path only."""
        from unittest.mock import Mock

        self.model.csv_field_model = Mock()
        self.model.set_ui_callbacks(lambda: None)

        # Call with full path, no dirname
        self.model._on_click_open("/full/path/to/test.csv", "", None)

        self.assertEqual(self.model.csv_file_path, "/full/path/to/test.csv")
        self.model.csv_field_model.set_value.assert_called_with("/full/path/to/test.csv")

    def test_on_click_open_empty_filename(self):
        """Test file selection callback with empty filename."""
        original_path = self.model.csv_file_path

        # Call with empty filename
        self.model._on_click_open("   ", "/data/", None)

        # Path should not change
        self.assertEqual(self.model.csv_file_path, original_path)

    def test_csv_with_negative_coordinates(self):
        """Test CSV validation with negative coordinates."""
        negative_csv = Path(self.temp_dir) / "negative.csv"
        with open(negative_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["name", "x", "y", "z", "cluster"])
            writer.writerow(["point1", "-10.5", "-20.3", "-30.1", "0"])

        self.model.csv_file_path = negative_csv
        success, message, row_count = self.model.validate_current_csv()

        self.assertTrue(success)
        self.assertEqual(row_count, 1)
