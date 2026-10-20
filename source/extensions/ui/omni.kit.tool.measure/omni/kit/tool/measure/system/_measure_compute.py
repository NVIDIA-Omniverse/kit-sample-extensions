# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = [
    "ComputeOutput",
    "MeasureCompute",
    "PointToPointCompute",
    "MultiPointCompute",
    "AngleCompute",
    "AreaCompute",
    "DiameterCompute",
    "SelectedCompute",
    "COMPUTE_MAP",
]

from abc import abstractmethod
from dataclasses import dataclass
from math import acos
from typing import Dict, List, Optional

import carb
import numpy as np
import omni.usd
import warp as wp
from omni.usd import get_context
from pxr import Gf, Sdf, Usd, UsdGeom

from ..common import (
    DisplayAxisSpace,
    MeasureMode,
    convert_area_to_units,
    convert_distance_and_units,
    find_valid_ancestor,
)
from ._measure_payload import MeasurePayload
from ._models import PointPrimRelationshipModel


@dataclass
class ComputeOutput:
    points: List[Gf.Vec3d]
    primary: float
    secondary: List[float]


class MeasureCompute:
    def __init__(self):
        self._ctx = get_context()
        self._point_models: List[PointPrimRelationshipModel] = []

    @abstractmethod
    def execute(self, payload: MeasurePayload) -> Optional[ComputeOutput]:
        raise NotImplementedError


class PointToPointCompute(MeasureCompute):
    def __init__(self):
        super().__init__()

    def execute(self, payload: MeasurePayload) -> Optional[ComputeOutput]:
        if len(payload.prim_paths) != len(payload.points):
            return None

        if len(self._point_models) == 0:
            # Create the PointPrimRelationship
            self._point_models.append(PointPrimRelationshipModel(payload.points[0], payload.prim, 0))
            self._point_models.append(PointPrimRelationshipModel(payload.points[1], payload.prim, 1))

        computed_points = [model.computed_point for model in self._point_models]
        distance = (computed_points[0] - computed_points[1]).GetLength()
        out_distance = convert_distance_and_units(distance, payload.unit_type.value)[0]

        # Compute secondary values (Axis display) if valid
        secondary_values = []
        if payload.axis_display in [DisplayAxisSpace.WORLD, DisplayAxisSpace.LOCAL]:
            start_point, end_point = computed_points[:2]
            if payload.axis_display == DisplayAxisSpace.WORLD:
                x_start, x_end = start_point, Gf.Vec3d(end_point[0], start_point[1], start_point[2])
                y_start, y_end = x_end, Gf.Vec3d(end_point[0], end_point[1], start_point[2])
                z_start, z_end = y_end, end_point
            else:
                prim = find_valid_ancestor(payload.prim_paths[0], attribute="xformOpOrder")
                if prim:
                    xformable = UsdGeom.Xformable(prim)
                    rot_matrix = xformable.GetLocalTransformation().GetOrthonormalized().ExtractRotationMatrix()
                    x_vec, y_vec = (rot_matrix.GetRow(i) for i in range(2))

                    base = start_point - end_point
                    x_len = Gf.Dot(base, x_vec)
                    y_len = Gf.Dot(base, y_vec)

                    x_start, x_end = start_point, (x_vec * -x_len) + start_point
                    y_start, y_end = x_end, (y_vec * -y_len) + x_end
                    z_start, z_end = y_end, end_point

                else:
                    carb.log_warn(f"Prim not found at path: {payload.prim_paths[0]}")
                    return ComputeOutput(computed_points, out_distance, [0.0, 0.0, 0.0])

            secondary_values = [
                convert_distance_and_units((x_start - x_end).GetLength(), payload.unit_type.value)[0],
                convert_distance_and_units((y_start - y_end).GetLength(), payload.unit_type.value)[0],
                convert_distance_and_units((z_start - z_end).GetLength(), payload.unit_type.value)[0],
            ]

        return ComputeOutput(computed_points, out_distance, secondary_values)


