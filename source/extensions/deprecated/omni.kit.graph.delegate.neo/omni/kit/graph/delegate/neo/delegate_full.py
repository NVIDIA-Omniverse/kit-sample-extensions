# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import colorsys
from functools import partial

import omni.ui as ui
from omni.kit.widget.graph.abstract_graph_node_delegate import (
    AbstractGraphNodeDelegate,
    GraphConnectionDescription,
    GraphNodeDescription,
    GraphPortDescription,
)
from omni.kit.widget.graph.graph_model import GraphModel

# Zoom level when the text disappears and the replacement line appears
TEXT_VISIBLE_MIN = 0.7
# Zoom level when the line disappears
LINE_VISIBLE_MIN = 0.4

CONNECTION_CURVE = 60

# Constants
MARGIN_WIDTH = 7.5
MARGIN_TOP = 20.0

ICON_OFFSET = 50
ICON_SIZE = 50
HEADER_HEIGHT = 8.0
BACKGROUND_HEADER_HEIGHT = 20.0
NODE_PORT_SIZE = 7
MIN_WIDTH = 180.0


def color_to_hex(color: tuple) -> int:
    """Convert float rgb to int"""

    def to_int(f: float) -> int:
        return int(255 * max(0.0, min(1.0, f)))

    red = to_int(color[0])
    green = to_int(color[1])
    blue = to_int(color[2])
    alpha = to_int(color[3]) if len(color) > 3 else 255
    return (alpha << 8 * 3) + (blue << 8 * 2) + (green << 8 * 1) + red


def hex_to_color(hex: int) -> tuple:
    """convert Value from int"""
    red = hex & 255
    green = (hex >> 8) & 255
    blue = (hex >> 16) & 255
    alpha = (hex >> 24) & 255
    rgba_values = (red / 255, green / 255, blue / 255, alpha / 255)
    return rgba_values


tooltip_style = {
    "Tooltip": {
        "background_color": 0x0,
        "margin_width": 0,
        "margin_height": 0,
        "border_width": 0,
    }
}


