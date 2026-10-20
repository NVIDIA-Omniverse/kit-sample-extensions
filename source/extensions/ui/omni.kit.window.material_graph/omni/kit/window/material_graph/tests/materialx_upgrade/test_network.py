# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""UsdShade network traversal coverage for MaterialX upgrades."""

from pxr import Sdf, Usd, UsdShade

from ...scripts.materialx_upgrade import IdentifierChange, upgrade_materialx_identifiers
from .base import MaterialXUpgradeTestCase


class TestMaterialXUpgradeNetwork(MaterialXUpgradeTestCase):
    """Verify traversal, identity mapping, cycles, and render contexts."""

    async def test_disconnected_nodes_and_duplicate_leaf_names_are_upgraded(self) -> None:
        """Upgrade disconnected nodes while preserving exact paths for duplicate names."""
        stage = Usd.Stage.CreateInMemory()
        material, surface = self.create_material(stage)
        connected = self.add_normalmap(stage, surface, "/Material/A/Normal")
        disconnected = UsdShade.Shader.Define(stage, "/Material/B/Normal")
        disconnected.CreateIdAttr("ND_normalmap")

        result = upgrade_materialx_identifiers(material.GetPrim())

        expected_changes = [
            IdentifierChange(str(connected.GetPath()), "ND_normalmap", "ND_normalmap_float"),
            IdentifierChange(str(disconnected.GetPath()), "ND_normalmap", "ND_normalmap_float"),
        ]
        self.assert_identifier_upgrade_or_host_fallback(result, expected_changes)
        self.assertIn('name="Normal"', result.pre_upgrade_xml)
        self.assertIn('name="Normal2"', result.pre_upgrade_xml)

    async def test_nodegraph_surface_indirection_is_resolved(self) -> None:
        """Follow a NodeGraph output from the material to its concrete shader."""
        stage = Usd.Stage.CreateInMemory()
        material = UsdShade.Material.Define(stage, "/Material")
        surface = UsdShade.Shader.Define(stage, "/Material/Surface")
        surface.CreateIdAttr("ND_standard_surface_surfaceshader")
        surface_output = surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        node_graph = UsdShade.NodeGraph.Define(stage, "/Material/NodeGraph")
        graph_output = node_graph.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        graph_output.ConnectToSource(surface_output)
        material.CreateSurfaceOutput("mtlx").ConnectToSource(graph_output)
        self.add_normalmap(stage, surface, "/Material/NormalMap")

        result = upgrade_materialx_identifiers(material.GetPrim())

        self.assert_identifier_upgrade_or_host_fallback(
            result,
            [IdentifierChange("/Material/NormalMap", "ND_normalmap", "ND_normalmap_float")],
        )

    async def test_nodegraph_cycle_terminates_with_diagnostic(self) -> None:
        """Stop safely when NodeGraph output indirection contains a cycle."""
        stage = Usd.Stage.CreateInMemory()
        material = UsdShade.Material.Define(stage, "/Material")
        node_graph = UsdShade.NodeGraph.Define(stage, "/Material/NodeGraph")
        graph_output = node_graph.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        self.assertTrue(graph_output.ConnectToSource(graph_output))
        material.CreateSurfaceOutput("mtlx").ConnectToSource(graph_output)

        result = upgrade_materialx_identifiers(material.GetPrim())

        self.assertFalse(result.upgrade_attempted)
        self.assertFalse(result.any_changes)
        self.assertIn("Empty material network or no surface terminal", result.diagnostics)

    async def test_requested_context_ignores_other_surface_terminal(self) -> None:
        """Traverse only the surface terminal for the requested render context."""
        stage = Usd.Stage.CreateInMemory()
        material, mtlx_surface = self.create_material(stage, context="mtlx")
        self.add_normalmap(stage, mtlx_surface, "/Material/NormalMap")
        mdl_surface = UsdShade.Shader.Define(stage, "/Material/MdlSurface")
        mdl_surface.CreateIdAttr("mdl::surface")
        mdl_output = mdl_surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("mdl").ConnectToSource(mdl_output)

        result = upgrade_materialx_identifiers(material.GetPrim(), "mtlx")

        self.assert_identifier_upgrade_or_host_fallback(
            result,
            [IdentifierChange("/Material/NormalMap", "ND_normalmap", "ND_normalmap_float")],
        )
