import weakref

import carb
import omni.graph.core as og
import omni.kit.commands
import omni.kit.undo
from omni.kit.usd_undo import *
from pxr import Gf

from .curve_editor import _CurveTangent
from .curve_editor_globals import *


# new curve general attribute, 1d or 2d or 3d or 4d
class NewAttributeCurveCommand(omni.kit.commands.Command):
    def __init__(self, prim_path: str, attr_name: str, components_quantity: int):
        self._attr_name = attr_name
        self._prim_path = prim_path
        if components_quantity > 0 and components_quantity <= 4:
            vec_types = [
                Sdf.ValueTypeNames.Double,
                Sdf.ValueTypeNames.Double2,
                Sdf.ValueTypeNames.Double3,
                Sdf.ValueTypeNames.Double4,
            ]
            default_values = [0, Gf.Vec2d(0, 0), Gf.Vec3d(0, 0, 0), Gf.Vec4d(0, 0, 0, 0)]
            component_index = components_quantity - 1
            self._type = vec_types[component_index]
            self._value = default_values[component_index]
        else:
            carb.log_error("Unexpected code path in NewAttributeCurveCommand.__init__()")
            self._type = Sdf.ValueTypeNames.Double
            self._value = 0

    def do(self):
        stage = omni.usd.get_context().get_stage()
        usd_undo = UsdLayerUndo(stage.GetEditTarget().GetLayer())
        usd_undo.reserve(self._prim_path)

        prim = stage.GetPrimAtPath(self._prim_path)

        if prim:
            # Must set value explicitly. Because by experiment, the type of attribute will return False by HasValue() after raw creation. This is the type's schema problem according to HasValue() USD document.
            prim.CreateAttribute(self._attr_name, self._type, False).Set(self._value)
        else:
            carb.log_warn("Unexpected code path in NewAttributeCurveCommand.do()")

        self._usd_undo = usd_undo

    def undo(self):
        if self._usd_undo is None:
            return
        self._usd_undo.undo()


# like a special case NewAttributeCurveCommand for timeline og node.
class NewTimelineNodeAttributeCurveCommand(omni.kit.commands.Command):
    def __init__(self, prim_path: str, attr_name: str, components_quantity: int):
        self._attr_name = attr_name
        self._prim_path = prim_path
        default_values = [0, Gf.Vec2d(0, 0), Gf.Vec3d(0, 0, 0), Gf.Vec4d(0, 0, 0, 0)]
        if components_quantity > 0 and components_quantity <= 4:
            self._type = og.Type(og.BaseDataType.DOUBLE, components_quantity, 0, og.AttributeRole.NONE)
            component_index = components_quantity - 1
            self._value = default_values[component_index]
        else:
            carb.log_error("Unexpected code path in NewTimelineNodeAttributeCurveCommand.__init__()")
            self._type = og.Type(og.BaseDataType.DOUBLE, 1, 0, og.AttributeRole.NONE)
            self._value = 0

    def do(self):
        stage = omni.usd.get_context().get_stage()
        usd_undo = UsdLayerUndo(stage.GetEditTarget().GetLayer())
        usd_undo.reserve(self._prim_path)

        prim = stage.GetPrimAtPath(self._prim_path)

        if is_timeline_node(prim):
            # create port and relevant internal usd attribute.
            helper = og.Controller()
            # it is not usd attribute. usd attribute is prim.GetAttribute(attr.get_name()) not prim.GetAttribute(self._attr_name).
            attr = helper.create_attribute(
                self._prim_path,
                self._attr_name,
                self._type,
                og.AttributePortType.ATTRIBUTE_PORT_TYPE_OUTPUT,
                attr_default=self._value,  # temptest. it is not effective, do not know why yet.
            )
        else:
            carb.log_warn("Unexpected code path in NewTimelineNodeAttributeCurveCommand.do()")

        self._usd_undo = usd_undo

    def undo(self):
        if self._usd_undo is None:
            return
        self._usd_undo.undo()
