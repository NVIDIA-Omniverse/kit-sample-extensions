import carb
import omni.graph.core as og
import pxr.Gf


class OgnSelectTransform:
    def initialize(graph_context, node):
        attr = node.get_attribute("inputs:index")
        attr.register_value_changed_callback(__class__._on_index_changed)

        __class__._on_index_changed(attr)

    def _get_upstream_node(input_attr: og.Attribute, input_attr_names: list) -> og.Node:
        """Get upsteam node recurrence

        Args:
            input_attr:        Start Attribute
            input_attr_names:  Attribute names link for recursive up

        Returns:
            Find the topmost node or None
        """
        upstreams = input_attr.get_upstream_connections()
        if not upstreams:
            return None

        upstream_node = upstreams[0].get_node()
        if not input_attr_names:
            return upstream_node

        upstream_input = upstream_node.get_attribute(input_attr_names[0])
        return __class__._get_upstream_node(upstream_input, input_attr_names[1:])

    def compute(db):
        if db.inputs.index == 0:
            db.outputs.result = db.inputs.input0
        elif db.inputs.index == 1:
            db.outputs.result = db.inputs.input1
        elif db.inputs.index == 2:
            db.outputs.result = db.inputs.input2
        elif db.inputs.index == 3:
            point = db.inputs.input3.bundle.get_attribute_by_name("points").get()[0]

            transform = pxr.Gf.Matrix4d()
            transform.SetTranslate(pxr.Gf.Vec3d(float(point[0]), float(point[1]), float(point[2])))

            db.outputs.result = transform
        elif db.inputs.index == 4:
            transform = pxr.Gf.Matrix4d()
            transform.SetTranslate(
                pxr.Gf.Vec3d(float(db.inputs.input4[0]), float(db.inputs.input4[1]), float(db.inputs.input4[2]))
            )

            db.outputs.result = transform
        else:
            carb.low_error(f"index {db.inputs.index} must be between 0 and 4.")

        return True

    def _on_index_changed(attr):
        input4 = attr.get_node().get_attribute("inputs:input4")
        curve_node = __class__._get_upstream_node(input4, [])
        if curve_node is not None:
            curve_node.set_disabled(attr.get() != 4)
