# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""Asset Importer filter metadata (same shape as omni.kit.converter.common.ConverterFilterData)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

__all__ = ["GsplatAssetImporterFilterData", "GSPLAT_ASSET_IMPORTER_FILTER_DATA"]


@dataclass
class GsplatAssetImporterFilterData:
    """Supported extensions for one Asset Importer delegate registration."""

    name: str
    filter_regexes: List[str]
    filter_descriptions: List[str]
    priority: int = 0


# Priority below built-in Asset Importer (0) so mesh PLY stays the default when both match.
GSPLAT_ASSET_IMPORTER_FILTER_DATA = [
    GsplatAssetImporterFilterData(
        "3D Gaussian Splat (Particle Field)",
        [r"(.*\.ply$)|(.*\.spz$)"],
        ["Gaussian Splat PLY / SPZ (*.ply, *.spz)"],
        -1,
    ),
]
