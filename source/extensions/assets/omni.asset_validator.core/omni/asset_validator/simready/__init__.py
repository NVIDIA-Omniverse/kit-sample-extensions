# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""SimReady rules shipped with omni.asset_validator.core.

Asset-type capability checkers (pedestrian, vehicle, environment, environment light,
traffic light) are registered from ``omni.cip.core`` (Content Ingestion Pipeline).
This package registers component (ground / non-visual / visual sensor), PhysX, and
SimReady-scoped wrappers over shared base checkers.
"""

import omni.capabilities as cap
from omni.asset_validator import AssetOriginPositioningChecker as BaseAssetOriginPositioningChecker
from omni.asset_validator import ContainsMeshChecker as BaseContainsMeshChecker
from omni.asset_validator import HierarchyHasRootChecker as BaseHierarchyHasRootChecker
from omni.asset_validator import RootPrimXformableChecker as BaseRootPrimXformableChecker
from omni.asset_validator import UnitsInMetersChecker as BaseUnitsInMetersChecker
from omni.asset_validator import UpAxisZChecker as BaseUpAxisZChecker
from omni.asset_validator import (
    register_requirements,
)
from omni.asset_validator.core import registerRule

from ._component_ground_truth_capability import GroundTruthCapabilityChecker
from ._component_non_visual_sensor_capability import NonVisualSensorCapabilityChecker
from ._component_visual_sensor_capability import VisualSensorCapabilityChecker
from ._physx_checker import PhysxArticulationChecker, PhysxRigidBodyChecker

__all__ = [
    "AssetOriginPositioningChecker",
    "ContainsMeshChecker",
    "GroundTruthCapabilityChecker",
    "HierarchyHasRootChecker",
    "MetersPerUnit1Checker",
    "NonVisualSensorCapabilityChecker",
    "PhysxArticulationChecker",
    "PhysxRigidBodyChecker",
    "RootPrimXformableChecker",
    "UpAxisZChecker",
    "VisualSensorCapabilityChecker",
]


registerRule("Omni:SimReady")(GroundTruthCapabilityChecker)
registerRule("Omni:SimReady")(NonVisualSensorCapabilityChecker)
registerRule("Omni:SimReady")(VisualSensorCapabilityChecker)
registerRule("Omni:SimReady")(PhysxRigidBodyChecker)
registerRule("Omni:SimReady")(PhysxArticulationChecker)


@registerRule("Omni:SimReady")
@register_requirements(cap.Requirements.VG_025, override=True)
class AssetOriginPositioningChecker(BaseAssetOriginPositioningChecker): ...


@registerRule("Omni:SimReady")
@register_requirements(cap.Requirements.VG_MESH_001, override=True)
class ContainsMeshChecker(BaseContainsMeshChecker): ...


@registerRule("Omni:SimReady")
@register_requirements(cap.Requirements.HI_001, override=True)
class HierarchyHasRootChecker(BaseHierarchyHasRootChecker): ...


@registerRule("Omni:SimReady")
@register_requirements(cap.Requirements.HI_003, override=True)
class RootPrimXformableChecker(BaseRootPrimXformableChecker): ...


@registerRule("Omni:SimReady")
@register_requirements(cap.Requirements.UN_006, override=True)
class UpAxisZChecker(BaseUpAxisZChecker): ...


@registerRule("Omni:SimReady")
@register_requirements(cap.Requirements.UN_007, override=True)
class MetersPerUnit1Checker(BaseUnitsInMetersChecker): ...
