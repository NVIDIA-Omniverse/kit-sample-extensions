# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Union

import carb
import carb.events
import carb.profiler
import carb.settings
import omni.kit.actions.core
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.kit.usd.layers
import omni.usd
from carb.input import KeyboardInput as Key
from omni.curve.creator import CurveInterpolateTypes
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

from ..bindings import CurveEditingModeType, CurveManipulatorContext, CurvesEventType, get_interface
from .cv_selection import CvSelection
from .settings_constants import Constants
from .utils import (
    TOLERANCE,
    find_anchor_index,
    get_array_index_offset_and_curve_index,
    get_primvars_value_and_interpolation,
    has_tangents,
)

EXTENSION_NAME = "omni.curve.manipulator"
DELETE_INSTANCE_ACTION_NAME = "Delete CV"
EXIT_EDIT_ACTION_NAME = "Exit Curve Editing"
CURVE_CV_EDIT_CONTEXT_NAME = "Curve CV Editing "

DEFAULT_WIDTH_SETTING = "persistent/exts/omni.curve.manipulator/defaultWidthMeters"
INTERPOLATE_MODE_SETTING = "persistent/exts/omni.curve.manipulator/pencilToolInterpolateMode"


class BezierCurveEdits:
    def __init__(self, usd_context_name: str, cv_selection: CvSelection):
        self._add_cv_to_new_curve = False
        self._curve_manip = get_interface()
        self._curve_modifier_pressed = False
        self._usd_context_name = usd_context_name
        self._cv_selection = cv_selection
        self._settings = carb.settings.get_settings()
        self._context = omni.usd.get_context(usd_context_name)
        self._selection = self._context.get_selection()
        self._prev_points_value = None
        self._hack_toggle_active = False

        self._curve_context = self._curve_manip.create_context(usd_context_name)
        self._curve_event_sub = self._curve_manip.get_curves_event_stream(
            self._curve_context
        ).create_subscription_to_pop(self.on_curves_event, name="omni.curve.manipulator")

        self._action_registry = omni.kit.actions.core.get_action_registry()
        self._del_action = None
        self._exit_action = None
        self._register_actions()

        self._del_hotkey = None
        self._exit_hotkey = None

        manager = omni.kit.app.get_app().get_extension_manager()
        self._hooks = manager.subscribe_to_extension_enable(
            lambda _: self._register_hotkeys(),
            lambda _: self._unregister_hotkeys(),
            ext_name="omni.kit.hotkeys.core",
            hook_name="omni.kit.manipulator.point_instancer listener",
        )

        self._settings.set(INTERPOLATE_MODE_SETTING, "cubic")

    def __del__(self):
        self.destroy()

    def __get_default_width(self):
        default_width_in_meters = self._settings.get(DEFAULT_WIDTH_SETTING)
        return default_width_in_meters / UsdGeom.GetStageMetersPerUnit(self._context.get_stage())

    # There seems to be an issue where after creating a blank curve and then adding points,
    # Hydra isn't rendering the curve.  So, this hack will toggle the active state of the curve
    # prim, thus causing Hydra to render the prim.  We only want to do this once the curve has
    # the appropriate amount of points as toggling the active state causes performance issues.
    def __hack_ensure_wireframe_visible(self, basis_curves, points):
        refresh = False
        if self._hack_toggle_active:
            if points is not None and self._prev_points_value is None or len(self._prev_points_value) <= 2:
                if type == UsdGeom.Tokens.cubic and len(points) > 2:
                    refresh = True
                elif len(points) > 1:
                    refresh = True
        if refresh:
            self._hack_toggle_active = False
            with Sdf.ChangeBlock():
                prim = basis_curves.GetPrim()
                prim.SetActive(False)
                prim.SetActive(True)

    def destroy(self):
        self._unregister_hotkeys()
        self._unregister_actions()

        self._hooks = None

        if self._curve_context and self._curve_manip.is_in_curve_editing_mode(self._curve_context):
            omni.kit.commands.execute("DisableCurveEditing", curve_context=self._curve_context)

        self._curve_event_sub = None
        if self._curve_context:
            self._curve_manip.destroy_context(self._curve_context)
            self._curve_context = None

    @property
    def curve_context(self) -> CurveManipulatorContext:
        return self._curve_context

    def break_tangents(self, basis_curves: UsdGeom.BasisCurves, ids: List[int]):
        self._displace_tangent(basis_curves, ids, False)

    def uneven_tangents(self, basis_curves: UsdGeom.BasisCurves, ids: List[int]):
        self._displace_tangent(basis_curves, ids, True)

    def set_curve_modifier_pressed(self, value: bool):
        self._add_cv_to_new_curve = value
        self._curve_modifier_pressed = value
        self._curve_manip.set_adding_curve_to_basis_curves(self._curve_context, self._add_cv_to_new_curve)

    def smooth_tangents(self, basis_curves: UsdGeom.BasisCurves, ids: List[int], force_smooth_anchor=False):
        wrap = basis_curves.GetWrapAttr().Get()

        points_attr = basis_curves.GetPointsAttr()
        points = points_attr.Get()

        curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
        curve_vertex_counts = curve_vertex_counts_attr.Get()

        dirty = False
        for id in ids:
            id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)

            index = id - id_curve_offset
            anchor_index = find_anchor_index(index)

            if force_smooth_anchor:
                index = anchor_index

            points_count = curve_vertex_counts[curve_index]

            if wrap == UsdGeom.Tokens.periodic:
                can_do = True
                if anchor_index == points_count:
                    anchor_index = 0
            else:
                can_do = index > 1 and index < points_count - 2

            if can_do:
                trans_anchor = points[anchor_index + id_curve_offset]

                if index == anchor_index:
                    tgt0_index = (index - 1 + points_count) % points_count
                    tgt1_index = (index + 1) % points_count

                    trans_tgt0 = points[tgt0_index + id_curve_offset]
                    trans_tgt1 = points[tgt1_index + id_curve_offset]

                    diff_tgt0 = trans_tgt0 - trans_anchor
                    diff_tgt1 = trans_tgt1 - trans_anchor

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
                    trans_tgt0f = Gf.Vec3f(diff_tgt0 + trans_anchor)

                    diff_tgt1 = diff_tgt1.GetLength() * new_tgt_dir * flip1
                    trans_tgt1f = Gf.Vec3f(diff_tgt1 + trans_anchor)

                    dirty |= self._set_points(points, tgt0_index + id_curve_offset, trans_tgt0f)
                    dirty |= self._set_points(points, tgt1_index + id_curve_offset, trans_tgt1f)
                else:
                    counter_index = (anchor_index - (index - anchor_index) + points_count) % points_count

                    trans_tgt0 = points[index + id_curve_offset]
                    trans_tgt1 = points[counter_index + id_curve_offset]

                    diff_tgt0 = trans_tgt0 - trans_anchor
                    diff_tgt1 = trans_tgt1 - trans_anchor

                    new_tgt_dir = -diff_tgt0.GetNormalized()
                    trans_tgt1f = Gf.Vec3f(diff_tgt1.GetLength() * new_tgt_dir + trans_anchor)

                    dirty |= self._set_points(points, counter_index + id_curve_offset, trans_tgt1f)
        if dirty:
            with omni.kit.undo.group():
                self._set_value_to_attribute(points_attr.GetPath(), points)

                # update extent
                self._update_extent_attribute(basis_curves)

    def even_tangents(self, basis_curves: UsdGeom.BasisCurves, ids: List[int]):
        wrap = basis_curves.GetWrapAttr().Get()
        points_attr = basis_curves.GetPointsAttr()
        points = points_attr.Get()

        curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
        curve_vertex_counts = curve_vertex_counts_attr.Get()

        dirty = False
        for id in ids:
            id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)

            index = id - id_curve_offset
            anchor_index = find_anchor_index(index)

            points_count = curve_vertex_counts[curve_index]

            if wrap == UsdGeom.Tokens.periodic:
                can_do = True
                if anchor_index == points_count:
                    anchor_index = 0
            else:
                can_do = index > 1 and index < points_count - 2

            if can_do:
                trans_anchor = points[anchor_index + id_curve_offset]

                # take average length of two tangents and apply to both
                if index == anchor_index:
                    tgt0_index = (index - 1 + points_count) % points_count
                    tgt1_index = (index + 1) % points_count

                    trans_tgt0 = points[tgt0_index + id_curve_offset]
                    trans_tgt1 = points[tgt1_index + id_curve_offset]

                    diff_tgt0 = trans_tgt0 - trans_anchor
                    diff_tgt1 = trans_tgt1 - trans_anchor

                    lenTgt0 = diff_tgt0.Normalize()
                    lenTgt1 = diff_tgt1.Normalize()
                    new_length = (lenTgt0 + lenTgt1) * 0.5

                    trans_tgt0f = Gf.Vec3f(diff_tgt0 * new_length + trans_anchor)
                    trans_tgt1f = Gf.Vec3f(diff_tgt1 * new_length + trans_anchor)

                    dirty |= self._set_points(points, tgt0_index + id_curve_offset, trans_tgt0f)
                    dirty |= self._set_points(points, tgt1_index + id_curve_offset, trans_tgt1f)
                else:  # take length of selected tangent and apply to counterpart
                    counter_index = (anchor_index - (index - anchor_index) + points_count) % points_count

                    trans_tgt0 = points[index + id_curve_offset]
                    trans_tgt1 = points[counter_index + id_curve_offset]

                    diff_tgt0 = trans_tgt0 - trans_anchor
                    diff_tgt1 = trans_tgt1 - trans_anchor

                    trans_tgt1f = Gf.Vec3f(diff_tgt1.GetNormalized() * diff_tgt0.GetLength() + trans_anchor)

                    dirty |= self._set_points(points, counter_index + id_curve_offset, trans_tgt1f)

        if dirty:
            with omni.kit.undo.group():
                self._set_value_to_attribute(points_attr.GetPath(), points)

                # update extent
                self._update_extent_attribute(basis_curves)

    # smooth a corner or bezier corner.
    # equivalent to call bezier corner + smooth tangent
    def bezier(self, basis_curves: UsdGeom.BasisCurves, ids: List[int]):
        with omni.kit.undo.group():
            self.bezier_corner(basis_curves, ids)
            self.smooth_tangents(basis_curves, ids, force_smooth_anchor=True)

    # convert into bezier corner (tangent in the middle of anchor to prev/next tangent)
    def bezier_corner(self, basis_curves: UsdGeom.BasisCurves, ids: List[int]):
        wrap = basis_curves.GetWrapAttr().Get()

        points_attr = basis_curves.GetPointsAttr()
        points = points_attr.Get()

        curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
        curve_vertex_counts = curve_vertex_counts_attr.Get()

        dirty = False
        for id in ids:
            id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)

            index = id - id_curve_offset
            anchor_index = find_anchor_index(index)
            points_count = curve_vertex_counts[curve_index]

            if wrap == UsdGeom.Tokens.periodic:
                if anchor_index == points_count:
                    anchor_index = 0

            trans_anchor = points[anchor_index + id_curve_offset]

            if wrap == UsdGeom.Tokens.periodic or anchor_index > 2:
                tgt_index = (anchor_index - 1 + points_count) % points_count
                prev_tgt_index = (anchor_index - 2 + points_count) % points_count
                trans_prev_tgt = points[prev_tgt_index + id_curve_offset]

                dirty |= self._set_points(points, tgt_index + id_curve_offset, (trans_anchor + trans_prev_tgt) / 2.0)

            if wrap == UsdGeom.Tokens.periodic or anchor_index < points_count - 3:
                tgt_index = (anchor_index + 1) % points_count
                next_tgt_index = (anchor_index + 2) % points_count
                trans_next_tgt = points[next_tgt_index + id_curve_offset]

                dirty |= self._set_points(points, tgt_index + id_curve_offset, (trans_anchor + trans_next_tgt) / 2.0)

        if dirty:
            with omni.kit.undo.group():
                self._set_value_to_attribute(points_attr.GetPath(), points)

                # update extent
                self._update_extent_attribute(basis_curves)

    # make a hard corner (both tangents and anchor at same location)
    def corner(self, basis_curves: UsdGeom.BasisCurves, ids: List[int]):
        wrap = basis_curves.GetWrapAttr().Get()

        points_attr = basis_curves.GetPointsAttr()
        points = points_attr.Get()

        curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
        curve_vertex_counts = curve_vertex_counts_attr.Get()

        dirty = False
        for id in ids:
            id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)

            index = id - id_curve_offset
            anchor_index = find_anchor_index(index)
            points_count = curve_vertex_counts[curve_index]

            if wrap == UsdGeom.Tokens.periodic:
                if anchor_index == points_count:
                    anchor_index = 0

            trans_anchor = points[anchor_index + id_curve_offset]

            if wrap == UsdGeom.Tokens.periodic or anchor_index > 2:
                tgt_index = (anchor_index - 1 + points_count) % points_count
                dirty |= self._set_points(points, tgt_index + id_curve_offset, trans_anchor)

            if wrap == UsdGeom.Tokens.periodic or anchor_index < points_count - 3:
                tgt_index = (anchor_index + 1) % points_count
                dirty |= self._set_points(points, tgt_index + id_curve_offset, trans_anchor)

        if dirty:
            with omni.kit.undo.group():
                self._set_value_to_attribute(points_attr.GetPath(), points)

                # update extent
                self._update_extent_attribute(basis_curves)

    def open_close_curve(self, basis_curves: UsdGeom.BasisCurves):
        vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
        vertex_counts = vertex_counts_attr.Get()
        wrap_attr = basis_curves.GetWrapAttr()

        type_attr = basis_curves.GetTypeAttr()
        type = type_attr.Get()

        basis_attr = basis_curves.GetBasisAttr()
        basis = basis_attr.Get()

        points_attr = basis_curves.GetPointsAttr()
        points = points_attr.Get()

        widths_attr = basis_curves.GetWidthsAttr()
        widths = widths_attr.Get()
        widths_interpolation = basis_curves.GetWidthsInterpolation()

        normals_attr = basis_curves.GetNormalsAttr()
        normals = normals_attr.Get()
        normals_interpolation = basis_curves.GetNormalsInterpolation()

        new_points = []
        new_widths = []
        new_normals = []
        new_vertex_counts = []
        points_changed = False

        with omni.kit.undo.group():
            if wrap_attr.Get() == UsdGeom.Tokens.periodic:  # to open the curve
                # No need to remove more points on other curve type and basis.
                # in other cases, only set the UsdGeom.Tokens.nonperiodic token is enough
                if type == UsdGeom.Tokens.cubic and basis == UsdGeom.Tokens.bezier:
                    # pop the last 2 CVs and that's it
                    new_vertex_counts = list(vertex_counts)

                    points_offset = 0
                    varying_offset = 0
                    for curve_index, cv_count in enumerate(vertex_counts):
                        min_cv_count = 3
                        varying_count = (cv_count + 2) // 3
                        points_count_to_remove = 2

                        # Cannot "open" a curve with less than min_cv_count cvs
                        if cv_count >= min_cv_count:
                            points_changed = True
                            new_points += list(
                                points[points_offset : points_offset + cv_count - points_count_to_remove]
                            )

                            def append_primvar(interpolation, value, new_value):
                                if value:
                                    if interpolation == UsdGeom.Tokens.varying:
                                        new_value += list(value[varying_offset : varying_offset + varying_count - 1])

                                    elif interpolation == UsdGeom.Tokens.vertex:
                                        new_value += list(
                                            value[points_offset : points_offset + cv_count - points_count_to_remove]
                                        )

                            append_primvar(widths_interpolation, widths, new_widths)
                            append_primvar(normals_interpolation, normals, new_normals)

                            new_vertex_counts[curve_index] -= points_count_to_remove

                        points_offset += cv_count
                        varying_offset += varying_count
                change_wrap_to = UsdGeom.Tokens.nonperiodic
            else:  # to close the curve
                # create a duplicated cv with opposite tangent at the start cv and set curve to periodic

                # No need to add more points on other curve type and basis.
                # in other cases, only set the UsdGeom.Tokens.periodic token is enough
                if type == UsdGeom.Tokens.cubic and basis == UsdGeom.Tokens.bezier:
                    new_vertex_counts = list(vertex_counts)

                    points_offset = 0
                    varying_offset = 0
                    for curve_index, cv_count in enumerate(vertex_counts):
                        min_cv_count = 4
                        varying_count = (cv_count + 2) // 3
                        points_count_to_add = 2

                        # Cannot "close" a curve with less than min_cv_count cvs
                        if cv_count >= min_cv_count:
                            points_changed = True
                            new_points += list(points[points_offset : points_offset + cv_count])

                            def append_primvar(interpolation, value, new_value):
                                if value:
                                    if interpolation == UsdGeom.Tokens.varying:
                                        new_value += list(value[varying_offset : varying_offset + varying_count])

                                    elif interpolation == UsdGeom.Tokens.vertex:
                                        new_value += list(value[points_offset : points_offset + cv_count])

                            append_primvar(widths_interpolation, widths, new_widths)
                            append_primvar(normals_interpolation, normals, new_normals)

                            last_anchor = new_points[-1]
                            dup_anchor = points[points_offset]

                            last_tangent = new_points[-2]
                            extend_tangent = last_anchor + last_anchor - last_tangent
                            dup_tangent = dup_anchor + dup_anchor - points[points_offset + 1]

                            new_points.append(extend_tangent)
                            new_points.append(dup_tangent)

                            def duplicate_primvar(interpolation, value, new_value):
                                if value:
                                    if interpolation == UsdGeom.Tokens.varying:
                                        # repeat the first CV
                                        new_value.append(new_value[points_offset])

                                    elif interpolation == UsdGeom.Tokens.vertex:
                                        last_anchor_val = new_value[-1]
                                        first_anchor_val = new_value[points_offset]
                                        if type == UsdGeom.Tokens.cubic and basis == UsdGeom.Tokens.bezier:
                                            # repeat the first CV and last CV's tangent
                                            # To come up with better interpolation
                                            new_value.append(last_anchor_val)
                                            new_value.append(first_anchor_val)

                            duplicate_primvar(widths_interpolation, widths, new_widths)
                            duplicate_primvar(normals_interpolation, normals, new_normals)

                            new_vertex_counts[curve_index] += points_count_to_add

                        points_offset += cv_count
                        varying_offset += varying_count
                change_wrap_to = UsdGeom.Tokens.periodic

            if points_changed:
                self._set_value_to_attribute(prop_path=points_attr.GetPath(), value=new_points)

                # update extent
                self._update_extent_attribute(basis_curves)

                # optional widths and normals
                if widths:
                    self._set_value_to_attribute(prop_path=widths_attr.GetPath(), value=new_widths)

                if normals:
                    self._set_value_to_attribute(prop_path=normals_attr.GetPath(), value=new_normals)

                self._set_value_to_attribute(prop_path=vertex_counts_attr.GetPath(), value=new_vertex_counts)
            self._set_value_to_attribute(prop_path=wrap_attr.GetPath(), value=change_wrap_to)

    def delete_anchor_cvs(self, cv_dict: Dict[UsdGeom.BasisCurves, List[int]]):
        modified_vertex_counts = {}
        points_mask_dict = {}

        for basis_curves, ids in cv_dict.items():
            points_attr = basis_curves.GetPointsAttr()
            points = points_attr.Get()

            curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
            curve_vertex_counts = curve_vertex_counts_attr.Get()

            type_attr = basis_curves.GetTypeAttr()
            type = type_attr.Get()

            basis_attr = basis_curves.GetBasisAttr()
            basis = basis_attr.Get()

            wrap_attr = basis_curves.GetWrapAttr()
            wrap = wrap_attr.Get()

            for id in ids:
                id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)
                cv_index = id - id_curve_offset
                anchor_index = find_anchor_index(cv_index) if type == UsdGeom.Tokens.cubic else cv_index

                # only delete anchor CV, not tangent
                if cv_index != anchor_index:
                    carb.log_warn(f"Skip deleting CV at index {id}. Cannot remove only the tangent CV.")
                    continue

                points_count = curve_vertex_counts[curve_index]

                if wrap == UsdGeom.Tokens.periodic:
                    if anchor_index == points_count:
                        anchor_index = 0

                points_index_begin = id_curve_offset
                points_index_end = id_curve_offset + points_count - 1
                points_index = id_curve_offset + anchor_index

                if type == UsdGeom.Tokens.cubic and basis == UsdGeom.Tokens.bezier:
                    if points_index == points_index_begin:
                        lower_bound = points_index_begin
                        upper_bound = min(points_index + 2, points_index_end) + 1
                    elif points_index == points_index_end:
                        lower_bound = max(points_index - 2, points_index_begin)
                        upper_bound = points_index_end + 1
                    else:
                        lower_bound = max(points_index - 1, points_index_begin)
                        upper_bound = min(points_index + 1, points_index_end) + 1

                else:  # only remove the point itself if not cubic bezier
                    lower_bound = points_index
                    upper_bound = lower_bound + 1

                points_mask = points_mask_dict.get(basis_curves, None)
                if not points_mask:
                    points_mask = [True] * len(points)
                    points_mask_dict[basis_curves] = points_mask

                # an entry might already been removed, do not include it as removed CV from this time
                already_removed_entry_count = points_mask[lower_bound:upper_bound].count(False)

                points_mask[lower_bound:upper_bound] = [False] * (upper_bound - lower_bound)

                # Update vertex counts
                vertex_counts = modified_vertex_counts.get(basis_curves, None)
                if not vertex_counts:
                    vertex_counts = basis_curves.GetCurveVertexCountsAttr().Get()
                    modified_vertex_counts[basis_curves] = vertex_counts

                vertex_counts[curve_index] -= upper_bound - lower_bound - already_removed_entry_count

        with omni.kit.undo.group():
            for basis_curves, points_mask in points_mask_dict.items():
                points_attr = basis_curves.GetPointsAttr()
                points = points_attr.Get()

                wrap_attr = basis_curves.GetWrapAttr()
                wrap = wrap_attr.Get()
                is_periodic = wrap == UsdGeom.Tokens.periodic

                type_attr = basis_curves.GetTypeAttr()
                type = type_attr.Get()

                basis_attr = basis_curves.GetBasisAttr()
                basis = basis_attr.Get()

                vertex_counts = basis_curves.GetCurveVertexCountsAttr().Get()

                # optional
                widths = None
                widths_attr = basis_curves.GetWidthsAttr()
                if widths_attr:
                    widths_interpolation = basis_curves.GetWidthsInterpolation()
                    if widths_interpolation == UsdGeom.Tokens.varying or widths_interpolation == UsdGeom.Tokens.vertex:
                        widths = widths_attr.Get()
                    elif widths_interpolation != UsdGeom.Tokens.constant:
                        carb.log_warn("Unsupported interpolation mode for widths attribute")

                normals = None
                normals_attr = basis_curves.GetNormalsAttr()
                if normals_attr:
                    normals_interpolation = basis_curves.GetNormalsInterpolation()
                    if (
                        normals_interpolation == UsdGeom.Tokens.varying
                        or normals_interpolation == UsdGeom.Tokens.vertex
                    ):
                        normals = normals_attr.Get()
                    elif normals_interpolation != UsdGeom.Tokens.constant:
                        carb.log_warn("Unsupported interpolation mode for normals attribute")

                # collect points that's not masked as False (removed)
                modified_points = []
                modified_widths = []
                modified_normals = []
                curve_index = 0
                curve_points_offset = 0
                varying_attr_index = -1
                for i, point_mask in enumerate(points_mask):
                    vertex_count = vertex_counts[curve_index]
                    if i - curve_points_offset >= vertex_count:
                        curve_points_offset += vertex_count
                        curve_index += 1

                    is_anchor = False
                    if (i - curve_points_offset) % 3 == 0 or type == UsdGeom.Tokens.linear:
                        is_anchor = True
                        varying_attr_index += 1

                    if point_mask:
                        # use this to fix the last CV of a periodic curve to match the new last tangent if the first CV is removed
                        modify_last_periodic_cv = (
                            is_periodic
                            and basis == UsdGeom.Tokens.bezier
                            and type == UsdGeom.Tokens.cubic
                            and points_mask[curve_points_offset] == False
                            and i == curve_points_offset + vertex_count - 1
                        )

                        modified_points.append(points[i])
                        if modify_last_periodic_cv:
                            modified_points[-1] = points[curve_points_offset + 2]

                        if widths:
                            if widths_interpolation == UsdGeom.Tokens.varying:
                                # Every curve anchor has a value
                                if is_anchor:
                                    modified_widths.append(widths[varying_attr_index])
                            elif widths_interpolation == UsdGeom.Tokens.vertex:
                                # Every curve vertex has a value
                                modified_widths.append(widths[i])
                                if modify_last_periodic_cv:
                                    modified_widths[-1] = widths[curve_points_offset + 2]

                        if normals:
                            if normals_interpolation == UsdGeom.Tokens.varying:
                                # Every curve anchor has a value
                                if is_anchor:
                                    modified_normals.append(normals[varying_attr_index])
                            elif normals_interpolation == UsdGeom.Tokens.vertex:
                                # Every curve vertex has a value
                                modified_normals.append(normals[i])
                                if modify_last_periodic_cv:
                                    modified_normals[-1] = widths[modified_normals + 2]

                # update points
                self._set_value_to_attribute(points_attr.GetPath(), modified_points)

                # update extent
                self._update_extent_attribute(basis_curves)

                # update curveVertexCounts
                vertex_counts = modified_vertex_counts.get(basis_curves, None)
                if vertex_counts is not None:
                    # remove the entry that has no points left
                    vertex_counts = [counts for counts in vertex_counts if counts != 0]
                    self._set_value_to_attribute(
                        prop_path=basis_curves.GetCurveVertexCountsAttr().GetPath(), value=vertex_counts
                    )

                # update widths:
                if widths is not None:
                    self._set_value_to_attribute(
                        prop_path=basis_curves.GetWidthsAttr().GetPath(), value=modified_widths
                    )

                # update normals:
                if normals is not None:
                    self._set_value_to_attribute(
                        prop_path=basis_curves.GetNormalsAttr().GetPath(), value=modified_normals
                    )

    def split_at_anchor_cvs(
        self,
        cv_dict: Dict[UsdGeom.BasisCurves, List[int]],
        to_new_basis_curves: bool,
        split_points_indices_result: defaultdict[UsdGeom.BasisCurves, list[int]] = None,
    ):
        """
        Splits basisCurves prim at given point indices. The index has to be anchor cv or it will be skipped.

        Args:
            cv_dict: a dictionary from basisCurves prim to the indices list to split at.
            to_new_basis_curves: When True, a new basisCurves prim will be created for each split new curve. Otherwise, they will be put in the same basisCurves prim but a new curve within in.
            split_points_indices_result: point index at which the curve is split. If to_new_basis_curves, the newly created basisCurves will be in this dict too with either or both of its starting and ending point in the list
        """

        with omni.kit.undo.group():
            for basis_curves, ids in cv_dict.items():
                # record the indices at which these attributes are split, so when to_new_basis_curves is true, we can
                # "cut" at these indices and make them into new basisCurves
                # All of them are in reverse order (larger index at front)
                split_points_indices: list[int] = []
                split_curve_vertex_counts_indices: list[int] = []
                split_widths_indices: list[int] = []
                split_normals_indices: list[int] = []

                if not ids:
                    continue

                wrap_attr = basis_curves.GetWrapAttr()
                wrap = wrap_attr.Get()
                if wrap == UsdGeom.Tokens.periodic:
                    carb.log_warn(
                        f"Splitting at CV(s) on periodic curves {basis_curves.GetPrim().GetPath()} is unsupported. Skipping..."
                    )
                    continue

                points_attr = basis_curves.GetPointsAttr()
                points = points_attr.Get()

                type_attr = basis_curves.GetTypeAttr()
                curve_type = type_attr.Get()

                curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
                curve_vertex_counts = curve_vertex_counts_attr.Get()

                if not points or not curve_vertex_counts:
                    continue

                # reverse sort the ids for easier processing
                # splitting curve cvs from back to front
                ids_sorted = ids.copy()
                ids_sorted.sort(reverse=True)

                # optional widths and normals
                # only need to update them if they exist and interpolation mode is varying or vertex.
                # in both case, just need to duplicate the value at proper index (path segment index or vertex index)
                widths_attr, new_widths, widths_interpolation = get_primvars_value_and_interpolation(
                    basis_curves,
                    lambda basis_curves: basis_curves.GetWidthsAttr(),
                    lambda basis_curves: basis_curves.GetWidthsInterpolation(),
                    UsdGeom.Tokens.widths,
                )

                normals_attr, new_normals, normals_interpolation = get_primvars_value_and_interpolation(
                    basis_curves,
                    lambda basis_curves: basis_curves.GetNormalsAttr(),
                    lambda basis_curves: basis_curves.GetNormalsInterpolation(),
                    UsdGeom.Tokens.normals,
                )

                type_attr = basis_curves.GetTypeAttr()
                type = type_attr.Get()

                new_curve_vertex_counts: list[int] = []
                new_points = list(points)

                processed_cv_index = -1
                # process each curve from back to the front
                split_points_count = None
                curve_index = len(curve_vertex_counts) - 1
                while curve_index >= 0 and processed_cv_index < len(ids_sorted):
                    if processed_cv_index < len(ids_sorted) - 1:
                        cv_index_to_process = processed_cv_index + 1
                        id = ids_sorted[cv_index_to_process]

                        id_curve_offset, id_curve_index = get_array_index_offset_and_curve_index(
                            id, curve_vertex_counts
                        )
                        cv_index = id - id_curve_offset

                        anchor_index = find_anchor_index(cv_index) if type == UsdGeom.Tokens.cubic else cv_index
                    else:
                        # all cv has been processed, mark a negative curve index to trigger copy
                        id_curve_index = -1

                    points_count = curve_vertex_counts[curve_index]

                    skip_process_cv = False
                    if id_curve_index == curve_index:
                        # only delete anchor CV, not tangent
                        if cv_index != anchor_index:
                            carb.log_warn(f"Skip splitting CV at index {id}. Cannot split at only the tangent CV.")
                            skip_process_cv = True

                        # do not split curve at the first or last anchor CV
                        if anchor_index == points_count - 1 or anchor_index == 0:
                            carb.log_warn(
                                f"Skip splitting CV at index {id}. Cannot split curve at the beginning or end of a segment."
                            )
                            skip_process_cv = True

                    if skip_process_cv or id_curve_index < curve_index:
                        # Have not hit the curve to be split. Copy the entire to new array
                        new_curve_vertex_counts.append(points_count)

                        if skip_process_cv:
                            processed_cv_index = cv_index_to_process

                        # nothing to process on this curve, move onto the next
                        curve_index -= 1
                    else:
                        if split_points_count is None:
                            split_points_count = points_count

                        # append a new curve
                        new_curve_size = split_points_count - anchor_index
                        new_curve_vertex_counts.append(new_curve_size)
                        split_curve_vertex_counts_indices.append(curve_index)
                        new_points.insert(id, new_points[id])
                        split_points_indices.append(id)

                        def split_primvars(primvar_data, interpolation):
                            if primvar_data:
                                if interpolation == UsdGeom.Tokens.constant:
                                    # do nothing
                                    return None
                                if curve_type == UsdGeom.Tokens.linear or interpolation == UsdGeom.Tokens.vertex:
                                    # if curve type is linear or interpolation is vertex, primvar has same number of entry as points
                                    # constant interpolation has been filtered out when fetching primvar values at the very beginning.
                                    primvar_data.insert(id, primvar_data[id])
                                    return id
                                elif interpolation == UsdGeom.Tokens.varying:
                                    # cubic varying
                                    # need to find the varying index, that is anchor_index // 3 on current curve,
                                    # then it needs to be converted to the global index on the entire basisCurves primvar array.

                                    # collect all preceding curves varying index
                                    varying_index = 0
                                    for i in range(curve_index):
                                        v_count = curve_vertex_counts[i]
                                        varying_index += ((v_count - 4) // 3 + 1) + 1  # segment count + 1

                                    # add current varying index
                                    varying_index += anchor_index // 3
                                    primvar_data.insert(varying_index, primvar_data[varying_index])
                                    return varying_index

                                # no need to handle constant interpolation since it only has one entry for entire basisCurves
                            return None

                        ret = split_primvars(new_widths, widths_interpolation)
                        if ret is not None:
                            split_widths_indices.append(ret)
                        ret = split_primvars(new_normals, normals_interpolation)
                        if ret is not None:
                            split_normals_indices.append(ret)

                        split_points_count -= new_curve_size - 1  # minus 1 to duplicate the split CV

                        # current split CV has been processed
                        processed_cv_index = cv_index_to_process

                        # check if current curve is finished
                        next_cv_index_to_process = processed_cv_index + 1

                        finished_curve = False
                        if next_cv_index_to_process >= len(ids_sorted):
                            # nothing more to process
                            finished_curve = True
                        else:
                            _, next_id_curve_index = get_array_index_offset_and_curve_index(
                                ids_sorted[next_cv_index_to_process], curve_vertex_counts
                            )

                            if next_id_curve_index != curve_index:
                                # the next split id is on a different curve, finish up this curve and move onto the next
                                finished_curve = True

                        if finished_curve:
                            # copy the data for the rest of the curve
                            new_curve_vertex_counts.append(split_points_count)

                            # move onto next curve
                            curve_index -= 1
                            split_points_count = None

                    # move onto next id or curve

                # if we have actually split the curve (some CV might be skipped)
                if split_points_indices:
                    new_curve_vertex_counts.reverse()

                    # since we duplicated the entries in each array, we need to add offset to each index
                    # index array is in reversed order (larger index -> smaller index)
                    def add_offset(ids):
                        ids_len = len(ids)
                        for i, id in enumerate(ids):
                            ids[i] = id + ids_len - i

                    if to_new_basis_curves:
                        # to split the curves into new basisCurves prim(s)
                        add_offset(split_points_indices)
                        add_offset(split_widths_indices)
                        add_offset(split_normals_indices)
                        add_offset(split_curve_vertex_counts_indices)

                        new_prims_count = len(split_points_indices)
                        basis_curves_list = []
                        current_prim_path = basis_curves.GetPrim().GetPath()
                        stage = basis_curves.GetPrim().GetStage()
                        for i in range(new_prims_count):
                            path_to = omni.usd.get_stage_next_free_path(stage, current_prim_path, False)
                            omni.kit.commands.execute(
                                "CopyPrim",
                                path_from=current_prim_path,
                                path_to=path_to,
                                duplicate_layers=True,
                            )
                            basis_curves_list.append(UsdGeom.BasisCurves.Get(stage, path_to))

                        # put in the order of basis_curves_03, basis_curves_02, basis_curves_01, basis_curves
                        # because split_indices are in reversed order, so the front slices maps to later duplicated prims
                        basis_curves_list.reverse()
                        basis_curves_list.append(basis_curves)

                        def slice_attr_for_curves(new_attr_data: list, split_indices: list[int], attr_name: str):
                            if not split_indices:
                                return

                            start_index = split_indices[0]
                            end_index = len(new_attr_data)
                            for i in range(len(split_indices) + 1):
                                split_basis_curves = basis_curves_list[i]
                                self._set_value_to_attribute(
                                    split_basis_curves.GetPrim().GetPath().AppendProperty(attr_name),
                                    new_attr_data[start_index:end_index],
                                )
                                end_index = start_index
                                start_index = split_indices[i + 1] if i + 1 < len(split_indices) else 0

                        # for points, widths and normal, the values are in normal order, and split_points_indices in revered order
                        slice_attr_for_curves(new_points, split_points_indices, UsdGeom.Tokens.points)
                        slice_attr_for_curves(new_widths, split_widths_indices, UsdGeom.Tokens.widths)
                        slice_attr_for_curves(new_normals, split_normals_indices, UsdGeom.Tokens.normals)
                        slice_attr_for_curves(
                            new_curve_vertex_counts, split_curve_vertex_counts_indices, UsdGeom.Tokens.curveVertexCounts
                        )

                        # because points are split into multiple basisCurves, the extent needs to be updated too
                        for basis_curves in basis_curves_list:
                            extent_attr = basis_curves.GetExtentAttr()
                            if extent_attr:
                                bounds = UsdGeom.Boundable.ComputeExtentFromPlugins(
                                    basis_curves, Usd.TimeCode.Default()
                                )
                                if bounds is not None:
                                    self._set_value_to_attribute(extent_attr.GetPath(), bounds)

                        # update the result dict
                        if split_points_indices_result is not None:
                            # again note that basis_curves_list is in reversed order, the last one is the original prim
                            for i, basis_curves in enumerate(basis_curves_list):
                                points = basis_curves.GetPointsAttr().Get()
                                if len(points) > 0:
                                    # the split point is either the first or the last point, or both
                                    if i > 0:  # if basisCurve is not the last split one
                                        split_points_indices_result[basis_curves].append(len(points) - 1)
                                    if i < len(basis_curves_list) - 1:  # if basisCurve is not the original prim
                                        split_points_indices_result[basis_curves].append(0)
                    else:
                        # to split the curves within current basisCurves prim
                        self._set_value_to_attribute(points_attr.GetPath(), new_points)
                        self._set_value_to_attribute(curve_vertex_counts_attr.GetPath(), new_curve_vertex_counts)
                        if new_widths:
                            self._set_value_to_attribute(widths_attr.GetPath(), new_widths)
                        if new_normals:
                            self._set_value_to_attribute(normals_attr.GetPath(), new_normals)

                        if split_points_indices_result is not None:
                            add_offset(split_points_indices)
                            for i in range(len(split_points_indices) - 1, -1, -1):
                                split_points_indices.insert(i, split_points_indices[i] - 1)
                            split_points_indices_result[basis_curves] = split_points_indices

    def delete_and_split_anchor_cvs(self, cv_dict: Dict[UsdGeom.BasisCurves, List[int]], to_new_basis_curves: bool):
        """
        Similar to split_at_anchor_cvs, but it also deletes the CV(s) being split at
        """
        split_points_indices_result: defaultdict[UsdGeom.BasisCurves, list[int]] = defaultdict(list)

        with omni.kit.undo.group():
            self.split_at_anchor_cvs(cv_dict, to_new_basis_curves, split_points_indices_result)
            self.delete_anchor_cvs(split_points_indices_result)

    def create_new_bezier_curve_and_edit(self, mode: CurveEditingModeType) -> bool:
        ret = False
        with omni.kit.undo.group():
            # if other curves are being edited, quit their edit mode first
            if self._curve_manip.is_in_curve_editing_mode(self._curve_context):
                omni.kit.commands.execute("DisableCurveEditing", curve_context=self._curve_context)

            with omni.kit.usd.layers.active_authoring_layer_context(self._context):
                omni.kit.commands.execute(
                    "CreatePrim",
                    prim_type="BasisCurves",
                    attributes={
                        UsdGeom.Tokens.basis: UsdGeom.Tokens.bezier,
                        UsdGeom.Tokens.type: UsdGeom.Tokens.cubic,
                        UsdGeom.Tokens.purpose: self._settings.get(
                            Constants.DEFAULT_USDGEOM_BASISCURVE_PURPOSE_SETTING
                        ),
                    },
                    select_new_prim=True,
                )

            paths = self._selection.get_selected_prim_paths()
            if len(paths) == 1 and UsdGeom.BasisCurves.Get(self._context.get_stage(), paths[0]):
                attr_path = Sdf.Path(paths[0]).AppendProperty("omni:scene:visualization:drawWireframe")
                omni.kit.commands.execute(
                    "ChangeProperty",
                    prop_path=attr_path,
                    value=True,
                    prev=None,
                    usd_context_name=self._context,
                    type_to_create_if_not_exist=Sdf.ValueTypeNames.Bool,
                )

                omni.kit.commands.execute(
                    "EnableCurveEditing", curve_context=self._curve_context, paths=[paths[0]], mode=mode
                )
                ret = True

        return ret

    def insert_cv(self, basis_curves: UsdGeom.BasisCurves, curve_index: int, segment_start_index: int, t: float):
        basis = basis_curves.GetBasisAttr().Get()
        if basis != UsdGeom.Tokens.bezier:
            return

        type = basis_curves.GetTypeAttr().Get()

        points_attr = basis_curves.GetPointsAttr()
        points = points_attr.Get()
        curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
        curve_vertex_counts = curve_vertex_counts_attr.Get()
        wrap = basis_curves.GetWrapAttr().Get()
        is_periodic = wrap == UsdGeom.Tokens.periodic

        varying_offset = 0
        for i in range(curve_index):
            if type == UsdGeom.Tokens.cubic:
                varying_offset += (curve_vertex_counts[i] + 2) // 3
            else:
                varying_offset += curve_vertex_counts[i]

        curve_points_offset = 0
        for i in range(curve_index):
            curve_points_offset += curve_vertex_counts[i]

        segment_points_array_start_index = curve_points_offset + segment_start_index

        if type == UsdGeom.Tokens.cubic:
            # subdiv at t
            subdiv = self._subdiv_curve(
                points,
                segment_points_array_start_index,
                curve_points_offset,
                curve_points_offset + curve_vertex_counts[curve_index],
                is_periodic,
                t,
            )

            points_list = list(points)

            if is_periodic and segment_start_index + 3 == curve_vertex_counts[curve_index]:
                # if inserting to the last segment of periodic cubic bezier curve, the last CV is a "virtual" one and do
                # not need to be inserted
                new_points = (
                    points_list[:segment_points_array_start_index]
                    + subdiv[:-1]
                    + points_list[segment_points_array_start_index + 3 :]
                )
            else:
                new_points = (
                    points_list[:segment_points_array_start_index]
                    + subdiv
                    + points_list[segment_points_array_start_index + 4 :]
                )

            # optional
            def interpolate_primvar(get_attr_fn_name, get_attr_interpolation_fn_name, normalize=False):
                new_value = None
                get_attr_func = getattr(basis_curves, get_attr_fn_name)
                attr = get_attr_func()
                if attr:
                    value = attr.Get()
                    if value:
                        get_attr_interpolation_fn = getattr(basis_curves, get_attr_interpolation_fn_name)
                        interpolation = get_attr_interpolation_fn()
                        if interpolation == UsdGeom.Tokens.varying:
                            anchor_lo_index = varying_offset + segment_start_index // 3
                            anchor_hi_index = varying_offset + (segment_start_index) // 3 + 1
                            v_lo = value[anchor_lo_index]
                            v_hi = value[anchor_hi_index]
                            new_value = list(value)
                            subdiv_value = v_lo * (1 - t) + v_hi * t
                            if normalize:
                                subdiv_value.Normalize()
                            new_value.insert(anchor_hi_index, subdiv_value)

                        elif interpolation == UsdGeom.Tokens.vertex:
                            value_list = list(value)

                            subdiv_value = self._subdiv_curve(
                                value,
                                segment_points_array_start_index,
                                curve_points_offset,
                                curve_points_offset + curve_vertex_counts[curve_index],
                                is_periodic,
                                t,
                            )
                            if normalize:
                                subdiv_value.Normalize()

                            if is_periodic and segment_start_index + 3 == curve_vertex_counts[curve_index]:
                                new_value = (
                                    value_list[:segment_points_array_start_index]
                                    + subdiv_value[:-1]
                                    + value_list[segment_points_array_start_index + 3 :]
                                )
                            else:
                                new_value = (
                                    value_list[:segment_points_array_start_index]
                                    + subdiv_value
                                    + value_list[segment_points_array_start_index + 4 :]
                                )

                        elif interpolation != UsdGeom.Tokens.constant:
                            carb.log_warn(f"Unsupported interpolation mode {interpolation} during {get_attr_fn_name}")
                return new_value

            new_widths = interpolate_primvar("GetWidthsAttr", "GetWidthsInterpolation")

            # FIXME linear interpolation of normals is incorrect. Should interpolate the rotation instead.
            new_normals = interpolate_primvar("GetNormalsAttr", "GetNormalsInterpolation", True)

            curve_vertex_counts[curve_index] += 3
        else:
            new_points = list(points)
            if is_periodic and segment_start_index == curve_vertex_counts[curve_index] - 1:
                end_index = curve_points_offset
            else:
                end_index = segment_points_array_start_index + 1

            new_points.insert(
                segment_points_array_start_index + 1,
                new_points[segment_points_array_start_index] * (1 - t) + new_points[end_index] * t,
            )

            # optional
            def interpolate_primvar(get_attr_fn_name, get_attr_interpolation_fn_name, normalize=False):
                new_value = None
                get_attr_func = getattr(basis_curves, get_attr_fn_name)
                attr = get_attr_func()
                if attr:
                    value = attr.Get()
                    if value:
                        get_attr_interpolation_fn = getattr(basis_curves, get_attr_interpolation_fn_name)
                        interpolation = get_attr_interpolation_fn()
                        if interpolation == UsdGeom.Tokens.varying or interpolation == UsdGeom.Tokens.vertex:
                            anchor_lo_index = segment_points_array_start_index
                            anchor_hi_index = segment_points_array_start_index + 1
                            v_lo = value[anchor_lo_index]
                            v_hi = value[end_index]
                            subdiv_value = v_lo * (1 - t) + v_hi * t
                            if normalize:
                                subdiv_value.Normalize()
                            new_value = list(value)
                            new_value.insert(anchor_hi_index, subdiv_value)

                        elif interpolation != UsdGeom.Tokens.constant:
                            carb.log_warn(f"Unsupported interpolation mode {interpolation} during {get_attr_fn_name}")
                return new_value

            new_widths = interpolate_primvar("GetWidthsAttr", "GetWidthsInterpolation")

            # FIXME linear interpolation of normals is incorrect. Should interpolate the rotation instead.
            new_normals = interpolate_primvar("GetNormalsAttr", "GetNormalsInterpolation", True)

            curve_vertex_counts[curve_index] += 1

        with omni.kit.undo.group():
            self._set_value_to_attribute(prop_path=points_attr.GetPath(), value=new_points)
            self._set_value_to_attribute(prop_path=curve_vertex_counts_attr.GetPath(), value=curve_vertex_counts)

            if new_widths is not None:
                self._set_value_to_attribute(prop_path=basis_curves.GetWidthsAttr().GetPath(), value=new_widths)

            if new_normals is not None:
                self._set_value_to_attribute(prop_path=basis_curves.GetNormalsAttr().GetPath(), value=new_normals)

    @carb.profiler.profile
    def add_cv(self, basis_curves: UsdGeom.BasisCurves, pos: Gf.Vec3f, type: CurvesEventType, add_new_curve: bool):
        curve_type = basis_curves.GetTypeAttr().Get()

        if type == int(CurvesEventType.BEGIN_ADD):
            carb.profiler.begin(0, "CurvesEventType.BEGIN_ADD")
            self._hack_toggle_active = True
            points_attr = basis_curves.GetPointsAttr()
            points = points_attr.Get()

            if points is None or len(points) <= 0:
                interpolation_type = self._settings.get(INTERPOLATE_MODE_SETTING)
                curve_type = UsdGeom.Tokens.cubic if interpolation_type == "cubic" else UsdGeom.Tokens.linear
                omni.usd.set_prop_val(basis_curves.GetTypeAttr(), curve_type)

            widths_attr = basis_curves.GetWidthsAttr()
            widths = widths_attr.Get()
            widths_interpolation = basis_curves.GetWidthsInterpolation()

            normals_attr = basis_curves.GetNormalsAttr()
            normals = normals_attr.Get()
            normals_interpolation = basis_curves.GetNormalsInterpolation()

            vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
            vertex_counts = vertex_counts_attr.Get()

            # save off the points for undo operation
            self._prev_points_value = points if points else []
            self._prev_widths_value = widths if widths else []
            self._prev_normals_value = normals if normals else []
            self._prev_vertex_counts_value = vertex_counts if vertex_counts else []

            points = points_attr.Get()
            widths = widths_attr.Get()
            normals = normals_attr.Get()
            vertex_counts = vertex_counts_attr.Get()

            periodic_cv = None
            periodic_tangent = None
            points_list = list(points) if points else []
            widths_list = list(widths) if widths else []
            normals_list = list(normals) if normals else None
            vertex_counts_list = list(vertex_counts) if vertex_counts else []

            curve_has_tangents = has_tangents(basis_curves)
            is_periodic = basis_curves.GetWrapAttr().Get() == UsdGeom.Tokens.periodic
            if is_periodic:
                if not add_new_curve and len(vertex_counts_list) > 0 and vertex_counts_list[-1] >= 2:
                    # periodic_cv locates at the beginning of the curve
                    periodic_cv = points_list[-vertex_counts_list[-1]]
                    if curve_has_tangents:
                        if vertex_counts_list[-1] >= 4:
                            periodic_tangent = points_list[-1]
                            points_list = points_list[:-1]
                        else:
                            periodic_tangent = periodic_cv + periodic_cv - points_list[-vertex_counts_list[-1] + 1]

            cache = UsdGeom.XformCache()
            world_xform = cache.GetLocalToWorldTransform(basis_curves.GetPrim())
            world_xform_inv = world_xform.GetInverse()

            curve_space_pos = Gf.Vec3f(world_xform_inv.Transform(pos))

            if curve_type == UsdGeom.Tokens.cubic and not add_new_curve:
                if len(vertex_counts_list) > 0 and vertex_counts_list[-1] >= 2:
                    if is_periodic:
                        # if periodic, just add the cv
                        points_list.append(curve_space_pos)
                    elif vertex_counts_list[-1] >= 4:
                        # If there's >= 4 CVs already, extend the tangent of last CV to opposite direction.
                        last_tangent = points_list[-2]
                        last_cv = points_list[-1]

                        new_tangent = last_cv + last_cv - last_tangent
                        points_list.append(new_tangent)

                    # widths and normals are optional attributes
                    # just repeat the last value for now. To come up with better extrapolation method
                    if widths_list and widths_interpolation == UsdGeom.Tokens.vertex:
                        widths_list.append(widths_list[-1])

                    if normals_list and normals_interpolation == UsdGeom.Tokens.vertex:
                        normals_list.append(normals_list[-1])

            points_list.append(curve_space_pos)

            if curve_type == UsdGeom.Tokens.cubic:
                points_list.append(curve_space_pos)

            if periodic_cv is not None:
                if periodic_tangent is not None:
                    points_list.append(periodic_tangent)

            # adding new periodic cubic bezier segment
            # need an additional repeated tangent at the end
            if add_new_curve and has_tangents and is_periodic and len(points_list) - len(self._prev_points_value) == 2:
                points_list.append(points_list[-2] + points_list[-2] - points_list[-1])

            omni.usd.set_prop_val(points_attr, points_list)

            # widths and normals are optional attributes
            # just repeat the last value for now. To come up with better extrapolation method
            def extrapolate_primvar(interpolation, value_list, default_value=None):
                if value_list is not None:
                    if len(value_list) > 0:
                        if interpolation == UsdGeom.Tokens.varying:
                            value_list.append(value_list[-1])

                        elif interpolation == UsdGeom.Tokens.vertex:
                            value_list += [value_list[-1]] * (len(points_list) - len(value_list))

                        elif interpolation != UsdGeom.Tokens.constant:
                            carb.log_warn(f"Unsupported interpolation mode {interpolation} when adding new CV")

                    elif default_value is not None:
                        if interpolation == UsdGeom.Tokens.varying:
                            value_list.append(default_value)

                        elif interpolation == UsdGeom.Tokens.vertex:
                            value_list += [default_value] * (len(points_list) - len(value_list))

                        else:
                            carb.log_warn(f"Unsupported interpolation mode {interpolation} when adding new CV")

            extrapolate_primvar(widths_interpolation, widths_list, self.__get_default_width())
            extrapolate_primvar(normals_interpolation, normals_list)

            omni.usd.set_prop_val(widths_attr, widths_list)

            if normals_list:
                omni.usd.set_prop_val(normals_attr, normals_list)

            vert_diff = len(points_list) - len(self._prev_points_value)
            if len(vertex_counts_list) <= 0:
                vertex_counts_list = [vert_diff]
            elif add_new_curve:
                vertex_counts_list.append(vert_diff)
            else:
                vertex_counts_list[-1] += vert_diff
            omni.usd.set_prop_val(vertex_counts_attr, vertex_counts_list)
            carb.profiler.end(0)

        elif type == int(CurvesEventType.ADDING):
            carb.profiler.begin(0, "CurvesEventType.ADDING")
            if curve_type == UsdGeom.Tokens.cubic:
                points_attr = basis_curves.GetPointsAttr()
                points = points_attr.Get()

                cache = UsdGeom.XformCache()
                world_xform = cache.GetLocalToWorldTransform(basis_curves.GetPrim())
                world_xform_inv = world_xform.GetInverse()
                curve_space_pos = Gf.Vec3f(world_xform_inv.Transform(pos))

                vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
                vertex_counts = vertex_counts_attr.Get()

                count = 0
                count_offset = 0
                if vertex_counts and len(vertex_counts) > 0:
                    count = vertex_counts[-1]
                    for count_index in range(len(vertex_counts) - 1):
                        count_offset += vertex_counts[count_index]

                if count < 4 or add_new_curve:
                    points[count_offset + 1] = curve_space_pos
                else:
                    is_periodic = has_tangents(basis_curves) and (
                        basis_curves.GetWrapAttr().Get() == UsdGeom.Tokens.periodic
                    )
                    if is_periodic:
                        count_offset -= 2

                    last_tangent = points[count_offset + count - 2]
                    last_cv = points[count_offset + count - 1]

                    last_tangent = last_cv - curve_space_pos + last_cv

                    points[count_offset + count - 2] = last_tangent
                    if is_periodic:
                        points[count_offset + count] = curve_space_pos

                carb.profiler.begin(0, "CurvesEventType.ADDING.set_prop_val")
                omni.usd.set_prop_val(points_attr, points)
                carb.profiler.end(0)

                self.__hack_ensure_wireframe_visible(basis_curves, points)

            carb.profiler.end(0)

        elif type == int(CurvesEventType.END_ADD):
            carb.profiler.begin(0, "CurvesEventType.END_ADD")
            points_attr = basis_curves.GetPointsAttr()
            vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()

            self.__hack_ensure_wireframe_visible(basis_curves, points_attr.Get())
            self._hack_toggle_active = False

            with omni.kit.undo.group():
                if len(self._prev_points_value) <= 0:
                    interpolation_type = self._settings.get(INTERPOLATE_MODE_SETTING)
                    curve_type = UsdGeom.Tokens.cubic if interpolation_type == "cubic" else UsdGeom.Tokens.linear
                    self._set_value_to_attribute(basis_curves.GetTypeAttr().GetPath(), curve_type)

                self._set_value_to_attribute(
                    vertex_counts_attr.GetPath(), vertex_counts_attr.Get(), self._prev_vertex_counts_value
                )
                self._set_value_to_attribute(points_attr.GetPath(), points_attr.Get(), self._prev_points_value)

                # update extent
                self._update_extent_attribute(basis_curves)

                # Only set widths and normals if they exists before
                if self._prev_widths_value:
                    widths_attr = basis_curves.GetWidthsAttr()
                    self._set_value_to_attribute(widths_attr.GetPath(), widths_attr.Get(), self._prev_widths_value)

                if self._prev_normals_value:
                    normals_attr = basis_curves.GetNormalsAttr()
                    self._set_value_to_attribute(normals_attr.GetPath(), normals_attr.Get(), self._prev_normals_value)

            self._prev_points_value = None
            self._prev_vertex_counts_value = None
            carb.profiler.end(0)

    def add_points_to_curve(
        self,
        prim_path: Union[str, Sdf.Path],
        interpolation_type: int,
        points: Union[List[Gf.Vec3f], Vt.Vec3fArray],
        add_new_curve: bool,
    ):
        def extrapolate_primvar(attr, interpolation, previous_count, new_count):
            attr_value = attr.Get()
            if attr_value is not None:
                value_list = [v for v in attr_value]
            else:
                value_list = []
            if len(value_list) > 0:
                add_count = 0
                if interpolation == UsdGeom.Tokens.varying:
                    add_count = max(0, new_count - previous_count)
                elif interpolation == UsdGeom.Tokens.vertex:
                    add_count = max(0, new_count - len(value_list))
                elif interpolation != UsdGeom.Tokens.constant:
                    carb.log_warn(f"Unsupported interpolation mode {interpolation} when adding new CV")
                if add_count > 0:
                    for _ in range(add_count):
                        value_list.append(value_list[-1])
                    self._set_value_to_attribute(attr.GetPath(), value_list, attr_value)

        basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Get(self._context.get_stage(), prim_path)
        cache = UsdGeom.XformCache()
        world_xform = cache.GetLocalToWorldTransform(basis_curves.GetPrim())
        world_xform_inv = world_xform.GetInverse()

        wrap = basis_curves.GetWrapAttr().Get()
        is_periodic = wrap == UsdGeom.Tokens.periodic
        curve_type = basis_curves.GetTypeAttr().Get()
        basis = basis_curves.GetBasisAttr().Get()

        attr_counts = basis_curves.GetCurveVertexCountsAttr()
        previous_counts = attr_counts.Get()

        # If the current curve to _append_ has invalid number of vertices, do not proceed furtuer
        if (
            not add_new_curve
            and previous_counts
            and not self._validate_point_count(basis, curve_type, wrap, previous_counts[-1])
        ):
            carb.log_warn(f"Cannot append vertices to incomplete curve {prim_path}")
            return

        point_count = len(points)
        can_add = False
        if add_new_curve:
            can_add = self._validate_point_count(
                basis,
                curve_type,
                UsdGeom.Tokens.nonperiodic,  # always act as if adding nonperiodic, since the periodic will be opened first then closed later
                point_count,
            )
        else:
            if curve_type == UsdGeom.Tokens.linear:
                can_add = point_count > 0
            elif curve_type == UsdGeom.Tokens.cubic:
                # Cannot handle other cubic types yet
                if basis == UsdGeom.Tokens.bezier:
                    can_add = point_count > 3

        if can_add:
            with omni.kit.undo.group():
                if is_periodic:
                    self.open_close_curve(basis_curves)
                    # update the counts since it has changed after open_close_curve
                    previous_counts = attr_counts.Get()
                attr_points = basis_curves.GetPointsAttr()
                previous_points = attr_points.Get()
                previous_points_array = [pt for pt in previous_points] if previous_points is not None else []
                previous_counts_array = [c for c in previous_counts] if previous_counts is not None else []
                new_counts_array = previous_counts_array + []
                new_points_array = [
                    Gf.Vec3f(world_xform_inv.Transform(pt)) for pt in points
                ]  # points come in world space. transform them back into curve's local space
                if previous_points is None or len(previous_points_array) <= 0:
                    attr_type = basis_curves.GetTypeAttr()
                    type = (
                        UsdGeom.Tokens.cubic
                        if interpolation_type == int(CurveInterpolateTypes.CUBIC)
                        else UsdGeom.Tokens.linear
                    )
                    self._set_value_to_attribute(attr_type.GetPath(), type)
                if add_new_curve:
                    if has_tangents(basis_curves):
                        point_count = 3 * int(point_count / 3) + 1
                        new_points_array = new_points_array[:point_count]
                    new_counts_array.append(point_count)
                elif len(new_counts_array) > 0:
                    if has_tangents(basis_curves):
                        new_point_count = new_counts_array[-1] + point_count
                        new_point_count = 3 * int(new_point_count / 3) + 1
                        point_count = new_point_count - new_counts_array[-1]
                        new_points_array = new_points_array[:point_count]
                    new_counts_array[-1] += point_count
                else:
                    if has_tangents(basis_curves):
                        point_count = 3 * int(point_count / 3) + 1
                        new_points_array = new_points_array[:point_count]
                    new_counts_array.append(point_count)
                new_points_array = previous_points_array + new_points_array
                self._set_value_to_attribute(attr_counts.GetPath(), new_counts_array, previous_counts)
                self._set_value_to_attribute(attr_points.GetPath(), new_points_array, previous_points)
                extrapolate_primvar(
                    basis_curves.GetWidthsAttr(),
                    basis_curves.GetWidthsInterpolation(),
                    len(previous_points_array),
                    len(new_points_array),
                )
                extrapolate_primvar(
                    basis_curves.GetNormalsAttr(),
                    basis_curves.GetNormalsInterpolation(),
                    len(previous_points_array),
                    len(new_points_array),
                )
                if is_periodic:
                    self.open_close_curve(basis_curves)
                self._update_extent_attribute(basis_curves)

    def _displace_tangent(
        self, basis_curves: UsdGeom.BasisCurves, ids: List[int], along_tangent_dir: bool, distance: float = 0.001
    ):
        points_attr = basis_curves.GetPointsAttr()
        points = points_attr.Get()

        curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
        curve_vertex_counts = curve_vertex_counts_attr.Get()

        dirty = False
        for id in ids:
            id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)

            # cv_index is the index on the current curve in a multi-curve basisCurves prim, not necessarily index in points array
            cv_index = id - id_curve_offset
            anchor_index = find_anchor_index(cv_index)
            modify_index = anchor_index + 1 if anchor_index == 0 else anchor_index - 1

            translation = points[modify_index + id_curve_offset]
            trans_anchor = points[anchor_index + id_curve_offset]
            tangent_dir = translation - trans_anchor
            if along_tangent_dir:
                # do not normalize. Scale distance to tangent len so longer tangent can break out of tolerance
                translation += tangent_dir * distance
            else:
                len = tangent_dir.GetLength()
                translation += Gf.Vec3f(distance * len)  # move it slightly so tangent breaks. Scale it to tangent len

            dirty |= self._set_points(points, modify_index + id_curve_offset, translation)

        if dirty:
            with omni.kit.undo.group():
                self._set_value_to_attribute(points_attr.GetPath(), points)

                # update extent
                self._update_extent_attribute(basis_curves)

    def set_curve_type(self, basis_curves_list: List[UsdGeom.BasisCurves], curve_type: str):
        with omni.kit.undo.group():
            for basis_curves in basis_curves_list:
                attr = basis_curves.GetTypeAttr()
                attr_path = attr.GetPath()
                previous_value = attr.Get()
                if curve_type == "cubic":
                    omni.kit.commands.execute(
                        "ChangeProperty", prop_path=attr_path, value=UsdGeom.Tokens.cubic, prev=previous_value
                    )
                elif curve_type == "linear":
                    omni.kit.commands.execute(
                        "ChangeProperty", prop_path=attr_path, value=UsdGeom.Tokens.linear, prev=previous_value
                    )

    def _set_points(self, points: List, array_index, translation: Gf.Vec3f) -> bool:
        if points[array_index] != translation:
            points[array_index] = translation
            return True
        return False

    def _set_value_to_attribute(self, prop_path, value: List, prev=None):
        omni.kit.commands.execute("ChangeProperty", prop_path=prop_path, value=value, prev=prev)

    def _update_extent_attribute(self, basis_curves):
        extent_attr = basis_curves.GetExtentAttr()
        if extent_attr:
            bounds = UsdGeom.Boundable.ComputeExtentFromPlugins(basis_curves, Usd.TimeCode.Default())
            if bounds is not None:
                self._set_value_to_attribute(extent_attr.GetPath(), bounds)

    def _subdiv_curve(
        self, points, start_index: int, curve_start_index: int, curve_end_index: int, is_periodic: bool, t: float
    ):
        p0 = points[start_index]
        p1 = points[start_index + 1]
        p2 = points[start_index + 2]

        if is_periodic and start_index + 3 == curve_end_index:
            # wrap it around on periodic cubic bezier curve
            p3 = points[curve_start_index]
        else:
            p3 = points[start_index + 3]

        p4 = (1 - t) * p0 + t * p1
        p5 = (1 - t) * p1 + t * p2
        p6 = (1 - t) * p2 + t * p3

        p7 = (1 - t) * p4 + t * p5
        p8 = (1 - t) * p5 + t * p6

        p9 = (1 - t) * p7 + t * p8

        return [p0, p4, p7, p9, p8, p6, p3]

    # Previous curve tool created incorrect number of vertices for periodic curve. Try to fix them upon new edits
    def _fix_periodic_curve_if_needed(self, paths: List[str]):
        for path in paths:
            stage = self._context.get_stage()
            basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Get(stage, path)
            wrap = basis_curves.GetWrapAttr().Get()
            if wrap != UsdGeom.Tokens.periodic:
                continue

            curves_type = basis_curves.GetTypeAttr().Get()
            basis = basis_curves.GetBasisAttr().Get()

            curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
            curve_vertex_counts = curve_vertex_counts_attr.Get() or []

            vert_count_to_remove = []
            need_fix = False

            if curves_type == UsdGeom.Tokens.linear:
                # No need to fix linear curves?
                ...
            elif curves_type == UsdGeom.Tokens.cubic:
                if basis == UsdGeom.Tokens.bezier:
                    vstep = 3
                else:
                    vstep = 1

                for i, vert_count in enumerate(curve_vertex_counts):
                    # The expected mod is 0 per https://graphics.pixar.com/usd/dev/api/class_usd_geom_basis_curves.html
                    # If there's additional number of vertex, remove them to fix up the curve(s).
                    mod = vert_count % vstep
                    vert_count_to_remove.append(mod)
                    if mod != 0:
                        need_fix = True

            # modify the affected attributes
            if need_fix:
                carb.log_warn(f"Fixing periodic curves {path} due to incorrect number of vertices")
                points_attr = basis_curves.GetPointsAttr()
                points = points_attr.Get()

                widths_attr = basis_curves.GetWidthsAttr()
                widths = widths_attr.Get()
                widths_interpolation = basis_curves.GetWidthsInterpolation()

                normals_attr = basis_curves.GetNormalsAttr()
                normals = normals_attr.Get()
                normals_interpolation = basis_curves.GetNormalsInterpolation()

                # only fix primvars with "vertex" interpolation
                fix_widths = widths and widths_interpolation == UsdGeom.Tokens.vertex and len(widths) == len(points)
                fix_normals = normals and normals_interpolation == UsdGeom.Tokens.vertex and len(normals) == len(points)

                # TODO fix other primvars?

                new_points = []
                new_widths = []
                new_normals = []
                point_offset = 0
                for i, vert_count in enumerate(curve_vertex_counts):
                    vert_remove_count = vert_count_to_remove[i]
                    new_points += list(points[point_offset : point_offset + vert_count - vert_remove_count])

                    if fix_widths:
                        new_widths += list(widths[point_offset : point_offset + vert_count - vert_remove_count])

                    if fix_normals:
                        new_normals += list(normals[point_offset : point_offset + vert_count - vert_remove_count])

                    point_offset += vert_count
                    curve_vertex_counts[i] = vert_count - vert_remove_count

                # Sets directly. Don't go though undo since we want to force fixing the curves
                curve_vertex_counts_attr.Set(curve_vertex_counts)
                points_attr.Set(new_points)

                if fix_widths:
                    widths_attr.Set(new_widths)

                if fix_normals:
                    normals_attr.Set(new_normals)

    def on_curves_event(self, event: carb.events.IEvent):
        if event.type == int(CurvesEventType.INSERT):
            self._on_insert_cv(event)
        elif event.type == int(CurvesEventType.ADD_MULTIPLE_POINTS):
            self._on_add_points_to_curve(event)
        elif (
            event.type == int(CurvesEventType.BEGIN_ADD)
            or event.type == int(CurvesEventType.ADDING)
            or event.type == int(CurvesEventType.END_ADD)
        ):
            self._on_add_cv(event)
        elif event.type == int(CurvesEventType.BEGIN_CURVE_EDIT):
            self._fix_periodic_curve_if_needed(event.payload["paths"])
            self._update_manipulator_visibility()
            self._register_hotkeys()
        elif event.type == int(CurvesEventType.END_CURVE_EDIT):
            self._update_manipulator_visibility()
            self._unregister_hotkeys()

    def _update_manipulator_visibility(self):
        """
        Hides/Shows the prim manipulator by activating/deactivating the curve stub (empty) manipulator
        """
        from omni.kit.manipulator.selector import get_manipulator_selector

        selector = get_manipulator_selector(self._usd_context_name)
        if selector:
            selector._refresh()

    def _on_insert_cv(self, event: carb.events.IEvent):
        prim_path = event.payload["pathStr"]
        segment_start_index = event.payload["segmentStartIndex"]
        curve_index = event.payload["curveIndex"]
        t = event.payload["t"]

        stage = self._context.get_stage()
        basis_curves = UsdGeom.BasisCurves.Get(stage, prim_path)

        if not basis_curves:
            return

        self.insert_cv(basis_curves, curve_index, segment_start_index, t)

    def _on_add_cv(self, event: carb.events.IEvent):
        type = event.type
        prim_path = event.payload["pathStr"]
        pos_x = event.payload["pos_x"]
        pos_y = event.payload["pos_y"]
        pos_z = event.payload["pos_z"]

        if type == int(CurvesEventType.END_ADD):
            self._add_cv_to_new_curve = False
            self._curve_manip.set_adding_curve_to_basis_curves(self._curve_context, self._add_cv_to_new_curve)

        pos = Gf.Vec3f(pos_x, pos_y, pos_z)

        stage = self._context.get_stage()
        basis_curves = UsdGeom.BasisCurves.Get(stage, prim_path)

        self.add_cv(basis_curves, pos, type, self._add_cv_to_new_curve)

    def _on_add_points_to_curve(self, event: carb.event.IEvent):
        prim_path = event.payload["pathStr"]
        interpolate_type = event.payload["type"]
        points = event.payload["points"]

        self.add_points_to_curve(prim_path, interpolate_type, points, self._curve_modifier_pressed)

    # https://graphics.pixar.com/usd/dev/api/class_usd_geom_basis_curves.html#details
    def _validate_point_count(self, basis: str, type: str, wrap: str, point_count: int) -> bool:
        vstep = {
            UsdGeom.Tokens.bezier: 3,
            UsdGeom.Tokens.catmullRom: 1,
            UsdGeom.Tokens.bspline: 1,
        }

        if type == UsdGeom.Tokens.linear:
            if wrap == UsdGeom.Tokens.nonperiodic:
                return point_count > 2
            elif wrap == UsdGeom.Tokens.periodic:
                return point_count > 3
        elif type == UsdGeom.Tokens.cubic:
            if wrap == UsdGeom.Tokens.nonperiodic:
                return point_count >= 4 and (point_count - 4) % vstep[basis] == 0
            elif wrap == UsdGeom.Tokens.periodic:
                return point_count >= vstep[basis] and point_count % vstep[basis] == 0
            elif wrap == UsdGeom.Tokens.pinned:
                return point_count >= 2
        return False

    def _register_actions(self):
        self._del_action = self._action_registry.register_action(
            EXTENSION_NAME,
            DELETE_INSTANCE_ACTION_NAME,
            self._on_delete_action,
            display_name=DELETE_INSTANCE_ACTION_NAME,
            tag="Curve CV Editing",
        )

        self._exit_action = self._action_registry.register_action(
            EXTENSION_NAME,
            EXIT_EDIT_ACTION_NAME,
            self._on_exit_action,
            display_name=EXIT_EDIT_ACTION_NAME,
            tag="Curve CV Editing",
        )

    def _unregister_actions(self):
        if self._del_action:
            self._action_registry.deregister_action(self._del_action)
            self._del_action = None

        if self._exit_action:
            self._action_registry.deregister_action(self._exit_action)
            self._exit_action = None

    def _on_delete_action(self):
        selected_cvs = self._cv_selection.get_selected_cvs()
        to_remove = defaultdict(list)
        for basis_curves, index in selected_cvs:
            to_remove[basis_curves].append(index)
        self.delete_anchor_cvs(to_remove)

    def _on_exit_action(self):
        if self._curve_manip.get_editing_curve_paths(self._curve_context):
            omni.kit.commands.execute("DisableCurveEditing", curve_context=self._curve_context)

    # hotkey is optional
    def _register_hotkeys(self):
        try:
            from omni.kit.hotkeys.core import HotkeyFilter, KeyCombination, get_hotkey_context, get_hotkey_registry

            hotkey_registry = get_hotkey_registry()
            if not self._curve_manip.get_editing_curve_paths(self._curve_context):
                return

            get_hotkey_context().push(CURVE_CV_EDIT_CONTEXT_NAME)

            self._del_hotkey = hotkey_registry.register_hotkey(
                EXTENSION_NAME,
                KeyCombination(Key.DEL),
                EXTENSION_NAME,
                DELETE_INSTANCE_ACTION_NAME,
                HotkeyFilter(context=CURVE_CV_EDIT_CONTEXT_NAME),
            )

            self._exit_hotkey = hotkey_registry.register_hotkey(
                EXTENSION_NAME,
                KeyCombination(Key.ENTER),
                EXTENSION_NAME,
                EXIT_EDIT_ACTION_NAME,
                HotkeyFilter(context=CURVE_CV_EDIT_CONTEXT_NAME),
            )
        except ImportError:
            pass

    def _unregister_hotkeys(self):
        try:
            from omni.kit.hotkeys.core import get_hotkey_context, get_hotkey_registry

            hotkey_context = get_hotkey_context()
            if hotkey_context.get() == CURVE_CV_EDIT_CONTEXT_NAME:
                hotkey_context.pop()

            hotkey_registry = get_hotkey_registry()
            if self._del_hotkey:
                hotkey_registry.deregister_hotkey(self._del_hotkey)
                self._del_hotkey = None

            if self._exit_hotkey:
                hotkey_registry.deregister_hotkey(self._exit_hotkey)
                self._exit_hotkey = None
        except ImportError:
            pass
