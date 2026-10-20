import copy
import math
from typing import Any, List, Tuple, Union

import AnimationSchema
import AnimationSchemaTools
import carb
import numpy
import omni.kit.commands
import omni.kit.undo
import omni.timeline
import omni.usd
from omni.kit.usd_undo import UsdLayerUndo
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade, Vt

from ..bindings._animcurve import *
from . import utils
from .keySelection import *
from .simplication_utils import SimplificationAlgorithm
from .utils import (
    BOOL_TYPE,
    FLOAT_FOUR_TYPE,
    FLOAT_THREE_TYPE,
    FLOAT_TWO_TYPE,
    FLOAT_TYPE,
    INT_FOUR_TYPE,
    INT_THREE_TYPE,
    INT_TWO_TYPE,
    INT_TYPE,
    TOKEN_TYPE,
    VALUE_VEC_TYPE,
    get_curvekey_clipboard,
)

_is_authoring = False


def is_authoring():
    return _is_authoring


_VALUE_DIM = {attr_value_type: 1 for attr_value_type in FLOAT_TYPE + INT_TYPE + BOOL_TYPE + TOKEN_TYPE}
_VALUE_DIM.update({attr_value_type: 2 for attr_value_type in FLOAT_TWO_TYPE + INT_TWO_TYPE})
_VALUE_DIM.update({attr_value_type: 3 for attr_value_type in FLOAT_THREE_TYPE + INT_THREE_TYPE})
_VALUE_DIM.update({attr_value_type: 4 for attr_value_type in FLOAT_FOUR_TYPE + INT_FOUR_TYPE})

_VALUE_TYPE = {
    attr_value_type: float for attr_value_type in FLOAT_TYPE + FLOAT_TWO_TYPE + FLOAT_THREE_TYPE + FLOAT_FOUR_TYPE
}
_VALUE_TYPE.update(
    {attr_value_type: int for attr_value_type in INT_TYPE + INT_TWO_TYPE + INT_THREE_TYPE + INT_FOUR_TYPE}
)
_VALUE_TYPE.update({attr_value_type: bool for attr_value_type in BOOL_TYPE})

_COMP_NAME_TO_IDX = {"x": 0, "y": 1, "z": 2, "w": 3}
_COMP_IDX_TO_NAME = {v: k for (k, v) in _COMP_NAME_TO_IDX.items()}


def _get_default_value(property):
    default_values = {"xformOp:scale": (1.0, 1.0, 1.0), "visibleInPrimaryRay": True}

    if isinstance(property, Usd.Attribute):
        prim = property.GetPrim()
        if prim:
            if (prim.IsA(UsdShade.Shader) or prim.IsA(UsdShade.NodeGraph)) and UsdShade.Input.IsInput(property):
                # This is not the standard USD way to get default. The
                # standard way is Sdr. But out shader compiler produces
                # this metadata in the session layer, so it will be
                # working for MDL
                custom = property.GetCustomData()
                if "default" in custom:
                    return True, custom["default"]
            else:
                prim_definition = prim.GetPrimDefinition()
                prop_spec = prim_definition.GetSchemaPropertySpec(property.GetPath().name)
                if prop_spec and prop_spec.default != None:
                    return True, prop_spec.default

            if property.GetName() in default_values:
                return True, default_values[property.GetName()]

            # If we still don't find default value, use type's default value
            value_type = property.GetTypeName()
            default_value = value_type.defaultValue
            return True, default_value
    # elif isinstance(property, PlaceholderAttribute):
    #     return True, property.Get()

    return False, None


class AnimCurveCommandBase(omni.kit.commands.Command):
    def __init__(
        self,
        name: str = "AnimCurveCommandBase",
        stage: Union[Usd.Stage, None] = None,
        paths: Union[list, None] = None,
        time: Union[Usd.TimeCode, None] = None,
    ):
        input_is_valid = True

        # Check the types of the parameters
        if isinstance(name, str):
            self._name = name
        else:
            carb.log_error(f"AnimCurveCommandBase: `name` TypeError: Expected str, got {type(name)}.")
            input_is_valid = False

        if stage is None or isinstance(stage, Usd.Stage):
            self._stage = stage
        else:
            carb.log_error(f"{name}: `stage` TypeError: Expected None or Usd.Stage, got {type(stage)}.")
            input_is_valid = False

        if paths is None or isinstance(paths, list):
            self._paths = paths
        else:
            carb.log_error(f"{name}: `paths` TypeError: Expected None or list, got {type(paths)}.")
            input_is_valid = False

        if time is None or isinstance(time, Usd.TimeCode):
            self._time = time
        else:
            carb.log_error(f"{name}: `time` TypeError: Expected None or Usd.TimeCode, got {type(time)}.")
            input_is_valid = False

        # Process the parameters. Child classes can override them if the default ones do not meet the requirements.
        input_is_valid = input_is_valid and self._process_stage()
        input_is_valid = input_is_valid and self._process_paths()
        input_is_valid = input_is_valid and self._process_time()

        # Sanity checks. Child classes can override them if the default ones do not meet the requirements.
        input_is_valid = input_is_valid and self._sanity_checks_stage()
        input_is_valid = input_is_valid and self._sanity_checks_paths()
        input_is_valid = input_is_valid and self._sanity_checks_time()

        self._input_is_valid = input_is_valid

        # Undo
        self._usd_undo = None

        # Typing
        self._name: str
        self._stage: Usd.Stage
        self._paths: List[str]
        self._time: float

    def _process_stage(self) -> bool:
        if self._stage is None:
            self._stage = omni.usd.get_context().get_stage()
        return True

    def _process_paths(self) -> bool:
        if self._paths is None:
            context = omni.usd.get_context()
            if context:
                selection = context.get_selection()
                if selection:
                    self._paths = selection.get_selected_prim_paths()  # rtn value is a list
                else:
                    carb.log_error(f"{self._name}: Can not get the path of the selected prim.")
                    return False
            else:
                carb.log_error(f"{self._name}: Can not get the path of the selected prim.")
                return False
        return True

    def _process_time(self) -> bool:
        if self._time == None or self._time == Usd.TimeCode.Default():
            self._time = (
                omni.timeline.get_timeline_interface().get_tentative_time() * self._stage.GetTimeCodesPerSecond()
            )
        else:
            self._time = self._time.GetValue()

        return True

    def _sanity_checks_stage(self) -> bool:
        if self._stage is None:
            carb.log_error(f"{self._name}: Stage is None!")
            return False
        if isinstance(self._stage, Usd.Stage):
            return True
        else:
            carb.log_error(f"{self._name}: `stage` TypeError: Expected Usd.Stage. Got {type(self._stage)}.")
            return False

    def _sanity_checks_paths(self) -> bool:
        if not isinstance(self._paths, list):  # It should not happen. Just a double check
            carb.log_error(f"{self._name}: `paths` TypeError: Expected list, got {type(self._paths)}.")
            return False

        if len(self._paths) == 0:
            carb.log_error(f"{self._name}: path is empty. Will not do anything.")
            return False

        for path in self._paths:
            if not isinstance(path, str):
                carb.log_error(f"{self._name}: `paths` TypeError: Expected list of str. Got {type(path)} inside.")
                return False

        return True

    def _sanity_checks_time(self) -> bool:
        if isinstance(self._time, float):
            return True
        else:
            carb.log_error(f"{self._name}: `time` TypeError: Expected float. Got {type(self._time)}.")
            return False

    def do(self) -> bool:
        # The kit framework will call do() anyway even if error is raised in the constructor,
        # so if we refuse to do anything due to failures in sanity checks, we have to do it here.
        # Please do not override this method.
        if self._input_is_valid:
            return self._do()
        else:
            return False

    def _do(self) -> bool:
        # Please override this method in child classes.
        carb.log_error(f"{self._name}: NotImplementedError.")
        return False

    def undo(self) -> None:
        if self._usd_undo is None:
            return
        self._usd_undo.undo()

    def _get_attr_dimension(self, attr_type_name) -> int:
        # to get attr_type_name from `attr`: attr.GetTypeName()
        return _VALUE_DIM.get(attr_type_name, 0)

    def _get_attr_type(self, attr_type_name) -> Union[int, None]:
        # to get attr_type_name from `attr`: attr.GetTypeName()
        return _VALUE_TYPE.get(attr_type_name, None)

    def _get_attr_type_dimension(self, attr) -> Tuple[Union[int, None], int]:
        attr_type_name = attr.GetTypeName()
        return self._get_attr_type(attr_type_name), self._get_attr_dimension(attr_type_name)

    def _get_animation_prim_path(self, prim):
        curve_prims = utils.get_curve_prims(prim)
        if curve_prims:
            return curve_prims[0].GetPath()
        else:
            return None

    def _get_comp_idx(self, comp_name: str) -> Union[int, None]:
        comp_idx = _COMP_NAME_TO_IDX.get(comp_name, None)
        if comp_idx is None:
            carb.log_error(f"{self.name}: {comp_name} is not a valid component name!")
            return None

        return comp_idx

    def _get_comp_attr_token(self, attr_token, comp_idx: int) -> Union[str, None]:
        comp_name = _COMP_IDX_TO_NAME.get(comp_idx, None)
        if comp_name is None:
            carb.log_error(f"{self.name}: {comp_idx} is not a valid component index!")
            return None

        return attr_token + ":" + comp_name

    def _get_comp_attr_path(self, attr_path, comp_idx: int) -> Union[str, None]:
        comp_name = _COMP_IDX_TO_NAME.get(comp_idx, None)
        if comp_name is None:
            carb.log_error(f"{self.name}: {comp_idx} is not a valid component index!")
            return None

        return attr_path + "|" + comp_name

    def _parse_path(self, path: str) -> Union[Tuple[Sdf.Path, str, int, int, bool, bool], None]:
        attr_path = None
        attr_token = None
        comp_len = 0
        comp_idx = 0
        is_prim_path = False
        is_comp_path = False

        if path.endswith("|x") or path.endswith("|y") or path.endswith("|z") or path.endswith("|w"):
            is_comp_path = True

            temp_attr_path = Sdf.Path(path[:-2])
            if temp_attr_path.IsPrimPropertyPath():
                prim_path, attr_path, attr_token = temp_attr_path.GetPrimPath(), temp_attr_path, temp_attr_path.name
            else:
                prim_path, attr_path, attr_token = None, None, None  # TODO@tutian: should we raise an error here?
            comp_idx = self._get_comp_idx(path[-1])

        elif Sdf.Path(path).IsPrimPath():
            is_prim_path = True
            prim_path = Sdf.Path(path)

        elif Sdf.Path(path).IsPrimPropertyPath():
            sdf_path = Sdf.Path(path)
            prim_path = sdf_path.GetPrimPath()
            attr_path = sdf_path
            attr_token = sdf_path.name

        else:
            carb.log_error(f"{self._name}: {path} is not a path of prim, prim property, nor attribute!")
            return None

        if attr_path is not None:
            attr = self._stage.GetAttributeAtPath(attr_path)
            # carb.log_warn(attr_path)  # uncomment when debugging
            # carb.log_warn(attr)
            if attr:
                attr_value_type = attr.GetTypeName()
                comp_len = self._get_attr_dimension(attr_value_type)
                if comp_len == 0:  # note that 0 is the default value
                    carb.log_error(f"{self._name}: {path}'s Attribute Type Error!")
                    return None
            else:
                carb.log_error(f"{self._name}: {path}'s Attribute {attr_path} is illegal!")
                return None

        return prim_path, attr_token, comp_len, comp_idx, is_prim_path, is_comp_path


