# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""fit_camera reads _worldExtent through _as_range3d: Fabric's usdrt returns a Gf.Range3d, Kit 111's OVStage usdrt
returns plain (min, max) values."""
import omni.kit.test

from ..utils import _as_range3d

usdrt_mod = None


class TestWorldExtentShapes(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        try:
            import usdrt  # loaded lazily, as fit_camera does: not every test process of this extension has it
        except ImportError:
            self.skipTest("usdrt is not loaded in this test process")
        global usdrt_mod
        usdrt_mod = usdrt

    def _assert_range(self, rng, lo, hi):
        self.assertIsInstance(rng, usdrt_mod.Gf.Range3d)
        self.assertEqual(tuple(rng.GetMin()), lo)
        self.assertEqual(tuple(rng.GetMax()), hi)

    async def test_range3d_passes_through(self):
        rng = usdrt_mod.Gf.Range3d(usdrt_mod.Gf.Vec3d(-1, -2, -3), usdrt_mod.Gf.Vec3d(1, 2, 3))
        self.assertIs(_as_range3d(usdrt_mod, rng), rng)

    async def test_min_max_pair(self):
        self._assert_range(_as_range3d(usdrt_mod, ((-1, -2, -3), (1, 2, 3))), (-1, -2, -3), (1, 2, 3))

    async def test_six_values(self):
        self._assert_range(_as_range3d(usdrt_mod, (-1, -2, -3, 1, 2, 3)), (-1, -2, -3), (1, 2, 3))

    async def test_none_is_no_extent(self):
        self.assertIsNone(_as_range3d(usdrt_mod, None))

    async def test_unknown_shape_is_no_extent(self):
        self.assertIsNone(_as_range3d(usdrt_mod, (1, 2, 3, 4)))
        self.assertIsNone(_as_range3d(usdrt_mod, 5.0))
