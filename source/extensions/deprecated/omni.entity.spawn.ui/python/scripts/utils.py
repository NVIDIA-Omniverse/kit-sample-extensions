import random
from typing import Any, List, Tuple, Union

import carb
import omni.graph.core as og
import omni.kit.notification_manager as nm
import omni.usd
from omni.kit.property.usd import UsdAttributeModel
from pxr import Sdf, Usd, Vt

NODE_TYPE_HINTS = Union[str, og.Node, Usd.Prim, None]
ATTRIBUTE_TYPE_HINTS = Union[str, og.Attribute, Usd.Attribute]
ATTRIBUTE_VALUE_PAIR = Tuple[ATTRIBUTE_TYPE_HINTS, Any]
ATTRIBUTE_VALUE_PAIRS = Union[ATTRIBUTE_VALUE_PAIR, List[ATTRIBUTE_VALUE_PAIR]]
SPAWN_ATTR_SOURCE_PATH = "inputs:sourcePaths"


ALLOWED_TOKEN_KEY_INPUTS = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "Apostrophe",
    "Backslash",
    "Backspace",
    "CapsLock",
    "Comma",
    "Del",
    "Down",
    "End",
    "Enter",
    "Equal",
    "Escape",
    "F1",
    "F10",
    "F11",
    "F12",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
    "GraveAccent",
    "Home",
    "Insert",
    "Key0",
    "Key1",
    "Key2",
    "Key3",
    "Key4",
    "Key5",
    "Key6",
    "Key7",
    "Key8",
    "Key9",
    "Left",
    "LeftAlt",
    "LeftBracket",
    "LeftControl",
    "LeftShift",
    "LeftSuper",
    "Menu",
    "Minus",
    "NumLock",
    "Numpad0",
    "Numpad1",
    "Numpad2",
    "Numpad3",
    "Numpad4",
    "Numpad5",
    "Numpad6",
    "Numpad7",
    "Numpad8",
    "Numpad9",
    "NumpadAdd",
    "NumpadDel",
    "NumpadDivide",
    "NumpadEnter",
    "NumpadEqual",
    "NumpadMultiply",
    "NumpadSubtract",
    "PageDown",
    "PageUp",
    "Pause",
    "Period",
    "PrintScreen",
    "Right",
    "RightAlt",
    "RightBracket",
    "RightControl",
    "RightShift",
    "RightSuper",
    "ScrollLock",
    "Semicolon",
    "Slash",
    "Space",
    "Tab",
    "Up",
]


def _show_warning(message="warning!"):
    nm.post_notification(
        message,
        hide_after_timeout=False,
        duration=0,
        status=nm.NotificationStatus.WARNING,
        button_infos=[nm.NotificationButtonInfo("OK")],
    )
    carb.log_warn(message)


def create_nodes_for_transform_from_mesh(graph: og.Graph, mesh_path: Sdf.Path = None, on_surface: bool = True):
    stage = omni.usd.get_context().get_stage()
    with omni.kit.undo.group():
        graph_path = graph.get_path_to_graph()

        import_prim_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/import_prim", False)
        random_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/random", False)
        scatter_points_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/scatter_points", False)

        og.Controller.edit(
            graph_path,
            {
                og.Controller.Keys.CREATE_NODES: [
                    (import_prim_node_path, "omni.graph.ImportUSDPrim"),
                    (random_node_path, "omni.graph.nodes.RandomNumeric"),
                    (scatter_points_node_path, "omni.genproc.core.ScatterPoints"),
                ],
                og.Controller.Keys.SET_VALUES: [
                    (scatter_points_node_path + ".inputs:binormals", False),
                    (scatter_points_node_path + ".inputs:exclusive", False),
                    (scatter_points_node_path + ".inputs:normals", False),
                    (scatter_points_node_path + ".inputs:numDesiredPoints", 1),
                    (scatter_points_node_path + ".inputs:objectIndices", False),
                    (scatter_points_node_path + ".inputs:rotations", False),
                    (scatter_points_node_path + ".inputs:scales", False),
                    (scatter_points_node_path + ".inputs:scatterAcrossPoints", False),
                    (scatter_points_node_path + ".inputs:scatterInsideVolume", not on_surface),
                    (scatter_points_node_path + ".inputs:scatterOnSurface", on_surface),
                    (scatter_points_node_path + ".inputs:tangents", False),
                    (random_node_path + ".inputs:max", 9999999, "uint64"),
                    (random_node_path + ".inputs:min", 0, "uint64"),
                ],
                og.Controller.Keys.CONNECT: [
                    (("outputs_output", import_prim_node_path), ("inputs:prim", scatter_points_node_path)),
                    (("outputs:random", random_node_path), ("inputs:randomSeed", scatter_points_node_path)),
                ],
            },
        )

        if mesh_path is not None:
            omni.kit.commands.execute(
                "SetRelationshipTargets",
                relationship=stage.GetRelationshipAtPath(import_prim_node_path + ".inputs:prim"),
                targets=[mesh_path],
            )

        return og.get_node_by_path(scatter_points_node_path).get_attribute("outputs_bundle"), og.get_node_by_path(
            random_node_path
        ).get_attribute("inputs:execIn")


