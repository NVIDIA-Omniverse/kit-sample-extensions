from collections import OrderedDict

import carb
import omni.graph.core as og
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, UsdSkel

GRAPH_TYPE = {"PushGraph": "push", "LazyGraph": "dirty_push", "ActionGraph": "execution"}


def get_prim(obj):
    """To get Usd Prim by given path.

    Args:
        obj: Path or Sdf path or Usd Prim.

    Returns:
        UsdPrim at the given path.

    """
    stage = omni.usd.get_context().get_stage()

    if isinstance(obj, Usd.Prim):
        return obj
    elif isinstance(obj, str) or isinstance(obj, Sdf.Path):
        return stage.GetPrimAtPath(obj)
    else:
        try:
            return get_prim(obj.GetPath())
        except:
            carb.log_error(f"Invalid object: {obj}")
            return None


class MeshData(object):
    """Mesh data container."""

    def __init__(self):
        super().__init__()
        self.points = []
        self.normals = []
        self.faceVertexIndices = []
        self.faceVertexCounts = []
        self.uvs = OrderedDict()
        self.subsetFamilies = OrderedDict()
        self.subsets = OrderedDict()
        self.interpolationTypes = OrderedDict()
        self.meshPrimvars = OrderedDict()
        self.skelMeshPrimvars = OrderedDict()
        self.skelRelationships = OrderedDict()
        self.elementSize = OrderedDict()
        self.custom_data = []


def create_mesh(
    path, mesh_data: MeshData, normal: bool, subset: bool, mesh_primvars: bool, skel_mesh_primvars: bool = False
):
    """Create a mesh by given mesh data.

    Args:
        path: Sdf path where mesh will be created.
        mesh_data (MeshData): Mesh geometric information.
        normal (bool): Include normal attribute.
        subset (bool): Include geom subsets.
        mesh_primvars (bool): Include Mesh primvars attributes such as doNotCastShadows
        skel_mesh_primvars (bool, optional): Include copy USDSkel mesh attributes from Mesh such as jointWeights

    Returns:
        The created UsdGeom Mesh.
    """
    stage = omni.usd.get_context().get_stage()
    attrs = {UsdGeom.Tokens.points: mesh_data.points}  # Pass points to command to avoid errors of bound computing.
    omni.kit.commands.execute(
        "CreatePrimCommand",
        prim_path=path,
        prim_type="Mesh",
        select_new_prim=False,
        attributes=attrs,
        create_default_xform=False,
    )
    prim = stage.GetPrimAtPath(path)
    mesh = UsdGeom.Mesh(prim)

    mesh.CreateFaceVertexCountsAttr().Set(mesh_data.faceVertexCounts)
    mesh.CreateFaceVertexIndicesAttr().Set(mesh_data.faceVertexIndices)

    # shading and texture
    if normal and mesh_data.normals:
        mesh.CreateNormalsAttr().Set(mesh_data.normals)
        mesh.SetNormalsInterpolation(mesh_data.interpolationTypes["normals"])

    display_color = prim.GetAttribute("primvars:displayColor")
    display_color.Set([Gf.Vec3f(0.5, 0.5, 0.5)])
    for mapName in mesh_data.uvs:
        uvset = mesh_data.uvs[mapName]
        uvAttr = prim.CreateAttribute(mapName, Sdf.ValueTypeNames.TexCoord2fArray, False)
        uvAttr.Set(uvset["uvs"])
        if uvset["customData"]:
            uvAttr.SetCustomData(uvset["customData"])
        UsdGeom.Primvar(uvAttr).SetInterpolation(mesh_data.interpolationTypes[mapName])
        if uvset["indices"]:
            prim.CreateAttribute("{}:indices".format(mapName), Sdf.ValueTypeNames.IntArray, False).Set(uvset["indices"])

    if subset:
        for family in mesh_data.subsetFamilies:
            value = mesh_data.subsetFamilies[family]
            prim.CreateAttribute(family, Sdf.ValueTypeNames.Token, False, Sdf.VariabilityUniform).Set(value)

        for subsetName in mesh_data.subsets:
            subset_data = mesh_data.subsets[subsetName]
            subsetPrim = stage.DefinePrim(f"{path}/{subsetName}", "GeomSubset")
            subsetPrim.CreateAttribute("elemetType", Sdf.ValueTypeNames.Token, False, Sdf.VariabilityUniform).Set(
                subset_data["elementType"]
            )
            subsetPrim.CreateAttribute("familyName", Sdf.ValueTypeNames.Token, False, Sdf.VariabilityUniform).Set(
                subset_data["familyName"]
            )
            subsetPrim.CreateAttribute("indices", Sdf.ValueTypeNames.IntArray, False).Set(subset_data["indices"])
            subsetPrim.CreateRelationship("material:binding", False).SetTargets(subset_data["material:binding"])

    # mesh primvars defined in mesh_data
    if mesh_primvars:
        if mesh_data.meshPrimvars:
            for at in mesh_data.meshPrimvars:
                at_type = mesh_data.meshPrimvars[at]["typeName"]
                at_value = mesh_data.meshPrimvars[at]["value"]
                prim.CreateAttribute(at, at_type).Set(at_value)

    # skel mesh primvars defined in mesh_data
    if skel_mesh_primvars:
        if mesh_data.skelMeshPrimvars:
            UsdSkel.BindingAPI.Apply(prim)
            for at in mesh_data.skelMeshPrimvars:
                at_value = mesh_data.skelMeshPrimvars[at]["value"]
                if not at_value:
                    continue
                prim.GetAttribute(at).Set(at_value)
                if at in mesh_data.interpolationTypes and at in mesh_data.elementSize:
                    prim_API = UsdGeom.PrimvarsAPI(prim)
                    prim_API.GetPrimvar(at).SetInterpolation(mesh_data.interpolationTypes[at])
                    prim_API.GetPrimvar(at).SetElementSize(mesh_data.elementSize[at])

            if mesh_data.skelRelationships:
                for rel_name in mesh_data.skelRelationships:
                    prim.CreateRelationship(rel_name, False)

    # custom data
    if mesh_data.custom_data:
        for custom_data in mesh_data.custom_data:
            attr = prim.CreateAttribute(custom_data.get("attr_name"), custom_data.get("attr_type"), True)
            attr.SetCustomData(custom_data.get("data_value"))

    return mesh


