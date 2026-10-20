# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

frame_properties = {
    # "rebuild": (PropertyType.CALLABLE, PropertyMode.RO),
    # "invalidate_raster": (PropertyType.CALLABLE, PropertyMode.RO),
    # "horizontal_clipping": (PropertyType.FLOAT, PropertyMode.RW),
    # "vertical_clipping": (PropertyType.FLOAT, PropertyMode.RW),
    "separate_window": (PropertyType.BOOL, PropertyMode.RW, False),
    # "raster_policy": (PropertyType.ENUM, PropertyMode.RW),
    # "frozen": (PropertyType.BOOL, PropertyMode.RW),
}

frame_style_properties = [
    "padding",
]
