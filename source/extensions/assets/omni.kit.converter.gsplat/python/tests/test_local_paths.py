# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""Tests for Kit path resolution and ``_validate_file_path`` in the asset importer delegate."""

import os
import tempfile
from pathlib import Path

import omni.kit.test
from omni.kit.converter.gsplat.gsplat_asset_importer_delegate import _validate_file_path
from usd_convert_gsplat import resolve_local_path


class TestResolveLocalPathKit(omni.kit.test.AsyncTestCaseFailOnLogError):
    async def test_existing_file_uri_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as f:
            path = f.name
        try:
            uri = Path(path).as_uri()
            resolved = resolve_local_path(uri)
            self.assertTrue(os.path.isfile(resolved))
            self.assertEqual(os.path.normpath(resolved), os.path.normpath(path))
        finally:
            os.unlink(path)

    async def test_percent_encoded_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "folder with spaces"
            sub.mkdir()
            p = sub / "a.ply"
            p.write_bytes(b"x")
            encoded = str(p).replace(" ", "%20")
            resolved = resolve_local_path(encoded)
            self.assertTrue(os.path.isfile(resolved))
            self.assertEqual(os.path.normpath(resolved), os.path.normpath(str(p)))

    async def test_omniverse_scheme_unchanged(self):
        u = "omniverse://localhost/Projects/a.ply"
        self.assertEqual(resolve_local_path(u), u)


class TestValidateFilePath(omni.kit.test.AsyncTestCaseFailOnLogError):
    """``_validate_file_path`` = ``resolve_local_path`` + local ``os.path.isfile``."""

    async def test_file_uri_to_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as f:
            path = f.name
        try:
            uri = Path(path).as_uri()
            out = _validate_file_path(uri)
            self.assertIsNotNone(out)
            self.assertTrue(os.path.isfile(out))
            self.assertEqual(os.path.normpath(out), os.path.normpath(path))
        finally:
            os.unlink(path)

    async def test_percent_encoded_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "dir with space"
            sub.mkdir()
            p = sub / "b.ply"
            p.write_bytes(b"ply\n")
            encoded = str(p).replace(" ", "%20")
            out = _validate_file_path(encoded)
            self.assertIsNotNone(out)
            self.assertTrue(os.path.isfile(out))
            self.assertEqual(os.path.normpath(out), os.path.normpath(str(p)))

    async def test_omniverse_url_not_a_local_file(self):
        self.assertIsNone(
            _validate_file_path("omniverse://localhost/Projects/missing.ply"),
        )


class TestValidUsdPrimName(omni.kit.test.AsyncTestCaseFailOnLogError):
    """``_valid_usd_prim_name`` in ``usd_writer`` (filenames with spaces, empty stem)."""

    async def test_stem_with_spaces_and_copy_suffix(self):
        from usd_convert_gsplat.usd_writer import _valid_usd_prim_name

        n = _valid_usd_prim_name("Industrial_Plant_Interior_Warehouse - Copy")
        self.assertNotIn(" ", n)
        self.assertGreater(len(n), 0)

    async def test_empty_falls_back(self):
        from usd_convert_gsplat.usd_writer import _valid_usd_prim_name

        self.assertEqual(_valid_usd_prim_name(""), "GaussianSplat")
        self.assertEqual(_valid_usd_prim_name("   "), "GaussianSplat")
