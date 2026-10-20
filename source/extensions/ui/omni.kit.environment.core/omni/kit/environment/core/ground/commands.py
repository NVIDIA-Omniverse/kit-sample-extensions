# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.commands
import omni.usd
from pxr import Gf, Sdf, UsdGeom, Vt

from ..constants import GROUND_PRIM_PATH
from .data import *


class CreateGroundCommand(omni.kit.commands.Command):
    def __init__(self, prim_path: str = GROUND_PRIM_PATH, ground_size: float = 100, **kwargs):
        """
        Creates ground.

        """
        self._prim_path = prim_path
        self._usd_context = omni.usd.get_context()
        self._selection = self._usd_context.get_selection()
        self._stage = self._usd_context.get_stage()

        self._attributes = {"object_origin": [0.0, 0.0, 0.0], **kwargs}

    def do(self):
        mesh = UsdGeom.Mesh.Define(self._stage, self._prim_path)

        self._define_mesh(mesh)
        return self._prim_path

    def undo(self):
        self._stage.RemovePrim(self._prim_path)

    def _define_mesh(self, mesh):

        stage = omni.usd.get_context().get_stage()
        up_axis = UsdGeom.GetStageUpAxis(stage)
        self._attributes["up_axis"] = up_axis

        mesh.GetPointsAttr().Set(Vt.Vec3fArray(GROUND_POINTS))
        mesh.GetNormalsAttr().Set(Vt.Vec3fArray(GROUND_NORMALS))
        mesh.GetFaceVertexIndicesAttr().Set(GROUND_POINT_INDICES)
        mesh.GetFaceVertexCountsAttr().Set(GROUND_FACE_VERTEX_COUNTS)
        mesh.SetNormalsInterpolation("faceVarying")
        mesh.GetExtentAttr().Set(Vt.Vec3fArray(GROUND_EXTENT))

        if hasattr(mesh, "CreatePrimvar"):
            sts_primvar = mesh.CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray)
        else:
            sts_primvar = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray)
        sts_primvar.SetInterpolation("faceVarying")
        sts_primvar.Set(Vt.Vec2fArray(GROUND_STS))
        sts_primvar.SetIndices(GROUND_POINT_INDICES)

        mesh.CreateSubdivisionSchemeAttr("none")

        default_translate = Gf.Vec3d(0.0, 0.0, 0.0)
        default_rotation = Gf.Vec3d(0.0, 0.0, 0.0) if up_axis == "Z" else Gf.Vec3d(-90.0, 0.0, 0.0)
        prim = mesh.GetPrim()
        attr_translate = prim.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, False)
        attr_translate.Set(default_translate)
        attr_rotation = prim.CreateAttribute("xformOp:rotateXYZ", Sdf.ValueTypeNames.Double3, False)
        attr_rotation.Set(default_rotation)
        attr_order = prim.CreateAttribute("xformOpOrder", Sdf.ValueTypeNames.TokenArray, False)
        attr_order.Set(["xformOp:translate", "xformOp:rotateXYZ"])


omni.kit.commands.register_all_commands_in_module(__name__)