class AddAnimCurves(AnimCurveCommandBase):
    """
    Add an empty curve for the given attribute path(s). Non-exist attribute paths will be skipped
    @param
        paths:  is a list of string-typed attribute paths. Each path can be one of three types
                1. prim path:  Add curves for all of its available attributes.  e.g. "/World/Cube"
                2. attribute path:  Add curves for that specific attribute. Multiple curves will be added \
                                    for vector-typed attribute e.g. "/World/Cube.size", "/World/Cube.xformOp:translate":\
                3. None:       Add curves for all currently selected prims
                paths default value is None

    @return
        Return True if we successfully add curves for all the paths
        Return False if any curve's addition is skipped due to some error
    @example
        AddAnimCurves(paths=["/World/Cube.xformOp:translate|x", "/World/Sphere.radius"])
        AddAnimCurves(paths=["/World/Cube.size|x"])  same as AddAnimCurves(paths=["/World/Cube.size"])
        AddAnimCurves(paths=["/World/Cube.xformOp:translate"])
        AddAnimCurves(paths=["/World/Cube"])
        AddAnimCurves()
    """

    def __init__(self, paths: list = None):
        super().__init__(name="AddAnimCurves", paths=paths)

    def _do(self):
        usd_undo = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())
        cached_path = set()

        result = True
        for path in self._paths:
            prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
            prim = self._stage.GetPrimAtPath(prim_path)
            if not utils.has_anim(prim):
                # TODO: We actually only need to reserve the animationData:binding relationship
                utils.add_anim(prim)
                animation_data_prim_path = self._get_animation_prim_path(prim)
                cached_path.add(animation_data_prim_path)
            else:
                animation_data_prim_path = self._get_animation_prim_path(prim)
                if animation_data_prim_path not in cached_path:
                    cached_path.add(animation_data_prim_path)
                    usd_undo.reserve(animation_data_prim_path)

            if is_prim_path:
                # We assume that the animationData:binding is already added here
                # usd_undo.reserve(prim_path)

                # Add curves for all attributes in this prim
                if utils.add_curves(prim):
                    # no AnimationSchemaTools.AddKeys here. So empty curves.
                    pass
                else:
                    carb.log_error("Unexpected code path in AddAnimCurves.do() AddCurves")
                    result = False
            else:
                if is_comp_path:
                    attr_token = attr_token + "|" + _COMP_IDX_TO_NAME[comp_idx]

                # API support full Attribute token, e.g. "xformOp:translate"
                # and component token, e.g. "xformOp:translate:x"
                if utils.add_curves(prim, attr_token):
                    # no AnimationSchemaTools.AddKey here. So an empty curve
                    pass
                else:
                    carb.log_error("Unexpected code path in AddAnimCurves.do() AddCurve")
                    result = False

        self._usd_undo = usd_undo
        return result


class RemoveAnimCurves(AnimCurveCommandBase):
    """
    Remove a list of curves specified by the paths
    @param
        paths:  1. curves' path,  only move keys in these curves         e.g. /World/Cube.xformOp:translate|x
                2. prims' path, move keys in all curves of this prim  e.g. /World/Cube
                3. None,  move keys in all curves of all the SELECTED prims
                The default value is None
    @return
        Return True if we successfully remove the curve without any errors
        Return False if no curve is removed or there are errors generated
    @example
        RemoveAnimCurves(paths=["/World/Cube.xformOp:translate|x", "/World/Sphere.radius"])  #Remove two curves
        RemoveAnimCurves(paths=["/World/Cube.size|x"])               #Remove the specified curve
        RemoveAnimCurves(paths=["/World/Cube.xformOp:translate"])    #Remove three curves
        RemoveAnimCurves(paths=["/World/Cube"])                      #Remove all of its curves in this prim
        RemoveAnimCurves()                                           #Remove all curves of the selected prim
    """

    def __init__(self, paths: list = None):
        super().__init__(name="RemoveAnimCurves", paths=paths)

    def _do(self):
        usd_undo = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())
        cached_path = set()
        remove_curves = False

        for path_index, path in enumerate(self._paths):
            prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
            prim = self._stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                continue
            # purely for undo purpose
            animation_data_prim_path = self._get_animation_prim_path(prim)
            if animation_data_prim_path not in cached_path:
                cached_path.add(animation_data_prim_path)
                usd_undo.reserve(animation_data_prim_path)

            if is_prim_path:
                # e.g. /World/Cube  Move all of its keys
                if utils.has_anim(prim):
                    curve_names = utils.get_curves(prim)
                    vt_curve_names = Vt.TokenArray(len(curve_names), curve_names)
                    utils.del_curves(prim, vt_curve_names)
                    remove_curves = True
            elif is_comp_path:
                # e.g. /World/Cube.xformOp:translate|x or /World/Cube.size|x
                # move specific keys
                curve_name = self._get_comp_attr_token(attr_token, comp_idx)
                vt_curve_names = Vt.TokenArray(1, curve_name)
                utils.del_curves(prim, vt_curve_names)
                remove_curves = True
            else:
                # /World/Cube.xformOp:translate or /World/Cube.size
                # move vector or scalar keys
                curve_names = []
                for index in range(comp_length):
                    curve_names.append(self._get_comp_attr_token(attr_token, index))
                vt_curve_names = Vt.TokenArray(comp_length, curve_names)
                utils.del_curves(prim, vt_curve_names)
                remove_curves = True

        self._usd_undo = usd_undo
        return remove_curves


