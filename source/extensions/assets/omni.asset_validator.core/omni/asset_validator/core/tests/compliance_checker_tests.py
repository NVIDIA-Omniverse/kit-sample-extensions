# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import omni.kit.test
from omni.asset_validator.core import is_omni_path
from pxr import Sdf


class IsOmniPathTest(omni.kit.test.AsyncTestCase):

    async def test_is_omni_path(self):
        self.assertTrue(is_omni_path(Sdf.Path("/OmniverseKit_Persp")))
        self.assertTrue(is_omni_path(Sdf.Path("/OmniverseKit_Front")))
        self.assertTrue(is_omni_path(Sdf.Path("/OmniverseKit_Top")))
        self.assertTrue(is_omni_path(Sdf.Path("/OmniverseKit_Right")))
        self.assertTrue(is_omni_path(Sdf.Path("/OmniKit_Viewport_LightRig")))
        self.assertTrue(is_omni_path(Sdf.Path("/World/Camera/OmniverseKitViewportCameraMesh")))
        self.assertFalse(is_omni_path(Sdf.Path("/World/Mesh")))
