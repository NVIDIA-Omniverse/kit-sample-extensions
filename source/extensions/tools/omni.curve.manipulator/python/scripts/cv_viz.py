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
import weakref
from collections import defaultdict
from typing import Callable, Set
from weakref import ProxyType

import carb
import carb.input
import omni.kit.commands
import omni.kit.undo
from omni.kit.manipulator.transform.gestures import TransformGesture
from omni.ui import color as cl
from omni.ui import scene as sc
from pxr import Gf, Sdf, Tf, Usd, UsdGeom

from .commands import ClearCvSelection
from .cv_selection import CvSelection, SelectMode
from .utils import find_anchor_index, get_array_index_offset_and_curve_index

CV_SIZE = 15
TANGENT_CV_RADIUS = 3
CV_INTERSECTION_SIZE = 15
UNSELECTED_COLOR = cl.white
UNSELECTED_TANGENT_CV_COLOR = cl("#39dcffff")
SELECTED_COLOR = cl("#ffff00ff")
TANGENT_COLOR = cl("#ffff00ff")
HOVER_COLOR = cl("#808080ff")


def flatten(transform):
    """Convert array[4][4] to array[16]"""

    # flatten the matrix by hand
    # USING LIST COMPREHENSION IS VERY SLOW (e.g. return [item for sublist in transform for item in sublist]), which takes around 10ms.
    return [
        transform[0][0],
        transform[0][1],
        transform[0][2],
        transform[0][3],
        transform[1][0],
        transform[1][1],
        transform[1][2],
        transform[1][3],
        transform[2][0],
        transform[2][1],
        transform[2][2],
        transform[2][3],
        transform[3][0],
        transform[3][1],
        transform[3][2],
        transform[3][3],
    ]


class CvClickGesture(sc.ClickGesture):
    def __init__(self, cv_viz: CvVisualizer, select_mode: SelectMode, **kwargs):
        super().__init__(**kwargs)
        self._cv_viz = cv_viz
        self._select_mode = select_mode

    def on_ended(self):
        point_id = self._choose_best_point(self.sender.gesture_payload.closest_point)
        self._cv_viz._on_point_clicked(self._select_mode, point_id)

    def _choose_best_point(self, point_id: int):
        basis_curves = self._cv_viz.basis_curves

        type_attr = basis_curves.GetTypeAttr()
        type = type_attr.Get()

        if type == UsdGeom.Tokens.linear:
            return point_id

        points_attr = basis_curves.GetPointsAttr()
        points = points_attr.Get()

        curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
        curve_vertex_counts = curve_vertex_counts_attr.Get()

        wrap = basis_curves.GetWrapAttr().Get()

        id_curve_offset, curve_index = get_array_index_offset_and_curve_index(point_id, curve_vertex_counts)

        id = point_id - id_curve_offset
        anchor_id = find_anchor_index(id)

        if anchor_id != id:
            points_count = curve_vertex_counts[curve_index]

            if wrap == UsdGeom.Tokens.periodic:
                if anchor_id == points_count:
                    anchor_id = 0

                tgt_id0 = (anchor_id - 1 + points_count) % points_count
                tgt_id1 = (anchor_id + 1) % points_count
            else:
                tgt_id0 = anchor_id - 1 if anchor_id > id_curve_offset + 1 else None
                tgt_id1 = anchor_id + 1 if anchor_id < id_curve_offset + points_count - 1 else None

            is_corner = True
            if tgt_id0 is not None:
                is_corner &= Gf.IsClose(points[anchor_id + id_curve_offset], points[tgt_id0], 1e-6)
            if is_corner and tgt_id1 is not None:
                is_corner &= Gf.IsClose(points[anchor_id + id_curve_offset], points[tgt_id1], 1e-6)

            if is_corner:
                return anchor_id + id_curve_offset

        return point_id


class CvHoverGesture(sc.HoverGesture):
    def __init__(self, cv_viz: CvVisualizer, **kwargs):
        super().__init__(**kwargs)
        self._cv_viz = cv_viz
        self._last_hovered_id = None

    def on_began(self):
        point_id = self.sender.gesture_payload.closest_point
        self._cv_viz._on_point_hover_changed(point_id, True)
        self._last_hovered_id = point_id

    def on_changed(self):
        point_id = self.sender.gesture_payload.closest_point
        if point_id != self._last_hovered_id:
            if self._last_hovered_id is not None:
                self._cv_viz._on_point_hover_changed(self._last_hovered_id, False)
            self._cv_viz._on_point_hover_changed(point_id, True)
            self._last_hovered_id = point_id

    def on_ended(self):
        if self._last_hovered_id is not None:
            self._cv_viz._on_point_hover_changed(self._last_hovered_id, False)
            self._last_hovered_id = None


