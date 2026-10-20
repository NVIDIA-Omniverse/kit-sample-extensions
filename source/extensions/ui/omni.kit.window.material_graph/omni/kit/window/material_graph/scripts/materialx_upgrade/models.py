# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Data contracts used by the MaterialX upgrade pipeline."""

from dataclasses import dataclass, field

from pxr import UsdShade


@dataclass(frozen=True)
class IdentifierChange:
    """Describe one UsdShade shader identifier changed by MaterialX."""

    prim_path: str
    old_identifier: str
    new_identifier: str


@dataclass
class UpgradeResult:
    """Collect the outcome of checking one material network for upgrades."""

    upgrade_attempted: bool = False
    changes: list[IdentifierChange] = field(default_factory=list)
    unresolved_prims: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    pre_upgrade_xml: str = ""
    post_upgrade_xml: str = ""

    @property
    def any_changes(self) -> bool:
        """Return whether the upgrade produced applicable identifier changes."""
        return bool(self.changes)


@dataclass
class NetworkNode:
    """Represent one UsdShade shader collected from a material network."""

    shader: UsdShade.Shader
    identifier: str
    connections: dict[str, tuple[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class MaterialXNodeSpec:
    """Describe how one UsdShade shader is represented in MaterialX."""

    category: str
    output_type: str
    node_def_name: str = ""
    swizzle_input_type: str = ""
    convertible: bool = True
