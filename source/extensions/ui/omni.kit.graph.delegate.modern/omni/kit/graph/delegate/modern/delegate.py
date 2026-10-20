# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from pathlib import Path

import omni.ui as ui
from omni.kit.widget.graph.graph_model import GraphModel
from omni.kit.widget.graph.graph_node_delegate_router import GraphNodeDelegateRouter
from omni.ui import color as cl

from .backdrop_delegate import BackdropDelegate
from .compound_node_delegate import CompoundInputOutputNodeDelegate
from .delegate_closed import GraphNodeDelegateClosed
from .delegate_full import GraphNodeDelegateFull

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")

# The main colors
BACKGROUND_COLOR = 0xFF34302A

CONNECTION = 0xFF9A9A9A
NODE_BORDER_DEFAULT = 0x0
NODE_BORDER_SELECTED = 0xFFF3D25F
NODE_BACKGROUND = 0xFF5C4D48
LABEL_COLOR = 0xFFD9D9D9
DARK_LABEL_COLOR = 0xFF101010

RESIZE_DEFAULT = 0xFFD8B74B
RESIZE_SELECTED = 0xFFDDDDDD


# we should move those into ui.Color
def hex_to_color(hex: int) -> tuple:
    # convert Value from int
    red = hex & 255
    green = (hex >> 8) & 255
    blue = (hex >> 16) & 255
    alpha = (hex >> 24) & 255
    rgba_values = (red / 255, green / 255, blue / 255, alpha / 255)
    return rgba_values


def color_to_hex(color: tuple) -> int:
    """Convert float rgb to int"""

    def to_int(f: float) -> int:
        return int(255 * max(0.0, min(1.0, f)))

    red = to_int(color[0])
    green = to_int(color[1])
    blue = to_int(color[2])
    alpha = to_int(color[3]) if len(color) > 3 else 255
    return (alpha << 8 * 3) + (blue << 8 * 2) + (green << 8 * 1) + red


