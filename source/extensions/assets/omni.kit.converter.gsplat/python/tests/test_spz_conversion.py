# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""
Unit tests for SPZ Gaussian Splat -> USD conversion with asset validation.

Reads the SPZ test file once, converts to USDA and USDZ once, then runs
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


class TestSpzConversion(omni.kit.test.AsyncTestCase):
    """Read an SPZ file, convert to USD once, then validate."""

    @classmethod
    def setUpClass(cls):
        spz_file = str(get_test_data_dir() / "racoonfamily.spz")
        if not os.path.isfile(spz_file):
            raise FileNotFoundError(f"Test SPZ file not found: {spz_file}")

        cls._spz_file = spz_file
        cls._tmp = tempfile.mkdtemp(prefix="gsplat_spz_test_")
        cls._splat = converter.read_spz(cls._spz_file)

        cls._usdz_path = os.path.join(cls._tmp, "out.usdz")
        converter.write_gaussian_splat_usd(cls._splat, cls._usdz_path, source_file=cls._spz_file)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    # -- reader sanity --------------------------------------------------------

    async def test_read_spz(self):
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
