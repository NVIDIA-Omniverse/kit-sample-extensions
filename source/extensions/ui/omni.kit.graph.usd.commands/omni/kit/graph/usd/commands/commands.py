# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = [
    "CreateUsdUIBackdropCommand",
    "CreateUsdUINoteCommand",
    "UsdUINodeGraphNodeSetCommand",
    "UsdUIRemovePositionCommand",
]

from typing import Optional, Tuple

import omni.kit.commands
from omni.usd.commands import DeletePrimsCommand, UsdStageHelper
from pxr import Sdf, Usd, UsdUI


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


class CreateUsdUIBackdropCommand(omni.kit.commands.Command, UsdStageHelper):
    def __init__(
        self,
        parent_path: Sdf.Path,
        identifier: str,
        position: Optional[Tuple[float]] = None,
        size: Optional[Tuple[float]] = None,
        display_color: Optional[Tuple[float]] = None,
        stage: Optional[Usd.Stage] = None,
    ):
        UsdStageHelper.__init__(self, stage)
        self._created_path = None
        self._parent_path = parent_path
        self._identifier = identifier
        self._position = position
        self._size = size
        self._display_color = display_color

    def do(self):
        stage = self._get_stage()
        self._created_path = get_first_available_path(stage, self._parent_path, self._identifier)

        backdrop = UsdUI.Backdrop.Define(stage, self._created_path)

        node_graph_node = UsdUI.NodeGraphNodeAPI.Apply(backdrop.GetPrim())
        if self._position:
            pos_attr = node_graph_node.CreatePosAttr()
            pos_attr.Set(self._position)
        if self._size:
            size_attr = node_graph_node.CreateSizeAttr()
            size_attr.Set(self._size)
        if self._display_color:
            display_color_attr = node_graph_node.CreateDisplayColorAttr()
            display_color_attr.Set(self._display_color)

    def undo(self):
        delete_cmd = DeletePrimsCommand([self._created_path])
        delete_cmd.do()


class CreateUsdUINoteCommand(omni.kit.commands.Command, UsdStageHelper):
    def __init__(
        self,
        parent_path: Sdf.Path,
        identifier: str,
        position: Optional[Tuple[float]] = None,
        size: Optional[Tuple[float]] = None,
        display_color: Optional[Tuple[float]] = None,
        stage: Optional[Usd.Stage] = None,
    ):
        UsdStageHelper.__init__(self, stage)
        self._created_path = None
        self._parent_path = parent_path
        self._identifier = identifier
        self._position = position
        self._size = size
        self._display_color = display_color

    def do(self):
        stage = self._get_stage()
        self._created_path = get_first_available_path(stage, self._parent_path, self._identifier)

        # This should work either with the Note schema, or just a generic prim
        note = stage.DefinePrim(self._created_path, "OmniNote")

        node_graph_node = UsdUI.NodeGraphNodeAPI.Apply(note.GetPrim())
        if self._position:
            pos_attr = node_graph_node.CreatePosAttr()
            pos_attr.Set(self._position)
        if self._size:
            size_attr = node_graph_node.CreateSizeAttr()
            size_attr.Set(self._size)
        if self._display_color:
            display_color_attr = node_graph_node.CreateDisplayColorAttr()
            display_color_attr.Set(self._display_color)

    def undo(self):
        delete_cmd = DeletePrimsCommand([self._created_path])
        delete_cmd.do()