def get_mesh_interpolation_type(obj, attribute_name: str):
    """Get attribute interpolation type from mesh and primVars.

    Args:
        obj: Path or Sdf path or Usd Prim.
        attribute_name: name of attribute in string

    Returns:
        interpolation type. e.g) constant, vetex, faceVarying
    """
    # get interpolation type, method UsdGeom.PrimvarsAPI
    prim = get_prim(obj)
    intp_type = None
    if attribute_name.startswith("primvars:"):
        prim_API = UsdGeom.PrimvarsAPI(prim)
        intp_type = prim_API.GetPrimvar(attribute_name).GetInterpolation()
    else:
        # get interpolation type, from mesh
        if "normals" == attribute_name:
            intp_type = UsdGeom.Mesh(prim).GetNormalsInterpolation()

    return intp_type


def get_mesh_element_size(obj, attribute_name: str):
    """Get attribute element size from mesh and primVars.

    Args:
        obj: Path or Sdf path or Usd Prim.
        attribute_name: name of attribute in string

    Returns:
        element size. e.g) 9
    """
    prim = get_prim(obj)
    elem_size = None
    if attribute_name.startswith("primvars:"):
        prim_API = UsdGeom.PrimvarsAPI(prim)
        elem_size = prim_API.GetPrimvar(attribute_name).GetElementSize()

    return elem_size


