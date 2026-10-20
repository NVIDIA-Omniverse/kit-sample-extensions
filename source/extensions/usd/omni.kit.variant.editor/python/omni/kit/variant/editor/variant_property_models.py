# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import copy
import functools
import weakref
from typing import List

import carb
import omni
import omni.kit.notification_manager as nm
import omni.kit.usd.layers as layers
import omni.timeline
import omni.ui as ui
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.app import queue_event, register_event_alias
from omni.kit.property.usd.control_state_manager import ControlStateManager
from omni.kit.property.usd.relationship import RelationshipTargetPicker
from omni.kit.property.usd.usd_attribute_model import SdfAssetPathAttributeModel
from omni.kit.property.usd.usd_model_base import UsdBase
from omni.kit.property.usd.usd_object_model import MetadataObjectModel
from pxr import Ar, Gf, Sdf, Tf, Trace, Usd, UsdShade

from .core import VariantEditorCore
from .placeholder_attribute import PlaceholderAttribute

VARIANT_CHANGED_EVENT = carb.events.type_from_string("omni.kit.variant.editor.VariantChanged")
GLOBAL_VARIANT_CHANGED_EVENT = "omni.kit.variant.editor.VariantChanged"
register_event_alias(VARIANT_CHANGED_EVENT, GLOBAL_VARIANT_CHANGED_EVENT)

try:
    from omni.kit.usd.layers import layer_event_name

    _is_legacy_layer_event = False
except ImportError:
    _is_legacy_layer_event = True

# OMPE-57990: timeline events is updated to Events 2.0 in 108.2 so here try to add transition code to accommodate both
_is_legacy_timeline = not hasattr(omni.timeline, "GLOBAL_EVENT_CURRENT_TIME_TICKED")


