from typing import Any

import AnimationSchema
import carb
import numpy as np
import omni.graph.core as og
import omni.timeline
import omni.usd
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt

from .curve_settings import (
    get_default_post_infinity_type,
    get_default_pre_infinity_type,
    get_default_tangent_broken,
    get_default_tangent_type,
    get_default_tangent_weighted,
)
from .keySelection import *
from .preserve_shape_utils import bezier_subdivision

FLOAT_TYPE = [Sdf.ValueTypeNames.Double, Sdf.ValueTypeNames.Float, Sdf.ValueTypeNames.Half]
FLOAT_TWO_TYPE = [Sdf.ValueTypeNames.Double2, Sdf.ValueTypeNames.Float2, Sdf.ValueTypeNames.Half2]
FLOAT_THREE_TYPE = [
    Sdf.ValueTypeNames.Double3,
    Sdf.ValueTypeNames.Float3,
    Sdf.ValueTypeNames.Half3,
    Sdf.ValueTypeNames.Point3d,
    Sdf.ValueTypeNames.Point3f,
    Sdf.ValueTypeNames.Point3h,
    Sdf.ValueTypeNames.Normal3d,
    Sdf.ValueTypeNames.Normal3f,
    Sdf.ValueTypeNames.Normal3h,
    Sdf.ValueTypeNames.Vector3d,
    Sdf.ValueTypeNames.Vector3f,
    Sdf.ValueTypeNames.Vector3h,
    Sdf.ValueTypeNames.Color3d,
    Sdf.ValueTypeNames.Color3f,
    Sdf.ValueTypeNames.Color3h,
]
FLOAT_FOUR_TYPE = [
    Sdf.ValueTypeNames.Double4,
    Sdf.ValueTypeNames.Float4,
    Sdf.ValueTypeNames.Half4,
    Sdf.ValueTypeNames.Color4h,
    Sdf.ValueTypeNames.Color4f,
    Sdf.ValueTypeNames.Color4d,
]

INT_TYPE = [Sdf.ValueTypeNames.Int, Sdf.ValueTypeNames.UInt, Sdf.ValueTypeNames.Int64, Sdf.ValueTypeNames.UInt64]
INT_TWO_TYPE = [Sdf.ValueTypeNames.Int2]
INT_THREE_TYPE = [Sdf.ValueTypeNames.Int3]
INT_FOUR_TYPE = [Sdf.ValueTypeNames.Int4]

BOOL_TYPE = [Sdf.ValueTypeNames.Bool]

TOKEN_TYPE = [Sdf.ValueTypeNames.Token]

VALUE_VEC_TYPE = [
    Gf.Vec2d,
    Gf.Vec3d,
    Gf.Vec4d,
    Gf.Vec2f,
    Gf.Vec3f,
    Gf.Vec4f,
    Gf.Vec2h,
    Gf.Vec3h,
    Gf.Vec4h,
    Gf.Vec2i,
    Gf.Vec3i,
    Gf.Vec4i,
]

curve_plugin = None


def get_curve_plugin():
    return curve_plugin


def key_time_to_time_code(key_time):
    tcps = omni.usd.get_context().get_stage().GetTimeCodesPerSecond()
    return (key_time * tcps) / curve_plugin.get_ticks_per_second()


def get_ticks_per_second():
    return curve_plugin.get_ticks_per_second()


