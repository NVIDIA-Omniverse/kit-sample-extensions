# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Constants used while translating UsdShade networks to MaterialX."""

import re

FALLBACK_SOURCE_MATERIALX_VERSION = "1.38"
MATERIALX_VERSION_ATTRIBUTE = "config:mtlx:version"
SWIZZLE_NODE_DEF_PATTERN = re.compile(r"^ND_swizzle_([^_]+)_([^_]+)$")

USD_TO_MATERIALX_TYPES = {
    "asset": "filename",
    "bool": "boolean",
    "color3d": "color3",
    "color3f": "color3",
    "color3h": "color3",
    "color4d": "color4",
    "color4f": "color4",
    "color4h": "color4",
    "double": "float",
    "double2": "vector2",
    "double3": "vector3",
    "double4": "vector4",
    "float": "float",
    "float2": "vector2",
    "float3": "vector3",
    "float4": "vector4",
    "half": "float",
    "half2": "vector2",
    "half3": "vector3",
    "half4": "vector4",
    "int": "integer",
    "int64": "integer",
    "matrix3d": "matrix33",
    "matrix4d": "matrix44",
    "normal3d": "vector3",
    "normal3f": "vector3",
    "normal3h": "vector3",
    "point3d": "vector3",
    "point3f": "vector3",
    "point3h": "vector3",
    "string": "string",
    "token": "string",
    "uchar": "integer",
    "uint": "integer",
    "uint64": "integer",
    "vector3d": "vector3",
    "vector3f": "vector3",
    "vector3h": "vector3",
}
