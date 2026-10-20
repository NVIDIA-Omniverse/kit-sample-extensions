# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
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
from omni.kit.widget.graph.abstract_graph_node_delegate import GraphNodeDescription

from .delegate_full import (
    BACKGROUND_RADIUS,
    HEADER,
    HIGHLIGHT_THICKNESS,
    NODE_MIN_WIDTH,
    NODE_WIDTH_MARGIN,
    PORT_VISIBLE_MIN,
    TEXT_VISIBLE_MIN,
    GraphNodeDelegateFull,
)


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


def darker_color(rgb_color):
    L_MULT = 0.6
    S_MULT = 0.7

    hls = colorsys.rgb_to_hls(rgb_color[0], rgb_color[1], rgb_color[2])
    darker_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT)), hls[2] * S_MULT)
    darker_color = color_to_hex(darker_colors)
    return darker_color


def background_color(rgb_color):
    L_MULT = 0.4
    S_MULT = 0.5

    hls = colorsys.rgb_to_hls(rgb_color[0], rgb_color[1], rgb_color[2])

    background_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT * 1.2)), hls[2] * S_MULT * 0.5)
    background_color = color_to_hex(background_colors)
    return background_color


class BackdropDelegate(GraphNodeDelegateFull):
    """
    The delegate with the Omniverse design for the nodes of the closed state.
    """

    def node_header(self, model, node_desc: GraphNodeDescription):
        BORDER_DEFAULT = 0xFFD8B74B

        def set_color(model, node, item_model):
            # function to change the display color of the backdrop background
            sub_models = item_model.get_item_children()
            rgb = (
                item_model.get_item_value_model(sub_models[0]).as_float,
                item_model.get_item_value_model(sub_models[1]).as_float,
                item_model.get_item_value_model(sub_models[2]).as_float,
            )
            model[node].display_color = rgb
            model.selection = []
            model._item_changed(None)

        header = ui.VStack()
        with header:
            node = node_desc.node
            node_name = model[node].name
            node_category = str(model[node].type)

            display_color = model[node].display_color
            if display_color:
                style = {
                    f"Graph.Node.Category::{node_category}": {"background_color": color_to_hex(display_color)},
                    f"Graph.Node.Secondary::{node_category}": {"background_color": darker_color(display_color)},
                }
            else:
                style = {}

            ui.Spacer(height=HIGHLIGHT_THICKNESS)
            with ui.ZStack():
                GraphNodeDelegateFull.build_tooltip([node_name, node_category])
                # label
                with ui.VStack():
                    # the header text with background
                    with ui.ZStack(height=HEADER["sec_height"]):
                        ui.Rectangle(style=style, name=node_category, style_type_name_override="Graph.Node.Secondary")
                        with ui.VStack():
                            ui.Spacer()
                            with ui.HStack(height=14):
                                ui.Spacer(width=3)
                                # color widget which allows to change the display color of the backdrop background
                                color_widget = ui.ColorWidget(height=14, width=14)

                                sub_models = color_widget.model.get_item_children()
                                border_color = model[node].display_color or hex_to_color(BORDER_DEFAULT)

                                color_widget.model.get_item_value_model(sub_models[0]).as_float = border_color[0]
                                color_widget.model.get_item_value_model(sub_models[1]).as_float = border_color[1]
                                color_widget.model.get_item_value_model(sub_models[2]).as_float = border_color[2]
                                color_widget.model.add_end_edit_fn(lambda m, i: set_color(model, node, m))

                                with ui.ZStack():
                                    label = ui.Label(
                                        node_name,
                                        visible_min=PORT_VISIBLE_MIN,
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
                            ui.Spacer()
                    ui.Rectangle(
                        height=HEADER["height"],
                        style=style,
                        name=node_category,
                        style_type_name_override="Graph.Node.Category",
                    )
            ui.Spacer(height=HIGHLIGHT_THICKNESS)
        return header

    def node_background(self, model, node_desc: GraphNodeDescription):
        """Override the node background call from delegate_full"""
        MIN_HEIGHT = 50.0
        HEADER_HEIGHT = 25.0
        MARGIN = 10.0

        node = node_desc.node

        def on_size_changed(placer):
            offset_x = placer.offset_x
            offset_y = placer.offset_y

            model[node].size = (offset_x.value, offset_y.value)

            if offset_x.value < NODE_MIN_WIDTH:
                placer.offset_x = NODE_MIN_WIDTH
            if offset_y.value < MIN_HEIGHT:
                placer.offset_y = MIN_HEIGHT

        def set_description(field: ui.StringField, model, node: any, description: str):
            """Called to set the description on the model and  remove the field with the description"""
            model[node].description = description
            field.visible = False
            model._item_changed(None)

        def on_description(model, node: any, frame: ui.Frame, description: str):
            """Called to create a field on the node to edit description"""
            try:
                color = model[node].display_color
            except TypeError:
                return

            with frame:
                field = ui.StringField(multiline=True, style={"background_color": darker_color(color), "font_size": 18})
                if description:
                    field.model.as_string = description
                field.model.add_end_edit_fn(lambda m: set_description(field, model, node, m.as_string))
                field.focus_keyboard()

        width, height = model[node].size or (NODE_MIN_WIDTH, MIN_HEIGHT)

        node_type = str(model[node].type)

        HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE = 4.0
        HIGHLIGHT_THICKNESS_ZOOM_OUT = 6.0

        # The node body
        background = ui.ZStack()
        with background:
            # highlight
            with ui.VStack(visible_max=PORT_VISIBLE_MIN):
                self._build_rectangle(BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS, False, "Graph.Node.Border", node_type)

            # zoomed out highlight
            # this is shown during the zoom in between PORT_VISIBLE_MIN and TEXT_VISIBLE_MIN
            margin = NODE_WIDTH_MARGIN - HIGHLIGHT_THICKNESS_ZOOM_OUT
            with ui.HStack(visible_max=TEXT_VISIBLE_MIN, visible_min=PORT_VISIBLE_MIN):
                ui.Spacer(width=margin)
                with ui.VStack():
                    ui.Spacer(height=HIGHLIGHT_THICKNESS - HIGHLIGHT_THICKNESS_ZOOM_OUT)
                    self._build_rectangle(
                        BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS_ZOOM_OUT, False, "Graph.Node.Border", node_type
                    )
                    ui.Spacer(height=HIGHLIGHT_THICKNESS - HIGHLIGHT_THICKNESS_ZOOM_OUT)
                ui.Spacer(width=margin)

            # zoomed out more highlight
            # this is shown when the zoom is > TEXT_VISIBLE_MIN
            margin = NODE_WIDTH_MARGIN - HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE
            with ui.HStack(visible_min=TEXT_VISIBLE_MIN):
                ui.Spacer(width=margin)
                with ui.VStack():
                    ui.Spacer(height=HIGHLIGHT_THICKNESS - HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE)
                    self._build_rectangle(
                        BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE, False, "Graph.Node.Border", node_type
                    )
                    ui.Spacer(height=HIGHLIGHT_THICKNESS - HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE)
                ui.Spacer(width=margin)

            # node background, this is shown across the whole zoom level
            with ui.HStack():
                ui.Spacer(width=NODE_WIDTH_MARGIN)
                with ui.VStack():
                    ui.Spacer(height=HIGHLIGHT_THICKNESS)
                    with ui.ZStack():
                        display_color = model[node].display_color
                        if display_color:
                            style = {
                                f"Graph.Node.Background::{node_type}": {
                                    "background_color": background_color(display_color)
                                },
                            }
                        else:
                            style = {}

                        self._build_rectangle(BACKGROUND_RADIUS, False, "Graph.Node.Background", node_type, style)

                        # Properly alighned description
                        with ui.VStack():
                            ui.Spacer(height=HEADER_HEIGHT + MARGIN)
                            with ui.HStack():
                                ui.Spacer(width=MARGIN)
                                with ui.ZStack():
                                    description = model[node].description
                                    if description:
                                        ui.Label(
                                            description,
                                            alignment=ui.Alignment.LEFT_TOP,
                                            style_type_name_override="Graph.Node.Description",
                                        )

                                    # Frame with description field
                                    frame = ui.Frame()
                                    frame.set_mouse_double_clicked_fn(
                                        lambda x, y, b, m, f=frame, d=description: on_description(model, node, f, d)
                                    )
                                ui.Spacer(width=MARGIN)
                            ui.Spacer(height=MARGIN)
                    ui.Spacer(height=HIGHLIGHT_THICKNESS)
                ui.Spacer(width=NODE_WIDTH_MARGIN)

            style_name = str(model[node].type)

            # The triangle that resizes the node
            with ui.VStack():
                ui.Spacer()
                with ui.HStack(height=0):
                    ui.Spacer()
                    placer = ui.Placer(draggable=True, width=BACKGROUND_RADIUS * 2, height=BACKGROUND_RADIUS * 2)
                    placer.offset_x = width
                    placer.offset_y = height
                    placer.set_offset_x_changed_fn(lambda _, p=placer: on_size_changed(p))
                    placer.set_offset_y_changed_fn(lambda _, p=placer: on_size_changed(p))
                    # draggable placer color
                    if model[node].display_color:
                        style = {
                            f"Graph.Node.Resize::{style_name}": {
                                "background_color": color_to_hex(model[node].display_color)
                            }
                        }
                    else:
                        style = {}

                    with placer:
                        drag_widget = ui.ZStack()
                        with drag_widget:
                            with ui.HStack():
                                ui.Spacer(width=BACKGROUND_RADIUS)
                                ui.Triangle(
                                    width=BACKGROUND_RADIUS,
                                    height=BACKGROUND_RADIUS,
                                    name=style_name,
                                    style=style,
                                    alignment=ui.Alignment.RIGHT_TOP,
                                    style_type_name_override="Graph.Node.Resize",
                                )
                            with ui.VStack():
                                ui.Spacer(height=BACKGROUND_RADIUS)
                                ui.Triangle(
                                    width=BACKGROUND_RADIUS,
                                    height=BACKGROUND_RADIUS,
                                    name=style_name,
                                    style=style,
                                    alignment=ui.Alignment.RIGHT_TOP,
                                    style_type_name_override="Graph.Node.Resize",
                                )
                            ui.Circle(
                                width=BACKGROUND_RADIUS * 2,
                                height=BACKGROUND_RADIUS * 2,
                                name=style_name,
                                style=style,
                                arc=ui.Alignment.RIGHT_BOTTOM,
                                style_type_name_override="Graph.Node.Resize",
                            )

                        drag_widget.set_mouse_pressed_fn(lambda x, y, b, m: b == 0 and model.size_begin_edit(node))
                        drag_widget.set_mouse_released_fn(lambda x, y, b, m: b == 0 and model.size_end_edit(node))
                    ui.Spacer(width=NODE_WIDTH_MARGIN)
                ui.Spacer(height=HIGHLIGHT_THICKNESS)
        return background
