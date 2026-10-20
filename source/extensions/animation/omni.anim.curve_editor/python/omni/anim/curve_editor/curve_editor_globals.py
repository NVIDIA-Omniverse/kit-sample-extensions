from enum import IntEnum

import carb
import omni.anim.curve.core
from pxr import Sdf

SHOW_MORE_LOG_WARN = False  # for developer debugging only
EDITOR_CONTROL_HANDLE_SMALL_LENGTH = 0.001
EDITOR_CONTROL_HANDLE_FIXED_LENGTH = 50
GUIDELINE_COLOR = 0x20FFFFFF

CURVE_PRIM_TYPE = "AnimationData"
# "token" is supported. It is taken as some kind of enumeration by the curve runtime.
UNSUPPORTED_CURVE_ATTR_USER_SCALAR_TYPES = {
    "timecode",
    "string",
    "asset",
    "matrix2d",
    "matrix3d",
    "matrix4d",
    "quatd",
    "quatf",
    "quath",
    "frame4d",
}

s_tokenAnimationDataBinding = "animationData:binding"
curve_plugin = omni.anim.curve.core.acquire_interface()


# a simple wrapper for the interpolation types.
class CurveInterpolation:
    TangentTypeTokens = ["auto", "smooth", "flat", "fixed", "linear", "step"]

    class TangentType(IntEnum):
        Automatic = 0
        Smooth = 1
        Flat = 2
        Fixed = 3
        Linear = 4
        Step = 5

        @staticmethod
        def get(tangent_type_token: str):
            if tangent_type_token in CurveInterpolation.TangentTypeTokens:
                index = CurveInterpolation.TangentType(CurveInterpolation.TangentTypeTokens.index(tangent_type_token))
            else:
                index = CurveInterpolation.TangentType.Automatic

            return index

        @staticmethod
        def to_tangent_type_token(index: int) -> str:
            if index < len(CurveInterpolation.TangentTypeTokens) and index >= 0:
                return CurveInterpolation.TangentTypeTokens[index]
            else:
                return ""


# a simple wrapper for the infinity type.
class CurveInfinityTypes:
    InfinityTypeTokens = ["constant", "cycle", "cycleRelative", "linear", "oscillate"]

    class InfinityType(IntEnum):
        Constant = 0
        Cycle = 1
        CycleRelative = 2
        Linear = 3
        Oscillate = 4

        @staticmethod
        def get(infinity_type_token: str):
            if infinity_type_token in CurveInfinityTypes.InfinityTypeTokens:
                return CurveInfinityTypes.InfinityType(CurveInfinityTypes.InfinityTypeTokens.index(infinity_type_token))
            else:
                return CurveInfinityTypes.InfinityType.Constant

        @staticmethod
        def to_infinity_type_token(index: int) -> str:
            if index < len(CurveInfinityTypes.InfinityTypeTokens) and index >= 0:
                return CurveInfinityTypes.InfinityTypeTokens[index]
            else:
                return ""


# check attribute validity before using this
def has_sample(attribute, time):
    intervalTuple = attribute.GetBracketingTimeSamples(time)
    if intervalTuple is None:
        return False

    hasSampleAtTheTime = len(intervalTuple) == 2 and time == intervalTuple[0] and time == intervalTuple[1]

    return hasSampleAtTheTime


# check attribute validity before using this
def _both_have_sample(attr0, attr1, time):  # pragma: no cover    Unused code
    return has_sample(attr0, time) and has_sample(attr1, time)


def get_sample_or_default(attribute, time):  # pragma: no cover    Unused code
    if has_sample(attribute, time):
        return attribute.Get(time)
    else:
        return attribute.Get()


def get_data_core_attribute_name(userAttributeName: str, componentIndex: int) -> str:  # pragma: no cover    Unused code
    components = [":x", ":y", ":z", ":w"]
    if componentIndex >= 0 and componentIndex <= 4:
        return userAttributeName + components[componentIndex]
    else:
        carb.log_error("Unexpected code path in get_component_string()")
        return ""