"""
print("#################################################################")
spawn_entity_node = og.get_node_by_path("/World/ActionGraph/spawn_entity")
if spawn_entity_node is not None:
    create_nodes_for_transform_from_mesh(spawn_entity_node, "/World/Cylinder", False)
"""


def create_nodes_for_transform_from_curve(spawn_entity_node: og.Node, curve_path: str):
    stage = omni.usd.get_context().get_stage()
    with omni.kit.undo.group():
        graph_path = spawn_entity_node.get_graph().get_path_to_graph()

        import_prim_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/import_prim", False)
        point_on_curve_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/point_on_curve", False)
        to_double_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/to_double", False)
        make_transform_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/make_transform", False)
        og.Controller.edit(
            graph_path,
            {
                og.Controller.Keys.CREATE_NODES: [
                    (import_prim_node_path, "omni.graph.ImportUSDPrim"),
                    (point_on_curve_node_path, "omni.genproc.core.PointOnCurve"),
                    (to_double_node_path, "omni.graph.nodes.ToDouble"),
                    (make_transform_node_path, "omni.graph.nodes.MakeTransform"),
                ],
                og.Controller.Keys.SET_VALUES: [
                    (point_on_curve_node_path + ".inputs:uValue", random.random()),
                ],
                og.Controller.Keys.CONNECT: [
                    (("outputs_output", import_prim_node_path), ("inputs:curvesBundle", point_on_curve_node_path)),
                    (("outputs:point", point_on_curve_node_path), ("inputs:value", to_double_node_path)),
                    (("outputs:converted", to_double_node_path), ("inputs:translation", make_transform_node_path)),
                    (("outputs:transform", make_transform_node_path), ("inputs:transform", spawn_entity_node)),
                ],
            },
        )

        omni.kit.commands.execute(
            "SetRelationshipTargets",
            relationship=stage.GetRelationshipAtPath(import_prim_node_path + ".inputs:prim"),
            targets=[curve_path],
        )


"""
print("#################################################################")
spawn_entity_node = og.get_node_by_path("/World/ActionGraph/spawn_entity")
if spawn_entity_node is not None:
    create_nodes_for_transform_from_curve(spawn_entity_node, "/World/BasisCurves")
"""


def create_nodes_for_transform_from_prim(graph: og.Graph):
    # print("create_nodes_for_transform_from_prim()")
    stage = omni.usd.get_context().get_stage()
    with omni.kit.undo.group():
        graph_path = graph.get_path_to_graph()

        read_time_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/read_time", False)
        get_xform_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/get_xform", False)
        select_transform_node = _create_node(node_type="omni.entity.spawn.core.SelectTransformTRS", graph=graph)
        og.Controller.edit(
            graph_path,
            {
                og.Controller.Keys.CREATE_NODES: [
                    (read_time_node_path, "omni.graph.nodes.ReadTime"),
                    (get_xform_node_path, "omni.anim.GetXform"),
                ],
                og.Controller.Keys.CONNECT: [
                    (("outputs:frame", read_time_node_path), ("inputs:usdTimecode", get_xform_node_path)),
                    (("outputs:transform", get_xform_node_path), ("inputs:transform", select_transform_node)),
                ],
            },
        )

        # omni.kit.commands.execute("SetRelationshipTargets", relationship=stage.GetRelationshipAtPath(get_xform_node_path + ".inputs:prim"), targets=[prim_path])

    return select_transform_node.get_attribute("outputs:transform")


"""
print("#################################################################")
spawn_entity_node = og.get_node_by_path("/World/ActionGraph/spawn_entity")
if spawn_entity_node is not None:
    create_nodes_for_transform_from_prim(spawn_entity_node, "/World/Cylinder")
"""