# Custom Class to Override Property Model Functions in an effort to write less local opinions
class UsdVariant:
    def __init__(
        self,
        stage: Usd.Stage,
        object_paths: List[Sdf.Path],
        self_refresh: bool,
        metadata: dict = {},
        change_on_edit_end: bool = False,
        treat_array_entry_as_comp: bool = False,
        **kwargs,
    ):

        self.__editor_core = VariantEditorCore.get_instance()
        self._control_state_mgr = ControlStateManager.get_instance()
        self._stage = stage
        self._usd_context = None
        self._object_paths = object_paths
        self._object_paths_set = set(object_paths)
        self._metadata = metadata
        self._change_on_edit_end = change_on_edit_end
        # Whether each array entry should be treated as a comp, if this property is of an array type.
        # If set to True, each array entry will have ambiguous and different from default state checked. It may have
        # huge perf impact if the array size is big.
        # It is useful if you need to build each array entry as a single widget with mixed/non-default indicator
        # an example would SdfAssetPathAttributeModel and _sdf_asset_path_array_builder
        self._treat_array_entry_as_comp = treat_array_entry_as_comp
        self._dirty = True
        self._value = None  # The value to be displayed on widget
        self._has_default_value = False
        self._default_value = None
        self._real_values = []
        self._connections = []
        self._is_big_array = False
        self._prev_value = None
        self._prev_real_values = []
        self._editing = 0
        self._ignore_notice = False
        self._ambiguous = False
        # "comp" is the first dimension of an array (when treat_array_entry_as_comp is enabled) or vector attribute.
        # - If attribute is non-array vector type, comp indexes into the vector itself. e.g. for vec3 type, comp=1 means
        #   the 2nd channel of the vector vec3[1].
        # - If attribute is an array type:
        #   - When treat_array_entry_as_comp is enabled) is enabled:
        #       - If the attribute is an array of scalar (i.e. float[]), `comp`` is the entry index. e.g. for
        #         SdfAssetArray type, comp=1 means the 2nd path in the path array.
        #       - If the attribute is an array of vector (i.e. vec3f[]), `comp` only indexes the array entry, it does
        #         not support indexing into the channel of the vector within the array entry. i.e a "2D" comp is not
        #         supported yet.
        #   - When treat_array_entry_as_comp is enabled) is disabled:
        #       - comp is 0 and the entire array is treated as one scalar value.
        #
        # This applies to all `comp` related functionality in this model base.
        self._comp_ambiguous = []
        self._might_be_time_varying = False  # Inaccurate named. It really means if timesamples > 0
        self._timeline = omni.timeline.get_timeline_interface()
        self._current_time = self._timeline.get_current_time()
        self._timeline_subs = None
        self._on_set_default_fn = None
        self._soft_range_min = None
        self._soft_range_max = None

        # Get soft_range userdata settings
        attributes = self._get_attributes()
        if attributes:
            attribute = attributes[-1]
            if isinstance(attribute, Usd.Attribute):
                soft_range = attribute.GetCustomDataByKey("omni:kit:property:usd:soft_range_ui")
                if soft_range:
                    self._soft_range_min = soft_range[0]
                    self._soft_range_max = soft_range[1]

        # Hard range for the value. For vector type, range value is a float/int that compares against each component individually
        self._min = kwargs.get("min", None)
        self._max = kwargs.get("max", None)

        # Invalid range
        if self._min is not None and self._max is not None and self._min >= self._max:
            self._min = self._max = None

        # The state of the icon on the right side of the line with widgets
        self._control_state = 0
        # Callback when the control state is changing. We use it to redraw UI
        self._on_control_state_changed_fn = None
        # Callback when the value is reset. We use it to redraw UI
        self._on_set_default_fn = None
        # True if the attribute has the default value and the current value is not default
        self._different_from_default = False
        # Per component different from default
        self._comp_different_from_default = []

        # Whether the UsdModel should self register Tf.Notice or let UsdPropertiesWidget inform a property change
        if self_refresh:
            self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, self._stage)
        else:
            self._listener = None

        self._on_variant_changed_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.variant.editor.UsdVariant",
            event_name=GLOBAL_VARIANT_CHANGED_EVENT,
            on_event=self._on_variant_changed,
        )

        # Notification handler to throttle notifications.
        self._notification = None

        usd_context = self._get_usd_context()
        # _get_usd_context() can return None, and get_layers() turns a falsy argument into the
        # default context - so passing it through would silently subscribe spec-lock events to
        # the wrong context. Resolve only from a real context, then guard the result.
        layer_interface = layers.get_layers(usd_context) if usd_context else None
        self._spec_locks_subscription = None
        # OMPE-57990: Layer event is updated to Events 2.0 in 108.2 so here try to add transition code to accommodate both
        if layer_interface is None:
            carb.log_info("Variant Editor could not resolve a Layers interface; spec-lock events are not tracked.")
        elif _is_legacy_layer_event:
            self._spec_locks_subscription = layer_interface.get_event_stream().create_subscription_to_pop(
                self._on_spec_locks_changed, name="Property USD"
            )
        else:
            self._spec_locks_subscription = get_eventdispatcher().observe_event(
                observer_name="omni.kit.variant.editor.UsdVariant:SpecLocks",
                event_name=layers.layer_event_name(layers.LayerEventType.SPECS_LOCKING_CHANGED),
                on_event=lambda _: self.update_control_state(),
                filter=layer_interface.get_event_key(),
            )

    @property
    def control_state(self):
        """Returns the current control state, it's the icon on the right side of the line with widgets"""
        return self._control_state

    @property
    def stage(self):
        return self._stage

    @property
    def metadata(self):
        return self._metadata

    def is_editing(self) -> bool:
        return bool(self._editing)

    def set_value(self, value, comp: int = -1):
        validate_edit = VariantEditorCore.get_instance().validate_variant_edit(not self._editing)
        if not validate_edit and not self._editing:
            return

        if self._min is not None:
            if hasattr(value, "__len__"):
                for i in range(len(value)):
                    if value[i] < self._min:
                        value[i] = self._min
            else:
                if value < self._min:
                    value = self._min

        if self._max is not None:
            if hasattr(value, "__len__"):
                for i in range(len(value)):
                    if value[i] > self._max:
                        value[i] = self._max
            else:
                if value > self._max:
                    value = self._max

        if not self._ambiguous and not any(self._comp_ambiguous) and value == self._value:
            return False

        if self.is_instance_proxy():
            self._post_notification("Cannot edit attributes of instance proxy.")
            self._update_value(True)  # reset value
            return False

        if self.is_locked():
            self._post_notification("Cannot edit locked attributes.")
            self._update_value(True)  # reset value
            return False

        if self._might_be_time_varying:
            self._post_notification("Setting time varying attribute is not supported yet")
            return False

        self._value = value if comp == -1 else UsdVariant.update_value_by_comp(value, self._value, comp)
        attributes = self._get_attributes()

        if len(attributes) == 0:
            return False

        self._create_placeholder_attributes(attributes)

        if self._editing:
            for i, attribute in enumerate(attributes):
                self._ignore_notice = True

                # When prim is defined inside session layer, edits should be authored into session layer directly
                # instead of current edit target to avoid leaving stale overrides.
                if comp == -1:
                    self._real_values[i] = self._value
                    if not self._change_on_edit_end and validate_edit:
                        self.__editor_core._update_variant_attribute(attribute.GetPath(), self._value)
                else:
                    # Only update a single component of the value (for vector type)
                    value = self._real_values[i]
                    self._real_values[i] = self._update_value_by_comp(value, comp)
                    if not self._change_on_edit_end and validate_edit:
                        self.__editor_core._update_variant_attribute(attribute.GetPath(), self._value)

                self._ignore_notice = False
        else:
            with omni.kit.undo.group():
                for i, attribute in enumerate(attributes):
                    self._ignore_notice = True

                    # begin_edit is not called for certain widget (like Checkbox), issue the command directly
                    if comp == -1:
                        self._change_property(attribute.GetPath(), self._value, None)
                    else:
                        # Only update a single component of the value (for vector type)
                        value = self._real_values[i]
                        self._real_values[i] = self._update_value_by_comp(value, comp)
                        self._change_property(attribute.GetPath(), value, None)
                    self._ignore_notice = False

        if comp == -1:
            # We just set all the properties to the same value, it's no longer ambiguous
            self._ambiguous = False
            self._comp_ambiguous.clear()
        else:
            self._comp_ambiguous[comp] = False
            self._ambiguous = any(self._comp_ambiguous)

        if self._has_default_value:
            self._comp_different_from_default = [False] * self._get_comp_num()
            if comp == -1:
                self._different_from_default = value != self._default_value
                if self._different_from_default:
                    for comp in range(len(self._comp_different_from_default)):
                        self._comp_different_from_default[comp] = not self._compare_value_by_comp(
                            value, self._default_value, comp
                        )
            else:
                self._comp_different_from_default[comp] = not self._compare_value_by_comp(
                    value, self._default_value, comp
                )
                self._different_from_default = any(self._comp_different_from_default)
        else:
            self._different_from_default = False
            self._comp_different_from_default.clear()

        self.update_control_state()

        return True

    def _post_notification(self, message):
        if not self._notification or self._notification.dismissed:
            status = nm.NotificationStatus.WARNING
            self._notification = nm.post_notification(message, status=status)
            carb.log_warn(message)

    def _change_property(self, path: Sdf.Path, new_value, old_value):

        target_layer, _ = omni.usd.find_spec_on_session_or_its_sublayers(
            self._stage,
            path.GetPrimPath(),
            lambda spec: spec.specifier == Sdf.SpecifierDef,
        )
        if not target_layer:
            target_layer = self._stage.GetEditTarget().GetLayer()

        self.__editor_core._set_variant_attribute(path, new_value)

    def _update_value(self, force=False):
        return self._update_value_objects(force, self._get_attributes())

    def update_control_state(self):
        control_state, force_refresh = self._control_state_mgr.update_control_state(self)

        # Redraw control state icon when the control state is changed
        if self._control_state != control_state or force_refresh:
            self._control_state = control_state
            if self._on_control_state_changed_fn:
                self._on_control_state_changed_fn()

    def set_on_control_state_changed_fn(self, fn):
        """Callback that is called when control state is changed"""
        self._on_control_state_changed_fn = fn

    def set_on_set_default_fn(self, fn):
        """Callback that is called when value is reset"""
        self._on_set_default_fn = fn

    def recompose_object_as_variant(self, object):  # pragma: no cover
        set_name, variant = Sdf.Path(self.__editor_core.active_variant).GetVariantSelection()
        object_name = object.GetName()
        object_prim_path = object.GetPrimPath()
        recomped_object_path = object_prim_path.AppendVariantSelection(set_name, variant).AppendProperty(object_name)
        object = self.__editor_core._get_edit_target_layer().GetObjectAtPath(recomped_object_path)
        return object

    def recompose_object_path_as_variant_path(self, object_path: Sdf.Path):  # pragma: no cover
        set_name, variant = Sdf.Path(self.__editor_core.active_variant).GetVariantSelection()
        recomposed_object_path = (
            object_path.GetPrimPath().AppendVariantSelection(set_name, variant).AppendProperty(object_path.name)
        )
        return recomposed_object_path

    def _update_value_objects(self, force: bool, objects: list):
        if (self._dirty or force) and self._stage:
            with Ar.ResolverContextBinder(self._stage.GetPathResolverContext()):
                with Ar.ResolverScopedCache():
                    carb.profiler.begin(1, "UsdVariant._update_value_objects")
                    current_time_code = self.get_current_time_code()
                    self._might_be_time_varying = False
                    self._value = None
                    self._has_default_value = False
                    self._default_value = None
                    self._real_values.clear()
                    self._connections.clear()
                    self._ambiguous = False
                    self._comp_ambiguous.clear()
                    self._different_from_default = False
                    self._comp_different_from_default.clear()
                    for index, object in enumerate(objects):
                        value = self._read_value(object, current_time_code)
                        self._real_values.append(value)
                        if isinstance(object, Usd.Attribute):
                            self._might_be_time_varying = self._might_be_time_varying or object.GetNumTimeSamples() > 0
                            self._connections.append(
                                [conn for conn in object.GetConnections()] if object.HasAuthoredConnections() else []
                            )
                        # only need to check the first prim. All other prims are supposedly to be the same
                        if index == 0:
                            self._value = value
                            if self._value and self._is_array_type(object) and len(self._value) > 16:
                                self._is_big_array = True
                            comp_num = self._get_comp_num()
                            self._comp_ambiguous = [False] * comp_num
                            self._comp_different_from_default = [False] * comp_num
                            # Loads the default value
                            self._has_default_value, self._default_value = self._get_default_value(object)
                        elif self._value != value:
                            self._value = value
                            self._ambiguous = True
                            comp_num = len(self._comp_ambiguous)
                            if comp_num > 0:
                                for i in range(comp_num):
                                    if not self._comp_ambiguous[i]:
                                        self._comp_ambiguous[i] = not self._compare_value_by_comp(
                                            value, self._real_values[0], i
                                        )

                        if self._has_default_value:
                            comp_num = len(self._comp_different_from_default)
                            if comp_num > 0:
                                for i in range(comp_num):
                                    if not self._comp_different_from_default[i]:
                                        self._comp_different_from_default[i] = not self._compare_value_by_comp(
                                            value, self._default_value, i
                                        )
                                self._different_from_default |= any(self._comp_different_from_default)
                            else:
                                self._different_from_default |= value != self._default_value

                    self._dirty = False
                    if _is_legacy_timeline:
                        self._timeline_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop(
                            self._on_timeline_event
                        )
                    else:
                        self._timeline_subs = [
                            get_eventdispatcher().observe_event(
                                observer_name="omni.kit.variant.editor.UsdVariant:Timeline",
                                filter=self._timeline.get_event_key(),
                                event_name=name,
                                on_event=func,
                            )
                            for name, func in (
                                (
                                    omni.timeline.GLOBAL_EVENT_CURRENT_TIME_TICKED,
                                    self._on_timeline_current_time_ticked,
                                ),
                                (
                                    omni.timeline.GLOBAL_EVENT_TENTATIVE_TIME_CHANGED,
                                    self._on_timeline_tentative_time_changed,
                                ),
                            )
                        ]

                    self.update_control_state()
                    carb.profiler.end(1)
            return True
        return False

    def _get_default_value(self, property):
        default_values = {
            "xformOp:scale": (1.0, 1.0, 1.0),
            "visibleInPrimaryRay": True,
            "primvars:multimatte_id": -1,
        }

        if isinstance(property, Usd.Attribute):
            prim = property.GetPrim()
            if prim:
                custom = property.GetCustomData()
                if "default" in custom:
                    # This is not the standard USD way to get default.
                    return True, custom["default"]
                elif "customData" in self._metadata:
                    # This is to fetch default value for custom property.
                    default_value = self._metadata["customData"].get("default", None)
                    if default_value:
                        return True, default_value
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
        elif isinstance(property, PlaceholderAttribute):
            return True, property.Get()
        elif isinstance(property, Sdf.AttributeSpec):
            return True, property.default

        return False, None

    def set_default(self, comp=-1):
        """Set the UsdAttribute default value if it exists in metadata"""
        self.set_soft_range_userdata(None, None)
        if self.is_different_from_default() is False or self._has_default_value is False:
            if self._soft_range_min is not None and self._soft_range_max is not None:
                if self._on_set_default_fn:
                    self._on_set_default_fn()
                self.update_control_state()
            return

        current_time_code = self.get_current_time_code()

        with omni.kit.undo.group():
            # TODO clear timesample
            # However, when a value is timesampled, the "default" button is overridden by timesampled button,
            # so there's no way to invoke this function
            for attribute in self._get_attributes():
                if isinstance(attribute, Usd.Attribute):
                    current_value = attribute.Get(current_time_code)
                    if comp >= 0:
                        # OM-46294: Make a value copy to avoid changing with reference.
                        default_value = copy.copy(current_value)
                        default_value[comp] = self._default_value[comp]
                    else:
                        default_value = self._default_value

                    self._change_property(attribute.GetPath(), default_value, current_value)

        # We just set all the properties to the same value, it's no longer ambiguous
        self._ambiguous = False
        self._comp_ambiguous.clear()

        self._different_from_default = False
        self._comp_different_from_default.clear()

        if self._on_set_default_fn:
            self._on_set_default_fn()

        # OM-106014 workaround. It only handles UI refresh on the <set default button>.
        # TOTO : A general data change notification based solution, like UsdPropertiesWidget._delayed_dirty_handler().
        self._set_dirty()

    def _read_value(self, object: Usd.Object, time_code: Usd.TimeCode):
        carb.profiler.begin(1, "UsdVariant._read_value")
        val = None
        if isinstance(object, Usd.Attribute):
            val = object.Get()
        elif isinstance(object, Sdf.AttributeSpec):
            val = object.default
        if val is None:
            result, val = self._get_default_value(object)
            if not result:
                val = self._get_obj_type_default_value(object)
        carb.profiler.end(1)
        return val

    def _get_obj_type_default_value(self, obj):
        type_name = self._get_type_name(obj)

        if isinstance(type_name, Sdf.ValueTypeName):
            return type_name.defaultValue
        else:
            return None

    def _get_type_name(self, obj=None):
        if obj:
            if hasattr(obj, "GetTypeName"):
                return obj.GetTypeName()
            elif hasattr(obj, "typeName"):
                return obj.typeName
            else:
                return None
        else:
            type_name = self._metadata.get(Sdf.PrimSpec.TypeNameKey, "unknown type")
            return Sdf.ValueTypeNames.Find(type_name)

    def _is_array_type(self, obj=None):
        type_name = self._get_type_name(obj)

        if isinstance(type_name, Sdf.ValueTypeName):
            return type_name.isArray
        else:
            return False

    def has_connections(self):
        return bool(len(self._connections[-1]) > 0)

    def _get_value_by_comp(self, value, comp: int):
        if value.__class__.__module__ == "pxr.Gf":
            if value.__class__.__name__.startswith("Quat"):
                if comp == 0:
                    return value.real
                else:
                    return value.imaginary[comp - 1]
            elif value.__class__.__name__.startswith("Matrix"):
                dimension = len(value)
                row = comp // dimension
                col = comp % dimension
                return value[row, col]
            elif value.__class__.__name__.startswith("Vec"):
                return value[comp]
        else:
            if comp < len(value):
                return value[comp]

        return None

    def _get_comp_num(self):
        # TODO: Improve finding if the value type is a vector type
        # Checks if the value type is a vector type
        if self._value.__class__.__module__ == "pxr.Gf":
            if self._value.__class__.__name__.startswith("Quat"):
                return 4
            elif self._value.__class__.__name__.startswith("Matrix"):
                mat_dimension = len(self._value)
                return mat_dimension * mat_dimension
            elif hasattr(self._value, "__len__"):
                return len(self._value)
        elif self._is_array_type() and self._treat_array_entry_as_comp:
            return len(self._value)
        return 0

    @Trace.TraceFunction
    def _on_usd_changed(self, notice, stage):
        if stage != self._stage:
            return

        if self._editing > 0:
            return

        if self._ignore_notice:
            return

        for path in notice.GetResyncedPaths():
            if path in self._object_paths_set:
                self._set_dirty()
                return

        for path in notice.GetChangedInfoOnlyPaths():
            if path in self._object_paths_set:
                self._set_dirty()
                return

    def _on_variant_changed(self, evt):
        if evt.payload["attribute_paths"] != None:
            path = Sdf.Path(str(evt.payload["attribute_paths"]))
            if path in self._object_paths_set:
                self._set_dirty()
                return

    def _on_dirty(self):
        pass

    def _set_dirty(self):
        if self._editing > 0:
            return

        self._dirty = True
        self._on_dirty()

    def _compare_value_by_comp(self, val1, val2, comp: int):
        return self._get_value_by_comp(val1, comp) == self._get_value_by_comp(val2, comp)

    def _update_value_by_comp(self, value, comp: int):
        """update value from self._value"""
        return UsdVariant.update_value_by_comp(self._value, value, comp)

    @staticmethod
    def update_value_by_comp(from_value, to_value, comp: int):
        """update value from from_value to to_value"""
        if from_value.__class__.__module__ == "pxr.Gf":
            if from_value.__class__.__name__.startswith("Quat"):
                if comp == 0:
                    to_value.real = from_value.real
                else:
                    imaginary = from_value.imaginary
                    imaginary[comp - 1] = from_value.imaginary[comp - 1]
                    to_value.SetImaginary(imaginary)
            elif from_value.__class__.__name__.startswith("Matrix"):
                dimension = len(from_value)
                row = comp // dimension
                col = comp % dimension
                to_value[row, col] = from_value[row, col]
            elif from_value.__class__.__name__.startswith("Vec"):
                to_value[comp] = from_value[comp]
        else:
            to_value[comp] = from_value[comp]
        return to_value

    # Set soft_range userdata settings
    def set_soft_range_userdata(self, soft_range_min, soft_range_max):
        for attribute in self._get_attributes():
            if isinstance(attribute, Usd.Attribute):
                if soft_range_min is None and soft_range_max is None:
                    attribute.SetCustomDataByKey("omni:kit:property:usd:soft_range_ui", None)
                else:
                    attribute.SetCustomDataByKey(
                        "omni:kit:property:usd:soft_range_ui",
                        Gf.Vec2f(soft_range_min, soft_range_max),
                    )

        self._soft_range_min = soft_range_min
        self._soft_range_max = soft_range_max

    def get_value(self):
        self._update_value()
        return self._value

    def get_current_time_code(self):
        return Usd.TimeCode(omni.usd.get_frame_time_code(self._current_time, self._stage.GetTimeCodesPerSecond()))

    def _on_timeline_event(self, e):
        if e.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_TICKED):
            current_time = e.payload["currentTime"]
            if current_time != self._current_time:
                self._current_time = current_time
                if self._might_be_time_varying:
                    self._set_dirty()
        elif e.type == int(omni.timeline.TimelineEventType.TENTATIVE_TIME_CHANGED):
            tentative_time = e.payload["tentativeTime"]
            if tentative_time != self._current_time:
                self._current_time = tentative_time
                if self._might_be_time_varying:
                    self._set_dirty()

    def _on_timeline_current_time_ticked(self, event):
        current_time = event.payload["currentTime"]
        if current_time != self._current_time:
            self._current_time = current_time
            if self._might_be_time_varying:
                self._set_dirty()

    def _on_timeline_tentative_time_changed(self, event):
        tentative_time = event.payload["tentativeTime"]
        if tentative_time != self._current_time:
            self._current_time = tentative_time
            if self._might_be_time_varying:
                self._set_dirty()

    def _get_objects(self):
        objects = []
        if not self._stage:
            return objects

        for path in self._object_paths:
            obj = self._stage.GetObjectAtPath(path)
            if obj and not obj.IsHidden():
                objects.append(obj)
        return objects

    def _get_attributes(self):
        if not self._stage:
            return []
        attributes = []
        if not self._stage:
            return attributes

        for path in self._object_paths:
            prim = self._stage.GetPrimAtPath(path.StripAllVariantSelections().GetPrimPath())
            if prim:
                attr = prim.GetAttribute(path.name)
                if attr:
                    if not attr.IsHidden():
                        attributes.append(attr)
                else:
                    attr = PlaceholderAttribute(name=path.name, prim=prim, metadata=self._metadata)
                    attributes.append(attr)
        return attributes

    def get_attribute_paths(self) -> List[Sdf.Path]:
        return self._object_paths

    def get_property_paths(self) -> List[Sdf.Path]:
        return self.get_attribute_paths()

    def get_connections(self):
        return self._connections

    def destroy(self):
        self._notification = None
        if _is_legacy_timeline:
            if self._timeline_sub:
                self._timeline_sub.unsubscribe()
                self._timeline_sub = None
        if self._timeline_subs:
            self._timeline_subs.clear()
            self._timeline_subs = None
        self._stage = None
        self._spec_locks_subscription = None
        if self._listener:
            self._listener.Revoke()
            self._listener = None
        if self._on_variant_changed_sub:
            self._on_variant_changed_sub = None

    def _is_prev_same(self):
        return self._prev_real_values == self._real_values

    def begin_edit(self):
        self._editing = self._editing + 1
        self._prev_value = self._value
        self._save_real_values_as_prev()

    def end_edit(self):
        self._editing = self._editing - 1

        if self._is_prev_same():
            return

        if not VariantEditorCore.get_instance().validate_variant_edit():
            return

        attributes = self._get_attributes()
        self._create_placeholder_attributes(attributes)

        with omni.kit.undo.group():
            self._ignore_notice = True
            for i in range(len(attributes)):
                attribute = attributes[i]
                self._change_property(attribute.GetPath(), self._real_values[i], self._prev_real_values[i])
            self._ignore_notice = False

        # Set flags. It calls _on_control_state_changed_fn when the user finished editing
        self._update_value(True)

    def _save_real_values_as_prev(self):
        # It's like copy.deepcopy but not all USD types support pickling (e.g. Gf.Quat*)
        self._prev_real_values = [type(value)(value) for value in self._real_values]

    def _create_placeholder_attributes(self, attributes):
        # NOTE: PlaceholderAttribute.CreateAttribute cannot throw exceptions
        for index, attribute in enumerate(attributes):
            if isinstance(attribute, PlaceholderAttribute):
                self._editing += 1
                attributes[index] = attribute.CreateAttribute()
                self._editing -= 1

    def _on_spec_locks_changed(self, event: carb.events.IEvent):
        payload = layers.get_layer_event_payload(event)
        if payload and payload.event_type == layers.LayerEventType.SPECS_LOCKING_CHANGED:
            self.update_control_state()

    def _get_usd_context(self):
        if not self._usd_context:
            self._usd_context = omni.usd.get_context_from_stage(self._stage)

        return self._usd_context

    def set_locked(self, locked):
        usd_context = self._get_usd_context()
        if not usd_context:
            carb.log_warn("Current stage is not attached to any usd context.")
            return

        if locked:
            omni.kit.usd.layers.lock_specs(usd_context, self._object_paths, False)
        else:
            omni.kit.usd.layers.unlock_specs(usd_context, self._object_paths, False)

    def is_instance_proxy(self):
        if not self._object_paths:
            return False

        path = Sdf.Path(self._object_paths[0]).GetPrimPath()
        prim = self._stage.GetPrimAtPath(path)

        return prim and prim.IsInstanceProxy()

    def is_locked(self):
        usd_context = self._get_usd_context()
        if not usd_context:
            carb.log_warn("Current stage is not attached to any usd context.")
            return

        for path in self._object_paths:
            if not omni.kit.usd.layers.is_spec_locked(usd_context, path):
                return False

        return True

    def is_different_from_default(self) -> bool:
        """Returns True if the attribute has the default value and the current value is not default"""
        self._update_value()
        # soft_range has been overridden
        if self._soft_range_min is not None and self._soft_range_max is not None:
            return True
        return self._different_from_default

    def is_ambiguous(self) -> bool:
        self._update_value()
        return self._ambiguous

    def is_comp_ambiguous(self, index: int) -> bool:
        self._update_value()
        comp_len = len(self._comp_ambiguous)
        if comp_len == 0 or index < 0:
            return self.is_ambiguous()
        if index < comp_len:
            return self._comp_ambiguous[index]
        return False

    def get_all_comp_ambiguous(self) -> List[bool]:
        """Empty array if attribute value is a scalar, check is_ambiguous instead"""
        self._update_value()
        return self._comp_ambiguous


