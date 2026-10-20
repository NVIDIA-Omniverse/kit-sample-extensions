# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = [
    "MaterialGraph_CreateUsdUIBackdropCommand",
]

from typing import Optional, Tuple

import omni.kit.commands
from omni.usd.commands import DeletePrimsCommand
from pxr import Sdf, Usd, UsdUI

from .stage_helper import UsdStageHelper


def get_first_available_path(stage, parent_path, identifier):
    prim_name = identifier
    counter = 1
    while True:
        created_path = parent_path.AppendElementString(prim_name)
        if not stage.GetPrimAtPath(created_path):
            break

        prim_name = "{}{:02d}".format(identifier, counter)
        counter += 1

    return created_path


class MaterialGraph_CreateUsdUIBackdropCommand(omni.kit.commands.Command, UsdStageHelper):
    def __init__(
        self,
        parent_path: Sdf.Path,
        identifier: str,
        position: Optional[Tuple[float]] = None,
        position_key: Optional[str] = None,
        size: Optional[Tuple[float]] = None,
        display_color: Optional[Tuple[float]] = None,
        stacking_order: Optional[int] = -1,
        stage: Optional[Usd.Stage] = None,
    ):
        UsdStageHelper.__init__(self, stage)
        self._created_path = None
        self._parent_path = parent_path
        self._identifier = identifier
        self._position = position
        self._position_key = position_key
        self._size = size
        self._display_color = display_color
        self._stacking_order = stacking_order

    def do(self):
        stage = self._get_stage()
        self._created_path = get_first_available_path(stage, self._parent_path, self._identifier)

        backdrop = UsdUI.Backdrop.Define(stage, self._created_path)
        prim = backdrop.GetPrim()
        api = UsdUI.NodeGraphNodeAPI.Apply(prim)

        attr = api.CreateStackingOrderAttr()
        attr.Set(self._stacking_order)

        if self._position:
            if self._position_key:
                prim.SetCustomDataByKey(self._position_key, self._position)
            else:
                attr = api.CreatePosAttr()
                attr.Set(self._position)

        if self._size:
            attr = api.CreateSizeAttr()
            attr.Set(self._size)

        if self._display_color:
            attr = api.CreateDisplayColorAttr()
            attr.Set(self._display_color)

        self._get_context().get_selection().set_selected_prim_paths([str(self._created_path)], True)
        return prim

    def undo(self):
        delete_cmd = DeletePrimsCommand([self._created_path], stage=self._get_stage())
        delete_cmd.do()
