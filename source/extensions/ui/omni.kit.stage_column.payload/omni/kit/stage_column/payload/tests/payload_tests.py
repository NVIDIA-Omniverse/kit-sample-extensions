# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from unittest import skip

import carb
import omni.kit.test
import omni.ui as ui
import omni.usd
from omni.kit import ui_test
from omni.kit.test_suite.helpers import wait_stage_loading

CURRENT_PATH = Path(__file__).parent.absolute()
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data/tests")


class TestPayload(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        await omni.usd.get_context().open_stage_async(f"{TEST_DATA_PATH}/payload_test.usda")
        await wait_stage_loading()

    async def tearDown(self):
        pass

    # TODO: This kind of function should be added to OmniUiTest, probably
    def _dump_ui_tree(self, frame):
        print("DUMP UI TREE START")
        children = [frame]

        print(str(dir(frame)))

        def recurse(children, path=""):
            for c in children:
                name = path + "/" + type(c).__name__
                print(name)
                if isinstance(c, ui.ComboBox):
                    print(str(dir(c)))

                recurse(ui.Inspector.get_children(c), name)

        recurse(children)
        print("DUMP UI TREE END")

    async def test_payload_column(self):
        stage_window = ui_test.find("Stage")
        await stage_window.focus()

        # show payload column - stage options menu in a ui.TreeView inside a ui.Menu
        await self.toggle_on_named_column("Payload")

        # show all prims in stage window
        stage_tree = ui_test.find("Stage//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        stage_tree.widget.set_expanded(None, True, True)
        await ui_test.human_delay()

        # get list of prims
        stage = omni.usd.get_context().get_stage()
        prim_list_full = [prim.GetPath().pathString for prim in stage.TraverseAll()]

        # w_name = "Stage"
        # self._dump_ui_tree(ui_test.find(f"{w_name}").window.frame)

        # click payload checkbox
        await stage_tree.find_all("**/CheckBox[*]")[0].click()
        await ui_test.human_delay()

        # verify prim list has changed
        prim_list = [prim.GetPath().pathString for prim in stage.TraverseAll()]
        self.assertNotEqual(prim_list_full, prim_list)

        # click payload checkbox
        await stage_tree.find_all("**/CheckBox[*]")[0].click()
        await ui_test.human_delay()

        # verify prim list has changed back
        prim_list = [prim.GetPath().pathString for prim in stage.TraverseAll()]
        self.assertEqual(prim_list_full, prim_list)

    async def toggle_on_named_column(self, column_name: str):
        from omni.kit.ui_test.query import MenuRef

        # Click on the Options hamburger menu
        await ui_test.find("Stage//Frame/**/Button[*].name=='options'").click()
        await ui_test.human_delay(10)

        menu = MenuRef(widget=ui.Menu.get_current(), path="Menu")
        # get treeview
        tree_menu = menu.find("**/TreeView[*]")

        # Find the specified child out of the treeview options and toggle it ON
        for child in tree_menu.widget.model.get_item_children(None):
            if child.name_model.as_string == column_name:
                child.checked_model.as_bool = True

        # click reset to hide menu
        await ui_test.select_context_menu("Reset", offset=ui_test.Vec2(10, 10))
        await ui_test.human_delay(50)

    async def test_shut_down(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.stage_column.payload"
        self.assertTrue(ext_id)
        self.assertTrue(manager.is_extension_enabled(ext_id))

        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertTrue(not manager.is_extension_enabled(ext_id))

        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay()
        self.assertTrue(manager.is_extension_enabled(ext_id))

    async def test_payload_column_multiple(self):
        stage_window = ui_test.find("Stage")
        await stage_window.focus()
        await self.toggle_on_named_column("Payload")

        # get list of prims
        stage = omni.usd.get_context().get_stage()
        prim_list_full = [prim.GetPath().pathString for prim in stage.TraverseAll()]

        # select multiple payloads
        ctx = omni.usd.get_context()
        ctx.get_selection().set_selected_prim_paths(["/World/Cup_0", "/World/Cup_1"], False)

        # click on the check box
        stage_tree = ui_test.find("Stage//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        stage_tree.widget.set_expanded(None, True, True)
        await ui_test.human_delay()
        checkboxes = stage_tree.find_all("**/CheckBox[*]")
        await checkboxes[0].click()
        await ui_test.human_delay()

        # the dialog should show, click yes
        dialog = ui_test.find("Warning")
        self._dump_ui_tree(dialog.window.frame)
        buttons = dialog.find_all("**/Button[*]")
        await buttons[0].click()
        await ui_test.human_delay()

        # verify prim list has changed
        prim_list = [prim.GetPath().pathString for prim in stage.TraverseAll()]
        self.assertNotEqual(prim_list_full, prim_list)

        # click on the check box and verify prim list again
        await checkboxes[0].click()
        await ui_test.human_delay()
        dialog = ui_test.find("Warning")
        self._dump_ui_tree(dialog.window.frame)
        buttons = dialog.find_all("**/Button[*]")
        await buttons[0].click()
        await ui_test.human_delay()
        prim_list = [prim.GetPath().pathString for prim in stage.TraverseAll()]
        self.assertEqual(prim_list_full, prim_list)

    async def test_payload_column_when_prim_expires(self):
        """Test that payload column handles the case when the prim reference held expires."""
        stage_window = ui_test.find("Stage")
        await stage_window.focus()
        await self.toggle_on_named_column("Payload")

        # remove cup 0 asset
        stage_tree = ui_test.find("Stage//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        stage_tree.widget.set_expanded(None, True, True)
        await ui_test.human_delay()
        cup_0 = stage_tree.find("**/Label[*].text=='Cup_0'")
        self.assertIsNotNone(cup_0)
        await cup_0.click()
        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.DEL)
        await ui_test.human_delay()

        # after removal, there should only be one prim and checkbox
        cup_0 = stage_tree.find("**/Label[*].text=='Cup_0'")
        self.assertIsNone(cup_0)
        checkboxes = stage_tree.find_all("**/CheckBox[*]")
        self.assertEqual(1, len(checkboxes))

        # undo the delete, now checkbox should be back to 2 and checked
        await ui_test.emulate_key_combo("Ctrl+Z")
        cup_0 = stage_tree.find("**/Label[*].text=='Cup_0'")
        self.assertIsNotNone(cup_0)
        checkboxes = stage_tree.find_all("**/CheckBox[*]")
        self.assertEqual(2, len(checkboxes))
        # Check checkbox model value to avoid ui-related difference between different versions of kit sdk
        for checkbox in checkboxes:
            self.assertTrue(checkbox.widget.model.get_value_as_bool())
