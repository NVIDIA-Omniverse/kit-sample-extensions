# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest.mock as mock

import omni.kit.test
from omni.asset_validator.core import LayerId, PrimId, PropertyId, StageId
from omni.asset_validator.ui import IdentifierLabel
from omni.ui import HStack, Window
from pxr import Sdf


class IdentifierLabelTest(omni.kit.test.AsyncTestCase):
    def setUp(self):
        self.widget = IdentifierLabel(None)

    def test_format_prim_id(self):
        # Given
        prim_id = mock.MagicMock(spec=PrimId)
        prim_id.path = Sdf.Path("/World/Mesh")
        # When / Then
        self.assertEqual(self.widget._format(prim_id), "/World/Mesh")

    def test_format_property_id(self):
        # Given
        prop_id = mock.MagicMock(spec=PropertyId)
        prop_id.path = Sdf.Path("/World/Mesh.points")
        # When / Then
        self.assertEqual(self.widget._format(prop_id), "/World/Mesh.points")

    def test_format_layer_id(self):
        # Given
        layer_id = mock.MagicMock(spec=LayerId)
        layer_id.identifier = "root.usda"
        # When / Then
        self.assertEqual(self.widget._format(layer_id), "@root.usda@")

    def test_format_stage_id(self):
        # Given
        stage_id = mock.MagicMock(spec=StageId)
        stage_id.identifier = "scene.usd"
        # When / Then
        self.assertEqual(self.widget._format(stage_id), "@scene.usd@")

    def test_format_fallback(self):
        # Given
        identifier = mock.MagicMock()
        identifier.as_str.return_value = "fallback"
        # When / Then
        self.assertEqual(self.widget._format(identifier), "fallback")

    async def test_build_none(self):
        # When / Then — should not raise
        window = Window(__name__)
        with window.frame:
            with HStack():
                IdentifierLabel(None)

    async def test_build_single(self):
        # Given
        prim_id = mock.MagicMock(spec=PrimId)
        prim_id.path = Sdf.Path("/World")
        prim_id.variant_selection_path.pathString = "/World"
        # When / Then — should not raise
        window = Window(__name__)
        with window.frame:
            with HStack():
                IdentifierLabel(prim_id)

    async def test_build_multiple(self):
        # Given
        prim_id1 = mock.MagicMock(spec=PrimId)
        prim_id1.path = Sdf.Path("/World/A")
        prim_id1.variant_selection_path.pathString = "/World/A"
        prim_id2 = mock.MagicMock(spec=PrimId)
        prim_id2.path = Sdf.Path("/World/B")
        prim_id2.variant_selection_path.pathString = "/World/B"
        # When / Then — should not raise
        window = Window(__name__)
        with window.frame:
            with HStack():
                IdentifierLabel((prim_id1, prim_id2))