class FloatModel(ui.SimpleFloatModel):
    def __init__(self, parent):
        super().__init__()
        self._parent = weakref.ref(parent)

    def begin_edit(self):
        parent = self._parent()
        parent.begin_edit(None)

    def end_edit(self):
        parent = self._parent()
        parent.end_edit(None)


class IntModel(ui.SimpleIntModel):
    def __init__(self, parent):
        super().__init__()
        self._parent = weakref.ref(parent)

    def begin_edit(self):
        parent = self._parent()
        parent.begin_edit(None)

    def end_edit(self):
        parent = self._parent()
        parent.end_edit(None)


class UsdAttributeModelVariant(ui.AbstractValueModel, UsdVariant):

    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        self_refresh: bool,
        metadata: dict,
        change_on_edit_end=False,
        **kwargs,
    ) -> None:
        UsdVariant.__init__(
            self,
            stage,
            attribute_paths,
            self_refresh,
            metadata,
            change_on_edit_end,
            **kwargs,
        )
        ui.AbstractValueModel.__init__(self)

    def destroy(self):
        UsdVariant.destroy(self)

    def begin_edit(self):
        UsdVariant.begin_edit(self)
        ui.AbstractValueModel.begin_edit(self)

    def end_edit(self):
        UsdVariant.end_edit(self)
        ui.AbstractValueModel.end_edit(self)
        if len(self._object_paths) > 0:
            queue_event(
                GLOBAL_VARIANT_CHANGED_EVENT,
                {"attribute_paths": self._object_paths[0].pathString},
            )

    def get_value_as_string(self, elide_big_array=True) -> str:
        self._update_value()
        if self._value is None:
            return ""
        elif self._is_big_array and elide_big_array:
            return "[...]"
        else:
            return str(self._value)

    def get_value_as_float(self) -> float:
        self._update_value()
        if self._value is None:
            return 0.0
        else:
            if hasattr(self._value, "__len__"):
                return float(self._value[self._channel_index])
            return float(self._value)

    def get_value_as_bool(self) -> bool:
        self._update_value()
        if self._value is None:
            return False
        else:
            if hasattr(self._value, "__len__"):
                return bool(self._value[self._channel_index])
            return bool(self._value)

    def get_value_as_int(self) -> int:
        self._update_value()
        if self._value is None:
            return 0
        else:
            if hasattr(self._value, "__len__"):
                return int(self._value[self._channel_index])
            return int(self._value)

    def set_value(self, value):
        if UsdVariant.set_value(self, value):
            self._value_changed()

    def _on_dirty(self):
        self._value_changed()


