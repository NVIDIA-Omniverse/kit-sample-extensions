# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

widget_properties = {
    # "FLAG_WANT_CAPTURE_KEYBOARD": (PropertyType.BOOL, PropertyMode.STATIC),
    "width": (
        PropertyType.LENGTH,
        PropertyMode.RW,
        -1.0,
    ),  # for lengths, positive is pixel values, negative means default, which is fraction 1. default them to -1.
    "height": (PropertyType.LENGTH, PropertyMode.RW, -1.0),
    "name": (PropertyType.STRING, PropertyMode.RW, ""),
    # "style_type_name_override": (PropertyType.STRING, PropertyMode.RW, None),
    # "identifier": (PropertyType.STRING, PropertyMode.RW),
    "visible": (PropertyType.BOOL, PropertyMode.RW, True),
    # "visible_min": (PropertyType.FLOAT, PropertyMode.RW),
    # "visible_max": (PropertyType.FLOAT, PropertyMode.RW),
    "tooltip": (PropertyType.STRING, PropertyMode.RW, ""),
    # "tooltip_offset_x": (PropertyType.FLOAT, PropertyMode.RW),
    # "tooltip_offset_y": (PropertyType.FLOAT, PropertyMode.RW),
    # "enabled": (PropertyType.BOOL, PropertyMode.RW, True),
    "selected": (PropertyType.BOOL, PropertyMode.RW, False),
    # "checked": (PropertyType.BOOL, PropertyMode.RW, False),
    # "dragging": (PropertyType.BOOL, PropertyMode.RW, False),
    # "opaque_for_mouse_events": (PropertyType.BOOL, PropertyMode.RW, False),
    # "skip_draw_when_clipped": (PropertyType.BOOL, PropertyMode.RW, False),
    # "scroll_only_window_hovered": (PropertyType.BOOL, PropertyMode.RW, True),
    "computed_width": (PropertyType.FLOAT, PropertyMode.RO, 0.0),
    "computed_height": (PropertyType.FLOAT, PropertyMode.RO, 0.0),
    # "computed_content_width": (PropertyType.FLOAT, PropertyMode.RO),
    # "computed_content_height": (PropertyType.FLOAT, PropertyMode.RO),
    "screen_position_x": (PropertyType.FLOAT, PropertyMode.RO, 0.0),
    "screen_position_y": (PropertyType.FLOAT, PropertyMode.RO, 0.0),
    # "destroy": (PropertyType.CALLABLE, PropertyMode.RO),
    # "set_style": (PropertyType.CALLABLE, PropertyMode.RO),
    # "set_tooltip": (PropertyType.CALLABLE, PropertyMode.RO),
    # "scroll_here_x": (PropertyType.CALLABLE, PropertyMode.RO),
    # "scroll_here_y": (PropertyType.CALLABLE, PropertyMode.RO),
    # "scroll_here": (PropertyType.CALLABLE, PropertyMode.RO),
    # "set_checked_changed_fn": (PropertyType.CALLABLE, PropertyMode.RO),
}

widget_style_properties = [
    "background_color",
    "border_color",
    "border_radius",
    "border_width",
    "debug_color",
    "margin",
    "margin_height",
    "margin_width",
    "custom",  # custom is a temporary hack
    "binding",  # Will be a relationship to StyleContainer
]
