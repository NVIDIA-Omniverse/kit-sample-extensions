# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = [
    "CenterSnapProvider",
    "PivotSnapProvider",
    "VertexSnapProvider",
    "EdgeSnapProvider",
    "MidPointSnapProvider",
    "SurfaceSnapProvider",
]

from typing import Any, Dict, Optional, Sequence, Tuple

import carb.profiler
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom

from ...common import SNAP_DISTANCE, SnapMode
from .provider import MeshBasedSnapProvider


class CenterSnapProvider(MeshBasedSnapProvider):
    def on_snap(
        self,
        ndc_location: Sequence[float],
        result: Any,
        want_orient: bool = True,
        want_keep_spacing: bool = True,
        conform_up_axis: str = "Stage",
        hysteresis_factor: float = 1.0,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        prim_path = result.get_target_usd_path()
        stage = self._viewport_api.usd_context.get_stage()
        prim = stage.GetPrimAtPath(prim_path)

        if prim.IsValid():
            # TODO: convert payload to dataclass
            payload = {}
            payload["type"] = SnapMode.CENTER
            payload["keep_spacing"] = want_keep_spacing
            payload["path"] = prim_path
            transform = self._viewport_api.usd_context.compute_path_world_transform(prim_path)
            payload["position"] = (transform[12], transform[13], transform[14])

            if want_orient:
                rotation = Gf.Matrix3d(
                    transform[0],
                    transform[1],
                    transform[2],
                    transform[3],
                    transform[4],
                    transform[5],
                    transform[6],
                    transform[7],
                    transform[8],
                    transform[9],
                    transform[10],
                )
                rotation.Orthonormalize()
                payload["orient"] = rotation.ExtractRotation()

            # on_snapped(**payload)
            return (True, payload)

        return (False, None)

    @staticmethod
    def get_name() -> str:
        return "CenterSnapProvider"

    @classmethod
    def get_display_name(cls) -> str:
        return "Center"

    @staticmethod
    def can_orient() -> bool:
        return True

    @staticmethod
    def get_order() -> float:
        return -1.0


class PivotSnapProvider(MeshBasedSnapProvider):
    def on_snap(
        self,
        ndc_location: Sequence[float],
        result: Any,
        want_orient: bool = True,
        want_keep_spacing: bool = True,
        conform_up_axis: str = "Stage",
        hysteresis_factor: float = 1.0,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        prim_path = result.get_target_usd_path()
        stage = self._viewport_api.usd_context.get_stage()
        prim = stage.GetPrimAtPath(prim_path)

        if prim.IsValid():
            # TODO: convert payload to dataclass
            payload = {}
            payload["type"] = SnapMode.PIVOT
            payload["keep_spacing"] = want_keep_spacing
            payload["path"] = prim_path
            prim = self._viewport_api.usd_context.get_stage().GetPrimAtPath(prim_path)
            parent_transform = Gf.Matrix4d(
                *self._viewport_api.usd_context.compute_path_world_transform(
                    Sdf.Path(prim_path).GetParentPath().pathString
                )
            )
            _, _, _, t = omni.usd.get_local_transform_SRT(prim, self._get_current_timecode())
            pivot_inv_mtx = self._get_local_transform_pivot_inv(prim, self._get_current_timecode())
            payload["position"] = parent_transform.Transform(pivot_inv_mtx.GetInverse().Transform(t))

            if want_orient:
                transform = Gf.Matrix4d(*self._viewport_api.usd_context.compute_path_world_transform(prim_path))
                rotation = Gf.Matrix3d(
                    transform[0],
                    transform[1],
                    transform[2],
                    transform[3],
                    transform[4],
                    transform[5],
                    transform[6],
                    transform[7],
                    transform[8],
                    transform[9],
                    transform[10],
                )
                rotation.Orthonormalize()
                payload["orient"] = rotation.ExtractRotation()

            # on_snapped(**payload)
            return (True, payload)

        return (False, None)

    def _get_local_transform_pivot_inv(self, prim: Usd.Prim, time: Usd.TimeCode = Usd.TimeCode):
        xform = UsdGeom.Xformable(prim)
        xform_ops = xform.GetOrderedXformOps()
        if len(xform_ops):
            pivot_op_inv = xform_ops[-1]
            if (
                pivot_op_inv.GetOpType() == UsdGeom.XformOp.TypeTranslate
                and pivot_op_inv.IsInverseOp()
                and pivot_op_inv.GetName().endswith("pivot")
            ):
                return pivot_op_inv.GetOpTransform(time)
        return Gf.Matrix4d(1.0)

    @staticmethod
    def get_name() -> str:
        return "PivotSnapProvider"

    @classmethod
    def get_display_name(cls) -> str:
        return "Pivot"

    @staticmethod
    def can_orient() -> bool:
        return True

    @staticmethod
    def get_order() -> float:
        return -1.0


class SurfaceSnapProvider(MeshBasedSnapProvider):
    def on_snap(
        self,
        ndc_location: Sequence[float],
        result: Any,
        want_orient: bool = True,
        want_keep_spacing: bool = True,
        conform_up_axis: str = "Stage",
        hysteresis_factor: float = 1.0,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        prim_path = result.get_target_usd_path()

        payload = {}
        payload["type"] = SnapMode.SURFACE
        payload["keep_spacing"] = want_keep_spacing
        payload["path"] = prim_path
        payload["position"] = Gf.Vec3d(result.hit_position[0], result.hit_position[1], result.hit_position[2])

        if want_orient:
            stage = self._viewport_api.stage
            stage_up_axis = UsdGeom.GetStageUpAxis(stage)

            normal = Gf.Vec3d(*result.normal)

            if conform_up_axis == "Stage":
                conform_up_axis = "Y" if stage_up_axis == UsdGeom.Tokens.y else "Z"

            def calculate_orientation(stage_up: Gf.Vec3d, stage_side: Gf.Vec3d):
                if conform_up_axis == "X":
                    x = normal.GetNormalized()
                    z = Gf.Cross(stage_up, x)
                    length = z.Normalize()
                    if length < 1e-6:
                        z = stage_side
                    y = Gf.Cross(z, x).GetNormalized()
                elif conform_up_axis == "Y":
                    y = normal.GetNormalized()
                    x = Gf.Cross(stage_up, y)
                    length = x.Normalize()
                    if length < 1e-6:
                        x = stage_side
                    z = Gf.Cross(x, y).GetNormalized()
                else:
                    z = normal.GetNormalized()
                    y = Gf.Cross(stage_up, z)
                    length = y.Normalize()
                    if length < 1e-6:
                        y = stage_side
                    x = Gf.Cross(y, z).GetNormalized()

                return x, y, z

            # TODO: Fix Typing
            up: Gf.Vec3d = Gf.Vec3d.YAxis() if stage_up_axis == UsdGeom.Tokens.y else Gf.Vec3d.ZAxis()
            side: Gf.Vec3d = Gf.Vec3d.XAxis() if stage_up_axis == UsdGeom.Tokens.y else Gf.Vec3d.YAxis()

            x, y, z = calculate_orientation(up, side)

            new_rotation = Gf.Matrix3d()
            new_rotation.SetRow(0, x)
            new_rotation.SetRow(1, y)
            new_rotation.SetRow(2, z)

            payload["normal"] = Gf.Vec3d(*result.normal)
            payload["orient"] = new_rotation.ExtractRotation()
        # on_snapped(**payload)
        return (True, payload)

    @staticmethod
    def get_name() -> str:
        return "SurfaceSnapProvider"

    @classmethod
    def get_display_name(cls) -> str:
        return "Surface"

    @staticmethod
    def can_orient() -> bool:
        return True

    @staticmethod
    def get_order() -> float:
        return 0.0


class EdgeSnapProvider(MeshBasedSnapProvider):
    def on_snap(
        self,
        ndc_location: Sequence[float],
        result: Any,
        want_orient: bool = False,
        want_keep_spacing: bool = True,
        conform_up_axis: str = "Stage",
        hysteresis_factor: float = 1.0,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        nearest_position = None
        nearest_sqdistance = None
        hit_point = Gf.Vec3d(result.hit_position[0], result.hit_position[1], result.hit_position[2])

        vert_poses = self._get_vert_world_pos_on_hit_face(result)
        for i in range(len(vert_poses)):
            edge_begin_pos = vert_poses[i]
            edge_end_pos = vert_poses[(i + 1) % len(vert_poses)]

            direction = edge_end_pos - edge_begin_pos
            length = direction.Normalize()
            begin_to_hit = hit_point - edge_begin_pos
            proj = Gf.Dot(begin_to_hit, direction)
            if proj >= 0 and proj <= length:
                nearest_pos_on_line = edge_begin_pos + direction * proj
                hit_to_line = nearest_pos_on_line - hit_point
                sqdistance = hit_to_line * hit_to_line

                if nearest_position is None or sqdistance < nearest_sqdistance:
                    nearest_position = nearest_pos_on_line
                    nearest_sqdistance = sqdistance

        snap_threshold = (SNAP_DISTANCE * hysteresis_factor) ** 2
        if nearest_position and nearest_sqdistance < snap_threshold:
            payload = {}
            payload["type"] = SnapMode.EDGE
            payload["keep_spacing"] = want_keep_spacing
            payload["path"] = result.get_target_usd_path()
            payload["position"] = Gf.Vec3d(nearest_position)

            return (True, payload)

        return (False, None)

    @staticmethod
    def get_name() -> str:
        return "EdgeSnapProvider"

    @classmethod
    def get_display_name(cls) -> str:
        return "Edge"

    @staticmethod
    def can_orient() -> bool:
        return False

    @staticmethod
    def get_order() -> float:
        return -3.0


class MidPointSnapProvider(MeshBasedSnapProvider):
    def on_snap(
        self,
        ndc_location: Sequence[float],
        result: Any,
        want_orient: bool = False,
        want_keep_spacing: bool = True,
        conform_up_axis: str = "Stage",
        hysteresis_factor: float = 1.0,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        nearest_position = None
        nearest_sqdistance = None
        hit_point = Gf.Vec3d(result.hit_position[0], result.hit_position[1], result.hit_position[2])

        vert_poses = self._get_vert_world_pos_on_hit_face(result)
        for i in range(len(vert_poses)):
            edge_begin_pos = vert_poses[i]
            edge_end_pos = vert_poses[(i + 1) % len(vert_poses)]

            direction = edge_end_pos - edge_begin_pos
            length = direction.Normalize()
            begin_to_hit = hit_point - edge_begin_pos
            proj = Gf.Dot(begin_to_hit, direction)
            if proj >= 0 and proj <= length:
                nearest_pos_on_line = edge_begin_pos + direction * proj
                hit_to_line = nearest_pos_on_line - hit_point
                sqdistance = hit_to_line * hit_to_line

                if nearest_position is None or sqdistance < nearest_sqdistance:
                    nearest_position = nearest_pos_on_line
                    nearest_sqdistance = sqdistance
                    mid_point_position = (edge_end_pos + edge_begin_pos) * 0.5

        snap_threshold = (SNAP_DISTANCE * hysteresis_factor) ** 2
        if nearest_position and nearest_sqdistance < snap_threshold:
            payload = {}
            payload["type"] = SnapMode.MIDPOINT
            payload["keep_spacing"] = want_keep_spacing
            payload["path"] = result.get_target_usd_path()
            payload["position"] = Gf.Vec3d(mid_point_position)

            return (True, payload)

        return (False, None)

    @staticmethod
    def get_name() -> str:
        return "MidPointSnapProvider"

    @classmethod
    def get_display_name(cls) -> str:
        return "Midpoint"

    @staticmethod
    def can_orient() -> bool:
        return False

    @staticmethod
    def get_order() -> float:
        return -3.0


class VertexSnapProvider(MeshBasedSnapProvider):
    @carb.profiler.profile
    def on_snap(
        self,
        ndc_location: Sequence[float],
        result: Any,
        want_orient: bool = False,
        want_keep_spacing: bool = True,
        hysteresis_factor: float = 1.0,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        nearest_position = None
        nearest_sqdistance = None
        hit_point = Gf.Vec3d(result.hit_position[0], result.hit_position[1], result.hit_position[2])

        for world_pos in self._get_vert_world_pos_on_hit_face(result):
            diff = world_pos - hit_point
            sqdistance = diff * diff
            if nearest_position is None or sqdistance < nearest_sqdistance:
                nearest_position = world_pos
                nearest_sqdistance = sqdistance

        snap_threshold = (SNAP_DISTANCE * hysteresis_factor) ** 2
        if nearest_position and nearest_sqdistance < snap_threshold:
            payload = {}
            payload["type"] = SnapMode.VERTEX
            payload["keep_spacing"] = want_keep_spacing
            payload["path"] = result.get_target_usd_path()
            payload["position"] = Gf.Vec3d(nearest_position)

            return (True, payload)

        return (False, None)

    @staticmethod
    def get_name() -> str:
        return "VertexSnapProvider"

    @classmethod
    def get_display_name(cls) -> str:
        return "Vertex"

    @staticmethod
    def can_orient() -> bool:
        return False

    @staticmethod
    def get_order() -> float:
        return -4.0
