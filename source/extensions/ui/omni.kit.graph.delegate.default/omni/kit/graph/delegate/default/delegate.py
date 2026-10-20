# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import colorsys
from pathlib import Path

import omni.ui as ui
from omni.kit.widget.graph.graph_model import GraphModel
from omni.kit.widget.graph.graph_node_delegate_router import GraphNodeDelegateRouter
from omni.ui import color as cl

from .delegate_closed import GraphNodeDelegateClosed
from .delegate_full import GraphNodeDelegateFull

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")

# The main colors
LABEL_COLOR = 0xFFB4B4B4
BACKGROUND_COLOR = 0xFF34302A
BORDER_DEFAULT = 0xFFDBA656
BORDER_SELECTED = 0xFFFFFFFF
CONNECTION = 0xFF80C280
NODE_BACKGROUND = 0xFF675853
NODE_BACKGROUND_SELECTED = 0xFF7F6C66


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
            "Graph": {"background_color": background or BACKGROUND_COLOR},
            "Graph.Connection": {"color": CONNECTION, "background_color": CONNECTION, "border_width": 3.0},
            "Graph.Connection:hovered": {"color": CONNECTION, "background_color": CONNECTION, "border_width": 6.0},
            "Graph.Connection.Low": {"color": CONNECTION, "background_color": CONNECTION, "border_width": 9.0},
            "Graph.Connection.Low:hovered": {"color": CONNECTION, "background_color": CONNECTION, "border_width": 18.0},
            "Graph.Connection.Making": {"color": CONNECTION, "background_color": CONNECTION, "border_width": 3.0},
            # Node
            "Graph.Node.Background": {"background_color": node_background or NODE_BACKGROUND},
            "Graph.Node.Background:selected": {
                "background_color": node_background_selected or NODE_BACKGROUND_SELECTED
            },
            "Graph.Node.Border": {"background_color": border or BORDER_DEFAULT},
            "Graph.Node.Border:selected": {"background_color": border_selected or BORDER_SELECTED},
            "Graph.Node.Resize": {"background_color": border or BORDER_DEFAULT},
            "Graph.Node.Resize:selected": {"background_color": border_selected or BORDER_SELECTED},
            "Graph.Node.Description": {"color": LABEL_COLOR},
            "Graph.Node.Description.Edit": {
                "color": LABEL_COLOR,
                "background_color": node_background or NODE_BACKGROUND,
            },
            # Header Input
            "Graph.Node.Input": {
                "background_color": border or BORDER_DEFAULT,
                "border_color": border or BORDER_DEFAULT,
                "border_width": 3.0,
            },
            "Graph.Node.Input:selected": {"border_color": border_selected or BORDER_SELECTED},
            # Header
            "Graph.Node.Header.Label": {"color": 0xFFB4B4B4, "margin_height": 5.0, "font_size": 14.0},
            "Graph.Node.Header.Label::Degenerated": {"font_size": 22.0},
            "Graph.Node.Header.Collapse": {
                "background_color": 0x0,
                "padding": 0,
                "image_url": f"{ICON_PATH}/hamburger-open.svg",
            },
            "Graph.Node.Header.Collapse::Open": {
                "background_color": 0x0,
                "padding": 0,
                "image_url": f"{ICON_PATH}/hamburger-open.svg",
            },
            "Graph.Node.Header.Collapse::Minimized": {"image_url": f"{ICON_PATH}/hamburger-minimized.svg"},
            "Graph.Node.Header.Collapse::Closed": {"image_url": f"{ICON_PATH}/hamburger-closed.svg"},
            # Header Output
            "Graph.Node.Output": {
                "background_color": background or BACKGROUND_COLOR,
                "border_color": border or BORDER_DEFAULT,
                "border_width": 3.0,
            },
            "Graph.Node.Output:selected": {"border_color": border_selected or BORDER_SELECTED},
            # Port Group
            "Graph.Node.Port.Group": {"color": 0xFFB4B4B4},
            "Graph.Node.Port.Group::Plus": {"image_url": f"{ICON_PATH}/Plus.svg"},
            "Graph.Node.Port.Group::Minus": {"image_url": f"{ICON_PATH}/Minus.svg"},
            # Port Input
            "Graph.Node.Port.Input": {
                "background_color": border or BORDER_DEFAULT,
                "border_color": border or BORDER_DEFAULT,
                "border_width": 3.0,
            },
            "Graph.Node.Port.Input:selected": {"border_color": border_selected or BORDER_SELECTED},
            "Graph.Node.Port.Input.CustomColor": {"background_color": 0x0},
            # Port
            "Graph.Node.Port.Branch": {"color": 0xFFB4B4B4, "border_width": 0.75},
            "Graph.Node.Port.Label": {
                "color": 0xFFB4B4B4,
                "margin_width": 5.0,
                "margin_height": 3.0,
                "font_size": 14.0,
            },
            "Graph.Node.Port.Label::output": {"alignment": ui.Alignment.RIGHT},
            # Port Output
            "Graph.Node.Port.Output": {
                "background_color": background or BACKGROUND_COLOR,
                "border_color": border or BORDER_DEFAULT,
                "border_width": 3.0,
            },
            "Graph.Node.Port.Output.CustomColor": {"background_color": 0x0, "border_color": 0x0, "border_width": 3.0},
            # Footer
            "Graph.Node.Footer": {
                "background_color": icon_background or BACKGROUND_COLOR,
                "border_color": border or BORDER_DEFAULT,
                "border_width": 3.0,
                "border_radius": 8.0,
            },
            "Graph.Node.Footer.Border": {
                "background_color": ui.color(0, 0, 0, 0),
                "border_color": border or BORDER_DEFAULT,
                "border_width": 3.0,
                "border_radius": 8.0,
            },
            "Graph.Node.Footer:selected": {"border_color": border_selected or BORDER_SELECTED},
            "Graph.Node.Footer.Border:selected": {"border_color": border_selected or BORDER_SELECTED},
            "Graph.Node.Footer.Image": {
                "image_url": f"{ICON_PATH}/0101.svg",
                "color": border or BORDER_DEFAULT,
                "border_radius": 8.0,
            },
            "Graph.Selecion.Rect": {"background_color": ui.color(1.0, 1.0, 1.0, 0.1)},
            "Graph.Tooltip.Background": {
                "background_color": NODE_BACKGROUND,
                "border_color": border or BORDER_DEFAULT,
                "border_width": 2.0,
                "border_radius": 2.0,
            },
        }

        return style

    @staticmethod
    def specialized_color_style(name, color, icon, icon_tint_color=None):
        """
        Return part of the style that has everything to color special node type.

        Args:
            name: Node type
            color: Node color
            icon: Filename to the icon the node type should display
            icon_tint_color: Icon tint color
        """
        style = {
            # Node
            f"Graph.Node.Border::{name}": {"background_color": color},
            # Header Input
            f"Graph.Node.Input::{name}": {"background_color": color, "border_color": color},
            # Header Output
            f"Graph.Node.Output::{name}": {"border_color": color},
            # Port Input
            f"Graph.Node.Port.Input::{name}": {"background_color": color, "border_color": color},
            f"Graph.Node.Port.Input::{name}:selected": {"background_color": color, "BORDER_SELECTED": color},
            # Port Output
            f"Graph.Node.Port.Output::{name}": {"border_color": color},
            # Footer
            f"Graph.Node.Footer::{name}": {"border_color": color},
            f"Graph.Node.Footer.Border::{name}": {"border_color": color},
            f"Graph.Node.Footer.Image::{name}": {"image_url": icon, "color": icon_tint_color or color},
            f"Graph.Connection::{name}": {"background_color": color, "color": color},
            f"Graph.Connection.Low::{name}": {"background_color": color, "color": color},
        }
        return style

    @staticmethod
    def specialized_port_style(name, color):
        """
        Return part of the style that has everything to color the customizable part of the port.

        Args:
            name: Port type type
            color: Port color
        """

        # 110% lightness from the border color
        L_MULT = 1.1

        colors = hex_to_color(color)
        hls = colorsys.rgb_to_hls(colors[0], colors[1], colors[2])

        brighter_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT)), hls[2])
        brighter_color = color_to_hex(brighter_colors)

        style = {
            f"Graph.Node.Port.Input.CustomColor::{name}": {"background_color": color},
            f"Graph.Node.Port.Output.CustomColor::{name}": {"background_color": color, "border_color": color},
            f"Graph.Connection::{name}": {"background_color": color, "color": color},
            f"Graph.Connection.Low::{name}": {"background_color": color, "color": color},
            f"Graph.Connection.Making::{name}": {"background_color": color, "color": color},
            f"Graph.Tooltip.Background::{name}": {
                "background_color": NODE_BACKGROUND,
                "border_color": color,
                "border_width": 2.0,
                "border_radius": 2.0,
            },
            f"Graph.Connection::{name}:selected": {
                "border_width": 6.0,
                "background_color": brighter_color,
                "color": brighter_color,
            },
            f"Graph.Connection::{name}:hovered": {
                "border_width": 6.0,
                "background_color": brighter_color,
                "color": brighter_color,
            },
            f"Graph.Connection.Low::{name}:selected": {
                "border_width": 18.0,
                "background_color": brighter_color,
                "color": brighter_color,
            },
            f"Graph.Connection.Low::{name}:hovered": {
                "border_width": 18.0,
                "background_color": brighter_color,
                "color": brighter_color,
            },
        }
        return style