class GfVecAttributeSingleChannelModelVariant(UsdAttributeModelVariant):
    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        channel_index: int,
        self_refresh: bool,
        metadata: dict,
        change_on_edit_end=False,
        **kwargs,
    ):
        self._channel_index = channel_index
        super().__init__(stage, attribute_paths, self_refresh, metadata, change_on_edit_end, **kwargs)

    def get_value_as_string(self, **kwargs) -> str:
        self._update_value()
        if self._value is None:
            return ""
        else:
            return str(self._value[self._channel_index])

    def get_value_as_float(self) -> float:
        self._update_value()
        if self._value is None:
            return 0.0
        else:
            if hasattr(self._value, "__len__"):
                return float(self._value[self._channel_index])
            return float(self._value)

    def get_value_as_bool(self) -> bool:
        self._update_value()
        if self._value is None:
            return False
        else:
            if hasattr(self._value, "__len__"):
                return bool(self._value[self._channel_index])
            return bool(self._value)

    def get_value_as_int(self) -> int:
        self._update_value()
        if self._value is None:
            return 0
        else:
            if hasattr(self._value, "__len__"):
                return int(self._value[self._channel_index])
            return int(self._value)

    def set_value(self, value):
        vec_value = copy.copy(self._value)
        vec_value[self._channel_index] = value

        if UsdVariant.set_value(self, vec_value, self._channel_index):
            self._value_changed()

    def is_different_from_default(self):
        """Override to only check channel"""
        if super().is_different_from_default():
            return self._comp_different_from_default[self._channel_index]
        return False


class TfTokenAttributeModelVariant(ui.AbstractItemModel, UsdVariant):
    class AllowedTokenItem(ui.AbstractItem):
        def __init__(self, item):
            super().__init__()
            self.token = item
            self.model = ui.SimpleStringModel(item)

    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        self_refresh: bool,
        metadata: dict,
    ):
        UsdVariant.__init__(self, stage, attribute_paths, self_refresh, metadata)
        ui.AbstractItemModel.__init__(self)

        self._allowed_tokens = []

        self._current_index = ui.SimpleIntModel()
        self._current_index.add_value_changed_fn(self._current_index_changed)

        self._updating_value = False

        self._has_index = False
        self._update_value()
        self._has_index = True

    def destroy(self):
        UsdVariant.destroy(self)

    def _get_allowed_tokens(self, attr):
        tokens = attr.GetMetadata("allowedTokens") or []
        for t in self._metadata.get("allowedTokens", []):
            if t not in tokens:
                tokens.append(t)

        return tokens

    def _update_allowed_token(self, token_item=AllowedTokenItem):
        self._allowed_tokens = []

        # For multi prim editing, the allowedTokens should all be the same
        attributes = self._get_attributes()
        attr = attributes[0] if len(attributes) > 0 else None
        if attr:
            for t in self._get_allowed_tokens(attr):
                self._allowed_tokens.append(token_item(t))

    def _update_value(self, force=False):
        was_updating_value = self._updating_value
        self._updating_value = True
        if UsdVariant._update_value(self, force):
            # Don't have to do this every time. Just needed when "allowedTokens" actually changed
            self._update_allowed_token()

            index = -1
            for i in range(0, len(self._allowed_tokens)):
                if self._allowed_tokens[i].token == self._value:
                    index = i

            if index != -1 and self._current_index.as_int != index:
                self._current_index.set_value(index)
                self._item_changed(None)
        self._updating_value = was_updating_value

    def get_item_value_model(self, item, column_id):
        if item is None:
            return self._current_index

        return item.model

    def begin_edit(self, item):
        UsdVariant.begin_edit(self)

    def end_edit(self, item):
        UsdVariant.end_edit(self)

    def _current_index_changed(self, model):
        if not self._has_index:
            return

        # If we're updating from USD notice change to UI, don't call set_value
        if self._updating_value:
            return

        index = model.as_int
        if self.set_value(self._get_value_from_index(index)):
            self._item_changed(None)

    def get_item_children(self, item):
        self._update_value()
        return self._allowed_tokens

    def _get_value_from_index(self, index):
        return self._allowed_tokens[index].token

    def get_value_as_token(self):
        index = self._current_index.as_int
        return self._allowed_tokens[index].token

    def is_allowed_token(self, token):
        return token in [allowed.token for allowed in self._allowed_tokens]

    def _on_dirty(self):
        self._item_changed(None)


