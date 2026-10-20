# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from typing import Any, List

import omni.ui as ui
from omni.kit.widget.graph.abstract_graph_node_delegate import GraphNodeDescription, GraphPortDescription

from .delegate import GraphNodeDelegate


class CompoundNodeDelegate(GraphNodeDelegate):
    """
    The delegate for the compound nodes.
    """

    pass


class CompoundInputOutputNodeDelegate(GraphNodeDelegate):
    """
    The delegate for the input/output nodes of the compound.
    """

    def __init__(self):
        super().__init__()
        self.__port_context_menu = None

    def destroy(self):
        self.__port_context_menu = None

    def port_input(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        node = node_desc.node
        port = port_desc.port
        frame = ui.Frame()
        with frame:
            super().port_input(model, node_desc, port_desc)

        frame.set_mouse_pressed_fn(lambda x, y, b, _, m=model, n=node, p=port: b == 1 and self.__on_menu(m, n, p))

    def port_output(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        node = node_desc.node
        port = port_desc.port
        frame = ui.Frame()
        with frame:
            super().port_output(model, node_desc, port_desc)

        frame.set_mouse_pressed_fn(lambda x, y, b, _, m=model, n=node, p=port: b == 1 and self.__on_menu(m, n, p))

    def port(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription):
        port = port_desc.port
        stack = ui.ZStack()
        with stack:
            super().port(model, node_desc, port_desc)

            # Draw input on top of the original port
            field = ui.StringField(visible=False)
            value_model = field.model
            value_model.as_string = model[port].name

        def begin_edit():
            field.visible = True

        def end_edit(value_model):
            # Hide
            field.visible = False
            # Rename
            model[port].name = value_model.as_string

        # Activate input with double click
        stack.set_mouse_double_clicked_fn(lambda x, y, b, m: begin_edit())
        value_model.add_end_edit_fn(end_edit)

    def __on_menu(self, model: "GraphModel", node: Any, port: Any):
        def disconnect(model: "GraphModel", port: Any):
            """Disconnect everything from the given port"""
            model[port].inputs = []

        def remove(model: "GraphModel", node: Any, port: Any):
            """Remove the given port from the node"""
            ports = model[node].ports
            ports.remove(port)
            model[node].ports = ports

        def move_up(model: "GraphModel", node: Any, port: Any):
            """Move the given port one position up"""
            ports: List = model[node].ports
            index = ports.index(port)
            if index > 0:
                ports.insert(index - 1, ports.pop(index))
                model[node].ports = ports

        def move_down(model: "GraphModel", node: Any, port: Any):
            """Move the given port one position down"""
            ports: List = model[node].ports
            index = ports.index(port)
            if index < len(ports) - 1:
                ports.insert(index + 1, ports.pop(index))
                model[node].ports = ports

        def move_top(model: "GraphModel", node: Any, port: Any):
            """Move the given port to the top of the node"""
            ports: List = model[node].ports
            index = ports.index(port)
            if index > 0:
                ports.insert(0, ports.pop(index))
                model[node].ports = ports

        def move_bottom(model: "GraphModel", node: Any, port: Any):
            """Move the given port to the bottom of the node"""
            ports: List = model[node].ports
            index = ports.index(port)
            if index < len(ports) - 1:
                ports.insert(len(ports) - 1, ports.pop(index))
                model[node].ports = ports

        self.__port_context_menu = ui.Menu(
            "CompoundInputOutputNodeDelegate Port Menu", menu_compatibility=False, tearable=False
        )
        with self.__port_context_menu:
            if model[port].inputs:
                ui.MenuItem("Disconnect", triggered_fn=lambda m=model, p=port: disconnect(m, p))
            ui.MenuItem("Remove", triggered_fn=lambda m=model, n=node, p=port: remove(m, n, p))
            ui.MenuItem("Move Up", triggered_fn=lambda m=model, n=node, p=port: move_up(m, n, p))
            ui.MenuItem("Move Down", triggered_fn=lambda m=model, n=node, p=port: move_down(m, n, p))
            ui.MenuItem("Move Top", triggered_fn=lambda m=model, n=node, p=port: move_top(m, n, p))
            ui.MenuItem("Move Bottom", triggered_fn=lambda m=model, n=node, p=port: move_bottom(m, n, p))

        self.__port_context_menu.show()
