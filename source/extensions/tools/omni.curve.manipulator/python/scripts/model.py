# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from __future__ import annotations

import asyncio
import math
from collections import defaultdict
from typing import List, Set

import carb
import carb.dictionary
import carb.settings
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
from omni.kit.manipulator.tool.snap import SnapProviderManager
from omni.kit.manipulator.tool.snap import settings_constants as snap_c
from omni.kit.manipulator.transform.gestures import (
    RotateChangedGesture,
    RotateDragGesturePayload,
    ScaleChangedGesture,
    ScaleDragGesturePayload,
    TransformDragGesturePayload,
    TranslateChangedGesture,
    TranslateDragGesturePayload,
)
from omni.kit.manipulator.transform.settings_constants import Constants
from omni.kit.manipulator.transform.settings_listener import OpSettingsListener, SnapSettingsListener
from omni.kit.manipulator.transform.simple_transform_model import (
    AbstractTransformManipulatorModel,
    SimpleTransformModel,
)
from omni.kit.manipulator.transform.types import Operation
from omni.ui import scene as sc
from pxr import Gf, Usd, UsdGeom, Vt

from .cv_selection import CvSelection
from .utils import TOLERANCE, find_anchor_index, has_tangents


class Viewport1WindowState:
    def __init__(self):
        super().__init__()
        self._focused_windows = None
        focused_windows = []
        try:
            # For some reason is_focused may return False, when a Window is definitely in fact is the focused window!
            # And there's no good solution to this when multiple Viewport-1 instances are open; so we just have to
            # operate on all Viewports for a given usd_context.
            import omni.kit.viewport_legacy as vp

            vpi = vp.acquire_viewport_interface()
            for instance in vpi.get_instance_list():
                window = vpi.get_viewport_window(instance)
                if not window:
                    continue
                focused_windows.append(window)
            if focused_windows:
                self._focused_windows = focused_windows
                for window in self._focused_windows:
                    # Disable the selection_rect, but enable_picking for snapping
                    window.disable_selection_rect(True)
                    # Schedule a picking request so if snap needs it later, it may arrive by the on_change event
                    window.request_picking()
        except Exception:
            pass

    def get_picked_world_pos(self):
        if self._focused_windows:
            # Try to reduce to the focused window now after, we've had some mouse-move input
            focused_windows = [window for window in self._focused_windows if window.is_focused()]
            if focused_windows:
                self._focused_windows = focused_windows
            for window in self._focused_windows:
                window.disable_selection_rect(True)
                # request picking FOR NEXT FRAME
                window.request_picking()
                # get PREVIOUSLY picked pos, it may be None the first frame but that's fine
                return window.get_picked_world_pos()
        return None

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._focused_windows = None

    def get_usd_context_name(self):
        if self._focused_windows:
            return self._focused_windows[0].get_usd_context_name()
        else:
            return ""


class CvTransformChangedGestureBase:
    def __init__(self, usd_context_name: str = "", viewport_api=None):
        self._viewport_api = viewport_api  # VP2
        self._vp1_window_state = None

    def on_began(self, payload_type=TransformDragGesturePayload):
        self._viewport_on_began()

        if not self.gesture_payload or not self.sender or not isinstance(self.gesture_payload, payload_type):
            return

        model = self.sender.model
        if not model:
            return

        model = self.sender.model

        self._begin_translate = model.get_as_floats(model.get_item("translate")).copy()
        self._begin_scale = model.get_as_floats(model.get_item("scale")).copy()
        model.on_began(self.gesture_payload)

    def on_ended(self, payload_type=TransformDragGesturePayload):
        self._viewport_on_ended()

        if not self.gesture_payload or not self.sender or not isinstance(self.gesture_payload, payload_type):
            return

        model = self.sender.model
        if not model:
            return

        model = self.sender.model
        model.on_ended(self.gesture_payload)

    def on_canceled(self, payload_type=TransformDragGesturePayload):
        self._viewport_on_ended()

        if not self.gesture_payload or not self.sender or not isinstance(self.gesture_payload, payload_type):
            return

        model = self.sender.model
        if not model:
            return

        model = self.sender.model
        model.on_canceled(self.gesture_payload)

    def _viewport_on_began(self):
        self._viewport_on_ended()
        if self._viewport_api is None:
            self._vp1_window_state = Viewport1WindowState()

    def _viewport_on_ended(self):
        if self._vp1_window_state:
            self._vp1_window_state.destroy()
            self._vp1_window_state = None