# check data_prim is a curve data prim before using this
def get_data_core_attributes(dataPrim, userAttributeName: str):  # pragma: no cover    Unused code
    result = []
    for i in range(4):
        dataAttribute = dataPrim.GetAttribute(get_data_core_attribute_name(userAttributeName, i))
        if dataAttribute.IsValid() and is_curve_data_core_attribute(dataAttribute):
            result.append(dataAttribute)
        else:
            result.append(None)
    return result


# check attribute validity before using this
def is_curve_user_attribute(attribute):  # pragma: no cover    Unused code
    if is_curve_user_prim(attribute.GetPrim()):
        valueTypeName = attribute.GetTypeName()
        if valueTypeName.isArray:
            return False
        else:
            return str(valueTypeName) not in UNSUPPORTED_CURVE_ATTR_USER_SCALAR_TYPES

    # not found as a curve animatable attribute.
    return False


# check attribute validity before using this
# core means not tangent*** attributes
def is_curve_data_core_attribute(attribute):  # pragma: no cover    Unused code
    if is_curve_data_prim(attribute.GetPrim()):
        # only one type - double. Other attributes in curve data are tangent attributes, they happen to not use "double" as type.
        return str(attribute.GetTypeName()) == "double"
    else:
        pass  # todo. curve user.

    return False


# check prim validity before using this
def is_curve_data_prim(prim):
    return prim.GetTypeName() == CURVE_PRIM_TYPE


# check prim valid before using this
# not must targetting a curve data.
def is_curve_user_prim(prim):  # pragma: no cover    Unused code
    success, relation = find_curve_user_relation(prim)
    if success:
        return success

    success, data_prim = find_curve_data_prim_from(prim)
    return success


def is_curve_node_prim(prim):  # pragma: no cover    Unused code
    return (prim.GetTypeName() in ("OmniGraphNode", "ComputeNode")) and prim.GetAttribute(
        "node:type"
    ).Get() == "omni.anim.curve.core.AnimCurve"


# check relation is valid before using it.
# not must targetting a curve data.
def is_curve_user_relation(relation):  # pragma: no cover    Unused code
    success, foundRelation = find_curve_user_relation(relation.GetPrim())
    return success and (foundRelation == relation)


# check prim is valid before using it.
# not must targetting a curve data.
def find_curve_user_relation(prim):  # pragma: no cover    Unused code
    # curve relation can not be recursive.
    if not is_curve_data_prim(prim):
        relation = prim.GetRelationship(s_tokenAnimationDataBinding)
        return relation.IsValid(), relation

    # default return
    return False, None


# check relation is valid before using it.
def is_targetting_curve_data(relation):  # pragma: no cover    Unused code
    success, prim = find_targetting_curve_data_prim(relation)
    return success


# check relation is valid before using it.
def find_targetting_curve_data_prim(relation):  # pragma: no cover    Unused code
    # if the 1st target is targetting a curve data.
    targets = relation.GetTargets()
    if targets:
        curvePrim = relation.GetStage().GetPrimAtPath(targets[0])
        if curvePrim.IsValid() and is_curve_data_prim(curvePrim):
            return True, curvePrim

    # not found
    return False, None


# check prim validity before using. A data prim itself will not be returned with success.
def find_curve_data_prim_from_other_prim(prim):  # pragma: no cover    Unused code
    success, dataPrim = find_curve_data_prim_from(prim)
    if success and prim == dataPrim:
        success = False

    return success, dataPrim


# check prim is valid before using it.
def find_curve_data_prim_from(prim):  # pragma: no cover    Unused code
    curve_prims = curve_plugin.get_curve_prims(str(prim.GetPath()))
    if curve_prims:
        return True, prim.GetStage().GetPrimAtPath(curve_prims[0])
    else:
        return False, None


