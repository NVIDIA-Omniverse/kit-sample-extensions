# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["NonVisualSensorCapabilityChecker"]


import dataclasses

import omni.capabilities as cap
from omni.asset_validator.core import (
    BaseRuleChecker,
    is_omni_path,
    register_requirements,
)
from pxr import Sdf, Usd, UsdGeom, UsdShade

from ._rule_checker_utils import validate_stage_default_prim


@dataclasses.dataclass
class AttributeConstraint:
    type_names: list[Sdf.ValueTypeName]
    """Any type in this list is allowed."""

    allow_empty: bool
    """If it allows to have no value."""

    allowed_values: list[str]
    """if not empty, list of allowed values for a type."""


@register_requirements(
    cap.Requirements.NVM_001,
    cap.Requirements.NVM_002,
    cap.Requirements.NVM_003,
    cap.Requirements.NVM_006,
)
class NonVisualSensorCapabilityChecker(BaseRuleChecker):
    """
    Validates the following component nonvisual sensor requirements rules in the AV Sim Specification: Creators

    - **3.0.C2.01**:

      Every geometry prim with a computed purpose of "render" or "default" must have non-visual material attributes assigned per visual material assigned, using the 3 attributes listed below:

      - ``token omni:simready:nonvisual:base``
      - ``token omni:simready:nonvisual:coating``
      - ``token[] omni:simready:nonvisual:attributes``

    - **3.0.C2.02**:

      Only valid values for ``nonvisual:base``, ``nonvisual:coating``, ``nonvisual:attributes`` can be used.
    """

    # The following value list is according to AVSimReady Content Specification 0.0.5
    ATTRIBUTE_RULES = {
        "omni:simready:nonvisual:base": AttributeConstraint(
            type_names=[Sdf.ValueTypeNames.Token],
            allow_empty=False,
            allowed_values=[
                # Metals
                "aluminum",
                "steel",
                "oxidized_steel",
                "iron",
                "oxidized_iron",
                "silver",
                "brass",
                "bronze",
                "oxidized_Bronze_Patina",
                "tin",
                # Polymers
                "plastic",
                "fiberglass",
                "carbon_fiber",
                "vinyl",
                "plexiglass",
                "pvc",
                "nylon",
                "polyester",
                # Glass
                "clear_glass",
                "frosted_glass",
                "one_way_mirror",
                "mirror",
                "ceramic_glass",
                # Other
                "asphalt",
                "concrete",
                "leaf_grass",
                "dead_leaf_grass",
                "rubber",
                "wood",
                "bark",
                "cardboard",
                "paper",
                "fabric",
                "skin",
                "fur_hair",
                "leather",
                "marble",
                "brick",
                "stone",
                "gravel",
                "dirt",
                "mud",
                "water",
                "salt_water",
                "snow",
                "ice",
                "calibration_lambertian",
            ],
        ),
        "omni:simready:nonvisual:coating": AttributeConstraint(
            type_names=[Sdf.ValueTypeNames.Token],
            allow_empty=True,
            allowed_values=["none", "paint", "clearcoat", "paint_clearcoat"],
        ),
        "omni:simready:nonvisual:attributes": AttributeConstraint(
            type_names=[Sdf.ValueTypeNames.TokenArray],
            allow_empty=True,
            allowed_values=["none", "emissive", "retroreflective", "single_sided", "visually_transparent"],
        ),
    }

    # Mapping from attribute names to their corresponding requirements
    _ATTRIBUTE_TO_REQUIREMENT = {
        "omni:simready:nonvisual:base": cap.Requirements.NVM_002,
        "omni:simready:nonvisual:coating": cap.Requirements.NVM_003,
        "omni:simready:nonvisual:attributes": cap.Requirements.NVM_001,
    }

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self.ResetCaches()

    @staticmethod
    def _is_from_default_prim(prim: Usd.Prim):
        stage: Usd.Stage = prim.GetStage()
        default_prim = stage.GetDefaultPrim()
        if not default_prim:
            return False

        return prim.GetPath().HasPrefix(default_prim.GetPath())

    @staticmethod
    def _has_default_or_renderable_purpose(prim: Usd.Prim) -> bool:
        """Returns True if the prim is Imageable with default or renderable purpose."""
        if not (imageable := UsdGeom.Imageable(prim)):
            return False
        purpose = imageable.ComputePurpose()
        return purpose in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render)

    def CheckStage(self, stage: Usd.Stage):
        validate_stage_default_prim(self, stage)

    def CheckPrim(self, prim: Usd.Prim):
        if is_omni_path(prim.GetPath()):
            return

        if not self._is_from_default_prim(prim):
            return

        if not UsdGeom.Gprim(prim) and not UsdGeom.Subset(prim):
            return

        if not self._has_default_or_renderable_purpose(prim):
            return

        mtl_binding_api: UsdShade.MaterialBindingAPI = UsdShade.MaterialBindingAPI(prim)

        material, _ = mtl_binding_api.ComputeBoundMaterial(materialPurpose=UsdShade.Tokens.full)
        if not material:
            return
        self.checkMaterial(material)

    def checkMaterial(self, material: UsdShade.Material):
        material_prim = material.GetPrim()

        if material_prim in self._checkedMaterialPrims:
            return

        for name, constraint in NonVisualSensorCapabilityChecker.ATTRIBUTE_RULES.items():
            allow_empty = constraint.allow_empty
            allow_values = constraint.allowed_values
            expected_typenames = constraint.type_names

            # Checks if the attribute exists.
            attr: Usd.Attribute = material.GetPrim().GetAttribute(name)
            if not attr:
                self._AddFailedCheck(
                    message=f'Required attribute "{name}" for nonvisual material doesn\'t exist.',
                    at=material_prim,
                    requirement=self._ATTRIBUTE_TO_REQUIREMENT[name],
                )
                continue

            # Checks type name then.
            typename: Sdf.ValueTypeName = attr.GetTypeName()
            if typename not in expected_typenames:
                self._AddFailedCheck(
                    message=f'Typename of attribute "{name}" for nonvisual material can only be '
                    + (
                        f"{expected_typenames[0]}."
                        if len(expected_typenames) == 1
                        else f"one of {expected_typenames!s}."
                    ),
                    at=material_prim,
                    requirement=self._ATTRIBUTE_TO_REQUIREMENT[name],
                )
                continue
            if (time_samples := attr.GetNumTimeSamples()) > 0:
                self._AddFailedCheck(
                    message=f"Attribute {name} has {time_samples} timeSamples when it should only have a default value.",
                    at=material_prim,
                    requirement=cap.Requirements.NVM_006,
                )

            # Lastly, checks value. It follows those rules:
            # * If allowed_values is empty, that means all values are allowed.
            # * Otherwise, it reports warnings for those values that are not in the allowed list.
            # * Lastly, if value is not given and allow_empty is False, an error is reported.
            value = attr.Get()
            if value is not None and allow_values:
                if typename.isArray:
                    if unexpected_values := list(set(value) - set(allow_values)):
                        self._AddFailedCheck(
                            message=(
                                (
                                    f"Element {unexpected_values[0]}"
                                    if len(unexpected_values) == 1
                                    else f"Elements {unexpected_values!s}"
                                )
                                + f' of array attribute "{name}" for nonvisual material not allowed.'
                            ),
                            at=material_prim,
                            requirement=self._ATTRIBUTE_TO_REQUIREMENT[name],
                        )
                elif value not in allow_values:
                    self._AddFailedCheck(
                        message=f'Value ({value}) of attribute "{name}" for nonvisual material is not in the '
                        "allowed list of values.",
                        at=material_prim,
                        requirement=self._ATTRIBUTE_TO_REQUIREMENT[name],
                    )
            elif value is None and not allow_empty:
                self._AddFailedCheck(
                    message=f'Required attribute "{name}" for nonvisual material must have a value specified.',
                    at=material_prim,
                    requirement=self._ATTRIBUTE_TO_REQUIREMENT[name],
                )

        self._checkedMaterialPrims.add(material_prim)

    def ResetCaches(self):
        self._checkedMaterialPrims = set()
