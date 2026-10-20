# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""Tests for PLY header validation in ``read_ply_raw`` (malformed vertex counts)."""

import os
import tempfile

import omni.kit.test
from usd_convert_gsplat import read_ply_raw

_ASCII_HEADER = (
    "ply\nformat ascii 1.0\nelement vertex {count}\n"
    "property float x\nproperty float y\nproperty float z\nend_header\n"
)


def _write_ply(body: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ply", delete=False) as f:
        f.write(body)
        return f.name


class TestPlyHeaderValidation(omni.kit.test.AsyncTestCaseFailOnLogError):
    """Malformed ``element vertex`` counts must raise ``ValueError``, never a raw ``IndexError``."""

    async def test_negative_vertex_count_raises_value_error(self):
        """Regression: 'element vertex -1' must not crash with IndexError."""
        path = _write_ply(_ASCII_HEADER.format(count=-1) + "0 0 0\n")
        try:
            with self.assertRaises(ValueError):
                read_ply_raw(path)
        finally:
            os.unlink(path)

    async def test_zero_vertex_count_raises_value_error(self):
        path = _write_ply(_ASCII_HEADER.format(count=0))
        try:
            with self.assertRaises(ValueError):
                read_ply_raw(path)
        finally:
            os.unlink(path)

    async def test_non_numeric_vertex_count_raises_value_error(self):
        path = _write_ply(_ASCII_HEADER.format(count="abc") + "0 0 0\n")
        try:
            with self.assertRaises(ValueError):
                read_ply_raw(path)
        finally:
            os.unlink(path)

    async def test_negative_vertex_count_does_not_raise_index_error(self):
        """The negative-count path must surface a ValueError, not the internal IndexError."""
        path = _write_ply(_ASCII_HEADER.format(count=-1) + "0 0 0\n")
        try:
            with self.assertRaises(ValueError):
                read_ply_raw(path)
        except IndexError:
            self.fail("read_ply_raw leaked an IndexError for a negative vertex count")
        finally:
            os.unlink(path)
