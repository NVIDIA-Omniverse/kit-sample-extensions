# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""Tests for Asset Importer integration (GaussianSplatAssetImporterDelegate)."""

import omni.kit.converter.gsplat as converter
import omni.kit.test
from omni.kit.converter.gsplat.asset_importer_filters import GSPLAT_ASSET_IMPORTER_FILTER_DATA
from omni.kit.converter.gsplat.gsplat_asset_importer_delegate import GaussianSplatAssetImporterDelegate


class TestGaussianSplatAssetImporterDelegate(omni.kit.test.AsyncTestCaseFailOnLogError):
    async def test_delegate_from_filter_data_matches_pattern(self):
        fd = GSPLAT_ASSET_IMPORTER_FILTER_DATA[0]
        d = GaussianSplatAssetImporterDelegate(fd.name, fd.filter_regexes, fd.filter_descriptions, fd.priority)
        self.assertEqual(d.priority, -1)
        self.assertEqual(d.name, fd.name)
        self.assertTrue(d.is_supported_format("omniverse://server/scene.ply"))
        self.assertTrue(d.is_supported_format("C:/data/model.SPZ"))
        self.assertTrue(d.is_supported_format("foo.ply"))
        self.assertFalse(d.is_supported_format("omniverse://server/scene.fbx"))
        d.destroy()

    async def test_module_exposes_extension(self):
        self.assertIsNotNone(converter.ThreeDGSConverterExtension)
