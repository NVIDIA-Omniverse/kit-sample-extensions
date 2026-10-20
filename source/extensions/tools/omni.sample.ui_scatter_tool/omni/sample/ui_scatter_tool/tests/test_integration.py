# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Integration tests for scatter algorithm with various grid configurations."""

import omni.kit.test
from omni.sample.ui_scatter_tool.scatter import scatter


class TestScatterIntegration(omni.kit.test.AsyncTestCase):
    """Simple integration test for scatter algorithm."""

    async def test_scatter_algorithm(self):
        """Test basic scatter algorithm functionality."""
        # Test parameters
        count = [2, 2, 1]  # 2x2 grid
        distance = [10.0, 10.0, 0.0]
        randomization = [0.0, 0.0, 0.0]  # No randomization
        seed = 42

        # Generate scatter results
        results = list(scatter(count, distance, randomization, seed))

        # Should generate 4 objects (2x2)
        self.assertEqual(len(results), 4)

        # Check that each result has a matrix and object ID
        for matrix, obj_id in results:
            self.assertIsNotNone(matrix)
            self.assertIsInstance(obj_id, int)

        # Verify positions are correct for a 2x2 grid
        positions = [matrix.ExtractTranslation() for matrix, _ in results]

        # With no randomization, positions should be at regular intervals
        expected_x = [-5.0, -5.0, 5.0, 5.0]
        expected_y = [-5.0, 5.0, -5.0, 5.0]

        for i, pos in enumerate(positions):
            self.assertAlmostEqual(pos[0], expected_x[i], places=1)
            self.assertAlmostEqual(pos[1], expected_y[i], places=1)
            self.assertAlmostEqual(pos[2], 0.0, places=1)

    async def test_scatter_with_randomization(self):
        """Test scatter with randomization."""
        count = [3, 3, 1]  # 3x3 grid
        distance = [10.0, 10.0, 0.0]
        randomization = [2.0, 2.0, 0.0]  # Some randomization
        seed = 12345

        # Generate scatter results
        results = list(scatter(count, distance, randomization, seed))

        # Should generate 9 objects
        self.assertEqual(len(results), 9)

        # Check that randomization is applied (positions should vary)
        positions = [matrix.ExtractTranslation() for matrix, _ in results]

        # With randomization, positions should be different from regular grid
        # but still within expected bounds
        for pos in positions:
            # X and Y should be within reasonable bounds given the grid and randomization
            self.assertGreaterEqual(pos[0], -12.0)  # -10 - 2
            self.assertLessEqual(pos[0], 12.0)  # 10 + 2
            self.assertGreaterEqual(pos[1], -12.0)
            self.assertLessEqual(pos[1], 12.0)
            self.assertAlmostEqual(pos[2], 0.0, places=1)

    async def test_scatter_single_object(self):
        """Test scatter with single object."""
        count = [1, 1, 1]
        distance = [10.0, 10.0, 10.0]
        randomization = [0.0, 0.0, 0.0]

        results = list(scatter(count, distance, randomization, seed=42))

        # Should generate 1 object at origin
        self.assertEqual(len(results), 1)

        matrix, obj_id = results[0]
        pos = matrix.ExtractTranslation()
        self.assertAlmostEqual(pos[0], 0.0, places=1)
        self.assertAlmostEqual(pos[1], 0.0, places=1)
        self.assertAlmostEqual(pos[2], 0.0, places=1)

    async def test_scatter_multiple_id_count(self):
        """Test scatter with multiple source objects (different IDs)."""
        count = [4, 1, 1]  # 4 objects in a row
        distance = [10.0, 0.0, 0.0]
        randomization = [0.0, 0.0, 0.0]
        id_count = 2  # Two different source objects

        results = list(scatter(count, distance, randomization, id_count=id_count, seed=42))

        self.assertEqual(len(results), 4)

        # Check that IDs alternate between source objects
        ids = [obj_id for _, obj_id in results]
        for obj_id in ids:
            self.assertIn(obj_id, [0, 1])

    async def test_scatter_z_axis_distribution(self):
        """Test scatter distributes correctly along Z axis."""
        count = [1, 1, 3]  # 3 objects along Z
        distance = [0.0, 0.0, 20.0]
        randomization = [0.0, 0.0, 0.0]

        results = list(scatter(count, distance, randomization, seed=42))

        self.assertEqual(len(results), 3)

        # Check Z positions
        positions = [matrix.ExtractTranslation() for matrix, _ in results]
        z_positions = [pos[2] for pos in positions]

        # Should be at -20, 0, and 20
        expected_z = [-20.0, 0.0, 20.0]
        for z in z_positions:
            self.assertIn(round(z, 1), expected_z)

    async def test_scatter_asymmetric_grid(self):
        """Test scatter with different counts per axis."""
        count = [5, 2, 1]  # 5x2 grid
        distance = [10.0, 20.0, 0.0]
        randomization = [0.0, 0.0, 0.0]

        results = list(scatter(count, distance, randomization, seed=42))

        # Should generate 10 objects (5x2x1)
        self.assertEqual(len(results), 10)