class SetAnimCurveKeys(AnimCurveCommandBase):
    """
    Set keys to the given paths at the given time, with the given value.
    @param
        paths:
            A list of string-typed USD paths. Each path can be one of the three types:
                1. Prims' path, set xformable attribute keys to the prims.
                2. Curves' path, set keys to the curve(s)
                3. None, set keys to the SELECTED prim(s).
                The default value is None.
                We allow a mixture of prims' paths and curves' paths.
        time:
            The time code to set keys at. Can be one of the three types:
                1. A single element of type float, int, or Usd.TimeCode, specifing the time to set keys at.
                2. A list of float, int, or Usd.TimeCode. See description for details.
                3. None, will use the current time.
                The default value is None.
        value:
            The value to set keys with. Can be one of the three types:
                1. A single scalar or vector.
                2. A list of scalars or vectors. See description for details.
                3. None, will use the default value read from USD.
                The default value is None. Must be None if prims' paths are provided.
        preserveCurveShape:
            Preserve the shape of the curve when add a new key between two exsiting keys, if possible. The default value is True.
            If True, `time` and `value` must be None or of length 1.
            If False, the tangent type of the new key will be Auto by default.
            Note that in order to keep the shape, the tangent and the weighted attribute of the two neighbouring keys may be changed.
            This parameter will be ignored silently, when:
                1. it's impossible to preserve the shape. For example, the user specifies some time and value that don't stay on the curve.
                2. either `inTangentType` or `outTangentType` is not None.
        inTangentType:
            A string to set the in tangent type of the key. Possible values are None, "auto", "smooth", "linear", "step", and "fixed".
            The default value is None. If not None, this command will override the tangent types of the target keys. `preserveCurveShape` will be ignored.
        outTangentType:
            A string to set the out tangent type of the key. Possible values are None, "auto", "smooth", "linear", "step", and "fixed".
            The default value is None. If not None, this command will override the tangent types of the target keys. `preserveCurveShape` will be ignored.
        tangentBreakDown:
            A bool value to indicate if the tangent of the key is broken. True for broken and False for unbroken.
            The default value is None, which means let the curve runtime system choose it, perhaps, from the preference setting.

    @return
        Return True if we successfully set the keys and there are no errors.
        Return False if no keys are added or there are errors.

    @description
        1.  If `time` is None or single-element, `value` must be None or single-element also. Vice versa.
        2.  If `time` is a list of elements, `value` must be a list of elements also. Vice versa.
            In addition, the lengths of `time` and `value` must be the same.
            The type of `value`s in the list must be the same.

    @example
        1.  SetAnimCurveKeys()                      # Set keys to the selected prim(s), at the current time, with the default value
        2.  SetAnimCurveKeys(paths=["/World/Cube"]) # Set xformable attribute keys (current time, default value) to /World/Cube
        3.  SetAnimCurveKeys(paths=["/World/Cube.xformOp:scale|x"])
                                                    # Set a key (current time, default value) to the attribute /World/Cube.xformOp:scale|x
        4.  SetAnimCurveKeys(paths=["/World/Cube", "/World/Cube.xformOp:scale|x"])
                                                    # The same as executing both 2. and 3.
        5.  SetAnimCurveKeys(paths=["/World/Cube.xformOp:scale|x"], value=2.0, time=Usd.TimeCode(50))
                                                    # Set a key (50, 2.0) to the attribute /World/Cube.xformOp:scale|x
        6.  SetAnimCurveKeys(paths=["/World/Cube.xformOp:scale|x", "/World/Cube.xformOp:translate|x"], value=[0.0, 3.14, 2.0], time=[0, 30, 60], preserveCurveShape=False)
                                                    # Set keys (0, 0.0), (30, 3.14), and (60, 2.0) to the two given curves. preserveCurveShape must be set to `False`
    """

    def __init__(
        self,
        paths: list = None,
        time: Union[Union[float, int, Usd.TimeCode], list] = None,
        value: Any = None,
        preserveCurveShape: bool = True,
        inTangentType: Union[str, None] = None,
        outTangentType: Union[str, None] = None,
        tangentBreakDown: Union[bool, None] = None,
    ):

        super().__init__(name="SetAnimCurveKeys", paths=paths)

        if self._input_is_valid == False:
            # Base sanity check doesn't pass. No need to proceed.
            return

        self._key_times = time
        # value could be a scalar or a vector but should not be a list
        self._key_values = value

        if self._key_times is None:
            self._key_times = [
                omni.timeline.get_timeline_interface().get_tentative_time() * self._stage.GetTimeCodesPerSecond()
            ]
        else:
            if not isinstance(self._key_times, list):
                self._key_times = [self._key_times]
            for i, t in enumerate(self._key_times):
                if not isinstance(t, Usd.TimeCode) and not isinstance(t, float) and not isinstance(t, int):
                    error_msg_core = "Expected None or list[Union[Usd.TimeCode,float, int]], found "
                    carb.log_error(f"SetAnimCurveKeys: `time` TypeError: {error_msg_core}{type(t)} in the list.")
                    self._input_is_valid = False
                elif isinstance(t, Usd.TimeCode):
                    self._key_times[i] = float(t.GetValue())
        if self._key_values is not None and not isinstance(self._key_values, list):
            self._key_values = [self._key_values]

        if self._key_values is not None and len(self._key_times) != len(self._key_values):
            carb.log_error(f"SetAnimCurveKeys: key and value count must match.")
            self._input_is_valid = False

        self._preserve_curve_shape = preserveCurveShape
        if inTangentType is not None or outTangentType is not None:
            self._preserve_curve_shape = False
        if self._preserve_curve_shape:
            if len(self._key_times) == 1 and (self._key_values is None or len(self._key_values) == 1):
                pass
            else:
                self._input_is_valid = False
                carb.log_error(
                    f"SetAnimCurveKeys: `time` and `value` must be None or of length 1, if preserveCurveShape=True!"
                )
        self._in_tangent_type = inTangentType
        self._out_tangent_type = outTangentType
        self._broken_tangent = tangentBreakDown
        self._usd_undo = None
        self._key_value_token_index = None

        # sanity checks for in/out tangent type and broken
        if not self._broken_tangent in (True, False, None):
            carb.log_error(f"SetAnimCurveKeys: tangentBreakDown must be a bool value or None.")
            self._input_is_valid = False
        if not self._in_tangent_type in (None, "auto", "smooth", "flat", "linear", "step", "fixed"):
            carb.log_error(
                f"SetAnimCurveKeys: inTangentType must be None, 'auto', 'smooth', 'flat', 'linear', 'step', or 'fixed'."
            )
            self._input_is_valid = False
        if not self._out_tangent_type in (None, "auto", "smooth", "flat", "linear", "step", "fixed"):
            carb.log_error(
                f"SetAnimCurveKeys: outTangentType must be None, 'auto', 'smooth', 'flat', 'linear', 'step', or 'fixed'."
            )
            self._input_is_valid = False

        if self._key_values is not None:
            # check the type of the first element then check if all values have the same type
            self._input_is_valid = self._input_is_valid and self._sanity_checks_value(self._key_values[0])
            for value in self._key_values:
                equal_type = type(self._key_values[0]) == type(value)
                self._input_is_valid = self._input_is_valid and equal_type
                if not equal_type:
                    carb.log_error(f"SetAnimCurveKeys: value types have to be the same for all keys.")
                    self._input_is_valid = False

        self._redo_path_values = {}  # path: value

    def _update_token_index(self, attr, token):
        tokens = attr.GetMetadata("allowedTokens")

        if isinstance(tokens, Vt.TokenArray):
            if token in tokens:
                self._key_value_token_index = list(tokens).index(token)

        if self._key_value_token_index is None:
            carb.log_error(
                f"SetAnimCurveKeys: path {attr.GetPath()} is of type token, but key value '{token}' is not in allowed token list."
            )

    def _check_attr_value_type(self, value):

        # Retrieve the key_value's type and length
        value_len = value_type = None
        if type(value) in VALUE_VEC_TYPE:
            value_len = len(value)
            # We don't support vector type more than 4 components
            if value_len > 4:
                return False
            value_type = type(value[0])

        elif type(value) == float or type(value) == int or type(value) == bool:
            value_len = 1
            value_type = type(value)

        # Now we have self._key_value's value type and vector length
        # Check if each attribute in the path matches it
        for path in self._paths:
            component_path = False
            attr_path = path
            component_idx = 0
            if path.endswith("|x") or path.endswith("|y") or path.endswith("|z") or path.endswith("|w"):
                component_path = True
                attr_path = path[:-2]
                postfix = path[-1]
                if postfix == "x":
                    component_idx = 0
                elif postfix == "y":
                    component_idx = 1
                elif postfix == "z":
                    component_idx = 2
                elif postfix == "w":
                    component_idx = 3
                else:
                    carb.log_error(f"SetAnimKeyCommand: Invalid attribute component postfix for the argument {path}")
                    return False
            elif Sdf.Path(path).IsPrimPath() and value != None:
                carb.log_error(f"SetAnimKeyCommand: Invalid param. {path} is a prim path, but value is not None!")
                return False

            attr = self._stage.GetAttributeAtPath(attr_path)
            if not attr:
                prim_path = Sdf.Path(path).GetPrimPath()
                prim = self._stage.GetPrimAtPath(prim_path)
                if not prim:
                    carb.log_error(f"SetAnimKeyCommand: Invalid prim {prim_path}")
                    return False

                prim_def = prim.GetPrimDefinition()
                if not prim_def:
                    carb.log_error(f"SetAnimKeyCommand: Invalid prim definition {prim_path}")
                    return False

            if not attr or not attr.IsValid():
                carb.log_error(f"SetAnimKeyCommand: Invalid attribute {path}")
                return False

            if attr.GetVariability() != Sdf.VariabilityVarying:
                carb.log_error(f"SetAnimKeyCommand: Attribute variability is not verying {path}")
                return False

            attr_value_type = attr.GetTypeName()

            # We don't support array type
            if attr_value_type.isArray:
                carb.log_error(
                    f"SetAnimKeyCommand: attribute {path} is an array-typed attribute, we don't support it yet!"
                )
                return False

            # Get the dimension of the attribute's value
            attr_type, attr_dim = self._get_attr_type_dimension(attr)
            # For component path, dimention is always 1, only compare the value type, not length
            if component_path:
                if attr_dim <= component_idx:
                    carb.log_error(f"SetAnimKeyCommand: Specifies a vector component index out of range")
                    return False
                if value_len > 1:
                    carb.log_error(
                        f"SetAnimKeyCommand: path {path} is a vector component path, but the value {value} is a vector."
                    )
                    return False
                if attr_type != value_type:
                    carb.log_error(
                        f"SetAnimKeyCommand: path {path} is of type {attr_type}, but the value {value} of type {value_type}, type mismatch!"
                    )
                    return False
            elif attr_value_type == Sdf.ValueTypeNames.Token:
                self._update_token_index(attr, value)
                return self._key_value_token_index is not None
            else:
                if attr_type != value_type:
                    carb.log_error(
                        f"SetAnimKeyCommand: path {path} is of type {attr_type}, but the value {value} of type {value_type}, type mismatch!"
                    )
                    return False
                if attr_dim != value_len:
                    carb.log_error(
                        f"SetAnimKeyCommand: path {path} value is a vector of length {attr_dim}, but the value {value} length is {value_len}, length mismatch!"
                    )
                    return False

            continue

        return True

    def _sanity_checks_value(self, value):

        # # value must be a scalar or a vector value
        # if isinstance(value, list):
        #     return False

        # Multiple attribute paths are provided and value is not None
        # need to check if their type are the same compatible with the provided value
        if value != None:
            return self._check_attr_value_type(value)
        else:
            return True

    def _do(self):
        usd_undo = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())
        cached_path = set()

        # Make sure we always use integer frame number
        for i in range(len(self._key_times)):
            self._key_times[i] = round(self._key_times[i], 0)

        for path in self._paths:
            prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
            prim = self._stage.GetPrimAtPath(prim_path)
            if not utils.has_anim(prim):
                utils.add_anim(prim)
                animation_data_prim_path = self._get_animation_prim_path(prim)
                # The animaitonData prim's undo will be executed by the OGN node
                cached_path.add(animation_data_prim_path)
            else:
                animation_data_prim_path = self._get_animation_prim_path(prim)
                if animation_data_prim_path not in cached_path:
                    cached_path.add(animation_data_prim_path)
                    usd_undo.reserve(animation_data_prim_path)

            if is_prim_path:
                # Add curves for all attributes in this prim
                if utils.add_curves(prim):
                    for time in self._key_times:
                        utils.add_keys(
                            prim,
                            omni.timeline.get_timeline_interface().get_tentative_time(),
                            time,
                            self._in_tangent_type,
                            self._out_tangent_type,
                            self._broken_tangent,
                            self._preserve_curve_shape,
                        )
            else:
                if self._key_values is None:
                    if path not in self._redo_path_values.keys():
                        # Use current value
                        attr = prim.GetAttribute(attr_token)
                        attr_value = attr.Get(Usd.TimeCode.Default())  # or current time?
                        if attr_value == None:
                            has_default_value, attr_value = _get_default_value(attr)
                            # There is no value to add for this key
                            if not has_default_value:
                                return False  # alternative: still add keys which have default values
                        # e.g. /World/Cube.size|x  is a comp_path but the comp_length is 1 a scalar attribute
                        if is_comp_path and comp_length > 1:
                            attr_value = attr_value[comp_idx]
                        attr_values = [attr_value]
                        self._redo_path_values[path] = attr_values
                    else:
                        attr_values = self._redo_path_values[path]
                else:
                    attr_values = [value for value in self._key_values]

                curve_path = attr_token
                if is_comp_path:
                    curve_path = attr_token + "|" + _COMP_IDX_TO_NAME[comp_idx]

                # API support full Attribute token, e.g. "xformOp:translate"
                # and component token, e.g. "xformOp:translate:x"
                if utils.add_curves(prim, curve_path):
                    attr_path = attr_token
                    if attr_path.endswith(":x"):
                        attr_path = attr_path[:-2]
                    attr = prim.GetAttribute(attr_path)
                    for i in range(len(self._key_times)):
                        attr_value = attr_values[0]
                        if len(attr_values) == len(self._key_times):
                            attr_value = attr_values[i]
                        # If the given value doesn't equal to the value at the given time, we must set preserve_shape=False
                        preserve_shape = self._preserve_curve_shape
                        if preserve_shape:
                            # Curve Runtime use nature time. The unit is second. Time = TimeCode / FPS
                            curve_name = curve_path.replace("|", ":")
                            evaluate_value = utils.curve_plugin.evaluate(
                                "%s.%s" % (prim_path, curve_name),
                                self._key_times[i] / prim.GetStage().GetTimeCodesPerSecond(),
                            )
                            if evaluate_value is not None:
                                evaluate_value = utils.get_curve_plugin().convert_to_attr_precision(
                                    attr.GetPath().pathString, evaluate_value
                                )

                            if evaluate_value is None or isinstance(attr_value, str):
                                # New Key, or Token typed attribute
                                preserve_shape = False
                            elif math.isclose(evaluate_value, attr_value):
                                pass
                                # attr_value = evaluate_value  # over-write the attr_value to the exact value, in order to better preserve the shape
                            else:
                                carb.log_info("attr_value != evaluate_value, will set `preserve_shape` to False")
                                preserve_shape = False

                        utils.add_key(
                            prim,
                            curve_path,
                            self._key_times[i],
                            attr_value,
                            self._in_tangent_type,
                            self._out_tangent_type,
                            self._broken_tangent,
                            preserve_shape,
                        )

        self._usd_undo = usd_undo
        return True