# borrowed from camera_tool create_or_find_animation_data.
# check prim is valid before using it.
def create_or_find_curve_data_prim_from(user_prim):  # pragma: no cover    Unused code
    stage = user_prim.GetStage()

    prim_path = user_prim.GetPath()
    rel = user_prim.GetRelationship(s_tokenAnimationDataBinding)

    # check if anim data already exists
    if rel != None:
        targets = rel.GetTargets()
        if len(targets) > 0:
            anim_data_path = targets[0]
            anim_data_prim = stage.GetPrimAtPath(anim_data_path)
            if anim_data_prim:
                return anim_data_prim

    # create a new AnimationData prim with generated path
    anim_data_path = str(prim_path) + "/animationData"
    anim_data_prim = stage.DefinePrim(anim_data_path, CURVE_PRIM_TYPE)
    if anim_data_prim == None:
        return None

    # create relationship
    rel = user_prim.CreateRelationship(s_tokenAnimationDataBinding, False)
    rel.AddTarget(anim_data_path)

    return anim_data_prim


# check prim is valid before using it.
def ext_create_or_find_curve_data_prim_from(user_prim):  # pragma: no cover    Unused code
    anim_data_prim = create_or_find_curve_data_prim_from(user_prim)

    # create attributes
    create_transform_animation_data(anim_data_prim)
    create_general_animation_data(anim_data_prim, user_prim)

    return anim_data_prim


# create all the transform relevent animation data attributes.
def create_transform_animation_data(prim):  # pragma: no cover    Unused code
    for token in s_transform_tokens:
        create_attribute_and_tangent(prim, token)


# create an attribute and tangents
def create_attribute_and_tangent(prim, attribute_name):  # pragma: no cover    Unused code
    prim.CreateAttribute(attribute_name, Sdf.ValueTypeNames.Double, False)
    prim.CreateAttribute(get_tangent_time_attribute_name(attribute_name), Sdf.ValueTypeNames.TimeCodeArray, False)
    prim.CreateAttribute(get_tangent_value_attribute_name(attribute_name), Sdf.ValueTypeNames.DoubleArray, False)
    prim.CreateAttribute(get_tangent_type_attribute_name(attribute_name), Sdf.ValueTypeNames.TokenArray, False)
    prim.CreateAttribute(get_tangent_broken_attribute_name(attribute_name), Sdf.ValueTypeNames.Bool, False)
    prim.CreateAttribute(get_tangent_weighted_attribute_name(attribute_name), Sdf.ValueTypeNames.Bool, False)


# create all the possible non-transform general animation data attributes.
def create_general_animation_data(prim, user_prim):  # pragma: no cover    Unused code
    # take all float or double attributes as they need curves.
    for attribute in user_prim.GetAttributes():
        if attribute.GetTypeName() == "float" or attribute.GetTypeName() == "double":
            attributeName = attribute.GetName()
            if not attributeName in s_overriddenScalarTransform:
                create_attribute_and_tangent(prim, attributeName)


def get_pre_infinity_type_attribute_name(attributeName: str):  # pragma: no cover    Unused code
    return attributeName + ":preInfinityType"


def get_post_infinity_type_attribute_name(attributeName: str):  # pragma: no cover    Unused code
    return attributeName + ":postInfinityType"


def get_tangent_time_attribute_name(attributeName: str):  # pragma: no cover    Unused code
    return attributeName + ":tangentTimes"


def get_tangent_value_attribute_name(attributeName: str):  # pragma: no cover    Unused code
    return attributeName + ":tangentValues"


def get_tangent_type_attribute_name(attr_name: str):  # pragma: no cover    Unused code
    return attr_name + ":tangentTypes"


def get_tangent_weighted_attribute_name(attr_name: str):  # pragma: no cover    Unused code
    return attr_name + ":tangentWeighted"


def get_tangent_broken_attribute_name(attr_name: str):  # pragma: no cover    Unused code
    return attr_name + ":tangentBroken"


def get_tangent_or_infinity_removed_attribute_name(attr_name: str):  # pragma: no cover    Unused code
    for strip_end in [
        ":tangentTimes",
        ":tangentValues",
        ":tangentTypes",
        ":tangentBroken",
        ":tangentWeighted",
        ":preInfinityType",
        ":postInfinityType",
    ]:
        string_pre, dummy, string_post = attr_name.rpartition(strip_end)
        if string_pre != attr_name and string_post == "":
            return string_pre

    return attr_name


