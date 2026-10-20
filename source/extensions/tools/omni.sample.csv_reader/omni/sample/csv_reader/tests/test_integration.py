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


class TestCSVReaderIntegration(omni.kit.test.AsyncTestCase):
    """Simple integration test for CSV Reader workflow."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_csv_path = Path(self.temp_dir) / "test.csv"

        # Create a test CSV file
        self._create_test_csv()

    async def tearDown(self):
        """Clean up after each test method."""
        if self.test_csv_path.exists():
            self.test_csv_path.unlink()
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    def _create_test_csv(self):
        """Create a simple test CSV file."""
        rows = [
            ["name", "x", "y", "z", "cluster"],
            ["point1", "1.0", "2.0", "3.0", "0"],
            ["point2", "4.0", "5.0", "6.0", "1"],
            ["point3", "7.0", "8.0", "9.0", "2"],
        ]

        with open(self.test_csv_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

    async def test_csv_validation(self):
        """Test that CSV file validation works correctly."""
        model = CSVReaderModel()
        model.csv_file_path = self.test_csv_path

        # Validate the CSV file
        success, message, row_count = model.validate_current_csv()

        # Check validation results
        self.assertTrue(success)
        self.assertIn("3 rows", message)
        self.assertEqual(row_count, 3)

    async def test_invalid_csv_path(self):
        """Test validation with non-existent file."""
        model = CSVReaderModel()
        model.csv_file_path = Path(self.temp_dir) / "nonexistent.csv"

        # Validate the non-existent file
        success, message, row_count = model.validate_current_csv()

        # Check validation results
        self.assertFalse(success)
        self.assertIn("not found", message)
        self.assertEqual(row_count, 0)

    async def test_model_defaults(self):
        """Test that model initializes with correct defaults."""
        model = CSVReaderModel()

        # Check default values
        self.assertEqual(model.root_path, "/World")
        self.assertEqual(model.scale_factor, 100.0)
        self.assertEqual(model.max_elements, 5000)
        self.assertFalse(model.group_by_cluster)

    async def test_csv_with_multiple_clusters(self):
        """Test CSV validation with multiple cluster values."""
        multi_cluster_csv = Path(self.temp_dir) / "multi_cluster.csv"
        rows = [
            ["name", "x", "y", "z", "cluster"],
            ["point1", "1.0", "2.0", "3.0", "0"],
            ["point2", "4.0", "5.0", "6.0", "1"],
            ["point3", "7.0", "8.0", "9.0", "2"],
            ["point4", "10.0", "11.0", "12.0", "0"],
            ["point5", "13.0", "14.0", "15.0", "1"],
        ]

        with open(multi_cluster_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

        model = CSVReaderModel()
        model.csv_file_path = multi_cluster_csv

        success, message, row_count = model.validate_current_csv()

        self.assertTrue(success)
        self.assertEqual(row_count, 5)
        self.assertIn("5 rows", message)

    async def test_shape_selection_workflow(self):
        """Test complete workflow of changing shapes."""
        model = CSVReaderModel()

        # Test cube selection (default)
        self.assertIn("Cube", model.shape_file_name)

        # Change to sphere
        model.shape_changed(1)
        self.assertIn("Sphere", model.shape_file_name)

        # Change back to cube
        model.shape_changed(0)
        self.assertIn("Cube", model.shape_file_name)

    async def test_cluster_grouping_workflow(self):
        """Test complete workflow of cluster grouping toggle."""
        model = CSVReaderModel()

        # Default should be disabled
        self.assertFalse(model.group_by_cluster)

        # Enable cluster grouping
        model.group_by_cluster_changed(True)
        self.assertTrue(model.group_by_cluster)

        # Disable cluster grouping
        model.group_by_cluster_changed(False)
        self.assertFalse(model.group_by_cluster)

    async def test_csv_with_floating_point_precision(self):
        """Test CSV with high precision floating point numbers."""
        precision_csv = Path(self.temp_dir) / "precision.csv"
        rows = [
            ["name", "x", "y", "z", "cluster"],
            ["point1", "1.123456789", "2.987654321", "3.555555555", "0"],
            ["point2", "0.000001", "0.000002", "0.000003", "1"],
        ]

        with open(precision_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

        model = CSVReaderModel()
        model.csv_file_path = precision_csv

        success, message, row_count = model.validate_current_csv()

        self.assertTrue(success)
        self.assertEqual(row_count, 2)

    async def test_csv_with_large_coordinates(self):
        """Test CSV with very large coordinate values."""
        large_csv = Path(self.temp_dir) / "large_coords.csv"
        rows = [
            ["name", "x", "y", "z", "cluster"],
            ["point1", "1000000.0", "2000000.0", "3000000.0", "0"],
            ["point2", "-1000000.0", "-2000000.0", "-3000000.0", "1"],
        ]

        with open(large_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

        model = CSVReaderModel()
        model.csv_file_path = large_csv

        success, message, row_count = model.validate_current_csv()

        self.assertTrue(success)
        self.assertEqual(row_count, 2)

    async def test_model_with_custom_max_elements(self):
        """Test model behavior with custom max_elements setting."""
        model = CSVReaderModel()
        model.max_elements = 2
        model.csv_file_path = self.test_csv_path

        # Validate - should limit to max_elements
        success, message, row_count = model.validate_current_csv()

        self.assertTrue(success)
        self.assertEqual(row_count, 2)  # Limited to max_elements
        self.assertIn("Will process 2 of 3 rows", message)