# copy:  src -> clipboard
# paste: clipboard -> dst
# it is a share clipboard used in property window, timeline and curve editor.
# it is standalone, so can copy from a stage then switch to another stage then paste.
# Clipboard can store (key_data, timecode) of multiply prims, curves
class CurveKeyClipboard:
    def __init__(self):
        self._prim_paths = {}
        self._timecode = None

    def get_prim_count(self):
        return len(self._prim_paths)

    def get_curve_count(self, prim_index: int = 0):
        if prim_index < self.get_prim_count():
            return len(self.get_prim_curves(prim_index))
        else:
            return 0

    def get_prim_curves(self, prim_index: int = 0) -> list:
        # since 3.7 python dict preserves order of insert sequence
        return list(self._prim_paths.values())[prim_index]

    def get_curve_keys(self, prim_index: int = 0, curve_index: int = 0) -> list:
        curves = self.get_prim_curves(prim_index)
        if curves is None:
            return None
        if curve_index < len(curves):
            return list(curves.values())[curve_index]
        else:
            return None

    def get_curve_name(self, prim_index: int = 0, curve_index: int = 0) -> str:
        curves = self.get_prim_curves(prim_index)
        if curves is None:
            return None
        if curve_index < len(curves):
            return list(curves.keys())[curve_index]
        else:
            return None

    def get_prim_name(self, prim_index: int = 0) -> str:
        if self._prim_paths == None or prim_index >= len(self._prim_paths):
            return None
        else:
            return list(self._prim_paths.keys())[prim_index]

    @property
    def timecode(self):
        return self._timecode

    @timecode.setter
    def timecode(self, timecode: float):
        self._timecode = timecode

    def add_key(self, prim_path: str, curve_name: str, key_datas: list):
        if prim_path is None or len(prim_path) == 0:
            return False
        if curve_name is None or len(curve_name) == 0:
            return False
        if not isinstance(key_datas, list) or len(key_datas) == 0:
            return False

        if prim_path not in self._prim_paths:
            self._prim_paths[prim_path] = {}

        curves = self._prim_paths[prim_path]

        if curve_name not in curves:
            curves[curve_name] = []

        curve_keys = curves[curve_name]
        curve_keys.extend(key_datas)

    def clear(self):
        self._prim_paths.clear()
        self._timecode = None

    # Sort all keys in the clipboard in time order and optionally set the earliest time to the self._timecode
    def sort_keys(self, set_time_code: bool = True):
        if set_time_code:
            self._timecode = None
        for prim_path, prim_curves in self._prim_paths.items():
            for curve_name, curve_keys in prim_curves.items():
                curve_keys.sort(key=lambda keyframe: keyframe.time)
                prim_curves[curve_name] = curve_keys
                if set_time_code:
                    smallest_time_code = key_time_to_time_code(curve_keys[0].time)
                    if self._timecode == None:
                        self._timecode = smallest_time_code
                    elif self._timecode >= smallest_time_code:
                        self._timecode = smallest_time_code
            self._prim_paths[prim_path] = prim_curves


global curvekey_clipboard_data
curvekey_clipboard_data = CurveKeyClipboard()


def get_curvekey_clipboard():
    return curvekey_clipboard_data


# only used in ext shutdown
def shutdown_curvekey_clipboard():
    global curvekey_clipboard_data
    curvekey_clipboard_data = None