def get_infinity_removed_attribute_name(attr_name: str):  # pragma: no cover    Unused code
    for strip_end in [":preInfinityType", ":postInfinityType"]:
        string_pre, dummy, string_post = attr_name.rpartition(strip_end)
        if string_pre != attr_name and string_post == "":
            return string_pre

    return attr_name


# Return 3 str couple (component_name, attr_name, prim_path)
# Returning (component_name, "", prim_path) as failure.
# Returning ("", attr_name, prim_path) also as failure.
# Checking the returned component_name or attr_name against "" for different purpose validation.
def get_component_and_attribute_name_and_prim(curve_path: str):
    component, attr_path = get_component_and_attribute_name(curve_path)
    string_pre, dummy, string_post = attr_path.rpartition(".")
    # if find the separator
    if dummy == ".":
        return component, string_post, string_pre

    return component, "", attr_path


# Returning ("", attr_name) as failure. Checking the returned component_name against "" is an easy way of validation.
def get_component_and_attribute_name(attr_name: str):
    string_pre, dummy, string_post = attr_name.rpartition(":")
    # if find the separator
    if dummy == ":":
        # if the postfix is among xyzw
        if string_post == "x" or string_post == "y" or string_post == "z" or string_post == "w":
            return string_post, string_pre

    return "", attr_name


def get_component_removed_attribute_name(attr_name: str):  # pragma: no cover    Unused code
    for strip_end in [":x", ":y", ":z", ":w"]:
        string_pre, dummy, string_post = attr_name.rpartition(strip_end)
        if dummy == strip_end and string_post == "":
            return string_pre

    return attr_name


def get_runtime_style_attribute_name(attr_name: str):
    replacer = ["|x", "|y", "|z", "|w"]
    for index, strip_end in enumerate([":x", ":y", ":z", ":w"]):
        string_pre, dummy, string_post = attr_name.rpartition(strip_end)
        if dummy == strip_end and string_post == "":
            return string_pre + replacer[index]

    return attr_name


# prim checked inside the function. helper for og using curve.
def is_timeline_node(prim):
    if prim and prim.GetTypeName() in ("OmniGraphNode", "ComputeNode"):
        attr = prim.GetAttribute("node:type")
        if attr and attr.Get() == "omni.anim.Timeline":
            return True

    return False


# return list of pair of component_name and attr_name for animatable prim
def get_track_attr_and_component_names_from_runtime(prim_path_str):
    result = []
    for name, curve in curve_plugin.get_curves(prim_path_str).items():
        component_name, attr_name = get_component_and_attribute_name(name)
        result.append((attr_name, component_name))

    return result


# return None if not found
def get_curve_from_runtime(prim_path_str, data_attr_name):
    curve = curve_plugin.get_curves(prim_path_str).get(data_attr_name)
    return curve


def time_code_to_time_tick(time_code: float, time_codes_per_second) -> int:
    return int(round(time_code * curve_plugin.get_ticks_per_second() / time_codes_per_second))


def time_tick_to_time_code(time_tick: int, time_codes_per_second) -> float:
    return (float(time_tick)) / curve_plugin.get_ticks_per_second() * time_codes_per_second


