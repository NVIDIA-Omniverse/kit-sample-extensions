# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["TeleportManipulator"]

import math
from functools import lru_cache

import carb.settings
import omni.kit.viewport.utility as vp_util
import omni.ui as ui
import omni.usd
from omni.kit.viewport.utility.camera_state import ViewportCameraState as VpCamera
from omni.ui import color as cl
from omni.ui import scene as sc
from pxr import Gf, UsdGeom

from .cylinder2 import Counts, Indices, Points
from .teleport_widget import MAX_SLOPE_ANGLE_DEF, MAX_SLOPE_ANGLE_PATH, get_stage_up
from .widget_geometry import RingGeometry

POINT_COUNT = 40
SETTING_SHOW_POSITION = "exts/omni.kit.tool.teleport/showPosition"


class BeamPoint:
    def __init__(self, start, end, scale, prev_points):
        dir_vec = end - start
        len = dir_vec.GetLength()
        rotation = Gf.Rotation(Gf.Vec3d(0, 0, 1), end - start)
        self.transform = (
            Gf.Matrix4d().SetScale(Gf.Vec3d(scale, scale, len))
            * Gf.Matrix4d().SetRotate(rotation)
            * Gf.Matrix4d().SetTranslate(start)
        )
        self._prev_points = prev_points

    def get_points(self):
        new_points = [self.transform.Transform(Gf.Vec3d(point)) for point in Points]
        # return [[point[0], point[1],point[2]] for point in new_points]
        if len(self._prev_points) != len(new_points):
            return [[point[0], point[1], point[2]] for point in new_points]
        out_points = []
        for i in range(len(new_points)):
            point = self._prev_points[i + 1] if i % 2 == 0 else new_points[i]
            out_points.append(point)
        return [[point[0], point[1], point[2]] for point in out_points]


def get_ring_probe_offset(radius: float, ring_scale: float, units_scale: float) -> float:
    """Half-width, in STAGE UNITS, of the world segment used to measure the ring on screen.

    `radius` comes from the gizmo asset's extent and is authored in centimeters, so it has to be
    converted to stage units before it can be projected to pixels.
    """
    return radius * ring_scale * units_scale


def get_ring_scale(ring_scale, screen_size, radius, fixed_size, min_size, max_size) -> float:
    """Scale of the ring mesh INSIDE the sc.Space.SCREEN transform.

    `screen_size`, `min_size` and `max_size` are pixels and `radius` is asset units, so the result
    is a pixels-per-asset-unit factor. It is deliberately independent of the stage units: this
    function takes no units_scale, and must not grow one.
    """
    if fixed_size:
        return ring_scale
    if screen_size > max_size:
        return ring_scale * (max_size / radius)
    if screen_size < min_size:
        return ring_scale * (min_size / radius)
    return ring_scale * (screen_size / radius)


def get_bezier_offset(distance: float, units_scale: float = 1.0) -> float:
    """Bulge of the beam arc, in stage units, for a stage-unit `distance`."""
    # `distance ** 0.5` is not linear in the unit, so the centimeter-tuned curve has to be
    # evaluated in centimeters and its result converted back to stage units.
    distance_cm = distance / units_scale
    offset_cm = (distance_cm**0.5) / 4.0 if distance_cm < 3600 else 15
    return offset_cm * units_scale


def get_label_offset(distance: float, units_scale: float = 1.0) -> float:
    """Height of the position label above the target, in stage units."""
    # TODO: should we make it as a setting value?
    avtar_height_cm = 240
    distance_cm = distance / units_scale
    return (avtar_height_cm + distance_cm / 1000 * 50) * units_scale


def world_coord_to_screen_pos(world_position) -> Gf.Vec2f:
    if (window := ui.Workspace.get_window("Viewport")) is None:
        return Gf.Vec2f(0.0, 0.0)

    api = window.viewport_api
    ndc_coord = api.world_to_ndc.Transform(world_position)

    screen_x_ndc = (ndc_coord[0] + 1) * 0.5
    screen_y_ndc = (ndc_coord[1] + 1) * 0.5

    screen_x = screen_x_ndc * window.width
    screen_y = screen_y_ndc * window.height
    return Gf.Vec2f(screen_x, screen_y)


