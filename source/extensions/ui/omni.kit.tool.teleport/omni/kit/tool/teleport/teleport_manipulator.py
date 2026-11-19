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
from pxr import Gf, Usd, UsdGeom

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


# The beam arc is tuned for targets up to 36m away, seen through Kit's default camera (60 degree horizontal
# field of view: tan(30) = 0.5 * horizontalAperture 20.955 / focalLength 18.147).
ARC_REFERENCE_DISTANCE_CM = 3600.0
ARC_REFERENCE_TAN_HALF_FOV = 0.5 * 20.955 / 18.147
# The beam is hidden past 2km, measured in the reference frustum (distance / get_arc_frustum_scale).
ARC_MAX_REFERENCE_DISTANCE_CM = 200000.0


def get_arc_frustum_scale(distance_cm: float, tan_half_fov: float) -> float:
    """How much larger the view frustum is at the target than the arc's reference frustum (never below 1).

    The frustum's world width at the target is 2 * distance * tan(fov / 2). Past the reference the beam is
    built for the reference frustum and then scaled about the eye by this factor. Scaling about the eye
    projects to the same image, so the arc keeps its on-screen shape when the camera zooms out.
    """
    if distance_cm <= 0.0 or tan_half_fov <= 0.0:
        return 1.0
    return max(1.0, (distance_cm * tan_half_fov) / (ARC_REFERENCE_DISTANCE_CM * ARC_REFERENCE_TAN_HALF_FOV))


BEAM_RGB = (0.2, 0.77, 0.99)
# The beam fades in over its first BEAM_FADE_SEGMENTS fine segments (of the 40 in the ribbon section),
# from BEAM_FADE_MIN_ALPHA to opaque.
BEAM_FADE_SEGMENTS = 25
BEAM_FADE_MIN_ALPHA = 0.1


def get_beam_fade_alpha(segment: int) -> float:
    """Alpha at the START of fine beam segment `segment` (the end of segment - 1).

    Smoothstep rather than linear: a linear ramp has a corner where it reaches full opacity, which the eye
    sees as an edge (Mach band). Smoothstep starts gently and meets the opaque beam with zero slope.
    """
    x = min(1.0, max(0.0, segment / BEAM_FADE_SEGMENTS))
    return BEAM_FADE_MIN_ALPHA + (1.0 - BEAM_FADE_MIN_ALPHA) * x * x * (3.0 - 2.0 * x)