class MultiPointCompute(MeasureCompute):
    def __init__(self):
        super().__init__()

    def execute(self, payload: MeasurePayload) -> Optional[ComputeOutput]:
        if len(payload.prim_paths) != len(payload.points):
            return None

        if len(self._point_models) == 0:
            # Create the PointPrimRelationship
            for i in range(len(payload.points)):
                self._point_models.append(PointPrimRelationshipModel(payload.points[i], payload.prim, i))

        computed_points = [model.computed_point for model in self._point_models]
        sub_point_lengths = [
            (computed_points[i] - computed_points[i + 1]).GetLength() for i in range(len(computed_points) - 1)
        ]
        total_length = sum(sub_point_lengths)

        out_length = convert_distance_and_units(total_length, payload.unit_type.value)[0]
        out_sub_lengths = [convert_distance_and_units(val, payload.unit_type.value)[0] for val in sub_point_lengths]

        return ComputeOutput(computed_points, out_length, out_sub_lengths)


class AngleCompute(MeasureCompute):
    def __init__(self):
        super().__init__()

    def _calculate_angle(self, points: Gf.Vec3d) -> float:
        start, axis, end = points[0], points[1], points[2]

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

    def execute(self, payload: MeasurePayload) -> Optional[ComputeOutput]:
        if len(payload.prim_paths) != len(payload.points):
            return None

        if len(self._point_models) == 0:
            # Create the PointPrimRelationship
            self._point_models.append(PointPrimRelationshipModel(payload.points[0], payload.prim, 0))
            self._point_models.append(PointPrimRelationshipModel(payload.points[1], payload.prim, 1))
            self._point_models.append(PointPrimRelationshipModel(payload.points[2], payload.prim, 2))

        computed_points = [model.computed_point for model in self._point_models]

        primary_angle = self._calculate_angle(computed_points)
        secondary_angle = 360 - primary_angle

        return ComputeOutput(computed_points, primary_angle, [secondary_angle])


class AreaCompute(MeasureCompute):
    def __init__(self):
        super().__init__()

    def _calculate_area(self, points: List[Gf.Vec3d]) -> float:
        unique_points: List[Gf.Vec3d] = []

        if points:
            unique_points.append(points[0])
            for pt in points[1:]:
                if pt != unique_points[-1]:
                    unique_points.append(pt)

        if len(unique_points) < 3:
            return 0.0

        start, mid, end = unique_points[:3]
        leg_a, leg_b = (start - mid).GetNormalized(), (end - mid).GetNormalized()
        surface_normal = Gf.Cross(leg_a, leg_b).GetNormalized()

        total = Gf.Vec3d(0, 0, 0)
        for i in range(len(unique_points)):
            v1 = unique_points[i]
            v2 = unique_points[0] if i == len(unique_points) - 1 else unique_points[i + 1]
            product = Gf.Cross(v1, v2)
            total += product

        return abs(Gf.Dot(total, surface_normal) * 0.5)

    def execute(self, payload: MeasurePayload) -> Optional[ComputeOutput]:
        if len(payload.prim_paths) != len(payload.points):
            return None

        if len(self._point_models) == 0:
            # Create the PointPrimRelationship
            for i in range(len(payload.points)):
                self._point_models.append(PointPrimRelationshipModel(payload.points[i], payload.prim, i))

        computed_points = [model.computed_point for model in self._point_models]
        computed_area = self._calculate_area(computed_points)
        out_area = convert_area_to_units(computed_area, payload.unit_type.value)
        return ComputeOutput(computed_points, out_area, [])


class DiameterCompute(MeasureCompute):
    def __init__(self):
        super().__init__()

    def _compute_center(self, a: Gf.Vec3d, b: Gf.Vec3d, c: Gf.Vec3d) -> Gf.Vec3d:
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

        return line_intersect(mid_a, bisect_a, mid_b, bisect_b)

    def execute(self, payload: MeasurePayload) -> Optional[ComputeOutput]:
        if len(payload.prim_paths) != len(payload.points):
            return None

        if len(self._point_models) == 0:
            # Create the PointPrimRelationship
            for i in range(len(payload.points)):
                self._point_models.append(PointPrimRelationshipModel(payload.points[i], payload.prim, i))

        computed_points = [model.computed_point for model in self._point_models]
        computed_points.append(self._compute_center(*computed_points[:3]))

        # Get diameter value
        diameter = (computed_points[-1] - computed_points[0]).GetLength() * 2
        out_diameter = convert_distance_and_units(diameter, payload.unit_type.value)[0]

        return ComputeOutput(computed_points, out_diameter, [])  # Need to return center to draw arc