# copy all keys from time to time+time_range in paths
# if time is None it means copy all the keys for the specified curves
def set_curvekey_clipboard(
    stage: Usd.Stage = None,
    paths: list = None,
    time: Usd.TimeCode = None,
    time_range: float = 0,
):
    context = omni.usd.get_context()
    if not context:
        carb.log_warn("set_curvekey_clipboard: usd context is None!")
        return False

    if stage is None:
        stage = context.get_stage()

    if paths is None:
        paths = []
        selection = context.get_selection()
        if selection:
            paths = selection.get_selected_prim_paths()

    if not sanity_checks(stage, paths, "set_curvekey_clipboard"):
        return False

    if time is None or time == Usd.TimeCode.Default():
        key_time = None
    else:
        key_time = time.GetValue()

    clipboard = get_curvekey_clipboard()
    clipboard.clear()
    clipboard.timecode = key_time

    for path in paths:
        # prase path
        prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = parse_path(stage, path)
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            continue

        # Get AnimationData prims(usually just the 1st prim)
        curve_prims = get_curve_prims(prim)
        if curve_prims is None or len(curve_prims) == 0:
            continue
        curve_api = AnimationSchema.AnimationCurveAPI(curve_prims[0])

        # get curve_names
        curve_names = []
        if is_prim_path:
            # e.g. /World/Cube  Move all of its keys
            if has_anim(prim):
                curve_names = get_curves(prim)
        elif is_comp_path:
            # e.g. /World/Cube.xformOp:translate|x or /World/Cube.size|x
            # move specific keys
            curve_names.append(gen_comp_attr_token(attr_token, comp_idx))
        else:
            # /World/Cube.xformOp:translate or /World/Cube.size
            for index in range(comp_length):
                curve_names.append(gen_comp_attr_token(attr_token, index))

        # get key data in each curve
        for curve_name in curve_names:
            key_datas = []
            keys = curve_api.GetKeys(curve_name)
            if keys is None:
                continue
            if key_time is not None:
                ticks_begin = key_time / stage.GetTimeCodesPerSecond() * curve_plugin.get_ticks_per_second()
                ticks_end = (
                    (key_time + time_range) / stage.GetTimeCodesPerSecond() * curve_plugin.get_ticks_per_second()
                )
                for key in keys:
                    if key.time <= ticks_end and key.time >= ticks_begin:
                        key_datas.append(key)
            else:
                for key in keys:
                    key_datas.append(key)
            clipboard.add_key(prim_path.pathString, curve_name, key_datas)

    return True


def sanity_checks(stage, paths: list, name: str = ""):
    if stage is None:
        carb.log_error(f"{name}: stage is None!")
        return False

    if not isinstance(paths, list):
        carb.log_error(f"{name}: the paths input must be a type of python list")
        return False

    if paths == []:
        carb.log_warn(f"{name}: no path input")
        return False

    for path in paths:
        if type(path) != str:
            carb.log_error(f"{name}: one of the path {path} is {type(path)}, not a string type")
            return False

    return True


def get_attr_token(path: str):
    attr_path = Sdf.Path(path[:-2])
    if attr_path.IsPrimPropertyPath():
        return attr_path.GetPrimPath(), attr_path, attr_path.name
    else:
        return None, None, None


# Get the animationData prim from the prim
def get_animation_prim_path(prim):
    curve_prims = get_curve_prims(prim)
    if curve_prims:
        return curve_prims[0].GetPath()
    else:
        return Sdf.Path()


def gen_comp_attr_token(attr_token, comp_idx: int, name: str = ""):
    comp_attr_token = attr_token
    if comp_idx == 0:
        comp_attr_token += ":x"
    elif comp_idx == 1:
        comp_attr_token += ":y"
    elif comp_idx == 2:
        comp_attr_token += ":z"
    elif comp_idx == 3:
        comp_attr_token += ":w"
    else:
        carb.log_error(f"{name}: Input Parameter Error component index greater than 4 out of range!")
    return comp_attr_token


def gen_comp_attr_path(attr_path, comp_idx: int, name: str = ""):
    comp_attr_path = attr_path
    if comp_idx == 0:
        comp_attr_path += "|x"
    elif comp_idx == 1:
        comp_attr_path += "|y"
    elif comp_idx == 2:
        comp_attr_path += "|z"
    elif comp_idx == 3:
        comp_attr_path += "|w"
    else:
        carb.log_error(f"{name}: Input Parameter Error component index greater than 4 out of range!")
    return comp_attr_path


