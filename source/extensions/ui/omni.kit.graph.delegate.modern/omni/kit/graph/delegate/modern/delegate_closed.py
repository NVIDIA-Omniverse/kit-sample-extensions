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

from .delegate_full import CONNECTION_PORT_WIDTH, PORT_VISIBLE_MIN, GraphNodeDelegateFull


class GraphNodeDelegateClosed(GraphNodeDelegateFull):
    """
    The delegate with the Omniverse design for the nodes of the closed state.
    """

    def __init__(self, scale_factor=1.0):
        super().__init__(scale_factor)

    def node_background(self, model, node_desc: GraphNodeDescription):
        return self._common_node_background(model, node_desc.node, False)

    def node_footer(self, model, node_desc: GraphNodeDescription):
        """Called to create widgets of the bottom of the node"""
        # Don't draw footer
        pass

    def node_header(self, model, node_desc: GraphNodeDescription):
        node = node_desc.node
        connected_ports = model[node].connected_ports
        connected_input_port = None
        connected_output_port = None
        stack = ui.ZStack()
        with stack:
            if len(connected_ports) > 0:
                for port in connected_ports:
                    if model[port].inputs is not None:
                        connected_input_port = model[port]
                    else:
                        connected_output_port = model[port]

            self._build_header(model, node_desc)

            with ui.HStack():
                if connected_input_port:
                    ui.Circle(
                        width=CONNECTION_PORT_WIDTH,
                        style_type_name_override="Graph.Connection",
                        visible_min=PORT_VISIBLE_MIN,
                        name=str(connected_input_port.type),
                        alignment=ui.Alignment.LEFT_CENTER,
                        arc=ui.Alignment.RIGHT,
                    )
                ui.Spacer()
                if connected_output_port:
                    ui.Circle(
                        width=CONNECTION_PORT_WIDTH,
                        style_type_name_override="Graph.Connection",
                        visible_min=PORT_VISIBLE_MIN,
                        name=str(connected_output_port.type),
                        alignment=ui.Alignment.RIGHT_CENTER,
                        arc=ui.Alignment.LEFT,
                    )
        return stack

    def node_header_input(self, model, node_desc: GraphNodeDescription):
        node = node_desc.node
        connected_ports = model[node].connected_ports
        connected_input_port = None
        if len(connected_ports) > 0:
            for port in connected_ports:
                if model[port].inputs is not None:
                    connected_input_port = model[port]
                    break
        if connected_input_port:
            return ui.Circle(
                width=CONNECTION_PORT_WIDTH,
                style_type_name_override="Graph.Connection",
                alignment=ui.Alignment.RIGHT_CENTER,
                arc=ui.Alignment.LEFT,
                visible_min=PORT_VISIBLE_MIN,
                name=str(connected_input_port.type),
            )
        else:
            return ui.Spacer(width=CONNECTION_PORT_WIDTH)

    def node_header_output(self, model, node_desc: GraphNodeDescription):
        node = node_desc.node
        connected_ports = model[node].connected_ports
        connected_output_port = None
        if len(connected_ports) > 0:
            for port in connected_ports:
                if model[port].inputs is None:
                    connected_output_port = model[port]
                    break
        if connected_output_port:
            stack = ui.HStack()
            with stack:
                ui.Circle(
                    width=CONNECTION_PORT_WIDTH,
                    style_type_name_override="Graph.Connection",
                    alignment=ui.Alignment.LEFT_CENTER,
                    arc=ui.Alignment.RIGHT,
                    visible_min=PORT_VISIBLE_MIN,
                    name=str(connected_output_port.type),
                )
            return stack
        else:
            return ui.Spacer(width=CONNECTION_PORT_WIDTH)
