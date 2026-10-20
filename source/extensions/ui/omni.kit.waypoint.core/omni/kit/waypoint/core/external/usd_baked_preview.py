# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["UsdBakedPreview"]

import base64
import zlib
from enum import Enum
from functools import lru_cache
from typing import List, Optional, Tuple

from pxr import Sdf, Usd


# OM-84028 - Caching the base64 decode results
# Saves us a lot of time when the live stage watcher catches renames.
# it was otherwise recomputing this constantly.
@lru_cache(maxsize=1024)
def get_decoded_values(encoded_string: str):
    return base64.a85decode(encoded_string)


# This class comes from omni.kit.widget.material_preview
class UsdBakedPreview:
    """ApiSchema-like object to store image preview on the prim"""

    ATTR_NAME = "omni:baked_preview"
    DECODE_CACHE = {}

    class PreviewType(Enum):
        ZIP = 0
        # TODO:
        # JPEG = 1

    def __init__(self, prim: Usd.Prim):
        self.__prim = prim

    def get_baked_preview_data(self) -> Optional[Tuple[bytes, int, int]]:
        """Returns baked preview (data, width, height) or an empty image if none"""
        attr = self.get_baked_preview_attr()
        if not attr:
            return

        packed = get_decoded_values(attr.Get())
        data_type = int.from_bytes(packed[0:4], "little")
        if data_type == UsdBakedPreview.PreviewType.ZIP.value:
            width = int.from_bytes(packed[4:8], "little")
            height = int.from_bytes(packed[8:12], "little")
            byte_list = zlib.decompress(packed[12:])
            return (byte_list, width, height)

    def set_baked_preview_data(self, data, width, height, format, data_type: PreviewType = PreviewType.ZIP):
        """
        Serializes bytes data to string and sets baked preview attribute.
        """
        attr = self.create_baked_preview_attr()
        if data_type == UsdBakedPreview.PreviewType.ZIP:
            compressed = zlib.compress(bytes(data))
            packed = (
                data_type.value.to_bytes(4, "little")
                + width.to_bytes(4, "little")
                + height.to_bytes(4, "little")
                + compressed
            )
            attr.Set(base64.a85encode(packed))
        # TODO: JPEG

    def has_baked_preview_attr(self) -> Optional[bool]:
        """True when the prim has the baked preview attribute"""
        if self.__prim:
            return self.__prim.HasAttribute(UsdBakedPreview.ATTR_NAME)

    def get_baked_preview_attr(self) -> Optional[Usd.Attribute]:
        """Returns the baked preview attribute"""
        if self.__prim:
            return self.__prim.GetAttribute(UsdBakedPreview.ATTR_NAME)

    def create_baked_preview_attr(self) -> Optional[Usd.Attribute]:
        """Creates and returns the baked preview attribute"""
        if self.__prim:
            attr = self.get_baked_preview_attr()
            if not attr:
                attr = self.__prim.CreateAttribute(UsdBakedPreview.ATTR_NAME, Sdf.ValueTypeNames.String)

            return attr