def get_mesh_data(obj, time_code, skel_mesh_primvars=False):
    """Get mesh data from existed mesh path from USD.

    Args:
        obj: Path or Sdf path or Usd Prim.
        time_code: Time to get the data.
        skel_mesh_primvars (bool, optional): Include copy USDSkel mesh attributes from Mesh such as jointWeights

    Returns:
        MeshData if succeeded or None if failed .
    """
    prim = get_prim(obj)
    if prim.GetTypeName() != "Mesh":
        carb.log_error(f"Invalid object type: {type(obj)}")
        return None

    mesh_data = MeshData()

    mesh_data.points = prim.GetAttribute("points").Get(time_code)
    mesh_data.normals = prim.GetAttribute("normals").Get(time_code)
    mesh_data.faceVertexIndices = prim.GetAttribute("faceVertexIndices").Get(time_code)
    mesh_data.faceVertexCounts = prim.GetAttribute("faceVertexCounts").Get(time_code)

    # Mesh primvars need to copy and if it has been modified
    mesh_primvars = [
        "primvars:doNotCastShadows",
        "primvars:enableShadowTerminatorFix",
        "primvars:holdoutObject",
        "primvars:invisibleToSecondaryRays",
        "primvars:isMatteObject",
        "primvars:multimatte_id",
    ]

    # only collect attribute that has been modified
    for at in mesh_primvars:
        if prim.HasProperty(at):
            _prpt = prim.GetProperty(at)
            mesh_data.meshPrimvars[at] = {"typeName": _prpt.GetTypeName(), "value": _prpt.Get()}

    # Skel Mesh primvars need to copy
    if prim.HasAPI(UsdSkel.BindingAPI) and skel_mesh_primvars:
        skel_mesh_primvars = [
            "primvars:skel:geomBindTransform",
            "primvars:skel:jointIndices",
            "primvars:skel:jointWeights",
            "primvars:skel:skinningBlendWeights",
            "slel:blendShapes",
            "skel:joints",
            "skel:skinningMethod",
        ]
        for at in skel_mesh_primvars:
            if prim.HasProperty(at):
                _prpt = prim.GetProperty(at)
                if not _prpt:
                    continue
                if not _prpt.Get():
                    continue
                mesh_data.skelMeshPrimvars[at] = {"typeName": _prpt.GetTypeName(), "value": _prpt.Get()}
                if at.endswith("jointIndices") or at.endswith("jointWeights"):
                    mesh_data.interpolationTypes[at] = get_mesh_interpolation_type(prim, at)
                    mesh_data.elementSize[at] = get_mesh_element_size(prim, at)

        skel_rels = [
            "skel:animationSource",
            "skel:blendShapeTargets",
            "skel:skeleton",
        ]
        for rel_name in skel_rels:
            rel = prim.GetRelationship(rel_name)
            if not rel:
                continue
            targets = rel.GetTargets()
            mesh_data.skelRelationships[rel_name] = {"relationshipName": rel_name, "targets": targets}

    # shading
    mesh_data.interpolationTypes["normals"] = get_mesh_interpolation_type(prim, "normals")

    for attr in prim.GetAttributes():
        if attr.HasCustomData():
            for v in attr.GetCustomData().values():
                if not isinstance(v, dict) or not v:
                    continue
                if "UVSetIndex" in v.keys():
                    mapName = attr.GetName()
                    uvset = {}
                    uvset["uvs"] = attr.Get(time_code)
                    uvset["customData"] = attr.GetCustomData()
                    uvset["variability"] = attr.GetVariability()
                    idxAttr = prim.GetAttribute(f"{mapName}:indices")
                    if idxAttr:
                        uvset["indices"] = idxAttr.Get(time_code)
                    else:
                        uvset["indices"] = None

                    mesh_data.uvs[mapName] = uvset
                    continue
            if "primvars:" not in attr.GetName():
                mesh_data.custom_data.append(
                    {"attr_name": attr.GetName(), "attr_type": attr.GetTypeName(), "data_value": attr.GetCustomData()}
                )
        if (
            "primvars:" in attr.GetName()
            and "texCoord2" in str(attr.GetTypeName())
            or "float2[]" in str(attr.GetTypeName())
        ):
            mapName = attr.GetName()
            uvset = {}
            uvset["uvs"] = attr.Get(time_code)
            uvset["customData"] = None
            uvset["variability"] = attr.GetVariability()
            idxAttr = prim.GetAttribute(f"{mapName}:indices")
            if idxAttr:
                uvset["indices"] = idxAttr.Get(time_code)
            else:
                uvset["indices"] = None
            mesh_data.uvs[mapName] = uvset
            mesh_data.interpolationTypes[mapName] = get_mesh_interpolation_type(prim, mapName)
        if attr.GetNamespace().startswith("subsetFamily:"):
            mesh_data.subsetFamilies[str(attr.GetBaseName())] = attr.Get()

    for child in prim.GetChildren():
        localName = str(child.GetName())
        if child.GetTypeName() == "GeomSubset":
            subset = {}
            subset["elementType"] = child.GetAttribute("elementType").Get()
            subset["familyName"] = child.GetAttribute("familyName").Get()
            subset["indices"] = child.GetAttribute("indices").Get()
            subset["material:binding"] = child.GetRelationship("material:binding").GetTargets()
            mesh_data.subsets[localName] = subset

    return mesh_data


