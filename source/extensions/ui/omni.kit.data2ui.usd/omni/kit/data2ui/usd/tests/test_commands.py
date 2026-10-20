# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.app
import omni.kit.commands
import omni.kit.test
import omni.kit.undo
import omni.usd
from pxr import UsdGeom

from ..commands.create_commands import getStageDefaultPrimPath
from ..prims.valid import valid_ui_prim_types

CURRENT_PATH = Path(__file__).parent.joinpath("data").absolute().resolve()


class TestData2UIUsdCommands(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()  # type: ignore

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()  # type: ignore

    async def test_create_prim_command(self):
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Frame")
        stage = omni.usd.get_context().get_stage()  # type: ignore
        default_prim_path = getStageDefaultPrimPath(stage)

        def check_exist():
            prim = stage.GetPrimAtPath(default_prim_path.AppendChild("UI").AppendChild("Frame"))
            self.assertTrue(prim)
            self.assertFalse(prim.IsA(UsdGeom.Mesh))
            self.assertFalse(prim.IsA(UsdGeom.Xformable))

        def check_does_not_exist():
            self.assertFalse(stage.GetPrimAtPath(default_prim_path.AppendChild("UI").AppendChild("Frame")))

        check_exist()

        # give hydra a frame before deleting to catch up so it doesn't spew coding error about not finding prim
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        omni.kit.undo.undo()
        check_does_not_exist()
        omni.kit.undo.redo()
        check_exist()
        omni.kit.undo.undo()
        check_does_not_exist()

    async def test_create_each_valid_prim_at_path_commands(self):
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Frame")

        stage = omni.usd.get_context().get_stage()  # type: ignore
        default_prim_path = getStageDefaultPrimPath(stage)

        def check_exist(prim_path):
            prim = stage.GetPrimAtPath(prim_path)
            self.assertTrue(prim)
            self.assertFalse(prim.IsA(UsdGeom.Mesh))
            self.assertFalse(prim.IsA(UsdGeom.Xformable))

        def check_does_not_exist(prim_path):
            self.assertFalse(stage.GetPrimAtPath(prim_path))

        for child in valid_ui_prim_types:
            prim_path = default_prim_path.AppendChild("UI").AppendChild("Frame").AppendChild(f"{child}")
            omni.kit.commands.execute("CreateUIPrimCommand", prim_type=child, prim_path=prim_path)
            check_exist(prim_path)
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            omni.kit.undo.undo()
            check_does_not_exist(prim_path)
            omni.kit.undo.redo()
            check_exist(prim_path)
            omni.kit.undo.undo()
            check_does_not_exist(prim_path)

    async def test_reorder_ui_prims_commands(self):
        context = omni.usd.get_context()
        stage = context.get_stage()  # type: ignore
        b1, b2, b3, b4 = (
            "/World/UI/Frame/VStack/Button1",
            "/World/UI/Frame/VStack/Button2",
            "/World/UI/Frame/VStack/Button3",
            "/World/UI/Frame/VStack/Button4",
        )
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Frame", prim_path="/World/UI/Frame")
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="VStack", prim_path="/World/UI/Frame/VStack")
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Button", prim_path=b1)
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Button", prim_path=b2)
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Button", prim_path=b3)
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Button", prim_path=b4)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

        selection = context.get_selection()
        selection.set_selected_prim_paths([], True)
        self.assertListEqual(selection.get_selected_prim_paths(), [])

        parent = stage.GetPrimAtPath("/World/UI/Frame/VStack")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        child_order = [c.GetPath() for c in parent.GetChildren()]
        self.assertListEqual(
            [b1, b2, b3, b4],
            child_order,
        )

        selection.set_selected_prim_paths([b2, b4], True)
        omni.kit.commands.execute("ReorderUIPrimsCommand", direction="Up")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        child_order = [c.GetPath() for c in parent.GetChildren()]
        self.assertListEqual(
            [b2, b1, b4, b3],
            child_order,
        )

        omni.kit.commands.execute("ReorderUIPrimsCommand", direction="Up")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        child_order = [c.GetPath() for c in parent.GetChildren()]
        self.assertListEqual(
            [b2, b4, b1, b3],
            child_order,
        )

        selection.set_selected_prim_paths([b2, b4, b1], True)
        omni.kit.commands.execute("ReorderUIPrimsCommand", direction="Down")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        child_order = [c.GetPath() for c in parent.GetChildren()]
        self.assertListEqual(
            [b3, b2, b4, b1],
            child_order,
        )

    async def test_parent_to_viewport(self):
        success, _ = omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Frame", prim_path="/World/UI/Frame")
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success, _ = omni.kit.commands.execute("ParentToViewportCommand", prim_path="/World/UI/Frame")
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success = omni.kit.undo.undo()
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def test_parent_to_viewport2(self):
        context = omni.usd.get_context()
        stage = context.get_stage()  # type: ignore
        selection = context.get_selection()
        selection.set_selected_prim_paths([], True)
        success, _ = omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Frame", prim_path="/World/UI/Frame")
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        selection.set_selected_prim_paths(["/World/UI/Frame"], True)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success, _ = omni.kit.commands.execute("ParentToViewportCommand")
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success = omni.kit.undo.undo()
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def test_remove_from_viewport(self):
        success, _ = omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Frame", prim_path="/World/UI/Frame")
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success, _ = omni.kit.commands.execute("ParentToViewportCommand", prim_path="/World/UI/Frame")
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success, _ = omni.kit.commands.execute("RemoveViewportPrim")
        self.assertTrue(success)

    async def test_create_viewport_frame(self):
        success, _ = omni.kit.commands.execute("CreateViewportUIFrame")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())

    async def test_create_window_frame(self):
        success, _ = omni.kit.commands.execute("CreateWindowUIFrame")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())
