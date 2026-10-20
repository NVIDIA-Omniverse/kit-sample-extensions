# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""LOD-related style invariants for the native graph canvas (no Kit runtime)."""

import omni.kit.test

from ...scripts.config.graph_style import GraphStyle


class TestLodBehavior(omni.kit.test.AsyncTestCase):
    """LOD thresholds and port scaling stay in valid ranges."""

    async def test_lod_thresholds_ordered(self) -> None:
        """More aggressive simplification uses lower effScale cutoffs."""
        self.assertLess(GraphStyle.LOD_THRESHOLD_3, GraphStyle.LOD_THRESHOLD_2)
        self.assertLess(GraphStyle.LOD_THRESHOLD_2, GraphStyle.LOD_THRESHOLD_0)

    async def test_lod_thresholds_positive(self) -> None:
        """All LOD thresholds are strictly positive."""
        for name in ("LOD_THRESHOLD_3", "LOD_THRESHOLD_2", "LOD_THRESHOLD_0"):
            self.assertGreater(getattr(GraphStyle, name), 0.0)

    async def test_lod_port_scaling_valid(self) -> None:
        """Port size/alpha multipliers stay within (0, 1]."""
        for attr in ("PORT_SIZE_LOD1", "PORT_SIZE_LOD2", "PORT_ALPHA_LOD1", "PORT_ALPHA_LOD2"):
            v = getattr(GraphStyle, attr)
            self.assertGreater(v, 0.0)
            self.assertLessEqual(v, 1.0)

    async def test_min_node_screen_size_positive(self) -> None:
        """Minimum on-screen node dimensions are positive pixels."""
        self.assertGreater(GraphStyle.MIN_NODE_SCREEN_W, 0.0)
        self.assertGreater(GraphStyle.MIN_NODE_SCREEN_H, 0.0)
