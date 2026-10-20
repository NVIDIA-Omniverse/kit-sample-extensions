# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections.abc import Generator

import omni.capabilities as cap
from omni.asset_validator import DanglingOverPrimChecker, DefaultPrimChecker, register_requirements
from pxr import Usd, UsdGeom

from ._compliance_checker import is_omni_path

__all__ = [
    "OmniDefaultPrimChecker",
    "OmniOrphanedPrimChecker",
]


@register_requirements(cap.Requirements.HI_004, override=True)
class OmniDefaultPrimChecker(DefaultPrimChecker):
    """
    When working with layers that represent assets, it is often useful to have a single, active,
    Xformable or Scope type root prim as the layers default prim.
    """

    # Keep this docstring in sync with base class' docstring

    @classmethod
    def _get_all_default_prim_candidates(cls, stage: Usd.Stage) -> Generator[Usd.Prim, None, None]:
        """
        Returns:
            All prims that can be default prims.
        """

        for prim in stage.GetPseudoRoot().GetChildren():
            # Must be Xformable or a Scope type
            if not prim.IsA(UsdGeom.Xformable) and not prim.IsA(UsdGeom.Scope):
                continue
            # Must be active
            if not prim.IsActive():
                continue
            # Cannot be abstract
            if prim.IsAbstract():
                continue
            # Cannot be prototyped
            if cls.__IsPrototype(prim):
                continue
            # Cannot be allowed
            if is_omni_path(prim.GetPath()):
                continue
            yield prim

    @staticmethod
    def __IsPrototype(prim):
        if hasattr(prim, "IsPrototype"):
            return prim.IsPrototype()
        return prim.IsMaster()


class OmniOrphanedPrimChecker(DanglingOverPrimChecker):
    """
    Prims usually need a ``def`` or ``class`` specifier, not just ``over`` specifiers.
    However, such overs may be used to hold relationship targets, attribute connections,
    or speculative opinions.
    """

    # Keep this docstring in sync with base class' docstring
    pass