# the adapter to use SchemaKey
class SchemaKeyTuber:
    def __init__(self, schema_key, time_codes_per_second=0):
        self._schema_key = schema_key
        self._time_codes_per_second = time_codes_per_second

    def get_time_tick(self) -> int:
        return self._schema_key.time

    def get_time_code(self) -> float:
        if self._time_codes_per_second > 0:
            return time_tick_to_time_code(self._schema_key.time, self._time_codes_per_second)
        else:
            carb.log_error("SchemaKeyTuber._time_codes_per_second is not initialized")

    def get_value(self):
        return self._schema_key.value

    def is_tangent_broken(self):
        return self._schema_key.tangentBroken

    def is_tangent_weighted(self):
        return self._schema_key.tangentWeighted

    def get_in_tangent_type(self):
        return CurveInterpolation.TangentType.get(self._schema_key.inTangent.type)

    def get_out_tangent_type(self):
        return CurveInterpolation.TangentType.get(self._schema_key.outTangent.type)

    def get_in_tangent_time_tick(self) -> int:
        return self._schema_key.inTangent.time + self._schema_key.time

    def get_in_tangent_time_code(self) -> float:
        if self._time_codes_per_second > 0:
            return time_tick_to_time_code(
                self._schema_key.inTangent.time + self._schema_key.time, self._time_codes_per_second
            )
        else:
            carb.log_error("SchemaKeyTuber._time_codes_per_second is not ininitialized")

    def get_in_tangent_value(self):
        return self._schema_key.inTangent.value + self._schema_key.value

    def get_out_tangent_time_tick(self) -> int:
        return self._schema_key.outTangent.time + self._schema_key.time

    def get_out_tangent_time_code(self) -> float:
        if self._time_codes_per_second > 0:
            return time_tick_to_time_code(
                self._schema_key.outTangent.time + self._schema_key.time, self._time_codes_per_second
            )
        else:
            carb.log_error("SchemaKeyTuber._time_codes_per_second is not ininitialized")

    def get_out_tangent_value(self):
        return self._schema_key.outTangent.value + self._schema_key.value

    def set_time_code(self, time_code: float):  # pragma: no cover    Unused code
        if self._time_codes_per_second > 0:
            self._schema_key.time = time_code_to_time_tick(time_code, self._time_codes_per_second)
        else:
            carb.log_error("SchemaKeyTuber._time_codes_per_second is not ininitialized")

    def set_time_tick(self, time_tick: int):
        self._schema_key.time = time_tick

    def set_value(self, value):
        self._schema_key.value = value

    def set_in_tangent_time_code(self, time_code):  # pragma: no cover    Unused code
        if self._time_codes_per_second > 0:
            self._schema_key.inTangent.time = (
                time_code_to_time_tick(time_code, self._time_codes_per_second) - self._schema_key.time
            )
        else:
            carb.log_error("SchemaKeyTuber._time_codes_per_second is not ininitialized")

    def set_in_tangent_time_tick(self, time_tick):
        self._schema_key.inTangent.time = time_tick - self._schema_key.time

    def set_in_tangent_value(self, value):
        self._schema_key.inTangent.value = value - self._schema_key.value

    def set_out_tangent_time_code(self, time_code):  # pragma: no cover    Unused code
        if self._time_codes_per_second > 0:
            self._schema_key.outTangent.time = (
                time_code_to_time_tick(time_code, self._time_codes_per_second) - self._schema_key.time
            )
        else:
            carb.log_error("SchemaKeyTuber._time_codes_per_second is not ininitialized")

    def set_out_tangent_time_tick(self, time_tick):
        self._schema_key.outTangent.time = time_tick - self._schema_key.time

    def set_out_tangent_value(self, value):
        self._schema_key.outTangent.value = value - self._schema_key.value

    def set_is_tangent_broken(self, is_tangent_broken: bool):
        self._schema_key.tangentBroken = is_tangent_broken

    def set_is_tangent_weighted(self, is_tangent_weighted: bool):
        self._schema_key.tangentWeighted = is_tangent_weighted

    def set_in_tangent_type(self, tangent_type: CurveInterpolation.TangentType):
        self._schema_key.inTangent.type = CurveInterpolation.TangentType.to_tangent_type_token(tangent_type)

    def set_out_tangent_type(self, tangent_type: CurveInterpolation.TangentType):
        self._schema_key.outTangent.type = CurveInterpolation.TangentType.to_tangent_type_token(tangent_type)

    # an QA option to use it as an indication that it is in an intermediate status.
    def reset_tangents_to_origin(self):
        self._schema_key.inTangent.time = 0
        self._schema_key.inTangent.value = 0
        self._schema_key.outTangent.time = 0
        self._schema_key.outTangent.value = 0


def get_track_is_selected(track_name, time_tick: int) -> bool:
    selected_keys = omni.anim.curve.core.KeySelectionState.global_instance.curves.get(track_name)
    return selected_keys.get(time_tick) != None if selected_keys != None else False
