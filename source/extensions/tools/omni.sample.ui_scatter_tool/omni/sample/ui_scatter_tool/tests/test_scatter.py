# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Unit tests for the scatter function's matrix generation and positioning logic."""

import omni.kit.test
from omni.sample.ui_scatter_tool.scatter import scatter
from pxr import Gf


class TestScatterFunction(omni.kit.test.AsyncTestCase):
    """
    Simple unit tests for Scatter tool core functionality.
    Tests the scatter function and its matrix generation.
    """

    async def setUp(self):
        """Set up test fixtures before each test method."""
        pass

    async def test_scatter_basic_generation(self):
        """Test that scatter generates the expected number of matrices."""
        count = [2, 2, 1]  # 2x2x1 = 4 objects
        distance = [10.0, 10.0, 0.0]
        randomization = [0.0, 0.0, 0.0]  # No randomization for predictable results

        results = list(scatter(count, distance, randomization, seed=42))

        # Should generate 4 matrices (2x2x1)
        self.assertEqual(len(results), 4)

        # Each result should be a tuple of (matrix, id)
        for matrix, obj_id in results:
            self.assertIsInstance(matrix, Gf.Matrix4d)
            self.assertIsInstance(obj_id, int)

    async def test_scatter_positioning(self):
        """Test that scatter positions objects correctly."""
        count = [3, 1, 1]  # 3 objects in a line
        distance = [10.0, 0.0, 0.0]
        randomization = [0.0, 0.0, 0.0]  # No randomization

        results = list(scatter(count, distance, randomization, seed=42))

        # Should generate 3 matrices
        self.assertEqual(len(results), 3)

        # Check positions are spaced correctly
        positions = [matrix.ExtractTranslation() for matrix, _ in results]
        expected_x_positions = [-10.0, 0.0, 10.0]  # Centered around origin

        for i, pos in enumerate(positions):
            self.assertAlmostEqual(pos[0], expected_x_positions[i], places=5)
            self.assertEqual(pos[1], 0.0)  # Y should be 0
            self.assertEqual(pos[2], 0.0)  # Z should be 0

    async def test_scatter_with_randomization(self):
        """Test that scatter applies randomization correctly."""
        count = [2, 1, 1]
        distance = [10.0, 0.0, 0.0]
        randomization = [5.0, 0.0, 0.0]  # 5 units of randomization in X

        # Test with fixed seed for reproducible results
        results1 = list(scatter(count, distance, randomization, seed=42))
        results2 = list(scatter(count, distance, randomization, seed=42))

        # Same seed should produce same results
        self.assertEqual(len(results1), len(results2))
        for (m1, id1), (m2, id2) in zip(results1, results2):
            self.assertEqual(m1, m2)
            self.assertEqual(id1, id2)

    async def test_scatter_id_generation(self):
        """Test that scatter generates IDs within the specified range."""
        count = [2, 2, 1]
        distance = [10.0, 10.0, 0.0]
        randomization = [0.0, 0.0, 0.0]
        id_count = 3  # Should generate IDs 0, 1, or 2

        results = list(scatter(count, distance, randomization, id_count=id_count, seed=42))

        # Check all IDs are within range
        for _, obj_id in results:
            self.assertGreaterEqual(obj_id, 0)
            self.assertLess(obj_id, id_count)

    async def test_scatter_empty_count(self):
        """Test scatter behavior with zero count."""
        count = [0, 1, 1]
        distance = [10.0, 10.0, 10.0]
        randomization = [0.0, 0.0, 0.0]

        results = list(scatter(count, distance, randomization, seed=42))

        # Should generate no results
        self.assertEqual(len(results), 0)

    async def test_scatter_3d_grid(self):
        """Test scatter with 3D grid generation."""
        count = [2, 2, 2]  # 2x2x2 cube
        distance = [10.0, 10.0, 10.0]
        randomization = [0.0, 0.0, 0.0]

        results = list(scatter(count, distance, randomization, seed=42))

        # Should generate 8 objects (2x2x2)
        self.assertEqual(len(results), 8)

        # Check Z coordinates are also spread out
        positions = [matrix.ExtractTranslation() for matrix, _ in results]
        z_values = set(pos[2] for pos in positions)
        self.assertEqual(len(z_values), 2)  # Two different Z values

    async def test_scatter_large_grid(self):
        """Test scatter with larger grid."""
        count = [5, 5, 1]  # 5x5 grid
        distance = [10.0, 10.0, 0.0]
        randomization = [0.0, 0.0, 0.0]

        results = list(scatter(count, distance, randomization, seed=42))

        # Should generate 25 objects
        self.assertEqual(len(results), 25)

    async def test_scatter_different_seeds(self):
        """Test that different seeds produce different results."""
        count = [3, 3, 1]
        distance = [10.0, 10.0, 0.0]
        randomization = [5.0, 5.0, 0.0]

        results1 = list(scatter(count, distance, randomization, seed=42))
        results2 = list(scatter(count, distance, randomization, seed=123))

        # Same count but different positions
        self.assertEqual(len(results1), len(results2))

        # At least one position should be different
        positions1 = [m.ExtractTranslation() for m, _ in results1]
        positions2 = [m.ExtractTranslation() for m, _ in results2]

        different = False
        for p1, p2 in zip(positions1, positions2):
            if abs(p1[0] - p2[0]) > 0.001 or abs(p1[1] - p2[1]) > 0.001:
                different = True
                break

        self.assertTrue(different)

    async def test_scatter_negative_distance(self):
        """Test scatter with negative distance values."""
        count = [2, 2, 1]
        distance = [-10.0, -10.0, 0.0]
        randomization = [0.0, 0.0, 0.0]

        results = list(scatter(count, distance, randomization, seed=42))

        # Should still generate objects
        self.assertEqual(len(results), 4)

        # Positions should be spaced with negative distance
        positions = [matrix.ExtractTranslation() for matrix, _ in results]
        for pos in positions:
            self.assertIsNotNone(pos)

    async def test_scatter_zero_distance(self):
        """Test scatter with zero distance (all objects at same location)."""
        count = [3, 1, 1]
        distance = [0.0, 0.0, 0.0]
        randomization = [0.0, 0.0, 0.0]

        results = list(scatter(count, distance, randomization, seed=42))

        # Should generate 3 objects
        self.assertEqual(len(results), 3)

        # All should be at origin
        positions = [matrix.ExtractTranslation() for matrix, _ in results]
        for pos in positions:
            self.assertAlmostEqual(pos[0], 0.0, places=5)
            self.assertAlmostEqual(pos[1], 0.0, places=5)
            self.assertAlmostEqual(pos[2], 0.0, places=5)
