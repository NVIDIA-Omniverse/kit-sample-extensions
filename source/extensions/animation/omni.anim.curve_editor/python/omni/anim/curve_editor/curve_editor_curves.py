import asyncio
import functools
import sys

import AnimationSchema
import AnimationSchemaTools
import carb
import omni.anim.curve.core
import omni.kit.notification_manager as nm
from omni.anim.curve.core import get_curvekey_clipboard, get_curves
from omni.kit.widget.timeline import EditScope, TimelineView, WeakMethod
from pxr import Gf, Sdf, Usd

from . import curve_editor_globals as globals
from .commands import *
from .curve_editor import SingletonCurveEditor, _CurveTangent
from .curve_editor_curve_infinity import *
from .curve_editor_globals import *
from .curve_editor_key_manager import *
from .guidelines import Guidelines
from .timeline_ruler import Ruler


# Wrapper of all UI reprentations of one curve attribute
class CurveOfAttribute:
    def __init__(self, owner_view, user_prim_path_str, data_attr_name):
        self._infinity_curve = None
        self._infinity_curve_pre_frame = None
        self._infinity_curve_post_frame = None
        self._pre_infinity_type = None  # means it is not initialized yet
        self._post_infinity_type = None  # means it is not initialized yet
        self._segment_list = []
        self._key_rects = []
        self._in_control_rects = []
        self._out_control_rects = []
        self._in_control_lines = []
        self._out_control_lines = []
        self._step_rects = []
        self._name = data_attr_name
        self._user = user_prim_path_str
        self._schema_curve_api = None
        self._time_codes_per_second = 0
        self._overriden_keys = []

        # these simple scopes are only used to check to be non reentrant
        self._in_control_edit_scope_simple = EditScope()
        self._out_control_edit_scope_simple = EditScope()

        self._view_wp = weakref.ref(owner_view)

        self._cached_index = 0

        # read/write with USD. Might be redesigned together with _CurveTanget later. All interfaces related to the following may need redesign someday.
        self._sample_tangents = []

    # update without reloading from USD data.
    def update_ui(self):
        for key_rect in self._key_rects:
            index = self._get_key_index(key_rect)
            key_time = self._get_time_code_from_index(index)
            offset_x = self._get_offset_x_from_time(key_time)
            offset_y = self._get_offset_y_from_scratchpad(index)
            key_rect._set_key_ui_x(offset_x)
            key_rect._set_key_ui_y(offset_y)
            key_rect._drag_align()

            # in control basic UI update. Derived UI update to do in later _refresh_control_related_ui()
            in_control_time = self._sample_tangents[index].get_in_time_code(self._time_codes_per_second)
            in_control_value = self._sample_tangents[index].get_in_value()
            in_control_offset_x = self._get_offset_x_from_time(in_control_time)
            in_control_offset_y = self._get_offset_y_from_value(in_control_value)
            self._in_control_rects[index]._set_control_ui_x(in_control_offset_x)
            self._in_control_rects[index]._set_control_ui_y(in_control_offset_y)

            # out control basic UI update. Derived UI update to do in later _refresh_control_related_ui()
            out_control_time = self._sample_tangents[index].get_out_time_code(self._time_codes_per_second)
            out_control_value = self._sample_tangents[index].get_out_value()
            out_control_offset_x = self._get_offset_x_from_time(out_control_time)
            out_control_offset_y = self._get_offset_y_from_value(out_control_value)
            self._out_control_rects[index]._set_control_ui_x(out_control_offset_x)
            self._out_control_rects[index]._set_control_ui_y(out_control_offset_y)

            # update prev step rect. Same x as this indexed key.
            if index > 0:
                prev_step_rect = self._step_rects[index - 1]
                prev_step_rect._set_ui_x(key_rect.get_key_ui_x())

            # update this step rect. Same y as this indexed key.
            if index < self._get_segment_quantity():
                step_rect = self._step_rects[index]
                step_rect._set_ui_y(key_rect.get_key_ui_y())

        self._refresh_control_related_ui()

        self._update_infinity_curve()

    def _notify_infinity_curve_segment_change(self, control_segment):
        if self._infinity_curve:
            index = self._get_segment_index(control_segment)
            self._infinity_curve.update_ui_by_origin_segment(self, index)

    def _notify_infinity_curve_segment_visibility_change(self, control_segment):
        if self._infinity_curve:
            index = self._get_segment_index(control_segment)
            self._infinity_curve.update_ui_by_origin_segment_visibility(self, index)

    def _notify_infinity_curve_anchor_x_change(self, key_rect_old_index, key_rect_index):
        if self._infinity_curve:
            if key_rect_old_index == key_rect_index:
                self._infinity_curve.update_ui_by_origin_anchor_x(self, key_rect_old_index, key_rect_index)
            else:
                # things are complicated in this code path
                # for simplicity, update x and y offset for all the influenced indexed rect
                index_start = min(key_rect_old_index, key_rect_index)
                index_end = max(key_rect_old_index, key_rect_index)
                self._infinity_curve.update_ui_by_origin_anchor_x(self, index_start, index_end)
                self._infinity_curve.update_ui_by_origin_anchor_y(self, index_start, index_end)

    def _notify_infinity_curve_anchor_y_change(self, key_rect_index):
        if self._infinity_curve:
            self._infinity_curve.update_ui_by_origin_anchor_y(self, key_rect_index, key_rect_index)

    def _notify_infinity_curve_pre_type_change(self, infinity_type: CurveInfinityTypes.InfinityType):
        if self._infinity_curve:
            self._pre_infinity_type = infinity_type
            self._build_pre_infinity_curve()
        else:
            carb.log_warn("Unexpected code path in CurveOfAttribute._notify_infinity_curve_pre_type_change()")

    def _notify_infinity_curve_post_type_change(self, infinity_type: CurveInfinityTypes.InfinityType):
        if self._infinity_curve:
            self._post_infinity_type = infinity_type
            self._build_post_infinity_curve()
        else:
            carb.log_warn("Unexpected code path in CurveOfAttribute._notify_infinity_curve_post_type_change()")

    def _notify_infinity_curve_adapt(self):
        # for special case curve without key, self._infinity_curve is None
        if self._infinity_curve:
            self._infinity_curve.adapt_ui_pre(self)
            self._infinity_curve.adapt_ui_post(self)

    def _build_pre_infinity_curve(self):
        self._infinity_curve.rebuild_ui_pre(self, self._pre_infinity_type)

    def _build_post_infinity_curve(self):
        self._infinity_curve.rebuild_ui_post(self, self._post_infinity_type)

    def _update_infinity_curve(self):
        # for special case curve without key, self._infinity_curve is None
        if self._infinity_curve:
            self._infinity_curve.update_ui(self)

    def get_curve_editor_timeline(self):
        return self._view_wp().get_curve_editor_timeline()

    def init(self, stage) -> bool:
        runtime_curve = self.get_runtime_curve()
        if runtime_curve != None:
            self._schema_curve_api = AnimationSchema.AnimationCurveAPI(stage.GetPrimAtPath(runtime_curve.anim_data))
            user_prim = stage.GetPrimAtPath(self._user)
            if is_timeline_node(user_prim):
                # temporary support of timeline node's framerate. If framerate attribute is change, no event is sent and responded.
                node = omni.graph.core.get_node_by_path(self._user)
                self._time_codes_per_second = node.get_attribute("inputs:framerate").get()
            else:
                self._time_codes_per_second = stage.GetTimeCodesPerSecond()
            return True
        else:
            return False

    # it is not persistent, for example after SetKeys(). So I must get it again and again. It might have some room for future improvement.
    def get_runtime_curve(self):
        return get_curve_from_runtime(self._user, self._name)

    def get_track_name(self):
        return self._user + "." + self._name

    def get_name(self):
        return self._name

    def _get_key_quantity(self):
        return len(self._key_rects)

    def _get_segment_quantity(self):
        return len(self._segment_list)

    def _get_offset_x_from_time(self, time):
        return self._view_wp()._get_offset_x_from_time(time)

    def _get_offset_y_from_value(self, value):
        return self._view_wp()._get_offset_y_from_value(value)

    def _get_value_x(self, offset_x) -> float:
        return self._view_wp()._get_value_x(offset_x)

    def _get_value_y(self, offset_y) -> float:
        return self._view_wp()._get_value_y(offset_y)

    def _get_key_rect_size(self):
        return self._view_wp()._get_key_rect_size()

    def _get_control_rect_size(self):
        return self._view_wp()._get_control_rect_size()

    def _get_curve_segment_color(self):
        return self._view_wp()._get_curve_color(self._name)

    def _is_key_x_movable(self) -> bool:
        return self._view_wp()._is_key_x_movable()

    def _is_key_y_movable(self) -> bool:
        return self._view_wp()._is_key_y_movable()

    # time can be any timecode. It does not have to be at some key time.
    def _get_prevoius_key_time(self, time) -> float:
        # default if no previous key found
        previous_key_time = time

        # iterate previous keys
        for index in range(self._get_key_quantity()):
            key_time = self._sample_tangents[index].get_time_code(self._time_codes_per_second)
            if key_time < time:
                # with incremental index, previous_key_time is getting bigger and bigger. But never greater_equal than time.
                previous_key_time = key_time
            else:
                break

        return previous_key_time

    # time can be any timecode. It does not have to be at some key time.
    def _get_next_key_time(self, time) -> float:
        # default if no previous key found
        next_key_time = time

        # iterate next keys, from end to front.
        for index in range(self._get_key_quantity() - 1, -1, -1):
            key_time = self._sample_tangents[index].get_time_code(self._time_codes_per_second)
            if key_time > time:
                # with decremental index, next_key_time is getting smaller and smaller. But never less_equal than time.
                next_key_time = key_time
            else:
                break

        return next_key_time

    def _get_default_tangent_type_from_runtime(self) -> CurveInterpolation.TangentType:
        tangent_type_token = self._schema_curve_api.GetDefaultTangentType(self._name)
        return CurveInterpolation.TangentType.get(tangent_type_token)

    # this is only expected to work for curve creation
    def _get_pre_infinity_type_from_runtime(self) -> CurveInfinityTypes.InfinityType:
        infinity_type_token = self._schema_curve_api.GetInfinityType(self._name, AnimationSchema.Infinity.Pre)
        return CurveInfinityTypes.InfinityType.get(infinity_type_token)

    # this is only expected to work for curve creation
    def _get_post_infinity_type_from_runtime(self) -> CurveInfinityTypes.InfinityType:
        infinity_type_token = self._schema_curve_api.GetInfinityType(self._name, AnimationSchema.Infinity.Post)
        return CurveInfinityTypes.InfinityType.get(infinity_type_token)

    def _get_default_tangent_type(self) -> CurveInterpolation.TangentType:
        return self._get_default_tangent_type_from_runtime()

    def _get_pre_infinity_type(self) -> CurveInfinityTypes.InfinityType:
        return self._pre_infinity_type

    def _get_post_infinity_type(self) -> CurveInfinityTypes.InfinityType:
        return self._post_infinity_type

    def _get_in_tangent_type(self, key_rect) -> int:
        index = self._get_key_index(key_rect)
        return self._in_control_rects[index].get_tangent_type()

    def _get_out_tangent_type(self, key_rect) -> int:
        index = self._get_key_index(key_rect)
        return self._out_control_rects[index].get_tangent_type()

    def _get_key_index(self, key_rect):
        return self._get_index(key_rect, self._key_rects)

    def _get_segment_index(self, curve_segment):
        return self._get_index(curve_segment, self._segment_list)

    def _usd_edit_scope(self):
        return self._view_wp()._usd_edit_scope()

    def _get_index(self, target, repo):
        # First do a quick test.
        if self._cached_index < len(repo) and repo[self._cached_index] == target:
            return self._cached_index
        else:
            # Cache miss. Loop to find.
            for i, content in enumerate(repo):
                if content == target:
                    self._cached_index = i
                    return i
            # For the time being, it is not really expected.
            carb.log_error("Unexpected code path in CurveOfAttribute._get_index()")
            return -1

    def _get_time_code_from_index(self, index) -> float:
        return self._sample_tangents[index].get_time_code(self._time_codes_per_second)

    def _get_time_tick_from_index(self, index) -> int:
        return self._sample_tangents[index].get_time_tick()

    def _get_value_from_scratchpad(self, index):
        return self._get_scratchpad_key(index).value

    def _get_offset_y_from_scratchpad(self, index):
        value = self._get_value_from_scratchpad(index)
        offset_y = self._get_offset_y_from_value(value)
        return offset_y

    def _get_schema_keys(self):
        return self._schema_curve_api.GetKeys(self._name)

    def _get_schema_key(self, index):
        return self._get_schema_keys()[index]

    def _get_schema_key_tuber(self, index):
        return SchemaKeyTuber(self._get_schema_key(index), self._time_codes_per_second)

    # wrapper to get a copy from the readable only src runtime key.
    def _get_scratchpad_key(self, index):
        if self._overriden_keys:
            return self._overriden_keys[index]
        else:
            curve = self.get_runtime_curve()
            return omni.anim.curve.core.Key(curve.keys[index])

    def _update_scratchpad_key(self, key, old_time):
        curve_plugin = omni.anim.curve.core.get_curve_plugin()
        curve = curve_plugin.get_curves(self._user).get(self._name, None)

        source_keys = []
        if self._overriden_keys:
            source_keys = self._overriden_keys
        else:
            for curve_key in curve.keys:
                source_keys.append(omni.anim.curve.core.Key(curve_key))

        overriden_keys = []

        inserted = False

        for curve_key in source_keys:
            if curve_key.time == old_time or curve_key.time == key.time:
                continue

            if not inserted:
                if curve_key.time > key.time:
                    overriden_keys.append(key)
                    inserted = True

            overriden_keys.append(curve_key)

        if not inserted:
            overriden_keys.append(key)

        self._overriden_keys = overriden_keys
        curve.overriden_keys = self._overriden_keys
        curve_plugin.pump_keys_overriden_event([f"{self._user}.{self._name}"])

    # raw move. It does not adjust/validate tangents. For clarity, it reset the tangents to the key origin to show explicitly that it is in an intermediate status.
    def _move_scratchpad_key_value(self, index, new_value):
        scratchpad_key = self._get_scratchpad_key(index)
        key_tuber = SchemaKeyTuber(scratchpad_key)
        key_tuber.set_value(new_value)
        key_tuber.reset_tangents_to_origin()
        self._update_scratchpad_key(scratchpad_key, None)

    def _move_key_value(self, index, new_value):
        with self._usd_edit_scope():
            self._move_scratchpad_key_value(index, new_value)

    # raw move. It does not adjust/validate tangents. For clarity, it reset the tangents to the key origin to show explicitly that it is in an intermediate status.
    def _move_scratchpad_key_time(self, old_index, new_time_tick):
        scratchpad_key = self._get_scratchpad_key(old_index)
        key_tuber = SchemaKeyTuber(scratchpad_key)
        old_time_tick = key_tuber.get_time_tick()
        key_tuber.set_time_tick(new_time_tick)
        key_tuber.reset_tangents_to_origin()
        self._update_scratchpad_key(scratchpad_key, old_time_tick)

    # Previous sorting is needed for data integrity.
    def _move_key_time(self, old_index, old_time_tick, index, time_tick) -> float:
        with self._usd_edit_scope():
            if self._get_scratchpad_key(old_index).time != old_time_tick:
                # sanity check. runtime cached key should match self._sample_tangents
                carb.log_error("Unexpected code path in CurveOfAttribute._move_key_time() before cache update")
            self._move_scratchpad_key_time(old_index, time_tick)
            if self._get_scratchpad_key(index).time != time_tick:
                # sanity check. runtime cached key should match self._sample_tangents
                carb.log_error("Unexpected code path in CurveOfAttribute._move_key_time() after cache update")
            self._sample_tangents[index].set_time_tick(time_tick)

    def _move_scratchpad_key_tangent(self, index):
        scratchpad_key = self._get_scratchpad_key(index)
        key_tuber = SchemaKeyTuber(scratchpad_key)
        self._sample_tangents[index].write_to_tuber(key_tuber)
        self._update_scratchpad_key(scratchpad_key, None)

    # change self._sample_tangents[index] partially and write to runtime scratchpad
    def _move_key_tangent(self, index, ui_in_x=None, ui_in_y=None, ui_out_x=None, ui_out_y=None):
        if ui_in_x is not None:
            self._sample_tangents[index].set_in_time_tick(
                time_code_to_time_tick(self._get_value_x(ui_in_x), self._time_codes_per_second)
            )
        if ui_in_y is not None:
            self._sample_tangents[index].set_in_value(self._get_value_y(ui_in_y))
        if ui_out_x is not None:
            self._sample_tangents[index].set_out_time_tick(
                time_code_to_time_tick(self._get_value_x(ui_out_x), self._time_codes_per_second)
            )
        if ui_out_y is not None:
            self._sample_tangents[index].set_out_value(self._get_value_y(ui_out_y))

        with self._usd_edit_scope():
            if self._get_scratchpad_key(index).time != self._get_time_tick_from_index(index):
                # sanity check. runtime cached key should match self._sample_tangents
                carb.log_error("Unexpected code path in CurveOfAttribute._move_key_tangent() before cache update")
            self._move_scratchpad_key_tangent(index)

    def _set_tangent_broken_to_runtime(self, index, is_tangent_broken: bool):
        with self._usd_edit_scope():
            key_tuber = self._get_schema_key_tuber(index)
            if key_tuber.get_time_tick() != self._get_time_tick_from_index(index):
                carb.log_error("Sanity check error in CurveOfAttribute._set_tangent_broken_to_runtime()")
            else:
                key_tuber.set_is_tangent_broken(is_tangent_broken)

    def _set_tangent_weighted_to_runtime(self, index, is_tangent_weighted: bool):
        with self._usd_edit_scope():
            key_tuber = self._get_schema_key_tuber(index)
            if key_tuber.get_time_tick() != self._get_time_tick_from_index(index):
                carb.log_error("Sanity check error in CurveOfAttribute._set_tangent_weighted_to_runtime()")
            else:
                key_tuber.set_is_tangent_weighted(is_tangent_weighted)

    def _set_tangent_type_to_runtime(self, index, in_tangent_type: int, out_tangent_type: int):
        with self._usd_edit_scope():
            key_tuber = self._get_schema_key_tuber(index)
            if key_tuber.get_time_tick() != self._get_time_tick_from_index(index):
                carb.log_error("Sanity check error in CurveOfAttribute._set_tangent_type_to_runtime()")
            else:
                key_tuber.set_in_tangent_type(in_tangent_type)
                key_tuber.set_out_tangent_type(out_tangent_type)

    def _on_key_selected(self, key_rect, selected: bool):
        index = self._get_key_index(key_rect)
        # here selection will trigger control UI presented.
        self._ttc_update_control_visibility(index, selected)

        # memorize selection status.
        self._sample_tangents[index].set_selected(selected)

    def _on_curve_double_clicked(self, curve_segment):
        self._view_wp()._on_curve_double_clicked(self)

    def _control_drag_align(self, index):
        # in and out drag align. without triggering recursive callback
        in_control_rect = self._in_control_rects[index]
        in_control_rect._drag_align()
        out_control_rect = self._out_control_rects[index]
        out_control_rect._drag_align()

    def _on_control_released_select(self, index, control_rect):
        if hasattr(control_rect, "_moved_during_press_and_release"):
            if control_rect._moved_during_press_and_release == False:
                self._view_wp()._on_control_released_select(self._key_rects[index], control_rect)
            self._destroy_moved_flag(control_rect)

    def _create_moved_flag(self, control_rect):
        control_rect._moved_during_press_and_release = False

    def _raise_moved_flag(self, control_rect):
        if hasattr(control_rect, "_moved_during_press_and_release"):
            control_rect._moved_during_press_and_release = True

    def _destroy_moved_flag(self, control_rect):
        delattr(control_rect, "_moved_during_press_and_release")

    def _time_tick_to_time_code(self, time_tick: int):
        return time_tick_to_time_code(time_tick, self._time_codes_per_second)

    # it is a hacky timeline node code path for runtime curve commands
    def _time_code_for_timeline_node_command(self, time_code):
        stage_tcps = omni.usd.get_context().get_stage().GetTimeCodesPerSecond()
        if stage_tcps != self._time_codes_per_second:
            # assume timeline node code path
            time_code *= stage_tcps / self._time_codes_per_second

        return time_code

    def _on_control_released(self, index, control_rect):
        if not hasattr(control_rect, "_pressed_values"):
            if SHOW_MORE_LOG_WARN:
                carb.log_warn(
                    "Control move operation command broken. It also might happen when multiple overlapping controls are selected."
                )
            return

        with self._usd_edit_scope():
            new_tIn = self._sample_tangents[index].get_in_time_tick()
            new_vIn = self._sample_tangents[index].get_in_value()
            new_tOut = self._sample_tangents[index].get_out_time_tick()
            new_vOut = self._sample_tangents[index].get_out_value()
            old_in_time_tick = control_rect._pressed_values[0]
            old_in_value = control_rect._pressed_values[1]
            old_out_time_tick = control_rect._pressed_values[2]
            old_out_value = control_rect._pressed_values[3]
            new_in_type = self._in_control_rects[index].get_tangent_type()
            new_out_type = self._out_control_rects[index].get_tangent_type()
            old_in_type = control_rect._pressed_values[4]
            old_out_type = control_rect._pressed_values[5]
            if (
                new_tIn != old_in_time_tick
                or new_vIn != old_in_value
                or new_tOut != old_out_time_tick
                or new_vOut != old_out_value
                or new_in_type != old_in_type
                or new_out_type != old_out_type
            ):
                time_tick = self._get_time_tick_from_index(index)
                key_value = self._get_value_from_scratchpad(index)
                track_name = self.get_track_name()
                # make command
                with omni.kit.undo.group():

                    if new_in_type != old_in_type or new_tIn != old_in_time_tick or new_vIn != old_in_value:
                        selection_state = omni.anim.curve.core.KeySelectionState(
                            track_name,
                            {time_tick: omni.anim.curve.core.KeySelectionState.SelectFlag(False, True, False)},
                        )
                        in_relative_time_code = self._time_tick_to_time_code(new_tIn - time_tick)
                        in_relative_time_code = self._time_code_for_timeline_node_command(in_relative_time_code)
                        in_relative_value = new_vIn - key_value
                        omni.kit.commands.execute(
                            "EditAnimCurveKeys",
                            selection_state=selection_state,
                            tangent_type=CurveInterpolation.TangentType.to_tangent_type_token(new_in_type),
                            time=in_relative_time_code,
                            value=in_relative_value,
                        )

                    if new_out_type != old_out_type or new_tOut != old_out_time_tick or new_vOut != old_out_value:
                        selection_state = omni.anim.curve.core.KeySelectionState(
                            track_name,
                            {time_tick: omni.anim.curve.core.KeySelectionState.SelectFlag(False, False, True)},
                        )
                        out_relative_time_code = self._time_tick_to_time_code(new_tOut - time_tick)
                        out_relative_time_code = self._time_code_for_timeline_node_command(out_relative_time_code)
                        out_relative_value = new_vOut - key_value
                        omni.kit.commands.execute(
                            "EditAnimCurveKeys",
                            selection_state=selection_state,
                            tangent_type=CurveInterpolation.TangentType.to_tangent_type_token(new_out_type),
                            time=out_relative_time_code,
                            value=out_relative_value,
                        )

        # control_rect._pressed_values release
        delattr(control_rect, "_pressed_values")

        self._control_drag_align(index)

    def _on_control_pressed(self, index, control_rect):
        # save _pressed_values for later use in _on_control_released.
        control_rect._pressed_values = []
        control_rect._pressed_values.append(self._sample_tangents[index].get_in_time_tick())
        control_rect._pressed_values.append(self._sample_tangents[index].get_in_value())
        control_rect._pressed_values.append(self._sample_tangents[index].get_out_time_tick())
        control_rect._pressed_values.append(self._sample_tangents[index].get_out_value())
        control_rect._pressed_values.append(self._in_control_rects[index].get_tangent_type())
        control_rect._pressed_values.append(self._out_control_rects[index].get_tangent_type())

    def _lazy_in_control_set_fixed(self, in_control_rect):
        if in_control_rect.get_tangent_type() != CurveInterpolation.TangentType.Fixed:
            in_control_rect._command_set_tangent_type(CurveInterpolation.TangentType.Fixed)

            index = self._get_in_control_index(in_control_rect)
            key_rect = self._key_rects[index]
            self._view_wp()._show_in_tangent_type(key_rect, in_control_rect)

    def _lazy_out_control_set_fixed(self, out_control_rect):
        if out_control_rect.get_tangent_type() == CurveInterpolation.TangentType.Step:
            # early return for the Step special situation
            return

        if out_control_rect.get_tangent_type() != CurveInterpolation.TangentType.Fixed:
            out_control_rect._command_set_tangent_type(CurveInterpolation.TangentType.Fixed)

            index = self._get_out_control_index(out_control_rect)
            key_rect = self._key_rects[index]
            self._view_wp()._show_out_tangent_type(key_rect, out_control_rect)

    def _get_in_control_index(self, control_rect):
        return self._get_index(control_rect, self._in_control_rects)

    def _on_in_control_moved_simple(self, control_rect):
        if self._in_control_edit_scope_simple:
            with self._in_control_edit_scope_simple:
                index = self._get_in_control_index(control_rect)
                self._ttc_on_in_control_moved(index)
                # update attribute
                self._move_key_tangent(
                    index, ui_in_x=control_rect.get_control_ui_x(), ui_in_y=control_rect.get_control_ui_y()
                )
        else:
            # _in_control_edit_scope_simple should not contain recursive code
            carb.log_error("Wrong logic in CurveOfAttribute._on_in_control_moved_simple()")

    def _on_in_control_moved(self, control_rect):
        self._raise_moved_flag(control_rect)

        if control_rect._within_setting_drag_scope() == False:
            # update all selection in control, if it is triggered by user UI operation. or when on_moved() is directly called.
            self._view_wp()._on_in_control_moved(control_rect)

        self._on_in_control_moved_simple(control_rect)

    def _on_in_control_released(self, control_rect):
        index = self._get_in_control_index(control_rect)
        self._on_control_released_select(index, control_rect)
        self._view_wp()._on_in_control_released(control_rect)

    def _on_in_control_pressed(self, control_rect):
        self._create_moved_flag(control_rect)
        self._view_wp()._on_in_control_pressed(control_rect)

    def _get_out_control_index(self, control_rect):
        return self._get_index(control_rect, self._out_control_rects)

    def _on_out_control_moved_simple(self, control_rect):
        if self._out_control_edit_scope_simple:
            with self._out_control_edit_scope_simple:
                index = self._get_out_control_index(control_rect)
                self._ttc_on_out_control_moved(index)
                # update attribute
                self._move_key_tangent(
                    index, ui_out_x=control_rect.get_control_ui_x(), ui_out_y=control_rect.get_control_ui_y()
                )
        else:
            # _out_control_edit_scope_simple should not contain recursive code
            carb.log_error("Wrong logic in CurveOfAttribute._on_out_control_moved_simple()")

    def _on_out_control_moved(self, control_rect):
        self._raise_moved_flag(control_rect)

        if control_rect._within_setting_drag_scope() == False:
            # update all selection out control, if it is triggered by user UI operation. or when on_moved() is directly called.
            self._view_wp()._on_out_control_moved(control_rect)

        self._on_out_control_moved_simple(control_rect)

    def _on_out_control_released(self, control_rect):
        index = self._get_out_control_index(control_rect)
        self._on_control_released_select(index, control_rect)
        self._view_wp()._on_out_control_released(control_rect)

    def _on_out_control_pressed(self, control_rect):
        self._create_moved_flag(control_rect)
        self._view_wp()._on_out_control_pressed(control_rect)

    def _pre_key_xy_changed(self, key_rect):
        # push old key related values, for later use in _post_key_xy_changed.
        index = self._get_key_index(key_rect)
        key_rect._pressed_values = []
        key_rect._pressed_values.append(self._get_time_tick_from_index(index))
        key_rect._pressed_values.append(self._get_value_from_scratchpad(index))
        key_rect._pressed_values.append(self._sample_tangents[index].get_in_time_tick())
        key_rect._pressed_values.append(self._sample_tangents[index].get_in_value())
        key_rect._pressed_values.append(self._sample_tangents[index].get_out_time_tick())
        key_rect._pressed_values.append(self._sample_tangents[index].get_out_value())
        key_rect._pressed_values.append({})
        self._cache_tangents_4_move_undo(key_rect)

        # also cache these ui constants, for kmb_manager
        key_rect._kmb_values = []
        old_offset_x = key_rect.get_key_ui_x()
        old_offset_y = key_rect.get_key_ui_y()
        old_in_tan_x = self._in_control_rects[index]._get_drag_ui_x() - old_offset_x
        old_in_tan_y = self._in_control_rects[index]._get_drag_ui_y() - old_offset_y
        old_out_tan_x = self._out_control_rects[index]._get_drag_ui_x() - old_offset_x
        old_out_tan_y = self._out_control_rects[index]._get_drag_ui_y() - old_offset_y
        key_rect._kmb_values.append(old_offset_x)
        key_rect._kmb_values.append(old_offset_y)
        key_rect._kmb_values.append(old_in_tan_x)
        key_rect._kmb_values.append(old_in_tan_y)
        key_rect._kmb_values.append(old_out_tan_x)
        key_rect._kmb_values.append(old_out_tan_y)

    def _update_segment_ui(self, index, next_index):
        if (index >= 0) and (next_index < self._get_key_quantity()):
            key_rect = self._key_rects[index]
            next_key_rect = self._key_rects[next_index]
            control_rect = self._out_control_rects[index]
            next_control_rect = self._in_control_rects[next_index]
            step_rect = self._step_rects[index]
            step_rect._set_ui_x(next_key_rect.get_key_ui_x())
            step_rect._set_ui_y(key_rect.get_key_ui_y())
            self._segment_list[index].update_ui(key_rect, next_key_rect, control_rect, next_control_rect, step_rect)
            # confirm step status in segment
            if self._key_rects[index].get_out_tangent_type() == CurveInterpolation.TangentType.Step:
                self._segment_list[index].show_as_step()

    # a little helper
    def _swap_list_element(self, list, i0, i1):
        list[i0], list[i1] = list[i1], list[i0]

    # need to swap between index and next_index, and refresh ui and _sample_tangents elements related to them.
    def _swap_2_keys(self, index, next_index):
        # swapping USD data
        self._swap_list_element(self._sample_tangents, index, next_index)

        # swapping keys and controls are straightforward.
        self._swap_list_element(self._key_rects, index, next_index)
        self._swap_list_element(self._in_control_rects, index, next_index)
        self._swap_list_element(self._out_control_rects, index, next_index)
        self._swap_list_element(self._in_control_lines, index, next_index)
        self._swap_list_element(self._out_control_lines, index, next_index)

        # at most 3 segments influenced.
        self._update_segment_ui(index - 1, index)
        self._update_segment_ui(index, next_index)
        self._update_segment_ui(next_index, next_index + 1)

    # return False if there is time collision.
    def _left_sort_key_index(self, index, now_time_tick: int) -> bool:
        while True:
            if index > 0:
                compare_index = index - 1
                compare_time_tick = self._get_time_tick_from_index(compare_index)
                if compare_time_tick > now_time_tick:
                    self._swap_2_keys(compare_index, index)
                    index -= 1
                    # while True goes on
                elif compare_time_tick < now_time_tick:
                    # here, the order is ok
                    break
                else:  # Time collion found.
                    self._swap_2_keys(compare_index, index)
                    # swap first so hole is at right.
                    return False
            else:
                # here, the index is the last key index.
                break

        return True

    # return False if there is time collision.
    def _right_sort_key_index(self, index, now_time_tick: int) -> bool:
        while True:
            if index < self._get_segment_quantity():
                compare_index = index + 1
                compare_time_tick = self._get_time_tick_from_index(compare_index)
                if compare_time_tick < now_time_tick:
                    self._swap_2_keys(index, compare_index)
                    index += 1
                    # while True goes on
                elif compare_time_tick > now_time_tick:
                    # here, the order is ok
                    break
                else:  # Time collion found.
                    return False
            else:
                # here, the index is the last key index.
                break

        return True

    # after _sort_key_index(), the _sample_tangents are reordered if needed. _sample_tangents might contain collision time keys that USD forgets. If there is time collsion, the hole key is to the right of original key.
    # return False if there is time collision
    def _sort_key_index(self, index, new_time_tick: int) -> bool:
        old_time_tick = self._get_time_tick_from_index(index)
        # bidirectional sort.
        if new_time_tick > old_time_tick:
            return self._right_sort_key_index(index, new_time_tick)
        else:
            return self._left_sort_key_index(index, new_time_tick)

    # return non-conflict time_tick
    def _relocate_key_time_tick(self, index, new_time_tick: int):
        while True:
            new_time_tick -= 1
            index -= 1
            if index < 0:
                break
            compare_time_tick = self._get_time_tick_from_index(index)
            if new_time_tick > compare_time_tick:
                break
            elif new_time_tick == compare_time_tick:
                continue
            else:  # new_time_tick < compare_time_tick
                carb.log_warn("Unexpected code path in CurveOfAttribute._relocate_key_time_tick()")
                continue
        return new_time_tick

    # this must be called before the move changes the USD attribute of the prev_time_tick and next_time_tick.
    def _cache_tangents_4_move_undo(self, key_rect):
        if hasattr(key_rect, "_pressed_values"):
            index = self._get_key_index(key_rect)
            # cache controls for undo command. only cache values not cached before.
            if index > 0:
                prev_index = index - 1
                prev_time_tick = self._get_time_tick_from_index(prev_index)
                if not (prev_time_tick in key_rect._pressed_values[6]):
                    key_rect._pressed_values[6][prev_time_tick] = []
                    key_rect._pressed_values[6][prev_time_tick].append(
                        self._sample_tangents[prev_index].get_in_time_tick()
                    )
                    key_rect._pressed_values[6][prev_time_tick].append(self._sample_tangents[prev_index].get_in_value())
                    key_rect._pressed_values[6][prev_time_tick].append(
                        self._sample_tangents[prev_index].get_out_time_tick()
                    )
                    key_rect._pressed_values[6][prev_time_tick].append(
                        self._sample_tangents[prev_index].get_out_value()
                    )
            if index < self._get_segment_quantity():
                next_index = index + 1
                next_time_tick = self._get_time_code_from_index(next_index)
                if not (next_time_tick in key_rect._pressed_values[6]):
                    key_rect._pressed_values[6][next_time_tick] = []
                    key_rect._pressed_values[6][next_time_tick].append(
                        self._sample_tangents[next_index].get_in_time_tick()
                    )
                    key_rect._pressed_values[6][next_time_tick].append(self._sample_tangents[next_index].get_in_value())
                    key_rect._pressed_values[6][next_time_tick].append(
                        self._sample_tangents[next_index].get_out_time_tick()
                    )
                    key_rect._pressed_values[6][next_time_tick].append(
                        self._sample_tangents[next_index].get_out_value()
                    )

    def _on_on_key_x_moved_internal(self, key_rect, offset_x: float, snap: bool):
        time_code = self._view_wp()._get_value_x(offset_x, snap=snap)
        time_tick = time_code_to_time_tick(time_code, self._time_codes_per_second)

        # sort based on self._sample_tangents.tick
        old_index = self._get_key_index(key_rect)
        old_time_tick = self._get_time_tick_from_index(old_index)
        is_perfect_sort = self._sort_key_index(old_index, time_tick)

        # after sort, the index might have been changed.
        index = self._get_key_index(key_rect)

        # time collision handling. Cook a fallback_time that is not the same as others.
        if is_perfect_sort == False:
            time_tick_corrected = self._relocate_key_time_tick(index, time_tick)
            is_perfect_sort_corrected = self._sort_key_index(index, time_tick_corrected)
            if is_perfect_sort_corrected == True:
                carb.log_warn(
                    f"Moving a key to time {time_code}:{time_tick} collide with an existing key. Relocate the key to time *:{time_tick_corrected}"
                )
                nm.post_notification(
                    f"Moving a key to time {time_code}:{time_tick} collide with an existing key. Relocate the key to time *:{time_tick_corrected}",
                    status=nm.NotificationStatus.WARNING,
                    duration=5,
                )
                # after sort, the index and time change.
                index = self._get_key_index(key_rect)
                time_tick = time_tick_corrected
                time_code = self._time_tick_to_time_code(time_tick_corrected)
            else:
                carb.log_error("Unexpected code path in CurveOfAttribute._on_on_key_x_moved_internal()")

        if index != old_index:
            # the key has just been set to a different index. Cache relevant tangents before _kmb_move_manage changes tangents.
            self._cache_tangents_4_move_undo(key_rect)

        # here. the time_tick might have been adjusted by snap and collision correction.
        # Underlying (runtime) scene data update. no control change. control change will take place in later _kmb_move_manage.
        self._move_key_time(old_index, old_time_tick, index, time_tick)

        # _set_key_ui_x will not cause recursive callback because only drag rect has callback
        offset_x = self._get_offset_x_from_time(time_code)
        key_rect._set_key_ui_x(offset_x)

        # corresponding infinity curve notification.
        self._notify_infinity_curve_anchor_x_change(old_index, index)

        # final update controls accordingly.
        self._kmb_move_manage(index)

    def _on_on_key_x_moved(self, key_rect, delta_ui_x):
        old_offset_x = key_rect._kmb_values[0]
        offset_x = old_offset_x + delta_ui_x
        self._on_on_key_x_moved_internal(key_rect, offset_x, snap=False)

    def _on_key_x_moved(self, key_rect):
        self._view_wp()._on_key_x_moved(key_rect)

    def _on_on_key_y_moved(self, key_rect, delta_ui_y):
        index = self._get_key_index(key_rect)
        # update key attribute value
        old_offset_y = key_rect._kmb_values[1]
        now_offset_y = old_offset_y + delta_ui_y
        key_rect._set_key_ui_y(now_offset_y)
        self._move_key_value(index, self._get_value_y(now_offset_y))

        # corresponding infinity curve notification.
        self._notify_infinity_curve_anchor_y_change(index)

        self._kmb_move_manage(index)

    def _on_key_y_moved(self, key_rect):
        self._view_wp()._on_key_y_moved(key_rect)

    # the final step move callback
    def _post_key_xy_changed(self, key_rect):
        if not hasattr(key_rect, "_pressed_values"):
            carb.log_warn(
                "Key move operation command broken. It also happens when multiple overlapping keys are selected."
            )
            return

        offset_x = key_rect.get_key_ui_x()
        self._on_on_key_x_moved_internal(key_rect, offset_x, snap=True)

        ## drag align.
        #
        # this is useful for both x_moved and y_moved
        key_rect._drag_align()
        #  this is mostly useful for x_moved.
        index = self._get_key_index(key_rect)
        self._control_drag_align(index)
        if index > 0:
            # here only the out_control needs align in fact
            self._control_drag_align(index - 1)
        if index < self._get_segment_quantity():
            # here only the in_control needs align in fact
            self._control_drag_align(index + 1)

        # the control visibility might change if the move changes the first or the last key.
        self._ttc_update_control_visibility(index, True)

        ## intend to get the change during mouse move. Record key move in one command. Record each control move in one command. And group them in one group command.
        #

        # all the following commands does not change attribute again because they have edit scope based branch code.
        with self._usd_edit_scope():
            index = self._get_key_index(key_rect)
            # prepare data for commands
            track_name = self.get_track_name()
            new_time_tick = self._get_time_tick_from_index(index)
            new_value = self._get_value_from_scratchpad(index)
            new_in_time_tick = self._sample_tangents[index].get_in_time_tick()
            new_in_value = self._sample_tangents[index].get_in_value()
            new_out_time_tick = self._sample_tangents[index].get_out_time_tick()
            new_out_value = self._sample_tangents[index].get_out_value()
            old_time_tick = key_rect._pressed_values[0]
            old_value = key_rect._pressed_values[1]
            old_in_time_tick = key_rect._pressed_values[2]
            old_in_value = key_rect._pressed_values[3]
            old_out_time_tick = key_rect._pressed_values[4]
            old_out_value = key_rect._pressed_values[5]
            if (new_time_tick != old_time_tick) or (
                new_in_time_tick != old_in_time_tick
                or new_in_value != old_in_value
                or new_out_time_tick != old_out_time_tick
                or new_out_value != old_out_value
                or new_value != old_value
            ):
                # create a group command only when there is real change.
                with omni.kit.undo.group():
                    # this (time value) change.
                    selection_state = omni.anim.curve.core.KeySelectionState(
                        track_name,
                        {old_time_tick: omni.anim.curve.core.KeySelectionState.SelectFlag(True, False, False)},
                    )
                    time = self._time_tick_to_time_code(new_time_tick)
                    time = self._time_code_for_timeline_node_command(time)
                    omni.kit.commands.execute(
                        "EditAnimCurveKeys", selection_state=selection_state, time=time, value=new_value
                    )

        # anyway the _pressed_values is no longer useful now.
        delattr(key_rect, "_pressed_values")
        # do similarly to _kmb_values
        delattr(key_rect, "_kmb_values")

    # a helper function for move|press conflict on multiple keys at same position.
    def _reverse_on_on_key_pressed(self, key_rect):
        if hasattr(key_rect, "_pressed_values"):
            delattr(key_rect, "_pressed_values")
            delattr(key_rect, "_kmb_values")

    def _on_on_key_pressed(self, key_rect):
        self._pre_key_xy_changed(key_rect)

    def _on_key_pressed(self, key_rect, modifier):
        self._view_wp()._on_key_pressed(key_rect, modifier)

    def _on_on_key_released(self, key_rect):
        self._post_key_xy_changed(key_rect)

    def _on_key_released(self, key_rect):
        self._view_wp()._on_key_released(key_rect)

    def _pre_tangent_broken_changed(self, key_rect):
        key_rect.old_tangent_broken = key_rect.get_tangent_broken()

    def _post_tangent_broken_changed(self, key_rect):
        new_tangent_broken = key_rect.get_tangent_broken()
        old_tangent_broken = key_rect.old_tangent_broken
        if new_tangent_broken == old_tangent_broken:
            carb.log_warn(
                "_post_tangent_broken_changed futile code path. Better avoid unnecessary tangentBroken change earlier."
            )
            return

        with self._usd_edit_scope():
            index = self._get_key_index(key_rect)
            time_tick = self._get_time_tick_from_index(index)

            if new_tangent_broken != old_tangent_broken:
                selection_state = omni.anim.curve.core.KeySelectionState(
                    self.get_track_name(),
                    {time_tick: omni.anim.curve.core.KeySelectionState.SelectFlag(True, False, False)},
                )
                omni.kit.commands.execute(
                    "EditAnimCurveKeys", selection_state=selection_state, tangent_broken=new_tangent_broken
                )

            delattr(key_rect, "old_tangent_broken")

    def _command_set_tangent_broken(self, key_rect, is_tangent_broken: bool):
        index = self._get_key_index(key_rect)
        # write to USD
        self._set_tangent_broken_to_runtime(index, is_tangent_broken)

    def _command_simplify(self):
        omni.kit.commands.execute("SimplifyAnimCurves", paths=[get_runtime_style_attribute_name(self.get_track_name())])

    def _command_set_pre_infinity_type(self, infinity_type: CurveInfinityTypes.InfinityType):
        with self._usd_edit_scope():
            omni.kit.commands.execute(
                "SetAnimCurveInfinityType",
                paths=[get_runtime_style_attribute_name(self.get_track_name())],
                is_post_infinity=False,
                infinity_type=CurveInfinityTypes.InfinityType.to_infinity_type_token(infinity_type),
            )

        self._notify_infinity_curve_pre_type_change(infinity_type)

    def _command_set_post_infinity_type(self, infinity_type: CurveInfinityTypes.InfinityType):
        with self._usd_edit_scope():
            omni.kit.commands.execute(
                "SetAnimCurveInfinityType",
                paths=[get_runtime_style_attribute_name(self.get_track_name())],
                is_post_infinity=True,
                infinity_type=CurveInfinityTypes.InfinityType.to_infinity_type_token(infinity_type),
            )

        self._notify_infinity_curve_post_type_change(infinity_type)

    def _pre_tangent_weighted_changed(self, key_rect):
        key_rect.old_tangent_weighted = key_rect.get_tangent_weighted()

    def _post_tangent_weighted_changed(self, key_rect):
        new_tangent_weighted = key_rect.get_tangent_weighted()
        old_tangent_weighted = key_rect.old_tangent_weighted
        if new_tangent_weighted == old_tangent_weighted:
            carb.log_warn(
                "_post_tangent_weighted_changed futile code path. Better avoid unnecessary tangentWeighted change earlier."
            )
            return

        with self._usd_edit_scope():
            index = self._get_key_index(key_rect)
            time_tick = self._get_time_tick_from_index(index)
            if new_tangent_weighted != old_tangent_weighted:
                selection_state = omni.anim.curve.core.KeySelectionState(
                    self.get_track_name(),
                    {time_tick: omni.anim.curve.core.KeySelectionState.SelectFlag(True, False, False)},
                )
                omni.kit.commands.execute(
                    "EditAnimCurveKeys", selection_state=selection_state, tangent_weighted=new_tangent_weighted
                )

            delattr(key_rect, "old_tangent_weighted")

    def _command_set_tangent_weighted(self, key_rect, is_tangent_weighted: bool):
        index = self._get_key_index(key_rect)
        # write to USD
        self._set_tangent_weighted_to_runtime(index, is_tangent_weighted)

        # Use key's weighted flag unless the ends controls. They are always weighted to simplify drag handling.
        self._in_control_rects[index]._command_set_tangent_weighted(is_tangent_weighted)
        self._out_control_rects[index]._command_set_tangent_weighted(is_tangent_weighted)

    # internal wrapper only.
    def _ttc_update_control_united(self, index):
        self._in_control_rects[index]._set_drag_ui_offset()
        self._out_control_rects[index]._set_drag_ui_offset()
        self._ttc_update_control_visibility(index, self._key_rects[index] in self._view_wp()._get_multi_selected_keys())
        self._control_drag_align(index)

    # get this curve's selection from track data, append in curve_select_keys_wp
    def _get_selection(self, select_keys_wp):
        for index in range(self._get_key_quantity()):
            time_tick = self._get_time_tick_from_index(index)
            if get_track_is_selected(self.get_track_name(), time_tick):
                select_keys_wp.append(weakref.ref(self._key_rects[index]))

    # refresh how controls and segments should present.
    # can be called when USD reload is not needed.
    def _refresh_control_related_ui(self):
        for index in range(self._get_key_quantity()):
            self._ttc_update_control_proxy(index)
            self._control_drag_align(index)
            # segment still needs to update though controls are not changed, because it may be flat type.
            self._ttc_update_segment(index - 1)

    # ui response.
    def _on_ttc_manager_changed(self, index):
        in_control_rect = self._in_control_rects[index]
        out_control_rect = self._out_control_rects[index]

        # write to USD
        self._set_tangent_type_to_runtime(
            index, in_control_rect.get_tangent_type(), out_control_rect.get_tangent_type()
        )

        # update control offset and visibility and so on.
        self._ttc_update_control_united(index)

        # update the curve segments at both sides of the key.
        self._ttc_update_segment(index - 1)
        self._ttc_update_segment(index)

    def _on_in_ttc_manager_changed(self, control_rect):
        index = self._get_in_control_index(control_rect)
        self._on_ttc_manager_changed(index)

    def _on_out_ttc_manager_changed(self, control_rect):
        index = self._get_out_control_index(control_rect)
        self._on_ttc_manager_changed(index)

    def _pre_tangent_type_changed(self, key_rect):
        index = self._get_key_index(key_rect)

        # no independant in or out tangent change because of USD data coupling.
        key_rect.old_in_tangent_type = key_rect.get_in_tangent_type()
        key_rect.old_out_tangent_type = key_rect.get_out_tangent_type()
        key_rect.old_in_time_tick = self._sample_tangents[index].get_in_time_tick()
        key_rect.old_in_value = self._sample_tangents[index].get_in_value()
        key_rect.old_out_time_tick = self._sample_tangents[index].get_out_time_tick()
        key_rect.old_out_value = self._sample_tangents[index].get_out_value()

    def _post_tangent_type_changed(self, key_rect):
        # no independant in or out tangent change because of USD data coupling.
        new_in_type = key_rect.get_in_tangent_type()
        new_out_type = key_rect.get_out_tangent_type()
        old_in_type = key_rect.old_in_tangent_type
        old_out_type = key_rect.old_out_tangent_type
        if (new_in_type == old_in_type) and (new_out_type == old_out_type):
            carb.log_warn(
                "_post_tangent_type_changed futile code path. Better avoid unnecessary tangentType change earlier."
            )
            return

        with self._usd_edit_scope():
            index = self._get_key_index(key_rect)
            time_tick = self._get_time_tick_from_index(index)
            # make command with group
            with omni.kit.undo.group():
                if new_in_type != old_in_type:
                    selection_state = omni.anim.curve.core.KeySelectionState(
                        self.get_track_name(),
                        {time_tick: omni.anim.curve.core.KeySelectionState.SelectFlag(False, True, False)},
                    )
                    omni.kit.commands.execute(
                        "EditAnimCurveKeys",
                        selection_state=selection_state,
                        tangent_type=CurveInterpolation.TangentType.to_tangent_type_token(new_in_type),
                    )

                if new_out_type != old_out_type:
                    selection_state = omni.anim.curve.core.KeySelectionState(
                        self.get_track_name(),
                        {time_tick: omni.anim.curve.core.KeySelectionState.SelectFlag(False, False, True)},
                    )
                    omni.kit.commands.execute(
                        "EditAnimCurveKeys",
                        selection_state=selection_state,
                        tangent_type=CurveInterpolation.TangentType.to_tangent_type_token(new_out_type),
                    )

            delattr(key_rect, "old_in_tangent_type")
            delattr(key_rect, "old_out_tangent_type")
            delattr(key_rect, "old_in_time_tick")
            delattr(key_rect, "old_in_value")
            delattr(key_rect, "old_out_time_tick")
            delattr(key_rect, "old_out_value")

    def _command_set_in_tangent_type(self, key_rect, type: int):
        index = self._get_key_index(key_rect)
        if type == CurveInterpolation.TangentType.Step:
            # Must skip if type is Step for in_tangent before.
            carb.log_error("Unexpected code path in CurveOfAttribute._command_set_in_tangent_type()")
            pass
        else:
            self._in_control_rects[index]._command_set_tangent_type(type)

    def _command_set_out_tangent_type(self, key_rect, type: int):
        index = self._get_key_index(key_rect)
        self._out_control_rects[index]._command_set_tangent_type(type)

    def _create_ttc_manager(self, type: int, weighted: bool):
        return create_ttc_manager(type, weighted)

    def _create_kmb_manager(self):
        return create_kmb_manager()

    def _get_rect_args(self, index):
        has_prev = index > 0
        has_next = index < self._get_segment_quantity()
        key_rect = self._key_rects[index]
        in_control_rect = self._in_control_rects[index]
        out_control_rect = self._out_control_rects[index]
        prev_key_rect = self._key_rects[index - 1] if has_prev else None
        prev_out_control_rect = self._out_control_rects[index - 1] if has_prev else None
        next_key_rect = self._key_rects[index + 1] if has_next else None
        next_in_control_rect = self._in_control_rects[index + 1] if has_next else None
        return (
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
        )

    def _ttc_on_in_control_moved(self, index):
        (
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
        ) = self._get_rect_args(index)
        prev_segment = self._segment_list[index - 1] if prev_key_rect else None
        in_control_rect._get_ttc_manager().on_in_control_moved(
            key_rect, prev_key_rect, next_key_rect, in_control_rect, prev_out_control_rect, prev_segment
        )

    def _ttc_on_out_control_moved(self, index):
        (
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
        ) = self._get_rect_args(index)
        segment = self._segment_list[index] if next_key_rect else None
        out_control_rect._get_ttc_manager().on_out_control_moved(
            key_rect, prev_key_rect, next_key_rect, out_control_rect, next_in_control_rect, segment
        )

    def _ttc_update_control_proxy(self, index):
        (
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
        ) = self._get_rect_args(index)
        in_control_rect._get_ttc_manager().update_control_proxy(key_rect, in_control_rect)
        out_control_rect._get_ttc_manager().update_control_proxy(key_rect, out_control_rect)

    def _ttc_update_control_visibility(self, index, active):
        (
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
        ) = self._get_rect_args(index)
        prev_out_manager = prev_out_control_rect._get_ttc_manager() if prev_key_rect else None
        next_in_manager = next_in_control_rect._get_ttc_manager() if next_key_rect else None
        in_control_line = self._in_control_lines[index]
        out_control_line = self._out_control_lines[index]
        in_control_rect._get_ttc_manager().update_in_control_visibility(
            active, prev_out_manager, in_control_rect, in_control_line
        )
        out_control_rect._get_ttc_manager().update_out_control_visibility(
            active, next_in_manager, out_control_rect, out_control_line
        )

    def _ttc_update_segment(self, index):
        if index < 0 or index >= self._get_segment_quantity():
            return
        (
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
        ) = self._get_rect_args(index)
        segment = self._segment_list[index]
        out_control_rect._get_ttc_manager().update_segment(
            segment, key_rect, next_key_rect, out_control_rect, next_in_control_rect
        )

    def _kmb_move_manage(self, index):
        (
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
        ) = self._get_rect_args(index)
        step_rect = self._step_rects[index] if next_key_rect else None
        prev_step_rect = self._step_rects[index - 1] if prev_key_rect else None
        prev_in_control_rect = self._in_control_rects[index - 1] if prev_key_rect else None
        next_out_control_rect = self._out_control_rects[index + 1] if next_key_rect else None
        key_rect._get_kmb_manager().move_manage(
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_in_control_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
            next_out_control_rect,
            step_rect,
            prev_step_rect,
        )


