# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""
Unit tests for PLY Gaussian Splat -> USD conversion with asset validation.

Reads the PLY test file once, converts to USDA and USDZ once, then runs
all assertions against the already-converted outputs.
"""

import os
import shutil
import tempfile

import omni.asset_validator.core
import omni.kit.converter.gsplat as converter
import omni.kit.test

from .rules import GaussianSplatSchemaChecker
from .test_basic import get_test_data_dir


class TestPlyConversion(omni.kit.test.AsyncTestCase):
    """Read a PLY file, convert to USD once, then validate."""

    @classmethod
    def setUpClass(cls):
        ply_file = str(get_test_data_dir() / "cactus_splat3_30kSteps_142k_splats.ply")
        if not os.path.isfile(ply_file):
            raise FileNotFoundError(f"Test PLY file not found: {ply_file}")

        cls._ply_file = ply_file
        cls._tmp = tempfile.mkdtemp(prefix="gsplat_ply_test_")
        cls._splat = converter.read_ply(cls._ply_file)

        cls._usdz_path = os.path.join(cls._tmp, "out.usdz")
        converter.write_gaussian_splat_usd(cls._splat, cls._usdz_path, source_file=cls._ply_file)

        cls._half_path = os.path.join(cls._tmp, "out_half.usdz")
        converter.write_gaussian_splat_usd(cls._splat, cls._half_path, source_file=cls._ply_file, half_precision=True)

        cls._partitioned_path = os.path.join(cls._tmp, "out_partitioned.usdz")
        converter.write_gaussian_splat_usd(
            cls._splat,
            cls._partitioned_path,
            source_file=cls._ply_file,
            max_splats_per_prim=50_000,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    async def test_read_ply(self):
        self.assertIsInstance(self._splat, converter.GaussianSplatData)
        self.assertGreater(self._splat.count, 0)

    async def test_usdz_file_exists(self):
        self.assertTrue(os.path.isfile(self._usdz_path))
        self.assertGreater(os.path.getsize(self._usdz_path), 0)

    async def test_usdz_asset_validation(self):
        """Validate converted USDZ against ParticleField3DGaussianSplat schema rules."""
        engine = omni.asset_validator.core.ValidationEngine()
        engine.enable_rule(GaussianSplatSchemaChecker)
        result = engine.validate(self._usdz_path)
        errors = result.issues(omni.asset_validator.core.IssuePredicates.IsError())
        self.assertFalse(errors, f"Asset validation errors:\n" + "\n".join(str(e) for e in errors))

    async def test_half_precision_usdz_asset_validation(self):
        """
        Half-precision output must validate too.

        Before the rules resolved either variant, they required the float names, so
        this asset failed with five missing-attribute errors — and because the vertex
        count is read from positions, every value-range check silently stopped as
        well. Half output was reported invalid by our own tooling and left largely
        unchecked.
        """
        engine = omni.asset_validator.core.ValidationEngine()
        engine.enable_rule(GaussianSplatSchemaChecker)
        result = engine.validate(self._half_path)
        errors = result.issues(omni.asset_validator.core.IssuePredicates.IsError())
        self.assertFalse(errors, f"Half-precision validation errors:\n" + "\n".join(str(e) for e in errors))

    async def test_partitioned_usdz_asset_validation(self):
        """Validate every ParticleField below the partition parent."""
        engine = omni.asset_validator.core.ValidationEngine()
        engine.enable_rule(GaussianSplatSchemaChecker)
        result = engine.validate(self._partitioned_path)
        errors = result.issues(omni.asset_validator.core.IssuePredicates.IsError())
        self.assertFalse(errors, f"Partitioned asset validation errors:\n" + "\n".join(str(e) for e in errors))