def copyXform(src, dest, time_code):
    """Copy all xformOp property from src to dest.

    Args:
        src: Source path or Sdf path or Usd Prim.
        dest: Destination path or Sdf path or Usd Prim.
        time_code: Time to get the data.

    Returns:
        None

    """
    srcPrim = get_prim(src)
    destPrim = get_prim(dest)
    for prop in srcPrim.GetAttributes():
        if prop.GetName().startswith("xformOp"):
            if prop.Get(time_code):
                destPrim.CreateAttribute(prop.GetName(), prop.GetTypeName(), False).Set(prop.Get(time_code))


def stamp_mesh(*args, **kwargs):
    carb.log_warn("stamp_mesh is deprecated. Use stamp_geom instead")
    return stamp_geom(*args, **kwargs)


def stamp_geom(
    obj, stamp_path=None, postfix: str = "stamp", normal: bool = True, subset: bool = False, mesh_primvars: bool = True
):
    """Create a clean Geometry (Mesh, Curve, etc) copy of the input prim.

    Args:
        obj: Path or Sdf path or Usd Prim.
        stamp_path (optional): Result path. Defaults to None.
        postfix (str, optional): Result postfix name to use if stamp_path is not provided. Defaults to "stamp".
        normal (bool, optional): Include normal attribute. Defaults to True.
        subset (bool, optional): Include geom subsets. Defaults to False.
        mesh_primvars (bool, optional): Include copy attribute from Mesh such as doNotCastShadows

    Returns:
        The result UsdPrim.

    """

    stage = omni.usd.get_context().get_stage()
    prim = get_prim(obj)
    if not stamp_path:
        stamp_path = omni.usd.get_stage_next_free_path(stage, f"{prim.GetPath()}_{postfix}", False)

    curr_time = omni.timeline.get_timeline_interface().get_current_time()
    current_time_code = Usd.TimeCode(curr_time * stage.GetTimeCodesPerSecond())

    prim_type = prim.GetTypeName()

    if prim_type == "Mesh":
        mesh_data = get_mesh_data(prim, current_time_code)
        geom = create_mesh(stamp_path, mesh_data, normal=normal, subset=subset, mesh_primvars=mesh_primvars)

    elif prim_type == "BasisCurves":
        curve_data = get_curve_data(prim, current_time_code)
        geom = create_curve(stamp_path, curve_data)

    else:
        carb.log_error(f"Invalid object type: {prim_type}")
        return

    copyXform(prim, geom.GetPrim(), curr_time)

    # copy material binding
    targets = prim.GetRelationship("material:binding").GetTargets()
    geom.GetPrim().CreateRelationship("material:binding", False).SetTargets(targets)
    return geom.GetPrim()


def get_graph(graph_type="LazyGraph"):
    """
    Return the push graph path from default scene root if found or create and return a new graph
    """

    if graph_type not in GRAPH_TYPE:
        raise Exception(f"Unknown Graph Type {list(GRAPH_TYPE.keys())}")

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
            and og.get_graph_settings(x).evaluator_type == GRAPH_TYPE[graph_type]
        ),
        None,
    )

    if not graph:
        free_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{graph_type}", False)
        # create time node on a brand new graph which force create the graph as well
        graph, nodes, _, _ = og.Controller.edit({"graph_path": free_path, "evaluator_name": GRAPH_TYPE[graph_type]}, {})

    return graph


def create_graph(graph_type: str = "LazyGraph", name: str = None):
    """Create a graph and return the graph path"""
    stage = omni.usd.get_context().get_stage()
    root_path = ""
    dp = stage.GetDefaultPrim()
    if dp:
        root_path = dp.GetPath()

    if not name:
        name = graph_type

    free_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{name}_{graph_type}", False)
    graph, _, _, _ = og.Controller.edit({"graph_path": free_path, "evaluator_name": GRAPH_TYPE[graph_type]}, {})
    return graph