class RemoveAnimCurveKeys(AnimCurveCommandBase):
    """
    Remove a list of keys from specificed curves(names)
    @param
        paths:  is a list of string-typed USD paths. Each path can be one of three types
                1) curves names path,  only remove keys in these curves      e.g. /World/Cube.xformOp:translate|x
                2) prims' path, remove keys from all animation curves of this prim  e.g. /World/Cube
                3) None,  remove keys from all curves of all the SELECTED prims
                The default value is None
        stage:  the USD stage of those USD paths resides in
        time:   UsdTimeCode, usually equal to the frame number as the index of the key. None to use the current time
    @return
        Return True if we successfully remove any keys and there is no errors
        Return False if no keys is removed or there are errors generated
    @example
        RemoveAnimCurveKeys(stage=stage, paths=["/World/Cube.xformOp:translate|x", "/World/Sphere.radius"], time=Usd.TimeCode(20.0))
        RemoveAnimCurveKeys(stage=stage, paths=["/World/Cube.size|x"], time=Usd.TimeCode(20.0))
        RemoveAnimCurveKeys(stage=stage, paths=["/World/Cube.xformOp:translate"], time=Usd.TimeCode(20.0))
        RemoveAnimCurveKeys(stage=stage, paths=["/World/Cube"])
        RemoveAnimCurveKeys(stage=stage, time=Usd.TimeCode(20.0))
        RemoveAnimCurveKeys(stage=stage)
    """

    def __init__(self, stage: Usd.Stage = None, paths: list = None, time: Usd.TimeCode = None):
        super().__init__(name="RemoveAnimCurveKeys", stage=stage, paths=paths, time=time)
        self._key_time = self._time

    def _do(self):
        usd_undo = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())

        if self._key_time == None:
            self._key_time = Usd.TimeCode(
                omni.timeline.get_timeline_interface().get_tentative_time() * self._stage.GetTimeCodesPerSecond()
            )

        settings = carb.settings.get_settings()
        delete_empty_curve = settings.get("/persistent/app/omni.anim.curve.core/deleteEmptyCurve")
        if delete_empty_curve is None:
            delete_empty_curve = True

        cached_path = set()
        result = True
        for path in self._paths:
            prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
            prim = self._stage.GetPrimAtPath(prim_path)
            if not prim:
                carb.log_error(f"RemoveAnimCurveKeys: Invalid input path {path}")
                continue

            animation_data_prim_path = self._get_animation_prim_path(prim)
            if animation_data_prim_path and animation_data_prim_path not in cached_path:
                cached_path.add(animation_data_prim_path)
                usd_undo.reserve(animation_data_prim_path)

            # Make property refresh
            def trigger_attr_change(attr):
                if not attr:
                    return

                global _is_authoring
                _is_authoring = True

                value = attr.Get()
                attr.ClearDefault()
                if value is not None:
                    attr.Set(value)

                _is_authoring = False

            if is_prim_path:
                if utils.has_anim(prim):
                    all_curves = utils.get_curves(prim)
                    if all_curves is not None:
                        for curve_name in all_curves:
                            ret = utils.delete_key(prim, curve_name, self._key_time, delete_empty_curve)
                            if ret:
                                attr_name = curve_name[:-2]  # curve name always contains a :x, :y, :z or :w postfix
                                attr = prim.GetAttribute(attr_name)
                                trigger_attr_change(attr)
                            result &= ret
                    else:
                        result &= False
            else:
                ret = False

                if is_comp_path:
                    curve_token = self._get_comp_attr_token(attr_token, comp_idx)
                    ret = utils.delete_key(prim, curve_token, self._key_time, delete_empty_curve)
                else:
                    curves = utils.get_curve_plugin().get_curves(prim_path.pathString)
                    for name, curve in curves.items():
                        if name[:-2] == attr_token:
                            ok = utils.delete_key(prim, name, self._key_time, delete_empty_curve)
                            ret = ret or ok

                if ret:
                    attr = prim.GetAttribute(attr_token)
                    trigger_attr_change(attr)

                result &= ret

        self._usd_undo = usd_undo
        return result


class PasteAnimCurveKeys(AnimCurveCommandBase):
    """
    Paste the curvekey data in global clipboard to target paths
    @param
        paths:  1. curves' path,  only Paste keys in these curves         e.g. /World/Cube.xformOp:translate|x
                2. prims' path, Paste keys in all curves of this prim  e.g. /World/Cube
                3. None,  move keys in all curves of all the SELECTED prims
                The default value is None
                Don't allow prim path and curves path both exist in target list
        time:   time code for the earliest key to start pasting.
                The default value is None which means the current system time

    @return
        Return True if we successfully Paste the curve without any errors
        Return False if no curve is Paste or there are errors generated

    @description
        The Paste command will paste key set from the global clipboard to the target paths.
        Depending on the clipboard content, the paste can have different behavior.
            The special case is when the clipboard has only one curve's key copied. It will be broadcast
        copy to all target paths' curves if they are curve paths. If the target paths are prim typed,
        we will paste the curve to every prim with the same curve name, if applicable. This is useful
        for the copy & paste key from the property window.
            If the clipboard contains multiple curves, but all from a single prim, we can have a prim level's
        broadcast if the target paths are all prim typed. We will paste curves from the clipboard's single prim
        to all target paths. This is useful for animation timeline's copy and paste keys to multiple selected prims.
            In a more general case, where the clipboard contains multiple curves and the target paths contains
        multiple curve pths, we iterate through both of them and paste the curves/keys sequentially.
    @example
        PasteAnimCurveKeys(paths=["/World/Cube.xformOp:translate|x", "/World/Sphere.radius"])  #Paste two curves
        PasteAnimCurveKeys(paths=["/World/Cube.size|x"])               #Paste the specified curve
        PasteAnimCurveKeys(paths=["/World/Cube.xformOp:translate"])    #Paste three curves
        PasteAnimCurveKeys(paths=["/World/Cube"])                      #Paste all of its curves in this prim
        PasteAnimCurveKeys()                                           #Paste all curves of the selected prim
        PassteAnimCurveKeys(paths=["/World/Cube.size|x], time=Usd.TimeCode(15)) #Paste the key starting from frame 15
    """

    def __init__(self, stage: Usd.Stage = None, paths: list = None, time: Usd.TimeCode = None):
        super().__init__(name="PasteAnimCurveKeys", stage=stage, paths=paths, time=time)
        self._key_time = self._time

    def _sanity_checks_paths(self) -> bool:
        valid = super()._sanity_checks_paths()

        # Additional paths check. Do not allow mix match prim paths and attribute/component paths
        if valid:
            prev_is_prim_path = None
            prev_path = None
            for path in self._paths:
                prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
                if prev_is_prim_path is not None:
                    if is_prim_path != prev_is_prim_path:
                        carb.log_error(
                            f"PasteAnimCurveKeys: mixture of prim paths \
                            [{path if is_prim_path else prev_path }] and non-prim paths \
                            [{prev_path if is_prim_path else prev_path }]is not allowed!"
                        )
                        return False
                prev_is_prim_path = is_prim_path
                prev_path = path
            return valid

    def _do(self):

        usd_undo = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())
        cached_path = set()
        clipboard = get_curvekey_clipboard()
        src_prim_count = clipboard.get_prim_count()
        if src_prim_count < 1:
            return True
        time_offset = self._key_time - clipboard.timecode

        rtn_value = True
        # There is only one curve in the clipboard. This is a broadcast operation
        if clipboard.get_prim_count() == 1 and clipboard.get_curve_count(0) == 1:
            copied_curve = clipboard.get_curve_keys(0, 0)  # this is the only curve we have
            copied_curve_name = clipboard.get_curve_name(0, 0)
            if copied_curve is None or copied_curve_name is None:
                carb.log_error(f"PasteAnimCurveKeys: Invalid curvesin clipboard!")
                rtn_value = False
                return rtn_value
            for path_index, path in enumerate(self._paths):
                prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
                prim = self._stage.GetPrimAtPath(prim_path)
                if not prim.IsValid():
                    carb.log_error(f"PasteAnimCurveKeys: invlid target prim! {prim_path}")
                    rtn_value = False
                    continue
                # add animation on prim if not exist

                if not utils.has_anim(prim):
                    utils.add_anim(prim)
                    animation_data_prim_path = self._get_animation_prim_path(prim)
                    # the animationData prim is added under the graph, will not be remove by this command
                    cached_path.add(animation_data_prim_path)

                # get Animation Schema data
                animation_data_prim_path = self._get_animation_prim_path(prim)
                animation_data_prim = self._stage.GetPrimAtPath(animation_data_prim_path)
                if not animation_data_prim:
                    carb.log_warn(f"PasteAnimCurveKeys: no animation in prim!")
                    rtn_value = False
                    continue

                curve_api = AnimationSchema.AnimationCurveAPI(animation_data_prim)

                if animation_data_prim_path not in cached_path:
                    cached_path.add(animation_data_prim_path)
                    usd_undo.reserve(animation_data_prim_path)

                # for prim path, the copied cures to the prim to corresponding attributes
                if is_prim_path:
                    anim_curve = []
                    for key_data in copied_curve:
                        dst_key_dat = key_data
                        dst_time = (
                            dst_key_dat.time
                            + time_offset
                            / self._stage.GetTimeCodesPerSecond()
                            * utils.curve_plugin.get_ticks_per_second()
                        )
                        dst_key_dat.time = round(dst_time)
                        anim_curve.append(dst_key_dat)
                    utils.set_keys(prim, copied_curve_name, anim_curve)
                else:
                    # usecase: paste on the property window
                    if is_comp_path:
                        # paste in attribute comonent
                        curve_name = self._get_comp_attr_token(attr_token, comp_idx)

                        # use key value of first timecode
                        anim_curve = []
                        dst_keys = utils.convert_to_usd_keys(copied_curve)
                        for dst_key_dat in dst_keys:
                            dst_time = (
                                dst_key_dat.time
                                + time_offset
                                / self._stage.GetTimeCodesPerSecond()
                                * utils.curve_plugin.get_ticks_per_second()
                            )
                            dst_key_dat.time = round(dst_time)
                            anim_curve.append(dst_key_dat)
                        utils.set_keys(prim, curve_name, anim_curve)
                    else:
                        # usecase: copy a single channel and paste on a vector in the property window
                        for i in range(comp_length):
                            curve_name = self._get_comp_attr_token(attr_token, i)
                            # use key value of first timecode
                            anim_curve = []
                            dst_keys = utils.convert_to_usd_keys(copied_curve)
                            for dst_key_dat in dst_keys:
                                dst_time = (
                                    dst_key_dat.time
                                    + time_offset
                                    / self._stage.GetTimeCodesPerSecond()
                                    * utils.curve_plugin.get_ticks_per_second()
                                )
                                dst_key_dat.time = round(dst_time)
                                anim_curve.append(dst_key_dat)
                            utils.set_keys(prim, curve_name, anim_curve)
        else:
            prim_idx = 0
            curve_idx = 0
            for path_index, path in enumerate(self._paths):
                prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
                prim = self._stage.GetPrimAtPath(prim_path)
                if not prim.IsValid():
                    carb.log_error(f"PasteAnimCurveKeys: invlid target prim! {prim_path}")
                    rtn_value = False
                    continue
                # add animation on prim if not exist
                if not utils.has_anim(prim):
                    utils.add_anim(prim)
                    cached_path.add(self._get_animation_prim_path(prim))

                # get Animation Schema data
                animation_data_prim_path = self._get_animation_prim_path(prim)
                animation_data_prim = self._stage.GetPrimAtPath(animation_data_prim_path)
                if not animation_data_prim:
                    carb.log_warn(f"PasteAnimCurveKeys: no animation in prim!")
                    rtn_value = False
                    continue

                curve_api = AnimationSchema.AnimationCurveAPI(animation_data_prim)
                if animation_data_prim not in cached_path:
                    cached_path.add(animation_data_prim_path)
                    usd_undo.reserve(animation_data_prim_path)

                # if it is a prim path copy a prim's curves from the clipboard
                if is_prim_path:
                    current_prim_curves = clipboard.get_prim_curves(prim_idx)
                    for curve_name, curve_keys in current_prim_curves.items():
                        dst_keys = utils.convert_to_usd_keys(curve_keys)
                        key_set = []
                        for dst_key in dst_keys:
                            dst_time = dst_key.time + utils.time_code_to_key_time(prim, time_offset)
                            dst_key.time = round(dst_time)
                            key_set.append(dst_key)
                        utils.set_keys(prim, curve_name, key_set)
                    # when the clipboard only have one prim's curves
                    # and the target paths are all prim paths. it is a broadcast operation
                    if src_prim_count != 1:
                        prim_idx += 1
                    # We already reach the end of the clipboard
                    if prim_idx >= src_prim_count:
                        break

                else:
                    if is_comp_path:
                        curve_name = self._get_comp_attr_token(attr_token, comp_idx)
                        curve_keys = clipboard.get_curve_keys(prim_idx, curve_idx)
                        dst_keys = utils.convert_to_usd_keys(curve_keys)
                        key_set = []
                        for dst_key in dst_keys:
                            dst_time = (
                                dst_key.time
                                + time_offset
                                / self._stage.GetTimeCodesPerSecond()
                                * utils.curve_plugin.get_ticks_per_second()
                            )
                            dst_key.time = round(dst_time)
                            key_set.append(dst_key)
                        utils.set_keys(prim, curve_name, key_set)

                        curve_idx += 1
                        if curve_idx >= clipboard.get_curve_count(prim_idx):
                            curve_idx = 0
                            prim_idx += 1
                            # clipboard contains multiple curves but we are reaching the end
                            # e.g. we have two curves in clipboard but there are three target paths
                            if prim_idx >= src_prim_count:
                                break
                    else:
                        for i in range(comp_length):
                            curve_name = self._get_comp_attr_token(attr_token, i)
                            curve_keys = clipboard.get_curve_keys(prim_idx, curve_idx)
                            dst_keys = utils.convert_to_usd_keys(curve_keys)
                            key_set = []
                            for dst_key in dst_keys:
                                dst_time = (
                                    dst_key.time
                                    + time_offset
                                    / self._stage.GetTimeCodesPerSecond()
                                    * utils.curve_plugin.get_ticks_per_second()
                                )
                                dst_key.time = round(dst_time)
                                key_set.append(dst_key)
                            utils.set_keys(prim, curve_name, key_set)
                            curve_idx += 1
                            if curve_idx >= clipboard.get_curve_count(prim_idx):
                                curve_idx = 0
                                prim_idx += 1
                                # clipboard contains multiple curves but we are reaching the end
                                # e.g. we have two curves in clipboard but there are three target paths
                                if prim_idx >= src_prim_count:
                                    break

        self._usd_undo = usd_undo
        return rtn_value


