# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

label_properties = {
    "text": (PropertyType.STRING, PropertyMode.RW, "Label"),
    "alignment": (PropertyType.ENUM, PropertyMode.RW, None),
    # "word_wrap": (PropertyType.BOOL, PropertyMode.RW),
    # "elided_text": (PropertyType.BOOL, PropertyMode.RW),
    # "elided_text_str": (PropertyType.STRING, PropertyMode.RW),
}

label_style_properties = [
    "padding",
    "alignment",
    "color",
    "font_size",
]