class GraphNodeDelegate(GraphNodeDelegateRouter):
    """
    The delegate with the Omniverse design that has both full and collapsed states.
    """

    def __init__(self):
        super().__init__()

        def is_closed(model, node):
            expansion_state = model[node].expansion_state
            return expansion_state == GraphModel.ExpansionState.CLOSED

        # Initial setup is the delegates for full and closed states.
        self.add_route(GraphNodeDelegateFull())
        self.add_route(GraphNodeDelegateClosed(), expression=is_closed)
        self.add_route(BackdropDelegate(), type="Backdrop")
        self.add_route(CompoundInputOutputNodeDelegate(), type="InputNode")
        self.add_route(CompoundInputOutputNodeDelegate(), type="OutputNode")

    @staticmethod
    def get_style(
        border=None,
        background=None,
        node_background=None,
        icon_background=None,
        border_selected=None,
        node_background_selected=None,
    ):
        """Return style that can be used with this delegate"""
        style = {
            # graph
            "Graph": {"background_color": background or BACKGROUND_COLOR},
            "Graph.Selecion.Rect": {"background_color": ui.color(1.0, 1.0, 1.0, 0.1)},
            # connection
            "Graph.Connection": {"color": CONNECTION, "border_width": 2.0},
            "Graph.Connection:hovered": {"color": CONNECTION, "border_width": 4.0},
            "Graph.Connection.Making": {"color": CONNECTION, "border_width": 3.0},
            # Node
            "Graph.Node.Border": {"background_color": border or 0x0},
            "Graph.Node.Border:selected": {"background_color": border_selected or NODE_BORDER_SELECTED},
            "Graph.Node.Background": {"background_color": node_background or NODE_BACKGROUND},
            "Graph.Node.Background::Backdrop": {
                "background_color": 0xFF34302A
            },  # special background color for backdrop
            "Graph.Node.Background::Note": {"background_color": 0xFFA4DE0},  # special background color for notes
            "Graph.Node.ColorWidget": {"border_color": ui.color.transparent},
            "Graph.Node.ColorWidgetBorder": {
                "background_color": ui.color.transparent,
                "border_color": 0xCC000000,
                "border_width": 0.2,
            },
            "Graph.Node.Resize": {"background_color": RESIZE_DEFAULT},
            "Graph.Node.Resize:selected": {"background_color": RESIZE_SELECTED},
            "Graph.Node.Label": {"color": LABEL_COLOR, "font_size": 15},
            "Graph.Node.Label.ZoomIn": {"color": LABEL_COLOR, "font_size": 17},
            "Graph.Node.Category": {"background_color": 0xFFADFB47},
            "Graph.Node.Icon": {"image_url": f"{ICON_PATH}/node/type_function_noBorder_dark.svg"},
            "Graph.Node.Icon.Background": {"background_color": 0xFF31291E},
            "Graph.Node.Secondary": {"background_color": 0xFF688E33},
            "Graph.Node.Description": {"color": LABEL_COLOR, "font_size": 18},
            "Graph.Node.Note.Description": {"color": DARK_LABEL_COLOR, "font_size": 20, "margin_width": 10},
            # Port
            "Graph.Node.Port.Input.Icon": {"image_url": f"{ICON_PATH}/omnigraph_input_value_dark.svg"},
            "Graph.Node.Port.Output.CustomColor": {
                "background_color": 0xFF34302A,
                "border_color": 0xFFFFFFFF,
                "border_width": 3,
                "margin_width": 2,
            },
            "Graph.Node.Port.Label": {
                "color": 0xFFB4B4B4,
                "margin_width": 4.0,
                "margin_height": 3.0,
                "font_size": 13.0,
            },
            "Graph.Node.Port.Branch": {"color": LABEL_COLOR, "border_width": 0.75},
            # Port Group
            "Graph.Node.Port.Group": {"color": LABEL_COLOR},
            "Graph.Node.Port.Group::Plus": {"image_url": f"{ICON_PATH}/Plus.svg"},
            "Graph.Node.Port.Group::Minus": {"image_url": f"{ICON_PATH}/Minus.svg"},
            # tooltip
            "Graph.Connection.Tooltip.Label": {"font_size": 14, "color": 0xFF23211F},
            "Graph.Port.Tooltip.Label": {"font_size": 14, "color": 0xFF23211F},
            "Graph.Tooltip.Background": {"background_color": 0xFF99CCCC},
        }

        return style

    @staticmethod
    def specialized_color_style(name, color, icon, secondary_color):
        """
        Return part of the style that has everything to color special node type.

        Args:
            name: Node type
            color: Node color
            icon: Filename to the icon the node type should display
        """
        style = {
            # Node
            f"Graph.Node.Category::{name}": {"background_color": color},
            f"Graph.Node.Secondary::{name}": {"background_color": secondary_color or color},
            f"Graph.Node.Icon::{name}": {"image_url": icon},
            f"Graph.Node.Border::{name}": {"background_color": 0x0},
        }
        return style

    @staticmethod
    def specialized_port_style(name, color):
        """
        Return part of the style that has everything to color the customizable part of the port.

        Args:
            name: Port type
            color: Port color
        """
        style = {
            f"Graph.Node.Port.Input.Icon::{name}": {
                "image_url": f"{ICON_PATH}/omnigraph_input_value_dark.svg",
                "color": color,
            },
            f"Graph.Node.Port.Output.CustomColor::{name}": {
                "background_color": 0xFF34302A,
                "border_color": color,
                "border_width": 3,
                "margin_width": 2,
            },
            f"Graph.Connection::{name}": {"color": color, "background_color": color, "border_width": 2.0},
            f"Graph.Connection::{name}:hovered": {"background_color": color, "color": color, "border_width": 4.0},
            f"Graph.Connection.Making::{name}": {"background_color": color, "color": color, "border_width": 3.0},
        }
        return style
