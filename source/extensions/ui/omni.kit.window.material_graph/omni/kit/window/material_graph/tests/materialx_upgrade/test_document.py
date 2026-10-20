# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""MaterialX document transformation coverage."""

from pxr import Sdf, Usd

from ...scripts.materialx_upgrade import IdentifierChange, upgrade_materialx_identifiers
from .base import MaterialXUpgradeTestCase


class TestMaterialXUpgradeDocument(MaterialXUpgradeTestCase):
    """Verify identifier and structural changes made by upgradeVersion()."""

    async def test_normalmap_identifier_is_upgraded_with_document_xml(self) -> None:
        """Upgrade the legacy normalmap identifier and retain diagnostic XML."""
        stage = Usd.Stage.CreateInMemory()
        material, surface = self.create_material(stage)
        normalmap = self.add_normalmap(stage, surface, "/Material/NormalMap")

        result = upgrade_materialx_identifiers(material.GetPrim())

        self.assert_identifier_upgrade_or_host_fallback(
            result,
            [IdentifierChange(str(normalmap.GetPath()), "ND_normalmap", "ND_normalmap_float")],
        )
        self.assertIn('<normalmap name="NormalMap" type="vector3"', result.pre_upgrade_xml)
        self.assertIn('<materialx version="1.38"', result.pre_upgrade_xml)
        expected_version = "1.39" if self.materialx_supports_139_upgrade() else "1.38"
        self.assertIn(f'<materialx version="{expected_version}"', result.post_upgrade_xml)

    async def test_removed_swizzle_is_structurally_upgraded(self) -> None:
        """Convert a removed value-driven swizzle node into a constant node."""
        stage = Usd.Stage.CreateInMemory()
        material, surface = self.create_material(stage)
        swizzle = self.add_swizzle(stage, surface)

        result = upgrade_materialx_identifiers(material.GetPrim())

        self.assert_identifier_upgrade_or_host_fallback(
            result,
            [IdentifierChange(str(swizzle.GetPath()), "ND_swizzle_color3_float", "ND_constant_float")],
        )
        self.assertIn('<swizzle name="Swizzle" type="float"', result.pre_upgrade_xml)
        expected_category = "constant" if self.materialx_supports_139_upgrade() else "swizzle"
        self.assertIn(f'<{expected_category} name="Swizzle" type="float"', result.post_upgrade_xml)

    async def test_current_materialx_version_prevents_legacy_transform(self) -> None:
        """Respect an authored current MaterialX version when upgrading a document."""
        stage = Usd.Stage.CreateInMemory()
        material, surface = self.create_material(stage)
        swizzle = self.add_swizzle(stage, surface)
        material.GetPrim().CreateAttribute("config:mtlx:version", Sdf.ValueTypeNames.String).Set("1.39")

        result = upgrade_materialx_identifiers(material.GetPrim())

        self.assertTrue(result.upgrade_attempted)
        self.assertFalse(result.any_changes)
        self.assertIn(str(swizzle.GetPath()), result.unresolved_prims)
        self.assertIn('<materialx version="1.39"', result.pre_upgrade_xml)
        self.assertIn('<swizzle name="Swizzle" type="float"', result.post_upgrade_xml)