def build_beam_fade_ribbon(curve_points: list, half_width: float, view_direction: Gf.Vec3d = None):
    """One camera-facing ribbon mesh along `curve_points` (eye-relative: the eye is the origin).

    `view_direction` is the fixed viewing direction of an orthographic camera; for a perspective camera
    (None) each point is viewed along the ray from the eye, which is the point itself.

    The fading start of the beam is translucent. Drawn as tube segments it showed both the front and back
    faces, and their alpha stacked differently depending on the draw order relative to the view, so orbiting
    changed it. A ribbon facing the eye is a single layer with the tube's on-screen width (the beam is flat
    colored), and one mesh through the exact curve points has no seams or overlapping segments.

    Returns (positions, colors, vertex_counts, vertex_indices) for sc.PolygonMesh. Colors are one per
    face-vertex, faded with get_beam_fade_alpha(curve point index).
    """
    last = len(curve_points) - 1
    positions = []
    previous_side = None
    for k, point in enumerate(curve_points):
        tangent = curve_points[min(k + 1, last)] - curve_points[max(k - 1, 0)]
        # The eye is the origin, so for a perspective camera `point` is also the direction from the eye.
        side = Gf.Cross(tangent, view_direction if view_direction is not None else point)
        length = side.GetLength()
        if length <= 1e-9 * max(tangent.GetLength(), 1e-12) * max(point.GetLength(), 1.0):
            # The curve heads straight along the view ray here: keep the previous side (no zero-width pinch).
            side = previous_side if previous_side is not None else Gf.Vec3d(0.0)
        else:
            side = side / length * half_width
            # The cross product flips sign where the curve's on-screen direction reverses; keep the ribbon's
            # left and right consistent so adjacent quads do not twist into bow-ties.
            if previous_side is not None and Gf.Dot(side, previous_side) < 0.0:
                side = -side
        previous_side = side
        positions.append(point + side)
        positions.append(point - side)

    vertex_counts = [4] * last
    vertex_indices = []
    colors = []
    for k in range(last):
        quad = [2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2]
        vertex_indices.extend(quad)
        colors.extend(cl(*BEAM_RGB, get_beam_fade_alpha(index // 2)) for index in quad)
    return [[p[0], p[1], p[2]] for p in positions], colors, vertex_counts, vertex_indices


def get_beam_start(eye: Gf.Vec3d, forward: Gf.Vec3d, camera_up: Gf.Vec3d, units_scale: float = 1.0) -> Gf.Vec3d:
    """Where the beam starts: 5cm in front of the eye and 2cm below it on SCREEN (the camera's up axis).

    Offsetting along the world up axis put the start at the bottom of the screen only for a level view: looking
    down, world-down is the view direction, so the start moved up the screen to its center.
    """
    return eye + forward * (5 * units_scale) - camera_up * (2 * units_scale)


def get_camera_up(camera_state, fallback: Gf.Vec3d) -> Gf.Vec3d:
    """The camera's up axis in world space, or `fallback` when there is no usable camera."""
    fallback = Gf.Vec3d(fallback[0], fallback[1], fallback[2])
    try:
        up = camera_state.usd_camera.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).TransformDir(Gf.Vec3d.YAxis())
    except Exception:  # noqa: BLE001 -- no usable camera: fall back to the world up axis
        return fallback
    length = up.GetLength()
    return up / length if length > 0.0 else fallback


def is_camera_orthographic(camera_state) -> bool:
    try:
        return camera_state.usd_camera.GetProjectionAttr().Get() == UsdGeom.Tokens.orthographic
    except Exception:  # noqa: BLE001 -- no usable camera: treat as perspective
        return False


def get_camera_tan_half_fov(camera_state) -> float:
    """tan(horizontal fov / 2) of a perspective camera, or 0.0 when unknown (orthographic, missing attributes)."""
    if is_camera_orthographic(camera_state):
        return 0.0
    try:
        camera = camera_state.usd_camera
        aperture = camera.GetHorizontalApertureAttr().Get()
        focal_length = camera.GetFocalLengthAttr().Get()
    except Exception:  # noqa: BLE001 -- no usable camera: draw the arc unscaled
        return 0.0
    if not aperture or not focal_length:
        return 0.0
    return 0.5 * float(aperture) / float(focal_length)


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
        view_forward = (target - pos).GetNormalized()
        c_pos = get_beam_start(pos, view_forward, get_camera_up(camera_state, world_up), units)
        # An orthographic camera views along one fixed direction; the fading ribbon must face it.
        ribbon_view = view_forward if is_camera_orthographic(camera_state) else None
        vert_count = len(Indices)
        # Build the beam for the arc's reference frustum, relative to the eye: the target is pulled toward the
        # eye by the frustum scale. The beam is drawn under one transform that moves it to the eye and scales it
        # back up, so its vertices stay small (float precision) and its shape is the reference arc's.
        eye = Gf.Vec3d(pos[0], pos[1], pos[2])
        frustum_scale = get_arc_frustum_scale(distance_cm, get_camera_tan_half_fov(camera_state))
        arc_target = (Gf.Vec3d(self._pos[0], self._pos[1], self._pos[2]) - eye) / frustum_scale
        bezier4 = Bezier4(c_pos - eye, arc_target, world_up, distance / frustum_scale, units_scale=units)
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

            # The 2km beam cutoff applies to the reference-frustum arc, so it scales with the frustum like the arc.
            if self.model.beam_visible and distance_cm / frustum_scale < ARC_MAX_REFERENCE_DISTANCE_CM:
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

                # One transform moves the eye-relative reference beam to the eye and scales it up to the frustum.
                eye_translation = sc.Matrix44.get_translation_matrix(eye[0], eye[1], eye[2])
                frustum_scaling = sc.Matrix44.get_scale_matrix(frustum_scale, frustum_scale, frustum_scale)
                with sc.Transform(transform=eye_translation):
                    with sc.Transform(transform=frustum_scaling):
                        for i in range(POINT_COUNT):
                            if i < 10:
                                if self._use_mesh:
                                    if i == 0:
                                        # The fading start (the 40 fine segments) is one camera-facing ribbon.
                                        fine_points = [bezier4.get_point_more(j) for j in range(10 * 4 + 1)]
                                        sc.PolygonMesh(*build_beam_fade_ribbon(fine_points, thickness, ribbon_view))
                                    continue
                                for j in range(i * 4, (i + 1) * 4):
                                    s = bezier4.get_point_more(j)
                                    e = bezier4.get_point_more(j + 1)
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