class SelectedCompute(MeasureCompute):
    def __init__(self):
        super().__init__()

    @wp.kernel
    def __find_closest_points(
        points_a: wp.array(dtype=wp.vec3d),
        points_b: wp.array(dtype=wp.vec3d),
        out_distances: wp.array(dtype=wp.float64),
        out_indices: wp.array(dtype=wp.int32),
    ):
        tid = wp.tid()

        point = points_a[tid]
        closest_index = wp.int32(0.0)
        closest_distance = wp.float64(1.7976931348623157e308)
        for i in range(points_b.shape[0]):
            distance = wp.length_sq(point - points_b[i])
            if distance < closest_distance:
                closest_distance = distance
                closest_index = i

        out_distances[tid] = closest_distance
        out_indices[tid] = closest_index

    @wp.kernel
    def __find_furthest_points(
        points_a: wp.array(dtype=wp.vec3d),
        points_b: wp.array(dtype=wp.vec3d),
        out_distances: wp.array(dtype=wp.float64),
        out_indices: wp.array(dtype=wp.int32),
    ):
        tid = wp.tid()

        point = points_a[tid]
        furthest_index = wp.int32(0.0)
        furthest_distance = wp.float64(0.0)
        for i in range(points_b.shape[0]):
            distance = wp.length_sq(point - points_b[i])
            if distance > furthest_distance:
                furthest_distance = distance
                furthest_index = i

        out_distances[tid] = furthest_distance
        out_indices[tid] = furthest_index

    def __compute_nearest(
        self, points_a: List[Gf.Vec3d], points_b: List[Gf.Vec3d], payload: MeasurePayload
    ) -> ComputeOutput:
        num_points_a = len(points_a)
        out_distances = wp.empty(num_points_a, dtype=wp.float64)
        out_indices = wp.empty(num_points_a, dtype=wp.int32)

        wp.launch(
            SelectedCompute.__find_closest_points,
            num_points_a,
            [wp.array(points_a, dtype=wp.vec3d), wp.array(points_b, dtype=wp.vec3d), out_distances, out_indices],
        )

        a_idx = out_distances.numpy().argmin(0)
        b_idx = out_indices.numpy()[a_idx]

        pt_a = points_a[a_idx]
        pt_b = points_b[b_idx]

        distance = (pt_a - pt_b).GetLength()
        out_distance = convert_distance_and_units(distance, payload.unit_type.value)[0]

        pt_a, pt_b = Gf.Vec3d(*pt_a), Gf.Vec3d(*pt_b)
        return ComputeOutput([pt_a, pt_b], out_distance, [])

    def __compute_furthest(
        self, points_a: List[Gf.Vec3d], points_b: List[Gf.Vec3d], payload: MeasurePayload
    ) -> ComputeOutput:
        num_points_a = len(points_a)
        out_distances = wp.empty(num_points_a, dtype=wp.float64)
        out_indices = wp.empty(num_points_a, dtype=wp.int32)

        wp.launch(
            SelectedCompute.__find_furthest_points,
            num_points_a,
            [wp.array(points_a, dtype=wp.vec3d), wp.array(points_b, dtype=wp.vec3d), out_distances, out_indices],
        )

        a_idx = out_distances.numpy().argmax(0)
        b_idx = out_indices.numpy()[a_idx]

        pt_a = points_a[a_idx]
        pt_b = points_b[b_idx]

        distance = (pt_a - pt_b).GetLength()
        out_distance = convert_distance_and_units(distance, payload.unit_type.value)[0]

        pt_a, pt_b = Gf.Vec3d(*pt_a), Gf.Vec3d(*pt_b)
        return ComputeOutput([pt_a, pt_b], out_distance, [])

    def __compute_center(self, prim_a: "Usd.Prim", prim_b: "Usd.Prim", payload: MeasurePayload) -> ComputeOutput:
        bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
        pt_a = bbox_cache.ComputeWorldBound(prim_a).ComputeCentroid()
        pt_b = bbox_cache.ComputeWorldBound(prim_b).ComputeCentroid()
        pt_a, pt_b = Gf.Vec3d(*pt_a), Gf.Vec3d(*pt_b)

        distance = (pt_a - pt_b).GetLength()
        out_distance = convert_distance_and_units(distance, payload.unit_type.value)[0]

        return ComputeOutput([pt_a, pt_b], out_distance, [])

    def execute(self, payload: MeasurePayload) -> Optional[ComputeOutput]:
        stage = self._ctx.get_stage()

        prim_a, prim_b = stage.GetPrimAtPath(payload.prim_paths[0]), stage.GetPrimAtPath(payload.prim_paths[1])

        if payload.tool_sub_mode == 2:  # Center
            return self.__compute_center(prim_a, prim_b, payload)

        # Compute surface points for Min or Max before executing.
        def extract_descendents_points(root):
            # Iterate through the prim and its descendants: point-based gprims (meshes, curves, points) give their
            # points; other gprims (implicit Cube, Sphere, Cylinder, Cone, Capsule, Plane) have no points, so they
            # give the corners and face centers of their extent (exact for cubes, the bounding box for the others).
            points = []
            predicate = Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)

            for prim in Usd.PrimRange(root, predicate):
                if prim.IsA(UsdGeom.PointBased):
                    point_attr = prim.GetAttribute("points")
                    if point_attr and point_attr.HasValue():
                        world_mtx = omni.usd.get_world_transform_matrix(prim)
                        points += [world_mtx.Transform(Gf.Vec3d(point)) for point in point_attr.Get()]
                elif prim.IsA(UsdGeom.Gprim):
                    extent = UsdGeom.Boundable.ComputeExtentFromPlugins(UsdGeom.Boundable(prim), Usd.TimeCode.Default())
                    if extent and len(extent) == 2:
                        world_mtx = omni.usd.get_world_transform_matrix(prim)
                        points += [world_mtx.Transform(point) for point in _extent_points(extent[0], extent[1])]

            # The prim may have no geometry: fall back to its own world position
            return points or [Gf.Vec3d(omni.usd.get_world_transform_matrix(root).ExtractTranslation())]

        points_a = extract_descendents_points(prim_a)
        points_b = extract_descendents_points(prim_b)

        is_min = payload.tool_sub_mode == 0  # 0=Min, 1=Max
        return (
            self.__compute_nearest(points_a, points_b, payload)
            if is_min
            else self.__compute_furthest(points_a, points_b, payload)
        )


def _extent_points(lo, hi) -> List[Gf.Vec3d]:
    """The 8 corners and 6 face centers of an extent (local space)."""
    lo, hi = Gf.Vec3d(lo), Gf.Vec3d(hi)
    mid = (lo + hi) * 0.5
    corners = [Gf.Vec3d(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    faces = [
        Gf.Vec3d(lo[0], mid[1], mid[2]),
        Gf.Vec3d(hi[0], mid[1], mid[2]),
        Gf.Vec3d(mid[0], lo[1], mid[2]),
        Gf.Vec3d(mid[0], hi[1], mid[2]),
        Gf.Vec3d(mid[0], mid[1], lo[2]),
        Gf.Vec3d(mid[0], mid[1], hi[2]),
    ]
    return corners + faces


COMPUTE_MAP: Dict = {
    MeasureMode.NONE: None,
    MeasureMode.POINT_TO_POINT: PointToPointCompute,
    MeasureMode.MULTI_POINT: MultiPointCompute,
    MeasureMode.ANGLE: AngleCompute,
    MeasureMode.AREA: AreaCompute,
    MeasureMode.DIAMETER: DiameterCompute,
    MeasureMode.SELECTED: SelectedCompute,
}