def parse_path(stage: Usd.Stage, path: str, name: str = ""):
    if not stage:
        return None

    is_comp_path = False
    is_prim_path = False
    prim_path = None
    attr_token = None
    comp_len = 0
    comp_idx = 0

    _attr_path = None
    # We'd not rely on Sdf.Path to determin illegal SdfPath .e.g /World/Cube.xformOp:translate|x
    if not path.endswith("|x") and not path.endswith("|y") and not path.endswith("|z") and not path.endswith("|w"):
        is_comp_path = False
    else:
        is_comp_path = True
    # Check if it is a prim path
    if not is_comp_path:
        if Sdf.Path(path).IsPrimPath():
            is_prim_path = True
            prim_path = Sdf.Path(path)
    # parse the attribute path
    if not is_prim_path:
        if path.endswith("|x"):
            prim_path, _attr_path, attr_token = get_attr_token(path)
            is_comp_path = True
            comp_idx = 0
        elif path.endswith("|y"):
            prim_path, _attr_path, attr_token = get_attr_token(path)
            is_comp_path = True
            comp_idx = 1
        elif path.endswith("|z"):
            prim_path, _attr_path, attr_token = get_attr_token(path)
            is_comp_path = True
            comp_idx = 2
        elif path.endswith("|w"):
            prim_path, _attr_path, attr_token = get_attr_token(path)
            is_comp_path = True
            comp_idx = 3
        elif Sdf.Path(path).IsPrimPropertyPath():
            sdf_path = Sdf.Path(path)
            prim_path = sdf_path.GetPrimPath()
            _attr_path = sdf_path
            attr_token = sdf_path.name
        else:
            carb.log_error(
                f"{name}: Attribute Path {path} is not a prim path nor a legal attribute nor an attribute component path!"
            )

        attr = stage.GetAttributeAtPath(_attr_path)
        if attr:
            attr_value_type = attr.GetTypeName()
            if attr_value_type in FLOAT_TYPE + INT_TYPE + BOOL_TYPE + TOKEN_TYPE:
                comp_len = 1
            elif attr_value_type in FLOAT_TWO_TYPE + INT_TWO_TYPE:
                comp_len = 2
            elif attr_value_type in FLOAT_THREE_TYPE + INT_THREE_TYPE:
                comp_len = 3
            elif attr_value_type in FLOAT_FOUR_TYPE + INT_FOUR_TYPE:
                comp_len = 4
            else:
                carb.log_error(f"{name}: {path}'s Attribute Type Error!")
        else:
            carb.log_error(f"{name}: {path}'s Attribute {_attr_path} is illegal!")
    return prim_path, attr_token, comp_len, comp_idx, is_prim_path, is_comp_path


def get_curves(prim):
    curves = curve_plugin.get_curves(str(prim.GetPath()))
    if curves:
        return list(curves.keys())
    else:
        return None


def has_anim(prim):
    prim_paths = curve_plugin.get_curve_prims(str(prim.GetPath()))
    if not prim_paths:
        return False

    return bool(prim.GetStage().GetPrimAtPath(prim_paths[0]))


def add_anim(prim):
    # Use existing curve node
    curve_prim_paths = curve_plugin.get_curve_prims(str(prim.GetPath()))
    if curve_prim_paths:
        return curve_prim_paths[0]

    # Find or create the graph
    stage = prim.GetStage()
    src_to_tgt_map = stage.GetEditTarget().GetMapFunction().sourceToTargetMap
    graph_path = list(src_to_tgt_map.values())[0].AppendChild("PushGraph").pathString
    graph_path = omni.usd.get_stage_next_free_path(stage, graph_path, True)
    for child_prim in stage.GetPrimAtPath(Sdf.Path(graph_path).GetParentPath()).GetChildren():
        graph = og.get_graph_by_path(str(child_prim.GetPath()))
        if graph is None:
            continue

        if graph.get_evaluator_name() == "push":
            graph_path = str(child_prim.GetPath())

    curve_node_path = omni.usd.get_stage_next_free_path(stage, graph_path + "/" + prim.GetName() + "CurveNode", True)
    graph, nodes, _, _ = og.Controller.edit(
        graph_path, {og.Controller.Keys.CREATE_NODES: [(curve_node_path, "omni.anim.curve.core.AnimCurve")]}
    )

    # Create curve node
    curve_node = nodes[0]
    curve_node_prim = og.Controller.prim(curve_node)

    curve_node_prim.GetRelationship("inputs:Prim").SetTargets([prim.GetPath()])

    return curve_node_path