@lru_cache()
def get_besizer_factor(i, count):
    t = float(i) / float(count)
    m1 = 1 - t
    m2 = m1 * m1
    m3 = m2 * m1
    k1 = m3
    k2 = 3 * m2 * t
    k3 = 3 * m1 * t * t
    k4 = t * t * t
    return k1, k2, k3, k4


class Bezier4:
    def __init__(self, start: Gf.Vec3d, end: Gf.Vec3d, world_up, distance, units_scale: float = 1.0):
        d = end - start
        # Unitless fractions of the chord, so they need no conversion.
        d1 = start + d / 200.0
        d2 = start + d / 90.0
        self.p1 = start
        offset = get_bezier_offset(distance, units_scale)
        self.p2 = Gf.Vec3d(d1[0], d1[1] + offset * world_up[1], d1[2] + offset * world_up[2])
        self.p3 = Gf.Vec3d(d2[0], d2[1] + offset * world_up[1], d2[2] + offset * world_up[2])
        self.p4 = end
        self.cache = {}
        self.cache2 = {}
        # self._t = pow(0.9, 90)

    def get_point(self, i):
        cache_point = self.cache.get(i, None)
        if cache_point:
            return cache_point
        k1, k2, k3, k4 = get_besizer_factor(i, POINT_COUNT)
        s = k1 * self.p1 + k2 * self.p2 + k3 * self.p3 + k4 * self.p4
        self.cache[i] = s
        return s

    def get_point_more(self, i):
        cache_point = self.cache2.get(i, None)
        if cache_point:
            return cache_point
        k1, k2, k3, k4 = get_besizer_factor(i, POINT_COUNT * 4)
        s = k1 * self.p1 + k2 * self.p2 + k3 * self.p3 + k4 * self.p4
        self.cache2[i] = s
        return s


rect = 230


