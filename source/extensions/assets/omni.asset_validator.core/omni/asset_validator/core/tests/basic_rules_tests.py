# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from omni.asset_validator.core import (
    ExtentsChecker,
)
from pxr import Sdf

from .engine_tests import getUrl
from .rule_test import AsyncValidationRuleTestCase, IsAFailure


class BasicRulesTest(AsyncValidationRuleTestCase):

    maxDiff = None

    async def test_extents(self):
        # When / Then
        await self.assertRuleAsync(
            asset=getUrl("extent.usda"),
            rule=ExtentsChecker,
            asserts=[
                IsAFailure("Prim does not have any extent value.*", at=Sdf.Path("/World/ParentTransform/CubeNoExtent")),
                IsAFailure("Prim has incorrect extent value.*", at=Sdf.Path("/World/CubeIncorrectExtent")),
                IsAFailure("Prim does not have any extent value.*", at=Sdf.Path("/World/deforming_mesh_no_extent")),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times (i.e. 1.0, 2.0)",
                    at=Sdf.Path("/World/deforming_mesh_incorrect_extent_samples"),
                ),
                IsAFailure("Prim does not have any extent value.*", at=Sdf.Path("/World/curve_0")),
                IsAFailure("Incorrect extent value for prim at time 2.0.*", at=Sdf.Path("/World/points_0")),
                IsAFailure(
                    "Prim does not have any extent value.*",
                    at=Sdf.Path("/World/SkelRoot_no_extent/SkinnedMesh_no_extent"),
                ),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times (i.e. 0.0, 23.0, 47.0)",
                    at=Sdf.Path("/World/SkelRoot_incorrect_extent_samples/Skel_incorrect_extent_samples"),
                ),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times (i.e. 0.0, 23.0, 47.0)",
                    at=Sdf.Path("/World/SkelRoot_incorrect_extent_samples"),
                ),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times (i.e. 0.0, 23.0, 47.0)",
                    at=Sdf.Path("/World/SkelRoot_incorrect_extent/Skel_incorrect_extent"),
                ),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times (i.e. 0.0, 23.0, 47.0)",
                    at=Sdf.Path("/World/SkelRoot_incorrect_extent"),
                ),
                IsAFailure(
                    "Prim has incorrect extent value.*",
                    at=Sdf.Path("/World/SkelRoot_no_time_samples/Skel_no_time_samples"),
                ),
                IsAFailure("Prim has incorrect extent value.*", at=Sdf.Path("/World/SkelRoot_no_time_samples")),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times (i.e. 0.0, 21.0, 45.0)",
                    at=Sdf.Path("/World/SkelRoot_multiple_skeletons/Skel"),
                ),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times (i.e. 0.0, 10.0, 23.0, 30.0, 40.0, ...)",
                    at=Sdf.Path("/World/SkelRoot_multiple_skeletons/Skel2"),
                ),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times (i.e. 0.0, 10.0, 21.0, 23.0, 30.0, ...)",
                    at=Sdf.Path("/World/SkelRoot_multiple_skeletons"),
                ),
            ],
        )
        await self.assertRuleAsync(
            asset=getUrl("curves.usda"),
            rule=ExtentsChecker,
            asserts=[],
        )