class CurveListView:
    def __init__(self, parent_curve_editor_timeline: TimelineView):

        self._timeline_wp = weakref.ref(parent_curve_editor_timeline)
        self._curve_list = []
        self._curve_frame_list = []
        self._curve_list_used_quantity = 0
        self._omni_time_range_frame = None
        self._curve_list_frame = None
        self._selected_key_wp = None
        self._multi_selected_keys_wp = []
        self._multi_selection_frame = None
        self._selected_control_rect_wp = None
        self._ruler = None
        self._copy_key_paths = []
        self._copy_schema_keys = []

        self._curve_list_frame_z_stack = None
        self._key_rect_size = 6
        self._control_rect_size = 8

        self._key_movement_type = 0

        self._fit_overhead = 0.1
        self._fit_min_delta_value_x = 1
        self._fit_min_delta_value_y = 0.01
        self._fit_default_min_value_y = -50.0
        self._fit_default_max_value_y = 50.0

        self._special_refit_flag = False
        self.raise_refit_flag()
        self.raise_update_flag()

    # some entry in self._curve_list is None after curve removal. Get the existing for convenience.
    def _get_existing_curves(self):
        existing = []
        for curve in self._curve_list:
            if curve != None:
                existing.append(curve)

        return existing

    # from the existing curves, get the visible ones
    def _get_existing_visible_curves(self):
        existing_visible = []
        for curve in self._curve_list:
            if curve != None and self._is_curve_visible(curve):
                existing_visible.append(curve)

        return existing_visible

    def _get_selected_control(self):
        return self._selected_control_rect_wp() if self._selected_control_rect_wp else None

    def _get_selected_key(self):
        return self._selected_key_wp() if self._selected_key_wp else None

    def _get_multi_selected_keys(self):
        result = []
        for key_wp in self._multi_selected_keys_wp:
            if key_wp():
                result.append(key_wp())
        return result

    def _get_multi_selected_curves(self):
        result = []
        for key_wp in self._multi_selected_keys_wp:
            if key_wp():
                curve = key_wp()._curve_wp()
                if curve and not (curve in result):
                    result.append(curve)

        return result

    def _get_value_x(self, offset_x, snap=False) -> float:
        # always use transform_position_to_timeline's without snap.
        result = self.get_curve_editor_timeline().transform_position_to_timeline(offset_x, snap=False)
        if snap:
            # find the nearest int. This is questionable, but in timeline_view.transform_position_to_timeline(snap = True) implementation, the result is just int(). If that is acceptable, I am here to do round() instead of int().
            result = round(result)

        return result

    def _get_value_y(self, offset_y) -> float:
        return (self._pixels_height - offset_y) / self._value2pixel + self._min_value_y

    def _get_key_rect_size(self):
        return self._key_rect_size

    def _get_control_rect_size(self):
        return self._control_rect_size

    def _get_curve_color(self, name: str):
        return self.get_curve_editor_view().get_curve_color(name)

    def _is_key_x_movable(self) -> bool:
        return self._key_movement_type == 0 or self._key_movement_type == 2

    def _is_key_y_movable(self) -> bool:
        return self._key_movement_type == 0 or self._key_movement_type == 1

    # Attention. It uses _sample_tangents. It might not return expected value based on context.
    def _get_key_time_tick(self, key_rect):
        return key_rect._curve_wp()._get_time_tick_from_index(key_rect._curve_wp()._get_key_index(key_rect))

    # For value to be unique for every key. It is different from a key press-move-release operation
    def _command_set_selection_value(self, value: float):
        selected_keys = self._get_multi_selected_keys()
        selected_key = self._get_selected_key()
        if selected_key == None:
            return

        # simulate as several move operations with only one selected key.
        with omni.kit.undo.group():
            offset_y = self._get_offset_y_from_value(value)
            for key_rect in selected_keys:
                self._set_multi_selected_keys([weakref.ref(key_rect)])
                key_rect._command_set_key_ui_y(offset_y)

        ## restore selection status
        #
        for key_rect in selected_keys:
            self._add_multi_selected_keys([weakref.ref(key_rect)])

        self._set_single_selected_key_wp(weakref.ref(selected_key))

    # For time, it is a simple simulation of a key press-move_release operation
    def _command_set_selection_time(self, time: float):
        if self._get_selected_key():
            offset_x = self._get_offset_x_from_time(time)
            self._get_selected_key()._command_set_key_ui_x(offset_x)

    def _get_previous_key_time(self, time):
        previous_key_times = []
        for curve in self._get_existing_visible_curves():
            curve_time = curve._get_prevoius_key_time(time)
            if curve_time < time:
                # curve has a real previous key.
                previous_key_times.append(curve_time)

        if len(previous_key_times) == 0:
            # no real previous found.
            return time
        else:
            return max(previous_key_times)

    def _get_next_key_time(self, time):
        next_key_times = []
        for curve in self._get_existing_visible_curves():
            curve_time = curve._get_next_key_time(time)
            if curve_time > time:
                # curve has a real next key.
                next_key_times.append(curve_time)

        if len(next_key_times) == 0:
            # no real next found.
            return time
        else:
            return min(next_key_times)

    def _command_set_key_movement_direction(self, key_movement_type: int):
        self._key_movement_type = key_movement_type

    def _command_set_infinity_type(self, infinity_type: CurveInfinityTypes.InfinityType, is_pre_infinity: bool):
        selected_curves = self._get_multi_selected_curves()
        with omni.kit.undo.group():
            for curve in selected_curves:
                if is_pre_infinity:
                    curve._command_set_pre_infinity_type(infinity_type)
                else:
                    curve._command_set_post_infinity_type(infinity_type)

    def _command_set_tangent_broken(self, is_tangent_broken):
        selected_keys = self._get_multi_selected_keys()
        with omni.kit.undo.group():
            for key_rect in selected_keys:
                key_rect._command_set_tangent_broken(is_tangent_broken)

    def _command_set_tangent_weighted(self, is_tangent_weighted):
        selected_keys = self._get_multi_selected_keys()
        with omni.kit.undo.group():
            for key_rect in selected_keys:
                key_rect._command_set_tangent_weighted(is_tangent_weighted)

    def _command_set_in_tangent_type(self, type: int):
        selected_keys = self._get_multi_selected_keys()
        with omni.kit.undo.group():
            for key_rect in selected_keys:
                key_rect._command_set_in_tangent_type(type)

    def _command_set_out_tangent_type(self, type: int):
        selected_keys = self._get_multi_selected_keys()
        with omni.kit.undo.group():
            for key_rect in selected_keys:
                key_rect._command_set_out_tangent_type(type)

    def _command_add_key(self, timecode):
        curve_paths = []
        curve_tangent_types = []
        for curve in self._get_existing_visible_curves():
            curve_paths.append(get_runtime_style_attribute_name(curve.get_track_name()))
            curve_tangent_types.append(curve._get_default_tangent_type())

        if len(curve_paths) > 0:
            with omni.kit.undo.group():
                for i in range(len(curve_paths)):
                    curve_path = curve_paths[i]
                    curve_tangent_type = curve_tangent_types[i]
                    # use default auto tangent types as preserveCurveShape = True code path
                    omni.kit.commands.execute(
                        "SetAnimCurveKeys",
                        time=Usd.TimeCode(timecode),
                        paths=[curve_path],
                        preserveCurveShape=curve_tangent_type == CurveInterpolation.TangentType.Automatic,
                    )

    def _command_delete_key(self):
        selected_keys = self._get_multi_selected_keys()
        if len(selected_keys) == 0:
            nm.post_notification(
                "Animation Curve Editor: No key is selected when trying to remove keys!",
                status=nm.NotificationStatus.WARNING,
                duration=5,
            )
            carb.log_info("Animation Curve Editor: No key is selected when trying to remove keys!")
            return

        paths_and_times = []
        for key_rect in selected_keys:
            path = get_runtime_style_attribute_name(key_rect._curve_wp().get_track_name())
            time = key_rect._curve_wp()._time_tick_to_time_code(self._get_key_time_tick(key_rect))
            time = key_rect._curve_wp()._time_code_for_timeline_node_command(time)
            # carb.log_info("RemoveAnimCurveKeys with time code is not precise enough. Using time tick might be a better option.")
            paths_and_times.append([path, time])

        with omni.kit.undo.group():
            # clear selection, with omni command inside.
            self._set_multi_selected_keys([])
            # remove usd keys
            for path_and_time in paths_and_times:
                omni.kit.commands.execute(
                    "RemoveAnimCurveKeys",
                    stage=omni.usd.get_context().get_stage(),
                    paths=[path_and_time[0]],
                    time=Usd.TimeCode(path_and_time[1]),
                )

    def _command_copy_key(self):
        selected_keys = self._get_multi_selected_keys()
        clipboard = get_curvekey_clipboard()
        clipboard.clear()
        for key_rect in selected_keys:
            curve = key_rect._curve_wp()
            schema_key = curve._get_schema_key(curve._get_key_index(key_rect))
            clipboard.add_key(curve._user, curve.get_name(), [schema_key])
        # Sort the keys such that the key with smalledst timecode become the base time
        # of all the copied keys, which is useful when you paste the keys, at a new base time
        clipboard.sort_keys()

    def _command_paste_key(self, timecode):
        clipboard = get_curvekey_clipboard()
        if clipboard.get_prim_count() == 0:
            carb.log_warn("Curve Editor Paste Key Fail! There is nothing in the clipboard!")
            return
        selected_curves_paths = [curve.get_track_name() for curve in self._get_existing_visible_curves()]
        if len(selected_curves_paths) == 0:
            carb.log_warn("Curve Editor Paste Key: No target curve is selected!")
            return

        if clipboard.get_curve_count() == 1:
            copied_prim_path = clipboard.get_prim_name(0)
            copied_curve_name = clipboard.get_curve_name(0, 0)
            copied_curve_path = copied_prim_path + "." + copied_curve_name
            paste_paths = []
            if copied_curve_path in selected_curves_paths:
                paste_paths.append(get_runtime_style_attribute_name(copied_curve_path))
            else:
                paste_paths.append(get_runtime_style_attribute_name(selected_curves_paths[0]))

            omni.kit.commands.execute(
                "PasteAnimCurveKeys",
                paths=paste_paths,
                time=Usd.TimeCode(timecode),
            )
        else:
            paste_paths = []
            unmatched_selected_curve_path = []
            for prim_idx in range(clipboard.get_prim_count()):
                copied_prim_path = clipboard.get_prim_name(prim_idx)
                for curve_idx in range(clipboard.get_curve_count(prim_idx)):
                    copied_curve_name = clipboard.get_curve_name(prim_idx, curve_idx)
                    copied_curve_path = copied_prim_path + "." + copied_curve_name

                    if copied_curve_path in selected_curves_paths:
                        paste_paths.append(copied_curve_path)

            unmatched_selected_curve_path = [
                curve_path for curve_path in selected_curves_paths if curve_path not in paste_paths
            ]
            paste_paths = paste_paths + unmatched_selected_curve_path
            dst_paths = []
            for paste_path in paste_paths:
                dst_paths.append(get_runtime_style_attribute_name(paste_path))
            omni.kit.commands.execute(
                "PasteAnimCurveKeys",
                paths=dst_paths,
                time=Usd.TimeCode(timecode),
            )

    # return True is success.
    def _command_new_curve(self, user_attribute_name: str, components_quantity: int) -> bool:
        # try early return
        if len(self._get_prims_obsolete()) == 0 or user_attribute_name == "":
            return False
        else:
            for prim in self._get_prims_obsolete():
                if not prim:
                    continue

                if is_curve_data_prim(prim):
                    continue

                if is_timeline_node(prim):
                    # user_attribute_name is the port name. The usd attribute is port name prefixed with "outputs:"
                    if prim.GetAttribute("outputs:" + user_attribute_name).IsValid():
                        # do not override existing attribute
                        return False
                else:
                    if prim.GetAttribute(user_attribute_name).IsValid():
                        # do not override existing attribute
                        return False

        # really need to do some command.
        with omni.kit.undo.group():
            for prim in self._get_prims_obsolete():
                curve_paths = []
                if is_timeline_node(prim):
                    omni.kit.commands.execute(
                        "NewTimelineNodeAttributeCurveCommand",
                        prim_path=str(prim.GetPath()),
                        attr_name=user_attribute_name,
                        components_quantity=components_quantity,
                    )
                    # user_attribute_name is the port name. The usd attribute is port name prefixed with "outputs:"
                    curve_paths.append(str(prim.GetPath()) + ".outputs:" + user_attribute_name)
                    asyncio.ensure_future(omni.kit.app.get_app().next_update_async())
                else:
                    omni.kit.commands.execute(
                        "NewAttributeCurveCommand",
                        prim_path=str(prim.GetPath()),
                        attr_name=user_attribute_name,
                        components_quantity=components_quantity,
                    )
                    curve_paths.append(str(prim.GetPath()) + "." + user_attribute_name)

                omni.kit.commands.execute("AddAnimCurves", paths=curve_paths)

        return True

    def _command_simplify_curves(self):
        selected_curves = self._get_multi_selected_curves()
        with omni.kit.undo.group():
            for curve in selected_curves:
                curve._command_simplify()

    def _on_control_pressed(self, index, control_rect):
        control_rect._curve_wp()._on_control_pressed(index, control_rect)

        control_rect._view_pressed_values = []
        control_rect._view_pressed_values.append(control_rect._get_drag_ui_x())
        control_rect._view_pressed_values.append(control_rect._get_drag_ui_y())

    def _on_control_released(self, index, control_rect):
        control_rect._curve_wp()._on_control_released(index, control_rect)

        if not hasattr(control_rect, "_view_pressed_values"):
            carb.log_error("Unexpected code path is CurveListView._on_control_released()")
        else:
            delattr(control_rect, "_view_pressed_values")

    # find delta for the control_rect. The length delta is encoded in ratio(1.0 means no change), the angle delta is encoded in sin_angle and cos_angle.
    # return sin_angle, cos_angle, length_ratio
    def _get_control_delta(self, key_rect, control_rect) -> (float, float, float):
        old_offset_x = control_rect._view_pressed_values[0]
        old_offset_y = control_rect._view_pressed_values[1]
        pivot_offset_x = key_rect.get_key_ui_x()
        pivot_offset_y = key_rect.get_key_ui_y()
        old_delta_x = old_offset_x - pivot_offset_x
        old_delta_y = old_offset_y - pivot_offset_y
        new_delta_x = control_rect._get_drag_ui_x() - pivot_offset_x
        new_delta_y = control_rect._get_drag_ui_y() - pivot_offset_y
        old_length = math.sqrt(old_delta_x * old_delta_x + old_delta_y * old_delta_y)
        new_length = math.sqrt(new_delta_x * new_delta_x + new_delta_y * new_delta_y)
        dot_product = old_delta_x * new_delta_x + old_delta_y * new_delta_y
        cross_product = old_delta_x * new_delta_y - old_delta_y * new_delta_x
        if old_length < EDITOR_CONTROL_HANDLE_SMALL_LENGTH:
            # for robustness, just simplify this kind of dragging handling. otherwise cos_angle might div by zero.
            cos_angle = 1.0
            sin_angle = 0.0
            length_ratio = 1.0
        else:
            cos_angle = dot_product / (old_length * new_length)
            sin_angle = math.sqrt(max(0, 1 - cos_angle * cos_angle))
            if cross_product < 0:
                sin_angle = -sin_angle
            length_ratio = new_length / old_length

        return sin_angle, cos_angle, length_ratio

    # apply delta returned from _get_control_delta().
    def _apply_control_delta(self, key_rect, control_rect, sin_angle, cos_angle, length_ratio):
        # get offset_x and offset_y
        old_offset_x = control_rect._view_pressed_values[0]
        old_offset_y = control_rect._view_pressed_values[1]
        pivot_offset_x = key_rect.get_key_ui_x()
        pivot_offset_y = key_rect.get_key_ui_y()
        old_delta_x = old_offset_x - pivot_offset_x
        old_delta_y = old_offset_y - pivot_offset_y

        # calc new
        new_delta_x_wo_rot = old_delta_x * length_ratio
        new_delta_y_wo_rot = old_delta_y * length_ratio
        new_delta_x = cos_angle * new_delta_x_wo_rot - sin_angle * new_delta_y_wo_rot
        new_delta_y = sin_angle * new_delta_x_wo_rot + cos_angle * new_delta_y_wo_rot
        offset_x = pivot_offset_x + new_delta_x
        offset_y = pivot_offset_y + new_delta_y

        # apply offset_x and offset_y
        control_rect._set_drag_ui_offset(offset_x, offset_y)

    def _on_in_control_released(self, control_rect):
        selected_keys = self._get_multi_selected_keys()
        with omni.kit.undo.group():
            for key_rect in selected_keys:
                curve = key_rect._curve_wp()
                index = curve._get_key_index(key_rect)

                in_control_rect = curve._in_control_rects[index]
                self._on_control_released(index, in_control_rect)

                # if unbroken, the other control should be handled.
                if key_rect.get_tangent_broken() == False:
                    out_control_rect = curve._out_control_rects[index]
                    self._on_control_released(index, out_control_rect)

    def _on_in_control_pressed(self, control_rect):
        self._mark_pressed()

        selected_keys = self._get_multi_selected_keys()
        for key_rect in selected_keys:
            curve = key_rect._curve_wp()
            index = curve._get_key_index(key_rect)

            in_control_rect = curve._in_control_rects[index]
            self._on_control_pressed(index, in_control_rect)

            # if unbroken, the other control should be handled.
            if key_rect.get_tangent_broken() == False:
                out_control_rect = curve._out_control_rects[index]
                self._on_control_pressed(index, out_control_rect)

    def _on_in_control_moved(self, control_rect):
        if not hasattr(control_rect, "_view_pressed_values"):
            # not triggered by real user UI interaction.
            return

        # get delta
        curve = control_rect._curve_wp()
        index = curve._get_in_control_index(control_rect)
        key_rect = curve._key_rects[index]
        sin_angle, cos_angle, length_ratio = self._get_control_delta(key_rect, control_rect)

        # for every multi selection.
        selected_keys = self._get_multi_selected_keys()
        for key_rect in selected_keys:
            curve = key_rect._curve_wp()
            index = curve._get_key_index(key_rect)
            in_control_rect = curve._in_control_rects[index]
            # update in control if needed
            if in_control_rect != control_rect:
                self._apply_control_delta(key_rect, in_control_rect, sin_angle, cos_angle, length_ratio)
                in_control_rect._lazy_set_fixed()

            # update out control if unbroken.
            if key_rect.get_tangent_broken() == False:
                out_control_rect = curve._out_control_rects[index]
                self._apply_control_delta(key_rect, out_control_rect, sin_angle, cos_angle, length_ratio)
                out_control_rect._lazy_set_fixed()

    def _on_out_control_released(self, control_rect):
        selected_keys = self._get_multi_selected_keys()
        with omni.kit.undo.group():
            for key_rect in selected_keys:
                curve = key_rect._curve_wp()
                index = curve._get_key_index(key_rect)

                out_control_rect = curve._out_control_rects[index]
                curve._on_control_released(index, out_control_rect)

                # if unbroken, the other control should be handled.
                if key_rect.get_tangent_broken() == False:
                    in_control_rect = curve._in_control_rects[index]
                    self._on_control_released(index, in_control_rect)

    def _on_out_control_pressed(self, control_rect):
        self._mark_pressed()

        selected_keys = self._get_multi_selected_keys()
        for key_rect in selected_keys:
            curve = key_rect._curve_wp()
            index = curve._get_key_index(key_rect)

            out_control_rect = curve._out_control_rects[index]
            self._on_control_pressed(index, out_control_rect)

            # if unbroken, the other control should be handled.
            if key_rect.get_tangent_broken() == False:
                in_control_rect = curve._in_control_rects[index]
                self._on_control_pressed(index, in_control_rect)

    def _on_out_control_moved(self, control_rect):
        if not hasattr(control_rect, "_view_pressed_values"):
            # not triggered by real user UI interaction.
            return

        # get delta
        curve = control_rect._curve_wp()
        index = curve._get_out_control_index(control_rect)
        key_rect = curve._key_rects[index]
        sin_angle, cos_angle, length_ratio = self._get_control_delta(key_rect, control_rect)

        # for every multi selection.
        selected_keys = self._get_multi_selected_keys()
        for key_rect in selected_keys:
            curve = key_rect._curve_wp()
            index = curve._get_key_index(key_rect)
            out_control_rect = curve._out_control_rects[index]
            # update out control if needed
            if out_control_rect != control_rect:
                self._apply_control_delta(key_rect, out_control_rect, sin_angle, cos_angle, length_ratio)
                out_control_rect._lazy_set_fixed()

            # update in control if unbroken.
            if key_rect.get_tangent_broken() == False:
                in_control_rect = curve._in_control_rects[index]
                self._apply_control_delta(key_rect, in_control_rect, sin_angle, cos_angle, length_ratio)
                in_control_rect._lazy_set_fixed()

    def _set_selected_control(self, control_rect):
        if self._get_selected_control() != None:
            self._get_selected_control()._set_active_color(False)

        if control_rect != None:
            control_rect._set_active_color(True)
            self._selected_control_rect_wp = weakref.ref(control_rect)
        else:
            self._selected_control_rect_wp = None

    def _on_control_released_select(self, key_rect, control_rect):
        # cook a special modifier to make the single selection happen.
        self._update_multi_selected_keys(
            [weakref.ref(key_rect)],
            ~(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL | carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT),
        )
        # update control selection after key selection change, there is some redundant toolbar refresh but it is still better to update control selection here.
        self._set_selected_control(control_rect)
        self._show_the_one_of_the_selected()

    # helper to workaroud the omniUI's move_fn and press_fn cooperation problem.
    def _mark_pressed(self):
        self._foreground_pressed = True

    def _on_key_pressed(self, key_rect, modifier):
        self._mark_pressed()

        # If there are multiple keys pressed at the same position, multiple _on_key_pressed will be triggered. I can not avoid this behavior from current UI system.
        # I can only workaround this by reverse the effect of previous _on_key_pressed().
        selected_keys = self._get_multi_selected_keys()
        for one_selected_key_rect in selected_keys:
            curve = one_selected_key_rect._curve_wp()
            curve._reverse_on_on_key_pressed(one_selected_key_rect)

        if modifier == 0 and self._set_single_selected_key_wp(weakref.ref(key_rect)):
            # Special code path. If simple click on already select key, the selection set is not changed.
            pass
        else:
            # the selection set is somehow changed
            self._update_multi_selected_keys([weakref.ref(key_rect)], modifier)

        # The selection set( might has only one key ) can be moved together.
        selected_keys = self._get_multi_selected_keys()
        for one_selected_key_rect in selected_keys:
            curve = one_selected_key_rect._curve_wp()
            curve._on_on_key_pressed(one_selected_key_rect)

    def _on_curve_double_clicked(self, curve):
        self._mark_pressed()

        # set curve's keys as selected.
        selected_wp = []
        for key_rect in curve._key_rects:
            selected_wp.append(weakref.ref(key_rect))
        self._set_multi_selected_keys(selected_wp)

    # helper class to use a ChangeBlock with a EditScope.
    class MultiMoveChangeBlock:
        def __init__(self, curve_list_view):
            self._usd_edit_scope = curve_list_view._usd_edit_scope()
            self._change_block = Sdf.ChangeBlock()

        def __enter__(self):
            return self._change_block.__enter__()

        def __exit__(self, type, value, trace):
            with self._usd_edit_scope:
                # this is when the real USD notification is dispatched.
                self._change_block.__exit__(type, value, trace)

    # this is a hypothetical performance optimization, unit x and y callback when possible. But it is not supported by the current UI callback mechanism.
    def _on_key_x_then_y_moved(self, key_rect):
        # get delta_ui_x
        now_offset_x = key_rect._get_drag_ui_x()
        old_offset_x = key_rect._kmb_values[0]
        delta_ui_x = now_offset_x - old_offset_x

        # get delta_ui_y
        now_offset_y = key_rect.get_key_ui_y()
        old_offset_y = key_rect._kmb_values[1]
        delta_ui_y = now_offset_y - old_offset_y

        if old_offset_x == 0 or old_offset_y == 0:
            carb.log_error("Unexpected code path in CurveListView._on_key_x_then_y_moved()")

        with CurveListView.MultiMoveChangeBlock(self):
            selected_keys = self._get_multi_selected_keys()
            for one_selected_key_rect in selected_keys:
                curve = one_selected_key_rect._curve_wp()
                curve._on_on_key_x_moved(one_selected_key_rect, delta_ui_x)
                curve._on_on_key_y_moved(one_selected_key_rect, delta_ui_y)

        # any one of the multi selected keys can show the value in UI.
        self._show_selection_value(self._get_selected_key())

    def _on_key_y_moved(self, key_rect):
        # get delta_ui_y
        now_offset_y = key_rect.get_key_ui_y()
        old_offset_y = key_rect._kmb_values[1]
        delta_ui_y = now_offset_y - old_offset_y

        with CurveListView.MultiMoveChangeBlock(self):
            selected_keys = self._get_multi_selected_keys()
            for one_selected_key_rect in selected_keys:
                curve = one_selected_key_rect._curve_wp()
                curve._on_on_key_y_moved(one_selected_key_rect, delta_ui_y)

        # any one of the multi selected keys can show the value in UI.
        self._show_selection_value(self._get_selected_key())

    def _on_key_x_moved(self, key_rect):
        # get delta_ui_x
        now_offset_x = key_rect._get_drag_ui_x()
        old_offset_x = key_rect._kmb_values[0]
        delta_ui_x = now_offset_x - old_offset_x

        with CurveListView.MultiMoveChangeBlock(self):
            selected_keys = self._get_multi_selected_keys()
            for one_selected_key_rect in selected_keys:
                curve = one_selected_key_rect._curve_wp()
                curve._on_on_key_x_moved(one_selected_key_rect, delta_ui_x)

        # any one of the multi selected keys can show the value in UI.
        self._show_selection_value(self._get_selected_key())

    def _on_key_released(self, key_rect):
        if not hasattr(key_rect, "_kmb_values"):
            # this code path can happen when multiple keys at the same position are clicked and then released.
            # the previous _on_key_released() deletes all keys' _kmb_values
            return
        # here key_rect._kmb_values does exist

        # get delta_ui_x, for sort direction.
        now_offset_x = key_rect._get_drag_ui_x()
        old_offset_x = key_rect._kmb_values[0]
        delta_ui_x = now_offset_x - old_offset_x

        # sort selected keys, so that in the next group command, later MoveTimeCurveCommand does not mess up former key when there is time collision.
        selected_keys = self._get_multi_selected_keys()
        selected_keys.sort(reverse=(delta_ui_x > 0), key=lambda k: k.get_key_ui_x())

        with omni.kit.undo.group():  # todo. empty commands
            for one_selected_key_rect in selected_keys:
                curve = one_selected_key_rect._curve_wp()
                curve._on_on_key_released(one_selected_key_rect)

            # Finished dragging preview. Clear overriden keys.
            for one_selected_key_rect in selected_keys:
                curve = one_selected_key_rect._curve_wp()
                curve._overriden_keys = []

        # time might change after mouse release. value does not change.
        self._show_selection_time(key_rect)

    def _show_key_in_toolbar(self, key_rect, in_control_rect, out_control_rect):
        self.get_curve_editor_view().show_pre_infinity_type(key_rect.get_pre_infinity_type())
        self.get_curve_editor_view().show_post_infinity_type(key_rect.get_post_infinity_type())
        self.get_curve_editor_view().show_tangent_broken(key_rect.get_tangent_broken())
        self.get_curve_editor_view().show_tangent_weighted(key_rect.get_tangent_weighted())
        self._show_in_tangent_type(key_rect, in_control_rect)
        self._show_out_tangent_type(key_rect, out_control_rect)
        self._show_selection_value(key_rect)
        self._show_selection_time(key_rect)

    def _show_in_tangent_type(self, key_rect, in_control_rect):
        if self._get_selected_key() == key_rect:
            show_type = (
                in_control_rect.get_tangent_type()
                if self._get_selected_control() == in_control_rect or self._get_selected_control() == None
                else None
            )
            self.get_curve_editor_view().show_in_tangent_type(show_type)
        else:
            # The code path is possible, for example, for some _lazy_in_control_set_fixed()
            pass

    def _show_out_tangent_type(self, key_rect, out_control_rect):
        if self._get_selected_key() == key_rect:
            show_type = (
                out_control_rect.get_tangent_type()
                if self._get_selected_control() == out_control_rect or self._get_selected_control() == None
                else None
            )
            self.get_curve_editor_view().show_out_tangent_type(show_type)
        else:
            # The code path is possible, for example, for some _lazy_out_control_set_fixed()
            pass

    def _show_selection_value(self, key_rect):
        if self._get_selected_key() == key_rect:
            self.get_curve_editor_view().show_selection_value(key_rect._get_value_y())
        else:
            # The code path is possible when multiple keys at the same place. But only one is active
            pass

    def _show_selection_time(self, key_rect):
        if self._get_selected_key() == key_rect:
            self.get_curve_editor_view().show_selection_time(key_rect._get_value_x())
        else:
            # The code path is possible when multiple keys at the same place. But only one is active
            pass

    def raise_refit_flag(self):
        self._refit_flag = True

    # a special hacky flag to do refit for 2 times. only for very special case when the curve editor window is first shown after visibility is toggled on from the menu.
    # the root problem is TimelineView does not handle invisible 0 size range robustly. But I just want a quick hacky here.
    def raise_special_refit_flag(self):
        self._refit_flag = True
        self._special_refit_flag = True

    def take_refit_flag(self) -> bool:
        if self._refit_flag:
            if self._special_refit_flag:
                self._special_refit_flag = False
                # keep self._refit_flag here
            else:
                self._refit_flag = False
            return True
        else:
            return False

    def raise_update_flag(self):
        self._need_update = True

    def _take_update_flag(self) -> bool:
        if self._need_update:
            self._need_update = False
            return True
        else:
            return False

    # height might be changed. Do it when needed. Strict height change callback may be better.
    def _set_pixels_height(self):
        # self._curve_list_frame.computed_height might be 0 sometimes. patch to avoid later DivByZero error.
        self._pixels_height = (
            self._curve_list_frame.computed_height if self._curve_list_frame.computed_height > 1.0 else 1.0
        )

    def _update_fit(self, stage):
        self._set_pixels_height()
        # use original _max_value_y and _min_value_y, but new self._pixels_height.
        self._set_fit_value_y()

        if self.take_refit_flag():
            # it might change nothing, so previouis _set_fit_value_y() is necessary
            self._on_fit_all()

    # this is called once after build_ui() creates _curve_list_frame
    def _init_fit(self):
        self._set_pixels_height()
        # must has a valid _pixels_height before _set_default_fit_value_y()
        self._set_default_fit_value_y()

    def _retained_update(self, stage):
        if self._curve_list_frame == None:
            # build_ui is not called yet, update is not allowed especially for fitting.
            return

        if self._take_update_flag():
            self._update(stage)

    def _update_curve_list(self):
        for curve in self._get_existing_curves():
            curve.update_ui()

    # update for ui
    def _update(self, stage):
        self._update_fit(stage)
        self._update_omni_time_range()
        self._update_multi_selection()
        self._update_curve_list()
        self._ruler.range = (self._max_value_y, self._min_value_y)

    # ui build
    def build_ui(self):
        with ui.ZStack(height=ui.Percent(100)):
            guildline_frame = ui.Frame()
            guildline_frame.set_build_fn(lambda: self._build_guidelines(guildline_frame))

            self._ruler = Ruler(face_dir=Ruler.FaceDirection.Right, style={"Line": {"color": globals.GUIDELINE_COLOR}})

            self._omni_time_range_placer = ui.Placer(draggable=False, stable_size=True, offset_x=0, offset_y=0)
            with self._omni_time_range_placer:
                self._omni_time_range_frame = ui.Frame()
            self._multi_selection_frame = ui.Frame(mouse_pressed_fn=self._on_timeline_node_mouse_pressed)
            self._curve_list_frame = ui.Frame(name="curve_list_frame")

        with self._curve_list_frame:
            self._curve_list_frame_z_stack = ui.ZStack()
            with self._curve_list_frame_z_stack:
                # Init the _curve_frame_list here with self._curve_list_frame_z_stack only to help understand that the frames to be in self._curve_frame_list will be with self._curve_list_frame_z_stack.
                self._curve_list_used_quantity = 0
                self._curve_frame_list = []

        self._build_multi_selection()

        self._init_fit()

    def _build_guidelines(self, guidelines_frame):
        with guidelines_frame:
            guidelines = Guidelines(style={"Line": {"color": globals.GUIDELINE_COLOR}})

            time_ruler = self.get_curve_editor_timeline()._ruler
            if time_ruler is None:
                return

            def on_time_ruler_built(range, begin_minor_step, minor_stride, begin_step, stride):
                range_length = abs(range[0] - range[1])
                if range_length == 0:
                    return

                guidelines.offset = abs(begin_step - range[0]) / range_length
                guidelines.stride = stride / range_length
                guidelines.rebuild()

            if time_ruler.on_built is None:
                time_ruler.on_built = on_time_ruler_built
                time_ruler.rebuild()

    # multi selection code start
    def _get_selected_keys_wp_in_range(self, offset_x, offset_y, width, height):
        result = []
        if float(width) <= 0 and float(height) <= 0:
            # this code path is not used yet.
            return result

        # do simple overlap test to get the current active keys
        for curve in self._get_existing_visible_curves():
            for key_rect in curve._key_rects:
                if (
                    (key_rect.get_key_ui_x() > offset_x - self._get_key_rect_size() * 0.5)
                    and (key_rect.get_key_ui_x() < offset_x + width + self._get_key_rect_size() * 0.5)
                    and (key_rect.get_key_ui_y() > offset_y - self._get_key_rect_size() * 0.5)
                    and (key_rect.get_key_ui_y() < offset_y + height + self._get_key_rect_size() * 0.5)
                ):
                    result.append(weakref.ref(key_rect))

        return result

    def _set_curve_visibility(self, curve, is_visible):
        curve._top_stack.visible = is_visible

    def _is_curve_visible(self, curve) -> bool:
        return curve._top_stack.visible

    def _update_segment_set_from_key_rect(self, segment_set, key_rect):
        curve = key_rect._curve_wp()
        index = curve._get_key_index(key_rect)
        # add segments before and after the key if possible.
        if index < curve._get_segment_quantity():
            segment_set.add(curve._segment_list[index])
        if index > 0:
            segment_set.add(curve._segment_list[index - 1])

    def _set_key_set_wp_active(self, key_set_wp, active: bool):
        segment_set = set()

        for key_wp in key_set_wp:
            if key_wp():
                key_wp()._set_active_color(active)
                key_wp()._command_set_selected(active)
                self._update_segment_set_from_key_rect(segment_set, key_wp())

        for segment in segment_set:
            segment._update_active_color()

    # return True if successful. only key in existing set can be single selected.
    def _set_single_selected_key_wp(self, key_wp):
        if key_wp in self._multi_selected_keys_wp:
            self._selected_key_wp = key_wp
            self._show_the_one_of_the_selected()
            return True
        else:
            return False

    # the last one is taken as the (single)selected_key
    def _set_single_selected_key_wp_from_multi_selected_keys(self):
        if len(self._multi_selected_keys_wp):
            self._selected_key_wp = self._multi_selected_keys_wp[-1]
            self._show_the_one_of_the_selected()
        else:
            self._selected_key_wp = None
            self.get_curve_editor_view()._update_ui_clear_selection()

    # internally used by _set*, _add* and _remove*.
    def _manage_multi_selected_keys(self, unchange_set_wp, delete_set_wp, new_set_wp):
        # if user mouse operation causes selection change...
        if self._usd_edit_scope():
            # command change
            with self._usd_edit_scope():
                # only insert in command list when necessary.
                if len(new_set_wp) > 0 or len(delete_set_wp) > 0:
                    with omni.kit.undo.group():
                        for key_rect_wp in delete_set_wp:
                            if key_rect_wp():
                                path = get_runtime_style_attribute_name(key_rect_wp()._curve_wp().get_track_name())
                                time = (
                                    key_rect_wp()
                                    ._curve_wp()
                                    ._time_tick_to_time_code(self._get_key_time_tick(key_rect_wp()))
                                )
                                time = key_rect_wp()._curve_wp()._time_code_for_timeline_node_command(time)
                                omni.kit.commands.execute(
                                    "SelectAnimCurveKeys", paths=[path], operation="remove", times=time
                                )
                        for key_rect_wp in new_set_wp:
                            if key_rect_wp():
                                path = get_runtime_style_attribute_name(key_rect_wp()._curve_wp().get_track_name())
                                time = (
                                    key_rect_wp()
                                    ._curve_wp()
                                    ._time_tick_to_time_code(self._get_key_time_tick(key_rect_wp()))
                                )
                                time = key_rect_wp()._curve_wp()._time_code_for_timeline_node_command(time)
                                omni.kit.commands.execute(
                                    "SelectAnimCurveKeys", paths=[path], operation="add", times=time
                                )
        else:
            # this code path is only expected to be triggered by _ui_restore_curve_selected_keys() currently. Avoid recursive command insertion.
            pass

        # visual change and pointer change for control rect, do it before _set_single_selected_key_wp_from_multi_selected_keys for toolbar refresh
        self._set_selected_control(None)

        # visual change
        self._set_key_set_wp_active(delete_set_wp, False)
        self._set_key_set_wp_active(new_set_wp, True)

        # selection pointer change
        self._multi_selected_keys_wp = list(new_set_wp.union(unchange_set_wp))
        if (len(new_set_wp)) == 1 and self._set_single_selected_key_wp(list(new_set_wp)[0]):
            # special code path so when one key is added, it must show info.
            pass
        else:
            self._set_single_selected_key_wp_from_multi_selected_keys()

    def _set_multi_selected_keys(self, keys_wp):
        key_set_wp = set(keys_wp)
        unchange_set_wp = set(self._multi_selected_keys_wp).intersection(key_set_wp)
        delete_set_wp = set(self._multi_selected_keys_wp).difference(unchange_set_wp)
        new_set_wp = key_set_wp.difference(unchange_set_wp)

        self._manage_multi_selected_keys(unchange_set_wp, delete_set_wp, new_set_wp)

    def _add_multi_selected_keys(self, keys_wp):
        key_set_wp = set(keys_wp)
        unchange_set_wp = set(self._multi_selected_keys_wp)
        delete_set_wp = set()
        new_set_wp = key_set_wp.difference(unchange_set_wp)

        self._manage_multi_selected_keys(unchange_set_wp, delete_set_wp, new_set_wp)

    def _remove_multi_selected_keys(self, keys_wp):
        key_set_wp = set(keys_wp)
        unchange_set_wp = set(self._multi_selected_keys_wp).difference(key_set_wp)
        delete_set_wp = key_set_wp
        new_set_wp = set()

        self._manage_multi_selected_keys(unchange_set_wp, delete_set_wp, new_set_wp)

    def _update_multi_selected_keys(self, keys_wp, modifier):
        if modifier & carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL:
            # if CONTROL key is pressed, add on existing seletion.
            self._add_multi_selected_keys(keys_wp)
        elif modifier & carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT:
            # if SHIFT key is pressed, minus from existing selection
            self._remove_multi_selected_keys(keys_wp)
        else:
            # replace selection.
            self._set_multi_selected_keys(keys_wp)

    def _show_the_one_of_the_selected(self):
        # show the (single)select_key info.
        single_select_key = self._get_selected_key()
        if single_select_key:
            curve = single_select_key._curve_wp()
            index = curve._get_key_index(single_select_key)
            in_control_rect = (
                None
                if self._get_selected_control() == curve._out_control_rects[index]
                else curve._in_control_rects[index]
            )
            out_control_rect = (
                None
                if self._get_selected_control() == curve._in_control_rects[index]
                else curve._out_control_rects[index]
            )
            self._show_key_in_toolbar(single_select_key, in_control_rect, out_control_rect)

    def _build_multi_selection(self):
        with self._multi_selection_frame:
            with ui.ZStack():
                self._multi_selection_range_begin_placer = ui.Placer(draggable=False, stable_size=True)
                with self._multi_selection_range_begin_placer:
                    self._multi_selection_mouse_placer = ui.Placer(
                        draggable=True,
                        stable_size=True,
                        offset_x_changed_fn=self._on_multi_selection_moved_x,
                        offset_y_changed_fn=self._on_multi_selection_moved_y,
                        mouse_pressed_fn=self._on_multi_selection_pressed,
                        mouse_released_fn=self._on_multi_selection_released,
                    )
                    with self._multi_selection_mouse_placer:
                        ui.Frame()
                self._multi_selection_rectangle_placer = ui.Placer(draggable=False, stable_size=True)
                with self._multi_selection_rectangle_placer:
                    self._multi_selection_rectangle = ui.Rectangle(
                        visible=False, style_type_name_override="Multi_selection_rectangle"
                    )

    def _update_multi_selection(self):
        # because of the parent frame (timeline's bottom frame ), somehow _multi_selection_frame does not start from the begin range.
        # do my own ajustment here.
        # if you do not ajust, the placer can not move if the mouse is leftmost.
        range_begin_offset_x = self._get_offset_x_from_time(self.get_curve_editor_timeline().range_begin())
        self._multi_selection_range_begin_placer.offset_x = range_begin_offset_x

    def _on_multi_selection_pressed(self, x, y, b, m):
        if b == 0:  # only handle left button
            # Recored start mouse offset in the _multi_selection_frame.
            self._selection_begin_offset_x = x - self._multi_selection_frame.screen_position_x
            self._selection_begin_offset_y = y - self._multi_selection_frame.screen_position_y
            # Init selection rectangle's offset and extent and make it invisible. Later it might update only x or only y.
            task = asyncio.ensure_future(self._async_change_selection_ui_x(self._selection_begin_offset_x, 0))
            task = asyncio.ensure_future(self._async_change_selection_ui_y(self._selection_begin_offset_y, 0))
            task = asyncio.ensure_future(self._async_hide_selection_ui())

            # Currently do not clear selection here. opaque_for_mouse_events issue is the blocker.

    def _on_multi_selection_released(self, x, y, b, m):
        if b == 0:  # only handle left button
            fore_ground_pressed = False
            if hasattr(self, "_foreground_pressed"):
                delattr(self, "_foreground_pressed")
                fore_ground_pressed = True

            if hasattr(self, "_selection_begin_offset_x"):
                delattr(self, "_selection_begin_offset_x")
                delattr(self, "_selection_begin_offset_y")

                # if the dragger is moved
                if hasattr(self, "_moved_during_press_and_release"):
                    delattr(self, "_moved_during_press_and_release")

                    # Get selected keys from the rectangle coverage.
                    keys_wp = self._get_selected_keys_wp_in_range(
                        self._multi_selection_rectangle_placer.offset_x,
                        self._multi_selection_rectangle_placer.offset_y,
                        self._multi_selection_rectangle_placer.width,
                        self._multi_selection_rectangle_placer.height,
                    )

                    self._update_multi_selected_keys(keys_wp, m)

                    # Reset dragger offset for later use. It will not trigger callback because _selection_begin_offset_x and _selection_begin_offset_y condition.
                    self._multi_selection_mouse_placer.offset_x = 0
                    self._multi_selection_mouse_placer.offset_y = 0
                elif fore_ground_pressed == False:
                    # empty selection.
                    self._set_multi_selected_keys([])

                # Hide selection rectangle.
                task = asyncio.ensure_future(self._async_hide_selection_ui())

    def _on_multi_selection_moved_x(self, placer_x):
        if hasattr(self, "_selection_begin_offset_x"):
            self._moved_during_press_and_release = True

            # get offset and extent. ensure extent is positive.
            if float(placer_x) > 0:
                width = float(placer_x)
                offset_x = self._selection_begin_offset_x
            else:
                width = -float(placer_x)
                offset_x = self._selection_begin_offset_x + placer_x

            # async update _multi_selection_rectangle_placer. otherwise the UI can not refresh because here it is in UI callback.
            task = asyncio.ensure_future(self._async_change_selection_ui_x(offset_x, width))

    def _on_multi_selection_moved_y(self, placer_y):
        if hasattr(self, "_selection_begin_offset_y"):
            self._moved_during_press_and_release = True

            # get offset and extent. ensure extent is positive.
            if float(placer_y) > 0:
                height = float(placer_y)
                offset_y = self._selection_begin_offset_y
            else:
                height = -float(placer_y)
                offset_y = self._selection_begin_offset_y + placer_y

            # async update _multi_selection_rectangle_placer. otherwise the UI can not refresh because here it is in UI callback.
            task = asyncio.ensure_future(self._async_change_selection_ui_y(offset_y, height))

    def _on_timeline_node_add_key(self, x, y):
        time = self._get_value_x(x - self._multi_selection_frame.screen_position_x)
        value = self._get_value_y(y - self._multi_selection_frame.screen_position_y)
        curve_paths = []
        times = []
        for curve in self._get_existing_visible_curves():
            times.append(curve._time_code_for_timeline_node_command(time))
            if times[-1] != times[0]:
                # supposed to support only one timeline node prim.
                carb.log_error("Unexpected code path in CurveListView._on_timeline_node_add_key()")
                return
            curve_paths.append(get_runtime_style_attribute_name(curve.get_track_name()))

        if len(curve_paths) > 0:
            omni.kit.commands.execute(
                "SetAnimCurveKeys",
                time=Usd.TimeCode(times[0]),
                paths=curve_paths,
                value=value,
                preserveCurveShape=False,
            )
        else:
            carb.log_warn(
                "There is no curve in the selected prim, please use the Create curve button to create a curve before adding a key"
            )

    def _on_timeline_node_mouse_pressed(self, x, y, button, modifier):
        if self.is_timeline_node_mode():
            if button != 1:
                return

            menu = {
                "name": "Add Key",
                "show_fn": lambda objects: True,
                "onclick_fn": lambda objects: self._on_timeline_node_add_key(x, y),
            }

            omni.kit.context_menu.get_instance().show_context_menu("", {}, [menu])

    async def _async_change_selection_ui_x(self, offset_x, width):
        self._multi_selection_rectangle_placer.offset_x = offset_x
        self._multi_selection_rectangle_placer.width = ui.Pixel(width)
        # enable visibility in async here seems to avoid some initial rectangle flicker
        self._multi_selection_rectangle.visible = True

    async def _async_change_selection_ui_y(self, offset_y, height):
        # ajust offset_y and height so that the _curve_list_frame.computed_height is not changed. So during dragging, self._ruler's range update is avoided.
        if offset_y < 0:
            height = height + offset_y
            offset_y = 0
        if offset_y + height > self._curve_list_frame.computed_height:
            height = self._curve_list_frame.computed_height - offset_y

        self._multi_selection_rectangle_placer.offset_y = offset_y
        self._multi_selection_rectangle_placer.height = ui.Pixel(height)
        # enable visibility in async  here seems to avoid some initial rectangle flicker
        self._multi_selection_rectangle.visible = True

    async def _async_hide_selection_ui(self):
        # enable visibility in async  here seems to avoid some initial rectangle flicker
        self._multi_selection_rectangle.visible = False

    # multi selection code end

    def _update_omni_time_range(self):
        # skip is not built yet.
        if self._omni_time_range_frame is None:
            return

        start_time_code = self.get_curve_editor_view().get_omni_timeline_start_time_code()
        end_time_code = self.get_curve_editor_view().get_omni_timeline_end_time_code()
        start_offset_x = self._get_offset_x_from_time(start_time_code)
        end_offset_x = self._get_offset_x_from_time(end_time_code)

        # update shading area
        self._omni_time_range_placer.offset_x = start_offset_x
        with self._omni_time_range_frame:
            self._omni_time_range_rect = ui.Rectangle(
                name="TimeRangeShading", width=ui.Pixel(end_offset_x - start_offset_x)
            )

    # set _min_value_y and _max_value_y in a fallback/default way.
    def _set_default_fit_value_y(self):
        self._set_fit_value_y(self._fit_default_min_value_y, self._fit_default_max_value_y)

    # set _min_value_y and _max_value_y with specification. Do not pass in value to use original value.
    def _set_fit_value_y(self, min_value_y=None, max_value_y=None):
        if min_value_y != None:
            self._min_value_y = min_value_y
        if max_value_y != None:
            self._max_value_y = max_value_y
        self._value2pixel = self._pixels_height / (self._max_value_y - self._min_value_y)

    def _on_fit_common_value_y(self, min_value_y, max_value_y):
        # to handle corner case of max_value_y == min_value_y, use self._fit_min_delta_value_y.
        delta_value_y = max((max_value_y - min_value_y) * self._fit_overhead, self._fit_min_delta_value_y)
        self._set_fit_value_y(min_value_y - delta_value_y, max_value_y + delta_value_y)

    def _on_fit_common_offset_y(self, min_offset_y, max_offset_y):
        # ui offset y => value y. upside down.
        min_value_y = self._get_value_y(max_offset_y)
        max_value_y = self._get_value_y(min_offset_y)
        self._on_fit_common_value_y(min_value_y, max_value_y)

    def _on_fit_common_value_x(self, min_value_x, max_value_x):
        # to handle corner case of max_value_x == min_value_x, , use self._fit_min_delta_value_x.
        delta_value_x = max((max_value_x - min_value_x) * self._fit_overhead, self._fit_min_delta_value_x)
        rb = round(min_value_x - delta_value_x)
        re = round(max_value_x + delta_value_x)
        self.get_curve_editor_timeline().set_range(rb, re)

        self._notify_infinity_curve_adapt()

    def _on_fit_common_offset_x(self, min_offset_x, max_offset_x):
        min_value_x = self._get_value_x(min_offset_x)
        max_value_x = self._get_value_x(max_offset_x)
        self._on_fit_common_value_x(min_value_x, max_value_x)

    def _on_fit_common(self, key_rects, singular_key_rects=[]):
        # init min max
        min_offset_x = sys.float_info.max
        max_offset_x = -sys.float_info.max  # sys.float_info.min should not be used here
        min_offset_y = sys.float_info.max
        max_offset_y = -sys.float_info.max  # sys.float_info.min should not be used here

        # filter through and get min max
        for key_rect in key_rects:
            min_offset_x = min(min_offset_x, key_rect.get_key_ui_x())
            max_offset_x = max(max_offset_x, key_rect.get_key_ui_x())
            min_offset_y = min(min_offset_y, key_rect.get_key_ui_y())
            max_offset_y = max(max_offset_y, key_rect.get_key_ui_y())

        time_code_range = carb.settings.get_settings().get("/persistent/app/stage/timeCodeRange")
        fit_default_offset_x_range = (
            0
            if time_code_range is None
            else self._get_offset_x_from_time(time_code_range[1]) - self._get_offset_x_from_time(time_code_range[0])
        )
        fit_default_offset_y_range = self._get_offset_y_from_value(
            self._fit_default_min_value_y
        ) - self._get_offset_y_from_value(
            self._fit_default_max_value_y
        )  # !!! the bigger the value, the smaller the offset

        for key_rect in singular_key_rects:
            # get singular_min_offset_x and singular_max_offset_x, based on the ov defalt time code range.
            singular_min_offset_x = key_rect.get_key_ui_x() - fit_default_offset_x_range * 0.5
            singular_max_offset_x = key_rect.get_key_ui_x() + fit_default_offset_x_range * 0.5

            # get singular_min_offset_y and singular_max_offset_y, based on self._fit_default_***_value_y.
            singular_min_offset_y = key_rect.get_key_ui_y() - fit_default_offset_y_range * 0.5
            singular_max_offset_y = key_rect.get_key_ui_y() + fit_default_offset_y_range * 0.5

            # update bounds
            min_offset_x = min(min_offset_x, singular_min_offset_x)
            max_offset_x = max(max_offset_x, singular_max_offset_x)
            min_offset_y = min(min_offset_y, singular_min_offset_y)
            max_offset_y = max(max_offset_y, singular_max_offset_y)

        # if there is some thing to fit
        if (min_offset_x <= max_offset_x) and (min_offset_y <= max_offset_y):
            self._on_fit_common_offset_x(min_offset_x, max_offset_x)
            self._on_fit_common_offset_y(min_offset_y, max_offset_y)
        else:
            # change nothing
            pass

    def _on_fit_all(self):
        key_rects = []
        singular_key_rects = []

        for curve in self._get_existing_visible_curves():
            if len(curve._key_rects) == 1:
                # special case for only one key fit. For displaying a curve with only one key.
                singular_key_rects.append(curve._key_rects[0])
            else:
                for key_rect in curve._key_rects:
                    key_rects.append(key_rect)

        self._on_fit_common(key_rects, singular_key_rects)

    def _on_fit_selection(self):
        key_rects = []

        for key_wp in self._multi_selected_keys_wp:
            key_rects.append(key_wp())

        self._on_fit_common(key_rects)

    def _on_fit_conditionally(self):
        if len(self._multi_selected_keys_wp):
            self._on_fit_selection()
        else:
            self._on_fit_all()

    def _on_view_zoom(self, scale_y: float, center_offset_y: float):
        self._value2pixel /= scale_y

        alpha = float(center_offset_y) / self._pixels_height
        pivot_value = self._min_value_y * alpha + self._max_value_y * (1 - alpha)
        value_delta = self._pixels_height / self._value2pixel
        self._min_value_y = pivot_value - value_delta * (1 - alpha)
        self._max_value_y = pivot_value + value_delta * alpha
        self._ruler.range = (self._max_value_y, self._min_value_y)

        self._notify_infinity_curve_adapt()

    def _on_view_pan_x(self, offset_x: float):
        self._notify_infinity_curve_adapt()

    def _on_view_pan_y(self, offset_y: float):
        # self._value2pixel is not changed here.
        # only change self._min_value_y and self._max_value_y.
        self._min_value_y += offset_y / self._value2pixel
        self._max_value_y = self._min_value_y + self._pixels_height / self._value2pixel
        self._ruler.range = (self._max_value_y, self._min_value_y)

    def _notify_infinity_curve_adapt(self):
        for curve in self._get_existing_curves():
            curve._notify_infinity_curve_adapt()

    def _usd_edit_scope(self):
        return self.get_curve_editor_view().get_internal_usd_edit_scope()

    # return CurveEditorView
    def get_curve_editor_view(self):
        return self.get_curve_editor_timeline().get_curve_editor_view()

    # this should be thought carefully, may be obsolete because the view only handles tracks directly now and it does not know prims conceptually.
    def _get_prims_obsolete(self):
        return self.get_curve_editor_view().get_current_user_prims()

    # return CurveEditorTimeline
    def get_curve_editor_timeline(self):
        return self._timeline_wp()

    def is_timeline_node_mode(self):
        is_timeline_node_selected = False

        # Check if timeline is the only type that contains curve animation
        for prim in self._get_prims_obsolete():
            if prim.IsValid() == False:
                # CurveEditorTimeline._on_timeline_event is responded before _get_prims_obsolete is refreshed. So IsValid() check is necessary. Otherwise the following find_curve_data_prim_from_other_prim() might fail after prim deletion operation.
                continue

            curve_prims = omni.anim.curve.core.utils.get_curve_plugin().get_curve_prims(prim.GetPath().pathString)
            if not curve_prims:
                continue

            if not (prim.GetTypeName() in ("OmniGraphNode", "ComputeNode")):
                return False

            if prim.GetAttribute("node:type").Get() != "omni.anim.Timeline":
                return False

            is_timeline_node_selected = True

        return is_timeline_node_selected

    # already has cached selection set, restore ui
    def _ui_restore_curve_selected_keys(self, curve):
        # Avoid recursive command insertion with _usd_edit_scope(). temptest todo. rethink how to avoid it.
        with self._usd_edit_scope():
            selected_keys_wp = []
            curve._get_selection(selected_keys_wp)
            # add selection in a batch, which is faster than adding one by one.
            self._add_multi_selected_keys(selected_keys_wp)

    # remove ui only selection, without cache change
    def _ui_remove_curve_selected_keys(self, curve):
        # ui selection set change accordingly
        shrink_keys_wp = []
        for key_wp in self._multi_selected_keys_wp:
            if key_wp()._curve_wp() != curve:
                shrink_keys_wp.append(key_wp)
        self._multi_selected_keys_wp = shrink_keys_wp
        self._set_single_selected_key_wp_from_multi_selected_keys()

    # called by _ui_add_track()
    # try use the slot to create a curve
    def _use_curve_list(self, stage, track, index) -> bool:
        if self._curve_list[index] == None:
            # create the curve widgets within the frame
            with self._curve_frame_list[index]:
                self._curve_list[index] = self._create_curve_of_attribute(
                    stage, track.get_prim_path_str(), track.get_data_attr_name()
                )

            if self._curve_list[index] != None:
                # update _curve_list_used_quantity if needed
                if index == self._curve_list_used_quantity:
                    self._curve_list_used_quantity += 1

                self._ui_restore_curve_selected_keys(self._curve_list[index])

            return True
        else:
            return False

    # currently the add has undetermined Z order. I do not know how to tune order in ZStack.
    # to avoid the Z order problem, I can recreate all curves like before but then there is performance concern.
    # track is read only
    def _ui_add_track(self, stage, track):
        if SHOW_MORE_LOG_WARN:
            carb.log_warn(f"CurveListView._ui_add_track : {track.get_track_name()}")

        if len(self._curve_frame_list) != len(self._curve_list):
            # defacto sanity check. one curve corresponds to one frame
            carb.log_error("Unexpected code path in CurveListView._ui_add_track()")

        # try find the first empty slot and create curve.
        for i in range(len(self._curve_list)):
            if self._use_curve_list(stage, track, i):
                return

        # no empty slot is found
        # create new slot first and then create curve.
        with self._curve_list_frame_z_stack:
            self._curve_frame_list.append(ui.Frame())
        self._curve_list.append(None)
        self._use_curve_list(stage, track, self._curve_list_used_quantity)

    # track is read only
    def _ui_remove_track(self, track):
        if SHOW_MORE_LOG_WARN:
            carb.log_warn(f"CurveListView._ui_remove_track : {track.get_track_name()}")

        if len(self._curve_frame_list) != len(self._curve_list):
            # defacto sanity check. one curve corresponds to one frame
            carb.log_error("Unexpected code path in CurveListView._ui_remove_track()")

        for i in range(self._curve_list_used_quantity):
            # find the curve that is UI representation of the track.
            if self._curve_list[i] != None and self._curve_list[i].get_track_name() == track.get_track_name():
                with self._curve_frame_list[i]:
                    # just visually clear first
                    ui.ZStack()

                self._ui_remove_curve_selected_keys(self._curve_list[i])
                # set None : 1, to mark the empty slot, 2 so GC can clear widgets
                self._curve_list[i] = None
                break

        # shrink _curve_list_used_quantity if needed
        while self._curve_list_used_quantity > 0 and self._curve_list[self._curve_list_used_quantity - 1] == None:
            self._curve_list_used_quantity -= 1

    # track is read only
    def _ui_update_track_visibility(self, track, is_visible: bool):
        for curve in self._get_existing_curves():
            if curve.get_track_name() == track.get_track_name():
                self._set_curve_visibility(curve, is_visible)
                # ui selection set change accordingly
                if is_visible:
                    self._ui_restore_curve_selected_keys(curve)
                else:
                    self._ui_remove_curve_selected_keys(curve)
                break

    def _create_curve_sub_stacks(self, curve):
        # this is just a normal ui.ZStack(). can be used for curve visibility toggling
        curve._top_stack = ui.ZStack()
        with curve._top_stack:
            # the order is important. Bezier curve end should be in deeper layer than curve for the evaluated curve to show in sync with curve end. Drag frame should be on top for user to see and manipulate well.
            curve._end_z_stack = ui.ZStack()
            curve._curve_z_stack = ui.ZStack()
            curve._line_z_stack = ui.ZStack()
            curve._control_drag_z_stack = ui.ZStack()
            curve._key_drag_z_stack = ui.ZStack()

    # May return None
    def _create_curve_of_attribute(self, stage, user_prim_path_str, data_attr_name) -> CurveOfAttribute:
        curve = CurveOfAttribute(self, user_prim_path_str, data_attr_name)
        if curve.init(stage) == False:
            return None

        # the stacks are needed even for an empty curve. like _top_stack for visibility related api.
        self._create_curve_sub_stacks(curve)

        schema_key_list = curve._get_schema_keys()
        num_samples = len(schema_key_list)
        if num_samples == 0:
            if SHOW_MORE_LOG_WARN:
                carb.log_warn("A curve without key.")
            return curve

        ## create all the UI elements of the curve
        #

        for schema_key in schema_key_list:
            key_tuber = SchemaKeyTuber(schema_key, curve._time_codes_per_second)
            self._create_curve_sample_tangent(curve, key_tuber)
            self._create_curve_key_rect(
                curve,
                key_tuber.get_time_code(),
                key_tuber.get_value(),
                key_tuber.is_tangent_broken(),
                key_tuber.is_tangent_weighted(),
            )
            self._create_curve_in_control_rect(
                curve,
                key_tuber.get_in_tangent_time_code(),
                key_tuber.get_in_tangent_value(),
                key_tuber.get_in_tangent_type(),
                key_tuber.is_tangent_weighted(),
            )
            self._create_curve_out_control_rect(
                curve,
                key_tuber.get_out_tangent_time_code(),
                key_tuber.get_out_tangent_value(),
                key_tuber.get_out_tangent_type(),
                key_tuber.is_tangent_weighted(),
            )

        for i in range(num_samples):
            self._create_curve_in_control_line(curve, curve._in_control_rects[i], curve._key_rects[i])
            self._create_curve_out_control_line(curve, curve._out_control_rects[i], curve._key_rects[i])

        for i in range(num_samples - 1):
            self._create_step_rect(curve, curve._key_rects[i], curve._key_rects[i + 1])
            self._create_curve_control_segment(
                curve,
                curve._key_rects[i],
                curve._key_rects[i + 1],
                curve._out_control_rects[i],
                curve._in_control_rects[i + 1],
                curve._step_rects[i],
            )

        self._create_infinity_curve(curve)

        # control appearance init
        curve._refresh_control_related_ui()

        return curve

    def _get_offset_x_from_time(self, time):
        x = ui.Pixel(self.get_curve_editor_timeline().transform_timeline_to_position(time, snap=False))
        return x

    def _get_offset_y_from_value(self, value):
        y = (value - self._min_value_y) * self._value2pixel
        y = self._pixels_height - y

        return ui.Pixel(y)

    def _get_offset_from_time_value(self, time, value):
        x = self._get_offset_x_from_time(time)
        y = self._get_offset_y_from_value(value)

        return x, y

    # create a helper data structure to communicate with USD attributes
    def _create_curve_sample_tangent(self, curve, key_tuber):
        tangent = _CurveTangent()
        tangent.set_from_tuber(key_tuber)
        curve._sample_tangents.append(tangent)
        return tangent

    # create a CurveKeyRect
    def _create_curve_key_rect(self, curve, time, value, is_tangent_broken, is_tangent_weighted):
        r = CurveKeyRect(curve, is_tangent_broken, is_tangent_weighted)
        x, y = self._get_offset_from_time_value(time, value)
        with curve._key_drag_z_stack:
            r.build_ui(x, y)
        with curve._end_z_stack:
            r.build_end_ui(x, y)

        curve._key_rects.append(r)

    def _create_curve_control_rect_ui(self, curve, time, value, r):
        x, y = self._get_offset_from_time_value(time, value)
        with curve._control_drag_z_stack:
            r.build_ui(x, y)
        with curve._end_z_stack:
            r.build_end_ui(x, y)

        # initially invisible until update with selection status
        r._set_visible(False)

    # create a CurveInControlRect:
    def _create_curve_in_control_rect(self, curve, time, value, tangent_type: int, is_tangent_weighted: bool):
        r = CurveInControlRect(curve, tangent_type, is_tangent_weighted)
        self._create_curve_control_rect_ui(curve, time, value, r)
        curve._in_control_rects.append(r)
        return r

    # create a CurveOutControlRect:
    def _create_curve_out_control_rect(self, curve, time, value, tangent_type: int, is_tangent_weighted: bool):
        r = CurveOutControlRect(curve, tangent_type, is_tangent_weighted)
        self._create_curve_control_rect_ui(curve, time, value, r)
        curve._out_control_rects.append(r)
        return r

    # create a CurveControlLine:
    def _create_curve_control_line(self, curve, control_rect, key_rect):
        l = CurveControlLine(curve)
        with curve._line_z_stack:
            l.build_ui(control_rect, key_rect)

        # initially invisible until update with selection status
        l._set_visible(False)

        return l

    def _create_curve_in_control_line(self, curve, control_rect, key_rect):
        l = self._create_curve_control_line(curve, control_rect, key_rect)
        curve._in_control_lines.append(l)
        return l

    def _create_curve_out_control_line(self, curve, control_rect, key_rect):
        l = self._create_curve_control_line(curve, control_rect, key_rect)
        curve._out_control_lines.append(l)
        return l

    # create a CurveInvisibleRect for step tangent type
    def _create_step_rect(self, curve, key_rect, next_key_rect):
        r = CurveInvisibleRect(curve)
        with curve._end_z_stack:
            r.build_ui(next_key_rect._placer.offset_x, key_rect._placer.offset_y)

        curve._step_rects.append(r)
        return r

    # create a CurveControlSegment:
    def _create_curve_control_segment(self, curve, key_rect, next_key_rect, control_rect, next_control_rect, step_rect):
        s = CurveControlSegment(curve)
        with curve._curve_z_stack:
            s.build_ui(key_rect, next_key_rect, control_rect, next_control_rect, step_rect)

        curve._segment_list.append(s)
        return s

    # create an InfinityCurve of curve.
    def _create_infinity_curve(self, curve):
        curve._infinity_curve = InfinityCurve()

        with curve._curve_z_stack:
            curve._infinity_curve_pre_frame = ui.Frame()
            curve._notify_infinity_curve_pre_type_change(curve._get_pre_infinity_type_from_runtime())

            curve._infinity_curve_post_frame = ui.Frame()
            curve._notify_infinity_curve_post_type_change(curve._get_post_infinity_type_from_runtime())

        return curve._infinity_curve
