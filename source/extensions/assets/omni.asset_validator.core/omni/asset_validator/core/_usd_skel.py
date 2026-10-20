# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

__all__ = ["OmniSkelUpgradeChecker", "is_omni_skel_upgrade_disabled"]

from enum import Enum

from omni.asset_validator import BaseRuleChecker, Suggestion
from pxr import Sdf, Usd, UsdGeom, UsdSkel

from ._compliance_checker import is_omni_path


class OmniSkinningMethod(str, Enum):
    Linear = "ClassicLinear"
    QualQuatenion = "DualQuaternion"
    WeightedBlend = "WeightedBlend"

    def __str__(self) -> str:
        return self.value


def is_omni_skel_upgrade_disabled() -> bool:
    """
    Returns: OmniSkelUpgradeChecker must be disabled for Kit 106.
    """
    try:
        from omni.kit.app import get_app

        major, _ = get_app().get_kit_version_short().split(".")
        return int(major) <= 106
    except:
        return False


class OmniSkelUpgradeChecker(BaseRuleChecker):
    """
    Omniverse had integrated a prototype of alternate skinning modes that ended up diverging from OpenUSD.
    This tries to migrate skinning and annotate the currently unsupported in OpenUSD weighted blend mode with
    an Omniverse specific API schema. Following are the rules:

        * If Legacy Omniverse property skel:skinningMethod is presented but OpenUSD supported
          primvars:skel:skinningMethod is not presented, it should add warning.
        * If Legacy Omniverse property skel:skinningMethod is presented and its value is 'DualQuaternion', it should
          offer migration path to add new property supported by stock USD.
        * If Legacy Omniverse property skel:skinningMethod is presented and its value is 'WeightedBlend' but no property
          primvars:skel:skinningBlendWeights is authored, it should warn user about that.
    """

    NV_SKINNING_METHOD = "skel:skinningMethod"

    NV_SKINNING_BLEND_WEIGHTS = "primvars:skel:skinningBlendWeights"

    # Supported after stock USD 22.11
    STOCK_SKINNING_METHOD = "primvars:skel:skinningMethod"
    NV_STOCK_SKINNING_METHOD_MAP = {
        OmniSkinningMethod.Linear: "classicLinear",
        OmniSkinningMethod.QualQuatenion: "dualQuaternion",
    }

    OMNI_SKINNING_BLEND_WEIGHT_SCHEMA = "OmniSkelWeightedBlendAPI"
    OMNI_SKINNING_BLEND_WEIGHT_ATTR = "primvars:omni:skel:skinningBlendWeights"

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

    def migrate_skinning_method(self, stage: Usd.Stage, prim: Usd.Prim):
        nv_attribute = prim.GetAttribute(self.NV_SKINNING_METHOD)
        if not nv_attribute:
            return

        stock_attribute = prim.CreateAttribute(self.STOCK_SKINNING_METHOD, Sdf.ValueTypeNames.Token, False)
        stock_method = self.NV_STOCK_SKINNING_METHOD_MAP.get(nv_attribute.Get(), "classicLinear")
        stock_attribute.Set(stock_method)

    def migrate_weighted_blend_schema(self, stage: Usd.Stage, prim: Usd.Prim):
        prim.AddAppliedSchema(self.OMNI_SKINNING_BLEND_WEIGHT_SCHEMA)
        nv_blend_weights: Usd.Attribute = prim.GetAttribute(self.NV_SKINNING_BLEND_WEIGHTS)
        new_omni_blend_weights: Usd.Attribute = prim.CreateAttribute(
            name=self.OMNI_SKINNING_BLEND_WEIGHT_ATTR,
            typeName=nv_blend_weights.GetTypeName(),
            custom=False,
        )
        new_omni_blend_weights.Set(nv_blend_weights.Get())

    def remove_nv_skinning_method(self, stage: Usd.Stage, prim: Usd.Prim):
        prim.RemoveProperty(self.NV_SKINNING_METHOD)

    def CheckPrim(self, prim: Usd.Prim):
        if is_omni_path(prim.GetPath()):
            return

        if not UsdSkel.IsSkinnablePrim(prim):
            return

        if not (boundable_prim := UsdGeom.Boundable(prim)):
            return

        mesh_prim = boundable_prim.GetPrim()
        nv_skinning_method: Usd.Attribute = mesh_prim.GetAttribute(self.NV_SKINNING_METHOD)
        if not nv_skinning_method or not nv_skinning_method.Get():
            return

        nv_blend_weights: Usd.Attribute = mesh_prim.GetAttribute(self.NV_SKINNING_BLEND_WEIGHTS)
        new_omni_blend_weights: Usd.Attribute = mesh_prim.GetAttribute(self.OMNI_SKINNING_BLEND_WEIGHT_ATTR)
        stock_skinning_method: Usd.Attribute = mesh_prim.GetAttribute(self.STOCK_SKINNING_METHOD)
        stock_skinnng_method_is_authored = self.STOCK_SKINNING_METHOD in mesh_prim.GetAuthoredPropertyNames()
        expected_stock_method = self.NV_STOCK_SKINNING_METHOD_MAP.get(nv_skinning_method.Get(), None)
        if stock_skinnng_method_is_authored and expected_stock_method != stock_skinning_method.Get():
            self._AddWarning(
                f"Both Legacy Omniverse property {self.NV_SKINNING_METHOD} and "
                f"OpenUSD supported property {self.STOCK_SKINNING_METHOD} are authored but with different values.",
                at=mesh_prim,
            )
        elif not stock_skinnng_method_is_authored:
            self._AddFailedCheck(
                f"Legacy Omniverse property {self.NV_SKINNING_METHOD} is authored but "
                f"OpenUSD supported {self.STOCK_SKINNING_METHOD} is not.",
                at=mesh_prim,
                suggestion=Suggestion(
                    callable=self.migrate_skinning_method,
                    message=f"Migrate {self.NV_SKINNING_METHOD} to {self.STOCK_SKINNING_METHOD}.",
                ),
            )

        if nv_skinning_method.Get() == OmniSkinningMethod.WeightedBlend and (
            not nv_blend_weights or not nv_blend_weights.Get()
        ):
            self._AddWarning(
                f"Legacy Omniverse property {self.NV_SKINNING_METHOD} is authored as 'WeightedBlend' but no "
                f"property {self.NV_SKINNING_BLEND_WEIGHTS} is presented.",
                at=mesh_prim,
                suggestion=Suggestion(
                    callable=self.remove_nv_skinning_method, message=f"Remove property {self.NV_SKINNING_METHOD}"
                ),
            )

        if nv_blend_weights:
            nv_blend_weights_value = nv_blend_weights.Get()
            new_omni_blend_weights_value = new_omni_blend_weights.Get() if new_omni_blend_weights else None
            if new_omni_blend_weights_value is not None and nv_blend_weights_value != new_omni_blend_weights_value:
                self._AddWarning(
                    f"Authored attributes {self.OMNI_SKINNING_BLEND_WEIGHT_ATTR} and "
                    f"{self.NV_SKINNING_BLEND_WEIGHTS} are both present with different values.",
                    at=mesh_prim,
                )

            if nv_blend_weights_value:
                api_schemas: Sdf.TokenListOp = mesh_prim.GetMetadata("apiSchemas")
                if not api_schemas:
                    return None

                applied_schemas = api_schemas.GetAddedOrExplicitItems()
                if self.OMNI_SKINNING_BLEND_WEIGHT_SCHEMA not in applied_schemas:
                    self._AddWarning(
                        "OpenUSD does not support weighted blend skinning if authored on a prim that does not have "
                        "'OmniSkelWeightedBlendAPI' applied.",
                        at=mesh_prim,
                        suggestion=Suggestion(
                            callable=self.migrate_weighted_blend_schema,
                            message=f"Migrate to {self.OMNI_SKINNING_BLEND_WEIGHT_SCHEMA}",
                        ),
                    )
