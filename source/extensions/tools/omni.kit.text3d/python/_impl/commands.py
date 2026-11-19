# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.commands
from omni.usd.commands import UsdStageHelper
from pxr import Sdf, Usd


class Create3dTextCommand(omni.kit.commands.Command, UsdStageHelper):
    """
    Inserts a 3d Text Prim into the stage

    ### Arguments:

        `target_prim_path: Sdf.Path`
            The path of the new text prim.

        `path_to_usd`: str`
            The file path of the usd to be copied

        `source_prim_path: Sdf.Path`
            The path to the prim in the usd to be copied to the target prim

        `stage : Optional[Usd.Stage]`
            The stage to add the prim to. If None, it takes the stage from the USD Context.
    """

    def __init__(
        self, target_prim_path: Sdf.Path, path_to_usd: str, source_prim_path: Sdf.Path, stage: Usd.Stage = None
    ):
        UsdStageHelper.__init__(self, stage)
        self._target_prim_path = target_prim_path
        self._path_to_usd = path_to_usd
        self._source_prim_path = source_prim_path

    def do(self):
        stage = self._get_stage()
        root_layer = stage.GetRootLayer()
        s = Usd.Stage.CreateInMemory()
        s.GetRootLayer().Import(self._path_to_usd)
        Sdf.CreatePrimInLayer(root_layer, self._target_prim_path)
        Sdf.CopySpec(s.GetRootLayer(), self._source_prim_path, root_layer, self._target_prim_path)

    def undo(self):
        stage = self._get_stage()
        stage.RemovePrim(self._target_prim_path)