def get_curve_prims(prim):
    curve_prims = []
    curve_prim_paths = curve_plugin.get_curve_prims(str(prim.GetPath()))
    for path in curve_prim_paths:
        curve_prim = prim.GetStage().GetPrimAtPath(path)
        if curve_prim:
            curve_prims.append(curve_prim)
    return curve_prims


def del_curves(prim, curve_names):
    for curve_prim in get_curve_prims(prim):
        for curve_name in curve_names:
            AnimationSchema.AnimationCurveAPI(curve_prim).DeleteCurve(curve_name)


def _parse_attr_token(prim, curve_path: str):
    if AnimationSchema.AnimationData(prim):
        return [curve_path]

    if "|" in curve_path:
        return [curve_path.replace("|", ":")]

    comp_list = ["x", "y", "z", "w"]

    attr = prim.GetAttribute(curve_path)
    if not attr:  # If it's an attribute name
        return []

    if not curve_plugin.is_attr_supported(str(attr.GetPath())):
        return []

    dimension = 1
    value_type = attr.GetTypeName().type.pythonClass
    if hasattr(value_type, "__isGfVec"):
        dimension = value_type.dimension

    curve_names = []
    for i in range(dimension):
        curve_names.append(str(attr.GetName()) + ":" + comp_list[i])
    return curve_names


def add_curve(prim, curve_name):
    curve_prims = get_curve_prims(prim)
    curve_prim = curve_prims[0]

    curve_api = AnimationSchema.AnimationCurveAPI(curve_prim)
    existing_curves = curve_api.GetCurves()
    if curve_name in existing_curves:
        return True

    if curve_api.SetKeys(curve_name, []):
        curve_api.SetDefaultTangentType(curve_name, get_default_tangent_type())
        curve_api.SetInfinityType(curve_name, get_default_pre_infinity_type(), AnimationSchema.Infinity.Pre)
        curve_api.SetInfinityType(curve_name, get_default_post_infinity_type(), AnimationSchema.Infinity.Post)
        return True
    else:
        return False


def add_curves(prim: Usd.Prim, curve_path: str = None):
    all_ok = True

    # Add curves to prim
    if curve_path is None:
        imageable = UsdGeom.Imageable(prim)
        if imageable:
            ok = add_curves(prim, str(UsdGeom.Tokens.visibility))
            all_ok = all_ok and ok

        xformable = UsdGeom.Xformable(prim)
        if xformable:
            for attr in prim.GetAttributes():
                if attr.GetNamespace() == "xformOp":
                    ok = add_curves(prim, attr.GetName())
                    all_ok = all_ok and ok

        return all_ok

    # Add curves to attribute
    if "|" not in curve_path:
        comp_list = ["x", "y", "z", "w"]

        attr = prim.GetAttribute(curve_path)
        if not attr:
            return False

        if not curve_plugin.is_attr_supported(str(attr.GetPath())):
            return False

        dimension = 1
        value_type = attr.GetTypeName().type.pythonClass
        if hasattr(value_type, "__isGfVec"):
            dimension = value_type.dimension

        comps = []
        for i in range(dimension):
            ok = add_curve(prim, curve_path + ":" + comp_list[i])
            all_ok = all_ok and ok

        return all_ok

    # Add curve to component
    curve_name = curve_path.replace("|", ":")
    ok = add_curve(prim, curve_name)
    all_ok = all_ok and ok

    return all_ok


def add_curve_and_anim(stage, prim, prim_path: str, curve_path: str):
    if not has_anim(prim):
        add_anim(prim)
    add_curves(prim, curve_path)