class PreventViewportOthers(sc.GestureManager):
    def can_be_prevented(self, gesture):
        return True

    def should_prevent(self, gesture, preventer):
        if preventer.state == sc.GestureState.BEGAN or preventer.state == sc.GestureState.CHANGED:
            if issubclass(type(preventer), CvClickGesture):
                if issubclass(type(gesture), CvClickGesture):
                    return gesture.gesture_payload.ray_distance > preventer.gesture_payload.ray_distance
                elif isinstance(gesture, TransformGesture):
                    return False
                else:
                    return True
            else:
                return True

        return super().should_prevent(gesture, preventer)


class PreventCvOthers(sc.GestureManager):
    def can_be_prevented(self, gesture):
        return gesture.state != sc.GestureState.CHANGED

    def should_prevent(self, gesture, preventer):
        if preventer.state == sc.GestureState.BEGAN or preventer.state == sc.GestureState.CHANGED:
            if isinstance(gesture, TransformGesture):
                return False

            if isinstance(preventer, InvertSelectGesture) or isinstance(preventer, RightClickGesture):
                return True

            elif isinstance(preventer, ResetAndSelectGesture):
                return not (isinstance(gesture, InvertSelectGesture) or isinstance(gesture, RightClickGesture))

        return super().should_prevent(gesture, preventer)


class ResetAndSelectGesture(CvClickGesture):
    def __init__(self, cv_viz: CvVisualizer):
        super().__init__(cv_viz=cv_viz, select_mode=SelectMode.RESET_AND_SELECT, manager=PreventViewportOthers())


class InvertSelectGesture(CvClickGesture):
    def __init__(self, cv_viz: CvVisualizer):
        super().__init__(
            cv_viz=cv_viz,
            select_mode=SelectMode.INVERT_SELECTION,
            modifiers=carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL,
            manager=PreventCvOthers(),
        )


class RightClickGesture(CvClickGesture):
    def __init__(self, cv_viz: CvVisualizer):
        super().__init__(cv_viz=cv_viz, select_mode=SelectMode.CONTEXT_MENU, mouse_button=1, manager=PreventCvOthers())


