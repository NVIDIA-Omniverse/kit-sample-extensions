# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["UsdBakedPreview"]

import base64
import zlib
from enum import Enum
from typing import List, Optional, Tuple

from pxr import Sdf, Usd


class UsdBakedPreview:
    """ApiSchema-like object to store image preview on the prim"""

    ATTR_NAME = "omni:baked_preview"

    class PreviewType(Enum):
        ZIP = 0
        # TODO:
        # JPEG = 1

    def __init__(self, prim: Usd.Prim):
        self.__prim = prim

    def get_baked_preview_data(self) -> Optional[Tuple[List[int], int, int]]:
        """Returns baked preview (data, width, height)"""
        attr = self.get_baked_preview_attr()
        if not attr:
            return

        packed = base64.a85decode(attr.Get())
        data_type = int.from_bytes(packed[0:4], "little")
        if data_type == UsdBakedPreview.PreviewType.ZIP.value:
            width = int.from_bytes(packed[4:8], "little")
            height = int.from_bytes(packed[8:12], "little")
            byte_list = zlib.decompress(packed[12:])
            return ([b for b in byte_list], width, height)

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
