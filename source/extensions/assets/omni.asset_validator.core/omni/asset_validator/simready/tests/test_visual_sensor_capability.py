# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

__all__ = ["VisualSensorCapabilityCheckerTest"]

from omni.asset_validator.simready import VisualSensorCapabilityChecker
from pxr import Sdf

from .simready_common import AsyncValidationRuleTestCase, IsAFailure, get_url


class VisualSensorCapabilityCheckerTest(AsyncValidationRuleTestCase):
    async def test_material_on_geom_success(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/primsWithMaterialBindingSuccess.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[],
        )

    async def test_material_on_geom_failure(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/primsWithMaterialBindingFailure.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[
                IsAFailure("No materials found on prim", at=Sdf.Path("/World/no_material")),
                IsAFailure("No materials found on prim", at=Sdf.Path("/World/preview")),
            ],
        )

    async def test_material_on_geomSubset_success(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/geomSubsetsWithMaterialBindingSuccess.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[],
        )

    async def test_material_on_geomSubset_success_without_material_binding_api(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/geomSubsetsWithoutMaterialBindingAPISuccess.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[],
        )

    async def test_material_on_geomSubset_failure(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/geomSubsetsWithMaterialBindingFailure.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[
                IsAFailure(
                    "GeomSubset.*has no materials and the GPrim.*has no material",
                    at=Sdf.Path("/World/Cube_GeomSubset/preview"),
                ),
                IsAFailure(
                    "GeomSubset.*has no materials and the GPrim.*has no material",
                    at=Sdf.Path("/World/Cube_GeomSubset/no_material"),
                ),
                IsAFailure(
                    "No materials found on prim .*. There are faces without material",
                    at=Sdf.Path("/World/Cube_GeomSubset_partial"),
                ),
                IsAFailure(
                    "GeomSubset.*has no materials and the GPrim.*has no material",
                    at=Sdf.Path("/World/Cube_GeomSubset_partial/no_material"),
                ),
            ],
        )

    async def test_geomSubset_with_material_opacity_retroreflection_emissive(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/geomSubsetsWithShaderEmissionOpacityRetroreflection.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[
                IsAFailure(
                    "AVSimReady asset requires geomSubset .* with the computed material .* that has opacity enabled to be separate Gprims.",
                    at=Sdf.Path("/World/Cube_GeomSubset_01/second"),
                ),
                IsAFailure(
                    "AVSimReady asset requires geomSubset .* with the computed material .* that has emissive enabled to be separate Gprims.",
                    at=Sdf.Path("/World/Cube_GeomSubset_01/third"),
                ),
                IsAFailure(
                    "AVSimReady asset requires geomSubset .* with the computed material .* that has retroreflection enabled to be separate Gprims.",
                    at=Sdf.Path("/World/Cube_GeomSubset_02/first"),
                ),
                IsAFailure(
                    "AVSimReady asset requires geomSubset .* with the computed material .* that has opacity emissive enabled to be separate Gprims.",
                    at=Sdf.Path("/World/Cube_GeomSubset_02/second"),
                ),
            ],
        )

    async def test_material_with_invalid_surface_shader(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/materialTypeFailure.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[
                IsAFailure(
                    "SimReady requires that the surface shader is MDL (in either the material's universal or MDL render context) or UsdPreviewSurface (in the material's universal render context only).",
                    at=Sdf.Path("/World/Looks/invalid_shader"),
                ),
                IsAFailure(
                    "SimReady requires that the surface shader is MDL (in either the material's universal or MDL render context) or UsdPreviewSurface (in the material's universal render context only).",
                    at=Sdf.Path("/World/Looks/no_surface_shader"),
                ),
                IsAFailure(
                    "SimReady requires that the surface shader is MDL (in either the material's universal or MDL render context) or UsdPreviewSurface (in the material's universal render context only).",
                    at=Sdf.Path("/World/Looks/ups_shader_in_mdl_render_context"),
                ),
            ],
        )

    async def test_material_type_success(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/materialTypeSuccess.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[],
        )

    async def test_UPS_with_opacity_and_emissive(self):  # This is an allowed case now.
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/usdPreviewSurfaceWithOpacityAndEmissive.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[],
        )

    async def test_usd_preview_surface_shader_success(self):
        await self.assertRuleAsync(
            asset=get_url("visual_sensor/usdPreviewSurfaceSuccess.usda"),
            rule=VisualSensorCapabilityChecker,
            asserts=[],
        )

    async def test_geom_without_default_prim(self):
        url = get_url("visual_sensor/geomWithoutDefaultPrim.usda")
        await self.assertRuleAsync(
            asset=url,
            rule=VisualSensorCapabilityChecker,
            asserts=[
                IsAFailure("Stage must have a default prim.", at=f"Stage <{url}>"),
            ],
        )

    async def test_geom_without_xformable_default_prim(self):
        url = get_url("visual_sensor/geomWithoutXformableDefaultPrim.usda")
        await self.assertRuleAsync(
            asset=url,
            rule=VisualSensorCapabilityChecker,
            asserts=[
                IsAFailure('The default prim <Cube> of type "Scope" is not Xformable.', at="Prim </Cube>"),
            ],
        )
