# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
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

from .delegate_backdrop import NeoGraphNodeDelegateBackdrop
from .delegate_closed import NeoGraphNodeDelegateClosed
from .delegate_compound import NeoCompoundInputOutputNodeDelegate
from .delegate_full import NeoGraphNodeDelegateFull, color_to_hex, hex_to_color

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")

# The main colors
LABEL_COLOR = 0xFFD4D4D4
BACKGROUND_COLOR = 0xFF3B2A1E
BORDER_DEFAULT = 0xFFD8B74B
BORDER_SELECTED = 0xFFDDDDDD
CONNECTION = 0xFF2FBB86
NODE_BACKGROUND = 0xFF60402D
NODE_BACKGROUND_SELECTED = 0xFF7F6C66


class NeoGraphNodeDelegate(GraphNodeDelegateRouter):
    """
    Custom Delegate with the new Neo Look
    """

    def __init__(self):
        super().__init__()

        def is_closed(model, node):
            expansion_state = model[node].expansion_state
            return expansion_state == GraphModel.ExpansionState.CLOSED

        # Initial setup is the delegates for full and closed states.
        self.add_route(NeoGraphNodeDelegateFull())
        self.add_route(NeoGraphNodeDelegateClosed(), expression=is_closed)

        self.add_route(NeoGraphNodeDelegateBackdrop(), type="Backdrop")
        self.add_route(NeoCompoundInputOutputNodeDelegate(), type="InputNode")
        self.add_route(NeoCompoundInputOutputNodeDelegate(), type="OutputNode")

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
            "Graph": {"background_color": BACKGROUND_COLOR},
            "Graph.Connection": {"color": CONNECTION, "background_color": CONNECTION, "border_width": 4.0},
            # Node
            "Graph.Node.BackgroundColor": {"background_color": NODE_BACKGROUND},
            "Graph.Node.Border": {"background_color": BORDER_DEFAULT},
            "Graph.Node.Border:selected": {"background_color": BORDER_SELECTED},
            "Graph.Node.Resize": {"background_color": BORDER_DEFAULT},
            "Graph.Node.Resize:selected": {"background_color": BORDER_SELECTED},
            "Graph.Node.Description": {"color": LABEL_COLOR, "font_size": 18},
            "Graph.Node.Description.Edit": {"color": LABEL_COLOR, "background_color": 0x0, "font_size": 18},
            # Header Input
            "Graph.Node.Input": {
                "background_color": BORDER_DEFAULT,
                "border_color": BORDER_DEFAULT,
                "border_width": 3.0,
            },
            # Header
            "Graph.Node.Header.Label": {"color": LABEL_COLOR, "margin_height": 2.0, "font_size": 16.0},
            "Graph.Node.Header.Label::Degenerated": {"font_size": 24.0},
            "Graph.Node.Header.Collapse": {
                "background_color": BORDER_DEFAULT,
                "padding": 0,
                "alignment": ui.Alignment.BOTTOM,
            },
            "Graph.Node.Header.Collapse::Minimized": {"alignment": ui.Alignment.RIGHT},
            "Graph.Node.Header.Collapse::Closed": {"alignment": ui.Alignment.TOP},
            "Graph.Node.Header.Port": {"background_color": 0xFFAD9452, "border_radius": 3},
            "Graph.Node.Header.Background": {"background_color": 0xFF492D1D},
            # Header Output
            "Graph.Node.Output": {
                "background_color": BACKGROUND_COLOR,
                "border_color": BORDER_DEFAULT,
                "border_width": 3.0,
            },
            # Port Group
            "Graph.Node.Port.Group": {"color": LABEL_COLOR},
            "Graph.Node.Port.Group::Plus": {"image_url": f"{ICON_PATH}/Plus.svg"},
            "Graph.Node.Port.Group::Minus": {"image_url": f"{ICON_PATH}/Minus.svg"},
            # Port Input
            "Graph.Node.Port.Input": {
                "background_color": BORDER_DEFAULT,
                "border_color": BORDER_DEFAULT,
                "border_width": 3.0,
            },
            "Graph.Node.Port.Input:selected": {"border_color": BORDER_SELECTED},
            "Graph.Node.Port.Input.CustomColor": {"background_color": 0xFFAAAAAA},
            # Port
            "Graph.Node.Port.Branch": {"color": LABEL_COLOR, "border_width": 0.75},
            "Graph.Node.Port.Label": {
                "color": LABEL_COLOR,
                "margin_width": 5.0,
                "margin_height": 3.0,
                "font_size": 14.0,
            },
            "Graph.Node.Port.Label::output": {"alignment": ui.Alignment.RIGHT},
            "Graph.Node.Port.Label::group": {"color": 0xFFEEEEEE},
            # Port Output
            "Graph.Node.Port.Output": {
                "background_color": BACKGROUND_COLOR,
                "border_color": BORDER_DEFAULT,
                "border_width": 3.0,
            },
            "Graph.Node.Port.Output.CustomColor": {"background_color": 0x0, "border_color": 0x0},
            # Footer
            "Graph.Node.Footer": {
                "background_color": NODE_BACKGROUND,
                "border_color": BORDER_DEFAULT,
                "border_width": 3.0,
                "border_radius": 8.0,
            },
            "Graph.Node.Footer.Crop": {
                "background_color": NODE_BACKGROUND,
                "border_color": NODE_BACKGROUND,
                #                "border_width": 3.0,
            },
            "Graph.Node.Footer:selected": {"border_color": BORDER_SELECTED},
            "Graph.Node.Footer.Image": {"image_url": f"{ICON_PATH}/Default_Node.svg", "color": BORDER_DEFAULT},
            "Graph.Node.Preview.Toggle": {"image_url": f"{ICON_PATH}/Preview.svg", "color": BORDER_DEFAULT},
            "Graph.Tooltip.Background": {
                "background_color": NODE_BACKGROUND,
                "border_color": BORDER_DEFAULT,
                "border_width": 2.0,
                "border_radius": 2.0,
            },
            "Graph.Selecion.Rect": {"background_color": ui.color(1.0, 1.0, 1.0, 0.1)},
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
        # 140% lightness from the border color
        # 50% saturation from the border color
        L_MULT = 0.4
        S_MULT = 0.5

        colors = hex_to_color(color)
        hls = colorsys.rgb_to_hls(colors[0], colors[1], colors[2])

        darker_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT)), hls[2] * S_MULT)
        darker_color = color_to_hex(darker_colors)

        background_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT * 1.2)), hls[2] * S_MULT * 0.5)
        background_color = color_to_hex(background_colors)

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
            f"Graph.Connection::{name}": {
                "Tooltip": {
                    "background_color": 0x0,
                    "color": 0xFFAAAAAA,
                    "margin_width": 0,
                    "margin_height": 0,
                    "border_width": 0,
                    "border_color": 0x0,
                },
                "background_color": color,
                "color": color,
            },
            # Footer
            f"Graph.Node.Footer::{name}": {"border_color": color, "background_color": background_color},
            f"Graph.Node.Footer.Image::{name}": {"image_url": icon, "color": icon_tint_color or color},
            f"Graph.Node.Preview.Toggle::{name}": {"color": color},
            f"Graph.Node.Header.Collapse::{name}": {"background_color": color},
            f"Graph.Node.BackgroundColor::{name}": {"background_color": background_color},
            f"Graph.Node.Header.Background::{name}": {"background_color": darker_color},
            f"Graph.Node.Footer.Crop::{name}": {"background_color": background_color, "border_color": background_color},
            f"Graph.Node.Header.Port::{name}": {"background_color": color},
            f"Graph.Node.Resize::{name}": {"background_color": color},
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

        # 140% lightness from the border color
        # 50% saturation from the border color
        L_MULT = 1.2

        colors = hex_to_color(color)
        hls = colorsys.rgb_to_hls(colors[0], colors[1], colors[2])

        brighter_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT)), hls[2])
        brighter_color = color_to_hex(brighter_colors)

        style = {
            f"Graph.Node.Port.Input.CustomColor::{name}": {"background_color": color},
            f"Graph.Node.Port.Output.CustomColor::{name}": {"background_color": color, "border_color": color},
            f"Graph.Connection::{name}": {"color": color, "background_color": color},
            f"Graph.Connection::{name}:selected": {
                "border_width": 8.0,
                "background_color": brighter_color,
                "color": brighter_color,
            },
            f"Graph.Connection::{name}:hovered": {
                "border_width": 8.0,
                "background_color": brighter_color,
                "color": brighter_color,
            },
        }
        return style
