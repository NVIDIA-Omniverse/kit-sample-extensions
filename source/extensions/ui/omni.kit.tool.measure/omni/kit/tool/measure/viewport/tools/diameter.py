# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Any, Dict, List, Optional, Sequence, Tuple

import carb.profiler
import numpy as np
from omni import ui
from omni.ui import scene as sc
from pxr import Gf, UsdGeom

from ...common import MeasureAxis, MeasureCreationState, MeasureMode, SnapMode
from ...common.utils import flatten
from ...manager import MeasurementManager, ReferenceManager
from ...system import MeasurePayload
from ..manipulator_items import PositionItem, PrimRefItem
from ..snap.manager import MeasureSnapProviderManager
from ._scene_widget import MeasureSceneLabel
from .viewport_mode_model import ViewportModeModel


class DiameterModel(ViewportModeModel):
    _mode = MeasureMode.DIAMETER

    def __init__(self, viewport_api):
        super().__init__(viewport_api, mode=self._mode)
        self._start_point: PositionItem = PositionItem()
        self._start_prim: PrimRefItem = PrimRefItem()
        self._mid_point: PositionItem = PositionItem()
        self._mid_prim: PrimRefItem = PrimRefItem()
        self._end_point: PositionItem = PositionItem()
        self._end_prim: PrimRefItem = PrimRefItem()
        self._arc_xform: Optional[sc.Transform] = None
        self._rubber_band: Optional[sc.Line] = None
        self._diameter_line: Optional[sc.Line] = None
        self._diameter_points: Optional[sc.Points] = None
        self._points: Optional[sc.Points] = None

        self._color = [0, 1, 1, 1]

        with self._label_root:
            self._ui_label: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.NONE, self._mode)

    def reset(self):
        super().reset()
        self._root.clear()
        self._arc_xform = None
        self._rubber_band = None
        self._diameter_line = None
        self._diameter_points = None
        self._points = None
        # class items
        self._start_point.value = [0, 0, 0]
        self._start_prim.update(None)
        self._mid_point.value = [0, 0, 0]
        self._mid_prim.update(None)
        self._end_point.value = [0, 0, 0]
        self._end_prim.update(None)
        # labels
        self._ui_label.visible(False)
        # state
        self.creation_state = MeasureCreationState.START_SELECTION

    @carb.profiler.profile
    def draw(self):
        # We just started, clear and create all the necessary scene elements
        if self.creation_state == MeasureCreationState.INTERMEDIATE_SELECTION:
            self._color = self._get_display_color()
            self._root.clear()
            with self._root:
                # Draw rubberband
                self._rubber_band = sc.Line(
                    self._start_point.value, self._mid_point.value, color=self._color, thickness=3
                )
                # Points
                self._points = sc.Points(
                    [self._start_point.value, self._mid_point.value, self._end_point.value],
                    sizes=[5, 5, 5],
                    colors=[self._color] * 3,
                )
        # entering end selection phase, create the Arc sc items to visualize the Arcs
        elif self.creation_state == MeasureCreationState.END_SELECTION and self._arc_xform is None:
            with self._root:
                # Hide the rubberband:
                if self._rubber_band:
                    self._rubber_band.visible = False

                # Create the arc
                self._arc_xform = sc.Transform()
                with self._arc_xform:
                    self._arc = sc.Arc(
                        radius=0,
                        axis=1,
                        thickness=2,
                        color=[1, 1, 0, 1],  # [*self._color[:3], 0.5],
                        wireframe=True,
                    )

                # Create Diameter
                self._diameter_line = sc.Line(
                    color=self._color,
                    thickness=3,
                )
                self._diameter_points = sc.Points([[0, 0, 0]] * 2, colors=[[1, 1, 1, 1]] * 2, visible=False)

        # only update the values without re-creating the ui scene items
        if self.creation_state != MeasureCreationState.FINALIZE:
            # If creation state is not finalize, we draw the three user-defined points on the arc
            self._points.positions = [self._start_point.value, self._mid_point.value, self._end_point.value]
            self._points.visible = True
        else:
            self._points.visible = False

        if self.creation_state in [MeasureCreationState.END_SELECTION, MeasureCreationState.FINALIZE]:
            start, mid, end = self._start_point.vector, self._mid_point.vector, self._end_point.vector
            center, xform_mtx = self._compute_center(start, mid, end)
            radius = (center - start).GetLength()

            # Update the arc
            if self._arc_xform:
                self._arc.radius = radius
                self._arc_xform.transform = flatten(xform_mtx)

            # Update the diameter
            if self._diameter_line and self._diameter_points:
                d_end = (center - start).GetNormalized() * (radius * 2) + start
                start_point = [start[0], start[1], start[2]]
                end_point = [d_end[0], d_end[1], d_end[2]]
                self._diameter_line.start = start_point
                self._diameter_line.end = end_point
                self._diameter_points.positions = [start_point, end_point]
                self._diameter_points.visible = True

            # Update the label
            position = center + -(Gf.Cross(start - mid, end - mid).GetNormalized() * 10)
            precision = self._get_precision_value()
            label_value, label_unit = self._value_to_unit(radius * 2)
            self._ui_label.set_position(position)
            self._ui_label.text = f"{label_value:.{precision}f} {label_unit}"
            self._ui_label.visible(True)

    def _compute_center(self, a: Gf.Vec3d, b: Gf.Vec3d, c: Gf.Vec3d) -> Tuple[Gf.Vec3d, Gf.Vec3d]:
        def line_intersect(a: Gf.Vec3d, b: Gf.Vec3d, c: Gf.Vec3d, d: Gf.Vec3d) -> Gf.Vec3d:
            # DO NOT use [*a], [*b] etc to unpack any Gf types. It is VERY slow.
            # By simply changing them to explicit unpacking ([a[0], a[1], a[2]]), this function goes down from 5ms to 0.1ms
            n_a, n_b, n_c, n_d = (
                np.array([a[0], a[1], a[2]]),
                np.array([b[0], b[1], b[2]]),
                np.array([c[0], c[1], c[2]]),
                np.array([d[0], d[1], d[2]]),
            )
            _a = np.vstack((n_b - n_a, n_d - n_c)).T
            _b = n_c - n_a
            x = np.linalg.lstsq(_a, _b, rcond=None)[0]
            _center = n_a + x[0] * (n_b - n_a)
            return Gf.Vec3d([*_center])

        mid_a = (a + b) * 0.5
        mid_b = (b + c) * 0.5
        normal = Gf.Cross(a - b, c - b)  # get the surface normal from the 'legs' of the triangle.
        bisect_a = mid_a + Gf.Cross(b - a, normal)
        bisect_b = mid_b + Gf.Cross(c - b, normal)

        center = line_intersect(mid_a, bisect_a, mid_b, bisect_b)

        # Transform Matrix
        dir_start = (a - center).GetNormalized()
        dir_end = (c - center).GetNormalized()

        up = Gf.Cross(dir_start, dir_end).GetNormalized()
        front = (dir_start + dir_end).GetNormalized()
        side = Gf.Cross(up, front).GetNormalized()
        xform_mtx = Gf.Matrix4d(1.0)
        xform_mtx.SetRow3(0, side)
        xform_mtx.SetRow3(1, up)
        xform_mtx.SetRow3(2, front)
        xform_mtx.SetTranslateOnly(center)

        return center, xform_mtx

    def _on_moved(self, coords: Sequence[float], result: Any):
        if self.creation_state not in [MeasureCreationState.NONE, MeasureCreationState.FINALIZE]:
            # Get snap if available
            self._snap_data: Optional[Dict[str, Any]] = MeasureSnapProviderManager().get_snap_position(coords, result)

            if not self._snap_data:
                self._set_snap_marker_position(None)
                return

            snap_type: SnapMode = self._snap_data["type"]
            snap_position: Gf.Vec3d = self._snap_data["position"]
            self._set_snap_marker_position(snap_position, snap_type)

            if self.creation_state == MeasureCreationState.INTERMEDIATE_SELECTION:
                self._mid_point.vector = snap_position
                self.draw()
            elif self.creation_state == MeasureCreationState.END_SELECTION:
                self._end_point.vector = snap_position
                self.draw()

    def _on_clicked(self, coords: Sequence[float], mouse_button: int = 0):
        if self.creation_state in [
            MeasureCreationState.START_SELECTION,
            MeasureCreationState.INTERMEDIATE_SELECTION,
            MeasureCreationState.END_SELECTION,
        ]:
            # Get snap if available
            if not self._snap_data:
                return

            if mouse_button != 0:
                return

            point_coords: Gf.Vec3d = self._snap_data["position"]
            prim_path: str = self._snap_data["path"]

            # Assign point values, get prim based on selection, set next state
            if self.creation_state == MeasureCreationState.START_SELECTION:
                self._start_point.vector = point_coords
                self._mid_point.vector = point_coords
                self._end_point.vector = point_coords
                self._start_prim.update(prim_path)
                self.creation_state = MeasureCreationState.INTERMEDIATE_SELECTION
                return
            elif self.creation_state == MeasureCreationState.INTERMEDIATE_SELECTION:
                if point_coords == self._start_point.vector:
                    return
                self._mid_point.vector = point_coords
                self._end_point.vector = point_coords
                self._mid_prim.update(prim_path)
                self.creation_state = MeasureCreationState.END_SELECTION
                return
            elif self.creation_state == MeasureCreationState.END_SELECTION:
                if point_coords == self._mid_point.vector:
                    return
                self._set_snap_marker_position(None)
                self._end_point.vector = point_coords
                self._end_prim.update(prim_path)
                self.creation_state = MeasureCreationState.FINALIZE

        if self.creation_state == MeasureCreationState.FINALIZE:
            self._on_save()
            self.reset()

    def _on_save(self):
        display_panel = ReferenceManager().ui_display_panel

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = [self._start_prim.path, self._mid_prim.path, self._end_prim.path]
        payload.points = MeasurePayload.world_to_local_points(
            [self._start_point.vector, self._mid_point.vector, self._end_point.vector], payload.prim_paths
        )
        payload.tool_mode = MeasureMode.DIAMETER
        payload.unit_type = display_panel.unit
        payload.precision = display_panel.precision
        payload.label_size = display_panel.text_size
        payload.label_color = display_panel.color
        MeasurementManager().create(payload)
