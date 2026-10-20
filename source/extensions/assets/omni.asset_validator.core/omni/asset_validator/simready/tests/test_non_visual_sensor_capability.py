# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

__all__ = ["NonVisualSensorCapabilityTests"]

from omni.asset_validator.simready import NonVisualSensorCapabilityChecker
from pxr import Sdf

from .simready_common import AsyncValidationRuleTestCase, IsAFailure, get_url


class NonVisualSensorCapabilityTests(AsyncValidationRuleTestCase):
    async def test_non_visual_sensor_materials_success(self):
        await self.assertRuleAsync(
            asset=get_url("non_visual_sensor/nonVisualSensorMaterialsSuccess.usda"),
            rule=NonVisualSensorCapabilityChecker,
            asserts=[],
        )

    async def test_non_visual_sensor_materials_invalid_base_label(self):
        await self.assertRuleAsync(
            asset=get_url("non_visual_sensor/nonVisualSensorMaterialsInvalidBaseLabel.usda"),
            rule=NonVisualSensorCapabilityChecker,
            asserts=[
                IsAFailure(
                    'Value (.*) of attribute "omni:simready:nonvisual:base" for nonvisual material is not in the allowed list of values.',
                    at=Sdf.Path("/World/Looks/invalid_base_label"),
                ),
                IsAFailure(
                    'Required attribute "omni:simready:nonvisual:base" for nonvisual material doesn\'t exist.',
                    at=Sdf.Path("/World/Looks/invalid_base_not_defined"),
                ),
            ],
        )

    async def test_non_visual_sensor_materials_invalid_coating_label(self):
        await self.assertRuleAsync(
            asset=get_url("non_visual_sensor/nonVisualSensorMaterialsInvalidCoatingLabel.usda"),
            rule=NonVisualSensorCapabilityChecker,
            asserts=[
                IsAFailure(
                    'Value (.*) of attribute "omni:simready:nonvisual:coating" for nonvisual material is not in the allowed list of values.',
                    at=Sdf.Path("/World/Looks/invalid_coating_label"),
                ),
                IsAFailure(
                    'Required attribute "omni:simready:nonvisual:coating" for nonvisual material doesn\'t exist.',
                    at=Sdf.Path("/World/Looks/invalid_coating_not_defined"),
                ),
            ],
        )

    async def test_non_visual_sensor_materials_invalid_attributes_label(self):
        await self.assertRuleAsync(
            asset=get_url("non_visual_sensor/nonVisualSensorMaterialsInvalidAttributesLabel.usda"),
            rule=NonVisualSensorCapabilityChecker,
            asserts=[
                IsAFailure(
                    'Elements (.*) of array attribute "omni:simready:nonvisual:attributes" for nonvisual material not allowed.',
                    at=Sdf.Path("/World/Looks/invalid_attributes_labels"),
                ),
                IsAFailure(
                    'Element something of array attribute "omni:simready:nonvisual:attributes" for nonvisual material not allowed.',
                    at=Sdf.Path("/World/Looks/invalid_attributes_label"),
                ),
                IsAFailure(
                    'Typename of attribute "omni:simready:nonvisual:attributes" for nonvisual material can only be .*.',
                    at=Sdf.Path("/World/Looks/invalid_attributes_type"),
                ),
                IsAFailure(
                    'Required attribute "omni:simready:nonvisual:attributes" for nonvisual material doesn\'t exist.',
                    at=Sdf.Path("/World/Looks/invalid_attributes_not_defined"),
                ),
                IsAFailure(
                    "Attribute omni:simready:nonvisual:base has .* timeSamples when it should only have a default value.",
                    at=Sdf.Path("/World/Looks/invalid_attributes_time_samples"),
                ),
                IsAFailure(
                    'Required attribute "omni:simready:nonvisual:base" for nonvisual material must have a value specified.',
                    at=Sdf.Path("/World/Looks/invalid_attributes_time_samples"),
                ),
                IsAFailure(
                    'Typename of attribute "omni:simready:nonvisual:attributes" for nonvisual material can only be .*.',
                    at=Sdf.Path("/World/Looks/invalid_attributes_type_string"),
                ),
            ],
        )