def create_node(node_type, name="", append_type_name=True, graph=None):
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
        graph = get_graph()

    stage = omni.usd.get_context().get_stage()
    if name:
        if append_type_name:
            name = "{}_{}".format(name, node_type.split(".")[-1])
    else:
        name = node_type.split(".")[-1]

    # find resolved name
    free_path = omni.usd.get_stage_next_free_path(stage, "{}/{}".format(graph.get_path_to_graph(), name), False)
    res_name = og.Controller.split_graph_from_node_path(free_path)[1]

    graph, nodes, _, _ = og.Controller.edit(graph, {og.Controller.Keys.CREATE_NODES: (res_name, node_type)})
    return nodes[0]


def create_mesh_points_graph(obj, time_code):
    """
    Sets up graph and graph nodes for getting skel mesh points

    Args:
        obj: Path or Sdf path or Usd Prim.
        time_code: Time to get the data.

    Returns:
        Mesh data omni graph and graph node
    """
    prim = get_prim(obj)
    mesh_data_node = None
    original_data = dict()

    mesh_data_node = get_prim_io(prim, "omni.graph.ImportUSDPrim", input_attr="inputs:prim", force=False)
    if mesh_data_node:
        for attr_name in [
            "inputs:applySkelBinding",
            "inputs:keepPrimsSeparate",
            "inputs:usdTimecode",
            "inputs:attrNamesToImport",
        ]:
            original_data[attr_name] = og.Controller.prim(mesh_data_node).GetAttribute(attr_name).Get()
    else:
        mesh_data_node = create_node("omni.graph.ImportUSDPrim", name="GetSkelMeshPoints")
        og.Controller.prim(mesh_data_node).GetRelationship("inputs:prim").SetTargets([prim.GetPath().pathString])

    set_mesh_node_data(mesh_data_node, time_code=time_code)

    return mesh_data_node, original_data


def set_mesh_node_data(node, time_code=0, data=None):
    """Set get mesh points node (ImportUSDPrim node) data"""
    attrNamesToImport_val = "points"
    curr_attrNamesToImport_val = og.Controller.prim(node).GetAttribute("inputs:attrNamesToImport").Get()
    if curr_attrNamesToImport_val and attrNamesToImport_val not in curr_attrNamesToImport_val:
        attrNamesToImport_val = f"{curr_attrNamesToImport_val} {attrNamesToImport_val}"

    default_data = {
        "inputs:applySkelBinding": True,
        "inputs:keepPrimsSeparate": False,
        "inputs:usdTimecode": time_code,
        "inputs:attrNamesToImport": attrNamesToImport_val,
    }

    if not data:
        data = default_data

    for attr_name, value in data.items():
        attr = og.Controller.prim(node).GetAttribute(attr_name)
        attr.Set(value)


def get_time_node(graph=None):
    """Return available scene time node or create a new one when none exists.

    Args:
        graph (Optional): Graph object. Default: None

    Returns:
        The time OmniGraph Node.

    """
    if not graph:
        graph = get_graph()

    time_node_path = f"{graph.get_path_to_graph()}/time_node"
    time_node = graph.get_node(time_node_path)
    if not time_node.is_valid():
        graph, nodes, _, _ = og.Controller.edit(
            graph, {og.Controller.Keys.CREATE_NODES: ("time_node", "omni.graph.nodes.ReadTime")}
        )
        time_node = nodes[0]

    return time_node


def get_prim_io(obj, node_type, input_attr="inputs:prim", force=True, graph=None):
    """Find reader node in the graph that points to the particular prim.

    Args:
        obj: Path or Sdf path or Usd Prim.
        node_type: reader node type. Defaults to None.
        input_attr (str, optional): Result postfix name to use if stamp_path is not provided. Defaults to "inputs:prim".
        force (Optional): Create if not found. Default True
        graph (Optional): Graph object. Default: None

    Returns:
        The result readerUsdPrim. or None

    """
    if not graph:
        graph = get_graph()

    if str(obj).startswith(graph.get_path_to_graph()):
        # is part of omnigraph node
        prim_path = str(obj)
    else:
        prim_path = get_prim(obj).GetPrimPath().pathString

    prim_name = prim_path.split("/")[-1]

    for node in graph.get_nodes():
        if node.get_type_name() == node_type:
            node_prim = og.Controller.prim(node)
            targets = node_prim.GetRelationship(input_attr).GetTargets()
            if targets and targets[0].pathString == prim_path:
                # found the node
                return node

    # if reach here, it means the node was not found
    if force:
        node = create_node(node_type, prim_name, graph=graph)
        par_path, bundle_name = prim_path.rsplit("/", 1)
        par_node = graph.get_node(par_path)
        if par_node:
            # is a bundle
            bundle_name = prim_path.split("/")[-1]
            og.Controller.connect(par_node.get_attribute(bundle_name), node.get_attribute(input_attr))
        else:
            # create relationship
            omni.kit.commands.execute(
                "AddRelationshipTargetCommand",
                relationship=og.Controller.prim(node).GetRelationship(input_attr),
                target=prim_path,
            )

        return node
    else:
        return None


