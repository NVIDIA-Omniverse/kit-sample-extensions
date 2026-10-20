# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

placer_properties = {
    # "invalidate_raster": (PropertyType.CALLABLE, PropertyMode.RO),
    "offset_x": (PropertyType.FLOAT, PropertyMode.RW, None),
    "offset_y": (PropertyType.FLOAT, PropertyMode.RW, None),
    "draggable": (PropertyType.BOOL, PropertyMode.RW, True),
    "drag_axis": (PropertyType.ENUM, PropertyMode.RW, None),  # default determined by enum order
    # "stable_size": (PropertyType.BOOL, PropertyMode.RW),
    # "frames_to_start_drag": (PropertyType.INT, PropertyMode.RW),
    # "set_offset_x_changed_fn": (PropertyType.CALLABLE, PropertyMode.RO),
    # "set_offset_y_changed_fn": (PropertyType.CALLABLE, PropertyMode.RO),
    # "raster_policy": (PropertyType.ENUM, PropertyMode.RW),
}

placer_style_properties = []