class MdlEnumAttributeModelVariant(ui.AbstractItemModel, UsdVariant):
    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        self_refresh: bool,
        metadata: dict,
    ):
        UsdVariant.__init__(self, stage, attribute_paths, self_refresh, metadata)
        ui.AbstractItemModel.__init__(self)

        self._options = []

        self._current_index = ui.SimpleIntModel()
        self._current_index.add_value_changed_fn(self._current_index_changed)

        self._updating_value = False

        self._has_index = False
        self._update_value()
        self._has_index = True

    def destroy(self):
        UsdVariant.destroy(self)

    def get_item_children(self, item):
        self._update_value()
        return self._options

    def get_item_value_model(self, item, column_id):
        if item is None:
            return self._current_index

        return item.model

    def begin_edit(self, item):
        UsdVariant.begin_edit(self)

    def end_edit(self, item):
        UsdVariant.end_edit(self)

    def _current_index_changed(self, model):
        if not self._has_index:
            return

        # If we're updating from USD notice change to UI, don't call set_value
        if self._updating_value:
            return

        index = model.as_int
        if self.set_value(self._options[index].value):
            self._item_changed(None)

    def _update_option(self):
        self._options = []

        # For multi prim editing, the options should all be the same
        attributes = self._get_attributes()
        attr = attributes[0] if len(attributes) > 0 else None
        if attr and isinstance(attr, Usd.Attribute):
            shade_input = UsdShade.Input(attr)
            if shade_input and shade_input.HasRenderType() and shade_input.HasSdrMetadataByKey("options"):
                options = shade_input.GetSdrMetadataByKey("options").split("|")

                class OptionItem(ui.AbstractItem):
                    def __init__(self, display_name: str, value: int):
                        super().__init__()
                        self.model = ui.SimpleStringModel(display_name)
                        self.value = value

                for option in options:
                    kv = option.split(":")
                    self._options.append(OptionItem(kv[0], int(kv[1])))

    def _update_value(self, force=False):
        was_updating_value = self._updating_value
        self._updating_value = True
        if UsdVariant._update_value(self, force):
            # Don't have to do this every time. Just needed when "option" actually changed
            self._update_option()

            index = -1
            for i in range(0, len(self._options)):
                if self._options[i].value == self._value:
                    index = i

            if index != -1 and self._current_index.as_int != index:
                self._current_index.set_value(index)
                self._item_changed(None)
        self._updating_value = was_updating_value

    def _on_dirty(self):
        self._item_changed(None)

    def get_value_as_string(self):
        index = self._current_index.as_int
        return self._options[index].model.as_string

    def is_allowed_enum_string(self, enum_str):
        return enum_str in [allowed.model.as_string for allowed in self._options]

    def set_from_enum_string(self, enum_str):
        if not self.is_allowed_enum_string(enum_str):
            return

        new_index = -1
        for index, option in enumerate(self._options):
            if option.model.as_string == enum_str:
                new_index = index
                break
        if new_index != -1:
            self._current_index.set_value(new_index)


class GfVecAttributeModelVariant(ui.AbstractItemModel, UsdVariant):

    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        comp_count: int,
        tf_type: Tf.Type,
        self_refresh: bool,
        metadata: dict,
        **kwargs,
    ):
        UsdVariant.__init__(self, stage, attribute_paths, self_refresh, metadata, **kwargs)
        ui.AbstractItemModel.__init__(self)
        self._comp_count = comp_count
        self._data_type_name = "Vec" + str(self._comp_count) + tf_type.typeName[-1]
        self._data_type = getattr(Gf, self._data_type_name)

        class UsdVectorItem(ui.AbstractItem):
            def __init__(self, model):
                super().__init__()
                self.model = model

        # Create root model
        self._root_model = ui.SimpleIntModel()
        self._root_model.add_value_changed_fn(lambda a: self._item_changed(None))

        # Create three models per component
        if self._data_type_name.endswith("i"):
            self._items = [UsdVectorItem(IntModel(self)) for i in range(self._comp_count)]
        else:
            self._items = [UsdVectorItem(FloatModel(self)) for i in range(self._comp_count)]
        for item in self._items:
            item.model.add_value_changed_fn(lambda a, item=item: self._on_value_changed(item))

        self._edit_mode_counter = 0

    def destroy(self):
        UsdVariant.destroy(self)

    def _construct_vector_from_item(self):
        if self._data_type_name.endswith("i"):
            data = [item.model.get_value_as_int() for item in self._items]
        else:
            data = [item.model.get_value_as_float() for item in self._items]
        return self._data_type(data)

    def _on_value_changed(self, item):
        """Called when the submodel is changed"""

        if self._edit_mode_counter > 0:
            vector = self._construct_vector_from_item()
            index = self._items.index(item)
            if vector and self.set_value(vector, index):
                # Read the new value back in case hard range clamped it
                item.model.set_value(self._value[index])
                self._item_changed(item)
            else:
                # If failed to update value in model, revert the value in submodel
                item.model.set_value(self._value[index])

        if len(self._object_paths) > 0:
            queue_event(
                GLOBAL_VARIANT_CHANGED_EVENT,
                {"attribute_paths": self._object_paths[0].pathString},
            )

    def _update_value(self, force=False):
        if UsdVariant._update_value(self, force):
            if not self._value:
                for i in range(len(self._items)):
                    self._items[i].model.set_value(0.0)
                return
            for i in range(len(self._items)):
                self._items[i].model.set_value(self._value[i])

    def _on_dirty(self):
        self._item_changed(None)

    def get_item_children(self, item):
        """Reimplemented from the base class"""
        self._update_value()
        return self._items

    def get_item_value_model(self, item, column_id):
        """Reimplemented from the base class"""
        if item is None:
            return self._root_model
        return item.model

    def begin_edit(self, item):
        """
        Reimplemented from the base class.
        Called when the user starts editing.
        """
        self._edit_mode_counter += 1
        UsdVariant.begin_edit(self)

    def end_edit(self, item):
        """
        Reimplemented from the base class.
        Called when the user finishes editing.
        """
        UsdVariant.end_edit(self)
        self._edit_mode_counter -= 1


class SdfAssetPathAttributeModelVariant(UsdAttributeModelVariant, SdfAssetPathAttributeModel):
    """The value model that is reimplemented in Python to watch a USD attribute path"""

    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        self_refresh: bool,
        metadata: dict,
    ):
        UsdAttributeModelVariant.__init__(
            self,
            stage,
            attribute_paths,
            self_refresh,
            metadata,
            True,
            treat_array_entry_as_comp=True,
        )
        SdfAssetPathAttributeModel.__init__(self, stage, attribute_paths, self_refresh, metadata)

    def get_value_as_string(self, **kwargs):
        self._update_value()
        return self._get_value_as_string(self._value)

    def is_valid_path(self) -> bool:
        return self._is_valid_path(self._value)

    def get_resolved_path(self):
        self._update_value()
        return self._get_resolved_path(self._value)

    def get_wildcard_resolved_path(self):
        self._update_value()
        return self._get_wildcard_resolved_path(self._value)

    def set_value(self, path, resolved_path: str = ""):
        value = path
        if not isinstance(path, Sdf.AssetPath):
            if resolved_path:
                value = Sdf.AssetPath(path, resolved_path)
            else:
                value = Sdf.AssetPath(path)

        if UsdVariant.set_value(self, value):
            self._value_changed()

    def _is_prev_same(self):
        # Strip the resolvedPath from the AssetPath for the comparison, since the prev values don't have resolvedPath.
        return [Sdf.AssetPath(value.path) for value in self._real_values] == self._prev_real_values

    def _save_real_values_as_prev(self):
        # Strip the resolvedPath from the AssetPath so that it can be recomputed.
        self._prev_real_values = [Sdf.AssetPath(value.path) for value in self._real_values]

    def _change_property(self, path: Sdf.Path, new_value, old_value):
        if path.name == "info:mdl:sourceAsset" and new_value.path:
            if isinstance(new_value, Sdf.AssetPath):
                stage = omni.usd.get_context().get_stage()
                asset_path = new_value.path

                # compute the asset path relative to the root layer that is safe in Ar 1.0 and Ar 2.0
                asset_id = Sdf.ComputeAssetPathRelativeToLayer(stage.GetRootLayer(), asset_path)
                resolved_path = Ar.GetResolver().Resolve(asset_id)

                # make the path relative to current edit target layer
                relative_path = omni.usd.make_path_relative_to_current_edit_target(str(resolved_path))
                new_value = Sdf.AssetPath(relative_path, resolved_path)

        if path.name == "info:mdl:sourceAsset":
            if isinstance(new_value, Sdf.AssetPath):
                # "info:mdl:sourceAsset" when is changed update "info:mdl:sourceAsset:subIdentifier"
                stage = self._stage
                asset_attr = stage.GetAttributeAtPath(path)
                subid_attr = stage.GetAttributeAtPath(
                    path.GetPrimPath().AppendElementString(".info:mdl:sourceAsset:subIdentifier")
                )
                if asset_attr and subid_attr:
                    mdl_path = new_value.resolvedPath if new_value.resolvedPath else new_value.path
                    if mdl_path:

                        def have_subids(id_list: list):
                            if len(id_list) > 0:
                                with omni.kit.undo.group():
                                    UsdAttributeModelVariant._change_property(
                                        self,
                                        subid_attr.GetPath(),
                                        str(id_list[0]),
                                        None,
                                    )
                                    UsdAttributeModelVariant._change_property(self, path, new_value, old_value)

                        asyncio.ensure_future(
                            omni.kit.material.library.get_subidentifier_from_mdl(
                                mdl_file=mdl_path,
                                on_complete_fn=have_subids,
                                use_functions=True,
                                show_alert=True,
                            )
                        )

                        # force a refresh so that the new selections for info:mdl:sourceAsset:subIdentifier
                        # are visible in the UI
                        async def refresh_ui():
                            for _ in range(5):
                                await omni.kit.app.get_app().next_update_async()
                            omni.kit.commands.execute("RefreshVariantUi")

                        asyncio.ensure_future(refresh_ui())
                        return

                    else:
                        UsdAttributeModelVariant._change_property(self, subid_attr.GetPath(), "", None)

        UsdAttributeModelVariant._change_property(self, path, new_value, old_value)

    # Private functions to be shared with SdfAssetPathArrayAttributeSingleEntryModel
    def _get_value_as_string(self, value, **kwargs):
        return value.path if value else ""

    def _is_valid_path(self, value) -> bool:
        if not value:
            return False
        path = value.path
        if path.lower().startswith("http"):
            return False
        return bool(path)

    def _get_resolved_path(self, value):
        if self._ambiguous:
            return "Mixed"
        else:
            return value.resolvedPath.replace("\\", "/") if value else ""

    def _get_wildcard_resolved_path(self, value):
        if self._ambiguous:
            return "Mixed"
        else:
            path = value.path.replace("\\", "/")
            if "<UDIM>" in path:
                import os
                import re

                if not os.path.isabs(path):
                    prim = self._stage.GetPrimAtPath(self._object_paths[-1].GetPrimPath())
                    filename = os.path.basename(path)
                    reg = re.compile(filename.replace("<UDIM>", ".+"))
                    for prim_spec in prim.GetPrimStack():
                        parent = prim_spec.layer.ComputeAbsolutePath(os.path.dirname(path))

                        result, entries = omni.client.list(parent)
                        for entry in entries:
                            if re.match(reg, entry.relative_path):
                                return f"{parent}/{entry.relative_path}"

                return path

            return value.resolvedPath.replace("\\", "/") if value else ""