# We assume that the spawner graph is right below the root graph
def _get_spawner_graph(spawn_graph_name="MySpawnGraph"):
    """
    Return the /World/SpawnEntityGraph graph path from default scene root if found or create and return a new graph
    """

    stage = omni.usd.get_context().get_stage()
    root_path = ""
    dp = stage.GetDefaultPrim()
    if dp:
        root_path = dp.GetPath()

    # find graph under default prim
    graph = next(
        (
            x
            for x in og.get_all_graphs()
            if (not root_path or x.get_path_to_graph().rsplit("/", 1)[0] == root_path)
            and og.get_graph_settings(x).evaluator_type == "execution"
        ),
        None,
    )

    if not graph:
        free_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{spawn_graph_name}", False)
        # create time node on a brand new graph which force create the graph as well
        (graph, nodes, _, _) = og.Controller.edit({"graph_path": free_path, "evaluator_name": "execution"}, {})

    return graph


# We assume that the spawner graph is right below the root graph
def create_spawner_graph(spawn_graph_name="MySpawnGraph"):
    """
    Return the /World/SpawnEntityGraph graph path from default scene root if found or create and return a new graph
    """

    stage = omni.usd.get_context().get_stage()
    root_path = ""
    dp = stage.GetDefaultPrim()
    if dp:
        root_path = dp.GetPath()

    free_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{spawn_graph_name}", False)
    # create time node on a brand new graph which force create the graph as well
    (graph, nodes, _, _) = og.Controller.edit({"graph_path": free_path, "evaluator_name": "execution"}, {})

    return graph


def _create_node(node_type, name="", append_type_name=True, graph=None):
    """Create node with next available path in the graph

    Args:
        node_type: reader node type. Defaults to None.
        name (Str, Optional): name of the node. Default: ""
        append_type_name (Bool, Optional): Append node type in the name. Default: True
        graph (Optional): Graph object. Default: None

    Returns:
        The create OmniGraph Node

    """
    if not graph:
        graph = _get_spawner_graph()

    stage = omni.usd.get_context().get_stage()
    if name:
        if append_type_name:
            name = "{}_{}".format(name, node_type.split(".")[-1])
    else:
        name = node_type.split(".")[-1]

    # find resolved name
    free_path = omni.usd.get_stage_next_free_path(stage, "{}/{}".format(graph.get_path_to_graph(), name), False)
    res_name = og.Controller.split_graph_from_node_path(free_path)[1]

    (graph, [node], _, _) = og.Controller.edit(graph, {og.Controller.Keys.CREATE_NODES: (res_name, node_type)})
    return node


def _set_value(node: og.Node, values_to_set: dict, graph=None):
    """Set the values to the OmniGraph Node's attribute

    Args:
        node: The node to set values to.
        values_to_set: a dict with {"attribute name": attribute_value}
        graph (Optional): Graph object. Default: None

    Returns:
        No returns, if there are any incompatible attributes, OmniGraph errors will be raised

    """
    if not graph:
        graph = _get_spawner_graph()

    controller = og.Controller()
    keys = controller.Keys

    values = [((key, node), value) for key, value in values_to_set.items()]

    controller.edit(graph, {keys.SET_VALUES: values})


def create_spawn_event_nodes(graph: og.Graph, event_index: int, input_values: dict):
    select_node = _create_node(node_type="omni.entity.spawn.core.SelectiveGate", graph=graph)

    key_event_node = _create_node(node_type="omni.graph.action.OnKeyboardInput", graph=graph)
    og.Controller.connect(key_event_node.get_attribute("outputs:pressed"), select_node.get_attribute("inputs:input0"))

    stage_event_node = _create_node(node_type="omni.graph.action.OnStageEvent", graph=graph)
    og.Controller.connect(stage_event_node.get_attribute("outputs:execOut"), select_node.get_attribute("inputs:input1"))
    og.Controller.set(
        attribute=stage_event_node.get_attribute("inputs:eventName"),
        value="OmniGraph Start Play",
        undoable=True,
        update_usd=True,
    )

    og.Controller.set(
        attribute=select_node.get_attribute("inputs:index"), value=event_index, undoable=True, update_usd=True
    )
    if event_index == 0:
        for name, value in input_values.items():
            og.Controller.set(
                attribute=key_event_node.get_attribute("inputs:" + name), value=value, undoable=True, update_usd=True
            )

    return select_node.get_attribute("outputs:execOut")


