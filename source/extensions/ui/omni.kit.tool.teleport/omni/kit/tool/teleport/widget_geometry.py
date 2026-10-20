# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni.ui import color as cl
from pxr import Usd, UsdGeom

GIZMO_COLOR_ALLOWED = cl(0.2, 0.77, 0.99, 1.0)
GIZMO_COLOR_DENY = cl(0.3, 0.3, 0.3, 1.0)

GEOMETRY_INSTANCE = None


class RingGeometry:
    def __init__(self):
        self.set_filename(None)

    def _load_geometry(self):
        if self._points is None:
            if self._filename:
                stage: Usd.Stage = Usd.Stage.Open(self._filename)

                prim = stage.GetPrimAtPath("/teleport_gizmo/teleport_ring/ring")
                if prim.IsValid():
                    if prim.IsA(UsdGeom.Mesh):
                        mesh = UsdGeom.Mesh(prim)
                        self._points = [(x[0], x[1], x[2]) for x in mesh.GetPointsAttr().Get()]
                        self._face_vertex_counts = [x for x in mesh.GetFaceVertexCountsAttr().Get()]
                        self._face_vertex_indices = [x for x in mesh.GetFaceVertexIndicesAttr().Get()]

                        extent = mesh.GetExtentAttr().Get()
                        width = extent[1][0] - extent[0][0]
                        height = extent[1][2] - extent[0][2]
                        self._radius = max(width, height) * 0.5

    @property
    def points(self):
        self._load_geometry()
        return self._points

    @property
    def face_vertex_counts(self):
        self._load_geometry()
        return self._face_vertex_counts

    @property
    def face_vertex_indices(self):
        self._load_geometry()
        return self._face_vertex_indices

    @property
    def colors_allowed(self):
        return [GIZMO_COLOR_ALLOWED] * self.num_vertices

    @property
    def colors_denied(self):
        return [GIZMO_COLOR_DENY] * self.num_vertices

    @property
    def num_vertices(self):
        return len(self.face_vertex_indices)

    @property
    def radius(self):
        self._load_geometry()
        return self._radius

    def get_colors(self, allowed: bool):
        if allowed:
            return self.colors_allowed
        return self.colors_denied

    def set_filename(self, filename: str):
        self._filename = filename
        self._points = None
        self._face_vertex_counts = None
        self._face_vertex_indices = None

    @staticmethod
    def get_instance():
        global GEOMETRY_INSTANCE
        if GEOMETRY_INSTANCE is None:
            GEOMETRY_INSTANCE = RingGeometry()
        return GEOMETRY_INSTANCE