class SdfAssetPathArrayAttributeSingleEntryModelVariant(SdfAssetPathAttributeModelVariant):
    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        index: int,
        self_refresh: bool,
        metadata: dict,
    ):
        self._index = index
        super().__init__(stage, attribute_paths, self_refresh, metadata)

    @property
    def index(self):
        return self._index

    def get_value_as_string(self, **kwargs):
        self._update_value()
        return self._get_value_as_string(self._value[self._index])

    def get_value(self):
        return super().get_value()[self._index]

    def is_valid_path(self) -> bool:
        self._update_value()
        return self._is_valid_path(self._value[self._index])

    def get_resolved_path(self):
        self._update_value()
        return self._get_resolved_path(self._value[self._index])

    def get_wildcard_resolved_path(self):
        self._update_value()
        return self._get_wildcard_resolved_path(self._value[self._index])

    def set_value(self, path, resolved_path: str = ""):
        value = path
        if not isinstance(path, Sdf.AssetPath):
            if resolved_path:
                value = Sdf.AssetPath(path, resolved_path)
            else:
                value = Sdf.AssetPath(path)

        vec_value = Sdf.AssetPathArray(self._value)
        vec_value[self._index] = value

        if UsdVariant.set_value(self, vec_value, self._index):
            self._value_changed()

    def _is_prev_same(self):
        # Strip the resolvedPath from the AssetPath for the comparison, since the prev values don't have resolvedPath.
        return [
            [Sdf.AssetPath(value.path) for value in values] for values in self._real_values
        ] == self._prev_real_values

    def _save_real_values_as_prev(self):
        # Strip the resolvedPath from the AssetPath so that it can be recomputed.
        self._prev_real_values = [[Sdf.AssetPath(value.path) for value in values] for values in self._real_values]


class SdfAssetPathArrayAttributeItemModelVariant(ui.AbstractItemModel):
    class SdfAssetPathItemVariant(ui.AbstractItem):
        """Single item of the model"""

        def __init__(
            self,
            stage: Usd.Stage,
            attribute_paths: List[Sdf.Path],
            index: int,
            self_refresh: bool,
            metadata: dict,
        ):
            super().__init__()
            self.sdf_asset_path_model = SdfAssetPathArrayAttributeSingleEntryModelVariant(
                stage, attribute_paths, index, self_refresh, metadata
            )

        def destroy(self):
            self.sdf_asset_path_model.destroy()

    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        self_refresh: bool,
        metadata: dict,
        delegate,
    ):
        super().__init__()
        self._delegate = delegate  # keep a reference of the delegate os it's not destroyed
        self._value_model = UsdAttributeModelVariant(stage, attribute_paths, False, metadata)
        value = self._value_model.get_value()
        self._entries = []

        self._repopulate_entries(value)

    def destroy(self):
        self._delegate = None

        for entry in self._entries:
            entry.destroy()
        self._entries.clear()

        if self._value_model:
            self._value_model.destroy()
            self._value_model = None

    @property
    def value_model(self) -> UsdAttributeModelVariant:
        return self._value_model

    def get_item_children(self, item):
        """Returns all the children when the widget asks it."""
        if item is not None:
            # Since we are doing a flat list, we return the children of root only.
            # If it's not root we return.
            return []

        return self._entries

    def get_item_value_model_count(self, item):
        return 1

    def get_item_value_model(self, item, column_id):
        return (item.sdf_asset_path_model, self._value_model)

    def get_drag_mime_data(self, item):
        return str(item.sdf_asset_path_model.index)

    def drop_accepted(self, target_item, source, drop_location=-1):
        try:
            source_id = self._entries.index(source)
        except ValueError:
            # Not in the list. This is the source from another model.
            return False

        return not target_item and drop_location >= 0

    def drop(self, target_item, source, drop_location=-1):
        try:
            source_id = self._entries.index(source)
        except ValueError:
            # Not in the list. This is the source from another model.
            return

        if source_id == drop_location:
            # Nothing to do
            return

        value = list(self._value_model.get_value())
        moved_entry_value = value[source_id]
        del value[source_id]

        if drop_location > len(value):
            # Drop it to the end
            value.append(moved_entry_value)
        else:
            if source_id < drop_location:
                # Because when we removed source, the array became shorter
                drop_location = drop_location - 1

            value.insert(drop_location, moved_entry_value)
        self._value_model.set_value(value)

    def _repopulate_entries(self, value: Sdf.AssetPathArray):
        for entry in self._entries:
            entry.destroy()
        self._entries.clear()

        stage = self._value_model.stage
        metadata = self._value_model.metadata
        attribute_paths = self._value_model.get_attribute_paths()

        for i in range(len(value)):
            model = SdfAssetPathArrayAttributeItemModelVariant.SdfAssetPathItemVariant(
                stage, attribute_paths, i, False, metadata
            )
            self._entries.append(model)

        self._item_changed(None)

    def _on_usd_changed(self, *args, **kwargs):
        # forward to all sub-models
        self._value_model._on_usd_changed(*args, **kwargs)
        for entry in self._entries:
            entry.sdf_asset_path_model._on_usd_changed(*args, **kwargs)

    def _set_dirty(self, *args, **kwargs):
        # forward to all sub-models
        self._value_model._set_dirty(*args, **kwargs)

        new_value = self._value_model.get_value()
        if len(new_value) != len(self._entries):
            self._repopulate_entries(new_value)
        else:
            for entry in self._entries:
                entry.sdf_asset_path_model._set_dirty(*args, **kwargs)

    def get_value(self, *args, **kwargs):
        return self._value_model.get_value(*args, **kwargs)

    def set_value(self, *args, **kwargs):
        return self._value_model.set_value(*args, **kwargs)


