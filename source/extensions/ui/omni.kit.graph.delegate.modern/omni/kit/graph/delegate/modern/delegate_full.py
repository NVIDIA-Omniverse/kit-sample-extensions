# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from functools import partial
from pathlib import Path
from typing import Tuple

import omni.ui as ui
from omni.kit.widget.graph.abstract_graph_node_delegate import (
    AbstractGraphNodeDelegate,
    GraphConnectionDescription,
    GraphNodeDescription,
    GraphPortDescription,
)
from omni.kit.widget.graph.graph_model import GraphModel
from omni.ui import color as cl

NODE_MIN_WIDTH = 200
BACKGROUND_RADIUS = 9.0
# Zoom level when the port text disappears
TEXT_VISIBLE_MIN = 0.65

# Zoom level when the port disapears
PORT_VISIBLE_MIN = 0.35
PORT_RADIUS = 6

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")

HIGHLIGHT_THICKNESS = 8.0
CONNECTION_PORT_WIDTH = 11.0
NODE_WIDTH_MARGIN = max(HIGHLIGHT_THICKNESS, CONNECTION_PORT_WIDTH)
INPUT_PORT_WIDTH_MARGIN = NODE_WIDTH_MARGIN + 1
OUTPUT_PORT_WIDTH_MARGIN = 9.0

PORT_HEIGHT = 20

HEADER = {
    "margin_to_left": 8,
    "margin_to_left_zoom_in": 14,
    "sec_height": 23,
    "note_sec_height": 14,
    "height": 3,
    "margin_to_ports": NODE_WIDTH_MARGIN,
}

STATE_TOGGER = {
    "radius": 2,
    "margin": 4,
    "spacing": 1,
}

ICON = {
    "height": 38,
    "width": 38,
    "border": 1.5,
    "radius": 9,
}