def get_xform_attr(obj, graph=None):
    """Find or create _builtin_.xform node under the object

    Args:
        obj: path or Sdf path or Usd Prim
        graph (Optional): Graph object. Default: None

    Returns:
        (OmniGraph Node, Matrix4d Attribute Name) of the object
    """
    xform_node = get_prim_io(obj, "omni.anim.GetXform", input_attr="inputs:prim", graph=graph)

    # connect time
    time_node = get_time_node(graph=graph)
    og.Controller.connect(time_node.get_attribute("outputs:frame"), xform_node.get_attribute("inputs:usdTimecode"))

    return (xform_node, "outputs:transform")


def get_points_attr(obj, graph=None, time_varying=False):
    """Find the node and attribute where the given object's points can be found.

    Get the points attr if no timesample or create points time sample node and
    return the timesample points attribute.

    Args:
        obj: path or Sdf path or Usd Prim
        graph (Optional): Graph object. Default: None
        time_varying (Optional): If True, connects a time node to the read points node

    Returns:
        (OmniGraph Node, Points Attribute Name) where the points for the node can be found
    """
    reader_node = get_prim_io(obj, "omni.graph.nodes.ReadPrimAttribute", input_attr="inputs:prim", graph=graph)
    attr = reader_node.get_attribute("inputs:name")
    og.Controller(attr).set("points", update_usd=True)

    if time_varying:
        time_node = get_time_node(graph=graph)
        time_attr = time_node.get_attribute("outputs:frame")
        og.Controller.connect(time_attr, reader_node.get_attribute("inputs:usdTimecode"))

    return (reader_node, "outputs:value")


def get_current_time_code(stage):
    """Return the current time code

    Args:
        stage: the usd stage

    Returns:
        timecode
    """
    current_time = omni.timeline.get_timeline_interface().get_current_time()
    current_time_code = Usd.TimeCode(current_time * stage.GetTimeCodesPerSecond())
    return current_time_code


def get_xform_input_path(obj, attr_name):
    """
    Return the prim path that is connected to this input of this attribute.

    If it finds the node with inputs:prim, it'll retreive the inputs:prim value.

    Args:
        obj: path or Sdf path or Usd Prim
        attr_name: attribute name of the prim to trace up the input

    Returns:
        The path
    """
    prim = get_prim(obj)
    result = None

    attr = prim.GetAttribute(attr_name)
    rel = prim.GetRelationship(attr_name)

    # given attr_name is an attribute
    if attr:
        input_path = attr.GetConnections()[0]
        input_prim = input_path.pathString.rsplit(".", 1)[0]
        result = get_inputs_prim_value(input_prim)

    # given attr_name is a relationship
    elif rel:
        targets = rel.GetTargets()
        if targets:
            if is_xform(targets[0]):
                result = targets[0]
            else:
                result = get_inputs_prim_value(targets[0])

    # check if result was found and is xformable
    if result:
        result_p = get_prim(result)
        if is_xform(result_p):
            return result_p.GetPath().pathString

    else:
        carb.log_warn(f"Could not get xform path for {obj}")
        return


def is_xform(obj):
    prim = get_prim(obj)
    return prim.IsA(UsdGeom.Xformable)


def get_inputs_prim_value(obj):
    """
    If given obj has an attribute or a relationsip called inputs:prim,
    this will return the value of that attr connection or relationship

    Args:
        obj: path or Sdf path or Usd Prim

    Returns:
        The value of inputs:prim as pxr.Sdf.Path
    """
    prim = get_prim(obj)

    # given obj has inputs:prim relationship, eg: ReadPrim
    rel = prim.GetRelationship("inputs:prim")
    if rel:
        targets = rel.GetTargets()
        if targets:
            return targets[0]

    # given obj is an output, check its parent, eg: readPrim.outputs_output
    elif prim.GetTypeName() == "Output":
        return get_inputs_prim_value(prim.GetParent())

    else:
        carb.log_warn(f"Could not get inputs:prim value for {obj}")
        return


