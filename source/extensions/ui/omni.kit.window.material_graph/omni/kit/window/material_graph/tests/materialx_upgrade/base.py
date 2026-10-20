# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Shared USD fixtures for MaterialX upgrade tests."""

from typing import Any
from unittest.mock import patch

import MaterialX as mx
import omni.kit.test
from pxr import Sdf, Usd, UsdShade

_UPGRADE_MODULE = "omni.kit.window.material_graph.scripts.materialx_upgrade.upgrade"
_RESOLVING_IDENTIFIERS = frozenset(
    {
        "ND_atan2_float",
        "ND_constant_float",
        "ND_normalmap_float",
        "ND_standard_surface_surfaceshader",
        "UsdPreviewSurface",
    }
)


def _find_test_sdr_node(_registry: Any, identifier: str, _source_type: str) -> Any:
    """Resolve only the current identifiers used by these upgrade fixtures."""
    return object() if identifier in _RESOLVING_IDENTIFIERS else None


class MaterialXUpgradeTestCase(omni.kit.test.AsyncTestCase):
    """Provide reusable UsdShade network builders for upgrade tests."""

    async def setUp(self) -> None:
        """Use a deterministic SDR view independent of the host Kit version."""
        super().setUp()
        self._find_sdr_node_patcher = patch(
            f"{_UPGRADE_MODULE}.find_sdr_node",
            side_effect=_find_test_sdr_node,
        )
        self._find_sdr_node_patcher.start()

    async def tearDown(self) -> None:
        """Restore the process-wide SDR lookup after each test."""
        self._find_sdr_node_patcher.stop()
        super().tearDown()

    @staticmethod
    def materialx_supports_139_upgrade() -> bool:
        """Return whether the host MaterialX can perform the 1.39 identifier migrations."""

        version = str(getattr(mx, "__version__", mx.getVersionString()))
        numeric_parts = []
        for part in version.split(".")[:2]:
            digits = "".join(character for character in part if character.isdigit())
            numeric_parts.append(int(digits or 0))
        return tuple(numeric_parts) >= (1, 39)

    def assert_identifier_upgrade_or_host_fallback(
        self,
        result: Any,
        expected_changes: list[Any],
    ) -> None:
        """Assert the supported upgrade or the actionable older-host fallback."""

        self.assertTrue(result.upgrade_attempted)
        if self.materialx_supports_139_upgrade():
            self.assertCountEqual(result.changes, expected_changes)
            return

        self.assertFalse(result.any_changes)
        expected_paths = [change.prim_path for change in expected_changes]
        self.assertCountEqual(result.unresolved_prims, expected_paths)
        for path in expected_paths:
            self.assertTrue(
                any(
                    "left unresolved identifier" in diagnostic and path in diagnostic
                    for diagnostic in result.diagnostics
                )
            )

    @staticmethod
    def create_material(
        stage: Usd.Stage,
        material_path: str = "/Material",
        context: str = "mtlx",
        surface_id: str = "ND_standard_surface_surfaceshader",
    ) -> tuple[UsdShade.Material, UsdShade.Shader]:
        """Create a material with a connected surface shader."""
        material = UsdShade.Material.Define(stage, material_path)
        surface = UsdShade.Shader.Define(stage, f"{material_path}/Surface")
        surface.CreateIdAttr(surface_id)
        surface_output = surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput(context).ConnectToSource(surface_output)
        return material, surface

    @staticmethod
    def add_normalmap(
        stage: Usd.Stage,
        surface: UsdShade.Shader,
        path: str,
    ) -> UsdShade.Shader:
        """Create and connect a legacy normalmap shader."""
        normalmap = UsdShade.Shader.Define(stage, path)
        normalmap.CreateIdAttr("ND_normalmap")
        normalmap_output = normalmap.CreateOutput("out", Sdf.ValueTypeNames.Float3)
        surface.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(normalmap_output)
        return normalmap

    @staticmethod
    def add_swizzle(
        stage: Usd.Stage,
        surface: UsdShade.Shader,
        path: str = "/Material/Swizzle",
    ) -> UsdShade.Shader:
        """Create and connect a legacy swizzle shader with an authored value."""
        swizzle = UsdShade.Shader.Define(stage, path)
        swizzle.CreateIdAttr("ND_swizzle_color3_float")
        swizzle.CreateInput("in", Sdf.ValueTypeNames.Color3f).Set((0.1, 0.2, 0.3))
        swizzle.CreateInput("channels", Sdf.ValueTypeNames.String).Set("r")
        swizzle_output = swizzle.CreateOutput("out", Sdf.ValueTypeNames.Float)
        surface.CreateInput("base", Sdf.ValueTypeNames.Float).ConnectToSource(swizzle_output)
        return swizzle
