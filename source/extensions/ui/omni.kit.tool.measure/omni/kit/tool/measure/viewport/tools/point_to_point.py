# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Any, Dict, List, Optional, Sequence

from carb import log_error
from omni import ui
from omni.ui import scene as sc
from pxr.Gf import Vec3d

from ...common import DisplayAxisSpace, MeasureAxis, MeasureCreationState, MeasureMode, SnapMode, SnapTo
from ...manager import MeasurementManager, ReferenceManager
from ...system import MeasurePayload
from ..manipulator_items import *
from ..snap.manager import MeasureSnapProviderManager
from ._scene_widget import MeasureAxisStackLabel, MeasureSceneLabel
from .viewport_mode_model import ViewportModeModel


class PointToPointModel(ViewportModeModel):
    _mode = MeasureMode.POINT_TO_POINT

    def __init__(self, viewport_api):
        super().__init__(viewport_api, mode=self._mode)
        self._start_point: PositionItem = PositionItem(changed_fn=self._on_point_changed)
        self._start_prim: PrimRefItem = PrimRefItem()
        self._end_point: PositionItem = PositionItem(changed_fn=self._on_point_changed)
        self._end_prim: PrimRefItem = PrimRefItem()

        # Metadata
        self._surface_normal: Optional[Gf.Vec3d] = None

        # Scene UI elements
        self._color = [0, 1, 1, 1]  # default to aqua blue
        self._ui_points: Optional[sc.Points] = None
        self._ui_line: Optional[sc.Line] = None

        with self._label_root:
            self._ui_scene_label: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.NONE, self._mode)
            self._ui_x_label: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.X, MeasureMode.NONE)
            self._ui_y_label: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.Y, MeasureMode.NONE)
            self._ui_z_label: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.Z, MeasureMode.NONE)
            self._ui_stack_label: MeasureAxisStackLabel = MeasureAxisStackLabel(self._mode, clicked_fn=self._on_save)
            self._ui_perpendicular: sc.Line = sc.Line(
                [0, 0, 0], [0, 0, 0], color=[1, 1, 0, 0.5], thickness=2, visible=False
            )

    def reset(self):
        super().reset()
        self._root.clear()
        self._start_point.value = [0, 0, 0]
        self._start_prim.update(None)
        self._end_point.value = [0, 0, 0]
        self._end_prim.value = None
        # labels
        self._ui_scene_label.visible(False)
        self._ui_x_label.visible(False)
        self._ui_y_label.visible(False)
        self._ui_z_label.visible(False)
        self._ui_stack_label.visible = False
        self._ui_perpendicular.visible = False
        # State
        self.creation_state = MeasureCreationState.START_SELECTION

    def draw(self):
        self._color = self._get_display_color()

        self._root.clear()
        with self._root:
            # Line
            self._ui_line = sc.Line(self._start_point.value, self._end_point.value, color=self._color, thickness=3)
            # Points
            self._ui_points = sc.Points(
                [self._start_point.value, self._end_point.value], sizes=[5, 5], colors=[self._color] * 2
            )

            if self.creation_state == MeasureCreationState.FINALIZE:
                self._draw_xyz()

    # TODO: Optimize and solely use Gf.Vec3d
    def _draw_xyz(self) -> None:
        display_axis: DisplayAxisSpace = ReferenceManager().ui_display_panel.display_axis
        if display_axis == DisplayAxisSpace.NONE:
            return

        start: Gf.Vec3d = self._start_point.vector
        end: Gf.Vec3d = self._end_point.vector

        if display_axis == DisplayAxisSpace.WORLD:
            # Calculate support line info
            x_start, x_end = Vec3d(start), Vec3d(end[0], start[1], start[2])  # [start, (end.x, start.y, start.z)]
            y_start, y_end = x_end, Vec3d(end[0], end[1], start[2])  # [x_end, (end.x, end.y, start.z)]
            z_start, z_end = y_end, Vec3d(end)
        else:
            if not self._start_prim.prim:
                log_error("Measurement created could not provide primitive to base local coordinates from")
                return

            # Get the first prim's local quaternion rotation
            rot_matrix = self._start_prim.local_xform.ExtractRotationMatrix()  # Use this for unit vectors
            x_vec, y_vec, z_vec = (rot_matrix.GetRow(i) for i in range(3))

            yellow = start - end
            x_len = Gf.Dot(yellow, x_vec)
            y_len = Gf.Dot(yellow, y_vec)

            x_start, x_end = Vec3d(start), (x_vec * -x_len) + start
            y_start, y_end = x_end, (y_vec * -y_len) + x_end
            z_start, z_end = y_end, Vec3d(end)

        # Calculate support line distances
        x_dist = (x_start - x_end).GetLength()
        y_dist = (y_start - y_end).GetLength()
        z_dist = (z_start - z_end).GetLength()

        # Calculate label position(s)
        x_label = (x_start + x_end) * 0.5
        y_label = (y_start + y_end) * 0.5
        z_label = (z_start + z_end) * 0.5

        # Get label precision int
        p_int = self._get_precision_value()

        # Calculate stacked positions
        _stacked: bool = True
        if _stacked:
            centroid = (start + end + y_start) * 0.333
            self._ui_stack_label.set_position(centroid + Gf.Vec3d(0, 75, 0))
            m_txt, m_unit = self._value_to_unit((start - end).GetLength())
            x_txt, x_unit = self._value_to_unit(x_dist)
            y_txt, y_unit = self._value_to_unit(y_dist)
            z_txt, z_unit = self._value_to_unit(z_dist)

            self._ui_stack_label.update_text(
                main=f"{m_txt:.{p_int}f}{m_unit}",
                x=f"{x_txt:.{p_int}f}{x_unit}",
                y=f"{y_txt:.{p_int}f}{y_unit}",
                z=f"{z_txt:.{p_int}f}{z_unit}",
            )
            self._ui_scene_label.visible(False)
            self._ui_stack_label.visible = True

        if x_dist != 0:
            x_line = sc.Line([*x_start], [*x_end], color=ui.color("#AA5555"), thickness=3)  # start point to end point X
            # x_txt, x_unit = self._value_to_unit(x_dist)
            # self._ui_x_label.update(text=f"{x_txt:.{p_int}f}{x_unit}", position=[*x_label], visible=True)
        if y_dist != 0:
            y_line = sc.Line(
                [*y_start], [*y_end], color=ui.color("#71A376"), thickness=3
            )  # x_line X END to end point Y
            # y_txt, y_unit = self._value_to_unit(y_dist)
            # self._ui_y_label.update(text=f"{y_txt:.{p_int}f}{y_unit}", position=[*y_label], visible=True)
        if z_dist != 0:
            z_line = sc.Line([*z_start], [*z_end], color=ui.color("#4F7DA0"), thickness=3)  # y_line Z to end point
            # z_txt, z_unit = self._value_to_unit(z_dist)
            # self._ui_z_label.update(text=f"{z_txt:.{p_int}f}{z_unit}", position=[*z_label], visible=True)

    def _draw_surface_normal(self) -> Gf.Vec3d:
        start, end = self._start_point.vector, self._end_point.vector
        proj_length = 100  # Default

        if self.creation_state == MeasureCreationState.START_SELECTION:
            projection = (self._surface_normal * -proj_length) + start
        else:
            proj_length = Gf.Dot(start - end, self._surface_normal)
            projection = (self._surface_normal * -proj_length) + start

        self._ui_perpendicular.start = [*start]
        self._ui_perpendicular.end = [*projection]
        self._ui_perpendicular.visible = True
        return projection

    def _update_scene_label(self, visible: bool = True):
        if self.creation_state != MeasureCreationState.END_SELECTION:
            return

        # Check if we're using the perpendicular mode or not. Must align label to correct distance
        if ReferenceManager().ui_placement_panel.snap_to == SnapTo.CUSTOM:  # Normal mode
            label_pos = (self._start_point.vector + self._end_point.vector) * 0.5
            label_dist = (self._start_point.vector - self._end_point.vector).GetLength()
        else:
            label_pos = (Gf.Vec3d(*self._ui_perpendicular.start) + Gf.Vec3d(*self._ui_perpendicular.end)) * 0.5
            label_dist = (Gf.Vec3d(*self._ui_perpendicular.start) - Gf.Vec3d(*self._ui_perpendicular.end)).GetLength()
        label_text, label_unit = self._value_to_unit(label_dist)

        # Get label precision int
        p_int = self._get_precision_value()

        self._ui_scene_label.set_position(label_pos)
        self._ui_scene_label.text = f"{label_text:.{p_int}f}{label_unit}"

        self._ui_scene_label.visible(visible)

    def _on_point_changed(self):
        if not self._ui_line or not self._ui_points:
            return

        self._ui_line.start = self._start_point.value
        self._ui_line.end = self._end_point.value
        self._ui_points.positions = [self._start_point.value, self._end_point.value]

        self._update_scene_label(self._start_point.value != self._end_point.value)

    # Input Handling
    def _on_moved(self, coords: Sequence[float], result: Any):
        if self.creation_state in [MeasureCreationState.START_SELECTION, MeasureCreationState.END_SELECTION]:
            # Get a snap position if available
            self._snap_data: Optional[Dict[str, Any]] = MeasureSnapProviderManager().get_snap_position(coords, result)

            # If snap data is not found, we need to be sure to update the UI
            if not self._snap_data:
                self._set_snap_marker_position(None)
                if self.creation_state == MeasureCreationState.END_SELECTION:
                    self._end_point.value = self._start_point.value  # Overlap points for 'null' or no-snap-to state
                return

            # TODO: Really should convert List[float] to Gf.Vec3d
            # Set snap marker to new position
            snap_type: SnapMode = self._snap_data["type"]
            snap_position: List[float] = [*self._snap_data["position"]]

            # If we are in END_SELECTION, we need to update the rubber band line via setting hte endpoint.
            if self.creation_state == MeasureCreationState.END_SELECTION:
                self._end_point.value = snap_position

                # Determine if we're using perpendicular mode or not
                if ReferenceManager().ui_placement_panel.snap_to == SnapTo.PERPENDICULAR:
                    snap_position = [*self._draw_surface_normal()]

            self._set_snap_marker_position(Gf.Vec3d(*snap_position), snap_type)

    def _on_clicked(self, coords: Sequence[float], mouse_button: int = 0):
        if self.creation_state in [MeasureCreationState.START_SELECTION, MeasureCreationState.END_SELECTION]:
            # Capture the coords, Get Snap point [or raycast point] which may already be acquired from on_moved/drag
            if not self._snap_data:
                return
            if mouse_button != 0:
                self.reset()
                return
            point_coords: List[float] = [*self._snap_data["position"]]
            prim_path: str = self._snap_data["path"]
            snap_type: SnapMode = self._snap_data["type"]

            # Assign to start/end point value, get the prim based on the selection, set next state
            if self.creation_state == MeasureCreationState.START_SELECTION:
                self.creation_state = MeasureCreationState.END_SELECTION
                self._start_point.value = point_coords
                self._end_point.value = point_coords  # Overlap the second point until updated
                self._start_prim.update(prim_path)
                # Checking for the perpendicular state
                if ReferenceManager().ui_placement_panel.snap_to == SnapTo.PERPENDICULAR:
                    self._surface_normal = self._snap_data["normal"]
                    self._draw_surface_normal()
                return
            elif self.creation_state == MeasureCreationState.END_SELECTION:
                self.creation_state = MeasureCreationState.FINALIZE
                # Checking for perpendicular state and setting the correct position
                if ReferenceManager().ui_placement_panel.snap_to == SnapTo.PERPENDICULAR:
                    self._end_point.value = [*self._draw_surface_normal()]
                else:
                    self._end_point.value = point_coords

                self._set_snap_marker_position(None)
                self._end_prim.update(prim_path)
                self._ui_line.color = [1, 1, 0, 1]  # Yellow for selection

        if self.creation_state == MeasureCreationState.FINALIZE:
            # Unsure what to do at this point being that the user will be selecting/deslecting items
            # in the viewport without confirmation of 'finalizing' in a generic way.
            # TODO: move -> saving each measurement now(for testing)
            self._on_save()
            self.reset()

    def _on_save(self):
        display_panel = ReferenceManager().ui_display_panel

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = [self._start_prim.path, self._end_prim.path]
        payload.points = MeasurePayload.world_to_local_points(
            [self._start_point.vector, self._end_point.vector], payload.prim_paths
        )
        payload.tool_mode = MeasureMode.POINT_TO_POINT
        payload.axis_display = display_panel.display_axis
        payload.unit_type = display_panel.unit
        payload.precision = display_panel.precision
        payload.label_size = display_panel.text_size
        payload.label_color = display_panel.color
        MeasurementManager().create(payload)