def list_children(obj):
    """
    To list all children

    obj : Sdf path or Usd Prim
    """

    def get_all_descendents(prim, output=[]):
        prim_children = prim.GetChildren()
        if prim_children:
            for child in prim_children:
                output.append(child)
                get_all_descendents(child, output)
        return output

    prim = get_prim(obj)
    output = []
    if prim:
        return get_all_descendents(prim, output)
    return output


def stampXformTool(obj, stamp_path=None, postfix="stamp"):
    """Create a clean copy of the selected Xform at its current state.

    obj : path or Sdf path or Usd Prim

    Returns:
        created Xform path

    """
    stage = omni.usd.get_context().get_stage()
    prim = get_prim(obj)

    if not stamp_path:
        stamp_path = omni.usd.get_stage_next_free_path(stage, f"{prim.GetPath()}_{postfix}", False)

    current_time = omni.timeline.get_timeline_interface().get_current_time()
    current_time_code = Usd.TimeCode(current_time * stage.GetTimeCodesPerSecond())

    omni.kit.commands.execute(
        "CreatePrimCommand",
        prim_path=stamp_path,
        prim_type=prim.GetTypeName(),
        select_new_prim=False,
        attributes={},
        create_default_xform=False,
    )
    out_prim = stage.GetPrimAtPath(stamp_path)

    copyXform(prim, out_prim, current_time_code)

    return stamp_path


class CurveData(object):
    """Curve data container."""

    def __init__(
        self,
        points=[],
        primvars=OrderedDict(),
        basis="bezier",
        type="cubic",
        curveVertexCounts=[],
        widths=[],
        wrap="nonperiodic",
    ):
        super().__init__()
        self.points = points
        self.primvars = primvars
        self.basis = basis
        self.type = type
        self.curveVertexCounts = curveVertexCounts
        self.widths = widths
        self.wrap = wrap


def get_curve_data(obj, time_code):
    prim = get_prim(obj)
    if prim.GetTypeName() != "BasisCurves":
        carb.log_error(f"Invalid object type: {type(obj)}")
        return None

    curve_data = CurveData()
    curve_data.points = prim.GetAttribute("points").Get(time_code)
    curve_data.basis = prim.GetAttribute("basis").Get(time_code)
    curve_data.type = prim.GetAttribute("type").Get(time_code)
    curve_data.curveVertexCounts = prim.GetAttribute("curveVertexCounts").Get(time_code)
    curve_data.widths = prim.GetAttribute("widths").Get(time_code)
    curve_data.wrap = prim.GetAttribute("wrap").Get(time_code)

    # primvars that have been modified
    primvars = [
        "primvars:doNotCastShadows",
        "primvars:enableShadowTerminatorFix",
        "primvars:enableFastRefractionShadow",
        "primvars:disableRtSssTransmission",
        "primvars:holdoutObject",
        "primvars:invisibleToSecondaryRays",
        "primvars:isMatteObject",
        "primvars:multimatte_id",
    ]
    for at in primvars:
        if prim.HasProperty(at):
            _prpt = prim.GetProperty(at)
            curve_data.primvars[at] = {"typeName": _prpt.GetTypeName(), "value": _prpt.Get()}

    return curve_data


def create_curve(path=None, curve_data: MeshData = None):
    """Main command for creating curves with any arbitrary input data"""

    # convert mesh_data to dict
    curve_data_as_dict = vars(curve_data)

    # primvars can not be added using CreatePrim command, extract them so we can apply them later
    primvars = curve_data_as_dict.pop("primvars", OrderedDict())

    # create curve from given mesh data dict
    omni.kit.commands.execute(
        "CreatePrim", prim_path=path, prim_type="BasisCurves", attributes=curve_data_as_dict, select_new_prim=True
    )

    # get prim of newly created curve
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(path)

    # apply primvars
    for at in primvars:
        at_type = primvars[at]["typeName"]
        at_value = primvars[at]["value"]
        prim.CreateAttribute(at, at_type).Set(at_value)

    # return
    curve = UsdGeom.BasisCurves(prim)
    return curve
