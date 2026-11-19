# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import carb
import numpy as np
import omni.timeline
from omni.ui import scene as sc
from pxr import Gf, Sdf, Usd, UsdGeom

from .attribute_value_cache import AttributeValueCache


def list_to_gf_matrix4d(data: Sequence[float]) -> Gf.Matrix4d:
    if len(data) != 16:
        raise RuntimeError("Gf.Matrix4d needs 16 nubmers to initialize")
    return Gf.Matrix4d(
        data[0],
        data[1],
        data[2],
        data[3],
        data[4],
        data[5],
        data[6],
        data[7],
        data[8],
        data[9],
        data[10],
        data[11],
        data[12],
        data[13],
        data[14],
        data[15],
    )


class MeasureSnapProvider(ABC):
    def __init__(self, viewport_api):
        self._viewport_api = viewport_api

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._value_cache = None

    def on_began(self, excluded_paths: List[Union[str, Sdf.Path]], **kwargs):
        self._excluded_paths = list(excluded_paths)

    def on_ended(self, **kwargs):
        self._excluded_paths = []

    @abstractmethod
    def on_snap(
        self,
        ndc_location: Sequence[float],
        result: Any,
        want_orient: bool = False,
        want_keep_spacing: bool = True,
        conform_up_axis: str = "Stage",
        hysteresis_factor: float = 1.0,
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Called when manipulator wants to perform a snap operation.
        Only current selected snap provider will be called.

        Args:
            xform (Gf.Matrix4d): Transformation of current manipulator object.
            ndc_location (Sequence[float]): Location of the cursor in NDC space.
            prim_path (str): Path to the prim to query raycast to
            scene_view (omni.ui.scene.SceneView): SceneView of manipulator who triggers this snap request.
            want_orient (bool): If the snap provider can change the orientation of object to be snapped,
                                it should supply `orient` to `on_snapped` when `want_orient` is True.
            want_keep_spacing (bool): Pass it through to `on_snapped`
            on_snapped (Callable): A callback function receiving `**kwargs`. Depending on if snap is successful
                                   and settings, `position`, `path`, `orient` may be provide to it.

        Returns:
            True if snap is successful. If snap is async operation, return True if the
            request of snapping is successful. False if snap failed or cannot be requested.
        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """
        Returns the name/id of the provider. This is the internal name used for managing snaps
        """
        raise NotImplementedError()

    @classmethod
    def get_display_name(cls) -> str:
        """
        Returns the display name of the provider. If not overridden, it falls back to get_name().
        """
        return cls.get_name()

    @staticmethod
    @abstractmethod
    def can_orient() -> bool:
        """
        Returns if the provider may change the orientation of object during a snap.
        """
        raise NotImplementedError()

    @staticmethod
    def require_viewport_api() -> bool:
        """
        Returns if the provider requires viewport_api to work
        """
        return True

    @staticmethod
    def get_order() -> float:
        """
        Returns the priority order of the snap provider.
        If more than one provider is enabled at the same time and both
        are able to provide snap result, the one with lower order wins.
        """
        return 0.0

    def _generate_picking_ray(self, ndc_location: Sequence[float]) -> Tuple[Gf.Vec3d, Gf.Vec3d, float]:
        """
        A helper function to generate picking ray from ndc cursor location.
        Only call it if self._viewport_api is not None.
        """
        ndc_near = (ndc_location[0], ndc_location[1], -1)
        ndc_far = (ndc_location[0], ndc_location[1], 1)
        view = self._viewport_api.view
        proj = self._viewport_api.projection
        view_proj_inv = (view * proj).GetInverse()

        origin = view_proj_inv.Transform(ndc_near)
        dir = view_proj_inv.Transform(ndc_far) - origin
        dist = dir.Normalize()

        return (origin, dir, dist)

    def _get_ndc_to_screen_matrix(self, scene_view: Optional[sc.SceneView]) -> Gf.Matrix4d:
        if scene_view:
            width = scene_view.computed_width
            height = scene_view.computed_height
        else:
            # fallback to resolution if scene_view is not available
            # Note, self._viewport_api.resolution may not map 1:1 to the actual viewport size
            width = self._viewport_api.resolution[0]
            height = self._viewport_api.resolution[1]

        ndc_to_screen = Gf.Matrix4d()
        ndc_to_screen.SetScale(Gf.Vec3d(width * 0.5, height * 0.5, 0.5))
        ndc_to_screen.SetTranslateOnly(Gf.Vec3d(width * 0.5, height * 0.5, 0.5))

        return ndc_to_screen


class MeshBasedSnapProvider(MeasureSnapProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeline = omni.timeline.get_timeline_interface()

    def destroy(self):
        super().destroy()

    def on_began(self, excluded_paths: List[Union[str, Sdf.Path]], **kwargs):
        super().on_began(excluded_paths, **kwargs)

    def on_ended(self, **kwargs):
        super().on_ended(**kwargs)

    def _get_current_timecode(self) -> Usd.TimeCode:
        return Usd.TimeCode(self._timeline.get_current_time() * self._timeline.get_time_codes_per_seconds())

    def _get_vert_world_pos_on_hit_face(self, result: Any) -> list[Gf.Vec3d]:
        vert_poses: list[Gf.Vec3d] = []

        prim_path = Sdf.Path(result.get_target_usd_path())
        stage = self._viewport_api.usd_context.get_stage()
        prim = stage.GetPrimAtPath(prim_path)
        mesh = UsdGeom.Mesh(prim)
        if not mesh:
            return vert_poses

        # Kit 111 pick hits carry no mesh face (the world-ray raycast query that reported it was dropped).
        hit_face_index = getattr(result, "primitive_id", None)
        if hit_face_index is None:
            return vert_poses

        value_cache = AttributeValueCache()
        face_vertex_counts = value_cache.get_value(prim_path.AppendProperty(UsdGeom.Tokens.faceVertexCounts))

        if hit_face_index >= len(face_vertex_counts):
            carb.log_error(
                "Invalid hit face index. `/rtx-transient/scenedb/useUniformsReindexing` setting must be True to use this snap option"
            )
            return vert_poses

        face_vertex_indices = value_cache.get_value(prim_path.AppendProperty(UsdGeom.Tokens.faceVertexIndices))
        points = value_cache.get_value(prim_path.AppendProperty(UsdGeom.Tokens.points))

        if not face_vertex_counts or not face_vertex_indices or not points:
            return vert_poses

        xform = self._viewport_api.usd_context.compute_path_world_transform(prim_path.pathString)
        xform = list_to_gf_matrix4d(xform)

        face_vert_offset = 0
        vertex_world_pos_cache = {}

        # transform points into world space
        # TODO should it be screen space for better UX?
        # we can also transform hit_point into local space but the result is wrong if prim has non-uniform scaling
        def get_world_pos(vi: int):
            if vi not in vertex_world_pos_cache:
                point = Gf.Vec3d(points[vi])
                vertex_world_pos_cache[vi] = xform.Transform(point)

            return vertex_world_pos_cache[vi]

        face_vert_offset = int(np.sum(face_vertex_counts[:hit_face_index]) or 0)
        face_vertex_count = face_vertex_counts[hit_face_index]
        for vii in range(face_vertex_count):
            fvi_begin = face_vert_offset + vii  # fvi: index into face vertex indices array,
            vi = face_vertex_indices[fvi_begin]  # vi: index into the points array,
            vert_poses.append(get_world_pos(vi))

        return vert_poses
