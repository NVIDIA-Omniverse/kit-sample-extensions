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

from .delegate_full import MARGIN_TOP, MARGIN_WIDTH, MIN_WIDTH, NODE_PORT_SIZE, NeoGraphNodeDelegateFull


class NeoGraphNodeDelegateClosed(NeoGraphNodeDelegateFull):
    """
    The delegate with the Neo design for the nodes of the closed state.
    """

    def __init__(self, scale_factor=1.0):
        super().__init__(scale_factor)

    def node_header_input(self, model, node_desc: GraphNodeDescription):
        """Called to create the left part of the header that will be used as input when the node is collapsed"""
        with ui.VStack():
            ui.Spacer(height=ui.Fraction(2))
            rect = ui.Rectangle(
                width=2 * NODE_PORT_SIZE,
                height=2 * NODE_PORT_SIZE,
                style_type_name_override="Graph.Node.Header.Port",
            )
            ui.Spacer()

        return rect

    def node_header_output(self, model, node_desc: GraphNodeDescription):
        """Called to create the right part of the header that will be used as output when the node is collapsed"""
        with ui.VStack():
            ui.Spacer(height=ui.Fraction(2))
            rect = ui.Rectangle(
                width=2 * NODE_PORT_SIZE,
                height=2 * NODE_PORT_SIZE,
                style_type_name_override="Graph.Node.Header.Port",
            )
            ui.Spacer()

        return rect

    def node_background(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the node background"""
        node = node_desc.node
        style_name = str(model[node].type)

        # Draw a rectangle and a top line
        with ui.HStack():
            # Left offset
            ui.Spacer(width=MARGIN_WIDTH)

            with ui.VStack():
                ui.Spacer(height=MARGIN_TOP)

                # The node body
                with ui.ZStack():
                    # This trick makes min width
                    ui.Spacer(width=MIN_WIDTH)
                    # Top Header Color
                    ui.Rectangle(name=style_name, style_type_name_override="Graph.Node.Border")

            # Right offset
            ui.Spacer(width=MARGIN_WIDTH)

    def node_header(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the top of the node"""
        node = node_desc.node

        with ui.VStack(skip_draw_when_clipped=True):
            self._common_node_header_top(model, node, False)

            style_name = str(model[node].type)
            ui.Spacer(height=6)

            with ui.ZStack(height=0):
                ui.Rectangle(name=style_name, style_type_name_override="Graph.Node.Header.Background")
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._build_collapse_bt(model, node)
                # Draw the circle and the image on the top of it
                with ui.VStack():
                    ui.Spacer(height=5)
                    with ui.HStack(height=0):
                        ui.Spacer()
                        with ui.ZStack(width=40, height=40):
                            ui.Image(style_type_name_override="Graph.Node.Footer.Image", name=style_name)
                        ui.Spacer()
                    ui.Spacer(height=5)
            ui.Spacer(height=6)

    def node_footer(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the bottom of the node"""
        # Don't draw footer
        pass