class GraphNodeDelegateFull(AbstractGraphNodeDelegate):
    """
    The delegate with the Omniverse design.
    """

    def __init__(self, *args):
        super().__init__()

    def _display_color_style(self, display_color, style_name: str, style_field: str, fallback=None):
        if display_color:
            style = {style_name: {style_field: cl(*display_color)}}
        else:
            style = fallback

        return style

    def _build_rectangle(
        self, radius, draw_top, type_name, name, style_override=None, top_round=False, bottom_round=False
    ):
        """
        Build rectangle of the specific design.

        Args:
            radius: The radius of round corners. The corners are top-left and
                    bottom-right.
            draw_top: When false the top corners are straight.
            type_name: style_type_name_override of each widget
            name: name of each widget
            style_override: the style to apply to the top level node
            top_round: make both top corners rounded
            bottom_round: make both bottom corners rounded
        """
        stack = ui.VStack(alignment=ui.Alignment.CENTER)
        if style_override:
            stack.set_style(style_override)

        with stack:
            # Top of the rectangle
            if draw_top:
                with ui.HStack(height=0):
                    ui.Circle(
                        radius=radius,
                        width=0,
                        height=0,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        alignment=ui.Alignment.RIGHT_BOTTOM,
                        style_type_name_override=type_name,
                        name=name,
                    )
                    ui.Rectangle(style_type_name_override=type_name, name=name)
                    if top_round:
                        ui.Circle(
                            radius=radius,
                            width=0,
                            height=0,
                            size_policy=ui.CircleSizePolicy.FIXED,
                            alignment=ui.Alignment.LEFT_BOTTOM,
                            style_type_name_override=type_name,
                            name=name,
                        )
            else:
                ui.Rectangle(style_type_name_override=type_name, name=name)

            # Middle of the rectangle
            ui.Rectangle(style_type_name_override=type_name, name=name)

            # Bottom of the rectangle
            with ui.HStack(height=0):
                if bottom_round:
                    ui.Circle(
                        radius=radius,
                        width=0,
                        height=0,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        alignment=ui.Alignment.RIGHT_TOP,
                        style_type_name_override=type_name,
                        name=name,
                    )
                ui.Rectangle(style_type_name_override=type_name, name=name)
                ui.Circle(
                    radius=radius,
                    width=0,
                    height=0,
                    size_policy=ui.CircleSizePolicy.FIXED,
                    alignment=ui.Alignment.LEFT_TOP,
                    style_type_name_override=type_name,
                    name=name,
                )

    def switch_expansion(self, model, node):
        current = model[node].expansion_state
        model[node].expansion_state = GraphModel.ExpansionState((current.value + 1) % 3)

    def build_expansion_widget(self, model, node, style_name):
        def create_tooltip(spacing=3):
            with ui.VStack():
                ui.Label(
                    "Node Display - Toggles between the three different methods of displaying the node.",
                    style_type_name_override="Graph.Port.Tooltip.Label",
                )
                ui.Spacer(height=3)
                ui.Line(alignment=ui.Alignment.BOTTOM)
                ui.Spacer(height=3)
                ui.Label("... Expand Node - Full node display.", style_type_name_override="Graph.Port.Tooltip.Label")
                ui.Label(
                    " .. Minimize Node - Only show connected ports.",
                    style_type_name_override="Graph.Port.Tooltip.Label",
                )
                ui.Label(
                    "  . Close Node - Smallest display. Connections all go into one port.",
                    style_type_name_override="Graph.Port.Tooltip.Label",
                )

        collapse = ui.HStack(width=14, visible_min=PORT_VISIBLE_MIN, tooltip_fn=create_tooltip)
        with collapse:
            ui.Circle(
                radius=STATE_TOGGER["radius"],
                size_policy=ui.CircleSizePolicy.FIXED,
                name=style_name,
                style_type_name_override="Graph.Node.Category",
            )
            if model[node].expansion_state.value == 2:
                override_type = "Graph.Node.Secondary"
            else:
                override_type = "Graph.Node.Category"
            ui.Circle(
                radius=STATE_TOGGER["radius"],
                size_policy=ui.CircleSizePolicy.FIXED,
                name=style_name,
                style_type_name_override=override_type,
            )
            if model[node].expansion_state.value % 3:
                override_type = "Graph.Node.Secondary"
            else:
                override_type = "Graph.Node.Category"
            ui.Circle(
                radius=STATE_TOGGER["radius"],
                size_policy=ui.CircleSizePolicy.FIXED,
                name=style_name,
                style_type_name_override=override_type,
            )
        collapse.set_mouse_pressed_fn(lambda x, y, b, m, model=model, node=node: self.switch_expansion(model, node))
        return collapse

    def _build_header(self, model, node_desc: GraphNodeDescription):
        header = ui.VStack()
        with header:
            node = node_desc.node
            node_name = model[node].name
            node_category = str(model[node].type)

            ui.Spacer(height=NODE_WIDTH_MARGIN)
            with ui.ZStack():
                GraphNodeDelegateFull.build_tooltip([node_name, node_category])
                if model[node].expansion_state.value == 2:
                    with ui.VStack(visible_max=PORT_VISIBLE_MIN):
                        self._draw_icon(ICON["width"], node_category)
                with ui.HStack():
                    # icon
                    with ui.ZStack(height=ICON["height"], width=ICON["width"]):
                        with ui.VStack(visible_min=TEXT_VISIBLE_MIN):
                            self._draw_icon(ICON["width"], node_category)
                        # new header (the part that covers the icon space) when zoomed out
                        with ui.VStack(visible_max=TEXT_VISIBLE_MIN, visible_min=PORT_VISIBLE_MIN):
                            ui.Rectangle(
                                height=HEADER["sec_height"],
                                name=node_category,
                                style_type_name_override="Graph.Node.Secondary",
                            )
                            ui.Rectangle(
                                height=HEADER["height"],
                                name=node_category,
                                style_type_name_override="Graph.Node.Category",
                            )

                    # label
                    with ui.VStack():
                        # the header text with background
                        with ui.ZStack(height=HEADER["sec_height"]):
                            ui.Rectangle(
                                visible_min=PORT_VISIBLE_MIN,
                                name=node_category,
                                style_type_name_override="Graph.Node.Secondary",
                            )
                            label = ui.Label(
                                node_name,
                                visible_min=TEXT_VISIBLE_MIN,
                                style_type_name_override="Graph.Node.Label",
                                style={"margin_width": HEADER["margin_to_left"]},
                            )

                            # Renaming Widget
                            label_field = ui.StringField()
                            label_field.visible = False

                            def show_edit_field(field, *args):
                                field.model.set_value(node_name)
                                field.visible = True

                            label.set_mouse_double_clicked_fn(partial(show_edit_field, label_field))

                            def label_edited(field, *args):
                                field.visible = False
                                model[node].name = field.model.as_string
                                model._item_changed(None)

                            label_field.model.add_end_edit_fn(partial(label_edited, label_field))

                        ui.Rectangle(
                            visible_min=PORT_VISIBLE_MIN,
                            height=HEADER["height"],
                            name=node_category,
                            style_type_name_override="Graph.Node.Category",
                        )
                        # the expansion button
                        ui.Spacer(height=STATE_TOGGER["margin"])
                        with ui.HStack():
                            ui.Spacer()
                            self.build_expansion_widget(model, node, node_category)
                            ui.Spacer(width=STATE_TOGGER["margin"])
                        ui.Spacer(height=STATE_TOGGER["margin"])
                ui.Label(
                    model[node].name,
                    height=HEADER["sec_height"],
                    visible_max=TEXT_VISIBLE_MIN,
                    visible_min=PORT_VISIBLE_MIN,
                    style_type_name_override="Graph.Node.Label.ZoomIn",
                    style={"margin_width": HEADER["margin_to_left_zoom_in"]},
                )
            ui.Spacer(height=NODE_WIDTH_MARGIN)
        return header

    def node_header(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the top of the node"""
        header = self._build_header(model, node_desc)
        return header

    def _draw_icon(self, icon_size, node_category):
        with ui.HStack(height=icon_size):
            ui.Spacer()
            icon_scale = icon_size / float(ICON["width"])
            with ui.ZStack(width=icon_size):
                # icon border
                outter_icon_radius = ICON["radius"] * icon_scale
                self._build_rectangle(outter_icon_radius, True, "Graph.Node.Category", node_category)
                # icon image
                icon_border = ICON["border"] * icon_scale
                with ui.HStack():
                    ui.Spacer(width=icon_border)
                    with ui.VStack():
                        ui.Spacer(height=icon_border)
                        with ui.ZStack():
                            self._build_rectangle(
                                outter_icon_radius - icon_border, True, "Graph.Node.Icon.Background", node_category
                            )
                            image_width = (ICON["width"] - ICON["border"]) * icon_scale
                            image_height = (ICON["height"] - ICON["border"]) * icon_scale
                            image = ui.ImageWithProvider(
                                style_type_name_override="Graph.Node.Icon",
                                name=node_category,
                                width=image_width,
                                height=image_height,
                                fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                            )
                            # Rasterize with big resolution
                            if hasattr(image, "prepare_draw"):
                                image.prepare_draw(1024, 1024)
                        ui.Spacer(height=icon_border)
                    ui.Spacer(width=icon_border)
            ui.Spacer()

    def _common_node_background(self, model, node, draw_icon: bool):
        """Called to create widgets of the node background"""
        node_type = str(model[node].type)
        HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE = 4.0
        HIGHLIGHT_THICKNESS_ZOOM_OUT = 6.0

        NODE_HEADER = ICON["height"] + HEADER["margin_to_ports"]

        ports = model[node].ports
        size_of_ports = len(ports)

        for port in ports:
            sub_ports = model[port].ports
            is_group = sub_ports is not None and len(sub_ports) > 0
            if is_group and model[port].expansion_state == GraphModel.ExpansionState.OPEN:
                size_of_ports += len(sub_ports)

        PORTS_HEIGHT = PORT_HEIGHT * size_of_ports
        if model[node].expansion_state.value == 1:
            PORTS_HEIGHT = PORT_HEIGHT * len(model[node].connected_ports)

        # The node body
        background = ui.ZStack()
        with background:
            GraphNodeDelegateFull.build_tooltip([model[node].name, node_type], None, TEXT_VISIBLE_MIN)

            # This trick makes min width
            ui.Spacer(width=NODE_MIN_WIDTH)
            # highlight
            with ui.VStack(visible_max=PORT_VISIBLE_MIN):
                self._build_rectangle(BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS, True, "Graph.Node.Border", node_type)

            # zoomed out highlight
            # this is shown during the zoom in between PORT_VISIBLE_MIN to TEXT_VISIBLE_MIN
            margin = NODE_WIDTH_MARGIN - HIGHLIGHT_THICKNESS_ZOOM_OUT
            with ui.HStack(visible_max=TEXT_VISIBLE_MIN, visible_min=PORT_VISIBLE_MIN):
                ui.Spacer(width=margin)
                with ui.VStack():
                    ui.Spacer(height=margin)
                    with ui.ZStack():
                        self._build_rectangle(
                            BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS_ZOOM_OUT, False, "Graph.Node.Border", node_type
                        )
                    ui.Spacer(height=margin)
                ui.Spacer(width=margin)

            # zoomed out more hightlight
            # this is shown duing when the zoom is > TEXT_VISIBLE_MIN
            margin = NODE_WIDTH_MARGIN - HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE
            with ui.HStack(visible_min=TEXT_VISIBLE_MIN):
                ui.Spacer(width=margin)
                with ui.VStack():
                    ui.Spacer(height=margin)
                    self._build_rectangle(
                        BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE, True, "Graph.Node.Border", node_type
                    )
                    ui.Spacer(height=margin)
                ui.Spacer(width=margin)

            # node
            with ui.HStack():
                ui.Spacer(width=NODE_WIDTH_MARGIN)
                with ui.VStack():
                    ui.Spacer(height=NODE_WIDTH_MARGIN)
                    with ui.ZStack():
                        # background, this is shown across the whole zoom level
                        self._build_rectangle(BACKGROUND_RADIUS, True, "Graph.Node.Background", node_type)
                        if draw_icon:
                            with ui.VStack(visible_max=PORT_VISIBLE_MIN):
                                ui.Spacer()
                                # this icon_size is not accurate, since there is no way to find the actual width of the node
                                # we use NODE_MIN_WIDTH
                                icon_size = min(NODE_MIN_WIDTH, PORTS_HEIGHT + NODE_HEADER)
                                self._draw_icon(icon_size, node_type)
                                ui.Spacer()
                    ui.Spacer(height=NODE_WIDTH_MARGIN)
                ui.Spacer(width=NODE_WIDTH_MARGIN)

            if draw_icon:
                # zoom in icon in the middle
                # this is shown during the zoom in between PORT_VISIBLE_MIN to TEXT_VISIBLE_MIN
                icon_size = min(NODE_MIN_WIDTH, PORTS_HEIGHT)
                with ui.VStack(visible_max=TEXT_VISIBLE_MIN, visible_min=PORT_VISIBLE_MIN):
                    ui.Spacer(height=NODE_HEADER)
                    # this icon_size is not accurate, since there is no way to find the actual width of the node
                    # we use NODE_MIN_WIDTH
                    self._draw_icon(icon_size, node_type)
        return background

    def node_background(self, model, node_desc: GraphNodeDescription):
        background = self._common_node_background(model, node_desc.node, True)
        return background

    def node_header_input(self, model, node_desc: GraphNodeDescription):
        """Called to create the left part of the header that will be used as input when the node is collapsed"""
        return ui.Spacer(width=NODE_WIDTH_MARGIN)

    def node_header_output(self, model, node_desc: GraphNodeDescription):
        """Called to create the right part of the header that will be used as output when the node is collapsed"""
        return ui.Spacer(width=NODE_WIDTH_MARGIN)

    def node_footer(self, model, node_desc: GraphNodeDescription):
        return ui.Spacer(height=16)

    @staticmethod
    def build_tooltip(text_tips=[], visible_min=None, visible_max=None):
        def tooltip():
            padding = 2
            with ui.VStack():
                ui.Spacer(height=padding)
                with ui.HStack():
                    ui.Spacer(width=padding)
                    message = ""
                    for text in text_tips:
                        if message:
                            message += "\n"
                        message += f"{text}"
                    ui.Label(
                        message,
                        style_type_name_override="Graph.Port.Tooltip.Label",
                    )
                    ui.Spacer(width=padding)
                ui.Spacer(height=padding)

        kwargs = {"tooltip_fn": lambda: tooltip()}

        if visible_min is not None:
            kwargs["visible_min"] = visible_min

        if visible_max is not None:
            kwargs["visible_max"] = visible_max

        ui.Frame(style={"Tooltip": {"background_color": 0xFF99CCCC}}, **kwargs)

    def port_input(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        style = {}
        return GraphNodeDelegateFull.build_port_input(model, node_desc, port_desc, style, "Graph.Connection")

    @staticmethod
    def build_port_input(model, node_desc, port_desc, style, override_style_name):
        INPUT_VALUE_WIDTH = 11
        INPUT_VALUE_HEIGHT = 17

        port = port_desc.port
        if model[port].inputs is None:
            return

        port_type = str(model[port].type)
        port_name = model[port].name

        sub_ports = model[port].ports
        is_group = sub_ports is not None and len(sub_ports) > 0

        stack = ui.ZStack()
        with stack:
            GraphNodeDelegateFull.build_tooltip([port_name, port_type])

            if is_group:
                # to align with the port labels
                ui.Spacer(width=INPUT_PORT_WIDTH_MARGIN)
            else:
                with ui.HStack():
                    ui.Spacer(width=NODE_WIDTH_MARGIN)
                    with ui.VStack(visible_min=PORT_VISIBLE_MIN):
                        ui.Spacer()
                        image = ui.ImageWithProvider(
                            height=INPUT_VALUE_HEIGHT,
                            width=INPUT_VALUE_WIDTH,
                            fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                            style_type_name_override="Graph.Node.Port.Input.Icon",
                            name=port_type,
                        )
                        # Rasterize with big resolution
                        if hasattr(image, "prepare_draw"):
                            image.prepare_draw(200, 200)
                        ui.Spacer()
                if port_desc.connected_target:
                    with ui.HStack():
                        ui.Spacer(width=NODE_WIDTH_MARGIN - 2)
                        ui.Circle(
                            width=CONNECTION_PORT_WIDTH,
                            style=style,
                            style_type_name_override=override_style_name,
                            visible_min=PORT_VISIBLE_MIN,
                            name=port_type,
                        )
        return stack

    def port(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        """Called to create the middle part of the port,  API in AbstractGraphNodeDelegate"""
        port = port_desc.port
        port_name = model[port].name
        return GraphNodeDelegateFull.build_port(model, node_desc, port_desc, port_name)

    @staticmethod
    def build_port(
        model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription, port_name, can_edit_fn=None
    ):
        """
        static method to build port in GraphNodeDelegateFull, so that derived delegate can easily reuse this method
        with different port_name.

        Args:
            model: Graph model.
            node_desc: Graph node description.
            port_desc: Graph port description.
            port_name: input port name.
            can_edit_fn: function to determine if rename UI can be enabled
        """
        port = port_desc.port
        if model[port].inputs is None and model[port].outputs is None:
            return

        alignment = ui.Alignment.LEFT if model[port].inputs is not None else ui.Alignment.RIGHT

        level = port_desc.level
        sub_ports = model[port].ports
        is_group = sub_ports is not None and len(sub_ports) > 0

        def set_expansion_state(model, port, state: GraphModel.ExpansionState, *args):
            model[port].expansion_state = state

        GROUP_IMAGE_WIDTH = 10
        stack = ui.HStack(height=PORT_HEIGHT)
        with stack:
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

                    ui.Image(
                        width=GROUP_IMAGE_WIDTH,
                        style_type_name_override="Graph.Node.Port.Group",
                        name=image_name,
                        visible_min=PORT_VISIBLE_MIN,
                        mouse_pressed_fn=partial(set_expansion_state, model, port, next_state),
                    )
            if level > 0:
                if alignment == ui.Alignment.RIGHT:
                    ui.Spacer(width=INPUT_PORT_WIDTH_MARGIN + GROUP_IMAGE_WIDTH)
                with ui.HStack():
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

            side_margin = HIGHLIGHT_THICKNESS + CONNECTION_PORT_WIDTH

            # in case we have super long output port name
            if alignment == ui.Alignment.RIGHT:
                if model[port].inputs is not None:
                    side_margin = NODE_WIDTH_MARGIN
                ui.Spacer(width=side_margin)

            zstack = ui.ZStack(spacing=0)
            with zstack:
                label = ui.Label(
                    port_name,
                    visible_min=TEXT_VISIBLE_MIN,
                    style_type_name_override="Graph.Node.Port.Label",
                    alignment=alignment,
                )

                # String field to allow rename of port in-place
                if can_edit_fn:
                    label_field = ui.StringField()
                    label_field.visible = False

                    def is_mouse_over(label, x):
                        # Is mouse is over the label text? Add padding to account for the fact that the text
                        # isn't totally flush with the x position of the label widget.
                        PADDING = 4
                        if label.alignment == ui.Alignment.LEFT:
                            return x < (label.screen_position_x + label.exact_content_width + PADDING)
                        else:
                            return x > (
                                label.screen_position_x + label.computed_width - label.exact_content_width - PADDING
                            )

                    def show_edit_field(field, label, x, y, b, m):
                        # Only show the edit field if the mouse was over the text of the label. Solves problem where
                        # there wasn't enough space on the node that wasn't covered by a port label to trigger the
                        # double-click to enter compound nodes.
                        if can_edit_fn() and hasattr(label, "exact_content_width") and is_mouse_over(label, x):
                            field.model.set_value(port_name)
                            field.visible = True
                            # Note: this may be triggered with a context menu as well, so set keyboard focus
                            field.focus_keyboard(True)

                    def label_edited(field, *args):
                        field.visible = False
                        model[port].name = field.model.as_string
                        model._item_changed(None)

                    edit_fn = partial(show_edit_field, label_field, label)
                    label.set_mouse_double_clicked_fn(edit_fn)
                    zstack.set_mouse_double_clicked_fn(edit_fn)

                    label_field.model.add_end_edit_fn(partial(label_edited, label_field))

            if alignment == ui.Alignment.LEFT:
                if model[port].outputs is not None:
                    side_margin = NODE_WIDTH_MARGIN
                ui.Spacer(width=side_margin)

        return stack

    def port_output(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        style = {}
        return GraphNodeDelegateFull.build_port_output(model, node_desc, port_desc, style, "Graph.Connection")

    @staticmethod
    def build_port_output(model, node_desc, port_desc, style, override_style_name):
        port = port_desc.port
        if model[port].outputs is None:
            return

        sub_ports = model[port].ports
        is_group = sub_ports is not None and len(sub_ports) > 0

        port_type = str(model[port].type)
        port_name = model[port].name
        stack = ui.ZStack()
        with stack:
            GraphNodeDelegateFull.build_tooltip([port_name, port_type])
            if is_group:
                # to align with the port labels
                ui.Spacer(width=OUTPUT_PORT_WIDTH_MARGIN)
            else:
                with ui.HStack():
                    ui.Circle(
                        radius=PORT_RADIUS,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        visible_min=PORT_VISIBLE_MIN,
                        name=port_type,
                        style_type_name_override="Graph.Node.Port.Output.CustomColor",
                    )
                    ui.Spacer(width=CONNECTION_PORT_WIDTH - HIGHLIGHT_THICKNESS)

                if port_desc.connected_source:
                    with ui.HStack():
                        ui.Spacer(width=2.5)
                        ui.Circle(
                            width=CONNECTION_PORT_WIDTH,
                            style=style,
                            style_type_name_override=override_style_name,
                            visible_min=PORT_VISIBLE_MIN,
                            name=port_type,
                        )
        return stack

    def connection(
        self,
        model: GraphModel,
        source: GraphConnectionDescription,
        target: GraphConnectionDescription,
        foreground: bool = False,
    ) -> Tuple[ui.ZStack, ui.FreeLine, ui.FreeBezierCurve]:
        """Called to create the connection between ports"""
        # make the tooltip style transparent to avoid the artifact while target is not set
        style = {"Tooltip": {"background_color": 0x0, "color": 0xFFAAAAAA, "border_color": 0x0}}
        return GraphNodeDelegateFull.build_connection(model, source, target, style, "Graph.Connection", foreground)

    @staticmethod
    def build_connection(
        model: GraphModel,
        source: GraphConnectionDescription,
        target: GraphConnectionDescription,
        style: dict,
        override_style_name: str,
        foreground: bool = False,
    ) -> Tuple[ui.ZStack, ui.FreeLine, ui.FreeBezierCurve]:
        """
        The idea behind the 'foreground' arg is that when it is False, you draw the curve normally, as well as
        any widget that should be sitting directly on the curve, such as the curve anchor dot.  When foreground
        is True, you would make the curve color transparent, but draw any anchor decoration like the floating
        value display, which needs to be on top of all nodes.  For example:

        if foreground:
            freeline_widget.set_anchor_fn(partial(draw_value_display, freeline_widget))
            curve_widget.set_anchor_fn(partial(draw_value_display, curve_widget))
        else:
            freeline_widget.set_anchor_fn(partial(draw_anchor_dot, freeline_widget))
            curve_widget.set_anchor_fn(partial(draw_anchor_dot, curve_widget))
            freeline_widget.set_tooltip_fn(tooltip)
            curve_widget.set_tooltip_fn(tooltip)

        By default the graph_view's "draw_curve_top_layer" arg will be False, so this method won't get called
        2x, but the foreground arg is there in the event that a floating value display situation is useful.
        """
        CONNECTION_CURVE = 60
        port_type = str(model[source.port].type)
        source_port = model[source.port]
        target_port = model[target.port]

        # If the connection is reversed, we need to mirror tangents
        source_reversed_tangent = -1.0 if target.is_tangent_reversed else 1.0
        target_reversed_tangent = -1.0 if source.is_tangent_reversed else 1.0

        def tooltip():
            if not source.node or not target.node:
                return
            padding = 2
            with ui.ZStack():
                ui.Rectangle(style_type_name_override="Graph.Tooltip.Background")
                with ui.VStack():
                    ui.Spacer(height=padding)
                    with ui.HStack():
                        ui.Spacer(width=padding)
                        ui.Label(
                            f"{model[source.node].name}.{source_port.name}({str(source_port.type)}) --> {model[target.node].name}.{target_port.name}({str(target_port.type)})",
                            style_type_name_override="Graph.Connection.Tooltip.Label",
                        )
                        ui.Spacer(width=padding)
                    ui.Spacer(height=padding)

        # The user drags connection
        if not target.node:
            override_style_name = "Graph.Connection.Making"

        curve_container_widget = ui.ZStack()
        with curve_container_widget:
            freeline_widget = ui.FreeLine(
                target.widget,
                source.widget,
                alignment=ui.Alignment.UNDEFINED,
                style=style,
                name=port_type,
                tooltip_fn=tooltip,
                visible_max=PORT_VISIBLE_MIN,
                style_type_name_override=override_style_name,
            )
            curve_widget = ui.FreeBezierCurve(
                target.widget,
                source.widget,
                start_tangent_width=ui.Percent(-CONNECTION_CURVE * source_reversed_tangent),
                end_tangent_width=ui.Percent(CONNECTION_CURVE * target_reversed_tangent),
                name=port_type,
                style=style,
                tooltip_fn=tooltip,
                visible_min=PORT_VISIBLE_MIN,
                style_type_name_override=override_style_name,
            )
        return curve_container_widget, freeline_widget, curve_widget