class SetAnimCurveInfinityType(AnimCurveCommandBase):
    """
    Set the Infinity loop type for the specified curves
    @param
        paths:              1. curves' path,  only Paste keys in these curves         e.g. /World/Cube.xformOp:translate|x
                            2. prims' path, Paste keys in all curves of this prim  e.g. /World/Cube
                            3. None,  move keys in all curves of all the SELECTED prims
                               The default value is None
        is_post_infinity:   1. True:  set the post infinity type, i.e. how a curve loops after the last key
                            2. False: set the pre infinity type, i.e. how a curve loops before the first key
                            The default value is True
        infinity_type:      "constant", "cycle", "cycleRelative", "linear", "oscillate"

    @return
        Return True if we successfully Paste the curve without any errors
        Return False if no curve is Paste or there are errors generated
    @example
        SetAnimCurveInfinityType(paths=["/World/Cube.xformOp:translate|x", "/World/Sphere.radius"])  # Set post-inifnity for two curves to "constant"
        SetAnimCurveInfinityType(paths=["/World/Cube.size|x"])                                       #Set post-infinity for the attribute size's animation curve as "constant"
        SetAnimCurveInfinityType(paths=["/World/Cube.xformOp:translate"])                            #Set three curves's post-inifity type for a vector set them as "constant"
        SetAnimCurveInfinityType(paths=["/World/Cube"])                                              #Set all curves' post-infinity type for the Cube prim as "constant"
        SetAnimCurveInfinityType()                                                                   #Set all curves' post-infinity type for the selected prim as "constant"
        SetAnimCurveInfinityType(paths=["/World/Sphere.visibility"], is_post_infinity=False)         # Set the pre-infinity type for the visibility attribute's curve as "constant"
        SetAnimCurveInfinityType(paths=["/World/Sphere.visibility"], is_post_infinity=False, infinity_type="cycle") # Set the pre-infinity type for the visibility attribute's curve as "cylce"

    """

    def __init__(
        self, paths: list = None, is_post_infinity: bool = True, infinity_type: str = AnimationSchema.Tokens.constant
    ):
        super().__init__(name="SetAnimCurveInfinityType", paths=paths)

        if isinstance(is_post_infinity, bool):
            self._is_post_infinity = is_post_infinity
        else:
            self._is_post_infinity = True

        if isinstance(infinity_type, str):
            if infinity_type in [
                AnimationSchema.Tokens.constant,
                AnimationSchema.Tokens.cycle,
                AnimationSchema.Tokens.cycleRelative,
                AnimationSchema.Tokens.linear,
                AnimationSchema.Tokens.oscillate,
            ]:
                self._infinity_type = infinity_type
            else:
                self._infinity_type = AnimationSchema.Tokens.constant
        else:
            self._infinity_type = AnimationSchema.Tokens.constant

    def _do(self):

        usd_undo = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())
        cached_path = set()

        for path in self._paths:
            prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
            prim = self._stage.GetPrimAtPath(prim_path)

            # We won't set any infinity attribute to a target attribute which doesn't have any animation curve yet
            if not utils.has_anim(prim):
                continue

            animation_data_prim_path = self._get_animation_prim_path(prim)
            animation_data_prim = self._stage.GetPrimAtPath(animation_data_prim_path)
            if not animation_data_prim.IsValid():
                continue
            anim_curve_api = AnimationSchema.AnimationCurveAPI(animation_data_prim)
            if anim_curve_api is None:
                continue

            # TODO: we can only reserve the inifnity attribute path
            if animation_data_prim_path not in cached_path:
                usd_undo.reserve(animation_data_prim_path)
                cached_path.add(animation_data_prim_path)

            curve_names = []
            if is_prim_path:
                curve_names = utils.get_curves(prim)
            else:
                if is_comp_path:
                    curve_names = [self._get_comp_attr_token(attr_token, comp_idx)]
                else:
                    attr = prim.GetAttribute(attr_token)
                    attr_value_type = attr.GetTypeName()
                    comp_len = self._get_attr_dimension(attr_value_type)
                    for i in range(comp_len):
                        curve_names.append(self._get_comp_attr_token(attr_token, i))

            # API support full Attribute token, e.g. "xformOp:translate"
            # and component token, e.g. "xformOp:translate:x"
            pre_or_post_infinity = (
                AnimationSchema.Infinity.Post if self._is_post_infinity else AnimationSchema.Infinity.Pre
            )
            for curve_name in curve_names:
                anim_curve_api.SetInfinityType(curve_name, self._infinity_type, pre_or_post_infinity)

        self._usd_undo = usd_undo
        return True


# follow the pattern SetAnimCurveInfinityType
class SetAnimCurveDefaultTangentType(AnimCurveCommandBase):
    def __init__(self, paths: list = None, default_tangent_type: str = AnimationSchema.Tokens.auto_):
        super().__init__(name="SetAnimCurveDefaultTangentType", paths=paths)

        if isinstance(default_tangent_type, str):
            if default_tangent_type in [
                AnimationSchema.Tokens.auto_,
                AnimationSchema.Tokens.smooth,
                AnimationSchema.Tokens.flat,
                AnimationSchema.Tokens.fixed,
                AnimationSchema.Tokens.linear,
                AnimationSchema.Tokens.step,
            ]:
                self._default_tangent_type = default_tangent_type
            else:
                self._default_tangent_type = AnimationSchema.Tokens.auto_
        else:
            self._default_tangent_type = AnimationSchema.Tokens.auto_

    def _do(self):

        usd_undo = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())
        cached_path = set()

        for path in self._paths:
            prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
            prim = self._stage.GetPrimAtPath(prim_path)

            # We won't set any default tangent type attribute to a target attribute which doesn't have any animation curve yet
            if not utils.has_anim(prim):
                continue

            animation_data_prim_path = self._get_animation_prim_path(prim)
            animation_data_prim = self._stage.GetPrimAtPath(animation_data_prim_path)
            if not animation_data_prim.IsValid():
                continue
            anim_curve_api = AnimationSchema.AnimationCurveAPI(animation_data_prim)
            if anim_curve_api is None:
                continue

            # TODO: we can only reserve the attribute path
            if animation_data_prim_path not in cached_path:
                usd_undo.reserve(animation_data_prim_path)
                cached_path.add(animation_data_prim_path)

            curve_names = []
            if is_prim_path:
                curve_names = utils.get_curves(prim)
            else:
                if is_comp_path:
                    curve_names = [self._get_comp_attr_token(attr_token, comp_idx)]
                else:
                    attr = prim.GetAttribute(attr_token)
                    attr_value_type = attr.GetTypeName()
                    comp_len = self._get_attr_dimension(attr_value_type)
                    for i in range(comp_len):
                        curve_names.append(self._get_comp_attr_token(attr_token, i))

            # API support full Attribute token, e.g. "xformOp:translate"
            # and component token, e.g. "xformOp:translate:x"
            for curve_name in curve_names:
                anim_curve_api.SetDefaultTangentType(curve_name, self._default_tangent_type)

        self._usd_undo = usd_undo
        return True