class GfMatrixAttributeModel(ui.AbstractItemModel, UsdVariant):
    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        comp_count: int,
        tf_type: Tf.Type,
        self_refresh: bool,
        metadata: dict,
    ):
        UsdVariant.__init__(self, stage, attribute_paths, self_refresh, metadata)
        ui.AbstractItemModel.__init__(self)
        self._comp_count = comp_count
        data_type_name = "Matrix" + str(self._comp_count) + tf_type.typeName[-1]
        self._data_type = getattr(Gf, data_type_name)

        class UsdMatrixItem(ui.AbstractItem):
            def __init__(self, model):
                super().__init__()
                self.model = model

        # Create root model
        self._root_model = ui.SimpleIntModel()
        self._root_model.add_value_changed_fn(lambda a: self._item_changed(None))

        # Create three models per component
        self._items = [UsdMatrixItem(FloatModel(self)) for i in range(self._comp_count * self._comp_count)]
        for item in self._items:
            item.model.add_value_changed_fn(lambda a, item=item: self._on_value_changed(item))

        self._edit_mode_counter = 0

    def destroy(self):
        UsdVariant.destroy(self)

    def _on_value_changed(self, item):
        """Called when the submodel is chaged"""

        if self._edit_mode_counter > 0:
            matrix = self._construct_matrix_from_item()
            if matrix and self.set_value(matrix, self._items.index(item)):
                self._item_changed(item)

    def _update_value(self, force=False):
        if UsdVariant._update_value(self, force):
            for i in range(len(self._items)):
                self._items[i].model.set_value(self._value[i // self._comp_count][i % self._comp_count])

    def _on_dirty(self):
        self._item_changed(None)
        # it's still better to call _value_changed for all child items
        for child in self._items:
            child.model._value_changed()

    def get_item_children(self, item):
        """Reimplemented from the base class."""
        self._update_value()
        return self._items

    def get_item_value_model(self, item, column_id):
        """Reimplemented from the base class."""
        if item is None:
            return self._root_model
        return item.model

    def begin_edit(self, item):
        """
        Reimplemented from the base class.
        Called when the user starts editing.
        """
        self._edit_mode_counter += 1
        UsdVariant.begin_edit(self)

    def end_edit(self, item):
        """
        Reimplemented from the base class.
        Called when the user finishes editing.
        """
        UsdVariant.end_edit(self)
        self._edit_mode_counter -= 1

    def _construct_matrix_from_item(self):
        data = [item.model.get_value_as_float() for item in self._items]
        matrix = []
        for i in range(self._comp_count):
            matrix_row = []
            for j in range(self._comp_count):
                matrix_row.append(data[i * self._comp_count + j])
            matrix.append(matrix_row)
        return self._data_type(matrix)


class UsdAttributeInvertedModelVariant(UsdAttributeModelVariant):
    def get_value_as_bool(self) -> bool:
        return not super().get_value_as_bool()

    def get_value_as_string(self, **kwargs) -> str:
        return str(self.get_value_as_bool())

    def set_value(self, value):
        super().set_value(not value)

    def get_value(self):
        return not super().get_value()


class SdfTimeCodeModelVariant(UsdAttributeModelVariant):
    def _save_real_values_as_prev(self):
        # SdfTimeCode cannot be inited from another SdfTimeCode, only from float (double in C++)..
        self._prev_real_values = [Sdf.TimeCode(float(value)) for value in self._real_values]


class RelationshipArrayModelVariant(ui.AbstractValueModel):
    def __init__(self, stage, property_paths, additional_widget_kwargs):
        super().__init__()
        self.stage = stage
        self.metadata = {}
        self._editor_core = VariantEditorCore.get_instance()
        self._additional_widget_kwargs = additional_widget_kwargs if additional_widget_kwargs else {}
        self.targets_limit = self._additional_widget_kwargs.get("targets_limit", 0)
        self.filter_type_list = self._additional_widget_kwargs.get("target_picker_filter_type_list", [])
        self.filter_lambda = self._additional_widget_kwargs.get("target_picker_filter_lambda", None)
        self.on_add_targets = self._additional_widget_kwargs.get("target_picker_on_add_targets", None)
        self.property_paths = property_paths
        self._id_name = f"{property_paths[-1]}_{property_paths[-1].name}".replace("/", "_")
        self._relationships = [
            stage.GetPrimAtPath(path.GetPrimPath()).GetRelationship(path.name) for path in property_paths
        ]
        self._button = None
        self._update_shared_targets()
        self._value_changed()
        self._vset, self._vname = Sdf.Path(
            self._editor_core.active_variant if self._editor_core.active_variant else ""
        ).GetVariantSelection()

    def destroy(self):
        self._frame = None
        self._button = None
        self._label = None
        self.on_add_targets = None
        self._on_remove_target = None
        self._enabled = True

    def _update_shared_targets(self):
        self._shared_targets = None
        for relationship in self._relationships:
            targets = relationship.GetTargets()
            if self._shared_targets is None:
                self._shared_targets = targets
            elif self._shared_targets != targets:
                self._shared_targets = None
                break

    def is_ambiguous(self) -> bool:
        return self._shared_targets is None

    def get_relationship_paths(self) -> List[Sdf.Path]:
        return [rel.GetPath() for rel in self._relationships]

    def get_targets(self) -> List[Sdf.Path]:
        return self._shared_targets

    def get_property_paths(self):
        return self.property_paths

    def set_targets(self, targets: List[Sdf.Path]):
        if not VariantEditorCore.get_instance().validate_variant_edit():
            return

        if self.targets_limit > 0 and len(targets) > self.targets_limit:
            targets = targets[: self.targets_limit]
        for relationship in self._relationships:
            self._editor_core._set_relationship_value(relationship, targets)
        if self.on_add_targets:
            self.on_add_targets(targets)

    def set_value(self, targets: List[Sdf.Path]):
        self.set_targets(targets)

    def get_value(self):
        return self.get_targets()

    def _set_dirty(self, *args, **kwargs):
        self._update_shared_targets()
        self._value_changed()

    def _on_usd_changed(self, *args, **kwargs):
        self._set_dirty()


class SdfRelationshipArraySingleEntryModelVariant(ui.SimpleStringModel):
    def __init__(self, stage: Usd.Stage, property_paths: List[Sdf.Path], index: int):
        super().__init__()
        self._stage = stage
        self._paths = property_paths
        self.index = index
        self._editor_core = VariantEditorCore.get_instance()
        self._vset, self._vname = Sdf.Path(self._editor_core.active_variant).GetVariantSelection()

    def destroy(self):
        self._stage = None
        self._paths = None
        self.index = None

    def get_value_as_string(self):
        path = self._paths[0]
        relationships = self._stage.GetPrimAtPath(path.GetPrimPath()).GetRelationship(path.name)
        if relationships:
            targets = relationships.GetTargets()
            if self.index < len(targets):
                return str(targets[self.index])
        return ""

    def set_value_as_string(self, value):
        if not VariantEditorCore.get_instance().validate_variant_edit():
            return

        path = self._paths[0]
        relationships = self._stage.GetPrimAtPath(path.GetPrimPath()).GetRelationship(path.name)
        if relationships:
            targets = relationships.GetTargets()
            if self.index < len(targets):
                targets[self.index] = Sdf.Path(value)
                self._editor_core._set_relationship_value(relationships, targets)
        self._value_changed()

    def get_value(self):
        return self.get_value_as_string()

    def set_value(self, value):
        self.set_value_as_string(str(value))

    def _set_dirty(self, *args, **kwargs):
        self._value_changed()

    def _on_usd_changed(self, *args, **kwargs):
        self._set_dirty()


class SdfRelationshipArrayItemModelVariant(ui.AbstractItemModel):
    class SdfRelationshipPathItemVariant(ui.AbstractItem):
        """Single item of the model"""

        def __init__(
            self,
            stage: Usd.Stage,
            property_paths: List[Sdf.Path],
            index: int,
            self_refresh: bool,
            metadata: dict,
        ):
            super().__init__()
            self.sdf_relationship_path_model = SdfRelationshipArraySingleEntryModelVariant(stage, property_paths, index)

        def destroy(self):
            self.sdf_relationship_path_model.destroy()

    def __init__(
        self,
        stage: Usd.Stage,
        property_paths: List[Sdf.Path],
        metadata: dict,
        delegate,
        additional_widget_kwargs,
    ):
        super().__init__()
        self.metadata = metadata
        self.property_paths = property_paths
        self._additional_widget_kwargs = additional_widget_kwargs if additional_widget_kwargs else {}
        self.targets_limit = self._additional_widget_kwargs.get("targets_limit", 0)
        self.filter_type_list = self._additional_widget_kwargs.get("target_picker_filter_type_list", [])
        self.filter_lambda = self._additional_widget_kwargs.get("target_picker_filter_lambda", None)
        self._button = None

        class Picker(RelationshipTargetPicker):
            def show(self, *args, **kargs):
                if not VariantEditorCore.get_instance().validate_variant_edit():
                    return

                super().show(*args, **kargs)

        self.picker = Picker(
            stage,
            self.filter_type_list,
            self.filter_lambda,
            self._additional_widget_kwargs,
        )
        self._enabled = self._additional_widget_kwargs.get("enabled", True)
        self._delegate = delegate  # Keep a reference of the delegate so it's not destroyed
        self._value_model = RelationshipArrayModelVariant(stage, property_paths, additional_widget_kwargs)

        def on_add_targets(self, targets):
            self._set_dirty()

        self._value_model.on_add_targets = functools.partial(on_add_targets, weakref.proxy(self))
        value = self._value_model.get_value()
        self._entries = []

        self._repopulate_entries(value)

    def destroy(self):
        self.picker.clean()
        self.picker = None

        self._delegate = None

        for entry in self._entries:
            entry.destroy()
        self._entries.clear()

        if self._value_model:
            self._value_model.destroy()
            self._value_model = None

    @property
    def value_model(self):
        return self._value_model

    def get_item_children(self, item):
        """Returns all the children when the widget asks it."""
        if item is not None:
            # Since we are doing a flat list, we return the children of root only.
            # If it's not root we return.
            return []

        return self._entries

    def get_item_value_model_count(self, item):
        return 1

    def get_item_value_model(self, item, column_id):
        return (item.sdf_relationship_path_model, self._value_model)

    def get_drag_mime_data(self, item):
        return str(item.sdf_relationship_path_model.index)

    def drop_accepted(self, target_item, source, drop_location=-1):
        try:
            self._entries.index(source)
        except ValueError:
            # Not in the list. This is the source from another model.
            return False

        return not target_item and drop_location >= 0

    def drop(self, target_item, source, drop_location=-1):
        try:
            source_id = self._entries.index(source)
        except ValueError:
            # Not in the list. This is the source from another model.
            return

        if source_id == drop_location:
            # Nothing to do
            return

        value = list(self._value_model.get_value())
        moved_entry_value = value[source_id]
        del value[source_id]

        if drop_location > len(value):
            # Drop it to the end
            value.append(moved_entry_value)
        else:
            if source_id < drop_location:
                # Because when we removed source, the array became shorter
                drop_location = drop_location - 1

            value.insert(drop_location, moved_entry_value)
        self._value_model.set_value(value)

    def _repopulate_entries(self, value):
        for entry in self._entries:
            entry.destroy()
        self._entries.clear()

        stage = self._value_model.stage
        metadata = self._value_model.metadata
        property_paths = self._value_model.get_property_paths()

        for i in range(len(value)):
            model = SdfRelationshipArrayItemModelVariant.SdfRelationshipPathItemVariant(
                stage, property_paths, i, False, metadata
            )
            self._entries.append(model)

        self._item_changed(None)

    def _on_usd_changed(self, *args, **kwargs):
        # forward to all sub-models
        self._value_model._on_usd_changed(*args, **kwargs)
        for entry in self._entries:
            entry.sdf_relationship_path_model._on_usd_changed(*args, **kwargs)

    def _set_dirty(self, *args, **kwargs):
        # forward to all sub-models
        self._value_model._set_dirty(*args, **kwargs)

        new_value = self._value_model.get_value()
        if len(new_value) != len(self._entries):
            self._repopulate_entries(new_value)
        else:
            for entry in self._entries:
                entry.sdf_relationship_path_model._set_dirty(*args, **kwargs)

    def get_value(self, *args, **kwargs):
        return self._value_model.get_value(*args, **kwargs)

    def set_value(self, *args, **kwargs):
        return self._value_model.set_value(*args, **kwargs)


class VariantSubIdentifierModel(TfTokenAttributeModelVariant):
    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        self_refresh: bool,
        metadata: dict,
        options: list,
        attr: Usd.Attribute,
    ):
        self._widget = None
        self._combobox_options = [attr.Get()]
        super().__init__(
            stage=stage,
            attribute_paths=attribute_paths,
            self_refresh=self_refresh,
            metadata=metadata,
        )
        self._has_index = False

        async def load_subids():
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.material.library.get_subidentifier_from_material(
                prim=attr.GetPrim(), on_complete_fn=self._have_list, use_functions=True
            )

        asyncio.ensure_future(load_subids())

    def _get_allowed_tokens(self, attr):
        return self._combobox_options

    def _update_allowed_token(self):
        super()._update_allowed_token(AllowedAnnoItem)

    def _update_value(self, force=False):

        was_updating_value = self._updating_value
        self._updating_value = True
        if UsdVariant._update_value(self, force):
            # Don't have to do this every time. Just needed when "allowedTokens" actually changed
            self._update_allowed_token()

            def find_allowed_token(value):
                if value is None:
                    return -1
                # Try to match the full token, i.e. simple name with function parameters
                for i in range(0, len(self._allowed_tokens)):
                    if self._allowed_tokens[i].token == value:
                        return i
                # If the above failed, drop the parameter list of the query
                # Try to find a match based on the simple name alone
                # NOTE: because of overloads there can be more than one match
                query = value.split("(", 1)[0]
                match_count = 0
                first_match_index = -1
                for i in range(0, len(self._allowed_tokens)):
                    if self._allowed_tokens[i].token.split("(", 1)[0] == query:
                        if match_count == 0:
                            first_match_index = i
                        match_count += 1
                # If there is one match based on simple name, we can safely return this one
                if match_count == 1:
                    return first_match_index
                # The match is not unique, we need to return a `<not found>`
                else:
                    return -1

            index = find_allowed_token(self._value)
            if self._value and index == -1:
                carb.log_warn(f"failed to find '{self._value}' in function name list")
                index = len(self._allowed_tokens)
                self._allowed_tokens.append(
                    AllowedAnnoItem(
                        token=self._value,
                        item=f"<sub-identifier not found: '{self._value}'>",
                    )
                )

            if index != -1 and self._current_index.as_int != index:
                self._current_index.set_value(index)
                self._item_changed(None)
        self._updating_value = was_updating_value

    def _have_list(self, mtl_list: list):
        if mtl_list:
            self._combobox_options = mtl_list
            self._set_dirty()
            if self._has_index is False:
                self._update_value()
                self._has_index = True


class AllowedAnnoItem(ui.AbstractItem):
    def __init__(self, item, token=None):
        from omni.kit.material.library import MaterialLibraryExtension

        super().__init__()
        if item is None:
            self.token = ""
            self.model = ui.SimpleStringModel("")
        elif isinstance(item, MaterialLibraryExtension.SubIDEntry):
            if "subid_token" in item.annotations:
                self.token = item.annotations["subid_token"]
            else:
                self.token = item.name
            self.model = ui.SimpleStringModel(item.name)
            if "subid_display_name" in item.annotations:
                self.model = ui.SimpleStringModel(item.annotations["subid_display_name"])
            elif "display_name" in item.annotations:
                self.model = ui.SimpleStringModel(item.annotations["display_name"])
            else:
                self.model = ui.SimpleStringModel(item.name)
        else:
            if token:
                self.token = token
                self.model = ui.SimpleStringModel(item)

            else:
                self.token = item
                self.model = ui.SimpleStringModel(item)


class VariantSetModel(ui.AbstractItemModel, UsdVariant):
    def __init__(
        self,
        stage: Usd.Stage,
        object_paths: List[Sdf.Path],
        variant_set_name: str,
        self_refresh: bool,
    ):
        UsdVariant.__init__(self, stage, object_paths, self_refresh, {})
        ui.AbstractItemModel.__init__(self)
        self._editor_core = VariantEditorCore.get_instance()

        self._variant_set_name = variant_set_name
        self._variant_names = []

        self._current_index = ui.SimpleIntModel()
        self._current_index.add_value_changed_fn(self._current_index_changed)

        self._has_index = False
        self._update_value()
        self._has_index = True

    def destroy(self):
        UsdVariant.destroy(self)

    def get_item_children(self, item):
        self._update_value()
        return self._variant_names

    def get_item_value_model(self, item, column_id):
        if item is None:
            return self._current_index

        return item.model

    def begin_edit(self, item):
        UsdVariant.begin_edit(self)

    def end_edit(self, item):
        UsdVariant.end_edit(self)

    def set_value(self, value, comp=-1):
        # If one than one item selected then don't early exit as anchor might be same but others may not
        if value == self._value and len(self._variant_names) == 1:
            return

        if not self._editor_core.validate_variant_edit():
            return

        self._editor_core._set_variant_selection_as_attribute(self._object_paths[0], self._variant_set_name, value)
        self._item_changed(None)

    def _current_index_changed(self, model):
        if not self._has_index:
            return

        index = model.as_int
        if self.set_value(self._variant_names[index].model.get_value_as_string()):
            self._item_changed(None)

    def _update_variant_names(self):
        self._variant_names = []

        vset = self._get_variant_set()
        if vset:
            vnames = vset.GetVariantNames()

            class AllowedTokenItem(ui.AbstractItem):
                def __init__(self, name):
                    super().__init__()
                    self.model = ui.SimpleStringModel(name)

            self._variant_names.append(AllowedTokenItem(""))  # Empty variant
            for name in vnames:
                self._variant_names.append(AllowedTokenItem(name))

    def _update_value(self, force=False):
        if self._update_value_objects(force, self._get_objects()):
            # Don't have to do this every time. Just needed when "VariantNames" actually changed
            self._update_variant_names()

            index = -1
            for i in range(0, len(self._variant_names)):
                if self._variant_names[i].model.get_value_as_string() == self._value:
                    index = i

            if index != -1 and self._current_index.as_int != index:
                self._current_index.set_value(index)
                self._item_changed(None)

    def _on_dirty(self):
        self._item_changed(None)

    def _read_value(self, object: Usd.Object, time_code: Usd.TimeCode):
        vsets = object.GetVariantSets()
        vset = vsets.GetVariantSet(self._variant_set_name)
        return vset.GetVariantSelection()

    def _get_variant_set(self):
        prims = self._get_objects()
        prim = prims[0] if len(prims) > 0 else None
        if prim:
            vsets = prim.GetVariantSets()
            return vsets.GetVariantSet(self._variant_set_name)
        return None


class MetadataObjectModelVariant(MetadataObjectModel):
    def destroy(self):
        self.clean()

    def get_active_variant_set(self):
        core = VariantEditorCore.get_instance()
        vset_name = core._get_active_variant_set()
        vset = core._get_variant_set_by_name(vset_name)
        return vset_name, vset

    def send_edit_variant_command(self, cmd_name, **kargs):
        vset_name, vset = self.get_active_variant_set()
        prim_path = vset.GetPrim().GetPath().pathString

        with VariantEditorCore.get_instance().AuthorVariant():
            omni.kit.commands.execute(
                "EditVariant",
                prim_path=prim_path,
                variant_set_name=vset_name,
                cmd_name=cmd_name,
                cmd_args={**kargs},
            )

    def _read_value(self, object: Usd.Object, time_code: Usd.TimeCode):
        _, vset = self.get_active_variant_set()
        with vset.GetVariantEditContext():
            value = object.GetMetadata(self._key)
            if not value:
                value = self._default_value
            return value

    def _write_value(self, objects: list, key: str, value):
        path_list = []
        for object in objects:
            path_list.append(object.GetPath())
        self.send_edit_variant_command("ChangeMetadata", object_paths=path_list, key=key, value=value)
