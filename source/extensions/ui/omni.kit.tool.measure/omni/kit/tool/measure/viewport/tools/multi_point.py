# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Any, Dict, List, Optional, Sequence, Tuple

from omni import ui
from omni.ui import scene as sc
from pxr import Gf

from ...common import LABEL_SCALE_MAPPING, MeasureAxis, MeasureCreationState, MeasureMode, SnapMode
from ...manager import MeasurementManager, ReferenceManager, StateMachine
from ...system import MeasurePayload
from ..manipulator_items import *
from ..snap.manager import MeasureSnapProviderManager
from ._scene_widget import MeasureSceneLabel
from .viewport_mode_model import ViewportModeModel


class MultiPointModel(ViewportModeModel):
    _mode = MeasureMode.MULTI_POINT

    def __init__(self, viewport_api):
        super().__init__(viewport_api, mode=self._mode)
        self._points: MultiPositionItem = MultiPositionItem(changed_fn=self._on_points_changed)
        self._prim_paths: List[str] = []
        self._color = [0, 1, 1, 1]  # default aqua blue
        self._label_map: Dict[Tuple[int, int], sc.Transform] = {}

        with self._label_root:
            self._ui_scene_label: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.NONE, self._mode)
            self._sub_label_root = sc.Transform()

    def reset(self):
        super().reset()
        self._root.clear()
        self._points.reset()
        self._prim_paths = []
        # labels
        self._ui_scene_label.visible(False)
        self._label_map.clear()
        self._sub_label_root.clear()
        # state
        self.creation_state = MeasureCreationState.START_SELECTION

    def draw(self):
        self._color = self._get_display_color()
        points: List[List[float]] = self._points.value
        pt_len = len(points)

        self._root.clear()
        with self._root:
            # Draw the lines + Labels
            for i in range(pt_len - 1):
                j = i + 1
                sc.Line(points[i], points[j], color=self._color, thickness=3)

            # Draw the points
            sc.Points(points, sizes=[5] * pt_len, colors=[self._color] * pt_len)

        self._sub_label_root.clear()
        if pt_len > 2:
            # Draw sub labels under the sub_label root
            with self._sub_label_root:
                for i in range(pt_len - 1):
                    j = i + 1
                    if pt_len > 1 and j < pt_len - 1:
                        self._draw_sub_label(points[i], points[j])

    def _draw_sub_label(self, start, end) -> sc.Transform:
        distance = (Gf.Vec3d(start) - Gf.Vec3d(end)).GetLength()
        label_position = (Gf.Vec3d(start) + Gf.Vec3d(end)) * 0.5

        # Get Label content and metadata
        label_text, label_unit = self._value_to_unit(distance)
        text_size = ReferenceManager().ui_display_panel.text_size
        size_bias = LABEL_SCALE_MAPPING[text_size]

        # Get label precision int
        p_int = self._get_precision_value()
        # Simple white label with text
        xform = sc.Transform(
            look_at=sc.Transform.LookAt.CAMERA, transform=sc.Matrix44.get_translation_matrix(*label_position)
        )
        with xform:
            with sc.Transform(scale_to=sc.Space.SCREEN):
                computed_label = f"{label_text:.{p_int}f}{label_unit}"
                sc.Label(computed_label, size=text_size.value, color=[0, 0, 0, 1], alignment=ui.Alignment.CENTER)
                rect_width = 14 * len(computed_label) * size_bias
                sc.Rectangle(width=rect_width, height=45, color=[1, 1, 1, 1], wireframe=False)

        return xform

    def _calculate_length_sum(self) -> float:
        points: List[Gf.Vec3d] = self._points.vectors
        pt_len = len(points)

        pt_sum = 0.0

        for i in range(pt_len - 1):
            j = i + 1
            pt_sum += (points[i] - points[j]).GetLength()

        return pt_sum

    def _update_scene_label(self):
        if self.creation_state not in [MeasureCreationState.INTERMEDIATE_SELECTION, MeasureCreationState.END_SELECTION]:
            return
        # Find the centroid of the points
        centroid = [sum(val) for val in zip(*self._points.value)]
        centroid = [val / self._points.length for val in centroid]

        label_dist = self._calculate_length_sum()
        label_text, label_unit = self._value_to_unit(label_dist)

        # Get label precision int
        p_int = self._get_precision_value()

        self._ui_scene_label.set_position([*centroid])
        self._ui_scene_label.text = f"{label_text:.{p_int}f}{label_unit}"
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
                self._set_snap_marker_position(None)
                return

            snap_type: SnapMode = self._snap_data["type"]
            snap_position: List[float] = [*self._snap_data["position"]]
            self._set_snap_marker_position(Gf.Vec3d(snap_position), snap_type)

            if self.creation_state in [MeasureCreationState.INTERMEDIATE_SELECTION, MeasureCreationState.END_SELECTION]:
                self._points.update(snap_position, self._points.length - 1)

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

            point_coords: List[float] = [*self._snap_data["position"]]
            prim_path: str = self._snap_data["path"]

            if self.creation_state == MeasureCreationState.START_SELECTION:
                self.creation_state = MeasureCreationState.INTERMEDIATE_SELECTION
                self._prim_paths.append(prim_path)
                self._points.append(point_coords)
                self._points.append(point_coords)  # Overlap the second point until updated
                return
            elif self.creation_state == MeasureCreationState.INTERMEDIATE_SELECTION:
                self.creation_state = MeasureCreationState.END_SELECTION
                self._points.update(point_coords, self._points.length - 1)
                self._prim_paths.append(prim_path)
                self._points.append(point_coords)
                return
            elif self.creation_state == MeasureCreationState.END_SELECTION:
                if mouse_button == 1 or self._points.value[0] == point_coords:
                    if mouse_button == 1:
                        self._points.remove(self._points.length - 1)
                    else:
                        self._prim_paths.append(self._prim_paths[-1])
                    # Closing the shape manually. Don't add new points, just move to Finalize.
                    self.creation_state = MeasureCreationState.FINALIZE
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
        payload.tool_mode = MeasureMode.MULTI_POINT
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
