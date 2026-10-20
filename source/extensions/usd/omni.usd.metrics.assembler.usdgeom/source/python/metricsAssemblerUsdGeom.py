# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Custom Metrics Assembler resolve rules for UsdGeom scene-unit attributes.

This module registers per-attribute scaling rules with the Metrics Assembler so
that ``UsdGeomCamera`` attributes which are explicitly defined in scene units
(see https://openusd.org/release/api/class_usd_geom_camera.html) are converted
correctly when a USD layer with a different ``metersPerUnit`` is referenced /
sublayered / payloaded into a stage.

Without these rules, dragging a camera authored in meters into a stage in
centimeters leaves ``focusDistance`` and ``clippingRange`` with their original
numeric value (e.g. ``focusDistance = 10`` stays ``10`` instead of being scaled
to ``1000`` for cm). Renderers that interpret these attributes in scene units
then produce wrong results (NVBugs 5494562 / OMPE-61911).

Notes
-----
``focalLength``, ``horizontalAperture`` and ``verticalAperture`` (and the
matching ``*Offset`` attributes) are *not* registered here on purpose. Per the
USD schema they are expressed in *tenths of stage unit*, and the renderer
handles the corrective scaling; FOV is therefore correct without an explicit
rule. If a downstream consumer needs those raw values converted, they can
register additional rules of their own through the standard
``IMetricsAssembler::registerCustomResolveRule`` API.
"""

from typing import List, Tuple

from omni.metrics.assembler.core import get_metrics_assembler_interface

# (attribute_name, meters_exponent, kilograms_exponent)
# meters_exponent = 1 means: value is in scene units (linear distance), so it must
# be multiplied by (sourceMPU / stageMPU) when units diverge.
CAMERA_SCENE_UNIT_ATTRIBUTES: List[Tuple[str, int, int]] = [
    # focusDistance - distance from the camera to the focus plane (scene units).
    ("focusDistance", 1, 0),
    # clippingRange - (near, far) distances (scene units). The Metrics Assembler
    # applies the same scalar to every component of the GfVec2f, so a single rule
    # correctly handles both near and far.
    ("clippingRange", 1, 0),
]


class CameraRuleRegistry:
    """Registers / unregisters the camera unit-conversion rules with the
    Metrics Assembler core extension.

    Held as a plain object so the extension class can keep a single instance
    alive for the lifetime of the extension and clean up deterministically on
    shutdown.
    """

    def __init__(self) -> None:
        self._registered_ids: List[int] = []

    def register(self) -> None:
        if self._registered_ids:
            # Idempotent - already registered.
            return
        iface = get_metrics_assembler_interface()
        for attr_name, meters_exp, kg_exp in CAMERA_SCENE_UNIT_ATTRIBUTES:
            rule_id = iface.register_custom_resolve_rule(attr_name, meters_exp, kg_exp)
            # rule_id == 0 (kInvalidRegistryId) means another extension already
            # registered the same attribute. We log a warning but keep going so
            # tests can be re-run cleanly.
            if rule_id:
                self._registered_ids.append(rule_id)

    def unregister(self) -> None:
        iface = get_metrics_assembler_interface()
        for rule_id in self._registered_ids:
            iface.unregister_custom_resolve_rule(rule_id)
        self._registered_ids = []