def convert_to_usd_keys(keys):
    usd_keys = []
    for key in keys:
        usd_key = AnimationSchema.Key()
        usd_key.time = key.time
        usd_key.value = key.value
        usd_key.inTangent.time = key.inTangent.time
        usd_key.inTangent.value = key.inTangent.value
        usd_key.inTangent.type = key.inTangent.type
        usd_key.outTangent.time = key.outTangent.time
        usd_key.outTangent.value = key.outTangent.value
        usd_key.outTangent.type = key.outTangent.type
        usd_key.tangentBroken = key.tangentBroken
        usd_key.tangentWeighted = key.tangentWeighted
        usd_keys.append(usd_key)

    return usd_keys


def add_keys(prim, src_time, time, in_tan_type=None, out_tan_type=None, broken=None, preserve_shape=True):
    curves = get_curves(prim)
    if not curves:
        return

    for curve_name in curves:
        attr = prim.GetAttribute(curve_name[:-2])
        value = attr.Get(src_time)
        add_key(prim, attr.GetName(), time, value, in_tan_type, out_tan_type, broken, preserve_shape)


def get_curve_api(prim):
    if AnimationSchema.AnimationData(prim):
        return AnimationSchema.AnimationCurveAPI(prim)
    else:
        return AnimationSchema.AnimationCurveAPI.Get(prim.GetStage(), get_animation_prim_path(prim))


def get_keys(prim, curve_name):
    curve_api = None
    if AnimationSchema.AnimationData(prim):
        curve_api = AnimationSchema.AnimationCurveAPI(prim)
    else:
        curve_api = AnimationSchema.AnimationCurveAPI.Get(prim.GetStage(), get_animation_prim_path(prim))

    if not curve_api:
        return None

    return curve_api.GetKeys(curve_name)


def set_keys(prim, curve_name, keys):
    curve_api = get_curve_api(prim)

    if not curve_api:
        return False

    existing_keys = curve_api.GetKeys(curve_name)

    keys = convert_to_usd_keys(keys)

    new_keys_times = list(key.time for key in keys)
    for existing_key in existing_keys:
        if existing_key.time not in new_keys_times:
            keys.append(existing_key)  # Add the existing key to the new `keys`
        # Else: The old key will be overwritten by the new key. Do not add the old key.

    keys.sort(key=lambda key: key.time)

    curve_api.SetKeys(curve_name, keys)


def set_keys_direct(prim, curve_name, keys):
    curve_api = get_curve_api(prim)

    if not curve_api:
        return

    keys.sort(key=lambda key: key.time)

    curve_api.SetKeys(curve_name, keys)


def delete_key(prim, curve_name, time_code, delete_empty_curve):
    curves = curve_plugin.get_curves(str(prim.GetPath()))
    if curve_name not in curves.keys():
        return False

    time = round(time_code / prim.GetStage().GetTimeCodesPerSecond() * curve_plugin.get_ticks_per_second())

    keys = []
    curve = curves[curve_name]
    for key in curve.keys:
        if key.time != time:
            keys.append(key)

    if len(keys) == len(curve.keys):
        return False

    KeySelectionState.on_keys_changed(str(prim.GetPath().AppendProperty(curve_name)), [], [time])
    KeySelectionState.ignore_curve_event = True

    curve_api = AnimationSchema.AnimationCurveAPI.Get(prim.GetStage(), curve.anim_data)
    ret = curve_api.SetKeys(curve_name, convert_to_usd_keys(keys))

    if delete_empty_curve and len(keys) == 0:
        curve_api.DeleteCurve(curve_name)

    KeySelectionState.ignore_curve_event = False

    return ret


def time_code_to_key_time(prim, time_code):
    return round(time_code * curve_plugin.get_ticks_per_second() / prim.GetStage().GetTimeCodesPerSecond())


