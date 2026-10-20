import functools

import carb
import omni.graph.core as og


class OgnSelect:
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
                og.Type(og.BaseDataType.TOKEN),
                og.AttributePortType.ATTRIBUTE_PORT_TYPE_INPUT,
                extendedType=og.ExtendedAttributeType.EXTENDED_ATTR_TYPE_ANY,
            )
        elif disconneted_count >= 2:
            for input in inputs[-(disconneted_count - 1) :]:
                node.remove_attribute(input)

    def _get_inputs(node):
        indices = []
        for attr in node.get_attributes():
            if attr.get_port_type() == og.AttributePortType.ATTRIBUTE_PORT_TYPE_INPUT and attr.get_name().startswith(
                "inputs:input"
            ):
                postfix = attr.get_name().removeprefix("inputs:input")
                if postfix.isnumeric():
                    indices.append(int(postfix))

        indices.sort()

        inputs = []
        for index in indices:
            inputs.append(f"inputs:input{index}")

        return inputs

    def on_connection_type_resolve(node):
        resolved_input_type = None
        for input in __class__._get_inputs(node):
            attr = node.get_attribute(input)
            type = attr.get_resolved_type()
            if type.base_type != og.BaseDataType.UNKNOWN:
                resolved_input_type = type
                break

        output = node.get_attribute("outputs:result")
        if resolved_input_type is not None:
            output.set_resolved_type(resolved_input_type)

    def compute(db):
        input_name = "input" + str(db.inputs.index)
        dyn_attrs = db.inputs.get_dynamic_attributes()
        if not dyn_attrs.has_attribute(input_name):
            carb.log_error(f"{input_name} doesn't exist.")
            return False

        value = dyn_attrs.get(input_name)
        db.outputs.result = value

        return True
