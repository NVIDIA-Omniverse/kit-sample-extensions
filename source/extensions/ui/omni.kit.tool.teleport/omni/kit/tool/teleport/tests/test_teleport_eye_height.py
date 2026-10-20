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
import omni.usd
from omni.kit.viewport.utility.camera_state import ViewportCameraState
from pxr import Gf, UsdGeom

from ..teleport import PERSISTENT_TELE_EYE_HEIGHT
from .utils import TestTeleportBase, is_viewport_legacy


class TestTeleportEyeHeight(TestTeleportBase):
    async def _teleport_and_get_height(self, meters_per_unit):
        """Teleport to the stage origin and return the resulting camera height."""
        stage = omni.usd.get_context().get_stage()
        UsdGeom.SetStageMetersPerUnit(stage, meters_per_unit)
        self._teleport._widgetPos = Gf.Vec3d(0, 0, 0)
        self._teleport._widgetUp = Gf.Vec3d(0, 1, 0)
        self._teleport._teleport(keep_direction=True)
        await ui_test.wait_n_updates(5)
        return ViewportCameraState().position_world[1]

    async def test_teleport_eye_height_scales_with_stage_units(self):
        """The eyeHeight setting is in centimeters and must be converted to stage units (OMPE-99144)."""
        if is_viewport_legacy():
            return

        settings = carb.settings.get_settings()
        eye_height_backup = settings.get(PERSISTENT_TELE_EYE_HEIGHT)
        settings.set(PERSISTENT_TELE_EYE_HEIGHT, 250)
        try:
            # Centimeters stage: 250cm eye height is 250 stage units.
            height = await self._teleport_and_get_height(0.01)
            self.assertAlmostEqual(height, 250.0, delta=0.01)

            # Meters stage: 250cm eye height is 2.5 stage units, not 250 (camera
            # would end up far outside the scene).
            height = await self._teleport_and_get_height(1.0)
            self.assertAlmostEqual(height, 2.5, delta=0.01)
        finally:
            if eye_height_backup is not None:
                settings.set(PERSISTENT_TELE_EYE_HEIGHT, eye_height_backup)
            # The Teleport singleton and the stage are shared with the other
            # tests in this process: restore the state _teleport() mutated
            # (a leftover _need_skip_teleport_frame swallows the next mouse
            # move event) and leave a fresh stage behind.
            self._teleport._need_skip_teleport_frame = False
            self._teleport._pre_click_pos = [-1000, -1000, -1000]
            self._teleport._widgetPos = Gf.Vec3d(0, 0, 0)
            self._teleport._widgetUp = Gf.Vec3d.YAxis()
            await omni.usd.get_context().new_stage_async()
            await ui_test.wait_n_updates(5)
