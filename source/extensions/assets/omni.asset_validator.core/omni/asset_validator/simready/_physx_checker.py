# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""PhysX-specific physics validation rules that extend the base physics checker functionality."""

__all__ = [
    "PhysxArticulationChecker",
    "PhysxRigidBodyChecker",
]

import omni.capabilities as cap
from omni.asset_validator.core import BaseRuleChecker, register_requirements
from pxr import Usd, UsdGeom, UsdPhysics


@register_requirements(cap.Requirements.RB_006)
class PhysxRigidBodyChecker(BaseRuleChecker):
    _NESTED_RIGID_BODY_REQUIREMENT = cap.Requirements.RB_006
    _NESTED_RIGID_BODY_MESSAGE = (
        "Enabled rigid body is missing xformstack reset, when a child of a rigid body ({0}) in hierarchy. "
        "Simulation of multiple rigid bodies in a hierarchy will cause unpredicted results. Please fix the hierarchy "
        "or use XformStack reset."
    )

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self._xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        self._is_a_or_under_a_dynamic_body_cache = dict()

    def ResetCaches(self):
        self._xform_cache.Clear()
        self._is_a_or_under_a_dynamic_body_cache.clear()

    def _is_dynamic_body(self, usd_prim: Usd.Prim) -> bool:
        """Check if a prim has an enabled rigid body API."""
        rb_api = UsdPhysics.RigidBodyAPI(usd_prim)
        return rb_api.GetRigidBodyEnabledAttr().Get() if rb_api else False

    def _has_dynamic_body_parent(
        self, usd_prim: Usd.Prim, rb_api: UsdPhysics.RigidBodyAPI
    ) -> tuple[bool, Usd.Prim | None]:
        """Check if this prim has a dynamic body parent in its hierarchy."""
        # early exit on disabled RB, no cache information
        if rb_api and not rb_api.GetRigidBodyEnabledAttr().Get():
            return False, None

        # early exit on immediate xformstack reset
        path = usd_prim.GetPath()
        xform = UsdGeom.Xformable(usd_prim)
        if xform and xform.GetResetXformStack():
            # save True to cache for children and point to me
            self._is_a_or_under_a_dynamic_body_cache[path] = (True, usd_prim)
            return False, None

        # look for either a dynamic body or an xformstack reset towards the root
        # apply cache downwards to all children on exit
        path_list = []
        current = usd_prim.GetParent()
        while current != usd_prim.GetStage().GetPseudoRoot():
            path = current.GetPath()
            cached = self._is_a_or_under_a_dynamic_body_cache.get(path)
            if cached is not None:
                for path in path_list:
                    self._is_a_or_under_a_dynamic_body_cache[path] = cached
                return cached[0], cached[1]

            path_list.append(path)

            # first check dynamic body
            if self._is_dynamic_body(current):
                for path in path_list:
                    self._is_a_or_under_a_dynamic_body_cache[path] = (True, current)
                self._is_a_or_under_a_dynamic_body_cache[usd_prim.GetPath()] = (True, usd_prim)
                return True, current

            # then check xformstack reset
            xform = UsdGeom.Xformable(current)
            if xform and xform.GetResetXformStack():
                # save False, I am not a dynamic body (checked above) and reset was encountered
                for path in path_list:
                    self._is_a_or_under_a_dynamic_body_cache[path] = (False, None)
                return False, None

            current = current.GetParent()

        # nothing found until root encountered
        for path in path_list:
            self._is_a_or_under_a_dynamic_body_cache[path] = (False, None)
        return False, None

    def CheckPrim(self, usd_prim: Usd.Prim):
        rb_api = UsdPhysics.RigidBodyAPI(usd_prim)
        if not rb_api:
            return

        # Check nested rigid body - PhysX-specific requirement
        has_dynamic_parent, body_parent = self._has_dynamic_body_parent(usd_prim, rb_api)
        if has_dynamic_parent:
            self._AddFailedCheck(
                message=self._NESTED_RIGID_BODY_MESSAGE.format(body_parent.GetPath()),
                at=usd_prim,
                requirement=self._NESTED_RIGID_BODY_REQUIREMENT,
            )


@register_requirements(
    cap.Requirements.JT_ART_003,
)
class PhysxArticulationChecker(BaseRuleChecker):
    _ARTICULATION_ON_KINEMATIC_BODY_REQUIREMENT = cap.Requirements.JT_ART_003
    _ARTICULATION_ON_KINEMATIC_BODY_MESSAGE = "ArticulationRootAPI definition on a kinematic rigid body is not allowed."

    def CheckPrim(self, usd_prim: Usd.Prim):
        art_api = UsdPhysics.ArticulationRootAPI(usd_prim)
        if not art_api:
            return
        rbo_api = UsdPhysics.RigidBodyAPI(usd_prim)
        if rbo_api:
            kinematic_enabled = rbo_api.GetKinematicEnabledAttr().Get()
            if kinematic_enabled:
                self._AddFailedCheck(
                    message=self._ARTICULATION_ON_KINEMATIC_BODY_MESSAGE,
                    at=usd_prim,
                    requirement=self._ARTICULATION_ON_KINEMATIC_BODY_REQUIREMENT,
                )