class PasteAnimCurves(AnimCurveCommandBase):
    def __init__(self, listSchemaKeys: list, dstCurvePath):
        super().__init__(name="PasteAnimCurves", paths=dstCurvePath)

        # basic sanity check for the user input type
        if isinstance(listSchemaKeys, list) and len(listSchemaKeys) == 4:
            self._list_schema_keys = listSchemaKeys
        else:
            # we don't accept non-list input
            self._list_schema_keys = [[], [], [], []]

    def _do(self):
        usd_undo = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())

        for path in self._paths:
            prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = self._parse_path(path)
            prim = self._stage.GetPrimAtPath(prim_path)
            if not utils.has_anim(prim):
                utils.add_anim(prim)
                animation_data_prim_path = self._get_animation_prim_path(prim)
            else:
                animation_data_prim_path = self._get_animation_prim_path(prim)
                usd_undo.reserve(animation_data_prim_path)

            data_prim = self._stage.GetPrimAtPath(animation_data_prim_path)

            if is_comp_path:
                component_indices = [comp_idx]
            else:
                # every component should be copied
                component_indices = range(comp_length)

            schema_anim_data = AnimationSchema.AnimationData(data_prim)
            for i in component_indices:
                attr_component_token = self._get_comp_attr_token(attr_token, i)

                utils.set_keys(prim=prim, curve_name=attr_component_token, keys=self._list_schema_keys[i])

        return True


class SelectAnimCurveKeys(AnimCurveCommandBase):
    """
    Similar to how we work with the selection list for prims in Kit, we need similar capability in the context
    of animation keyframes.  Keyframe (and their tangents) selection is application wide and all commands are
    aware of it.  For example, users can select keys programmablely and then use the EditAnimCurveKey command
    to edit the selected keysframe(and their tangents).  The selection can go to a global selection clipboard,
    or a user supplied buffer.

    @param
        paths:          A list of path strings to specify the curves
                        1. Attribute Paths,  only the keys/tangents from their animation curves will be selected.
                            If the attributes is a vector, the paths element could be a channel-typed path,
                                e.g. xformOp:translate|x,
                            or a vector-typed path,
                                e.g. xformOp:translate,
                            which includes all three curves.
                        2. Prim path, keys/tangents from all animation curves associated with all attributes
                            from these prims will be considered
                        3. None,  All keys/tangents from all animation curves from selected prims in the stage will be considered
                        4. The default value is None
        operation:      1. "replace":  replace the previous selection
                        2. "add":      incremental selection
                        3. “remove”:   remove the selection from the original list
                        4. "clear":    clear all the selections from the clipboard or the user buffer
                        The default value is "replace"
        indices:        Can be an integer or list of integers identifying key indices in the considered
                        animation curves (see argument path). The default is None.
        times:          1. A float value: only keys/tangents at this time will be considered.
                        2. A tuple2 of float:  for example (10, 20)) - only keys/tangents within that range, including, will be considered.
                        3. Can be set to a list of tuple2 for multiple ranges.
                        4. None. the current animation time will be used
                        5. The default is None
        key:            A boolean flag, select the key or not. The default is True
        in_tangent:     A boolean flag, select the incoming tangent or not. The default is True
        out_tangent:     A boolean flag, select the out going tangent or not. The default is True
        selection_state: A KeySelectionState typed user defined buffer to hold the selection state.
                         if None, which is the default, the selection state goes to a system global selection clipboard
    """

    class Operation:
        replace = "replace"
        remove = "remove"
        add = "add"
        clear = "clear"

    def __init__(
        self,
        paths: Union[str, List[str]] = None,
        operation=Operation.replace,
        indices: Union[int, List[int]] = None,
        times: Union[float, Tuple[float, float], List[Union[float, Tuple[float, float]]]] = None,
        key: bool = True,
        in_tangent: bool = True,
        out_tangent: bool = True,
        selection_state: KeySelectionState = None,
    ):
        self._paths = paths
        self._operation = operation
        self._indices = indices
        self._times = times
        self._key = key
        self._in_tangent = in_tangent
        self._out_tangent = out_tangent
        self._selection_state = selection_state
        self._prev_selection_state = None

        self._input_is_valid = True

    def _pump_event(self):
        if self._selection_state is not KeySelectionState.global_instance:
            return

        event_stream = utils.curve_plugin.get_event_stream()
        event_stream.push(
            CurveEventType.KeySelectionChanged, payload={"paths": []}
        )  # Uses the same payload as other events for simplicity
        event_stream.pump()

    def _do(self):
        if self._selection_state is None:
            self._selection_state = KeySelectionState.global_instance

        self._prev_selection_state = KeySelectionState()
        self._prev_selection_state.replace(self._selection_state)

        if self._operation == self.Operation.clear:
            self._selection_state.replace(KeySelectionState())
            self._pump_event()
            return

        paths = []

        if self._paths is None:
            paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        elif isinstance(self._paths, str):
            paths.append(self._paths)
        else:
            paths = self._paths

        selection_state = KeySelectionState()

        if self._times is None:
            timeline = omni.timeline.get_timeline_interface()
            self._times = timeline.get_current_time() * timeline.get_time_codes_per_seconds()

        for path in paths:
            prim_path = None
            attr_name = None
            comps = None

            tokens = path.split("|", 2)

            path = Sdf.Path(tokens[0])
            prim_path = path.GetPrimPath()
            if path.IsPropertyPath():
                attr_name = path.name

            if len(tokens) >= 2:
                comps = tokens[1]

            curves = utils.curve_plugin.get_curves(str(prim_path))
            for curve_name, curve in curves.items():
                select = False

                if attr_name is None:
                    select = True
                elif curve_name[:-2] != attr_name:
                    continue

                if comps is None:
                    select = True
                elif curve_name[-1][0] in comps:
                    select = True

                if select:
                    keys = self._select_keys(curve.keys)
                    curve_selection_state = KeySelectionState(str(path.GetPrimPath()) + "." + curve_name, keys)
                    selection_state.add(curve_selection_state)

        if self._operation == self.Operation.replace:
            self._selection_state.replace(selection_state)
            self._pump_event()
        elif self._operation == self.Operation.remove:
            self._selection_state.remove(selection_state)
            self._pump_event()
        elif self._operation == self.Operation.add:
            self._selection_state.add(selection_state)
            self._pump_event()

    def undo(self):
        if self._prev_selection_state is not None:
            self._selection_state.replace(self._prev_selection_state)
            self._pump_event()

    def _select_keys(self, keys):
        selected_keys = {}
        tcps = omni.usd.get_context().get_stage().GetTimeCodesPerSecond()
        for i in range(0, len(keys)):
            select = False
            if self._indices is not None:
                if hasattr(self._indices, "__iter__"):
                    if i in self._indices:
                        select = True
                elif i == self._indices:
                    select = True

            if self._times is not None and not select:
                times = []
                if not isinstance(self._times, list):
                    times.append(self._times)

                for time in times:
                    if isinstance(time, tuple):
                        begin = round(time[0] / tcps * AnimationSchema.AnimationCurveAPI.GetTicksPerSecond())
                        end = round(time[1] / tcps * AnimationSchema.AnimationCurveAPI.GetTicksPerSecond())
                        if keys[i].time >= begin and keys[i].time <= end:
                            select = True
                    elif keys[i].time == round(time / tcps * AnimationSchema.AnimationCurveAPI.GetTicksPerSecond()):
                        select = True

            if self._indices is None and self._times is None:
                select = True

            if select:
                selected_keys[keys[i].time] = KeySelectionState.SelectFlag(
                    self._key, self._in_tangent, self._out_tangent
                )

        return selected_keys


class EditAnimCurveKeys(AnimCurveCommandBase):
    """
    Edit selected keyframes/tangents.

    @param
        selection_state: A KeySelectionState typed user defined buffer to hold the selection state.
                        if None, which is the default, the selection state goes to a system global selection clipboard
        time:           1. A float value: only keys/tangents at this time will be considered.
                        2. None. Keeps time of keys/tangents not touched.
                        3. The default is None
        value:          A float value of keys/tangents that you want to set to keys. Default is None, which means values are not touched.
        additive :      A boolean flag to toggle whether to override times/values of the considered keys/tangents or
                        add to them the specified ones by arguments time and value.
                        The default value is False
        tangent_broken: A boolean flag which is the value of the tangent broken component of the keyframe
                        The default is None, which means to keep the component untouched
        tangent_type:   A string to set the tangent type component, possible values are
                        "auto", "smooth", "linear", "step", "fixed".
                        The default is None, which means to keep the component untouched
        tangent_weighted:  A boolean flag which is the value of the weighted tangent component of the keyframe
                            The default is None, which means to keep the component untouched

    """

    def __init__(
        self,
        selection_state: KeySelectionState = None,
        time=None,
        value=None,
        additive=False,
        tangent_broken: bool = None,
        tangent_type: str = None,
        tangent_weighted: bool = None,
    ):
        self._input_is_valid = True
        self._selection_state = selection_state
        self._time = time
        self._value = value
        self._additive = additive
        self._tangent_broken = tangent_broken
        self._tangent_type = tangent_type
        self._tangent_weighted = tangent_weighted
        self._moved_keys = {}

    def _do(self):
        stage = omni.usd.get_context().get_stage()
        usd_undo = UsdLayerUndo(stage.GetEditTarget().GetLayer())

        if self._selection_state is None:
            self._selection_state = KeySelectionState.global_instance

        time = None
        if self._time is not None:
            time = round(
                self._time / stage.GetTimeCodesPerSecond() * AnimationSchema.AnimationCurveAPI.GetTicksPerSecond()
            )

        for curve_path, select_keys in self._selection_state.curves.items():
            path = Sdf.Path(curve_path)
            curves = utils.curve_plugin.get_curves(str(path.GetPrimPath()))
            curve = curves[path.name]

            moved_select_keys = {}
            moved_keys = []

            keys = utils.convert_to_usd_keys(curve.keys)

            for key in keys:
                select_key = select_keys.get(key.time)
                if select_key is None:
                    continue

                def edit_time_value(tgt):
                    if time is not None:
                        if self._additive:
                            tgt.time += time
                        else:
                            tgt.time = time

                    if self._value is not None:
                        if self._additive:
                            tgt.value += self._value
                        else:
                            tgt.value = self._value

                def edit_tangent_type(tangent):
                    if self._tangent_type is not None:
                        tangent.type = self._tangent_type

                if select_key.key:
                    old_key_time = key.time
                    edit_time_value(key)

                    if key.time != old_key_time:
                        moved_keys.append((old_key_time, key.time))

                    if self._tangent_broken is not None:
                        key.tangentBroken = self._tangent_broken

                    if self._tangent_weighted is not None:
                        key.tangentWeighted = self._tangent_weighted

                if select_key.in_tangent:
                    if not select_key.key:
                        edit_time_value(key.inTangent)
                    edit_tangent_type(key.inTangent)

                if select_key.out_tangent:
                    if not select_key.key:
                        edit_time_value(key.outTangent)
                    edit_tangent_type(key.outTangent)

            KeySelectionState.on_keys_changed(curve_path, moved_keys, [])
            self._moved_keys[curve_path] = moved_keys
            KeySelectionState.ignore_curve_event = True

            curve_api = AnimationSchema.AnimationCurveAPI.Get(stage, Sdf.Path(curve.anim_data))
            usd_undo.reserve(curve_api.GetPath())
            curve_api.SetKeys(path.name, keys)

            KeySelectionState.ignore_curve_event = False

        self._usd_undo = usd_undo

    def undo(self) -> None:

        KeySelectionState.ignore_curve_event = True

        super().undo()

        for curve, keys in self._moved_keys.items():
            undo_moved = []
            for old, new in keys:
                undo_moved.append((new, old))

            KeySelectionState.on_keys_changed(curve, undo_moved, [])

        KeySelectionState.ignore_curve_event = False