# this code is not used, ignore from the test for now
def move_key(prim, curve_name, src_time_code, dest_time_code):  # pragma: no cover
    curves = curve_plugin.get_curves(str(prim.GetPath()))

    curve = curves.get(curve_name)
    if curve is None:
        return False

    src_time = time_code_to_key_time(prim, src_time_code)
    dest_time = time_code_to_key_time(prim, dest_time_code)

    usd_keys = convert_to_usd_keys(curve.keys)
    for key in usd_keys:
        if key.time == src_time:
            key.time = dest_time
            break

    usd_keys.sort(key=lambda key: key.time)
    return AnimationSchema.AnimationCurveAPI.Get(prim.GetStage(), curve.anim_data).SetKeys(curve_name, usd_keys)


def add_key(
    prim, curve_path, time_code, attr_value, in_tan_type=None, out_tan_type=None, broken=None, preserve_shape=True
):

    assert preserve_shape == False or (preserve_shape and in_tan_type is None and out_tan_type is None)
    curve_names = _parse_attr_token(prim, curve_path)
    if not curve_names:
        return

    key_time = round(time_code / prim.GetStage().GetTimeCodesPerSecond() * curve_plugin.get_ticks_per_second())

    if isinstance(attr_value, str):
        allowed_tokens = prim.GetAttribute(curve_names[0][:-2]).GetMetadata("allowedTokens")
        if allowed_tokens is None:
            return

        if attr_value not in allowed_tokens:
            return

        attr_value = list(allowed_tokens).index(attr_value)
        if out_tan_type is None:
            out_tan_type = "step"  # outTanType should be step by default for tokens

    if broken == None:
        broken = get_default_tangent_broken()

    weighted = get_default_tangent_weighted()

    curve_api = get_curve_api(prim)
    if not curve_api:
        return

    curves = curve_plugin.get_curves(str(prim.GetPath()))
    for curve_name in curve_names:
        if curve_name not in curves.keys():
            continue

        new_key = AnimationSchema.Key()
        new_key.time = key_time

        if hasattr(attr_value, "__getitem__"):
            indices = [3, 0, 1, 2]
            comp_index = indices[ord(curve_name[-1]) - ord("w")]
            new_key.value = attr_value[comp_index]
        else:
            new_key.value = attr_value

        default_tangent_type = curve_api.GetDefaultTangentType(curve_name)
        if default_tangent_type == "":
            default_tangent_type = "auto"
        curve_in_tangent_type = default_tangent_type if in_tan_type is None else in_tan_type
        curve_out_tangent_type = default_tangent_type if out_tan_type is None else out_tan_type
        if curve_in_tangent_type == "step":
            # inTangentType can not be "step"
            curve_in_tangent_type = "auto"

        if curve_out_tangent_type == "step" or preserve_shape == False:
            new_key.inTangent.type = curve_in_tangent_type
            new_key.outTangent.type = curve_out_tangent_type
            new_key.tangentBroken = broken
            new_key.tangentWeighted = weighted
            new_keys = [new_key]
        else:
            # Preserve Shape Main Logic Here: out_tangent_type != step and preserve_shape==True
            existing_keys = curve_api.GetKeys(curve_name)
            existing_keys_dict = {key.time: key for key in existing_keys}
            existing_key_times = list(existing_keys_dict.keys())
            new_key = convert_to_usd_keys([new_key])[0]
            new_key.inTangent.type = curve_in_tangent_type
            new_key.outTangent.type = curve_out_tangent_type
            new_key.tangentBroken = broken
            new_key.tangentWeighted = weighted

            overriden = False
            if new_key.time in existing_key_times:
                carb.log_info("Setting an existing key with `preserve_shape=True`. Will not do anything.")
                continue

            existing_keys.append(new_key)
            existing_keys.sort(key=lambda key: key.time)
            existing_key_times = list(key.time for key in existing_keys)

            new_key_idx = existing_key_times.index(new_key.time)
            if overriden or new_key.time == existing_key_times[0] or new_key.time == existing_key_times[-1]:
                # carb.log_info('The new key is either the first key or the last key. Will ignore `preserve_shape` option.')
                new_keys = [new_key]
            else:
                prev_key = existing_keys[new_key_idx - 1]
                next_key = existing_keys[new_key_idx + 1]

                if prev_key.outTangent.type == "step":
                    # keep new_key.inTangent.type, change new_key.outTangent.type
                    new_key.outTangent.type = "step"
                    new_keys = [new_key]

                elif prev_key.outTangent.type == next_key.inTangent.type == "linear":
                    new_key.inTangent.type = "linear"
                    new_key.outTangent.type = "linear"
                    new_keys = [new_key]

                else:
                    # main logic
                    P0 = np.array((prev_key.time, prev_key.value))
                    P1 = P0 + np.array((prev_key.outTangent.time, prev_key.outTangent.value))
                    P3 = np.array((next_key.time, next_key.value))
                    P2 = P3 + np.array((next_key.inTangent.time, next_key.inTangent.value))

                    bezier_subdivision(P0, P1, P2, P3, prev_key, new_key, next_key)

                    new_keys = [prev_key, new_key, next_key]

        set_keys(prim, curve_name, new_keys)


