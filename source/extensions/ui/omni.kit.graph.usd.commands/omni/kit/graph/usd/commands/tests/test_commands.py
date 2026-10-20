## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import omni.kit
import omni.usd
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf, UsdUI


class TestCommands(OmniUiTest):
    async def test_commands(self):
        """Create a backdrop"""
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()

        if stage.HasDefaultPrim():
            root_path = stage.GetDefaultPrim().GetPath()
        else:
            root_path = Sdf.Path.absoluteRootPath

        # create backdrop node
        backdrop_name = "backdrop"
        backdrop_pos_val = (-500, 0)
        omni.kit.commands.execute(
            "CreateUsdUIBackdropCommand", parent_path=root_path, identifier=backdrop_name, position=backdrop_pos_val
        )
        backdrop_path = root_path.AppendChild(backdrop_name)
        backdrop_prim = stage.GetPrimAtPath(backdrop_path)

        # check the stage has the new created backdrop node
        backdrop_prim = stage.GetPrimAtPath(backdrop_path)
        self.assertTrue(backdrop_prim.IsValid())

        # change the size of backdrop
        backdrop_size_val = (250, 300)
        omni.kit.commands.execute(
            "UsdUINodeGraphNodeSetCommand",
            attribute=UsdUI.Tokens.uiNodegraphNodeSize,
            prim_path=backdrop_path,
            value=backdrop_size_val,
            prev=None,
        )

        # check the position and size of the backdrop node
        pos_attr = backdrop_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodePos)
        self.assertEqual(pos_attr.Get(), backdrop_pos_val)
        size_attr = backdrop_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodeSize)
        self.assertEqual(size_attr.Get(), backdrop_size_val)

        # remove the node postition and test UsdUIRemovePositionCommand
        omni.kit.commands.execute("UsdUIRemovePositionCommand", prim_path=backdrop_path)
        pos_attr = backdrop_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodePos)
        self.assertEqual(pos_attr.Get(), None)

        # test UsdUIRemovePositionCommand undo
        omni.kit.commands.execute("Undo")
        pos_attr = backdrop_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodePos)
        self.assertEqual(pos_attr.Get(), backdrop_pos_val)

        # test UsdUINodeGraphNodeSetCommand undo
        omni.kit.commands.execute("Undo")
        size_attr = backdrop_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodeSize)
        self.assertEqual(size_attr.Get(), None)

        # test CreateUsdUIBackdropCommand undo
        omni.kit.commands.execute("Undo")
        backdrop_prim = stage.GetPrimAtPath(backdrop_path)
        self.assertFalse(backdrop_prim.IsValid())

    async def test_note_commands(self):
        """Create a note"""
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()

        if stage.HasDefaultPrim():
            root_path = stage.GetDefaultPrim().GetPath()
        else:
            root_path = Sdf.Path.absoluteRootPath

        # create note node
        note_name = "note"
        note_pos_val = (-500, 0)
        omni.kit.commands.execute(
            "CreateUsdUINoteCommand", parent_path=root_path, identifier=note_name, position=note_pos_val
        )
        note_path = root_path.AppendChild(note_name)
        note_prim = stage.GetPrimAtPath(note_path)

        # check the stage has the new created note node
        note_prim = stage.GetPrimAtPath(note_path)
        self.assertTrue(note_prim.IsValid())

        # change the size of note
        note_size_val = (250, 300)
        omni.kit.commands.execute(
            "UsdUINodeGraphNodeSetCommand",
            attribute=UsdUI.Tokens.uiNodegraphNodeSize,
            prim_path=note_path,
            value=note_size_val,
            prev=None,
        )

        # check the position and size of the note node
        pos_attr = note_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodePos)
        self.assertEqual(pos_attr.Get(), note_pos_val)
        size_attr = note_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodeSize)
        self.assertEqual(size_attr.Get(), note_size_val)

        # remove the node postition and test UsdUIRemovePositionCommand
        omni.kit.commands.execute("UsdUIRemovePositionCommand", prim_path=note_path)
        pos_attr = note_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodePos)
        self.assertEqual(pos_attr.Get(), None)

        # test UsdUIRemovePositionCommand undo
        omni.kit.commands.execute("Undo")
        pos_attr = note_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodePos)
        self.assertEqual(pos_attr.Get(), note_pos_val)

        # test UsdUINodeGraphNodeSetCommand undo
        omni.kit.commands.execute("Undo")
        size_attr = note_prim.GetAttribute(UsdUI.Tokens.uiNodegraphNodeSize)
        self.assertEqual(size_attr.Get(), None)

        # test CreateUsdUINoteCommand undo
        omni.kit.commands.execute("Undo")
        note_prim = stage.GetPrimAtPath(note_path)
        self.assertFalse(note_prim.IsValid())