class CvTranslateChangedGesture(TranslateChangedGesture, CvTransformChangedGestureBase):
    def __init__(self, snap_manager: SnapProviderManager, **kwargs):
        TranslateChangedGesture.__init__(self)
        CvTransformChangedGestureBase.__init__(self, **kwargs)
        self._snap_manager = snap_manager

    def on_began(self):
        CvTransformChangedGestureBase.on_began(self, payload_type=TranslateDragGesturePayload)

        model = self._get_model(TranslateDragGesturePayload)
        if model and self._can_snap(model):
            # TODO No need for gesture=self when VP1 has viewport_api
            exclude_paths = [basis_curves.GetPrim().GetPath() for basis_curves in model.per_curves_id_map.keys()]
            self._snap_manager.on_began(exclude_paths, gesture=self)

    def on_changed(self):
        model = self._get_model(TranslateDragGesturePayload)
        if not model:
            return

        item = self.gesture_payload.changing_item
        translated = self.gesture_payload.moved.copy()
        axis = self.gesture_payload.axis

        new_translate = model.get_as_floats(item)
        new_manip_xform = Gf.Matrix4d(1)
        new_manip_xform.SetTranslate((new_translate[0], new_translate[1], new_translate[2]))

        def apply_position(snap_world_pos=None, snap_world_orient=None, keep_spacing: bool = True):
            # ignore snap_world_orient and keep_spacing for now

            nonlocal translated
            if self.state != sc.GestureState.CHANGED:
                return
            if (
                snap_world_pos
                and (
                    math.isfinite(snap_world_pos[0])
                    and math.isfinite(snap_world_pos[1])
                    and math.isfinite(snap_world_pos[2])
                )
                and not (
                    snap_world_pos[0] == 0 and snap_world_pos[1] == 0 and snap_world_pos[2] == 0
                )  # TODO why garbage (0, 0, 0)?
            ):
                translated = Gf.Vec3f(*snap_world_pos) - Gf.Vec3f(*self._begin_translate)

            translation = [a + b for a, b in zip(translated, self._begin_translate)]

            model.set_floats(item, [translation[0], translation[1], translation[2]])

        if (
            model._snap_settings_listener.snap_enabled
            and model._snap_settings_listener.snap_provider
            and axis == [1, 1, 1]
        ):
            ndc_location = None
            if self._viewport_api:
                # No mouse location is available, have to convert back to NDC space
                ndc_location = self.sender.transform_space(
                    sc.Space.WORLD, sc.Space.NDC, self.gesture_payload.ray_closest_point
                )

            if self._snap_manager.get_snap_pos(
                new_manip_xform,
                ndc_location,
                self.sender.scene_view,
                lambda **kwargs: apply_position(
                    kwargs.get("position", None), kwargs.get("orient", None), kwargs.get("keep_spacing", True)
                ),
            ):
                return

        apply_position()

    def on_ended(self):
        CvTransformChangedGestureBase.on_ended(self, payload_type=TranslateDragGesturePayload)

        model = self._get_model(TranslateDragGesturePayload)
        if model and self._can_snap(model):
            self._snap_manager.on_ended()

    def on_canceled(self):
        CvTransformChangedGestureBase.on_canceled(self, payload_type=TranslateDragGesturePayload)

        model = self._get_model(TranslateDragGesturePayload)
        if model and self._can_snap(model):
            self._snap_manager.on_ended()

    def _get_model(self, payload_type) -> CvTransformModel:
        if not self.gesture_payload or not self.sender or not isinstance(self.gesture_payload, payload_type):
            return None

        return self.sender.model

    def _can_snap(self, model: CvTransformModel):
        axis = self.gesture_payload.axis
        if (
            model.snap_settings_listener.snap_enabled
            and model.snap_settings_listener.snap_provider
            and axis == [1, 1, 1]
        ):
            return True

        return False


class CvRotateChangedGesture(RotateChangedGesture, CvTransformChangedGestureBase):
    def __init__(self, **kwargs):
        RotateChangedGesture.__init__(self)
        CvTransformChangedGestureBase.__init__(self, **kwargs)

    def on_began(self):
        CvTransformChangedGestureBase.on_began(self, payload_type=RotateDragGesturePayload)

    def on_changed(self):
        if (
            not self.gesture_payload
            or not self.sender
            or not isinstance(self.gesture_payload, RotateDragGesturePayload)
        ):
            return

        model = self.sender.model
        item = self.gesture_payload.changing_item
        axis = self.gesture_payload.axis
        angle_delta = self.gesture_payload.angle_delta
        model.set_floats(item, [axis[0], axis[1], axis[2], angle_delta])

    def on_ended(self):
        CvTransformChangedGestureBase.on_ended(self, payload_type=RotateDragGesturePayload)

    def on_canceled(self):
        CvTransformChangedGestureBase.on_canceled(self, payload_type=RotateDragGesturePayload)


