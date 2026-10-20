# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from math import acos, pi
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from omni import ui
from omni.ui import scene as sc
from pxr import Gf, UsdGeom

from ...common import LABEL_SCALE_MAPPING, MeasureAxis, MeasureCreationState, MeasureMode, SnapMode
from ...common.utils import flatten
from ...interface.style import get_icon_path
from ...manager import MeasurementManager, ReferenceManager
from ...system import MeasurePayload
from ..manipulator_items import *
from ..snap.manager import MeasureSnapProviderManager
from ._scene_widget import MeasureSceneLabel
from .viewport_mode_model import ViewportModeModel


# AngleModel: TODO: Move Angle drawing to its own class object to handle compute
# so the AngleModel class isn't _obtuse_ with math-based code
class AngleModel(ViewportModeModel):
    _mode = MeasureMode.ANGLE

    def __init__(self, viewport_api):
        super().__init__(viewport_api, mode=self._mode)
        self._start_point: PositionItem = PositionItem(changed_fn=self._on_point_changed)
        self._start_prim: PrimRefItem = PrimRefItem()
        self._axis_point: PositionItem = PositionItem(changed_fn=self._on_point_changed)
        self._axis_prim: PrimRefItem = PrimRefItem()
        self._end_point: PositionItem = PositionItem(changed_fn=self._on_point_changed)
        self._end_prim: PrimRefItem = PrimRefItem()

        # Scene UI Elements
        self._color = [0, 1, 1, 1]  # default aqua blue
        self._ui_points: Optional[sc.Points] = None
        self._ui_seg_a: Optional[sc.Line] = None
        self._ui_seg_b: Optional[sc.Line] = None
        self._label_root_xform: Optional[sc.Transform] = None
        self._label_text_xform_primary: Optional[sc.Transform] = None
        self._label_text_xform_secondary: Optional[sc.Transform] = None
        self._label_icon_xform_primary: Optional[sc.Transform] = None
        self._label_icon_xform_secondary: Optional[sc.Transform] = None
        self._label_rect: Optional[sc.Rectangle] = None
        self._arc_xform: Optional[sc.Transform] = None
        self._acute_arc: Optional[sc.Arc] = None
        self._obtuse_arc: Optional[sc.Arc] = None

        with self._label_root:
            self._ui_scene_label_acute: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.NONE, self._mode)
            self._ui_scene_label_obtuse: MeasureSceneLabel = MeasureSceneLabel("", MeasureAxis.NONE, self._mode)

    def reset(self):
        super().reset()
        self._ui_points = None
        self._ui_seg_a = None
        self._ui_seg_b = None
        self._label_root_xform = None
        self._label_text_xform_primary = None
        self._label_text_xform_secondary = None
        self._label_icon_xform_primary = None
        self._label_icon_xform_secondary = None
        self._label_rect = None
        self._arc_xform = None
        self._acute_arc = None
        self._obtuse_arc = None
        self._root.clear()
        # class items
        self._start_point.value = [0, 0, 0]
        self._start_prim.update(None)
        self._axis_point.value = [0, 0, 0]
        self._axis_prim.update(None)
        self._end_point.value = [0, 0, 0]
        self._end_prim.update(None)
        # labels
        self._ui_scene_label_acute.visible(False)
        self._ui_scene_label_obtuse.visible(False)
        # state
        self.creation_state = MeasureCreationState.START_SELECTION

    def draw(self):
        self._color = self._get_display_color()

        # We just started, clear and create all the necessary scene elements
        if self.creation_state == MeasureCreationState.INTERMEDIATE_SELECTION:
            self._root.clear()
            with self._root:
                # Segment A (Leg A)
                self._ui_seg_a = sc.Line(
                    self._start_point.value, self._axis_point.value, color=self._color, thickness=3
                )
                # Segment B (Leg B)
                self._ui_seg_b = sc.Line(self._axis_point.value, self._end_point.value, color=self._color, thickness=3)
                # Points
                self._ui_points = sc.Points(
                    [self._start_point.value, self._axis_point.value, self._end_point.value],
                    sizes=[5, 5, 5],
                    colors=[self._color] * 3,
                )

        # Arcs
        # entering end selection phase, create the Arc sc items to visualize the Arcs
        elif self.creation_state == MeasureCreationState.END_SELECTION and self._arc_xform is None:
            with self._root:
                self._arc_xform = sc.Transform()
                with self._arc_xform:
                    self._acute_arc = sc.Arc(
                        radius=80,
                        axis=1,
                        thickness=2,
                        color=ui.color.white,
                        wireframe=True,
                        sector=False,
                    )

                    self._obtuse_arc = sc.Arc(
                        radius=50,
                        axis=1,
                        thickness=2,
                        color=ui.color.red,
                        wireframe=True,
                        sector=False,
                    )

                start, mid, end = self._start_point.vector, self._axis_point.vector, self._end_point.vector
                self._update_arcs(start, mid, end)
                self._create_label()
        else:
            # only update the values without re-creating the ui scene items
            # Segment A (Leg A)
            self._ui_seg_a.start = self._start_point.value
            self._ui_seg_a.end = self._axis_point.value

            # Segment B (Leg B)
            self._ui_seg_b.start = self._axis_point.value
            self._ui_seg_b.end = self._end_point.value

            # Points
            self._ui_points.positions = [self._start_point.value, self._axis_point.value, self._end_point.value]

            if self.creation_state in [MeasureCreationState.END_SELECTION, MeasureCreationState.FINALIZE]:
                start, mid, end = self._start_point.vector, self._axis_point.vector, self._end_point.vector
                self._update_arcs(start, mid, end)
                self._update_labels(Gf.RadiansToDegrees(self._acute_arc.end * 2))

    def _calculate_arc_matrix_and_angle(
        self, start: Gf.Vec3d, mid: Gf.Vec3d, end: Gf.Vec3d
    ) -> tuple[Gf.Matrix4d | None, float | None]:
        dir_start = (start - mid).GetNormalized()
        dir_end = (end - mid).GetNormalized()

        dot = dir_start * dir_end
        try:
            angle = acos(dot)
        except ValueError:
            return None, None

        up = Gf.Cross(dir_start, dir_end).GetNormalized()
        front = (dir_start + dir_end).GetNormalized()
        side = Gf.Cross(up, front).GetNormalized()
        xform_mtx = Gf.Matrix4d(1.0)
        xform_mtx.SetRow3(0, side)
        xform_mtx.SetRow3(1, up)
        xform_mtx.SetRow3(2, front)
        xform_mtx.SetTranslateOnly(mid)

        return xform_mtx, angle

    def _calculate_angle(self, start: Gf.Vec3d, axis: Gf.Vec3d, end: Gf.Vec3d) -> float:
        vec_a = Gf.Vec3d(start[0] - axis[0], start[1] - axis[1], start[2] - axis[2])
        vec_b = Gf.Vec3d(end[0] - axis[0], end[1] - axis[1], end[2] - axis[2])

        try:
            vec_a_mag = Gf.Sqrt(vec_a[0] * vec_a[0] + vec_a[1] * vec_a[1] + vec_a[2] * vec_a[2])
            vec_a_norm = [vec_a[0] / vec_a_mag, vec_a[1] / vec_a_mag, vec_a[2] / vec_a_mag]

            vec_b_mag = Gf.Sqrt(vec_b[0] * vec_b[0] + vec_b[1] * vec_b[1] + vec_b[2] * vec_b[2])
            vec_b_norm = [vec_b[0] / vec_b_mag, vec_b[1] / vec_b_mag, vec_b[2] / vec_b_mag]
        except ZeroDivisionError:
            return 0.0

        res = vec_a_norm[0] * vec_b_norm[0] + vec_a_norm[1] * vec_b_norm[1] + vec_a_norm[2] * vec_b_norm[2]

        try:
            angle_rad = acos(res)
        except ValueError:
            angle_rad = 0.0

        return angle_rad * 57.2957795131  # 180.0/π

    def _calculate_angle_rotation(self, start: Gf.Vec3d, axis: Gf.Vec3d, end: Gf.Vec3d) -> Gf.Vec3d:
        up_vector = [0, 1, 0] if UsdGeom.GetStageUpAxis(self._api.stage) == UsdGeom.Tokens.y else [0, 0, 1]

        # Get the normailzed unit vectors of each leg of the angle from point to axis
        leg_a = (start - axis).GetNormalized()
        leg_b = (end - axis).GetNormalized()

        # get the normalized direction unit vector
        # We need to find a constant distance to pull a point from so distances are equal along the vector
        leg_a_pt = Gf.Vec3d([*((leg_a * 100) + axis)])
        leg_b_pt = Gf.Vec3d([*((leg_b * 100) + axis)])

        leg_a = (leg_a_pt - axis).GetNormalized()
        leg_b = (leg_b_pt - axis).GetNormalized()

        # Get the normalized surface normal vector
        surface_normal = Gf.Cross(leg_a, leg_b).GetNormalized()
        rotation: Gf.Rotation = Gf.Rotation(up_vector, surface_normal)
        quaternion: Gf.Quaternion = rotation.GetQuaternion()

        w = quaternion.GetReal()
        x, y, z = [*Gf.Vec3d(quaternion.GetImaginary())]

        # Convert Quat to Euler Vectorized
        y_sqr = y * y

        t0 = 2.0 * (w * x + y * z)
        t1 = 1.0 - 2.0 * (x * x + y_sqr)
        roll = np.arctan2(t0, t1)

        t2 = 2.0 * (w * y - z * x)
        pitch = -1 * np.arcsin(t2)

        t3 = 2.0 * (w * z + x * y)
        t4 = 1.0 - 2.0 * (y_sqr + z * z)
        yaw = np.arctan2(t3, t4)

        return Gf.Vec3d(roll, pitch, yaw)

    def _get_label_pos(self) -> Gf.Vec3d:
        return self._axis_point.vector + Gf.Vec3d(0, 22.5, 0)

    def _create_label(self) -> None:
        if self.creation_state not in [MeasureCreationState.END_SELECTION, MeasureCreationState.FINALIZE]:
            return

        start, axis, end = self._start_point.vector, self._axis_point.vector, self._end_point.vector

        label_angle = self._calculate_angle(start, axis, end)
        self._label_root_xform = sc.Transform(look_at=sc.Transform.LookAt.CAMERA, visible=False)

        with self._label_root_xform:
            with sc.Transform(scale_to=sc.Space.SCREEN):
                # Primary Value Label
                self._label_text_xform_primary = sc.Transform()
                with self._label_text_xform_primary:
                    self._acute_label = sc.Label("", color=[0, 0, 0, 1], alignment=ui.Alignment.LEFT_CENTER)
                # Secondary Label
                self._label_text_xform_secondary = sc.Transform()
                with self._label_text_xform_secondary:
                    self._obstus_label = sc.Label("", color=[0, 0, 0, 1], alignment=ui.Alignment.LEFT_CENTER)
                # Background
                self._label_rect = sc.Rectangle(height=90, color=[1, 1, 1, 1], wireframe=False)

                icon_path = get_icon_path(f"tool_angle")
                # Primary Icon
                self._label_icon_xform_primary = sc.Transform()
                with self._label_icon_xform_primary:
                    sc.Rectangle(width=45, height=45, color=[0, 0, 0, 1], wireframe=False)
                    # Icon Image
                    self._tool_image = sc.Image(source_url=icon_path, width=45, height=45)
                # Secondary Icon
                self._label_icon_xform_secondary = sc.Transform()
                with self._label_icon_xform_secondary:
                    sc.Rectangle(width=45, height=45, color=[0, 0, 0, 1], wireframe=False)
                    # Icon Image
                    self._tool_image = sc.Image(source_url=icon_path, width=45, height=45, color=ui.color.red)

        self._update_labels(label_angle)
        self._label_root_xform.visible = True

    def _update_labels(self, acute_angle: float):
        label_pos = self._get_label_pos()
        self._label_root_xform.transform = sc.Matrix44.get_translation_matrix(label_pos[0], label_pos[1], label_pos[2])
        label_angle = acute_angle
        label_inverse_angle = 360 - label_angle

        # Get label precision int
        display_panel = ReferenceManager().ui_display_panel
        p_int = self._get_precision_value()
        acute_label = f"{label_angle:.{p_int}f}°"
        obtuse_label = f"{label_inverse_angle:.{p_int}f}°"
        text_size = display_panel.text_size
        size_bias = LABEL_SCALE_MAPPING[text_size]

        char_len = max(len(acute_label) - 3, len(obtuse_label) - 3)
        rect_width = int((45 * 1.5 * size_bias) + (10 * char_len))

        self._acute_label.text = acute_label
        self._acute_label.size = text_size.value
        self._obstus_label.text = obtuse_label
        self._obstus_label.size = text_size.value

        self._label_text_xform_primary.transform = sc.Matrix44.get_translation_matrix(
            (rect_width * -0.5) + 22.5, 22.5, 0
        )
        self._label_text_xform_secondary.transform = sc.Matrix44.get_translation_matrix(
            (rect_width * -0.5) + 22.5, -22.5, 0
        )
        self._label_rect.width = rect_width
        self._label_icon_xform_primary.transform = sc.Matrix44.get_translation_matrix(
            (rect_width * -0.5) - 22.5, 22.5, 0
        )
        self._label_icon_xform_secondary.transform = sc.Matrix44.get_translation_matrix(
            (rect_width * -0.5) - 22.5, -22.5, 0
        )

    def _update_arcs(self, start: Gf.Vec3d, mid: Gf.Vec3d, end: Gf.Vec3d):
        mtx, angle = self._calculate_arc_matrix_and_angle(start, mid, end)
        if mtx is not None and angle is not None:
            self._arc_xform.transform = flatten(mtx)

            self._acute_arc.begin = -angle / 2
            self._acute_arc.end = angle / 2
            self._obtuse_arc.begin = -angle / 2
            self._obtuse_arc.end = angle / 2 - 2 * pi

    def _on_point_changed(self):
        if not self._ui_points:
            return

        self._ui_seg_a.start, self._ui_seg_a.end = self._start_point.value, self._axis_point.value
        self._ui_seg_b.start, self._ui_seg_b.end = self._axis_point.value, self._end_point.value

        self._ui_points.positions = [self._start_point.value, self._axis_point.value, self._end_point.value]

        # self._update_scene_label()

    # Input Handling
    def _on_moved(self, coords: Sequence[float], result: Any):
        if self.creation_state in [
            MeasureCreationState.START_SELECTION,
            MeasureCreationState.INTERMEDIATE_SELECTION,
            MeasureCreationState.END_SELECTION,
        ]:
            # Get snap if available
            self._snap_data: Optional[Dict[str, Any]] = MeasureSnapProviderManager().get_snap_position(coords, result)

            if not self._snap_data:
                self._set_snap_marker_position(None)
                return

            snap_type: SnapMode = self._snap_data["type"]
            snap_position: List[float] = [*self._snap_data["position"]]
            self._set_snap_marker_position(Gf.Vec3d(snap_position), snap_type)

            if self.creation_state == MeasureCreationState.INTERMEDIATE_SELECTION:
                self._axis_point.value = snap_position
            elif self.creation_state == MeasureCreationState.END_SELECTION:
                self._end_point.value = snap_position
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

            point_coords: List[float] = [*self._snap_data["position"]]
            prim_path: str = self._snap_data["path"]

            # Assign to start/axis/end point value, get the prim based on the selection, set next state
            if self.creation_state == MeasureCreationState.START_SELECTION:
                self.creation_state = MeasureCreationState.INTERMEDIATE_SELECTION
                self._start_point.value = point_coords
                self._axis_point.value = point_coords
                self._end_point.value = point_coords
                self._start_prim.update(prim_path)
                return
            elif self.creation_state == MeasureCreationState.INTERMEDIATE_SELECTION:
                if point_coords == self._start_point.value:
                    return
                self.creation_state = MeasureCreationState.END_SELECTION
                self._axis_point.value = point_coords
                self._end_point.value = point_coords
                self._axis_prim.update(prim_path)
                return
            elif self.creation_state == MeasureCreationState.END_SELECTION:
                if point_coords == self._axis_point.value:
                    return
                self.creation_state = MeasureCreationState.FINALIZE
                self._set_snap_marker_position(None)
                self._end_point.value = point_coords
                self._end_prim.update(prim_path)
                self._ui_seg_a.color = [1, 1, 0, 1]
                self._ui_seg_b.color = [1, 1, 0, 1]

        if self.creation_state == MeasureCreationState.FINALIZE:
            # TODO: move -> saving each measurement now(for testing)
            self._on_save()
            self.reset()

    def _on_save(self):
        display_panel = ReferenceManager().ui_display_panel

        payload: MeasurePayload = MeasurePayload()
        payload.prim_paths = [self._start_prim.path, self._axis_prim.path, self._end_prim.path]
        payload.points = MeasurePayload.world_to_local_points(
            [self._start_point.vector, self._axis_point.vector, self._end_point.vector], payload.prim_paths
        )
        payload.tool_mode = MeasureMode.ANGLE
        payload.unit_type = display_panel.unit
        payload.precision = display_panel.precision
        payload.label_size = display_panel.text_size
        payload.label_color = display_panel.color
        MeasurementManager().create(payload)