def create_event_node(
    event: str = "Key Pressed",
    key: str = "A",
    has_ctrl: bool = False,
    has_shift: bool = False,
    has_alt: bool = False,
    consume: bool = True,
    prim_path: str = None,
    spawner_graph=None,
):
    """Create an event node with next available path in the graph.
        Currently only support 'Key Pressed' 'Key Released' 'Start Playback` 'Stop playback' four events

    Args:
        event(Optional):        name of the event which corresponds to the node type. Default:"Key Pressed"
        key(Optional):          Key's name, e.g. A to Z.  Only useful when the event name is 'Key Pressed' or `Key Released`.  Default:"A"
        has_ctrl(Optional):     Whether to use the Ctrl modifier key. Only useful when the event name is 'Key Pressed' or `Key Released`. Default: False
        has_shift(Optional):    Whether to use the Shift modifier key. Only useful when the event name is 'Key Pressed' or `Key Released`. Default: False
        has_alt(Optional):      Whether to use the Alt modifier key. Only useful when the event name is 'Key Pressed' or `Key Released`. Default: False
        consume(Optional):      Whether the event is consumed(only take place once). Only useful when the event name is "Key Pressed" or "Key Released", Default: True
        prim_path(Optional):    The auxiliar prim path for the future "Collision" type support, not used right now. Default: None
        graph (Optional):       Graph object. Default: None

    Returns:
        The create OmniGraph Node and the output attribute plug

    """

    if not spawner_graph:
        spawner_graph = _get_spawner_graph()
    if event == "Key Pressed" or event == "Key Released":
        event_node = _create_node(node_type="omni.graph.action.OnKeyboardInput", graph=spawner_graph)
        if event_node:
            _set_value(event_node, {"inputs:keyIn": key}, graph=spawner_graph)
            _set_value(event_node, {"inputs:ctrlIn": has_ctrl}, graph=spawner_graph)
            _set_value(event_node, {"inputs:altIn": has_alt}, graph=spawner_graph)
            _set_value(event_node, {"inputs:shiftIn": has_shift}, graph=spawner_graph)
            if event == "Key Pressed":
                out_attribute = event_node.get_attribute("outputs:pressed")
            else:
                out_attribute = event_node.get_attribute("outputs:released")
            return event_node, out_attribute
    elif event == "Simulation Start":
        event_node = _create_node(node_type="omni.graph.action.OnStageEvent", graph=spawner_graph)
        if event_node:
            _set_value(event_node, {"inputs:eventName": "OmniGraph Start Play"}, graph=spawner_graph)
            out_attribute = event_node.get_attribute("outputs:execOut")
            return event_node, out_attribute
    elif event == "Simulation Stop":
        event_node = _create_node(node_type="omni.graph.action.OnStageEvent", graph=spawner_graph)
        if event_node:
            _set_value(event_node, {"inputs:eventName": "OmniGraph Stop Play"}, graph=spawner_graph)
            out_attribute = event_node.get_attribute("outputs:execOut")
            return event_node, out_attribute


def create_nodes_for_transform_from_curve(graph):
    random_node = _create_node(node_type="omni.graph.nodes.RandomNumeric", graph=graph)
    import_prim_node = _create_node(node_type="omni.graph.ImportUSDPrim", graph=graph)

    og.Controller.edit(
        graph,
        {
            og.Controller.Keys.SET_VALUES: [
                (("inputs:max", random_node), 1, "float"),
                (("inputs:min", random_node), 0, "float"),
            ]
        },
    )

    point_on_curve_node = _create_node(node_type="omni.genproc.core.PointOnCurve", graph=graph)
    point_on_curve_node.set_disabled(True)

    og.Controller.connect(
        random_node.get_attribute("outputs:random"), point_on_curve_node.get_attribute("inputs:uValue")
    )
    og.Controller.connect(
        import_prim_node.get_attribute("outputs_output"), point_on_curve_node.get_attribute("inputs:curvesBundle")
    )

    return point_on_curve_node.get_attribute("outputs:point"), random_node.get_attribute("inputs:execIn")