class CvScaleChangedGesture(ScaleChangedGesture, CvTransformChangedGestureBase):
    def __init__(self, **kwargs):
        ScaleChangedGesture.__init__(self)
        CvTransformChangedGestureBase.__init__(self, **kwargs)

    def on_began(self):
        CvTransformChangedGestureBase.on_began(self, payload_type=ScaleDragGesturePayload)

    def on_changed(self):
        if not self.gesture_payload or not self.sender or not isinstance(self.gesture_payload, ScaleDragGesturePayload):
            return

        model = self.sender.model
        item = self.gesture_payload.changing_item
        axis = self.gesture_payload.axis
        scale = self.gesture_payload.scale

        scale_delta = [scale * v for v in axis]
        scale_vec = [0, 0, 0]
        curr_scale = model.get_as_floats(item)
        for i in range(3):
            scale_vec[i] = self._begin_scale[i] * scale_delta[i] if scale_delta[i] else curr_scale[i]

        model.set_floats(item, scale_vec)

    def on_ended(self):
        CvTransformChangedGestureBase.on_ended(self, payload_type=ScaleDragGesturePayload)

    def on_canceled(self):
        CvTransformChangedGestureBase.on_canceled(self, payload_type=ScaleDragGesturePayload)


class CvTransformModel(SimpleTransformModel):
    def __init__(self, selection: CvSelection, usd_context_name: str = ""):
        super().__init__()
        self._dict = carb.dictionary.get_dictionary()
        self._settings = carb.settings.get_settings()
        self._selection = selection
        self._usd_context_name = usd_context_name
        self._selected_cvs = []
        self._setting_property = False
        self._xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        self._set_transform_to_selection_center_task = None
        self.reset()

        self._selection_sub = self._selection.subscribe_to_selection_changed(self._on_selection_changed)

        self._op_settings_listener = OpSettingsListener()
        self._op_settings_listener_sub = self._op_settings_listener.subscribe_listener(self._on_op_listener_changed)
        self._update_mode()

        # subscribe to snap events
        self._snap_settings_listener = SnapSettingsListener(
            enabled_setting_path=None,
            move_x_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            move_y_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            move_z_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            rotate_setting_path=snap_c.SNAP_ROTATE_SETTING_PATH,
            scale_setting_path=snap_c.SNAP_SCALE_SETTING_PATH,
            provider_setting_path=snap_c.SNAP_PROVIDER_NAME_SETTING_PATH,
        )

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._op_settings_listener_sub = None
        if self._op_settings_listener:
            self._op_settings_listener.destroy()
            self._op_settings_listener = None

        if self._snap_settings_listener:
            self._snap_settings_listener.destroy()
            self._snap_settings_listener = None

    def reset(self):
        if self._set_transform_to_selection_center_task and not self._set_transform_to_selection_center_task.done():
            self._set_transform_to_selection_center_task.cancel()
        self._set_transform_to_selection_center_task = None
        self._per_curves_id_map = defaultdict(list)
        self._curves_paths_set = set()
        self._changing_selection = False
        self._selected_cvs = []
        self._xform_cache.Clear()
        self._clear_value_caches()

    def _clear_value_caches(self):
        self._points_prev_value_maps = {}
        self._extent_prev_value_maps = {}
        self._points_curr_value_maps = {}
        self._extent_curr_value_maps = {}

    def on_began(self, payload):
        self._clear_value_caches()

        for basis_curves in self._per_curves_id_map.keys():
            points_attr = basis_curves.GetPointsAttr()
            points = points_attr.Get()
            self._points_prev_value_maps[basis_curves] = points

            extent_attr = basis_curves.GetExtentAttr()
            extent = extent_attr.Get()
            self._extent_prev_value_maps[basis_curves] = extent

    def on_ended(self, payload):
        with omni.kit.undo.group():
            self._setting_property = True
            for basis_curves, points in self._points_curr_value_maps.items():
                omni.kit.commands.execute(
                    "ChangeProperty",
                    prop_path=basis_curves.GetPointsAttr().GetPath(),
                    value=points,
                    prev=self._points_prev_value_maps[basis_curves],
                )

            for basis_curves, extent in self._extent_curr_value_maps.items():
                omni.kit.commands.execute(
                    "ChangeProperty",
                    prop_path=basis_curves.GetExtentAttr().GetPath(),
                    value=extent,
                    prev=self._extent_prev_value_maps[basis_curves],
                )

            self._setting_property = False

    def on_canceled(self, payload): ...

    def _set_transform_to_selection_center(self):
        if not self._selected_cvs:
            return

        average_translation = Gf.Vec3f(0)
        id_counts = 0
        for basis_curves, ids in self._per_curves_id_map.items():
            points_attr = basis_curves.GetPointsAttr()
            points = points_attr.Get()
            world_xform = self._xform_cache.GetLocalToWorldTransform(basis_curves.GetPrim())

            id_counts += len(ids)
            for id in ids:
                if id < len(points):
                    point = Gf.Vec3f(world_xform.Transform(points[id]))
                    average_translation += point
                else:
                    id_counts -= 1

        if id_counts:
            average_translation /= id_counts
            # Use super here to only set manipulator translation but not modify the CV
            super().set_floats(
                self._translate_item, [average_translation[0], average_translation[1], average_translation[2]]
            )

    def _on_selection_changed(self, selected_cvs):
        self._selected_cvs = selected_cvs
        self._per_curves_id_map.clear()
        self._curves_paths_set.clear()

        if self._selected_cvs:
            # rebuild _per_curves_id_map
            for basis_curves, id in self._selected_cvs:
                self._per_curves_id_map[basis_curves].append(id)
                self._per_curves_id_map[basis_curves].sort()
                self._curves_paths_set.add(basis_curves.GetPrim().GetPath())

            # always put the translation at the last selected
            self._changing_selection = True
            self._set_transform_to_selection_center()
            self._changing_selection = False
        else:
            # hide itself?
            pass

    def _update_op(self):
        if self._op_settings_listener.selected_op == Constants.TRANSFORM_OP_MOVE:
            self.set_operation(Operation.TRANSLATE)
        elif self._op_settings_listener.selected_op == Constants.TRANSFORM_OP_ROTATE:
            self.set_operation(Operation.ROTATE)
        elif self._op_settings_listener.selected_op == Constants.TRANSFORM_OP_SCALE:
            self.set_operation(Operation.SCALE)

    def _on_op_listener_changed(self, type: OpSettingsListener.CallbackType, value: str):
        if type == OpSettingsListener.CallbackType.OP_CHANGED:
            self._update_op()
            self._update_mode()
        elif (
            type == OpSettingsListener.CallbackType.TRANSLATION_MODE_CHANGED
            or type == OpSettingsListener.CallbackType.ROTATION_MODE_CHANGED
        ):
            self._update_mode()

    def _update_mode(self):
        # TODO always use global mode for now
        # We can define the "local" coordinate using curve tangent, normal and bi-tangent?
        self.global_mode = True

        """
        if self._selected_op == Constants.TRANSFORM_OP_MOVE:
            self.global_mode = self._translate_mode == Constants.TRANSFORM_MODE_GLOBAL
        elif self._selected_op == Constants.TRANSFORM_OP_ROTATE:
            self.global_mode = self._rotation_mode == Constants.TRANSFORM_MODE_GLOBAL
        elif self._selected_op == Constants.TRANSFORM_OP_SCALE:
            self.global_mode = False
        """

    def _move_point(self, points: Vt.Vec3fArray, id: int, translation: Gf.Vec3f, processed_ids: Set[int], sign=1):
        points[id] += translation * sign
        processed_ids.add(id)

    def _move_anchor(
        self,
        points: Vt.Vec3fArray,
        curve_id_start: int,
        curve_id_ends: int,
        periodic: bool,
        linear: bool,
        id: int,
        translation: Gf.Vec3f,
        processed_ids: Set[int],
    ):
        self._move_point(points, id, translation, processed_ids)
        if periodic:
            if id == curve_id_start:
                self._move_point(points, curve_id_ends, translation, processed_ids)
                # if not linear:
                #    self._move_point(points, curve_id_ends - 1, translation, processed_ids)
            # elif id == curve_id_ends:
            #     self._move_point(points, curve_id_start, translation, processed_ids)
            #     if not linear:
            #         self._move_point(points, curve_id_start + 1, translation, processed_ids)

        if not linear:
            if id > curve_id_start:
                self._move_point(points, id - 1, translation, processed_ids)
            if id < curve_id_ends:
                self._move_point(points, id + 1, translation, processed_ids)

    def _move_single_tangent(
        self,
        points: Vt.Vec3fArray,
        id: int,
        counter_id: int,
        translation: Gf.Vec3f,
        anchor_translation: Gf.Vec3f,
        was_smooth: bool,
        was_even: bool,
        prev_counter_tgt_len: int,
        processed_ids: Set[int],
    ):
        # only one end of manipulator is selected
        if was_smooth and counter_id is not None:
            if was_even:
                # move the other end of tangent along the opposite direction.
                self._move_point(points, id, translation, processed_ids)
                self._move_point(points, counter_id, translation, processed_ids, -1)
            else:
                # Tangent is smooth but not even, move the opposite site along the new direction
                self._move_point(points, id, translation, processed_ids)
                curr_translate = points[id]
                curr_tangent = curr_translate - anchor_translation
                curr_counter_tangent = (-curr_tangent).GetNormalized() * prev_counter_tgt_len
                curr_counter_translate = anchor_translation + curr_counter_tangent

                points[counter_id] = curr_counter_translate
                processed_ids.add(counter_id)
        else:
            # if it wasn't smooth, or it doesn't have a counter (first/last of non-periodic curve tangent), move the current cv itself only
            self._move_point(points, id, translation, processed_ids)

    def _move_tangents_pair(
        self,
        points: Vt.Vec3fArray,
        id: int,
        counter_id: int,
        translation: Gf.Vec3f,
        anchor_translation: Gf.Vec3f,
        was_smooth: bool,
        was_even: bool,
        processed_ids: Set[int],
    ):
        # If the counter tangent cv is also being selected, we need to reconcile and fine the best move
        if was_smooth:
            if was_even:
                # If both end of CV is manipulated, skip both (only on non-broken even curve)
                processed_ids.add(id)
                processed_ids.add(counter_id)
            else:
                # Tangent is smooth but not even (better movement?)
                translate_diff = translation

                trans_tgt0 = points[id] + translate_diff
                trans_tgt1 = points[counter_id] + translate_diff

                # Then do a smooth
                diff_tgt0 = trans_tgt0 - anchor_translation
                diff_tgt1 = trans_tgt1 - anchor_translation

                new_tgt_dir = (trans_tgt0 - trans_tgt1).GetNormalized()

                dot0 = Gf.Dot(diff_tgt0.GetNormalized(), new_tgt_dir)
                dot1 = Gf.Dot(diff_tgt1.GetNormalized(), new_tgt_dir)
                flip0 = 1.0
                flip1 = 1.0

                if dot0 * dot1 < 0:  # different sign
                    flip0 = math.copysign(flip0, dot0)
                    flip1 = math.copysign(flip1, dot1)
                else:  # same sign
                    if dot0 < dot1:
                        flip0 = -1.0
                    else:
                        flip1 = -1.0

                diff_tgt0 = diff_tgt0.GetLength() * new_tgt_dir * flip0
                trans_tgt0 = diff_tgt0 + anchor_translation

                diff_tgt1 = diff_tgt1.GetLength() * new_tgt_dir * flip1
                trans_tgt1 = diff_tgt1 + anchor_translation

                points[id] = trans_tgt0
                points[counter_id] = trans_tgt1

                processed_ids.add(id)
                processed_ids.add(counter_id)
        else:
            # if it wasn't smooth, move both tangent with same gizmo delta
            self._move_point(points, id, translation, processed_ids)
            self._move_point(points, counter_id, translation, processed_ids)

    def _on_translation_manipulated(self, translation):
        translation = Gf.Vec3f(*translation)

        # get the diff
        translate = translation - Gf.Vec3f(*self.get_as_floats(self._translate_item))

        for basis_curves, ids in self._per_curves_id_map.items():
            wrap = basis_curves.GetWrapAttr().Get()
            points_attr = basis_curves.GetPointsAttr()
            points = points_attr.Get()
            vertex_counts = basis_curves.GetCurveVertexCountsAttr().Get()

            is_periodic = wrap == UsdGeom.Tokens.periodic

            curve_index = 0
            curve_points_offset = 0

            world_xform = self._xform_cache.GetLocalToWorldTransform(basis_curves.GetPrim())
            world_xform_inverse = world_xform.GetInverse()
            local_translate = Gf.Vec3f(world_xform_inverse.TransformDir(translate))

            processed_ids = set()
            for id in ids:
                if id in processed_ids:
                    continue

                if id - curve_points_offset >= vertex_counts[curve_index]:
                    curve_points_offset += vertex_counts[curve_index]
                    curve_index += 1

                if not has_tangents(basis_curves):
                    self._move_anchor(
                        points,
                        curve_points_offset,
                        curve_points_offset + vertex_counts[curve_index] - 1,
                        is_periodic,
                        True,
                        id,
                        local_translate,
                        processed_ids,
                    )
                else:  # cubic
                    is_anchor = (id - curve_points_offset) % 3 == 0
                    if is_anchor:
                        self._move_anchor(
                            points,
                            curve_points_offset,
                            curve_points_offset + vertex_counts[curve_index] - 1,
                            is_periodic,
                            False,
                            id,
                            local_translate,
                            processed_ids,
                        )
                    else:
                        cv_id_this_curve = id - curve_points_offset
                        anchor_id_this_curve = find_anchor_index(cv_id_this_curve)
                        points_count = vertex_counts[curve_index]

                        # wrap around the last "virtual anchor"
                        if is_periodic and anchor_id_this_curve == points_count:
                            anchor_id_this_curve = 0

                        anchor_id = anchor_id_this_curve + curve_points_offset
                        if anchor_id in ids:
                            # If anchor is also selected, just move anchor itself
                            self._move_anchor(
                                points,
                                curve_points_offset,
                                curve_points_offset + vertex_counts[curve_index] - 1,
                                is_periodic,
                                False,
                                anchor_id,
                                local_translate,
                                processed_ids,
                            )
                        else:
                            if is_periodic:
                                counter_id_this_curve = (
                                    anchor_id_this_curve - (cv_id_this_curve - anchor_id_this_curve) + points_count
                                ) % points_count

                                counter_id = counter_id_this_curve + curve_points_offset
                            else:
                                # If the curve is non-periodic, the begin/end cv only has one tangent
                                counter_id = None
                                if cv_id_this_curve < anchor_id_this_curve and anchor_id_this_curve + 1 < points_count:
                                    counter_id = anchor_id_this_curve + 1 + curve_points_offset
                                elif cv_id_this_curve > anchor_id_this_curve and anchor_id_this_curve - 1 >= 0:
                                    counter_id = anchor_id_this_curve - 1 + curve_points_offset

                            prev_translate = points[id]
                            prev_translate_counter = points[counter_id] if counter_id is not None else None
                            prev_translate_anchor = points[anchor_id]
                            (was_smooth, was_even) = self._was_smooth_or_even(
                                prev_translate,
                                prev_translate_counter,
                                prev_translate_anchor,
                            )

                            if counter_id in ids:
                                # If the counter tangent cv is also being selected, we need to reconcile and fine the best move
                                self._move_tangents_pair(
                                    points,
                                    id,
                                    counter_id,
                                    local_translate,
                                    prev_translate_anchor,
                                    was_smooth,
                                    was_even,
                                    processed_ids,
                                )
                            else:
                                # only one end of manipulator is selected
                                prev_tan_1 = (
                                    (prev_translate_counter - prev_translate_anchor)
                                    if prev_translate_counter is not None
                                    else None
                                )
                                prev_tan_1_len = prev_tan_1.Normalize() if prev_tan_1 is not None else None

                                self._move_single_tangent(
                                    points,
                                    id,
                                    counter_id,
                                    local_translate,
                                    prev_translate_anchor,
                                    was_smooth,
                                    was_even,
                                    prev_tan_1_len,
                                    processed_ids,
                                )

            self._setting_property = True

            points_attr.Set(points)
            self._points_curr_value_maps[basis_curves] = points

            self._update_extent(basis_curves)

            self._setting_property = False

        self._set_transform_to_selection_center()

    def _on_rotation_manipulated(self, value):
        # The point itself does not rotate, but rotate around center of manipulator

        axis = Gf.Vec3d(value[0], value[1], value[2])
        rotation = Gf.Rotation(axis, value[3])
        rotation_mtx = Gf.Matrix4d(rotation, Gf.Vec3d())

        def rotate_point(index, translation, world_xform, world_xform_inverse, points, prev_points, processed_ids):
            point = points[index]
            point_world_pos = Gf.Vec3f(world_xform.Transform(point))
            point_world_pos = Gf.Vec3f(rotation_mtx.Transform(point_world_pos - translation)) + translation

            point_local_pos = Gf.Vec3f(world_xform_inverse.Transform(point_world_pos))

            points[index] = point_local_pos
            processed_ids.add(index)

        self._handle_scale_or_rotate(rotate_point)

    def _on_scale_manipulated(self, value):
        # The point itself does not scale, but scale the distance  to the center of manipulator
        scale = Gf.Vec3f(*value)

        def scale_point_distance(
            index, translation, world_xform, world_xform_inverse, points, prev_points, processed_ids
        ):
            id_prev_world_translate = Gf.Vec3f(world_xform.Transform(prev_points[index]))
            diff = id_prev_world_translate - translation
            id_world_translate = translation + Gf.Vec3f(diff[0] * scale[0], diff[1] * scale[1], diff[2] * scale[2])

            id_local_translate = Gf.Vec3f(world_xform_inverse.Transform(id_world_translate))
            points[index] = id_local_translate
            processed_ids.add(index)

        self._handle_scale_or_rotate(scale_point_distance)

    def _handle_scale_or_rotate(self, process_fn):
        translation = self.get_as_floats(self._translate_item)
        translation = Gf.Vec3f(translation[0], translation[1], translation[2])

        for basis_curves, ids in self._per_curves_id_map.items():
            wrap = basis_curves.GetWrapAttr().Get()
            points_attr = basis_curves.GetPointsAttr()
            points = points_attr.Get()
            type = basis_curves.GetTypeAttr().Get()
            prev_points = self._points_prev_value_maps[basis_curves]
            vertex_counts = basis_curves.GetCurveVertexCountsAttr().Get()
            is_periodic = wrap == UsdGeom.Tokens.periodic
            curve_index = 0
            curve_points_offset = 0

            world_xform = self._xform_cache.GetLocalToWorldTransform(basis_curves.GetPrim())
            world_xform_inverse = world_xform.GetInverse()

            processed_ids = set()
            for id in ids:
                if id in processed_ids:
                    continue

                while id - curve_points_offset >= vertex_counts[curve_index]:
                    curve_points_offset += vertex_counts[curve_index]
                    curve_index += 1

                points_count = vertex_counts[curve_index]

                if type == UsdGeom.Tokens.linear:
                    process_fn(id, translation, world_xform, world_xform_inverse, points, prev_points, processed_ids)
                else:  # cubic
                    is_anchor = (id - curve_points_offset) % 3 == 0

                    # whether to manipulate both tangents and the anchor cv together against manipulator
                    manip_all = False

                    if not is_anchor:
                        cv_id_this_curve = id - curve_points_offset
                        anchor_id_this_curve = find_anchor_index(cv_id_this_curve)

                        # wrap around the last "virtual anchor"
                        if is_periodic and anchor_id_this_curve == points_count:
                            anchor_id_this_curve = 0

                        anchor_id = anchor_id_this_curve + curve_points_offset
                    else:
                        anchor_id_this_curve = id - curve_points_offset
                        anchor_id = id

                    if is_periodic:
                        tgt_id0 = (anchor_id_this_curve - 1 + points_count) % (points_count) + curve_points_offset
                        tgt_id1 = (anchor_id_this_curve + 1) % points_count + curve_points_offset
                    else:
                        tgt_id0 = anchor_id - 1 if anchor_id > curve_points_offset + 1 else None
                        tgt_id1 = anchor_id + 1 if anchor_id < curve_points_offset + points_count - 1 else None

                    # If only the anchor is selected
                    if is_anchor and tgt_id0 not in ids and tgt_id1 not in ids:
                        manip_all |= True

                    # If begin/end CV
                    if is_anchor and (tgt_id0 is None or tgt_id1 is None):
                        manip_all |= True

                    # If both tangents are selected
                    if tgt_id0 in ids and tgt_id1 in ids:
                        manip_all |= True

                    if manip_all:
                        for i in [tgt_id0, anchor_id, tgt_id1]:
                            if i is not None:
                                process_fn(
                                    i, translation, world_xform, world_xform_inverse, points, prev_points, processed_ids
                                )
                    else:
                        # If we reach here, it means:
                        # - only one tangent cv is selected, anchor cv can be or not be selected, and it's not the begin/end of non-periodic curve
                        # - or only the tangent is selected on begin/end of a non-periodic curve
                        (selected_id, unselected_id) = (tgt_id0, tgt_id1) if tgt_id0 in ids else (tgt_id1, tgt_id0)

                        process_fn(
                            selected_id,
                            translation,
                            world_xform,
                            world_xform_inverse,
                            points,
                            prev_points,
                            processed_ids,
                        )

                        if anchor_id in ids:
                            process_fn(
                                anchor_id,
                                translation,
                                world_xform,
                                world_xform_inverse,
                                points,
                                prev_points,
                                processed_ids,
                            )

                        if unselected_id is not None:
                            (was_smooth, was_even) = self._was_smooth_or_even(
                                prev_points[selected_id],
                                prev_points[unselected_id] if unselected_id is not None else None,
                                prev_points[anchor_id],
                            )

                            if was_smooth:
                                tgt = points[selected_id] - points[anchor_id]
                                if was_even:
                                    points[unselected_id] = points[anchor_id] - tgt
                                else:
                                    original_len = (prev_points[unselected_id] - prev_points[anchor_id]).GetLength()
                                    points[unselected_id] = points[anchor_id] - tgt.GetNormalized() * original_len
                                processed_ids.add(unselected_id)

            self._setting_property = True

            points_attr.Set(points)
            self._points_curr_value_maps[basis_curves] = points

            self._update_extent(basis_curves)

            self._setting_property = False

    def _was_smooth_or_even(self, prev_translate, prev_translate_counter, prev_translate_anchor):
        prev_tan_0 = prev_translate - prev_translate_anchor
        prev_tan_1 = (prev_translate_counter - prev_translate_anchor) if prev_translate_counter is not None else None

        prev_tan_0_len = prev_tan_0.Normalize()
        prev_tan_1_len = prev_tan_1.Normalize() if prev_tan_1 is not None else None

        if prev_tan_1 is not None:
            prev_dot = Gf.Dot(prev_tan_0, prev_tan_1)
            prev_cross = Gf.Cross(prev_tan_0, prev_tan_1)

            was_smooth = prev_dot < 0 and Gf.IsClose(prev_cross, Gf.Vec3f(0.0), TOLERANCE)
            was_even = Gf.IsClose(prev_tan_0_len, prev_tan_1_len, TOLERANCE * max(prev_tan_0_len, prev_tan_1_len))
        else:
            # can't be smooth or even if there's no counter tangent
            was_smooth = was_even = False

        return (was_smooth, was_even)

    async def _set_transform_to_selection_center_async(self):
        self._set_transform_to_selection_center()
        self._set_transform_to_selection_center_task = None

    # called by BezierCurveEdits to reduce direct Tf Notice handler
    @carb.profiler.profile
    def on_objects_changed(self, notice, stage):
        if not self._selected_cvs:
            return

        if self._setting_property:
            return

        if self._set_transform_to_selection_center_task is not None:
            return

        for p in notice.GetChangedInfoOnlyPaths():
            if p.GetPrimPath() in self._curves_paths_set:
                if UsdGeom.Xformable.IsTransformationAffectedByAttrNamed(p.name) or p.name == "points":
                    if p.name != "points":
                        self._xform_cache.Clear()

                    if self._set_transform_to_selection_center_task is None:
                        self._set_transform_to_selection_center_task = asyncio.ensure_future(
                            self._set_transform_to_selection_center_async()
                        )

    def set_floats(self, item: AbstractTransformManipulatorModel.OperationItem, value: List[float]):
        if item == self._translate_item:
            self._on_translation_manipulated(value)
        elif item == self._rotate_item:
            self._on_rotation_manipulated(value)
        elif item == self._scale_item:
            self._on_scale_manipulated(value)
        else:
            carb.log_warn(f"Unsupported item {item}")

    def get_snap(self, item: AbstractTransformManipulatorModel.OperationItem):
        if not self._snap_settings_listener.snap_enabled:
            return None

        if item.operation == Operation.TRANSLATE:
            if self._snap_settings_listener.snap_provider:
                return None

            return (
                self._snap_settings_listener.snap_move_x,
                self._snap_settings_listener.snap_move_y,
                self._snap_settings_listener.snap_move_z,
            )
        elif item.operation == Operation.ROTATE:
            return self._snap_settings_listener.snap_rotate
        elif item.operation == Operation.SCALE:
            return self._snap_settings_listener.snap_scale

        return None

    @property
    def snap_settings_listener(self):
        return self._snap_settings_listener

    @property
    def per_curves_id_map(self):
        return self._per_curves_id_map

    def _update_extent(self, basis_curves):
        bounds = UsdGeom.Boundable.ComputeExtentFromPlugins(basis_curves, Usd.TimeCode.Default())
        if bounds is not None:
            extent_attr = basis_curves.GetExtentAttr()
            extent_attr.Set(bounds)
            self._extent_curr_value_maps[basis_curves] = bounds
