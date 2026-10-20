# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.actions.core
import omni.kit.app
import omni.kit.commands
import omni.kit.test
import omni.kit.undo
import omni.usd
from pxr import UsdGeom

from ..commands.create_commands import getStageDefaultPrimPath
from ..prims.valid import valid_ui_prim_types

CURRENT_PATH = Path(__file__).parent.joinpath("data").absolute().resolve()

registry = omni.kit.actions.core.get_action_registry()


class TestData2UIUsdActions(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()

    async def test_create_each_prim_actions(self):
        frame_action = registry.get_action("omni.kit.data2ui.usd", "create_ui_prim_frame")
        stage = omni.usd.get_context().get_stage()
        default_prim_path = getStageDefaultPrimPath(stage)

        def check_exist(prim_type):
            if "Style" in prim_type:
                prim = stage.GetPrimAtPath(default_prim_path.AppendChild("Styles").AppendChild(f"{prim_type}"))
            elif "Viewport" in prim_type:
                prim = stage.GetPrimAtPath(default_prim_path.AppendChild("Viewport").AppendChild(f"{prim_type}"))
            else:
                prim = stage.GetPrimAtPath(
                    default_prim_path.AppendChild("UI").AppendChild("Frame").AppendChild(f"{prim_type}")
                )

            self.assertTrue(prim)
            self.assertFalse(prim.IsA(UsdGeom.Mesh))
            self.assertFalse(prim.IsA(UsdGeom.Xformable))

        def check_does_not_exist(prim_type):
            self.assertFalse(
                stage.GetPrimAtPath(
                    default_prim_path.AppendChild("UI").AppendChild("Frame").AppendChild(f"{prim_type}")
                )
            )

        for prim_type in valid_ui_prim_types:
            frame_action.execute()
            prim_action_name = f"create_ui_prim_{prim_type.lower()}"
            prim_action = registry.get_action("omni.kit.data2ui.usd", prim_action_name)
            prim_action.execute()
            await omni.kit.app.get_app().next_update_async()
            check_exist(prim_type)
            omni.kit.undo.undo()
            omni.kit.undo.undo()
            await omni.kit.app.get_app().next_update_async()
            check_does_not_exist(prim_type)
            omni.kit.undo.redo()
            omni.kit.undo.redo()
            await omni.kit.app.get_app().next_update_async()
            check_exist(prim_type)
            omni.kit.undo.undo()
            omni.kit.undo.undo()

    async def test_reorder_ui_prims_actions(self):
        context = omni.usd.get_context()
        stage = context.get_stage()
        default_prim_path = getStageDefaultPrimPath(stage)
        selection = context.get_selection()
        b0, b1, b2, b3 = (
            f"{default_prim_path}UI/Frame/VStack/Button",
            f"{default_prim_path}UI/Frame/VStack/Button_01",
            f"{default_prim_path}UI/Frame/VStack/Button_02",
            f"{default_prim_path}UI/Frame/VStack/Button_03",
        )

        frame_action = registry.get_action("omni.kit.data2ui.usd", "create_ui_prim_frame")
        vstack_action = registry.get_action("omni.kit.data2ui.usd", "create_ui_prim_vstack")
        button_action = registry.get_action("omni.kit.data2ui.usd", "create_ui_prim_button")
        up_action = registry.get_action("omni.kit.data2ui.usd", "reorder_ui_prims_up")
        down_action = registry.get_action("omni.kit.data2ui.usd", "reorder_ui_prims_down")
        frame_action.execute()
        await omni.kit.app.get_app().next_update_async()
        selection.set_selected_prim_paths([f"{default_prim_path}UI/Frame"], True)
        vstack_action.execute()
        await omni.kit.app.get_app().next_update_async()
        selection.set_selected_prim_paths([f"{default_prim_path}UI/Frame/VStack"], True)
        button_action.execute()
        await omni.kit.app.get_app().next_update_async()
        button_action.execute()
        await omni.kit.app.get_app().next_update_async()
        button_action.execute()
        await omni.kit.app.get_app().next_update_async()
        button_action.execute()
        await omni.kit.app.get_app().next_update_async()

        selection = context.get_selection()
        selection.set_selected_prim_paths([], True)

        parent = stage.GetPrimAtPath(f"{default_prim_path}UI/Frame/VStack")
        # self.assertListEqual([], parent.GetChildren())
        child_order = [c.GetPath() for c in parent.GetChildren()]
        self.assertListEqual(
            [b0, b1, b2, b3],
            child_order,
        )

        selection.set_selected_prim_paths([b1, b3], True)
        up_action.execute()
        await omni.kit.app.get_app().next_update_async()
        child_order = [c.GetPath() for c in parent.GetChildren()]
        self.assertListEqual(
            [b1, b0, b3, b2],
            child_order,
        )

        up_action.execute()
        await omni.kit.app.get_app().next_update_async()
        child_order = [c.GetPath() for c in parent.GetChildren()]
        self.assertListEqual(
            [b1, b3, b0, b2],
            child_order,
        )

        selection.set_selected_prim_paths([b1, b3, b0], True)
        down_action.execute()
        await omni.kit.app.get_app().next_update_async()
        child_order = [c.GetPath() for c in parent.GetChildren()]
        self.assertListEqual(
            [b2, b1, b3, b0],
            child_order,
        )
