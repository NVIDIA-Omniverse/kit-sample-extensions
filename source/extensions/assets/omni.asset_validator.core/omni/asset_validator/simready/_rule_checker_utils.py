# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["validate_stage_default_prim"]

from omni.asset_validator.core import BaseRuleChecker
from pxr import Usd, UsdGeom


def validate_stage_default_prim(rule_checker: BaseRuleChecker, stage: Usd.Stage) -> bool:
    """Validate stage's default prim to ensure it is an active, xformable, and not abstract prim."""

    default_prim = stage.GetDefaultPrim()
    if not default_prim:
        rule_checker._AddFailedCheck("Stage must have a default prim.", at=stage)
        return False

    if not default_prim.GetParent().IsPseudoRoot():
        rule_checker._AddFailedCheck("The default prim must be a root prim.", at=default_prim)
        return False

    if not default_prim.IsA(UsdGeom.Xformable):
        rule_checker._AddFailedCheck(
            f'The default prim <{default_prim.GetName()}> of type "{default_prim.GetTypeName()}" ' "is not Xformable.",
            at=default_prim,
        )
        return False

    if not default_prim.IsActive():
        rule_checker._AddFailedCheck(
            f"The default prim <{default_prim.GetName()}> should be active.",
            at=default_prim,
        )
        return False

    if default_prim.IsAbstract():
        rule_checker._AddFailedCheck(
            f"The default prim <{default_prim.GetName()}> should not be abstract.",
            at=default_prim,
        )
        return False

    return True