class ExtractAnimCurves(AnimCurveCommandBase):
    """
    Converts dense key data to curve data
    @param
        paths:  1. attributes' path, e.g. /World/Cube.xformOp:translate
                2. prims' path, e.g. /World/Cube

        recursive:
                If True, for prim every prim path in paths extract all curves recursively for children

        attribute_mask: Only attributes that contain this string are processed

        source_frame_rate:
                Source frame rate (time samples per seconds), or zero to use the current frame rate

        start_time:
                Start time of the output curve (in seconds)

        sparse:
                Apply curve simplification to reduce the number of keys

        max_error_percent:
                Maximum allowed error for each removed key, as percentage of curve value range (approximate)

        compute_tangents:
                When 'sparse' is set, compute the tangents of the sparse curve from the dense samples

    @example
        ExtractAnimCurves(paths=["/World/Cube.xformOp:translate", "/World/Sphere.visibility"])  # Extracts two attributes
        ExtractAnimCurves(paths=["/World"], recursive=True)            # Extracts all attributes on all prims under /World
        ExtractAnimCurves(paths=["/World/Cube.xformOp:translate|x"])   # Error: components are not supported
        ExtractAnimCurves()                                            # Extracts all curves of the selected prim
    """

    def __init__(
        self,
        stage: Usd.Stage = None,
        paths: list = None,
        recursive: bool = False,
        attribute_mask=None,
        source_frame_rate: float = 0.0,
        start_time: float = 0.0,
        sparse: bool = False,
        max_error_percent=0.1,
        compute_tangents=False,
    ):
        super().__init__(name="ExtractAnimCurves", stage=stage, paths=paths)
        self._recursive = recursive
        self._attribute_mask = attribute_mask
        self._source_frame_rate = source_frame_rate
        self._start_time = start_time
        self._sparse = sparse
        self._max_error_percent = max_error_percent
        self._compute_tangents = compute_tangents
        self._settings = carb.settings.acquire_settings_interface()

    @staticmethod
    def _mask_match(input: str, mask: str) -> bool:
        return mask is None or mask in input

    def _do(self):
        self._usd_undo_old = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())
        self._extract(self._paths)
        self._usd_undo = self._usd_undo_old

        return True

    def _convert_value(self, attr_token, value):
        if "visibility" in attr_token:
            if "inherited" in value:
                return 0
            else:
                return 1
        else:
            return value

    def _is_orthogonal(self, matrix: Union[Gf.Matrix4d, Gf.Matrix4f]) -> bool:
        eps = 0.00001
        return (
            abs(Gf.Dot(matrix.GetColumn(0), matrix.GetColumn(1))) < eps
            and abs(Gf.Dot(matrix.GetColumn(0), matrix.GetColumn(2))) < eps
            and abs(Gf.Dot(matrix.GetColumn(1), matrix.GetColumn(2))) < eps
        )

    def _rotation_to_euler(self, rotation: Gf.Rotation, order: str) -> Gf.Vec3d:
        rotation_euler = Gf.Vec3d()
        if not order.startswith("rotate"):
            order = "rotate" + order
        if UsdGeom.XformOpTypes.rotateXYZ == order:
            rotation_euler = rotation.Decompose(Gf.Vec3d.ZAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.XAxis())
            rotation_euler = Gf.Vec3d(rotation_euler[2], rotation_euler[1], rotation_euler[0])
        elif UsdGeom.XformOpTypes.rotateXZY == order:
            rotation_euler = rotation.Decompose(Gf.Vec3d.YAxis(), Gf.Vec3d.ZAxis(), Gf.Vec3d.XAxis())
            rotation_euler = Gf.Vec3d(rotation_euler[2], rotation_euler[0], rotation_euler[1])
        elif UsdGeom.XformOpTypes.rotateYXZ == order:
            rotation_euler = rotation.Decompose(Gf.Vec3d.ZAxis(), Gf.Vec3d.XAxis(), Gf.Vec3d.YAxis())
            rotation_euler = Gf.Vec3d(rotation_euler[1], rotation_euler[2], rotation_euler[0])
        elif UsdGeom.XformOpTypes.rotateYZX == order:
            rotation_euler = rotation.Decompose(Gf.Vec3d.XAxis(), Gf.Vec3d.ZAxis(), Gf.Vec3d.YAxis())
            rotation_euler = Gf.Vec3d(rotation_euler[0], rotation_euler[2], rotation_euler[1])
        elif UsdGeom.XformOpTypes.rotateZXY == order:
            rotation_euler = rotation.Decompose(Gf.Vec3d.YAxis(), Gf.Vec3d.XAxis(), Gf.Vec3d.ZAxis())
            rotation_euler = Gf.Vec3d(rotation_euler[1], rotation_euler[0], rotation_euler[2])
        elif UsdGeom.XformOpTypes.rotateZYX == order:
            rotation_euler = rotation.Decompose(Gf.Vec3d.XAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.ZAxis())
            rotation_euler = Gf.Vec3d(rotation_euler[0], rotation_euler[1], rotation_euler[2])
        return rotation_euler

    def _set_precision(self, vec: Union[Gf.Vec3d, Gf.Vec3f, Gf.Vec3h], precision):
        if precision == "Double":
            return Gf.Vec3d(vec[0], vec[1], vec[2])
        elif precision == "Float":
            return Gf.Vec3f(vec[0], vec[1], vec[2])
        elif precision == "Half":
            return Gf.Vec3h(vec[0], vec[1], vec[2])
        return vec

    def _extract_TRS_from_matrix(self, prim: Usd.Prim, attribute: Usd.Attribute) -> Dict[str, List[Tuple[float, Any]]]:
        assert attribute.GetNumTimeSamples() >= 1  # this needs to be checked by the caller
        s = attribute.GetName()
        precision = self._settings.get("/persistent/app/primCreation/DefaultXformOpPrecision")
        rotation_order = self._settings.get("/persistent/app/primCreation/DefaultRotationOrder")
        if rotation_order is None:
            rotation_order = "XYZ"
        # remove last part of name with ':' splitting, e.g. 'xformOp:transform' -> 'xformOp'
        name_prefix = s.removesuffix(":" + s.split(":")[-1]) if ":" in s else s
        translate_name = name_prefix + ":" + "translate"
        rotate_name = name_prefix + ":" + "rotate" + rotation_order
        scale_name = name_prefix + ":" + "scale"
        had_translation = prim.HasAttribute(translate_name)
        had_rotation = prim.HasAttribute(rotate_name)
        had_scale = prim.HasAttribute(scale_name)
        out_attributes = {}
        if had_translation and had_rotation and had_scale:
            # just use the existing data, ignore transform
            return out_attributes
        attr_path = attribute.GetPath()
        carb.log_info(f"{self._name}: extracting translation, rotation, scale from matrix attribute {attr_path}.")
        UsdGeom.Xformable(prim).ClearXformOpOrder()
        if not had_translation:
            translation_attr: Usd.Attribute = UsdGeom.Xformable(prim).AddTranslateOp()
            out_attributes[translate_name] = []
        if not had_rotation:
            if rotation_order == "XYZ":
                rotation_attr: Usd.Attribute = UsdGeom.Xformable(prim).AddRotateXYZOp()
            elif rotation_order == "XZY":
                rotation_attr: Usd.Attribute = UsdGeom.Xformable(prim).AddRotateXZYOp()
            elif rotation_order == "YXZ":
                rotation_attr: Usd.Attribute = UsdGeom.Xformable(prim).AddRotateYXZOp()
            elif rotation_order == "YZX":
                rotation_attr: Usd.Attribute = UsdGeom.Xformable(prim).AddRotateYZXOp()
            elif rotation_order == "ZXY":
                rotation_attr: Usd.Attribute = UsdGeom.Xformable(prim).AddRotateZXYOp()
            elif rotation_order == "ZYX":
                rotation_attr: Usd.Attribute = UsdGeom.Xformable(prim).AddRotateZYXOp()
            out_attributes[rotate_name] = []
        if not had_scale:
            scale_attr: Usd.Attribute = UsdGeom.Xformable(prim).AddScaleOp()
            out_attributes[scale_name] = []
        default_value = None
        for i, time in enumerate(attribute.GetTimeSamples()):
            time_code = Usd.TimeCode(time)
            matrix: Gf.Matrix4d = attribute.Get(time=time_code)
            if not had_translation:
                translation = matrix.ExtractTranslation()
                translation = self._set_precision(translation, precision)
                out_attributes[translate_name].append((time, translation))
                if i == 0:
                    translation_attr.Set(translation)  # default value
            rotation_mat = matrix.ExtractRotationMatrix()
            if not self._is_orthogonal(rotation_mat):  # rotation matrices are always orthogonal
                carb.log_warn(
                    f"{self._name}: matrix sample at attribute {s}, time {time} has shearing, rotation will be inaccurate"
                )
            if not had_rotation:
                rotation_rot = rotation_mat.GetOrthonormalized().ExtractRotation()
                rotation_euler = self._rotation_to_euler(rotation_rot, rotation_order)
                rotation_euler = self._set_precision(rotation_euler, precision)
                out_attributes[rotate_name].append((time, rotation_euler))
                if i == 0:
                    rotation_attr.Set(rotation_euler)  # default value
            if not had_scale:
                scale = Gf.Vec3d(
                    rotation_mat.GetColumn(0).GetLength(),
                    rotation_mat.GetColumn(1).GetLength(),
                    rotation_mat.GetColumn(2).GetLength(),
                )
                scale = self._set_precision(scale, precision)
                out_attributes[scale_name].append((time, scale))
                if i == 0:
                    scale_attr.Set(scale)  # default value
            if i == 0:
                default_value = (time_code, matrix)

        return out_attributes

    def _extract(self, in_path, in_samples_values=None):
        from .simplication_utils import CurveSimplifier, KeyData
        from .utils import resample_times

        for i_path, path in enumerate(in_path):
            path_parsed = self._parse_path(path)

            if path_parsed is not None:
                prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = path_parsed

                prim = self._stage.GetPrimAtPath(prim_path)
                if not prim.IsValid():
                    carb.log_error(f"ExtractAnimCurves: {prim_path} is not a valid prim path.")
                    continue

                if is_prim_path:
                    if self._recursive:
                        child_paths = []
                        for child in prim.GetAllChildren():
                            name_skip = "animationData"  # it is a special prim that contains animation curve data
                            child_path = str(child.GetPath())
                            if len(child_path) < len(name_skip) or child_path[-len(name_skip) :] != name_skip:
                                child_paths.append(child_path)
                        if len(child_paths) > 0:
                            self._extract(child_paths)

                    new_attributes = {}
                    for attribute in prim.GetAttributes():
                        if attribute.GetNumTimeSamples() >= 1:
                            attribute_name = str(attribute.GetName())
                            attr_path = path + "." + attribute_name
                            if not ExtractAnimCurves._mask_match(attribute_name, self._attribute_mask):
                                continue
                            if utils.get_curve_plugin().is_attr_supported(attr_path):
                                utils.add_curve_and_anim(self._stage, prim, str(prim_path), attribute_name)
                                self._extract([attr_path])
                            elif attribute_name == "xformOp:transform":
                                new_attributes.update(self._extract_TRS_from_matrix(prim, attribute))
                    for attribute_name, samples in new_attributes.items():
                        attribute = prim.GetAttribute(attribute_name)
                        attr_path = path + "." + attribute_name
                        utils.add_curve_and_anim(self._stage, prim, str(prim_path), attribute_name)
                        self._extract([attr_path], [samples])
                elif is_comp_path:
                    carb.log_error(f"ExtractAnimCurves: component extraction is not supported ({path})")
                    continue
                else:  # attribute, but not a component
                    if not ExtractAnimCurves._mask_match(attr_token, self._attribute_mask):
                        continue

                    carb.log_info(f"ExtractAnimCurves: Converting time samples to curves in {prim_path}:{attr_token}")
                    keys = {"x": [], "y": [], "z": [], "w": []}
                    default_value = None
                    attribute = prim.GetAttribute(attr_token)
                    if not attribute.IsValid():
                        carb.log_error(f"ExtractAnimCurves: {attr_token} is not a valid attribute.")
                        continue

                    # NOTE: these are frame indices
                    values = None
                    if in_samples_values is not None and i_path < len(in_samples_values):
                        samples = [v[0] for v in in_samples_values[i_path]]
                        values = [v[1] for v in in_samples_values[i_path]]
                        if len(samples) != len(values):
                            carb.log_error(f"{self._name}: programming error, size mismatch in times and values")
                            continue
                    else:
                        samples = attribute.GetTimeSamples()
                    if len(samples) == 0:
                        continue

                    target_frame_rate = omni.timeline.get_timeline_interface().get_time_codes_per_seconds()
                    target_frame_offset = round(self._start_time * target_frame_rate)
                    if (
                        self._source_frame_rate is not None
                        and self._source_frame_rate != 0
                        and self._source_frame_rate != target_frame_rate
                    ):
                        samples = resample_times(samples, self._source_frame_rate, target_frame_rate, self._start_time)
                        target_frame_offset = 0  # so it is not added twice below
                    else:
                        samples = [(t, t) for t in samples]

                    # at this point each entry t in samples is a tuple
                    # - t[0] is the the float frame index of the sampling grid corresponding to the target frame rate
                    # - t[1] is the the target frame index
                    for i, t in enumerate(samples):
                        t_sample = t[0]
                        t_target = t[1] + target_frame_offset
                        if values is not None:
                            value = values[i]
                        else:
                            value = attribute.Get(time=Usd.TimeCode(t_sample))
                        if default_value is None:
                            default_value = value
                        if comp_length == 1:
                            keys["x"].append(KeyData(t_target, value, i))
                        elif comp_length > 1:
                            keys["x"].append(KeyData(t_target, value[0], i))
                            keys["y"].append(KeyData(t_target, value[1], i))
                            if comp_length > 2:
                                keys["z"].append(KeyData(t_target, value[2], i))
                            if comp_length > 3:
                                keys["w"].append((t_target, KeyData(t_target, value[3], i)))

                    self._usd_undo_old.reserve(attribute.GetPath())
                    attribute.Set(default_value)

                    components = ["x", "y", "z", "w"]
                    with Sdf.ChangeBlock(True):
                        for i in range(comp_length):
                            component = components[i]
                            curve_name = self._get_comp_attr_token(attr_token, i)

                            component_keys = keys[component]
                            if self._sparse:
                                import time

                                start = time.time()
                                key_count = len(component_keys)
                                simplifier = CurveSimplifier(self._max_error_percent)
                                component_keys = simplifier.simplify_keys(
                                    component_keys, attr_token, self._compute_tangents
                                )
                                end = time.time()
                                carb.log_info(
                                    "{}: curve simplification reduced key_count from {} to {} in {:.3f} seconds".format(
                                        self._name, key_count, len(component_keys), end - start
                                    )
                                )

                            converted_keys = []
                            for key in component_keys:
                                new_key = AnimationSchema.Key()
                                new_key.time = utils.time_code_to_key_time(prim, key.time)
                                new_key.value = self._convert_value(attr_token, key.value)
                                new_key.inTangent.type = "auto"
                                new_key.outTangent.type = "auto"
                                utils.set_tangent(prim, new_key, key.tangent)
                                converted_keys.append(new_key)
                            utils.set_keys_direct(prim, curve_name, converted_keys)