class NeoGraphNodeDelegateFull(AbstractGraphNodeDelegate):
    """
    The delegate with the Neo design for full node.
    """

    def darker_color(self, rgb_color):
        L_MULT = 0.4
        S_MULT = 0.5

        hls = colorsys.rgb_to_hls(rgb_color[0], rgb_color[1], rgb_color[2])
        darker_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT)), hls[2] * S_MULT)
        darker_color = color_to_hex(darker_colors)
        return darker_color

    def background_color(self, rgb_color):
        L_MULT = 0.4
        S_MULT = 0.5

        hls = colorsys.rgb_to_hls(rgb_color[0], rgb_color[1], rgb_color[2])

        background_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT * 1.2)), hls[2] * S_MULT * 0.5)
        background_color = color_to_hex(background_colors)
        return background_color

    def __init__(self, *args):
        super().__init__()
        self._bezier_connection = True
        self._show_icon = True
        self._top_preview = False

    def node_background(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the node background"""
        node = node_desc.node
        style_name = str(model[node].type)

        with ui.ZStack():
            with ui.HStack():
                # Left offset
                ui.Spacer(width=MARGIN_WIDTH)

                with ui.VStack():
                    ui.Spacer(height=MARGIN_TOP)

                    # The node body
                    with ui.ZStack():
                        # This trick makes min width
                        ui.Spacer(width=MIN_WIDTH)

                        # for backdrops, we have a different style
                        display_color = model[node].display_color
                        if display_color:
                            style = {
                                f"Graph.Node.Border::{style_name}": {"background_color": color_to_hex(display_color)},
                                f"Graph.Node.Header.Background::{style_name}": {
                                    "background_color": self.darker_color(display_color)
                                },
                                f"Graph.Node.BackgroundColor::{style_name}": {
                                    "background_color": self.background_color(display_color)
                                },
                            }
                        else:
                            style = {}

                        # Header Background
                        with ui.VStack():
                            ui.Rectangle(
                                name=style_name, style=style, style_type_name_override="Graph.Node.BackgroundColor"
                            )

                            # if we show the icon we need to offet the background vertically
                            if self._show_icon and not (
                                model[node].preview and model[node].preview_state == GraphModel.ExpansionState.OPEN
                            ):
                                ui.Spacer(height=ICON_OFFSET)

                        # Top Header Color
                        ui.Rectangle(
                            height=HEADER_HEIGHT,
                            name=style_name,
                            style=style,
                            style_type_name_override="Graph.Node.Border",
                        )

                        # Header Background Color
                        with ui.VStack():
                            ui.Spacer(height=HEADER_HEIGHT)
                            ui.Rectangle(
                                height=BACKGROUND_HEADER_HEIGHT,
                                name=style_name,
                                style=style,
                                style_type_name_override="Graph.Node.Header.Background",
                            )

                        if (
                            self._top_preview
                            and model[node].preview
                            and model[node].preview_state == GraphModel.ExpansionState.OPEN
                        ):
                            with ui.VStack():
                                ui.Spacer(height=HEADER_HEIGHT + BACKGROUND_HEADER_HEIGHT)
                                self._build_image_preview_image(model, node_desc)
                                ui.Rectangle(
                                    height=4, name=style_name, style=style, style_type_name_override="Graph.Node.Border"
                                )

                        # Build Bottom Node Rectangle
                        # if we show the icon we need to offet the background vertically
                        if not self._show_icon:
                            with ui.VStack():
                                ui.Spacer()
                                ui.Rectangle(
                                    height=4, name=style_name, style=style, style_type_name_override="Graph.Node.Border"
                                )
                        else:
                            with ui.VStack(visible_min=TEXT_VISIBLE_MIN):
                                ui.Spacer()
                                ui.Spacer(height=10)
                                self._build_icon_footer(model, node_desc)

                            if (
                                self._top_preview
                                and model[node].preview
                                and model[node].preview_state == GraphModel.ExpansionState.OPEN
                            ):
                                pass
                            else:
                                # when the Icons become invisible
                                with ui.VStack(visible_max=TEXT_VISIBLE_MIN):
                                    ui.Spacer()
                                    ui.Spacer(height=10)
                                    ui.Rectangle(
                                        name=style_name,
                                        style=style,
                                        style_type_name_override="Graph.Node.BackgroundColor",
                                    )
                                    ui.Rectangle(
                                        height=6,
                                        name=style_name,
                                        style=style,
                                        style_type_name_override="Graph.Node.Border",
                                    )

                # Right offset
                ui.Spacer(width=MARGIN_WIDTH)

            if self._show_icon:
                # Preview Icons When Zoomed Out
                with ui.VStack(visible_max=TEXT_VISIBLE_MIN):
                    ui.Spacer()
                    if (
                        self._top_preview
                        and model[node].preview
                        and model[node].preview_state == GraphModel.ExpansionState.OPEN
                    ):
                        ui.Spacer(height=185)
                    with ui.HStack():
                        ui.Spacer()
                        ui.Image(
                            width=70, height=70, style_type_name_override="Graph.Node.Footer.Image", name=style_name
                        )
                        ui.Spacer()
                    ui.Spacer()

    def _build_icon_footer(self, model, node_desc: GraphNodeDescription):
        node = node_desc.node
        style_name = str(model[node].type)
        with ui.VStack():
            ui.Spacer()
            if (
                not self._top_preview
                and model[node].preview
                and model[node].preview_state == GraphModel.ExpansionState.OPEN
            ):
                ui.Rectangle(height=4, name=style_name, style_type_name_override="Graph.Node.Border")
            else:
                with ui.ZStack(height=0, visible_min=TEXT_VISIBLE_MIN):
                    with ui.HStack():
                        ui.Spacer()
                        ui.Circle(
                            width=ICON_SIZE,
                            height=ICON_SIZE + 3,
                            style_type_name_override="Graph.Node.Footer",
                            name=style_name,
                        )
                        ui.Spacer()

                    with ui.VStack():
                        ui.Rectangle(
                            style_type_name_override="Graph.Node.Footer.Crop",
                            name=style_name,
                            visible_min=TEXT_VISIBLE_MIN,
                        )
                        ui.Rectangle(height=4, name=style_name, style_type_name_override="Graph.Node.Border")
                        ui.Spacer(height=18)

                    with ui.HStack():
                        ui.Spacer()
                        ui.Circle(
                            width=ICON_SIZE,
                            height=ICON_SIZE - 1.5,
                            style_type_name_override="Graph.Node.Footer.Crop",
                            name=style_name,
                            visible_min=TEXT_VISIBLE_MIN,
                        )
                        ui.Spacer()

                    with ui.VStack():
                        ui.Spacer(width=0, height=10)
                        ui.Image(
                            style_type_name_override="Graph.Node.Footer.Image",
                            name=style_name,
                            visible_min=TEXT_VISIBLE_MIN,
                        )
                        ui.Spacer(width=0, height=10)

    def node_header_input(self, model, node_desc: GraphNodeDescription):
        """Called to create the left part of the header that will be used as input when the node is collapsed"""
        node = node_desc.node
        if not model[node].expansion_state or model[node].expansion_state == GraphModel.ExpansionState.OPEN:
            ui.Spacer(height=2 * NODE_PORT_SIZE)
            return

        style_name = str(model[node].type)

        with ui.HStack():
            # Left offset
            ui.Spacer(width=MARGIN_WIDTH - NODE_PORT_SIZE)
            with ui.VStack():
                ui.Spacer(height=MARGIN_TOP + HEADER_HEIGHT + NODE_PORT_SIZE - 4)
                ui.Rectangle(
                    width=2 * NODE_PORT_SIZE,
                    height=2 * NODE_PORT_SIZE,
                    name=style_name,
                    style_type_name_override="Graph.Node.Header.Port",
                )

    def node_header_output(self, model, node_desc: GraphNodeDescription):
        """Called to create the right part of the header that will be used as output when the node is collapsed"""
        node = node_desc.node
        if not model[node].expansion_state or model[node].expansion_state == GraphModel.ExpansionState.OPEN:
            ui.Spacer(height=2 * NODE_PORT_SIZE)
            return

        style_name = str(model[node].type)

        with ui.HStack():
            # Left offset
            ui.Spacer(width=MARGIN_WIDTH + NODE_PORT_SIZE)
            with ui.VStack():
                ui.Spacer(height=MARGIN_TOP + HEADER_HEIGHT + NODE_PORT_SIZE - 4)
                ui.Rectangle(
                    width=2 * NODE_PORT_SIZE,
                    height=2 * NODE_PORT_SIZE,
                    name=style_name,
                    style_type_name_override="Graph.Node.Header.Port",
                )

    def _build_collapse_bt(self, model, node):
        style_name = str(model[node].type)

        if not model[node].expansion_state:
            return

        def switch_expansion(model, node):
            current = model[node].expansion_state
            model[node].expansion_state = GraphModel.ExpansionState((current.value + 1) % 3)

        with ui.HStack():
            ui.Spacer()
            ui.Spacer(width=12)
            # Collapse button
            collapse = ui.Triangle(
                width=12,
                height=12,
                name=style_name,
                visible_min=LINE_VISIBLE_MIN,
                style_type_name_override="Graph.Node.Header.Collapse",
            )
            ui.Spacer()

            expansion_state = model[node].expansion_state
            if expansion_state == GraphModel.ExpansionState.CLOSED:
                collapse.alignment = ui.Alignment.CENTER_TOP
            elif expansion_state == GraphModel.ExpansionState.MINIMIZED:
                collapse.alignment = ui.Alignment.RIGHT_CENTER
            else:
                collapse.alignment = ui.Alignment.CENTER_BOTTOM

            collapse.set_mouse_pressed_fn(lambda x, y, b, m, model=model, node=node: switch_expansion(model, node))

    def _common_node_header_top(self, model, node, show_collapse=True):
        """Node header part that is used in both full and closed states"""
        # Draw the node name and a bit of space
        with ui.HStack():
            ui.Spacer(width=MARGIN_WIDTH)

            with ui.ZStack():

                with ui.ZStack():
                    label = ui.Label(
                        model[node].name,
                        style_type_name_override="Graph.Node.Header.Label",
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                    # Renaming Widget
                    label_field = ui.StringField()
                    label_field.visible = False

                    def show_edit_field(field, *args):
                        field.model.set_value(model[node].name)
                        field.visible = True

                    label.set_mouse_double_clicked_fn(partial(show_edit_field, label_field))

                    def label_edited(field, *args):
                        field.visible = False
                        model[node].name = field.model.as_string
                        model._item_changed(None)

                    label_field.model.add_end_edit_fn(partial(label_edited, label_field))

                with ui.Placer(
                    stable_size=True, visible_min=LINE_VISIBLE_MIN, visible_max=TEXT_VISIBLE_MIN, offset_y=-6
                ):
                    ui.Label(model[node].name, name="Degenerated", style_type_name_override="Graph.Node.Header.Label")

        if show_collapse:
            ui.Spacer(height=14)
            self._build_collapse_bt(model, node)

            ui.Spacer(width=MARGIN_WIDTH)

    def node_header(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the top of the node"""
        node = node_desc.node
        with ui.VStack(height=0, skip_draw_when_clipped=True):
            self._common_node_header_top(model, node_desc.node)
            ui.Spacer(height=5)
            if (
                self._top_preview
                and model[node].preview
                and model[node].preview_state == GraphModel.ExpansionState.OPEN
            ):
                ui.Spacer(height=185)

    def _build_image_preview_image(self, model, node_desc: GraphNodeDescription):
        """Create the Image Preview on the Footer or the Header depending on the Layout Mode"""
        node = node_desc.node
        style_name = str(model[node].type)
        preview_data = model[node].preview  # New API
        if not preview_data:
            return

        with ui.ZStack(height=0):
            ui.Image(preview_data, height=180)
            with ui.VStack(visible_min=LINE_VISIBLE_MIN, skip_draw_when_clipped=True):
                ui.Spacer()
                with ui.HStack(height=0):
                    ui.Spacer()

                    def toggle_image(model, node, *args):
                        if model[node].preview_state == GraphModel.ExpansionState.OPEN:
                            model[node].preview_state = GraphModel.ExpansionState.MINIMIZED
                        else:
                            model[node].preview_state = GraphModel.ExpansionState.OPEN
                        model._item_changed(None)

                    with ui.HStack(height=0):
                        ui.Spacer()
                        ui.Image(
                            width=20,
                            height=15,
                            style_type_name_override="Graph.Node.Preview.Toggle",
                            name=style_name,
                            mouse_pressed_fn=partial(toggle_image, model, node),
                        )

                    ui.Spacer(width=5)

                ui.Spacer(height=5)

    def _build_image_preview(self, model, node_desc: GraphNodeDescription):
        """Create the Image Preview on the Footer or the Header depending on the Layout Mode"""

        node = node_desc.node
        style_name = str(model[node].type)

        with ui.ZStack():
            with ui.HStack():
                # Left offset
                ui.Spacer(width=MARGIN_WIDTH)

                with ui.VStack():
                    ui.Spacer(height=4)
                    # Top Header Color
                    ui.Rectangle(height=2, name=style_name, style_type_name_override="Graph.Node.Border")

                    preview_data = model[node].preview  # New API
                    if preview_data:
                        self._build_image_preview_image(model, node_desc)
                    ui.Spacer(height=4)

                ui.Spacer(width=MARGIN_WIDTH)

    def node_footer(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the bottom of the node"""
        node = node_desc.node
        style_name = str(model[node].type)
        # Draw the circle and the image on the top of it

        preview_data = model[node].preview  # New API
        if not self._top_preview and preview_data and model[node].preview_state == GraphModel.ExpansionState.OPEN:
            self._build_image_preview(model, node_desc)
        else:
            if preview_data:
                ui.Spacer(height=ICON_SIZE - 5)
                with ui.VStack(visible_min=LINE_VISIBLE_MIN, skip_draw_when_clipped=True):
                    ui.Spacer()

                    def toggle_image(model, node, *args):
                        if model[node].preview_state == GraphModel.ExpansionState.OPEN:
                            model[node].preview_state = GraphModel.ExpansionState.MINIMIZED
                        else:
                            model[node].preview_state = GraphModel.ExpansionState.OPEN
                        model._item_changed(None)

                    with ui.HStack(height=0):
                        ui.Spacer()
                        ui.Image(
                            width=20,
                            height=15,
                            style_type_name_override="Graph.Node.Preview.Toggle",
                            name=style_name,
                            mouse_pressed_fn=partial(toggle_image, model, node),
                        )
                        ui.Spacer(width=MARGIN_WIDTH + 3)
                    ui.Spacer(height=25)
            else:
                ui.Spacer(height=ICON_SIZE - 5)

    def tooltip(self, tooltip_str):
        padding = 5
        with ui.ZStack():
            ui.Rectangle(style_type_name_override="Graph.Tooltip.Background")
            with ui.VStack():
                ui.Spacer(height=padding)
                with ui.HStack():
                    ui.Spacer(width=padding)
                    ui.Label(
                        tooltip_str,
                        style={"font_size": 16},
                    )
                    ui.Spacer(width=padding)
                ui.Spacer(height=padding)

    def port_input(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        """Called to create the left part of the port that will be used as input"""
        port = port_desc.port
        if port is None:
            ui.Spacer(width=75)
            return

        inputs = model[port].inputs
        if inputs is None:
            return

        sub_ports = model[port].ports

        is_group = sub_ports is not None
        if is_group:
            ui.Spacer(width=10)
            return

        port_type = str(model[port].type)

        with ui.ZStack():
            level = port_desc.level
            if level > 0 or is_group:
                with ui.HStack():
                    ui.Spacer(height=4)

            with ui.VStack(tooltip_fn=lambda: self.tooltip(port_type), style=tooltip_style):
                ui.Spacer(height=4)
                customcolor_style_type_name = "Graph.Node.Port.Input.CustomColor"
                connected_source = port_desc.connected_source
                if connected_source:
                    with ui.HStack():
                        ui.Spacer(width=2)
                        ui.Rectangle(
                            width=12, height=12, name=port_type, style_type_name_override=customcolor_style_type_name
                        )
                else:
                    with ui.HStack():
                        ui.Spacer(width=8)
                        ui.Rectangle(
                            width=6,
                            height=12,
                            name=port_type,
                            visible_min=LINE_VISIBLE_MIN,
                            style_type_name_override=customcolor_style_type_name,
                        )
                ui.Spacer(height=4)

    def port_output(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        """Called to create the right part of the port that will be used as output"""
        """Called to create the left part of the port that will be used as input"""
        port = port_desc.port
        if port is None:
            ui.Spacer(width=75)
            return

        outputs = model[port].outputs
        if outputs is None:
            return

        port_type = str(model[port].type)

        with ui.VStack(tooltip_fn=lambda: self.tooltip(port_type), style=tooltip_style):
            ui.Spacer(height=4)
            customcolor_style_type_name = "Graph.Node.Port.Output.CustomColor"
            connected_source = port_desc.connected_source
            if connected_source:
                with ui.HStack():
                    ui.Rectangle(
                        width=12, height=12, name=port_type, style_type_name_override=customcolor_style_type_name
                    )
                    ui.Spacer(width=4)
            else:
                with ui.HStack():
                    ui.Rectangle(
                        width=6,
                        height=12,
                        name=port_type,
                        visible_min=LINE_VISIBLE_MIN,
                        style_type_name_override=customcolor_style_type_name,
                    )
                    ui.Spacer(width=8)
            ui.Spacer(height=4)

    def port(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        """Called to create the middle part of the port"""
        port = port_desc.port
        if port is None:
            return

        sub_ports = model[port].ports
        is_group = sub_ports is not None

        inputs = model[port].inputs
        is_input = inputs is not None

        if is_group:
            style_name = "group"
        elif is_input:
            style_name = "input"
        else:
            style_name = "output"

        with ui.ZStack():
            level = port_desc.level
            if level > 0:
                with ui.HStack():
                    ui.Rectangle(
                        name=model[node_desc.node].type,
                        style_type_name_override="Graph.Node.BackgroundColor",
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                    ui.Spacer(width=MARGIN_WIDTH)

            with ui.HStack():
                if level > 0:
                    style_type_name_override = "Graph.Node.Port.Branch"
                    if port_desc.relative_position == port_desc.parent_child_count - 1:
                        ui.Line(
                            width=4,
                            height=ui.Percent(50),
                            style_type_name_override=style_type_name_override,
                            alignment=ui.Alignment.RIGHT,
                            visible_min=TEXT_VISIBLE_MIN,
                        )
                    else:
                        ui.Line(
                            width=4,
                            style_type_name_override=style_type_name_override,
                            alignment=ui.Alignment.RIGHT,
                            visible_min=TEXT_VISIBLE_MIN,
                        )
                    ui.Line(width=8, style_type_name_override=style_type_name_override, visible_min=TEXT_VISIBLE_MIN)

                if is_group:
                    # +/- button
                    with ui.ZStack(width=0):
                        state = model[port].expansion_state
                        if state == GraphModel.ExpansionState.CLOSED:
                            image_name = "Plus"
                            next_state = GraphModel.ExpansionState.OPEN
                        else:
                            image_name = "Minus"
                            next_state = GraphModel.ExpansionState.CLOSED

                        def set_expansion_state(model, port, state: GraphModel.ExpansionState, *args):
                            model[port].expansion_state = state

                        ui.Image(
                            width=10,
                            style_type_name_override="Graph.Node.Port.Group",
                            name=image_name,
                            visible_min=TEXT_VISIBLE_MIN,
                            mouse_pressed_fn=partial(set_expansion_state, model, port, next_state),
                        )
                ui.Label(
                    model[port].name,
                    style_type_name_override="Graph.Node.Port.Label",
                    name=style_name,
                    visible_min=TEXT_VISIBLE_MIN,
                )

    def connection(
        self, model, source: GraphConnectionDescription, target: GraphConnectionDescription, foreground: bool = False
    ):
        """Called to create the connection between ports"""
        port_type = str(model[source.port].type)

        # If the connection is reversed, we need to mirror tangents
        source_reversed_tangent = -1.0 if target.is_tangent_reversed else 1.0
        target_reversed_tangent = -1.0 if source.is_tangent_reversed else 1.0

        if self._bezier_connection:
            with ui.ZStack():
                ui.FreeLine(
                    target.widget,
                    source.widget,
                    alignment=ui.Alignment.UNDEFINED,
                    style=tooltip_style,
                    name=port_type,
                    visible_max=LINE_VISIBLE_MIN,
                    style_type_name_override="Graph.Connection",
                )
                tooltip_str = f"{model[source.node].name}.{model[source.port].name} --> {model[target.node].name}.{model[target.port].name}"
                ui.FreeBezierCurve(
                    target.widget,
                    source.widget,
                    start_tangent_width=ui.Percent(-CONNECTION_CURVE * source_reversed_tangent),
                    end_tangent_width=ui.Percent(CONNECTION_CURVE * target_reversed_tangent),
                    name=port_type,
                    style=tooltip_style,
                    tooltip_fn=lambda: self.tooltip(tooltip_str),
                    visible_min=LINE_VISIBLE_MIN,
                    style_type_name_override="Graph.Connection",
                )
        else:
            ui.FreeLine(
                target.widget,
                source.widget,
                style=tooltip_style,
                alignment=ui.Alignment.UNDEFINED,
                name=port_type,
                style_type_name_override="Graph.Connection",
            )
