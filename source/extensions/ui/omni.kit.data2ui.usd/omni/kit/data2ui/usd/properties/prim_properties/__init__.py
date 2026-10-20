# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["prim_properties", "all_prim_style_properties", "ATTR_NS", "DISABLED_PROPERTY"]

ATTR_NS = "omni:ui"
DISABLED_PROPERTY = f"{ATTR_NS}:NoCode:DisableProperty"

from .Button import button_properties, button_style_properties
from .Circle import circle_properties, circle_style_properties
from .CollapsableFrame import collapsable_frame_properties, collapsable_frame_style_properties
from .Container import container_properties, container_style_properties
from .Frame import frame_properties, frame_style_properties
from .HStack import hstack_properties, hstack_style_properties
from .Image import image_properties, image_style_properties
from .Label import label_properties, label_style_properties
from .Line import line_properties, line_style_properties
from .Placer import placer_properties, placer_style_properties
from .Rectangle import rectangle_properties, rectangle_style_properties
from .ScrollingFrame import scrolling_frame_properties, scrolling_frame_style_properties
from .Shape import shape_properties, shape_style_properties
from .Spacer import spacer_properties, spacer_style_properties
from .Stack import stack_properties, stack_style_properties
from .Triangle import triangle_properties, triangle_style_properties
from .ViewportButton import viewport_button_properties, viewport_button_style_properties
from .ViewportCircle import viewport_circle_properties, viewport_circle_style_properties
from .VStack import vstack_properties, vstack_style_properties
from .Widget import widget_properties, widget_style_properties
from .ZStack import zstack_properties, zstack_style_properties

prim_properties = {
    "Widget": widget_properties,
    "Container": container_properties,
    "Frame": frame_properties,
    "ScrollingFrame": scrolling_frame_properties,
    "CollapsableFrame": collapsable_frame_properties,
    "Placer": placer_properties,
    "Spacer": spacer_properties,
    "Stack": stack_properties,
    "HStack": hstack_properties,
    "VStack": vstack_properties,
    "ZStack": zstack_properties,
    "Image": image_properties,
    "Button": button_properties,
    "Label": label_properties,
    "Shape": shape_properties,
    "Rectangle": rectangle_properties,
    "Circle": circle_properties,
    "Line": line_properties,
    "Triangle": triangle_properties,
    "ViewportButton": viewport_button_properties,
    "ViewportCircle": viewport_circle_properties,
}

prim_style_properties = {
    "Widget": widget_style_properties,
    "Container": container_style_properties,
    "Frame": frame_style_properties,
    "ScrollingFrame": scrolling_frame_style_properties,
    "CollapsableFrame": collapsable_frame_style_properties,
    "Placer": placer_style_properties,
    "Spacer": spacer_style_properties,
    "Stack": stack_style_properties,
    "HStack": hstack_style_properties,
    "VStack": vstack_style_properties,
    "ZStack": zstack_style_properties,
    "Image": image_style_properties,
    "Button": button_style_properties,
    "Label": label_style_properties,
    "Shape": shape_style_properties,
    "Rectangle": rectangle_style_properties,
    "Circle": circle_style_properties,
    "Line": line_style_properties,
    "Triangle": triangle_style_properties,
    "ViewportButton": viewport_button_style_properties,
    "ViewportCircle": viewport_circle_style_properties,
}

all_prim_style_properties = []
for prim, props in prim_style_properties.items():
    for prop in props:
        if prop not in all_prim_style_properties:
            all_prim_style_properties.append(prop)
