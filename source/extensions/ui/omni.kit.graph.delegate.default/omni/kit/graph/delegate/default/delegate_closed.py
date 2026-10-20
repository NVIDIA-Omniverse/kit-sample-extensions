# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import omni.ui as ui
from omni.kit.widget.graph.abstract_graph_node_delegate import GraphNodeDescription

from .delegate_full import LINE_VISIBLE_MIN, TEXT_VISIBLE_MIN, GraphNodeDelegateFull


class GraphNodeDelegateClosed(GraphNodeDelegateFull):
    """
    The delegate with the Omniverse design for the nodes of the closed state.
    """

    def __init__(self, scale_factor=1.0):
        super().__init__(scale_factor)

    def node_header_input(self, model, node_desc: GraphNodeDescription):
        """Called to create the left part of the header that will be used as input when the node is collapsed"""
        node = node_desc.node
        connected_source = node_desc.connected_source
        connected_target = node_desc.connected_target

        style_type_name = "Graph.Node.Input"
        node_type = str(model[node].type)
        node_border_color = model[node].display_color
        if node_border_color:
            node_border_style = {
                f"{style_type_name}::{node_type}": {
                    "border_color": ui.color(*node_border_color),
                    "background_color": 0x0,
                }
            }
        else:
            node_border_style = {"background_color": 0x0}

        with ui.VStack(width=8, skip_draw_when_clipped=True):
            ui.Spacer(height=15)
            preview = model[node].preview
            if preview:
                ui.Spacer(height=self.PREVIEW_SIZE)
            with ui.ZStack():
                input_circle = ui.Circle(
                    radius=6,
                    name=node_type,
                    style_type_name_override=style_type_name,
                    size_policy=ui.CircleSizePolicy.FIXED,
                    style=node_border_style,
                    alignment=ui.Alignment.RIGHT_CENTER,
                    arc=ui.Alignment.RIGHT,
                    visible_min=TEXT_VISIBLE_MIN,
                )

                if connected_source:
                    # Circle that shows that the port is a source for the connection
                    ui.Circle(
                        radius=7,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style_type_name_override="Graph.Connection",
                        alignment=ui.Alignment.RIGHT_CENTER,
                        visible_min=LINE_VISIBLE_MIN,
                    )
                if connected_target:
                    # Circle that shows that the port is a target for the connection
                    ui.Circle(
                        radius=5,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style_type_name_override="Graph.Connection",
                        alignment=ui.Alignment.RIGHT_CENTER,
                        visible_min=LINE_VISIBLE_MIN,
                    )

        return input_circle

    def node_header_output(self, model, node_desc: GraphNodeDescription):
        """Called to create the right part of the header that will be used as output when the node is collapsed"""
        node = node_desc.node
        connected_source = node_desc.connected_source
        connected_target = node_desc.connected_target

        with ui.VStack(width=8, skip_draw_when_clipped=True):
            ui.Spacer(height=15)
            preview = model[node].preview
            if preview:
                ui.Spacer(height=self.PREVIEW_SIZE)
            with ui.ZStack(width=8):
                style_name = str(model[node].type)
                border_color = model[node].display_color
                if border_color:
                    style = {f"Graph.Node.Output::{style_name}": {"border_color": ui.color(*border_color)}}
                else:
                    style = {}
                output_circle = ui.Circle(
                    radius=6,
                    name=style_name,
                    style=style,
                    style_type_name_override="Graph.Node.Output",
                    size_policy=ui.CircleSizePolicy.FIXED,
                    alignment=ui.Alignment.LEFT_CENTER,
                    visible_min=TEXT_VISIBLE_MIN,
                )

                if connected_source:
                    # Circle that shows that the port is a source for the connection
                    ui.Circle(
                        radius=7,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style_type_name_override="Graph.Connection",
                        alignment=ui.Alignment.LEFT_CENTER,
                        visible_min=LINE_VISIBLE_MIN,
                    )
                if connected_target:
                    # Circle that shows that the port is a target for the connection
                    ui.Circle(
                        radius=5,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style_type_name_override="Graph.Connection",
                        alignment=ui.Alignment.LEFT_CENTER,
                        visible_min=LINE_VISIBLE_MIN,
                    )

        return output_circle

    def node_header(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the top of the node"""
        node = node_desc.node

        with ui.VStack(skip_draw_when_clipped=True):
            self._common_node_header_top(model, node)

            style_name = str(model[node].type)

            # Draw the circle and the image on the top of it
            with ui.HStack(height=0):
                with ui.VStack():
                    ui.Label(
                        "Inputs",
                        alignment=ui.Alignment.CENTER,
                        style_type_name_override="Graph.Node.Port.Label",
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                    ui.Spacer(height=15)

                with ui.ZStack(width=50, height=50):
                    border_color = model[node].display_color
                    if border_color:
                        style = {f"Graph.Node.Footer::{style_name}": {"border_color": ui.color(*border_color)}}
                        style_border = {
                            f"Graph.Node.Footer.Border::{style_name}": {"border_color": ui.color(*border_color)}
                        }
                    else:
                        style = {}
                        style_border = {}

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
                    # Scale up the icon when zooming out
                    with ui.Placer(stable_size=True, visible_max=TEXT_VISIBLE_MIN, offset_x=-15, offset_y=-20):
                        with ui.ZStack(width=0, height=0):
                            ui.Rectangle(
                                style_type_name_override="Graph.Node.Footer",
                                name=style_name,
                                style=style,
                                width=80,
                                height=80,
                            )
                            self._icon(model, node, style_name, width=80, height=80)
                            ui.Rectangle(
                                style_type_name_override="Graph.Node.Footer.Border",
                                name=style_name,
                                style=style_border,
                                width=80,
                                height=80,
                            )

                with ui.VStack():
                    ui.Label(
                        "Outputs",
                        alignment=ui.Alignment.CENTER,
                        style_type_name_override="Graph.Node.Port.Label",
                        visible_min=TEXT_VISIBLE_MIN,
                    )
                    ui.Spacer(height=15)

            ui.Spacer(height=18)

    def node_background(self, model, node_desc: GraphNodeDescription):
        self._common_node_node_background(model, node_desc.node, False)

    def node_footer(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the bottom of the node"""
        # Don't draw footer
        pass
