# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from omni.asset_validator.core import (
    MaterialOldMdlSchemaChecker,
    OmniMaterialUsdPreviewSurfaceChecker,
)
from pxr import Sdf

from .engine_tests import getUrl
from .rule_test import AsyncValidationRuleTestCase, IsAFailure


class OmniMaterialUsdPreviewSurfaceCheckerTest(AsyncValidationRuleTestCase):
    async def test_api(self):
        await self.assertRuleAsync(
            asset=getUrl("usdPreviewSurfaceFail.usda"),
            rule=OmniMaterialUsdPreviewSurfaceChecker,
            asserts=[
                IsAFailure(
                    "/World/Looks/mtl_cube/PreviewSurfaceTexture.inputs:diffuseColor: Expected type: 'color3f' actual type: 'float3'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/PreviewSurfaceTexture.inputs:metallic: Expected type: 'float' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/PreviewSurfaceTexture.inputs:roughness: Expected type: 'float' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/PreviewSurfaceTexture.inputs:specular: Has a connection; however this parameter is not defined in the specification.",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/diffuseColorTex.inputs:sourceColorSpace: Attribute token value: 'bad' is not present in the list of allowed tokens: '['raw', 'sRGB', 'auto']'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/diffuseColorTex.outputs:rgb: Expected type: 'float3' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/metallicTex.outputs:rgb: Expected type: 'float3' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/roughnessTex.outputs:rgb: Expected type: 'float3' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/normalTex.outputs:rgb: Expected type: 'float3' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
            ],
        )

    async def test_pass(self):
        await self.assertRuleAsync(
            asset=getUrl("usdPreviewSurfacePass.usda"),
            rule=OmniMaterialUsdPreviewSurfaceChecker,
            asserts=[],
        )

    async def test_autofix_suggestions(self):
        await self.assertSuggestionAsync(
            asset=getUrl("usdPreviewSurfaceFail.usda"),
            rule=OmniMaterialUsdPreviewSurfaceChecker,
            predicate=None,
        )

    async def test_time_sampled(self):
        await self.assertRuleAsync(
            asset=getUrl("usdPreviewSurfaceTimeSampledFail.usda"),
            rule=OmniMaterialUsdPreviewSurfaceChecker,
            asserts=[
                IsAFailure(
                    "/World/Looks/mtl_sphere/Shader.inputs:metallic: Expected type: 'float' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_sphere"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_sphere/roughnessTex.inputs:wrapT: Attribute contains time sampled value(s) that "
                    "are not present in the list of allowed tokens: ['black', 'clamp', 'repeat', 'mirror', "
                    "'useMetadata']",
                    at=Sdf.Path("/World/Looks/mtl_sphere"),
                ),
            ],
        )

    async def test_fix_time_sampled(self):
        await self.assertRuleAsync(
            asset=getUrl("usdPreviewSurfaceTimeSampledPass.usda"),
            rule=OmniMaterialUsdPreviewSurfaceChecker,
            asserts=[],
        )


class OmniMaterialOldMdlSchemaCheckerTest(AsyncValidationRuleTestCase):
    async def test_fail(self):
        await self.assertRuleAsync(
            asset=getUrl("omniMaterialOldMdlSchema.usda"),
            rule=MaterialOldMdlSchemaChecker,
            asserts=[
                IsAFailure(
                    "The shader is using the deprecated MDL schema where 'info:sourceImplementation' is set to 'mdlMaterial',"
                    " the 'module' attribute contains the assetPath of the MDL module and the 'name' attribute the subIdentifer.",
                    at=Sdf.Path("/mtl_test/Shader"),
                ),
            ],
        )

    async def test_autofix_suggestions(self):
        await self.assertSuggestionAsync(
            asset=getUrl("omniMaterialOldMdlSchema.usda"),
            rule=MaterialOldMdlSchemaChecker,
            predicate=None,
        )
