# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Contract and failure-path coverage for MaterialX upgrades."""

from unittest.mock import patch

from pxr import Sdf, Usd, UsdShade

from ...scripts.materialx_upgrade import IdentifierChange, UpgradeResult, upgrade_materialx_identifiers
from ...scripts.materialx_upgrade.models import MaterialXNodeSpec, NetworkNode
from ...scripts.materialx_upgrade.upgrade import _record_identifier_changes
from .base import MaterialXUpgradeTestCase

_UPGRADE_MODULE = "omni.kit.window.material_graph.scripts.materialx_upgrade.upgrade"


class TestMaterialXUpgradeContract(MaterialXUpgradeTestCase):
    """Verify public result behavior and guarded failure paths."""

    async def test_result_contract(self) -> None:
        """Report whether a result contains at least one identifier change."""
        change = IdentifierChange("/Material/Node", "ND_old", "ND_new")
        result = UpgradeResult(changes=[change])

        self.assertTrue(result.any_changes)
        self.assertEqual(change.prim_path, "/Material/Node")
        self.assertEqual(change.old_identifier, "ND_old")
        self.assertEqual(change.new_identifier, "ND_new")

    async def test_invalid_and_non_material_prims_return_diagnostics(self) -> None:
        """Reject invalid and non-material prims without attempting an upgrade."""
        invalid_result = upgrade_materialx_identifiers(Usd.Prim())
        self.assertIn("Invalid material prim", invalid_result.diagnostics)

        stage = Usd.Stage.CreateInMemory()
        non_material = stage.DefinePrim("/NotMaterial", "Xform")
        non_material_result = upgrade_materialx_identifiers(non_material)
        self.assertIn("Prim is not a UsdShadeMaterial", non_material_result.diagnostics)

    async def test_material_without_surface_terminal_is_not_upgraded(self) -> None:
        """Return a diagnostic when the requested surface terminal is absent."""
        stage = Usd.Stage.CreateInMemory()
        material = UsdShade.Material.Define(stage, "/Material")

        result = upgrade_materialx_identifiers(material.GetPrim())

        self.assertFalse(result.upgrade_attempted)
        self.assertFalse(result.any_changes)
        self.assertIn("Empty material network or no surface terminal", result.diagnostics)

    async def test_resolving_identifiers_skip_port_only_materialx_migrations(self) -> None:
        """Preserve the identifier-only behavior of the Material Graph 2.2.0 upgrader."""
        stage = Usd.Stage.CreateInMemory()
        material, _surface = self.create_material(stage)
        atan2 = UsdShade.Shader.Define(stage, "/Material/Atan2")
        atan2.CreateIdAttr("ND_atan2_float")
        atan2.CreateInput("in1", Sdf.ValueTypeNames.Float).Set(1.0)
        atan2.CreateInput("in2", Sdf.ValueTypeNames.Float).Set(2.0)

        result = upgrade_materialx_identifiers(material.GetPrim())

        self.assertFalse(result.upgrade_attempted)
        self.assertFalse(result.any_changes)
        self.assertEqual(result.pre_upgrade_xml, "")
        self.assertTrue(atan2.GetInput("in1"))
        self.assertTrue(atan2.GetInput("in2"))
        self.assertFalse(atan2.GetInput("iny"))
        self.assertFalse(atan2.GetInput("inx"))
        self.assertIn(
            "All node identifiers resolve in SDR; no identifier repair needed",
            result.diagnostics,
        )

    async def test_nvbug_6575961_preview_surface_with_authored_input_returns_safely(self) -> None:
        """Do not invoke the vulnerable HdMtlx path for a cross-context terminal with inputs."""
        stage = Usd.Stage.CreateInMemory()
        material = UsdShade.Material.Define(stage, "/World/Looks/OpenPBR_Base")
        preview_surface = UsdShade.Shader.Define(stage, "/World/Looks/OpenPBR_Base/UsdPreviewSurface")
        preview_surface.CreateIdAttr("UsdPreviewSurface")
        diffuse_color = preview_surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
        diffuse_color.Set((0.18, 0.18, 0.18))
        surface_output = preview_surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("mtlx").ConnectToSource(surface_output)

        result = upgrade_materialx_identifiers(material.GetPrim(), "mtlx")

        self.assertFalse(result.upgrade_attempted)
        self.assertFalse(result.any_changes)
        self.assertFalse(result.unresolved_prims)
        self.assertEqual(
            result.diagnostics,
            ["All node identifiers resolve in SDR; no identifier repair needed"],
        )
        self.assertEqual(preview_surface.GetIdAttr().Get(), "UsdPreviewSurface")
        self.assertTrue(diffuse_color.GetAttr().HasAuthoredValueOpinion())

    async def test_unknown_identifier_is_not_replaced_by_a_fallback(self) -> None:
        """Report an unknown identifier without proposing a fabricated change."""
        stage = Usd.Stage.CreateInMemory()
        material, surface = self.create_material(stage, surface_id="ND_removed_custom_float")

        result = upgrade_materialx_identifiers(material.GetPrim())

        self.assertFalse(result.any_changes)
        self.assertEqual(result.unresolved_prims, [str(surface.GetPath())])
        self.assertTrue(any("Cannot construct a MaterialX node" in item for item in result.diagnostics))

    async def test_convertible_identifier_left_unchanged_remains_actionable(self) -> None:
        """Older MaterialX hosts must not silently drop unresolved convertible identifiers."""

        path = "/Material/Legacy"
        result = UpgradeResult()
        nodes = {path: NetworkNode(UsdShade.Shader(), "ND_legacy_float")}
        specs = {path: MaterialXNodeSpec("legacy", "float")}

        with patch(f"{_UPGRADE_MODULE}.resolved_identifier", return_value="ND_legacy_float"):
            _record_identifier_changes(
                result,
                nodes,
                {path: object()},
                specs,
                {path},
                object(),
                "mtlx",
            )

        self.assertFalse(result.any_changes)
        self.assertEqual(result.unresolved_prims, [path])
        self.assertEqual(
            result.diagnostics,
            ["MaterialX left unresolved identifier 'ND_legacy_float' unchanged at /Material/Legacy"],
        )

    async def test_library_loading_failure_returns_diagnostic(self) -> None:
        """Contain MaterialX library loading failures at the public boundary."""
        stage = Usd.Stage.CreateInMemory()
        material, surface = self.create_material(stage)
        self.add_normalmap(stage, surface, "/Material/NormalMap")

        with patch(f"{_UPGRADE_MODULE}.get_standard_libraries", side_effect=RuntimeError("library failure")):
            result = upgrade_materialx_identifiers(material.GetPrim())

        self.assertFalse(result.upgrade_attempted)
        self.assertTrue(any("Failed to load MaterialX standard libraries" in item for item in result.diagnostics))

    async def test_registry_failure_returns_diagnostic(self) -> None:
        """Contain SDR registry construction failures at the public boundary."""
        stage = Usd.Stage.CreateInMemory()
        material, surface = self.create_material(stage)
        self.add_normalmap(stage, surface, "/Material/NormalMap")

        with patch(f"{_UPGRADE_MODULE}.get_sdr_registry", side_effect=RuntimeError("registry failure")):
            result = upgrade_materialx_identifiers(material.GetPrim())

        self.assertFalse(result.upgrade_attempted)
        self.assertTrue(any("Failed to access SDR registry" in item for item in result.diagnostics))