class CvVisualizer(sc.Manipulator):
    def __init__(
        self,
        enabled: bool = True,
        basis_curves: UsdGeom.BasisCurves = None,
        selection: ProxyType[CvSelection] = None,
        on_context_menu_fn: Callable = None,
    ):
        super().__init__()

        self._enabled = enabled
        self._basis_curves = basis_curves
        self._update_has_tangent()
        self._selection = selection
        self._selection_sub = None
        self._on_context_menu_fn = on_context_menu_fn
        self._selected_ids = set()
        self._scene_points_interactable_item = None  # sc item for mouse interaction purpose
        self._scene_points_visual_items = []  # sc items for visual purpose
        self._scene_points_visual_items_transform = []  # transform item for sc items for visual purpose
        self._scene_tangent_items = defaultdict(list)
        self._selected_scene_points_visual_item_ids = set()
        self._hovered_scene_points_visual_item_ids = set()
        self._stage_listener = None
        self._xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        self._pending_object_changed_paths: Set[Sdf.Path] = set()
        self._pending_object_changed_task = None
        self._interactive_items_enabled = True

        if self._selection:
            self._selection_sub = self._selection.subscribe_to_selection_changed(self._on_selection_changed)

    def on_build(self):
        if self._basis_curves:
            self._scene_points_visual_items.clear()
            self._scene_points_visual_items_transform.clear()
            self._scene_tangent_items.clear()
            self._selected_scene_points_visual_item_ids.clear()
            self._hovered_scene_points_visual_item_ids.clear()
            self._xform_cache.Clear()
            world_xform = self._xform_cache.GetLocalToWorldTransform(self._basis_curves.GetPrim())
            points_attr = self._basis_curves.GetPointsAttr()
            points = points_attr.Get()
            wrap = self._basis_curves.GetWrapAttr().Get()
            scene_points = []

            if points:
                curve_vertex_counts_attr = self._basis_curves.GetCurveVertexCountsAttr()
                curve_vertex_counts = curve_vertex_counts_attr.Get()

                total_vertex_counts = sum(curve_vertex_counts)
                if total_vertex_counts > len(points):
                    carb.log_warn(
                        f"Not enough points data on {self._basis_curves.GetPrim().GetPath()}, unable to create curve controls"
                    )
                    return

                for point in points:
                    point = world_xform.Transform(point)
                    scene_points.append([point[0], point[1], point[2]])

                curve_index = 0
                id_curve_offset = 0

                for point_id in range(len(scene_points)):
                    if point_id >= id_curve_offset + curve_vertex_counts[curve_index]:
                        id_curve_offset += curve_vertex_counts[curve_index]
                        curve_index += 1

                    id = point_id - id_curve_offset
                    anchor_id = find_anchor_index(id) if self._has_tangent else id

                    # draw points for CVs
                    sc_transform = sc.Transform(transform=sc.Matrix44.get_translation_matrix(*scene_points[point_id]))
                    with sc_transform:
                        with sc.Transform(transform=sc.Matrix44.get_scale_matrix(1, 1, 1), scale_to=sc.Space.SCREEN):
                            with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                                if anchor_id == id:
                                    visual_item = sc.Rectangle(
                                        axis=2,
                                        width=CV_SIZE,
                                        height=CV_SIZE,
                                        color=UNSELECTED_COLOR,
                                        wireframe=True,
                                        thickness=2,
                                    )
                                    self._scene_points_visual_items.append([visual_item])
                                else:
                                    visual_item = sc.Arc(
                                        TANGENT_CV_RADIUS,
                                        tesselation=16,
                                        color=UNSELECTED_COLOR,
                                    )
                                    visual_item2 = sc.Arc(
                                        TANGENT_CV_RADIUS,
                                        tesselation=16,
                                        color=UNSELECTED_TANGENT_CV_COLOR,
                                        wireframe=True,
                                        thickness=4,
                                    )
                                    # visual_item2 at [0] to change color
                                    self._scene_points_visual_items.append([visual_item2, visual_item])
                                self._scene_points_visual_items_transform.append(sc_transform)

                # draw tangent lines
                offset = 0
                if self._has_tangent:
                    is_periodic = wrap == UsdGeom.Tokens.periodic
                    for vertex_count in curve_vertex_counts:
                        if not is_periodic:
                            # only add an empty tangent to non-periodic starting CV
                            self._scene_tangent_items[offset].append(None)
                        range_end = vertex_count - 3
                        if is_periodic:
                            range_end += 1  # the last "virtual vertex" is a repeat of the first vertex
                        for i in range(0, range_end, 3):
                            point_index = offset + i
                            # tangent cv is always the "end" on sc.Line
                            t0 = sc.Line(
                                start=scene_points[point_index], end=scene_points[point_index + 1], color=TANGENT_COLOR
                            )

                            # if this is the last tangent on the periodic bezier curve, it's anchor CV doesn't actually
                            # exists but a "virtual" repeat of the first CV
                            if is_periodic and point_index + 3 - offset >= vertex_count:
                                t1_start_index = offset
                            else:
                                t1_start_index = point_index + 3

                            t1 = sc.Line(
                                start=scene_points[t1_start_index],
                                end=scene_points[point_index + 2],
                                color=TANGENT_COLOR,
                            )
                            self._scene_tangent_items[point_index].append(t0)
                            self._scene_tangent_items[point_index + 1].append(t0)
                            self._scene_tangent_items[point_index + 2].append(t1)
                            self._scene_tangent_items[t1_start_index].append(t1)

                        if vertex_count == 2:
                            # This curve has insufficient number of vertices
                            # it can happen when adding the first two points on a new curve.
                            # draw the tangent for it, otherwise nothing will show up on screen
                            t0 = sc.Line(start=scene_points[offset], end=scene_points[offset + 1], color=TANGENT_COLOR)
                            self._scene_tangent_items[offset].append(t0)
                            self._scene_tangent_items[offset + 1].append(t0)

                        if not is_periodic and vertex_count != 2:
                            # only add an empty tangent to non-periodic ending CV
                            self._scene_tangent_items[offset + vertex_count - 1].append(None)
                        offset += vertex_count

            if not self._stage_listener:
                self._stage_listener = Tf.Notice.Register(
                    Usd.Notice.ObjectsChanged, self._on_objects_changed, self._basis_curves.GetPrim().GetStage()
                )
        else:
            scene_points = []
            if self._stage_listener:
                self._stage_listener.Revoke()
                self._stage_listener = None
        if not self._interactive_items_enabled:
            self.enable_interactive_items(False)

        self._scene_points_interactable_item = sc.Points(
            scene_points.copy(),
            colors=[UNSELECTED_COLOR],
            sizes=[0],  # interfactable item always has size of 0
            intersection_sizes=CV_INTERSECTION_SIZE,
            gestures=[
                ResetAndSelectGesture(weakref.proxy(self)),
                InvertSelectGesture(weakref.proxy(self)),
                RightClickGesture(weakref.proxy(self)),
                CvHoverGesture(weakref.proxy(self)),
            ],
            visible=self._enabled,
        )

    def _on_point_clicked(self, mode: SelectMode, id: int):
        if self._selection:
            was_selected = id in self._selected_ids

            if mode == SelectMode.RESET_AND_SELECT:
                omni.kit.commands.execute(
                    "AddCvSelection",
                    selection=self._selection,
                    basis_curves=self._basis_curves,
                    id=id,
                    clear_previous=True,
                )

            elif mode == SelectMode.INVERT_SELECTION:
                if was_selected:
                    omni.kit.commands.execute(
                        "RemoveCvSelection", selection=self._selection, basis_curves=self._basis_curves, id=id
                    )
                else:
                    omni.kit.commands.execute(
                        "AddCvSelection",
                        selection=self._selection,
                        basis_curves=self._basis_curves,
                        id=id,
                        clear_previous=False,
                    )

            elif mode == SelectMode.MERGE_SELECTION:
                if not was_selected:
                    omni.kit.commands.execute(
                        "AddCvSelection",
                        selection=self._selection,
                        basis_curves=self._basis_curves,
                        id=id,
                        clear_previous=False,
                    )

            elif mode == SelectMode.CONTEXT_MENU:
                if self._on_context_menu_fn:
                    self._on_context_menu_fn(self._basis_curves, id)

    def _on_selection_changed(self, selected_cvs):
        if self._basis_curves:
            self.selected_ids = self._selection.get_selected_ids(self._basis_curves)

    def _on_point_hover_changed(self, id: int, hovered: bool):
        if hovered:
            if id in self._selected_scene_points_visual_item_ids:
                return

            point_item = self._scene_points_visual_items[id][0]
            point_item.color = HOVER_COLOR
            self._hovered_scene_points_visual_item_ids.add(id)

        else:
            if id in self._hovered_scene_points_visual_item_ids:
                point_item = self._scene_points_visual_items[id][0]
                point_item.color = UNSELECTED_TANGENT_CV_COLOR if isinstance(point_item, sc.Arc) else UNSELECTED_COLOR
                self._hovered_scene_points_visual_item_ids.discard(id)

    @property
    def basis_curves(self) -> UsdGeom.BasisCurves:
        return self._basis_curves

    @basis_curves.setter
    def basis_curves(self, value: UsdGeom.BasisCurves):
        if self._basis_curves != value:
            self._basis_curves = value
            self._update_has_tangent()

            # will trigger on_build
            self.invalidate()

    def refresh_tangents(self):
        self._update_has_tangent()
        self.invalidate()

    def enable_interactive_items(self, value: bool):
        self._interactive_items_enabled = value
        if self._scene_points_interactable_item:
            self._scene_points_interactable_item.visible = value
        for items in self._scene_points_visual_items:
            for item in items:
                item.visible = value

    @property
    def selection(self) -> CvSelection:
        return self._selection

    @selection.setter
    def selection(self, value: CvSelection):
        if self._selection != value:
            self._selection = value
            self._selection_sub = None
            if self._selection:
                self._selection_sub = self._selection.subscribe_to_selection_changed(self._on_selection_changed)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if value != self._enabled:
            if self._scene_points_interactable_item:
                self._scene_points_interactable_item.visible = value
                if not value:
                    self._scene_points_interactable_item = None

            for items in self._scene_points_visual_items:
                for item in items:
                    item.visible = value

            for items in self._scene_tangent_items.values():
                for item in items:
                    if item is not None:
                        item.visible = value

            self._enabled = value

            if not value:
                self._basis_curves = None
                if self._stage_listener:
                    self._stage_listener.Revoke()
                    self._stage_listener = None

                if self._pending_object_changed_task is not None:
                    self._pending_object_changed_task.cancel()
                    self._pending_object_changed_task = None

    @property
    def on_context_menu_fn(self):
        return self._on_context_menu_fn

    @on_context_menu_fn.setter
    def on_context_menu_fn(self, value: Set):
        if self._on_context_menu_fn != value:
            self._on_context_menu_fn = value

    @property
    def selected_ids(self):
        return self._selected_ids

    @selected_ids.setter
    def selected_ids(self, value: Set):
        if self._selected_ids != value:
            self._refresh_selection(value)

    @carb.profiler.profile
    def _refresh_selection(self, new_selected_ids: Set):
        # clear old selected colors
        for id in self._selected_scene_points_visual_item_ids:
            if self._scene_points_visual_items:
                item = self._scene_points_visual_items[id][0]
                item.color = UNSELECTED_TANGENT_CV_COLOR if isinstance(item, sc.Arc) else UNSELECTED_COLOR

        self._selected_scene_points_visual_item_ids.clear()

        # set selected colors
        for id in new_selected_ids:
            # periodic curve may not have visual item for the repeated node, check index bound
            if self._scene_points_visual_items and id < len(self._scene_points_visual_items):
                # change point color
                point_item = self._scene_points_visual_items[id][0]
                point_item.color = SELECTED_COLOR
                self._selected_scene_points_visual_item_ids.add(id)
                self._hovered_scene_points_visual_item_ids.discard(id)

        self._selected_ids = new_selected_ids

    def _update_has_tangent(self):
        if not self.basis_curves:
            self._has_tangent = False
        else:
            self._has_tangent = (
                self._basis_curves.GetTypeAttr().Get() == UsdGeom.Tokens.cubic
                and self._basis_curves.GetBasisAttr().Get() == UsdGeom.Tokens.bezier
            )

    @carb.profiler.profile
    def _on_objects_changed(self, notice, sender):
        if not self._basis_curves or not self._scene_points_interactable_item:
            return

        for p in notice.GetResyncedPaths():
            if p.GetPrimPath() == self._basis_curves.GetPath():
                self._pending_object_changed_paths.add(p)

        for p in notice.GetChangedInfoOnlyPaths():
            if p.GetPrimPath() == self._basis_curves.GetPath():
                self._pending_object_changed_paths.add(p)

        if self._pending_object_changed_paths:
            if self._pending_object_changed_task is None or self._pending_object_changed_task.done():
                self._pending_object_changed_task = asyncio.ensure_future(self._delayed_objects_changed_handler())

    @carb.profiler.profile
    async def _delayed_objects_changed_handler(self):
        xform_cache_cleared = False
        if self.enabled:
            for p in self._pending_object_changed_paths:
                if UsdGeom.Xformable.IsTransformationAffectedByAttrNamed(p.name) or p.name == UsdGeom.Tokens.points:
                    points_attr = self._basis_curves.GetPointsAttr()
                    points = points_attr.Get()

                    if p.name != UsdGeom.Tokens.points and not xform_cache_cleared:
                        self._xform_cache.Clear()
                        xform_cache_cleared = True

                    new_size = len(points) if points else 0
                    if len(self._scene_points_interactable_item.positions) == new_size:
                        world_xform = self._xform_cache.GetLocalToWorldTransform(self._basis_curves.GetPrim())

                        scene_points = []
                        if points:
                            for point in points:
                                point = world_xform.Transform(point)
                                scene_points.append([point[0], point[1], point[2]])

                        prev_positions = self._scene_points_interactable_item.positions
                        for i in range(len(self._scene_points_visual_items_transform)):
                            if prev_positions[i] != scene_points[i]:
                                self._scene_points_visual_items_transform[i].transform = (
                                    sc.Matrix44.get_translation_matrix(*scene_points[i])
                                )

                                if self._has_tangent:
                                    tangents = self._scene_tangent_items.get(i, [])
                                    if len(tangents) == 2:
                                        # this is an anchor CV
                                        for tgt in tangents:
                                            if tgt:
                                                tgt.start = scene_points[i]
                                    elif len(tangents) == 1:
                                        # this is a tangent CV
                                        if tangents[0]:
                                            tangents[0].end = scene_points[i]
                        self._scene_points_interactable_item.positions = scene_points
                    else:
                        ClearCvSelection(selection=self._selection).do()
                        self.invalidate()
                    break
                elif (
                    p.name == UsdGeom.Tokens.basis
                    or p.name == UsdGeom.Tokens.type
                    or p.name == UsdGeom.Tokens.curveVertexCounts
                ):
                    # fully rebuild if type or basis changed
                    self.invalidate()
                    break

        self._pending_object_changed_paths.clear()
        self._pending_object_changed_task = None