def create_transform_nodes(graph):
    select_node = _create_node(node_type="omni.entity.spawn.core.SelectTransform", graph=graph)

    # Value transform node
    value_transform_node = _create_node(node_type="omni.graph.nodes.MakeTransform", graph=graph)
    og.Controller.connect(
        value_transform_node.get_attribute("outputs:transform"), select_node.get_attribute("inputs:input0")
    )

    # Ranged transform node
    ranged_transform_node = _create_node(node_type="omni.entity.spawn.core.RandomTransform", graph=graph)
    og.Controller.connect(
        ranged_transform_node.get_attribute("outputs:transform"), select_node.get_attribute("inputs:input1")
    )

    # Prim transform node
    prim_transform_attr = create_nodes_for_transform_from_prim(graph)
    og.Controller.connect(prim_transform_attr, select_node.get_attribute("inputs:input2"))

    # Mesh node
    mesh_transform_attr, from_mesh_exec_in = create_nodes_for_transform_from_mesh(graph)
    og.Controller.connect(mesh_transform_attr, select_node.get_attribute("inputs:input3"))

    # Curve node
    curve_transform_attr, from_curve_exec_in = create_nodes_for_transform_from_curve(graph)
    og.Controller.connect(curve_transform_attr, select_node.get_attribute("inputs:input4"))

    result_attr = select_node.get_attribute("outputs:result")
    return result_attr, [from_mesh_exec_in, from_curve_exec_in]


def create_transform_matrix_node(
    translate: og.types.double3 = [0, 0, 0],
    rotateXYZ: og.types.float3 = [0, 0, 0],
    scale: og.types.float3 = [1.0, 1.0, 1.0],
    spawner_graph=None,
):
    """Create a MakeTransform node which will convert the translate/rotateXYZ/scale to a transform matrix

    Args:
        translate(Optional):        translation vector. Default is [0,0,0]
        rotateXYZ(Optional):        rotation vector, Euler angles.  Default is [0, 0, 0]
        scale(Optional):            scale vector.  Default is [1, 1, 1]
        spawner_graph (Optional):   SpawnerGraph object. Default: None

    Returns:
        The create OmniGraph Node and the output attribute plug

    """
    if not spawner_graph:
        spawner_graph = _get_spawner_graph()
    make_transform_node = _create_node(node_type="omni.graph.nodes.MakeTransform", graph=spawner_graph)
    if make_transform_node:
        _set_value(
            make_transform_node,
            {"inputs:translation": translate, "inputs:rotationXYZ": rotateXYZ, "inputs:scale": scale},
            graph=spawner_graph,
        )
    return make_transform_node


def create_spawn_entity_node(spawn_even_node_out_attribute: og.Attribute, transform_attr, spawner_graph=None):
    """Create a SpawnEntity node and connect the node to the rest of the nodes

    Args:
        spawn_event_node:               A trigger node on when to spawn the entity. The upper stream node of the SpawnEntity node's ExecIn plug
        spawn_even_node_out_attribute:  The attribute plug from the spawn_event_node. It will connect to SpawnEntity node's ExecIn plug
        transform_node:                 The transform matrix node which conncects to the SpawnEnity's transform input plug
        spawner_graph (Optional):       SpawnerGraph object. Default: None

    Returns:
        The create SpawnEntity OmniGraph Node

    """
    if not spawner_graph:
        spawner_graph = _get_spawner_graph()

    spawn_entity_node = _create_node(node_type="omni.entity.spawn.core.SpawnEntity", graph=spawner_graph)
    loop_node = _create_node(node_type="omni.graph.action.ForLoop", graph=spawner_graph)

    controller = og.Controller()
    """
    if transform_node:
        controller.edit(spawner_graph, {
            controller.Keys.CONNECT: [
                #(("inputs:value", source_path_node), ("inputs:sourcePaths",spawn_entity_node)),
                ((spawn_even_node_out_attribute, spawn_event_node), ("inputs:execIn", spawn_entity_node)),
                (("outputs:transform", transform_node), ("inputs:transform", spawn_entity_node))
            ]
        })
    else:"""
    controller.edit(
        spawner_graph,
        {
            controller.Keys.CONNECT: [
                (spawn_even_node_out_attribute, ("inputs:execIn", loop_node)),
                (("outputs:loopBody", loop_node), ("inputs:execIn", spawn_entity_node)),
                (transform_attr, ("inputs:transform", spawn_entity_node)),
            ],
            controller.Keys.SET_VALUES: [(("inputs:stop", loop_node), 1)],
        },
    )

    return spawn_entity_node, loop_node.get_attribute("outputs:loopBody")


