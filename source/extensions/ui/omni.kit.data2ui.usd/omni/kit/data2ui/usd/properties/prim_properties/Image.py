# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

image_properties = {
    "source_url": (PropertyType.ASSET, PropertyMode.RW, ""),
    "alignment": (PropertyType.ENUM, PropertyMode.RW, None),  # default determined by enum order
    "fill_policy": (PropertyType.ENUM, PropertyMode.RW, None),  # default determined by enum order
    # "pixel_aligned": (PropertyType.ENUM, PropertyMode.RW),
    # "set_progress_changed_fn": (PropertyType.CALLABLE, PropertyMode.RO),
}

image_style_properties = [
    "alignment",
    "border_color",
    "border_radius",
    "border_width",
    "color",
    "corner_flag",
    "fill_policy",
    "image_url",
]
