# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
USD commands for creating PointInstancer prims.

This module provides undoable commands for creating USD PointInstancers,
which are used for efficient instancing of scattered objects.
"""

from typing import List, Optional, Tuple

import omni.kit.commands
import omni.usd.commands
from pxr import Gf, Sdf, Usd, UsdGeom


class ScatterCreatePointInstancerCommand(omni.kit.commands.Command, omni.usd.commands.stage_helper.UsdStageHelper):
    """
    Create PointInstancer undoable **Command**.

    ### Arguments:

        `path_to: str`
            The path for the new prims

        `transforms: List`
            Pairs containing transform matrices and ids to apply to new objects

        `prim_names: List[str]`
            Prims to duplicate
    """

    def __init__(
        self,
        path_to: str,
        transforms: List[Tuple[Gf.Matrix4d, int]],
        prim_names: List[str],
        stage: Optional[Usd.Stage] = None,
        context_name: Optional[str] = None,
    ):
        omni.usd.commands.stage_helper.UsdStageHelper.__init__(self, stage, context_name)
        self._path_to = path_to

        # We have it like [(tr, id), (tr, id), ...]
        # It will be transformed to [[tr, tr, ...], [id, id, ...]]
        unzipped = list(zip(*transforms))

        # Convert Vec3d to Vec3f for PointInstancer positions (PointInstancer uses point3f[])
        self._positions = [Gf.Vec3f(m.ExtractTranslation()) for m in unzipped[0]]
        self._proto_indices = list(unzipped[1])
        self._prim_names = prim_names.copy()

    def do(self):
        stage = self._get_stage()

        # Set up PointInstancer
        instancer = UsdGeom.PointInstancer.Define(stage, Sdf.Path(self._path_to))
        attr = instancer.CreatePrototypesRel()

        # Add prototype prims (maintain order to preserve proto_indices alignment)
        for name in self._prim_names:
            if name and name.strip():
                prim_path = Sdf.Path(name.strip())
                if not prim_path.isEmpty:
                    attr.AddTarget(prim_path)

        # Set attributes
        instancer.CreatePositionsAttr().Set(self._positions)
        instancer.CreateProtoIndicesAttr().Set(self._proto_indices)

    def undo(self):
        delete_cmd = omni.usd.commands.DeletePrimsCommand([self._path_to])
        delete_cmd.do()


omni.kit.commands.register_all_commands_in_module(__name__)