class SimplifyAnimCurves(AnimCurveCommandBase):
    """
    Simplifies a curve by removing keys
    @param
        paths:  1. components' path, e.g. /World/Cube.xformOp:rotateXYZ|x
                2. attributes' path, e.g. /World/Cube.xformOp:translate
                3. prims' path, e.g. /World/Cube

        attribute_mask:
                Only attributes that contain this string are processed

        max_error_percent:
                Maximum allowed error for each removed key, as percentage of curve value range (approximate)

        continuous_algorithm:
                Algorithm for to simplify curves with continuous data

        compute_tangents:
                True to compute tangents of the sparse curve from the input keys

    @example
        SimplifyAnimCurves(paths=["/World/Cube.xformOp:translate|x", "/World/Sphere.rotateXYZ|z"])  # Simplifies two components
        SimplifyAnimCurves(paths=["/World/Cube.xformOp:translate")     # Simplifies all components
        SimplifyAnimCurves(paths=["/World/Cube")                       # Simplifies all curves of a prim
        SimplifyAnimCurves()                                           # Simplifies all curves of the selected prim
        SimplifyAnimCurves(max_error_percent=10)                       # Simplifies curves with approx. 10% allowed error
    """

    def __init__(
        self,
        stage: Usd.Stage = None,
        paths: list = None,
        max_error_percent: float = 1,
        attribute_mask: str = None,
        continuous_algorithm: SimplificationAlgorithm = None,
        compute_tangents=True,
    ):
        super().__init__(name="SimplifyAnimCurves", stage=stage, paths=paths)
        self.attribute_mask = attribute_mask
        self.max_error_percent = max_error_percent
        self.continuous_algorithm = continuous_algorithm
        self.compute_tangents = compute_tangents

    def _do(self):
        self._usd_undo_old = UsdLayerUndo(self._stage.GetEditTarget().GetLayer())
        self._simplify(self._paths)
        self._usd_undo = self._usd_undo_old

        return True

    def _simplify(self, in_path):
        from .simplication_utils import CurveSimplifier, KeyData

        for path in in_path:
            path_parsed = self._parse_path(path)

            if path_parsed is not None:
                prim_path, attr_token, comp_length, comp_idx, is_prim_path, is_comp_path = path_parsed
                prim = self._stage.GetPrimAtPath(prim_path)
                if not prim.IsValid():
                    carb.log_error(f"SimplifyAnimCurves: {prim_path} is not a valid prim path.")
                    continue

                if is_prim_path:
                    if not utils.has_anim(prim):
                        continue

                    attribute_names = ["xformOp:rotateXYZ", "xformOp:translate", "xformOp:scale", "visibility"]
                    valid_attribute_paths = []
                    for attribute_name in attribute_names:
                        attribute = prim.GetAttribute(attribute_name)
                        if attribute.IsValid():
                            attribute_path = str(prim_path) + "." + attribute_name
                            valid_attribute_paths.append(attribute_path)

                    self._simplify(valid_attribute_paths)
                elif not is_comp_path:
                    if not ExtractAnimCurves._mask_match(attr_token, self.attribute_mask):
                        continue
                    comp_paths = []
                    for i in range(comp_length):
                        comp_paths.append(str(prim_path) + "." + self._get_comp_attr_path(attr_token, i))
                    self._simplify(comp_paths)
                else:
                    animation_data_prim_path = self._get_animation_prim_path(prim)
                    self._usd_undo_old.reserve(animation_data_prim_path)

                    curves = utils.get_curve_plugin().get_curves(str(prim_path))
                    curve_name = self._get_comp_attr_token(attr_token, comp_idx)
                    curve = curves.get(curve_name)
                    if curve is not None:
                        simplifier = CurveSimplifier(self.max_error_percent, self.continuous_algorithm)
                        all_keys = curve.keys
                        keys = []
                        for i in range(len(all_keys)):
                            time = utils.key_time_to_time_code(all_keys[i].time)
                            keys.append(KeyData(time, all_keys[i].value, i))
                        sparse_keys = simplifier.simplify_keys(keys, attr_token, self.compute_tangents)

                        converted_keys = []
                        for key in sparse_keys:
                            new_key = AnimationSchema.Key()
                            new_key.time = utils.time_code_to_key_time(prim, key.time)
                            new_key.value = key.value
                            new_key.inTangent.type = "auto"
                            new_key.outTangent.type = "auto"
                            utils.set_tangent(prim, new_key, key.tangent)
                            converted_keys.append(new_key)
                        utils.set_keys_direct(prim, curve_name, converted_keys)