DefaultAnimationKey = AnimationSchema.Key()


class TangentSideData:
    def __init__(
        self,
        time: float = DefaultAnimationKey.inTangent.time,
        value: float = DefaultAnimationKey.inTangent.value,
        type="auto",
    ):
        self.time = time
        self.value = value
        self.type = type


class TangentData:
    def __init__(
        self,
        inTangent: TangentSideData = None,
        outTangent: TangentSideData = None,
        tangentBroken: bool = DefaultAnimationKey.tangentBroken,
        tangentWeighted: bool = DefaultAnimationKey.tangentWeighted,
    ):
        self.inTangent = inTangent
        self.outTangent = outTangent
        self.tangentBroken = tangentBroken
        self.tangentWeighted = tangentWeighted


def set_tangent(prim, anim_key: AnimationSchema.Key(), tangent: TangentData):
    if tangent is None:  # not computed
        return
    inTime = time_code_to_key_time(prim, tangent.inTangent.time)
    outTime = time_code_to_key_time(prim, tangent.outTangent.time)
    anim_key.inTangent.time = inTime
    anim_key.inTangent.value = tangent.inTangent.value
    anim_key.inTangent.type = tangent.inTangent.type
    anim_key.outTangent.time = outTime
    anim_key.outTangent.value = tangent.outTangent.value
    anim_key.outTangent.type = tangent.outTangent.type
    anim_key.tangentBroken = tangent.tangentBroken
    anim_key.tangentWeighted = tangent.tangentWeighted


# This is for timesample to animation curve data conversion method.
def resample_times(
    frame_indices: list, source_frame_rate: float, target_frame_rate: float, target_start_time: float = 0
) -> list:
    if source_frame_rate == 0:
        return [(t, t) for t in frame_indices]

    assert target_frame_rate != 0.0

    Epsilon = 0.000001

    frame_indices.sort()
    source_dt = 1.0 / source_frame_rate
    target_dt = 1.0 / target_frame_rate

    source_start_time = frame_indices[0] * source_dt
    source_end_time = frame_indices[-1] * source_dt

    sampling_start_frame = source_start_time / target_dt
    sampling_start_time = int(sampling_start_frame) * target_dt  # NOTE: avoided modulo due to numerical problems
    # make sure sampling starts after we have samples
    if sampling_start_time + Epsilon < source_start_time:
        sampling_start_time += target_dt

    target_frame_offset = round(target_start_time / target_dt)

    new_frames = []
    t = sampling_start_time
    while t <= source_end_time:
        t_sample = t / source_dt
        target_frame_index = float(round(t / target_dt))
        new_frames.append((t_sample, target_frame_index + target_frame_offset))
        t += target_dt

    return new_frames
