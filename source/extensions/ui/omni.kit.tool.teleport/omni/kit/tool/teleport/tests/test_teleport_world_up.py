# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb.settings
import omni.kit.ui_test as ui_test
from pxr import Gf

from .utils import TestTeleportBase, is_near_point, is_viewport_legacy

# Kept as a literal so the test is identical before/after the fix; only the source changes.
TELE_USE_WORLD_UP = "/exts/omni.kit.tool.teleport/useWorldUp"


class _FakeHitResult:
    """Minimal surface hit (_SurfaceHit) stand-in with a surface normal far from world up (point-cloud sphere case)."""

    def __init__(self, hit_position, normal):
        self.valid = True
        self.hit_position = hit_position
        self.normal = normal


class TestTeleportWorldUp(TestTeleportBase):
    async def test_world_up_keeps_teleport_level_and_enabled(self):
        """OMPE-74317: over a surface whose picked normal is far from world up (point clouds), the
        useWorldUp opt-in must keep the teleport level and allowed instead of tilted/denied."""
        if is_viewport_legacy():
            return

        settings = carb.settings.get_settings()

        # A pick normal ~65 degrees from world up, like a randomly oriented point-cloud sphere normal.
        tilted_normal = Gf.Vec3d(0.9, 0.42, 0.1).GetNormalized()
        coords = (0.0, 0.0)
        hit = _FakeHitResult((10.0, 0.0, 10.0), tilted_normal)
        use_ring = self._teleport.is_using_ring_manipulator()

        # Default (setting off): tool derives "up" from the tilted normal -> steep slope, teleport denied.
        settings.set(TELE_USE_WORLD_UP, False)
        pos, world_up = self._teleport._get_surface_pos(coords, hit)
        self.assertIsNotNone(pos)
        self._teleport._widget.set_direction_and_up(Gf.Vec3d(0, 0, 1), self._teleport._widgetUp, use_ring)
        self.assertFalse(is_near_point(self._teleport._widgetUp, world_up))
        self.assertFalse(self._teleport._widget.can_teleport())

        # Opt-in world up: ignore the tilted normal -> level camera up and teleport stays allowed.
        settings.set(TELE_USE_WORLD_UP, True)
        pos, world_up = self._teleport._get_surface_pos(coords, hit)
        self.assertIsNotNone(pos)
        self.assertTrue(is_near_point(self._teleport._widgetUp, world_up))
        self._teleport._widget.set_direction_and_up(Gf.Vec3d(0, 0, 1), self._teleport._widgetUp, use_ring)
        self.assertTrue(self._teleport._widget.can_teleport())

        settings.set(TELE_USE_WORLD_UP, False)
        await ui_test.wait_n_updates(2)
        await self.finalize_test_no_image()
