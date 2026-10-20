# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Unit tests for ScatterCreatePointInstancerCommand.

This module contains comprehensive tests for the ScatterCreatePointInstancerCommand class,
which creates USD PointInstancer prims for efficient scattering of objects. Tests cover
command initialization, do/undo functionality, USD attribute validation, and edge cases.
"""

import omni.kit.test
import omni.usd
from omni.sample.ui_scatter_tool.commands import ScatterCreatePointInstancerCommand
from pxr import Gf, Sdf, UsdGeom


class TestScatterCreatePointInstancerCommand(omni.kit.test.AsyncTestCase):
    """Unit tests for ScatterCreatePointInstancerCommand."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a new USD stage for each test
        await omni.usd.get_context().new_stage_async()
        self.stage = omni.usd.get_context().get_stage()

        # Create some test prims to use as prototypes
        UsdGeom.Cube.Define(self.stage, "/World/Cube")
        UsdGeom.Sphere.Define(self.stage, "/World/Sphere")
        UsdGeom.Cone.Define(self.stage, "/World/Cone")

    async def tearDown(self):
        """Clean up after each test method."""
        await omni.usd.get_context().close_stage_async()

    async def test_command_initialization(self):
        """Test that command initializes with correct parameters."""
        # Create test data
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(10, 0, 0))

        matrix2 = Gf.Matrix4d(1)
        matrix2.SetTranslate(Gf.Vec3d(20, 0, 0))

        transforms = [(matrix1, 0), (matrix2, 0)]
        prim_names = ["/World/Cube"]
        path_to = "/World/PointInstancer"

        # Create command
        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        # Verify internal state
        self.assertEqual(cmd._path_to, path_to)
        self.assertEqual(len(cmd._positions), 2)
        self.assertEqual(len(cmd._proto_indices), 2)
        self.assertEqual(cmd._prim_names, prim_names)

    async def test_command_do_creates_point_instancer(self):
        """Test that do() creates a PointInstancer prim."""
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(10, 0, 0))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Cube"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        # Execute the command
        cmd.do()

        # Verify the PointInstancer was created
        prim = self.stage.GetPrimAtPath(path_to)
        self.assertTrue(prim.IsValid())
        self.assertTrue(prim.IsA(UsdGeom.PointInstancer))

    async def test_command_do_sets_prototypes(self):
        """Test that do() correctly sets prototype relationships."""
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(5, 5, 5))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Sphere"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Get the PointInstancer and check prototypes
        instancer = UsdGeom.PointInstancer(self.stage.GetPrimAtPath(path_to))
        prototypes_rel = instancer.GetPrototypesRel()
        targets = prototypes_rel.GetTargets()

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0], Sdf.Path("/World/Sphere"))

    async def test_command_do_sets_positions(self):
        """Test that do() correctly sets instance positions."""
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(10, 20, 30))

        matrix2 = Gf.Matrix4d(1)
        matrix2.SetTranslate(Gf.Vec3d(40, 50, 60))

        transforms = [(matrix1, 0), (matrix2, 0)]
        prim_names = ["/World/Cube"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Get the PointInstancer and check positions
        instancer = UsdGeom.PointInstancer(self.stage.GetPrimAtPath(path_to))
        positions = instancer.GetPositionsAttr().Get()

        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[0], Gf.Vec3f(10, 20, 30))
        self.assertEqual(positions[1], Gf.Vec3f(40, 50, 60))

    async def test_command_do_sets_proto_indices(self):
        """Test that do() correctly sets prototype indices."""
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(0, 0, 0))

        matrix2 = Gf.Matrix4d(1)
        matrix2.SetTranslate(Gf.Vec3d(10, 0, 0))

        matrix3 = Gf.Matrix4d(1)
        matrix3.SetTranslate(Gf.Vec3d(20, 0, 0))

        # Mix of different prototype indices
        transforms = [(matrix1, 0), (matrix2, 1), (matrix3, 0)]
        prim_names = ["/World/Cube", "/World/Sphere"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Get the PointInstancer and check proto indices
        instancer = UsdGeom.PointInstancer(self.stage.GetPrimAtPath(path_to))
        proto_indices = instancer.GetProtoIndicesAttr().Get()

        self.assertEqual(len(proto_indices), 3)
        self.assertEqual(proto_indices[0], 0)
        self.assertEqual(proto_indices[1], 1)
        self.assertEqual(proto_indices[2], 0)

    async def test_command_with_multiple_prototypes(self):
        """Test command with multiple prototype prims."""
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(0, 0, 0))

        matrix2 = Gf.Matrix4d(1)
        matrix2.SetTranslate(Gf.Vec3d(10, 0, 0))

        matrix3 = Gf.Matrix4d(1)
        matrix3.SetTranslate(Gf.Vec3d(20, 0, 0))

        transforms = [(matrix1, 0), (matrix2, 1), (matrix3, 2)]
        prim_names = ["/World/Cube", "/World/Sphere", "/World/Cone"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Verify all prototypes are set
        instancer = UsdGeom.PointInstancer(self.stage.GetPrimAtPath(path_to))
        prototypes_rel = instancer.GetPrototypesRel()
        targets = prototypes_rel.GetTargets()

        self.assertEqual(len(targets), 3)
        self.assertIn(Sdf.Path("/World/Cube"), targets)
        self.assertIn(Sdf.Path("/World/Sphere"), targets)
        self.assertIn(Sdf.Path("/World/Cone"), targets)

    async def test_command_undo(self):
        """Test that undo() removes the created PointInstancer."""
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(10, 0, 0))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Cube"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        # Execute the command
        cmd.do()

        # Verify it was created
        prim = self.stage.GetPrimAtPath(path_to)
        self.assertTrue(prim.IsValid())

        # Undo the command
        cmd.undo()

        # Verify it was removed
        prim = self.stage.GetPrimAtPath(path_to)
        self.assertFalse(prim.IsValid())

    async def test_command_do_undo_cycle(self):
        """Test multiple do/undo cycles."""
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(5, 5, 5))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Sphere"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        # First cycle
        cmd.do()
        self.assertTrue(self.stage.GetPrimAtPath(path_to).IsValid())

        cmd.undo()
        self.assertFalse(self.stage.GetPrimAtPath(path_to).IsValid())

        # Second cycle
        cmd.do()
        self.assertTrue(self.stage.GetPrimAtPath(path_to).IsValid())

        cmd.undo()
        self.assertFalse(self.stage.GetPrimAtPath(path_to).IsValid())

    async def test_command_with_large_instance_count(self):
        """Test command with many instances."""
        # Create 100 instances
        transforms = []
        for i in range(100):
            matrix = Gf.Matrix4d(1)
            matrix.SetTranslate(Gf.Vec3d(i * 10, 0, 0))
            transforms.append((matrix, 0))

        prim_names = ["/World/Cube"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Verify all instances are created
        instancer = UsdGeom.PointInstancer(self.stage.GetPrimAtPath(path_to))
        positions = instancer.GetPositionsAttr().Get()
        proto_indices = instancer.GetProtoIndicesAttr().Get()

        self.assertEqual(len(positions), 100)
        self.assertEqual(len(proto_indices), 100)

    async def test_command_with_nested_path(self):
        """Test command with nested prim path."""
        # Create parent structure
        UsdGeom.Xform.Define(self.stage, "/World/ScatterGroup")

        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(10, 0, 0))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Cube"]
        path_to = "/World/ScatterGroup/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Verify nested prim was created
        prim = self.stage.GetPrimAtPath(path_to)
        self.assertTrue(prim.IsValid())
        self.assertTrue(prim.IsA(UsdGeom.PointInstancer))

    async def test_command_with_single_instance(self):
        """Test command with just one instance."""
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(0, 0, 0))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Cube"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Verify single instance
        instancer = UsdGeom.PointInstancer(self.stage.GetPrimAtPath(path_to))
        positions = instancer.GetPositionsAttr().Get()

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0], Gf.Vec3f(0, 0, 0))

    async def test_command_with_identity_matrices(self):
        """Test command with identity transform matrices (all at origin)."""
        matrix1 = Gf.Matrix4d(1)
        matrix2 = Gf.Matrix4d(1)
        matrix3 = Gf.Matrix4d(1)

        transforms = [(matrix1, 0), (matrix2, 0), (matrix3, 0)]
        prim_names = ["/World/Sphere"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Verify all instances are at origin
        instancer = UsdGeom.PointInstancer(self.stage.GetPrimAtPath(path_to))
        positions = instancer.GetPositionsAttr().Get()

        self.assertEqual(len(positions), 3)
        for pos in positions:
            self.assertEqual(pos, Gf.Vec3f(0, 0, 0))

    async def test_command_preserves_prim_names(self):
        """Test that command preserves the original prim names list."""
        matrix1 = Gf.Matrix4d(1)
        transforms = [(matrix1, 0)]
        prim_names = ["/World/Cube"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        # Modify the original list
        prim_names.append("/World/Sphere")

        # Command should have a copy, not affected by changes
        self.assertEqual(len(cmd._prim_names), 1)
        self.assertEqual(cmd._prim_names[0], "/World/Cube")

    async def test_command_extracts_translations_correctly(self):
        """Test that command correctly extracts translations from complex matrices."""
        # Create a matrix with rotation and translation
        matrix1 = Gf.Matrix4d(1)
        matrix1.SetRotate(Gf.Rotation(Gf.Vec3d(0, 0, 1), 45))  # 45 degree rotation
        matrix1.SetTranslate(Gf.Vec3d(100, 200, 300))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Cube"]
        path_to = "/World/PointInstancer"

        cmd = ScatterCreatePointInstancerCommand(
            path_to=path_to, transforms=transforms, prim_names=prim_names, stage=self.stage
        )

        cmd.do()

        # Verify only translation is used (PointInstancer uses positions)
        instancer = UsdGeom.PointInstancer(self.stage.GetPrimAtPath(path_to))
        positions = instancer.GetPositionsAttr().Get()

        self.assertEqual(len(positions), 1)
        # Should extract translation component
        self.assertAlmostEqual(positions[0][0], 100, places=5)
        self.assertAlmostEqual(positions[0][1], 200, places=5)
        self.assertAlmostEqual(positions[0][2], 300, places=5)
