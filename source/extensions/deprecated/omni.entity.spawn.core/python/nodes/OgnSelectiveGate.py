import functools

import omni.graph.core as og


class OgnSelectiveGate:
    _node_type_name = None

    def initialize_type(node_type: og.NodeType):
        __class__._node_type_name = node_type.get_node_type()
        return True

    def initialize(graph_context, node):
        node.register_on_connected_callback(__class__._on_connection_changed)
        node.register_on_disconnected_callback(__class__._on_connection_changed)

        __class__._refresh_inputs(node)

    def _on_connection_changed(src, dest):
        if dest.get_node().get_type_name() == __class__._node_type_name:
            __class__._refresh_inputs(dest.get_node())

    def _refresh_inputs(node):
        inputs = __class__._get_inputs(node)
        disconneted_count = 0
        for input in reversed(inputs):
            attr = node.get_attribute(input)
            if attr.get_upstream_connection_count() > 0:
                break
            else:
                disconneted_count += 1

        if disconneted_count == 0:
            node.create_attribute(
                f"inputs:input{len(inputs)}",
                og.Type(og.BaseDataType.UINT, role=og.AttributeRole.EXECUTION),
                og.AttributePortType.ATTRIBUTE_PORT_TYPE_INPUT,
            )
        elif disconneted_count >= 2:
            for input in inputs[-(disconneted_count - 1) :]:
                node.remove_attribute(input)

    def _get_inputs(node):
        inputs = []
        for attr in node.get_attributes():
            if (
                attr.get_port_type() == og.AttributePortType.ATTRIBUTE_PORT_TYPE_INPUT
                and attr.get_resolved_type().role == og.AttributeRole.EXECUTION
            ):
                inputs.append(attr.get_name())

        inputs.sort()

        return inputs

    def compute(db):
        inputs = __class__._get_inputs(db.node)

        if db.inputs.index < 0 or db.inputs.index >= len(inputs):
            db.outputs.execOut = og.ExecutionAttributeState.DISABLED
            return True

        input_name = inputs[db.inputs.index]
        input_name = input_name.replace("inputs:", "")
        dyn_attrs = db.inputs.get_dynamic_attributes()
        state = dyn_attrs.get(input_name)
        if state in [
            og.ExecutionAttributeState.ENABLED,
            og.ExecutionAttributeState.ENABLED_AND_PUSH,
            og.ExecutionAttributeState.LATENT_FINISH,
        ]:
            db.outputs.execOut = og.ExecutionAttributeState.ENABLED
        else:
            db.outputs.execOut = og.ExecutionAttributeState.DISABLED

        return True
