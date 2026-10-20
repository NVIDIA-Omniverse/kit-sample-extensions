# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""Kit extension ``omni.kit.converter.gsplat`` — Asset Importer registration; conversion API is ``usd_convert_gsplat``."""

from usd_convert_gsplat import (
    UP_AXIS_Y,
    UP_AXIS_Z,
    GaussianSplatData,
    __version__,
    convertPlyUSD,
    get_version,
    read_ply,
    read_ply_raw,
    read_spz,
    write_gaussian_splat_usd,
    write_ply,
)

from .extension import ThreeDGSConverterExtension, get_instance

__all__ = [
    "__version__",
    "get_version",
    "ThreeDGSConverterExtension",
    "get_instance",
    "GaussianSplatData",
    "read_ply",
    "read_ply_raw",
    "read_spz",
    "write_gaussian_splat_usd",
    "convertPlyUSD",
    "write_ply",
    "UP_AXIS_Y",
    "UP_AXIS_Z",
]
