# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Expansion chevron state cycling (mirrors ``GraphCanvasView._toggle_expansion_state`` logic)."""

import omni.kit.test


def _next_expansion_state(current: int) -> int:
    """Cycle OPEN(0) → MINIMIZED(1) → CLOSED(2) → OPEN; unknown ints snap to OPEN."""
    if current not in (0, 1, 2):
        return 0
    return (current + 1) % 3


class TestNativeExpansionState(omni.kit.test.AsyncTestCase):
    """Three-state expansion toggle without instantiating the canvas widget."""

    async def test_cycle_open_to_minimized(self) -> None:
        self.assertEqual(_next_expansion_state(0), 1)

    async def test_cycle_minimized_to_closed(self) -> None:
        self.assertEqual(_next_expansion_state(1), 2)

    async def test_cycle_closed_to_open(self) -> None:
        self.assertEqual(_next_expansion_state(2), 0)

    async def test_invalid_state_defaults_to_open(self) -> None:
        for invalid in (-1, 3, 4, 99):
            self.assertEqual(_next_expansion_state(invalid), 0)
