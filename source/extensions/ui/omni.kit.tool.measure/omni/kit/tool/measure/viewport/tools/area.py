# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Any, Dict, List, Optional, Sequence, Tuple

from omni.ui import scene as sc
from pxr import Gf, UsdGeom

from ...common import ConstrainAxis, MeasureAxis, MeasureCreationState, MeasureMode, SnapMode, convert_area_to_units
from ...manager import MeasurementManager, ReferenceManager, StateMachine
from ...system import MeasurePayload
from ..manipulator_items import *
from ..snap.manager import MeasureSnapProviderManager
from ._scene_widget import MeasureSceneLabel
from .viewport_mode_model import ViewportModeModel

# TODO: Delauney Triangulation of the mesh


class AreaModel(ViewportModeModel):
    _mode = MeasureMode.AREA

    def __init__(self, viewport_api):
        super().__init__(viewport_api, mode=self._mode)
        self._points: MultiPositionItem = MultiPositionItem(changed_fn=self._on_points_changed)
        self._prim_paths: List[str] = []
        self._color = [0, 1, 1, 1]  # default aqua blue
        self._color_map = {
            MeasureAxis.X: [1, 0, 0, 0.125],
            MeasureAxis.Y: [0, 1, 0, 0.125],
            MeasureAxis.Z: [0, 0, 1, 0.125],
        }

        with self._label_root:
            self._constrain_xform: sc.Transform = sc.Transform()
            self._ui_scene_label: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.NONE, self._mode)
            self._ui_constrain_line: sc.Line = sc.Line([0, 0, 0], [0, 0, 0], thickness=2, visible=False)

    def reset(self):
        super().reset()
        self._root.clear()
        self._points.reset()
        self._prim_paths = []
        self._constrain_xform.clear()
        # labels
        self._ui_scene_label.visible(False)
        # state
        self.creation_state = MeasureCreationState.START_SELECTION
        self._lock_constrain_axis(False)

    def _draw_constrain_plane(self) -> None:
        placement_panel = ReferenceManager().ui_placement_panel
        if not placement_panel or placement_panel.constrain_mode == ConstrainAxis.DYNAMIC:
            return

        axis, stage_up = self._get_constrain_axis()
        if axis == MeasureAxis.NONE:
            return

        color = self._color_map[axis]

        # Because sc.Rectangle Axis is aligning perpendicular versus parallel-to, we need to flipo the Axis values for
        # X and Z to ensure the alignment is correct for the axis captured by the panel. Otherwise, retrofitting the
        # current enum to use this pattern would cause a world of hurt across the extension.
        if stage_up == MeasureAxis.Y:
            p_axis = 0 if axis == MeasureAxis.Z else (2 if axis == MeasureAxis.X else 1)
        else:
            p_axis = 1 if axis == MeasureAxis.X else (2 if axis == MeasureAxis.Z else 0)

        self._constrain_xform.clear()
        self._constrain_xform.transform = sc.Matrix44.get_translation_matrix(*self._points.value[0])
        with self._constrain_xform:
            with sc.Transform(scale_to=sc.Space.SCREEN):
                sc.Rectangle(width=1024, height=1024, color=color, axis=p_axis)

    def draw(self):
        self._color = self._get_display_color()

        self._root.clear()
        with self._root:
            # Draw the lines
            points: List[List[float]] = self._points.value
            pt_len = len(points)

            for i in range(pt_len - 1):
                j = i + 1 if i + 1 <= pt_len - 1 else 0  # Connects to the first point to complete the shape
                sc.Line(points[i], points[j], color=self._color, thickness=3)

            # draw final connecting line
            if pt_len >= 2 and points[0] != points[-1]:
                sc.Line(points[0], points[-1], color=self._color, thickness=3)

            # FIXME: When mesh drawing is easier to work with...
            # Draw the mesh -- Need to figure out how to handle concave shapes properly.
            # if pt_len >= 3:
            # TODO: When able to get feature working properly
            # pt_list, v_count, v_idx = self._calculate_delaunay(self._points.vectors)

            # sc.PolygonMesh(
            #     pt_list,  # List[List[float]]
            #     [[0,1,1,0.2]] * pt_len,
            #     v_count,  # List[int]
            #     v_idx,  # List[int]
            #     wireframe=False  # Polygons!
            # )

            # LEGACY MESH DRAWING
            # sc.PolygonMesh(
            #     points,
            #     [[0,1,1,0.2]] * pt_len,
            #     [pt_len],
            #     [i for i in range(pt_len)]
            # )

            # Draw the points
            sc.Points(points, sizes=[5] * pt_len, colors=[self._color] * pt_len)

    def _get_constrain_axis(self) -> Tuple[MeasureAxis, MeasureAxis]:
        stage_up = MeasureAxis.Y if UsdGeom.GetStageUpAxis(self._api.stage) == UsdGeom.Tokens.y else MeasureAxis.Z
        placement_panel = ReferenceManager().ui_placement_panel
        if not placement_panel or placement_panel.constrain_mode == ConstrainAxis.STAGE_UP:
            return stage_up, stage_up

        if placement_panel and placement_panel.constrain_mode == ConstrainAxis.DYNAMIC:
            return stage_up, stage_up

        return MeasureAxis(placement_panel.constrain_mode.value + 1), stage_up  # +1 offset from "NONE"

    def _lock_constrain_axis(self, value: bool) -> None:
        placement_panel = ReferenceManager().ui_placement_panel
        if placement_panel:
            placement_panel._constrain_combo.enabled = not value

    def _get_dynamic_axis_coord(self, coords: List[float]) -> List[float]:
        vec_coords = Gf.Vec3d(coords)
        vectors = self._points.vectors

        if len(vectors) <= 3:
            return coords

        start, axis, end = vectors[0], vectors[1], vectors[2]
        leg_a = (start - axis).GetNormalized()
        leg_b = (end - axis).GetNormalized()
        plane_normal = Gf.Cross(leg_a, leg_b).GetNormalized()  # Direction

        n_dot_u = Gf.Dot(plane_normal, -plane_normal)
        w = vec_coords - axis
        si = 0.0
        if n_dot_u != 0:
            si = Gf.Dot(-plane_normal, w) / n_dot_u
        out_vec = w + si * -plane_normal + axis
        return [*out_vec]

    def _get_axis_aligned_coord(self, coords: List[float]) -> Tuple[List[float], Optional[MeasureAxis]]:
        if self._points.length == 0:  # First point
            return coords, None

        # Check if constrain mode is Dynamic. If so we need to return an completely different coordinate
        # based on the surface normal. This is only valid if the Axis is Dynamic and we're in the End Selection
        placement_panel = ReferenceManager().ui_placement_panel
        if placement_panel and placement_panel.constrain_mode == ConstrainAxis.DYNAMIC:
            if self.creation_state != MeasureCreationState.END_SELECTION:  # When three points have been placed
                return coords, None
            return self._get_dynamic_axis_coord(coords), None

        first_coord: List[float] = self._points.vectors[0]
        constrain_axis, stage_up = self._get_constrain_axis()

        # Depending on the stage up axis we have a different set of
        # planes to constrain points to. Annoying but has to be done.

        if stage_up == MeasureAxis.Y:  # Stage Y-UP
            if constrain_axis == MeasureAxis.X:
                return [coords[0], coords[1], first_coord[2]], MeasureAxis.Z  # YZ
            elif constrain_axis == MeasureAxis.Y:
                return [coords[0], first_coord[1], coords[2]], MeasureAxis.Y  # XZ
            else:  # Z
                return [first_coord[0], coords[1], coords[2]], MeasureAxis.X  # XY
        else:  # Stage Z-UP
            if constrain_axis == MeasureAxis.X:
                return [coords[0], first_coord[1], coords[2]], MeasureAxis.Y  # XZ
            elif constrain_axis == MeasureAxis.Y:
                return [first_coord[0], coords[1], coords[2]], MeasureAxis.X  # YZ
            else:
                return [coords[0], coords[1], first_coord[2]], MeasureAxis.Z  # XY

    def _get_axis_aligned_indices(self) -> Tuple[int, int]:
        constrain_axis, stage_up = self._get_constrain_axis()
        y_up = stage_up == MeasureAxis.Y

        if constrain_axis == MeasureAxis.X:
            return (0, 1) if y_up else (0, 2)  # YZ / XZ
        elif constrain_axis == MeasureAxis.Y:
            return (0, 2) if y_up else (1, 2)  # XZ / YZ
        else:
            return (1, 2) if y_up else (0, 1)  # XY / YZ

    def _calculate_area(self) -> Tuple[float, str]:
        points: List[Gf.Vec3d] = []

        if self._points.vectors:
            points.append(self._points.vectors[0])
            for pt in self._points.vectors[1:]:
                if pt != points[-1]:
                    points.append(pt)

        if len(points) < 3:
            return self._value_to_unit(0.0)

        start, mid, end = points[:3]
        leg_a, leg_b = (start - mid).GetNormalized(), (end - mid).GetNormalized()
        poly_normal = Gf.Cross(leg_a, leg_b).GetNormalized()

        total = Gf.Vec3d(0, 0, 0)
        for i in range(len(points)):
            v1 = points[i]
            v2 = points[0] if i == len(points) - 1 else points[i + 1]
            product = Gf.Cross(v1, v2)
            total += product

        return self._value_to_unit(abs(Gf.Dot(total, poly_normal) * 0.5), is_area=True)

    def _update_constrain_line(self, start: List[float], end: List[float]) -> None:
        axis_colors = [0xFF5555AA, 0xFF76A371, 0xFFA07D4F]

        self._ui_constrain_line.start, self._ui_constrain_line.end = start, end

        if ReferenceManager().ui_placement_panel.constrain_mode == ConstrainAxis.DYNAMIC:
            self._ui_constrain_line.color = 0xFF6E6C6A  # grey
        else:
            constrain_axis, _ = self._get_constrain_axis()
            self._ui_constrain_line.color = axis_colors[constrain_axis.value - 1]

    def _update_scene_label(self):
        if self.creation_state != MeasureCreationState.END_SELECTION:
            return
        # Find the centroid of the points, using the List[List[float]] value.
        centroid = [sum(val) for val in zip(*self._points.value)]
        centroid = [val / self._points.length for val in centroid]

        label_text, label_unit = self._calculate_area()
        # Get label precision int
        p_int = self._get_precision_value()

        self._ui_scene_label.set_position([*centroid])
        self._ui_scene_label.text = f"{label_text:.{p_int}f}{label_unit}²"
        self._ui_scene_label.visible(True)

    def _on_points_changed(self):
        if self.creation_state not in [MeasureCreationState.INTERMEDIATE_SELECTION, MeasureCreationState.END_SELECTION]:
            return
        self.draw()
        self._update_scene_label()

    # Input Handling
    def _on_moved(self, coords: Sequence[float], result: Any):
        if self.creation_state in [
            MeasureCreationState.START_SELECTION,
            MeasureCreationState.INTERMEDIATE_SELECTION,
            MeasureCreationState.END_SELECTION,
        ]:
            # Get a snap position if available
            self._snap_data: Optional[Dict[str, Any]] = MeasureSnapProviderManager().get_snap_position(coords, result)
            # If snap data is not found, we need to be sure to update the UI
            if not self._snap_data:
                self._ui_constrain_line.visible = False
                self._set_snap_marker_position(None)
                return

            snap_type: SnapMode = self._snap_data["type"]
            snap_position: List[float] = [*self._snap_data["position"]]
            self._set_snap_marker_position(Gf.Vec3d(snap_position), snap_type)

            if self.creation_state in [MeasureCreationState.INTERMEDIATE_SELECTION, MeasureCreationState.END_SELECTION]:
                coords = self._get_axis_aligned_coord(snap_position)[0]
                # TODO: Do we draw/update a new line to show the offset?
                self._update_constrain_line(snap_position, coords)  # Update regardless, no visibility change.
                self._ui_constrain_line.visible = coords != snap_position

                self._points.update(coords, self._points.length - 1)

    def _on_clicked(self, coords: Sequence[float], mouse_button: int = 0):
        if self.creation_state in [
            MeasureCreationState.START_SELECTION,
            MeasureCreationState.INTERMEDIATE_SELECTION,
            MeasureCreationState.END_SELECTION,
        ]:
            # Capture the coords, Get Snap point [or raycast point] which may already be acquired from on_moved/drag
            if not self._snap_data:
                return

            if mouse_button == 1 and self.creation_state != MeasureCreationState.END_SELECTION:
                return

            point_coords: List[float] = self._get_axis_aligned_coord([*self._snap_data["position"]])[0]
            prim_path: str = self._snap_data["path"]

            # Assign to start/end point value, get the prim based on the selection, set next state
            if self.creation_state == MeasureCreationState.START_SELECTION:
                self.creation_state = MeasureCreationState.INTERMEDIATE_SELECTION
                self._lock_constrain_axis(True)
                self._prim_paths.append(prim_path)
                self._points.append(point_coords)
                self._points.append(point_coords)  # Overlap the second point until updated
                self._draw_constrain_plane()
                return
            elif self.creation_state == MeasureCreationState.INTERMEDIATE_SELECTION:
                self._points.update(point_coords, self._points.length - 1)
                self._prim_paths.append(prim_path)
                self._points.append(point_coords)
                if self._points.length == 4:  # Three created points and One 'interactive' point
                    self.creation_state = MeasureCreationState.END_SELECTION
                return
            elif self.creation_state == MeasureCreationState.END_SELECTION:
                if mouse_button == 1 or self._points.value[0] == point_coords:
                    if mouse_button == 1:
                        self._points.remove(self._points.length - 1)
                    else:
                        self._prim_paths.append(self._prim_paths[-1])

                    # Closing the shape manually. Don't add new points, just move to Finalize.
                    self.creation_state = MeasureCreationState.FINALIZE
                    self._ui_constrain_line.visible = False
                    self._set_snap_marker_position(None)
                else:
                    # Add another point. Continue under "END SELECTION".
                    self._points.update(point_coords, self._points.length - 1)
                    self._prim_paths.append(prim_path)
                    self._points.append(point_coords)

        if self.creation_state == MeasureCreationState.FINALIZE:
            self._on_save()
            self.reset()

    def _on_save(self):
        display_panel = ReferenceManager().ui_display_panel

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = self._prim_paths
        payload.points = MeasurePayload.world_to_local_points(self._points.vectors, payload.prim_paths)
        payload.tool_mode = MeasureMode.AREA
        payload.unit_type = display_panel.unit
        payload.precision = display_panel.precision
        payload.label_size = display_panel.text_size
        payload.label_color = display_panel.color
        MeasurementManager().create(payload)

    def _try_auto_complete_and_save(self):
        if self.creation_state == MeasureCreationState.END_SELECTION:
            self._points.remove(self._points.length - 1)
            self._set_snap_marker_position(None)
            self._on_save()
            self.reset()
