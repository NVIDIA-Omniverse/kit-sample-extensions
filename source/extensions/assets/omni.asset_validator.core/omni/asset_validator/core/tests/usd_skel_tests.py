# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["OmniSkelUpgradeCheckerTest"]

from unittest import skipIf

from omni.asset_validator.core import OmniSkelUpgradeChecker, is_omni_skel_upgrade_disabled
from pxr import Sdf

from .engine_tests import getUrl
from .rule_test import AsyncValidationRuleTestCase, IsAFailure, IsAWarning


@skipIf(is_omni_skel_upgrade_disabled(), "OmniSkelUpgradeChecker is disabled in Kit 106")
class OmniSkelUpgradeCheckerTest(AsyncValidationRuleTestCase):
    async def test_skel_without_stock_skinning_method(self):
        asset_url = getUrl("UsdSkel/skelWithoutStockSkinningMethod.usda")

        await self.assertRuleAsync(
            asset=asset_url,
            rule=OmniSkelUpgradeChecker,
            asserts=[
                IsAFailure(
                    "Legacy Omniverse property skel:skinningMethod is authored but "
                    "OpenUSD supported primvars:skel:skinningMethod is not.",
                    at=Sdf.Path("/Root/skelroot/triangle"),
                ),
            ],
        )

    async def test_skel_diff_skinning_methods(self):
        asset_url = getUrl("UsdSkel/skelWithDiffSkinningMethods.usda")

        await self.assertRuleAsync(
            asset=asset_url,
            rule=OmniSkelUpgradeChecker,
            asserts=[
                IsAWarning(
                    "Both Legacy Omniverse property skel:skinningMethod and OpenUSD supported property "
                    "primvars:skel:skinningMethod are authored but with different values.",
                    at=Sdf.Path("/Root/skelroot/triangle"),
                ),
            ],
        )

    async def test_skel_without_blend_weights(self):
        asset_url = getUrl("UsdSkel/skelWithoutBlendWeights.usda")

        await self.assertRuleAsync(
            asset=asset_url,
            rule=OmniSkelUpgradeChecker,
            asserts=[
                IsAFailure(
                    "Legacy Omniverse property skel:skinningMethod is authored but OpenUSD supported "
                    "primvars:skel:skinningMethod is not.",
                    at=Sdf.Path("/Root/skelroot/triangle"),
                ),
                IsAWarning(
                    "Legacy Omniverse property skel:skinningMethod is authored as 'WeightedBlend' but "
                    "no property primvars:skel:skinningBlendWeights is presented.",
                    at=Sdf.Path("/Root/skelroot/triangle"),
                ),
                IsAFailure(
                    "Legacy Omniverse property skel:skinningMethod is authored but OpenUSD supported "
                    "primvars:skel:skinningMethod is not.",
                    at=Sdf.Path("/Root/skelroot/triangle_with_blend_weights"),
                ),
                IsAWarning(
                    "OpenUSD does not support weighted blend skinning if authored on a prim that "
                    "does not have 'OmniSkelWeightedBlendAPI' applied.",
                    at=Sdf.Path("/Root/skelroot/triangle_with_blend_weights"),
                ),
            ],
        )

    async def test_skel_diff_blend_weights(self):
        await self.assertRuleAsync(
            asset=getUrl("UsdSkel/skelWithDiffBlendWeights.usda"),
            rule=OmniSkelUpgradeChecker,
            asserts=[
                IsAFailure(
                    "Legacy Omniverse property skel:skinningMethod is authored but "
                    "OpenUSD supported primvars:skel:skinningMethod is not.",
                    at=Sdf.Path("/Root/skelroot/triangle_with_blend_weights"),
                ),
                IsAWarning(
                    "Authored attributes primvars:omni:skel:skinningBlendWeights and "
                    "primvars:skel:skinningBlendWeights are both present with different values.",
                    at=Sdf.Path("/Root/skelroot/triangle_with_blend_weights"),
                ),
            ],
        )
