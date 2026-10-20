# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import omni.ui as ui
from omni.kit.widget.graph.abstract_graph_node_delegate import GraphNodeDescription

from .delegate_full import MARGIN_TOP, MARGIN_WIDTH, MIN_WIDTH, NeoGraphNodeDelegateFull, color_to_hex, hex_to_color


class NeoGraphNodeDelegateBackdrop(NeoGraphNodeDelegateFull):
    """
    The delegate with the Neo design for the backdrop node.
    """

    def __init__(self, *args):
        super().__init__(args)
        # no icon on the footer
        self._show_icon = False

    def node_header(self, model, node_desc: GraphNodeDescription):
        """Override the node header call from delegate_full"""
        BORDER_DEFAULT = 0xFFD8B74B
        node = node_desc.node

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

        with ui.ZStack(skip_draw_when_clipped=True):
            with ui.VStack():
                with ui.HStack():
                    ui.Spacer(width=10)
                    # editable node name
                    self._common_node_header_top(model, node, False)
                ui.Spacer(height=30)
            with ui.VStack():
                ui.Spacer(height=30)
                with ui.HStack():
                    ui.Spacer(width=8)
                    # color widget which allows to change the display color of the backdrop background
                    color_widget = ui.ColorWidget(width=15, height=15)
                    sub_models = color_widget.model.get_item_children()

                    border_color = model[node].display_color or hex_to_color(BORDER_DEFAULT)

                    color_widget.model.get_item_value_model(sub_models[0]).as_float = border_color[0]
                    color_widget.model.get_item_value_model(sub_models[1]).as_float = border_color[1]
                    color_widget.model.get_item_value_model(sub_models[2]).as_float = border_color[2]
                    color_widget.model.add_end_edit_fn(lambda m, i: set_color(model, node, m))

    def node_header_output(self, model, node_desc: GraphNodeDescription):
        """Override the node header output call from delegate_full"""
        pass

    def node_header_input(self, model, node_desc: GraphNodeDescription):
        """Override the node header input call from delegate_full"""
        pass

    def node_background(self, model, node_desc: GraphNodeDescription):
        """Override the node background call from delegate_full"""
        MARGIN_BOTTOM = 25.0
        BORDER_THICKNESS = 0
        HEADER_HEIGHT = 25.0
        TRIANGLE = 20
        MIN_HEIGHT = 50.0

        node = node_desc.node

        def on_size_changed(placer):
            offset_x = placer.offset_x
            offset_y = placer.offset_y

            model[node].size = (offset_x.value, offset_y.value)

            if offset_x.value < MIN_WIDTH:
                placer.offset_x = MIN_WIDTH
            if offset_y.value < MIN_HEIGHT:
                placer.offset_y = MIN_HEIGHT

        def set_description(field: ui.StringField, description: str):
            """Called to set the description on the model and remove the field with the description"""
            self._description_label.visible = True
            model[node].description = description
            self._description_label.text = description
            field.visible = False

        def on_description(model, node, frame: ui.Frame, description: str):
            """Called to create a field on the node to edit description"""
            self._description_label.visible = False
            with frame:
                field = ui.StringField(multiline=True, style_type_name_override="Graph.Node.Description.Edit")
                if description:
                    field.model.as_string = description
                field.model.add_end_edit_fn(lambda m: set_description(field, m.as_string))
                field.focus_keyboard()

        width, height = model[node].size or (MIN_WIDTH, MIN_HEIGHT)
        with ui.ZStack(width=0, height=0):
            super().node_background(model, node_desc)
            style_name = str(model[node].type)

            # Properly alighned description
            with ui.VStack():
                ui.Spacer(height=HEADER_HEIGHT + MARGIN_TOP + 12)
                with ui.HStack():
                    ui.Spacer(width=MARGIN_WIDTH)
                    with ui.ZStack():
                        description = model[node].description
                        if description:
                            self._description_label = ui.Label(
                                description,
                                alignment=ui.Alignment.LEFT_TOP,
                                style_type_name_override="Graph.Node.Description",
                            )

                        # Frame with description field
                        frame = ui.Frame()
                        frame.set_mouse_double_clicked_fn(
                            lambda x, y, b, m, f=frame, d=description: on_description(model, node, f, d)
                        )
                    ui.Spacer(width=MARGIN_WIDTH)
                ui.Spacer(height=MARGIN_BOTTOM)

            # The triangle that resizes the node
            with ui.VStack():
                ui.Spacer()
                with ui.HStack(height=0):
                    placer = ui.Placer(draggable=True)
                    placer.offset_x = width
                    placer.offset_y = height
                    placer.set_offset_x_changed_fn(lambda _, p=placer: on_size_changed(p))
                    placer.set_offset_y_changed_fn(lambda _, p=placer: on_size_changed(p))
                    if model[node].display_color:
                        style = {
                            f"Graph.Node.Resize::{style_name}": {
                                "background_color": color_to_hex(model[node].display_color)
                            }
                        }
                    else:
                        style = {}

                    with placer:
                        triangle = ui.Triangle(
                            width=TRIANGLE,
                            height=TRIANGLE,
                            name=style_name,
                            style=style,
                            alignment=ui.Alignment.RIGHT_TOP,
                            style_type_name_override="Graph.Node.Resize",
                        )
                        triangle.set_mouse_pressed_fn(lambda x, y, b, m: b == 0 and model.size_begin_edit(node))
                        triangle.set_mouse_released_fn(lambda x, y, b, m: b == 0 and model.size_end_edit(node))
                    ui.Spacer(width=MARGIN_WIDTH + 0.5 * BORDER_THICKNESS)

    def node_footer(self, model, node_desc: GraphNodeDescription):
        """Override the node footer call from delegate_full"""
        pass
