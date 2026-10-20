# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import colorsys
from typing import Any, Optional

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


def tweak_color(rgb_color, l_mult=1.0, s_mult=1.0):
    hls = colorsys.rgb_to_hls(rgb_color[0], rgb_color[1], rgb_color[2])
    tweaked_colors = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * l_mult)), hls[2] * s_mult)
    tweaked_color = color_to_hex(tweaked_colors)
    return tweaked_color


def darker_color(rgb_color):
    return tweak_color(rgb_color, l_mult=0.75, s_mult=0.3)


def background_color(rgb_color):
    return tweak_color(rgb_color, l_mult=1.0, s_mult=1.0)


def get_contrast_text_color(bg_color_hex):
    r, g, b, a = hex_to_color(bg_color_hex)
    hls = colorsys.rgb_to_hls(r, g, b)

    # Choose the text color based on the perceived brightness
    if hls[1] > 0.5:
        text_color = 0xFF101010  # Black for bright backgrounds
    else:
        text_color = 0xFFFAFAFA  # White for dark backgrounds

    return text_color


class NoteDelegate(GraphNodeDelegateFull):
    """
    The delegate with the Omniverse design for the Note type.
    """

    def node_header(self, model, node_desc: GraphNodeDescription):
        BORDER_DEFAULT = 0xFFD8B74B

        def set_color(model, node, item_model):
            # function to change the display color of the note background
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
                    # This is the main header color
                    f"Graph.Node.Secondary::{node_category}": {
                        "background_color": darker_color(display_color),
                        "border_radius": BACKGROUND_RADIUS,
                        "corner_flag": ui.CornerFlag.TOP,
                    },
                }
            else:
                style = {}

            ui.Spacer(height=HIGHLIGHT_THICKNESS)
            with ui.ZStack():
                GraphNodeDelegateFull.build_tooltip([node_name, node_category])
                # label
                with ui.VStack():
                    # the header text with background
                    with ui.ZStack(height=HEADER["note_sec_height"]):
                        ui.Rectangle(style=style, name=node_category, style_type_name_override="Graph.Node.Secondary")
                        with ui.VStack():
                            ui.Spacer()
                            with ui.HStack(height=0):
                                ui.Spacer()  # Right align

                                # color widget which allows to change the display color of the backdrop background
                                with ui.VStack(width=0):
                                    ui.Spacer()
                                    with ui.ZStack(width=8, height=8):
                                        with ui.Frame(horizontal_clipping=1, vertical_clipping=1):
                                            color_widget = ui.ColorWidget(
                                                style_type_name_override="Graph.Node.ColorWidget"
                                            )

                                            sub_models = color_widget.model.get_item_children()
                                            border_color = model[node].display_color or hex_to_color(BORDER_DEFAULT)

                                            color_widget.model.get_item_value_model(sub_models[0]).as_float = (
                                                border_color[0]
                                            )
                                            color_widget.model.get_item_value_model(sub_models[1]).as_float = (
                                                border_color[1]
                                            )
                                            color_widget.model.get_item_value_model(sub_models[2]).as_float = (
                                                border_color[2]
                                            )
                                            color_widget.model.add_end_edit_fn(lambda m, i: set_color(model, node, m))

                                        ui.Rectangle(style_type_name_override="Graph.Node.ColorWidgetBorder")
                                    ui.Spacer()

                                ui.Spacer(width=8)  # Right Margin

                            ui.Spacer()
            ui.Spacer(height=HIGHLIGHT_THICKNESS)
        return header

    def node_background(self, model, node_desc: GraphNodeDescription):
        """Override the node background call from delegate_full"""
        MIN_HEIGHT = 120.0
        MIN_WIDTH = 150.0
        HEADER_HEIGHT = 14.0
        MARGIN = 10.0

        node = node_desc.node
        description_label = None

        def on_size_changed(placer):
            offset_x = placer.offset_x
            offset_y = placer.offset_y

            model[node].size = (offset_x.value, offset_y.value)

            if offset_x.value < MIN_WIDTH:
                placer.offset_x = MIN_WIDTH
            if offset_y.value < MIN_HEIGHT:
                placer.offset_y = MIN_HEIGHT

            if description_label:
                description_label.width = ui.Length(placer.offset_x.value)

        def set_description(
            field: ui.StringField, model, node: Any, description: str, desc_label: Optional[ui.Label] = None
        ):
            """Called to set the description on the model and remove the field with the description"""
            model[node].description = description
            field.visible = False
            if desc_label:
                desc_label.visible = True
            model._item_changed(None)

        def on_description(model, node: Any, frame: ui.Frame, description: str, desc_label: Optional[ui.Label] = None):
            """Called to create a field on the node to edit description"""
            with frame:
                field = ui.StringField(
                    multiline=True,
                    style={
                        "color": ui.color.black,
                        "background_color": darker_color(model[node].display_color),
                        "font_size": 18,
                    },
                )
                if description:
                    field.model.as_string = description
                field.model.add_end_edit_fn(lambda m: set_description(field, model, node, m.as_string, desc_label))
                field.focus_keyboard()
                if desc_label:
                    desc_label.visible = False

        width, height = model[node].size or (NODE_MIN_WIDTH, MIN_HEIGHT)

        node_type = str(model[node].type)
        style_name = node_type

        HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE = 4.0
        HIGHLIGHT_THICKNESS_ZOOM_OUT = 6.0

        # The node body
        background = ui.ZStack()
        with background:
            # highlight
            with ui.VStack(visible_max=PORT_VISIBLE_MIN):
                self._build_rectangle(
                    BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS,
                    True,
                    "Graph.Node.Border",
                    node_type,
                    top_round=True,
                    bottom_round=True,
                )

            # zoomed out highlight
            # this is shown during the zoom in between PORT_VISIBLE_MIN and TEXT_VISIBLE_MIN
            margin = NODE_WIDTH_MARGIN - HIGHLIGHT_THICKNESS_ZOOM_OUT
            with ui.HStack(visible_max=TEXT_VISIBLE_MIN, visible_min=PORT_VISIBLE_MIN):
                ui.Spacer(width=margin)
                with ui.VStack():
                    ui.Spacer(height=HIGHLIGHT_THICKNESS - HIGHLIGHT_THICKNESS_ZOOM_OUT)
                    self._build_rectangle(
                        BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS_ZOOM_OUT,
                        True,
                        "Graph.Node.Border",
                        node_type,
                        top_round=True,
                        bottom_round=True,
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
                        BACKGROUND_RADIUS + HIGHLIGHT_THICKNESS_ZOOM_OUT_MORE,
                        True,
                        "Graph.Node.Border",
                        node_type,
                        top_round=True,
                        bottom_round=True,
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
                            bg_color = background_color(display_color)
                            style = {
                                f"Graph.Node.Background::{node_type}": {"background_color": bg_color},
                                "Graph.Node.Note.Description": {"color": get_contrast_text_color(bg_color)},
                                "Graph.Note.ScrollView": {
                                    "background_color": ui.color.transparent,
                                    "secondary_color": darker_color(model[node].display_color),
                                },
                            }
                        else:
                            style = {}

                        self._build_rectangle(
                            BACKGROUND_RADIUS,
                            True,
                            "Graph.Node.Background",
                            node_type,
                            style,
                            top_round=True,
                            bottom_round=True,
                        )

                        # Properly aligned description
                        with ui.VStack():
                            ui.Spacer(height=HEADER_HEIGHT + MARGIN)
                            with ui.HStack():
                                ui.Spacer(width=MARGIN * 0.5)
                                with ui.ZStack():
                                    description_label = None
                                    with ui.ScrollingFrame(
                                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                                        style=style,
                                        style_type_name_override="Graph.Note.ScrollView",
                                    ):
                                        description = model[node].description
                                        if description:
                                            description_label = ui.Label(
                                                description,
                                                alignment=ui.Alignment.LEFT_TOP,
                                                width=width,
                                                height=0,
                                                word_wrap=True,
                                                style_type_name_override="Graph.Node.Note.Description",
                                            )
                                        else:
                                            # Shrink box back to min size if no description
                                            width, height = NODE_MIN_WIDTH, MIN_HEIGHT

                                    # Frame with description field
                                    frame = ui.Frame()
                                    frame.set_mouse_double_clicked_fn(
                                        lambda x, y, b, m, f=frame, d=description, d_lbl=description_label: on_description(
                                            model, node, f, d, d_lbl
                                        )
                                    )

                            ui.Spacer(height=MARGIN)
                    ui.Spacer(height=HIGHLIGHT_THICKNESS)
                ui.Spacer(width=NODE_WIDTH_MARGIN)

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
                                "background_color": darker_color(model[node].display_color)
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
