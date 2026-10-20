# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""Tests for truncated-input validation in ``read_spz`` (malformed/short SPZ files)."""

import gzip
import os
import struct
import tempfile

import omni.kit.test
from usd_convert_gsplat import read_spz


def _write_spz(payload: bytes) -> str:
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".spz", delete=False) as f:
        f.write(gzip.compress(payload))
        return f.name


def _v3_header(num_points: int, sh_degree: int = 0, fractional_bits: int = 12) -> bytes:
    # magic "NGSP", version 3, numPoints, shDegree, fractionalBits, flags, reserved
    return struct.pack("<IIIBBBB", 0x5053474E, 3, num_points, sh_degree, fractional_bits, 0, 0)


class TestSpzHeaderValidation(omni.kit.test.AsyncTestCaseFailOnLogError):
    """Truncated SPZ input must raise ``ValueError``, never a raw ``struct.error``."""

    async def test_truncated_v3_rotation_raises_value_error(self):
        """Regression for NVBugs 6400398: missing v3 rotation chunk must raise ValueError."""
        # N=1 v3 body: positions(9) + alpha(1) + colors(3) + scales(3) = 16 bytes.
        # The 4-byte rotation chunk is entirely absent -> truncated file.
        body = b"\x00" * 9 + b"\x80" + b"\x80" * 3 + b"\x80" * 3
        path = _write_spz(_v3_header(1) + body)
        try:
            with self.assertRaises(ValueError):
                read_spz(path)
        finally:
            os.unlink(path)

    async def test_header_only_file_raises_value_error(self):
        """A header with no per-splat data for N>0 must raise ValueError."""
        path = _write_spz(_v3_header(4))
        try:
            with self.assertRaises(ValueError):
                read_spz(path)
        finally:
            os.unlink(path)

    async def test_zero_num_points_raises_value_error(self):
        """A header declaring zero splats must raise ValueError, matching read_ply_raw's
        rejection of empty geometry, rather than silently returning empty arrays."""
        path = _write_spz(_v3_header(0))
        try:
            with self.assertRaises(ValueError):
                read_spz(path)
        finally:
            os.unlink(path)

    async def test_oversized_num_points_raises_value_error(self):
        """Regression: a header declaring an enormous
        ``numPoints`` must be rejected up front (bomb guard) rather than
        attempting a multi-GB decompressed allocation."""
        # 0xFFFFFFFF splats => hundreds of GB of declared body, far above the cap.
        path = _write_spz(_v3_header(0xFFFFFFFF))
        try:
            with self.assertRaises(ValueError):
                read_spz(path)
        finally:
            os.unlink(path)

    async def test_decompression_bomb_reads_bounded(self):
        """Regression: a small compressed file whose gzip
        stream expands far beyond the declared geometry must NOT be materialized
        in full. read_spz declares 1 splat, so only that splat's body is read;
        the megabytes of trailing zeros in the stream are never decompressed."""
        # Valid N=1 v3 body: positions(9) + alpha(1) + colors(3) + scales(3) + rot(4).
        body = b"\x00" * 9 + b"\x80" + b"\x80" * 3 + b"\x80" * 3 + b"\x00" * 4
        # Append 256 MiB of zeros: on disk this is tiny (~KB) but would OOM if
        # the reader still did an unbounded f.read() of the whole stream.
        payload = _v3_header(1) + body + b"\x00" * (256 * 1024 * 1024)
        path = _write_spz(payload)
        try:
            result = read_spz(path)
            self.assertEqual(result.count, 1)
        finally:
            os.unlink(path)