class UsdUINodeGraphNodeSetCommand(omni.kit.commands.Command, UsdStageHelper):
    """
    Set UsdUINodeGraphNode attribute value.

    Args:
        attribute (str): Name of the UsdUINodeGraphNode attribute to set.
        prim_path (Sdf.Path): Prim path.
        value: Value to change to.
        prev: Value to undo to.
        stage (Usd.Stage): Stage on which to perform the action.
    """

    def __init__(self, attribute: str, prim_path: Sdf.Path, value, prev, stage: Usd.Stage = None):
        UsdStageHelper.__init__(self, stage)
        self._attribute = attribute
        self._value = value
        self._prev = prev
        self._prim_path = prim_path

        self._new_schema = False
        self._new_attribute = False
        self._edit_target = None

    def do(self):
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        if prim.HasAPI(UsdUI.NodeGraphNodeAPI):
            node_graph_node = UsdUI.NodeGraphNodeAPI(prim)
        else:
            node_graph_node = UsdUI.NodeGraphNodeAPI.Apply(prim)
            self._new_schema = True

        mapping = {
            UsdUI.Tokens.uiNodegraphNodePos: (UsdUI.NodeGraphNodeAPI.GetPosAttr, UsdUI.NodeGraphNodeAPI.CreatePosAttr),
            UsdUI.Tokens.uiNodegraphNodeSize: (
                UsdUI.NodeGraphNodeAPI.GetSizeAttr,
                UsdUI.NodeGraphNodeAPI.CreateSizeAttr,
            ),
            UsdUI.Tokens.uiNodegraphNodeDisplayColor: (
                UsdUI.NodeGraphNodeAPI.GetDisplayColorAttr,
                UsdUI.NodeGraphNodeAPI.CreateDisplayColorAttr,
            ),
            UsdUI.Tokens.uiNodegraphNodeExpansionState: (
                UsdUI.NodeGraphNodeAPI.GetExpansionStateAttr,
                UsdUI.NodeGraphNodeAPI.CreateExpansionStateAttr,
            ),
        }

        get_attr, create_attr = mapping.get(self._attribute, (None, None))
        if get_attr and create_attr:
            attribute = get_attr(node_graph_node)
            if not attribute:
                attribute = create_attr(node_graph_node)
                self._new_attribute = True
            elif self._prev is None:
                self._prev = attribute.Get()

            attribute.Set(self._value)

        self._edit_target = stage.GetEditTarget()

    def undo(self):
        stage = self._get_stage()
        if self._new_attribute or self._prev is None:
            with Usd.EditContext(stage, self._edit_target):
                prim = stage.GetPrimAtPath(self._prim_path)
                prim.RemoveProperty(self._attribute)
                if self._new_schema:
                    prim.RemoveAPI(UsdUI.NodeGraphNodeAPI)
        else:
            prim = stage.GetPrimAtPath(self._prim_path)
            node_graph_node = UsdUI.NodeGraphNodeAPI(prim)
            if self._attribute == UsdUI.Tokens.uiNodegraphNodePos:
                pos_attr = node_graph_node.GetPosAttr()
                pos_attr.Set(self._prev)
            elif self._attribute == UsdUI.Tokens.uiNodegraphNodeSize:
                size_attr = node_graph_node.GetSizeAttr()
                size_attr.Set(self._prev)
            elif self._attribute_name == UsdUI.Tokens.uiNodegraphNodeExpansionState:
                expansion_attr = node_graph_node.GetExpansionStateAttr()
                expansion_attr.Set(self._prev_value)


class UsdUIRemovePositionCommand(omni.kit.commands.Command, UsdStageHelper):
    """
    Remove UsdUI position attribute from prim.

    Args:
        prim_path (Sdf.Path): Prim path.
        stage (Usd.Stage): Stage on which to perform the action.
    """

    def __init__(self, prim_path: Sdf.Path, stage: Usd.Stage = None):
        UsdStageHelper.__init__(self, stage)
        self._prim_path = prim_path
        self._edit_target = None
        self._prev = None
        self._affected_specs = []

    def do(self):
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        if not (prim and prim.HasAPI(UsdUI.NodeGraphNodeAPI)):
            return

        node_graph_node = UsdUI.NodeGraphNodeAPI(prim)
        pos_attr = node_graph_node.GetPosAttr()
        if not pos_attr:
            return

        self._prev = pos_attr.Get()
        self._prev_name = pos_attr.GetName()
        self._prev_type_name = pos_attr.GetTypeName()
        self._prev_variability = pos_attr.GetVariability()
        self._prev_is_custom = pos_attr.IsCustom()

        # Remove the position attribute from all the authored SdfPrimSpecs
        self._affected_specs = []
        for prim_spec in prim.GetPrimStack():
            # Check if prim_spec has the position property
            position_path = prim_spec.path.AppendProperty(self._prev_name)
            position_spec = prim_spec.GetPropertyAtPath(position_path)
            if position_spec:
                self._affected_specs += [prim_spec]
                prim_spec.RemoveProperty(position_spec)
        self._edit_target = stage.GetEditTarget()

    def undo(self):
        if not self._affected_specs:
            return

        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        if not (prim and prim.HasAPI(UsdUI.NodeGraphNodeAPI)):
            return

        pos_attr = UsdUI.NodeGraphNodeAPI(prim).GetPosAttr()
        if not pos_attr:
            return

        with Usd.EditContext(stage, self._edit_target):
            for prim_spec in self._affected_specs:
                # add the posisiton property if not exist
                if self._prev_name not in prim_spec.properties:
                    # Creating the AttributeSpec is sufficient to add it to the prim_spec's properties.
                    Sdf.AttributeSpec(
                        prim_spec, self._prev_name, self._prev_type_name, self._prev_variability, self._prev_is_custom
                    )
        # restore the attribute value
        pos_attr.Set(self._prev)