def create_destroy_entity_node(spawn_entity_node, spawner_graph=None):
    """Create a DestroyEntity node and connect the node to its upperstream nodes

    Args:
        spawn_entity_node:                  SpawnEntity node which contains an entityName output plug connect to DestroyNode's input entityName
        destory_event_node:                 A trigger node on when to destroy the entity. The upper stream node of the DestroyEntity node's ExecIn plug
        destroy_event_node_out_attribute:   The attribute plug from the destroy_event_node. It will connect to DestroyEntity node's ExecIn plug
        spawner_graph (Optional):       SpawnerGraph object. Default: None

    Returns:
        The create DestroyEntity OmniGraph Node

    """
    if not spawner_graph:
        spawner_graph = _get_spawner_graph()

    stage_event_node = _create_node(node_type="omni.graph.action.OnStageEvent", graph=spawner_graph)
    branch_node = _create_node(node_type="omni.graph.action.Branch", graph=spawner_graph)
    key_node = _create_node(node_type="omni.graph.action.OnKeyboardInput", graph=spawner_graph)
    select_node = _create_node(node_type="omni.entity.spawn.core.SelectiveGate", graph=spawner_graph)
    destroy_entity_node = _create_node(node_type="omni.entity.spawn.core.DestroyEntity", graph=spawner_graph)

    controller = og.Controller()

    controller.edit(
        spawner_graph,
        {
            controller.Keys.CONNECT: [
                (("outputs:pressed", key_node), ("inputs:input0", select_node)),
                (("outputs:execOut", select_node), ("inputs:execIn", destroy_entity_node)),
                (("outputs:execOut", stage_event_node), ("inputs:execIn", branch_node)),
                (("outputs:execTrue", branch_node), ("inputs:execIn", destroy_entity_node)),
                (("outputs:allSpawnedEntityNames", spawn_entity_node), ("inputs:entityNames", destroy_entity_node)),
            ],
            controller.Keys.SET_VALUES: [
                (("inputs:condition", branch_node), True),
                (("inputs:eventName", stage_event_node), "OmniGraph Stop Play"),
                (("inputs:index", select_node), -1),
            ],
        },
    )

    return destroy_entity_node


def set_spawn_source_paths(spawn_entity_node, source_paths: list):
    """Set source paths in spawn entity node

    Args:
        spawn_entity_node: SpawnEntity node which contains an entityName output plug connect to DestroyNode's input entityName
        source_paths:      list of source paths
    """
    keys = og.Controller.Keys
    og.Controller.edit(
        spawn_entity_node.get_graph(),
        {keys.SET_VALUES: [((SPAWN_ATTR_SOURCE_PATH, spawn_entity_node), Vt.TokenArray(source_paths))]},
    )


def get_upstream_node(input_attr: og.Attribute, input_attr_names: list) -> og.Node:
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
    return get_upstream_node(upstream_input, input_attr_names[1:])


def get_usd_attribute_model(stage, node, attribute_name, cls=UsdAttributeModel):
    attr_path = Sdf.Path(node.get_prim_path() + "." + attribute_name)
    attr = stage.GetAttributeAtPath(attr_path)
    model = cls(stage, [attr_path], False, attr.GetAllMetadata())
    return attr_path, model


def locate_file(model):
    url = model.get_value_as_string()
    if len(url) == 0:
        return

    if Sdf.Path.IsValidPathString(url):
        import omni.usd

        context = omni.usd.get_context()
        context.get_selection().set_selected_prim_paths([url], True)
        return

    # omni.kit.window.content_browser is optional dependency
    try:
        from omni.kit.property.usd.asset_filepicker import replace_query

        # Remove the checkpoint and branch so navigate_to works
        url = replace_query(url, None)

        import omni.kit.window.content_browser

        instance = omni.kit.window.content_browser.get_instance()
        instance.navigate_to(url)
    except Exception as e:
        carb.log_warn(f"Failed to locate file: {e}")


def create_default_spawn_graph():
    with omni.kit.undo.group():
        spawner_graph = create_spawner_graph()

        default_event_inputs = {"keyIn": "A", "ctrlIn": False, "shiftIn": False, "altIn": False}
        # Default spawn event is Key Pressed, no modifier key.
        spawn_event_attr = create_spawn_event_nodes(spawner_graph, event_index=0, input_values=default_event_inputs)

        # Create an identity transform matrix node
        transform_output, exec_ins = create_transform_nodes(spawner_graph)

        # Create the spawn entity node and connect to the spawn event node, source path node, transform matrix node
        spawn_entity_node, loop_exec_out = create_spawn_entity_node(
            spawn_event_attr, transform_output, spawner_graph=spawner_graph
        )

        # Connect random generator nodes
        for exec_in in exec_ins:
            og.Controller.connect(loop_exec_out, exec_in)

        # Create the destroy entity node connect from the spawn entity node
        destroy_entity_node = create_destroy_entity_node(
            spawn_entity_node=spawn_entity_node, spawner_graph=spawner_graph
        )