class TeleportManipulator(sc.Manipulator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pos = None
        self._gizmo = None
        self._label_len = 0
        self._label_degree = None
        self._use_mesh = True
        self._angle = 0
        self._max_slope_angle = None
        self._usd_context = omni.usd.get_context()

    def on_model_updated(self, item):
        self.invalidate()

    def on_build(self):
        if not self.model:
            return

        visible = self.model.get_as_bool(self.model.get_item("visible"))
        if visible:
            self._gizmo = sc.Transform()
            position = self.model.position
            visual_up = self.model.visual_up
            visual_front = self.model.visual_front
            distance = self.model.distance
            angle = self.model.angle
            world_up = self.model.world_up
            if not self.draw(position, visual_up, visual_front, distance, angle, world_up):
                self.update_degree(angle)

        else:
            self.clear()

    def clear(self):
        if self._gizmo:
            self._gizmo.clear()

    def update_degree(self, angle):
        if abs(self._angle - angle) < 0.0001:
            return
        self._angle = angle
        angle_str = format((angle) / 3.1415926 * 180 + 90, ".2f")
        label_text = f"Target Orient:      {angle_str} degrees"
        label_len3 = len(label_text)
        if self._label_len > label_len3:
            label_text = label_text + " " * 2 * (self._label_len - label_len3)
        if self._label_degree:
            self._label_degree.text = label_text

    def draw(self, position, visual_up, visual_front, distance, angle, world_up):
        if position:
            # if self._pos == position:
            #     return False
            self._pos = position
        if not self._pos:
            return False
        # The gizmo, beam and label sizes below are authored in centimeters: convert them to stage
        # units, and convert the stage-unit distance to centimeters for the cm-tuned formulas.
        units = self.model.units_scale
        distance_cm = distance / units
        cam_path = vp_util.get_viewport_window_camera_path()
        if not cam_path:
            return
        camera_state = VpCamera()
        try:
            pos = camera_state.position_world
            # some times couldn't get the target world correct
            # is there a bug in camera state's target_world?
            target = camera_state.target_world
        except:
            return
        # The beam starts a fixed physical offset in front of and below the camera (5cm / 2cm).
        mid_pos = pos + (target - pos).GetNormalized() * (5 * units)
        c_pos = Gf.Vec3d(mid_pos[0], mid_pos[1] - 2 * units * world_up[1], mid_pos[2] - 2 * units * world_up[2])
        vert_count = len(Indices)
        bezier4 = Bezier4(c_pos, self._pos, world_up, distance, units_scale=units)
        prev_points = []

        self._gizmo.clear()
        with self._gizmo:
            show_position = carb.settings.get_settings().get(SETTING_SHOW_POSITION)
            if show_position:
                offset = get_label_offset(distance, units)
                with sc.Transform(
                    transform=sc.Matrix44.get_translation_matrix(
                        self._pos[0], self._pos[1] + offset * world_up[1], self._pos[2] + offset * world_up[2]
                    )
                ):
                    with sc.Transform(look_at=sc.Transform.LookAt.CAMERA, scale_to=sc.Space.SCREEN):
                        self._rect = sc.Rectangle(width=rect * 3, height=rect, color=cl("#000000a0"))
                        pos = self._pos
                        font_size = 18
                        font_color = cl("#a8a8a8")
                        label_len = 50
                        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 50, 0)):
                            p0 = format(pos[0], ".2f")
                            p1 = format(pos[1], ".2f")
                            p2 = format(pos[2], ".2f")
                            label_text1 = f"Target Position:   {p0},{p1},{p2}"
                            label_len = len(label_text1)
                            self._label_len = label_len
                            sc.Label(
                                label_text1, color=font_color, alignment=ui.Alignment.CENTER_BOTTOM, size=font_size
                            )
                        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, -10, 0)):
                            dis_str = format(distance, ".2f")
                            label_text = f"Target Distance:  {dis_str}"
                            label_len2 = len(label_text)
                            if label_len > label_len2:
                                label_text = label_text + " " * 2 * (label_len - label_len2 - 3)
                            sc.Label(label_text, color=font_color, alignment=ui.Alignment.CENTER_BOTTOM, size=font_size)

                        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, -70, 0)):
                            angle_str = format((angle + 1.57) / 3.14 * 180, ".2f")
                            label_text = f"Target Orient:       {angle_str} degrees"
                            label_len3 = len(label_text)
                            if label_len > label_len3:
                                label_text = label_text + " " * 2 * (label_len - label_len3)
                            self._label_degree = sc.Label(
                                label_text, color=font_color, alignment=ui.Alignment.CENTER_BOTTOM, size=font_size
                            )

            if self.model.ring_visible:
                stage = self._usd_context.get_stage()
                up = get_stage_up(stage)
                up_axis = UsdGeom.GetStageUpAxis(stage)

                slope_angle = Gf.RadiansToDegrees(math.acos(Gf.Dot(visual_up, up)))
                visible = slope_angle <= self._get_max_slope_angle()

                if not visible:
                    visual_side = Gf.Cross(up, visual_up).GetNormalized()
                    if Gf.IsClose(visual_side, Gf.Vec3d(0), 1e-6):
                        visual_side = Gf.Vec3d().XAxis() if up_axis == UsdGeom.Tokens.y else Gf.Vec3d().YAxis()
                else:
                    visual_side = Gf.Cross(visual_up, visual_front).GetNormalized()
                    if Gf.IsClose(visual_side, Gf.Vec3d(0), 1e-6):
                        visual_side = Gf.Cross(up, visual_front).GetNormalized()
                    if Gf.IsClose(visual_side, Gf.Vec3d(0), 1e-6):
                        visual_side = Gf.Vec3d().XAxis() if up_axis == UsdGeom.Tokens.y else Gf.Vec3d().YAxis()

                visual_front = Gf.Cross(visual_side, visual_up).GetNormalized()

                rotation_mtx = sc.Matrix44(
                    visual_side[0],
                    visual_side[1],
                    visual_side[2],
                    0.0,
                    visual_up[0],
                    visual_up[1],
                    visual_up[2],
                    0.0,
                    visual_front[0],
                    visual_front[1],
                    visual_front[2],
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                ) * sc.Matrix44.get_rotation_matrix(0.0, -90.0, 0.0, True)

                geometry = RingGeometry.get_instance()

                # WORLD-space probe: geometry.radius is a centimeter-authored asset length, so it
                # must be converted to stage units before it can be projected to the screen.
                probe = get_ring_probe_offset(geometry.radius, self.model.ring_scale, units)
                screen_left = self.world_coord_to_screen_pos(self._pos - probe * visual_side)
                screen_right = self.world_coord_to_screen_pos(self._pos + probe * visual_side)
                screen_size = (screen_right - screen_left).GetLength()

                # NOTE: inside get_ring_scale, geometry.radius is NOT a world length. The mesh below
                # is drawn under sc.Transform(scale_to=sc.Space.SCREEN), so it is the asset-space
                # divisor turning a pixel size into a screen-space scale factor: leave it unconverted.
                scale = get_ring_scale(
                    self.model.ring_scale,
                    screen_size,
                    geometry.radius,
                    self.model.ring_fixed_size,
                    self.model.ring_min_size,
                    self.model.ring_max_size,
                )

                with sc.Transform(
                    transform=sc.Matrix44.get_translation_matrix(self._pos[0], self._pos[1], self._pos[2])
                ):
                    with sc.Transform(scale_to=sc.Space.SCREEN):
                        with sc.Transform(transform=sc.Matrix44.get_scale_matrix(scale, scale, scale)):
                            with sc.Transform(transform=rotation_mtx):
                                sc.PolygonMesh(
                                    geometry.points,
                                    geometry.get_colors(visible),
                                    geometry.face_vertex_counts,
                                    geometry.face_vertex_indices,
                                )

            if self.model.beam_visible and distance_cm < 200000:
                thickness = 0.06 * units
                # Dimensionless ratios: the unit propagates from the already-converted thickness.
                reduce_factor = 0.99

                def get_line_thickness(dis):  # pragma: no cover -- currently unused
                    if dis < 3000:
                        return 19
                    if dis < 6000:
                        return 21 - dis / (1100 + (dis - 8000) / 20)
                    if dis < 32000:
                        return 20 - dis / (1100 + (dis - 8000) / 20)
                    if dis < 40000:
                        return 6
                    if dis < 50000:
                        return 5
                    if dis < 70000:
                        return 4
                    if dis < 90000:
                        return 3
                    return 2

                for i in range(POINT_COUNT):
                    if i < 10:
                        for j in range(i * 4, (i + 1) * 4):
                            s = bezier4.get_point_more(j)
                            e = bezier4.get_point_more(j + 1)
                            if self._use_mesh:
                                points = BeamPoint(s, e, thickness, prev_points).get_points()
                                prev_points = points
                                # TODO: waiting OM-42395 fix then set color tranparent
                                mesh_color = cl(0.2, 0.77, 0.99, 0.1 * (j + 1))
                                sc.PolygonMesh(points, [mesh_color] * vert_count, Counts, Indices)
                            else:
                                mesh_color = cl(0.2, 0.77, 0.99, 0.05 * (j + 1))
                                sc.Line(
                                    [s[0], s[1], s[2]],
                                    [e[0], e[1], e[2]],
                                    thickness=get_line_thickness(distance_cm) / 5,
                                    color=mesh_color,
                                )

                    else:
                        s = bezier4.get_point(i)
                        e = bezier4.get_point(i + 1)
                        if self._use_mesh:
                            factor = i - 5
                            thickness = thickness / (reduce_factor - (i - 5) / 10000)
                            # TODO: waiting OM-42395 fix then set color tranparent
                            mesh_color = cl(0.2, 0.77, 0.99, 1)

                            points = BeamPoint(s, e, thickness, prev_points).get_points()
                            prev_points = points

                            sc.PolygonMesh(points, [mesh_color] * vert_count, Counts, Indices)
                        else:
                            mesh_color = cl(0.2, 0.77, 0.99, 1)
                            sc.Line(
                                [s[0], s[1], s[2]],
                                [e[0], e[1], e[2]],
                                thickness=get_line_thickness(distance_cm) / 5,
                                color=mesh_color,
                            )
        return True

    def _get_max_slope_angle(self):
        self._max_slope_angle = carb.settings.get_settings().get(MAX_SLOPE_ANGLE_PATH)
        if self._max_slope_angle is None:
            self._max_slope_angle = MAX_SLOPE_ANGLE_DEF
        return self._max_slope_angle

    def world_coord_to_screen_pos(self, world_position) -> Gf.Vec2f:
        return world_coord_to_screen_pos(world_position)
