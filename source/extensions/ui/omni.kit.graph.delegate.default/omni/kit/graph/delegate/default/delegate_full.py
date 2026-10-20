# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import colorsys
import math
from functools import partial

import omni.ui as ui
from omni.kit.widget.graph.abstract_graph_node_delegate import (
    AbstractGraphNodeDelegate,
    GraphConnectionDescription,
    GraphNodeDescription,
    GraphNodeLayout,
    GraphPortDescription,
)
from omni.kit.widget.graph.graph_model import GraphModel
from omni.ui import color as cl

# Zoom level when the text disappears and the replacement line appears
TEXT_VISIBLE_MIN = 0.7
# Zoom level when the line disappears
LINE_VISIBLE_MIN = 0.4


CONNECTION_CURVE = 60


class GraphNodeDelegateFull(AbstractGraphNodeDelegate):
    """
    The delegate with the Omniverse design.
    """

    PREVIEW_SIZE = 175

    def __init__(self, scale_factor=1.0):
        super().__init__()
        self._scale_factor = scale_factor
        self._bezier_connection = True
        self._viewport_provider = None

    def __scale(self, value):
        """Return the value multiplied by global scale multiplier"""
        return value * self._scale_factor

    def _display_color_style(self, display_color, style_name: str, style_field: str, fallback=None):
        if display_color:
            style = {style_name: {style_field: cl(*display_color)}}
        else:
            style = fallback

        return style

    def __build_rectangle(self, radius, width, height, draw_top, style_name, name, style_override=None):
        """
        Build rectangle of the specific design.

        Args:
            radius: The radius of round corners. The corners are top-left and
                    bottom-right.
            width: The width of triangle to cut. The top-right and
                   bottom-left trialgles are cut.
            height: The height of triangle to cut. The top-right and
                    bottom-left trialgles are cut.
            draw_top: When false the top corners are straight.
            style_name: style_type_name_override of each widget
            name: name of each widget
            style_override: the style to apply to the top level node
        """
        stack = ui.VStack()
        if style_override:
            stack.set_style(style_override)

        with stack:
            # Top of the rectangle
            if draw_top:
                with ui.HStack(height=0):
                    with ui.VStack(width=0):
                        ui.Circle(
                            radius=radius,
                            width=0,
                            height=0,
                            size_policy=ui.CircleSizePolicy.FIXED,
                            alignment=ui.Alignment.RIGHT_BOTTOM,
                            style_type_name_override=style_name,
                            name=name,
                        )
                        ui.Rectangle(style_type_name_override=style_name, name=name)
                    ui.Rectangle(style_type_name_override=style_name, name=name)
                    ui.Triangle(
                        width=width,
                        height=height,
                        alignment=ui.Alignment.LEFT_TOP,
                        style_type_name_override=style_name,
                        name=name,
                    )

            # Middle of the rectangle
            ui.Rectangle(style_type_name_override=style_name, name=name)

            # Bottom of the rectangle
            with ui.HStack(height=0):
                ui.Triangle(
                    width=width,
                    height=height,
                    alignment=ui.Alignment.RIGHT_BOTTOM,
                    style_type_name_override=style_name,
                    name=name,
                )
                ui.Rectangle(style_type_name_override=style_name, name=name)
                with ui.VStack(width=0):
                    ui.Rectangle(style_type_name_override=style_name, name=name)
                    ui.Circle(
                        radius=radius,
                        width=0,
                        height=0,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        alignment=ui.Alignment.LEFT_TOP,
                        style_type_name_override=style_name,
                        name=name,
                    )

    def _icon(self, model, node, style_name, **kwargs):
        icon = model[node].icon
        if isinstance(icon, str):
            style = {f"Graph.Node.Footer.Image::{style_name}": {"image_url": icon, "color": cl(1.0)}}
        else:
            style = {}

        ui.ImageWithProvider(style_type_name_override="Graph.Node.Footer.Image", name=style_name, style=style, **kwargs)

    def _common_node_node_background(self, model, node, draw_icon: bool):
        """Called to create widgets of the node background"""
        # Constants
        MARGIN_WIDTH = 7.5
        MARGIN_TOP = 20.0
        MARGIN_BOTTOM = 25.0

        BORDER_THICKNESS = 3.0
        BORDER_RADIUS = 3.5
        HEADER_HEIGHT = 25.0
        MIN_WIDTH = 180.0
        TRIANGLE = 20.0

        # Computed values
        left_right_offset = MARGIN_WIDTH - BORDER_THICKNESS * 0.5
        outer_radius = BORDER_RADIUS + BORDER_THICKNESS * 0.5
        inner_radius = BORDER_RADIUS - BORDER_THICKNESS * 0.5

        # The size of the triangle
        outer_triangle = TRIANGLE
        # The size of the triangle to make the thickness of the diagonal line
        # the same as horizontal and vertial thickness. Works only with 45
        # degrees diagonals
        inner_triangle = outer_triangle - BORDER_THICKNESS / (
            math.sqrt(2) * math.tan(math.radians((180.0 - 45.0) / 2.0))
        )

        style_name = str(model[node].type)

        # Draw a rectangle and a top line
        with ui.HStack():
            # Left offset
            ui.Spacer(width=self.__scale(left_right_offset))

            with ui.ZStack():
                with ui.VStack():
                    ui.Spacer(height=self.__scale(MARGIN_TOP))

                    # The node body
                    with ui.ZStack():
                        # This trick makes min width
                        ui.Spacer(width=self.__scale(MIN_WIDTH))

                        # The color override for the border
                        border_color = model[node].display_color
                        style = self._display_color_style(
                            border_color, f"Graph.Node.Border::{style_name}", "background_color"
                        )

                        # Build outer rectangle
                        self.__build_rectangle(
                            self.__scale(outer_radius),
                            self.__scale(outer_triangle),
                            self.__scale(outer_triangle),
                            True,
                            "Graph.Node.Border",
                            style_name,
                            style,
                        )

                        # Build inner rectangle
                        with ui.VStack():
                            ui.Spacer(height=self.__scale(HEADER_HEIGHT))
                            with ui.HStack():
                                ui.Spacer(width=self.__scale(BORDER_THICKNESS))

                                if border_color:
                                    # 50% lightness from the border color
                                    # 30% saturation from the border color
                                    L_MULT = 0.5
                                    S_MULT = 0.3
                                    hls = colorsys.rgb_to_hls(border_color[0], border_color[1], border_color[2])
                                    rgb = colorsys.hls_to_rgb(hls[0], min(1.0, (hls[1] * L_MULT)), hls[2] * S_MULT)
                                    if len(border_color) > 3:  # alpha
                                        rgb = rgb + (border_color[3],)
                                    style = {"background_color": cl(*rgb)}
                                else:
                                    style = None

                                self.__build_rectangle(
                                    self.__scale(inner_radius),
                                    self.__scale(inner_triangle),
                                    self.__scale(inner_triangle),
                                    False,
                                    "Graph.Node.Background",
                                    style_name,
                                    style,
                                )
                                ui.Spacer(width=self.__scale(BORDER_THICKNESS))
                            ui.Spacer(height=self.__scale(BORDER_THICKNESS))
                    ui.Spacer(height=self.__scale(MARGIN_BOTTOM))

                if draw_icon:
                    with ui.VStack(visible_max=TEXT_VISIBLE_MIN):
                        # Space for top sign
                        if model[node].expansion_state != GraphModel.ExpansionState.CLOSED:
                            ui.Spacer(height=40)
                        preview = model[node].preview
                        if preview:
                            ui.Spacer(height=self.PREVIEW_SIZE)
                        ui.Spacer()
                        self._icon(
                            model,
                            node,
                            style_name,
                            height=100,
                            alignment=ui.Alignment.CENTER,
                            fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                        )
                        ui.Spacer(height=ui.Fraction(2))

            # Right offset
            ui.Spacer(width=self.__scale(left_right_offset))

    def node_background(self, model, node_desc: GraphNodeDescription):
        self._common_node_node_background(model, node_desc.node, True)

    def node_header_input(self, model, node_desc: GraphNodeDescription):
        """Called to create the left part of the header that will be used as input when the node is collapsed"""
        ui.Spacer(width=self.__scale(8))

    def node_header_output(self, model, node_desc: GraphNodeDescription):
        """Called to create the right part of the header that will be used as output when the node is collapsed"""
        ui.Spacer(width=self.__scale(8))

    def _common_node_header_top(self, model, node):
        """Node header part that is used in both full and closed states"""

        def switch_expansion(model, node):
            current = model[node].expansion_state
            model[node].expansion_state = GraphModel.ExpansionState((current.value + 1) % 3)

        # Draw the node name and a bit of space
        with ui.ZStack(width=0):
            ui.Label(model[node].name, style_type_name_override="Graph.Node.Header.Label", visible_min=TEXT_VISIBLE_MIN)
            with ui.Placer(stable_size=True, visible_min=LINE_VISIBLE_MIN, visible_max=TEXT_VISIBLE_MIN, offset_y=-8):
                ui.Label(model[node].name, name="Degenerated", style_type_name_override="Graph.Node.Header.Label")
        with ui.HStack():
            # Collapse button
            collapse = ui.ImageWithProvider(
                width=self.__scale(18), height=self.__scale(18), style_type_name_override="Graph.Node.Header.Collapse"
            )

            expansion_state = model[node].expansion_state
            if expansion_state == GraphModel.ExpansionState.CLOSED:
                collapse.name = "Closed"
            elif expansion_state == GraphModel.ExpansionState.MINIMIZED:
                collapse.name = "Minimized"
            else:
                collapse.name = "Open"

            collapse.set_mouse_pressed_fn(lambda x, y, b, m, model=model, node=node: switch_expansion(model, node))

        preview = model[node].preview

        preview_image = None
        if isinstance(preview, dict):
            # Check if we can use the image provider for the preview image
            # Note these keys are odd and exits only because of prior implementation,
            # gpu_reference will exist but be set to None, indicating that the model is
            # a UsdShadeGraphModel whose preview property returns this dict.
            #
            # TODO: Express this as a proper API to funnel the render to anything that needs it
            #  omni.kit.window.material_graph\omni\kit\window\material_graph\graph_widget.py@832
            #   __on_material_preview_drawable_changed(self)
            #
            gpu_reference = preview.get("gpu_reference", None)
            resolution = preview.get("resolution", None)
            if "gpu_reference" in preview and resolution:
                # It provides GPU ID, we can use it.
                self._viewport_provider = ui.ImageProvider()
                self._viewport_provider.set_image_data(gpu_reference)
                preview_image = self._viewport_provider
        else:
            # It's a regular path
            preview_image = preview

        if preview_image:
            style_name = str(model[node].type)

            border_color = model[node].display_color
            style = self._display_color_style(border_color, f"Graph.Node.Border::{style_name}", "background_color", {})

            ui.Spacer(height=2)
            with ui.HStack(height=0):
                ui.Spacer(width=1)
                with ui.ZStack():
                    ui.Rectangle(width=self.PREVIEW_SIZE, style={"background_color": cl(0)})
                    ui.ImageWithProvider(
                        preview_image,
                        height=self.PREVIEW_SIZE,
                        alignment=ui.Alignment.CENTER,
                        fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                    )
                ui.Spacer(width=1)
            ui.Rectangle(height=4, style=style, style_type_name_override="Graph.Node.Border", name=style_name)

    def node_header(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the top of the node"""
        with ui.VStack(skip_draw_when_clipped=True):
            self._common_node_header_top(model, node_desc.node)
            ui.Spacer(height=self.__scale(8))

    def node_footer(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the bottom of the node"""
        node = node_desc.node

        style_name = str(model[node].type)
        border_color = model[node].display_color
        style = self._display_color_style(border_color, f"Graph.Node.Footer::{style_name}", "border_color", {})
        style_border = self._display_color_style(
            border_color, f"Graph.Node.Footer.Border::{style_name}", "border_color", {}
        )

        # Draw the circle and the preview_image on the top of it
        with ui.VStack(visible_min=LINE_VISIBLE_MIN, skip_draw_when_clipped=True):
            ui.Spacer(height=self.__scale(10))
            with ui.HStack(height=0):
                ui.Spacer()
                with ui.ZStack(width=self.__scale(50), height=self.__scale(50)):
                    ui.Rectangle(
                        style_type_name_override="Graph.Node.Footer",
                        name=style_name,
                        style=style,
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                    self._icon(model, node, style_name, visible_min=TEXT_VISIBLE_MIN)
                    ui.Rectangle(
                        style_type_name_override="Graph.Node.Footer.Border",
                        name=style_name,
                        style=style_border,
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                ui.Spacer()
            ui.Spacer(height=self.__scale(2))

    def port_input(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        """Called to create the left part of the port that will be used as input"""
        node = node_desc.node
        port = port_desc.port
        connected_source = port_desc.connected_source
        connected_target = port_desc.connected_target

        if port is None:
            ui.Spacer(width=self.__scale(7.5))
            return

        style_type_name = "Graph.Node.Port.Input"
        customcolor_style_type_name = "Graph.Node.Port.Input.CustomColor"
        inputs = model[port].inputs

        node_type = str(model[node].type)
        port_type = str(model[port].type)

        def tooltip():
            margin = 5
            with ui.ZStack():
                ui.Rectangle(name=port_type, style_type_name_override="Graph.Tooltip.Background")
                with ui.VStack():
                    ui.Spacer(height=margin)
                    with ui.HStack():
                        ui.Spacer(width=margin)
                        ui.Label(port_type)
                        ui.Spacer(width=margin)
                    ui.Spacer(height=margin)

        tooltip_style = {
            "Tooltip": {
                "background_color": 0x0,
                "color": 0xFFAAAAAA,
                "margin_width": 0,
                "margin_height": 0,
                "border_width": 0,
                "border_color": 0x0,
            }
        }

        node_border_color = model[node].display_color
        if node_border_color:
            node_border_style = {
                f"{style_type_name}::{node_type}": {"border_color": cl(*node_border_color), "background_color": 0x0},
                f"{style_type_name}::{node_type}:selected": {"background_color": 0x0},
            }
        else:
            node_border_style = {"background_color": 0x0}

        with ui.HStack(skip_draw_when_clipped=True, tooltip_fn=tooltip, style=tooltip_style):
            ui.Spacer(width=self.__scale(6))
            with ui.ZStack(width=self.__scale(8)):
                if inputs is not None:
                    # Half-circle that shows the port is able to have input connection
                    # Background of the node color
                    ui.Circle(
                        radius=self.__scale(6),
                        name=node_type,
                        style_type_name_override=style_type_name,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style={"border_color": 0x0, "border_width": 0},
                        alignment=ui.Alignment.LEFT_CENTER,
                        arc=ui.Alignment.RIGHT,
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                    # Port has unique color
                    ui.Circle(
                        radius=self.__scale(6),
                        name=port_type,
                        style_type_name_override=customcolor_style_type_name,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        alignment=ui.Alignment.LEFT_CENTER,
                        arc=ui.Alignment.RIGHT,
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                    # Border of the node color
                    ui.Circle(
                        radius=self.__scale(6),
                        name=node_type,
                        style_type_name_override=style_type_name,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style=node_border_style,
                        alignment=ui.Alignment.LEFT_CENTER,
                        arc=ui.Alignment.RIGHT,
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                if connected_source:
                    # Circle that shows that the port is a source for the connection
                    ui.Circle(
                        radius=self.__scale(7),
                        name=port_type,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style_type_name_override="Graph.Connection",
                        alignment=ui.Alignment.LEFT_CENTER,
                        visible_min=LINE_VISIBLE_MIN,
                    )
                if connected_target:
                    # Circle that shows that the port is a target for the connection
                    ui.Circle(
                        radius=self.__scale(5),
                        name=port_type,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style_type_name_override="Graph.Connection",
                        alignment=ui.Alignment.LEFT_CENTER,
                        visible_min=LINE_VISIBLE_MIN,
                    )

    def port_output(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        """Called to create the right part of the port that will be used as output"""
        node = node_desc.node
        port = port_desc.port
        connected_source = port_desc.connected_source
        connected_target = port_desc.connected_target

        if port is None:
            ui.Spacer(width=self.__scale(7.5))
            return

        style_type_name = "Graph.Node.Port.Output"
        customcolor_style_type_name = "Graph.Node.Port.Output.CustomColor"
        outputs = model[port].outputs

        node_type = str(model[node].type)
        port_type = str(model[port].type)

        # TODO: Victor we should review what is the best way to do that
        # also we do have the same zooming issue with the Tooltip_fn
        def tooltip():
            margin = 5
            with ui.ZStack():
                ui.Rectangle(name=port_type, style_type_name_override="Graph.Tooltip.Background")
                with ui.VStack():
                    ui.Spacer(height=margin)
                    with ui.HStack():
                        ui.Spacer(width=margin)
                        ui.Label(port_type)
                        ui.Spacer(width=margin)
                    ui.Spacer(height=margin)

        tooltip_style = {
            "Tooltip": {
                "background_color": 0x0,
                "color": 0xFFAAAAAA,
                "margin_width": 0,
                "margin_height": 0,
                "border_width": 0,
                "border_color": 0x0,
            }
        }

        # Style to make the port border the same color as the node border
        node_border_style = self._display_color_style(
            model[node].display_color, f"{style_type_name}::{node_type}", "border_color", {}
        )

        with ui.ZStack(width=self.__scale(16), skip_draw_when_clipped=True, tooltip_fn=tooltip, style=tooltip_style):
            if outputs is not None:
                # Circle that shows the port is able to be an output connection
                # Background of the node color
                ui.Circle(
                    name=node_type,
                    style_type_name_override=style_type_name,
                    style=node_border_style,
                    alignment=ui.Alignment.CENTER,
                    radius=self.__scale(6),
                    size_policy=ui.CircleSizePolicy.FIXED,
                    visible_min=TEXT_VISIBLE_MIN,
                )
                # Port has unique color
                ui.Circle(
                    name=port_type,
                    style_type_name_override=customcolor_style_type_name,
                    style={"background_color": 0x0},
                    alignment=ui.Alignment.CENTER,
                    radius=self.__scale(6),
                    size_policy=ui.CircleSizePolicy.FIXED,
                    visible_min=TEXT_VISIBLE_MIN,
                )
            if connected_source:
                # Circle that shows that the port is a source for the connection
                ui.Circle(
                    radius=self.__scale(7),
                    name=port_type,
                    size_policy=ui.CircleSizePolicy.FIXED,
                    style_type_name_override="Graph.Connection",
                    alignment=ui.Alignment.CENTER,
                    visible_min=LINE_VISIBLE_MIN,
                )
            if connected_target:
                # Circle that shows that the port is a target for the connection
                ui.Circle(
                    radius=self.__scale(5),
                    name=port_type,
                    size_policy=ui.CircleSizePolicy.FIXED,
                    style_type_name_override="Graph.Connection",
                    alignment=ui.Alignment.CENTER,
                    visible_min=LINE_VISIBLE_MIN,
                )

    def port(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        """Called to create the middle part of the port"""

        def set_expansion_state(model, port, state: GraphModel.ExpansionState, *args):
            model[port].expansion_state = state

        port = port_desc.port
        level = port_desc.level

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

        with ui.HStack(skip_draw_when_clipped=True):
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
                state = model[port].expansion_state
                if state == GraphModel.ExpansionState.CLOSED:
                    image_name = "Plus"
                    next_state = GraphModel.ExpansionState.OPEN
                else:
                    image_name = "Minus"
                    next_state = GraphModel.ExpansionState.CLOSED
                ui.ImageWithProvider(
                    width=10,
                    style_type_name_override="Graph.Node.Port.Group",
                    name=image_name,
                    visible_min=TEXT_VISIBLE_MIN,
                    mouse_pressed_fn=partial(set_expansion_state, model, port, next_state),
                )
            with ui.ZStack():
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

        def tooltip(name: str):
            if not source.node or not target.node:
                return

            padding = 10
            with ui.ZStack():
                # TODO: Victor with
                ui.Rectangle(name=name, style_type_name_override="Graph.Tooltip.Background")
                with ui.VStack():
                    ui.Spacer(height=padding)
                    with ui.HStack():
                        ui.Spacer(width=padding)
                        ui.Label(
                            f"{model[source.node].name}.{model[source.port].name} --> {model[target.node].name}.{model[target.port].name}",
                            style={"font_size": 16},
                        )
                        ui.Spacer(width=padding)
                    ui.Spacer(height=padding)

        # @Victor I would like to do that in the Graph.Connection style but it was not applying ?
        tooltip_style = {
            "Tooltip": {
                "background_color": 0x0,
                "color": 0xFFAAAAAA,
                "margin_width": 0,
                "margin_height": 0,
                "border_width": 0,
                "border_color": 0x0,
            }
        }

        if target.node:
            # Conection is done
            style_type_name = "Graph.Connection"
            style_line_type_name = "Graph.Connection.Low"
        else:
            # The user drags connection
            style_type_name = "Graph.Connection.Making"
            style_line_type_name = "Graph.Connection.Making"

        if self._bezier_connection:
            with ui.ZStack():
                ui.FreeLine(
                    target.widget,
                    source.widget,
                    alignment=ui.Alignment.UNDEFINED,
                    style=tooltip_style,
                    tooltip_fn=lambda name=port_type: tooltip(name),
                    name=port_type,
                    visible_max=LINE_VISIBLE_MIN,
                    style_type_name_override=style_line_type_name,
                )
                ui.FreeBezierCurve(
                    target.widget,
                    source.widget,
                    start_tangent_width=ui.Percent(-CONNECTION_CURVE * source_reversed_tangent),
                    end_tangent_width=ui.Percent(CONNECTION_CURVE * target_reversed_tangent),
                    name=port_type,
                    style=tooltip_style,
                    tooltip_fn=lambda name=port_type: tooltip(name),
                    visible_min=LINE_VISIBLE_MIN,
                    style_type_name_override=style_type_name,
                )
        else:
            ui.FreeLine(
                target.widget,
                source.widget,
                style=tooltip_style,
                tooltip_fn=lambda name=port_type: tooltip(name),
                alignment=ui.Alignment.UNDEFINED,
                name=port_type,
                style_type_name_override=style_type_name,
            )
