# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Unit tests for utility functions like get_selection and duplicate_prims."""

from unittest.mock import Mock, patch

import omni.kit.test
from omni.sample.ui_scatter_tool.utils import duplicate_prims, get_selection
from pxr import Gf


class TestUtils(omni.kit.test.AsyncTestCase):
    """Unit tests for utility functions."""

    async def setUp(self):
        """Set up test fixtures before each test method."""
        pass

    @patch("omni.sample.ui_scatter_tool.utils.omni.usd.get_context")
    def test_get_selection(self, mock_get_context):
        """Test get_selection returns selected prim paths."""
        # Mock the USD context and selection
        mock_context = Mock()
        mock_selection = Mock()
        mock_selection.get_selected_prim_paths.return_value = ["/World/Cube", "/World/Sphere"]
        mock_context.get_selection.return_value = mock_selection
        mock_get_context.return_value = mock_context

        # Call get_selection
        result = get_selection()

        # Verify it returns the expected paths
        self.assertEqual(result, ["/World/Cube", "/World/Sphere"])
        mock_context.get_selection.assert_called_once()
        mock_selection.get_selected_prim_paths.assert_called_once()

    @patch("omni.sample.ui_scatter_tool.utils.omni.usd.get_context")
    def test_get_selection_empty(self, mock_get_context):
        """Test get_selection when nothing is selected."""
        mock_context = Mock()
        mock_selection = Mock()
        mock_selection.get_selected_prim_paths.return_value = []
        mock_context.get_selection.return_value = mock_selection
        mock_get_context.return_value = mock_context

        result = get_selection()

        self.assertEqual(result, [])

    @patch("omni.sample.ui_scatter_tool.utils.omni.kit.commands.execute")
    @patch("omni.sample.ui_scatter_tool.utils.omni.usd.get_context")
    def test_duplicate_prims_point_instancer_mode(self, mock_context, mock_execute):
        """Test duplicate_prims in PointInstancer mode."""
        transforms = [
            (Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(0, 0, 0)), 0),
            (Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(10, 0, 0)), 0),
        ]
        prim_names = ["/World/Cube"]
        target_path = "/World/Scatter"

        duplicate_prims(transforms, prim_names, target_path, mode="PointInstancer")

        # Verify ScatterCreatePointInstancer command was called
        mock_execute.assert_called_once_with(
            "ScatterCreatePointInstancer",
            path_to=target_path,
            transforms=transforms,
            prim_names=prim_names,
        )

    @patch("omni.sample.ui_scatter_tool.utils.omni.kit.undo.group")
    @patch("omni.sample.ui_scatter_tool.utils.omni.kit.commands.execute")
    @patch("omni.sample.ui_scatter_tool.utils.omni.usd.get_context")
    def test_duplicate_prims_copy_mode(self, mock_context, mock_execute, mock_undo_group):
        """Test duplicate_prims in Copy mode."""
        # Mock undo group as a context manager
        mock_undo_group.return_value.__enter__ = Mock(return_value=None)
        mock_undo_group.return_value.__exit__ = Mock(return_value=None)

        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(10, 0, 0))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Cube"]
        target_path = "/World/Scatter"

        duplicate_prims(transforms, prim_names, target_path, mode="Copy")

        # Verify commands were called (CreatePrim for group, CopyPrims, TransformPrim)
        self.assertGreater(mock_execute.call_count, 0)

    @patch("omni.sample.ui_scatter_tool.utils.omni.kit.undo.group")
    @patch("omni.sample.ui_scatter_tool.utils.omni.kit.commands.execute")
    @patch("omni.sample.ui_scatter_tool.utils.omni.usd.get_context")
    def test_duplicate_prims_reference_mode(self, mock_context, mock_execute, mock_undo_group):
        """Test duplicate_prims in Reference mode."""
        mock_undo_group.return_value.__enter__ = Mock(return_value=None)
        mock_undo_group.return_value.__exit__ = Mock(return_value=None)

        matrix1 = Gf.Matrix4d(1)
        matrix1.SetTranslate(Gf.Vec3d(5, 5, 0))

        transforms = [(matrix1, 0)]
        prim_names = ["/World/Sphere"]
        target_path = "/World/ScatterRef"

        duplicate_prims(transforms, prim_names, target_path, mode="Reference")

        # Verify commands were called
        self.assertGreater(mock_execute.call_count, 0)

    @patch("omni.sample.ui_scatter_tool.utils.omni.kit.undo.group")
    @patch("omni.sample.ui_scatter_tool.utils.omni.kit.commands.execute")
    @patch("omni.sample.ui_scatter_tool.utils.omni.usd.get_context")
    def test_duplicate_prims_invalid_mode(self, mock_context, mock_execute, mock_undo_group):
        """Test duplicate_prims with invalid mode."""
        mock_undo_group.return_value.__enter__ = Mock(return_value=None)
        mock_undo_group.return_value.__exit__ = Mock(return_value=None)

        matrix1 = Gf.Matrix4d(1)
        transforms = [(matrix1, 0)]
        prim_names = ["/World/Cube"]
        target_path = "/World/Scatter"

        # Invalid mode should be handled gracefully
        duplicate_prims(transforms, prim_names, target_path, mode="InvalidMode")

        # CreatePrim should still be called for the group
        mock_execute.assert_called()
