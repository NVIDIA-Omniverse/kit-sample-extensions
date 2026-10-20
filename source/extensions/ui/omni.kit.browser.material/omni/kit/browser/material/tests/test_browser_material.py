# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import asyncio
import sys
import unittest
from pathlib import Path
from typing import Optional, Tuple
from unittest.mock import MagicMock

import carb.input
import carb.settings
import omni.kit.app
import omni.kit.commands as cmd
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.kit.undo
import omni.ui as ui
import omni.usd
from omni.kit.test.teamcity import is_running_in_teamcity
from omni.kit.ui_test import Vec2, emulate_mouse_drag_and_drop, emulate_mouse_move, emulate_mouse_move_and_click
from omni.kit.viewport.utility import get_active_viewport_window, get_ui_position_for_prim
from omni.ui.tests.test_base import OmniUiTest
from pxr import UsdShade

from ..model import MaterialDetailItem
from ..window import MaterialBrowserWindow

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


async def wait_for_window(window_name: str):
    MAX_WAIT = 100

    # Find active window
    for _ in range(MAX_WAIT):
        window_root = ui_test.find(f"{window_name}")
        if window_root and window_root.widget.visible:
            await ui_test.human_delay()
            break
        await ui_test.human_delay(1)

    if not window_root:
        raise Exception("Can't find window {window_name}, wait time exceeded.")


def get_prim_viewport_position(prim_path: str):
    viewport_window = get_active_viewport_window()
    (x, y), success = get_ui_position_for_prim(viewport_window, prim_path)
    if success:
        return ui_test.Vec2(x, y)


async def wait_stage_loading(usd_context=omni.usd.get_context()):
    while True:
        _, files_loaded, total_files = usd_context.get_stage_loading_status()
        if files_loaded or total_files:
            await omni.kit.app.get_app().next_update_async()
            continue
        break

    for _ in range(2):
        await omni.kit.app.get_app().next_update_async()


async def open_stage(path: str, usd_context=omni.usd.get_context()):
    await usd_context.open_stage_async(path)
    await wait_stage_loading(usd_context)


class TestMaterialBrowser(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        carb.settings.get_settings().set("/persistent/app/viewport/displayOptions", 0)

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        await omni.usd.get_context().new_stage_async()

        vp_window = ui.Workspace.get_window("Viewport")
        vp_window.undock()
        vp_window.position_x = 0
        vp_window.position_y = 0
        vp_window.width = 800
        vp_window.height = 400

        ui.Workspace.show_window("Material Browser")
        await wait_for_window("Material Browser")

        self._browser = omni.kit.browser.material.get_instance()
        self._window: MaterialBrowserWindow = self._browser._window
        self._window.position_x = 0
        self._window.position_y = 400
        self._window.width = 800
        self._window.height = 200
        self._window.focus()

        for _ in range(4):
            await omni.kit.app.get_app().next_update_async()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    @unittest.skipIf((sys.platform == "linux" and is_running_in_teamcity()), "Golden different")
    async def __test_ui(self):  # pragma: no cover - never called
        await self.docked_test_window(window=self._browser._window, width=1280, height=720)
        await self.__wait_collection_loaded()
        # Wait for thumbnails updated
        await asyncio.sleep(20)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="test_material.png")

    async def test_execution_normal_mdl(self):
        detail_items = await self.__wait_collection_loaded(collection_index=0)
        await omni.kit.app.get_app().next_update_async()
        self._browser._window._browser_model.execute(detail_items[0])
        # Wait for material created
        await self.__wait_material_created(detail_items[0])

        mtl_name = self.__get_material_name(detail_items[0])
        self._verify_material_prim(mtl_name)

    async def test_execution_and_undo_normal_mdl(self):
        detail_items = await self.__wait_collection_loaded(collection_index=0)
        await omni.kit.app.get_app().next_update_async()
        self._browser._window._browser_model.execute(detail_items[0])
        # Wait for material created
        await self.__wait_material_created(detail_items[0])

        mtl_name = self.__get_material_name(detail_items[0])
        self._verify_material_prim(mtl_name)

        omni.kit.undo.undo()
        await self.wait_n_updates(5)
        # Verify that it doesn't exist now
        self._verify_material_prim(mtl_name, exists=False)

    async def test_rt_click_menu(self):
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()
        detail_items = await self.__wait_collection_loaded(collection_index=0)
        await omni.kit.app.get_app().next_update_async()
        # Wait for material created
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        x, y = self.__get_item_position(detail_items[0])
        await emulate_mouse_move_and_click(Vec2(x, y), right_click=True, human_delay_speed=2)
        await emulate_mouse_move_and_click(Vec2(x + 25, y + 35), right_click=False, human_delay_speed=20)

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        mtl_name = self.__get_material_name(detail_items[0])
        self._verify_material_prim(mtl_name)

    async def test_options_menu(self):
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()
        detail_items = await self.__wait_collection_loaded(collection_index=0)
        await omni.kit.app.get_app().next_update_async()
        # Wait for material created
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        # Create a mock for self._thumbnail_manager.put, so we don't have to actually write out to a file
        mock_thumbnail_mgr = MagicMock()
        # Set the return value of the mock to None so it doesn't actually run
        mock_thumbnail_mgr.return_value = None
        # Replace the actual self._thumbnail_manager.put with the mock
        self._window._delegate._thumbnail_manager.put = mock_thumbnail_mgr

        # Select a detail item (if necessary)
        x, y = self.__get_item_position(detail_items[0])
        await emulate_mouse_move_and_click(Vec2(x, y), human_delay_speed=2)
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        mtl_browser_widget = ui_test.find("Material Browser")
        top_y = mtl_browser_widget.position.y
        right_x = mtl_browser_widget.position.x + mtl_browser_widget.size.x

        async def __click_options_menu(menu_text: str) -> bool:
            # Click on Gear icon for options menu
            await emulate_mouse_move_and_click(Vec2(right_x - 18, top_y + 40), human_delay_speed=20)
            for i in range(10):
                await omni.kit.app.get_app().next_update_async()

            option_menu = ui_test.WidgetRef(self._window._widget._options_menu._options_menu, "", self._window)
            option_menu.widget.visible = True
            clicked = await self.__menu_click(option_menu, menu_text)
            if not clicked:
                option_menu.widget.visible = False

        if await __click_options_menu("Generate Thumbnail For Selected"):
            for i in range(10):
                await omni.kit.app.get_app().next_update_async()

            self.assertEqual(mock_thumbnail_mgr.call_count, 1)

        call_count = mock_thumbnail_mgr.call_count
        if await __click_options_menu("Generate Thumbnail For Current Category"):
            for i in range(10):
                await omni.kit.app.get_app().next_update_async()

            # There are 3 detail items, so add 3 to the previous 1
            self.assertEqual(mock_thumbnail_mgr.call_count, call_count + len(detail_items))

        mock_thumbnail_mgr.reset_mock()

    async def test_drag_normal_mdl(self):
        await omni.kit.app.get_app().next_update_async()
        details = await self.__wait_collection_loaded(collection_index=0)

        await self._simulate_drag_drop(details[0])
        await self.__wait_material_created(details[0])
        self._verify_material_prim(self.__get_material_name(details[0]))

    async def test_drag_vmaterial(self):
        # Wait for folder loaded
        details = await self.__wait_collection_loaded(collection_index=1)
        mtl_name = self.__get_material_name(details[0])

        await self._simulate_drag_drop(details[0])
        await self.__wait_material_created(details[0])
        self._verify_material_prim(mtl_name)

    async def test_drag_single_prim(self):
        detail_items = await self.__wait_collection_loaded()
        mtl_name = self.__get_material_name(detail_items[0])

        # load stage with multi-descendent prim
        await open_stage(f"{TEST_DATA_PATH}/stage/multi-material-object-cube-component.usda")
        await wait_stage_loading()

        # test DnD single & multi subid material from Content window to /World/Sphere - Create material & Binding
        stage = omni.usd.get_context().get_stage()
        verify_prim_list = ["/World/Sphere"]
        drag_target = get_prim_viewport_position(verify_prim_list[0])
        x, y = self.__get_item_position(detail_items[0])
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(x, y), drag_target)
        await wait_stage_loading()
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()
        await self.verify_prims_with_material(stage, mtl_name, verify_prim_list)

    async def test_drag_multiple_descendents(self):
        # custom menu find function as menu uses custom class and "/" in menu names & kind_text
        def find_menu_item(query, menu_root, kind):
            import re

            for item in ui.Inspector.get_children(menu_root):
                if isinstance(item, ui.MenuItem) or isinstance(item, ui.Menu):
                    kind_text = item.kind_text if hasattr(item, "kind_text") else ""
                    if kind_text == kind:
                        name = re.sub(r"[^\x00-\x7F]+", " ", item.text).lstrip()
                        if query == name.replace("/", "_"):
                            return item

        details = await self.__wait_collection_loaded()
        material_name = self.__get_material_name(details[0])

        # load stage with multi-descendent prim
        await open_stage(f"{TEST_DATA_PATH}/stage/multi-material-object-cube-component.usda")
        await wait_stage_loading()

        # set pick mode to "All Model Kinds"
        carb.settings.get_settings().set("/persistent/app/viewport/pickingMode", "kind:model.ALL")

        # test drag material to /World/pCube1 - Create material & Binding
        context = omni.usd.get_context()
        stage = context.get_stage()
        multiple_descendents_prim = "/World/pCube1"
        descendents = [
            "/World/pCube1/front1",
            "/World/pCube1/side1",
            "/World/pCube1/back",
            "/World/pCube1/side2",
            "/World/pCube1/top1",
            "/World/pCube1/bottom",
        ]
        drag_target = get_prim_viewport_position(multiple_descendents_prim)

        x, y = self.__get_item_position(details[0])
        for target_prim in descendents:
            await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(x, y), drag_target)
            await wait_stage_loading()

            menu_path = f"_World_pCube1/{target_prim.replace('/', '_')}"
            await ui_test.select_context_menu(
                menu_path, offset=ui_test.Vec2(10, 10), find_fn=lambda q, m: find_menu_item(q, m, "")
            )
            await ui_test.human_delay(10)

            # verify created/bound prims
            await self.verify_prims_with_material(stage, material_name, [target_prim])

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        # Set pick model to "type:ALL" to get selected paths for GeomSubset
        carb.settings.get_settings().set("/persistent/app/viewport/pickingMode", "type:ALL")

        # Get position of detail item that doesn't have anything bound to it
        x, y = self.__get_item_position(details[1])
        await emulate_mouse_move_and_click(Vec2(x, y), right_click=True, human_delay_speed=2)
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()
        await emulate_mouse_move_and_click(Vec2(x + 25, y + 80), right_click=False, human_delay_speed=20)

        # Make sure no prims are selected, because no prims are bound to this mtl
        self.assertListEqual(context.get_selection().get_selected_prim_paths(), [])

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        # Get position of detail item that does have prims bound to it
        x, y = self.__get_item_position(details[0])
        await emulate_mouse_move_and_click(Vec2(x, y), right_click=True, human_delay_speed=2)
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()
        await emulate_mouse_move_and_click(Vec2(x + 25, y + 80), right_click=False, human_delay_speed=20)

        # Make sure the 6 bound prims are selected
        self.assertEqual(len(context.get_selection().get_selected_prim_paths()), 6)

    async def verify_prims_with_material(self, stage, mtl_name, verify_prim_list):
        # verify material
        prim_paths = [p.GetPrimPath().pathString for p in stage.Traverse()]
        self.assertTrue(f"/World/Looks/{mtl_name}" in prim_paths, msg=f"/World/Looks/{mtl_name} not FOUND")
        self.assertTrue(f"/World/Looks/{mtl_name}/Shader" in prim_paths)

        # verify bound material
        if verify_prim_list:
            for prim_path in verify_prim_list:
                prim = stage.GetPrimAtPath(prim_path)
                bound_material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
                self.assertTrue(bound_material.GetPrim().IsValid() == True)
                self.assertTrue(
                    bound_material.GetPrim().GetPrimPath().pathString.startswith(f"/World/Looks/{mtl_name}")
                )

    def _verify_material_prim(self, name: str, exists=True):
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        prim_path = f"/World/Looks/{name}"
        prim = stage.GetPrimAtPath(prim_path)
        if exists:
            self.assertTrue(prim, msg=f"{prim_path} not found!")
            self.assertTrue(prim.IsA(UsdShade.Material))
        else:
            self.assertFalse(prim, msg=f"{prim_path} was found!")

    async def _simulate_drag_drop(self, item: MaterialDetailItem, target_prim: Optional[str] = None):
        x, y = self.__get_item_position(item)
        viewport = ui.Workspace.get_window("Viewport")
        viewport_x, viewport_y = (viewport.position_x + viewport.width / 2, viewport.position_y + viewport.height / 2)
        await emulate_mouse_drag_and_drop(Vec2(x, y), Vec2(viewport_x, viewport_y))

    async def handle_multiple_descendents_dialog(self, stage, prim_path: str, target_prim: str):
        root_prim = stage.GetPrimAtPath(prim_path)
        if not root_prim:  # pragma: no cover
            return

        descendents = omni.usd.get_prim_descendents(root_prim)

        # skip if only root_prim
        if descendents == [root_prim]:  # pragma: no cover
            return

        await wait_for_window("Target prim has multiple descendents")
        await omni.kit.app.get_app().next_update_async()

        # need to select target_prim in combo_widget
        combo_widget = ui_test.find(
            "Target prim has multiple descendents//Frame/**/ComboBox[*].identifier=='multi_descendents_combo'"
        )
        combo_list = combo_widget.model.get_item_children(None)
        combo_index = 0
        for index, item in enumerate(combo_list):
            if item.prim.GetPrimPath().pathString == target_prim:
                combo_index = index

        combo_widget.model.set_current_index(combo_index)
        await ui_test.human_delay()

        ok_widget = ui_test.find(
            "Target prim has multiple descendents//Frame/**/Button[*].identifier=='multi_descendents_ok_button'"
        )
        await ok_widget.click()

        await wait_stage_loading()

    async def test_donot_cast_shadows(self):
        # Create and select a cube
        prim_path = "/cube"
        kwargs = {"prim_type": "Cube", "prim_path": prim_path, "attributes": {"size": 100.0}}

        cmd.execute("CreatePrimWithDefaultXform", **kwargs)
        context = omni.usd.get_context()
        stage = context.get_stage()
        prim = stage.GetPrimAtPath(prim_path)

        async def __test_collection(collection_index):
            context.get_selection().clear_selected_prim_paths()
            await omni.kit.app.get_app().next_update_async()
            context.get_selection().set_selected_prim_paths([prim_path], True)
            # Bind material to cube
            detail_items = await self.__wait_collection_loaded(collection_index=collection_index)

            item = detail_items[0]
            await omni.kit.app.get_app().next_update_async()
            self._browser._window._browser_model.execute(item)
            # Wait for material created
            await self.__wait_material_created(item)

            dirs = item.file.url.split("/")
            folder = dirs[-2]
            folders = carb.settings.get_settings().get("/exts/omni.kit.browser.material/doNotCastShadows/folders")
            if folder not in folders:
                self.assertEqual(collection_index, 0)
                self.assertIsNone(item.donot_cast_shadows)
                attr = prim.GetAttribute("primvars:doNotCastShadows")
                self.assertIsNone(attr.Get())
            else:
                self.assertEqual(collection_index, 1)
                self.assertTrue(item.donot_cast_shadows)
                attr = prim.GetAttribute("primvars:doNotCastShadows")
                self.assertTrue(attr.Get())

        await __test_collection(0)
        await __test_collection(1)

    async def __wait_material_created(self, item: MaterialDetailItem):
        context = omni.usd.get_context()
        stage = context.get_stage()
        prim_path = f"/World/Looks/{item.name}"
        if prim_path.endswith(".mdl"):
            prim_path = prim_path[:-4]
        await self.assertTrueWithRetry(lambda: stage.GetPrimAtPath(prim_path))

    async def __wait_collection_loaded(self, collection_index=0, expand=True):
        browser_widget = self._window._widget._browser_widget
        await omni.kit.app.get_app().next_update_async()
        model = self._window._browser_model
        collections = model.get_item_children(None)
        category_item = model.get_item_children(collections[0])[1 + collection_index]
        browser_widget.category_selection = [category_item]
        while True:
            if hasattr(category_item, "folder") and not category_item.folder.prepared:
                await omni.kit.app.get_app().next_update_async()
            else:
                # Always expand first category
                await omni.kit.app.get_app().next_update_async()
                collections = model.get_item_children(None)
                category_item = model.get_item_children(collections[0])[1 + collection_index]
                if expand:
                    browser_widget._category_view.set_expanded(category_item, True, True)
                await omni.kit.app.get_app().next_update_async()
                return model.get_item_children(category_item)

    def __get_material_name(self, item: MaterialDetailItem) -> str:
        name = item.name
        if name.endswith(".mdl"):
            name = name[:-4]
        return name

    def __get_item_position(self, item: MaterialDetailItem) -> Tuple[float, float]:
        browser_widget = self._window._widget._browser_widget
        frame = browser_widget._detail_view._delegates[item]
        return (frame.screen_position_x + 10, frame.screen_position_y + 10)

    async def __menu_click(self, menu_widget: ui_test.WidgetRef, menu_text: str) -> bool:
        menu_item = menu_widget.find(f"MenuItem[*].text=='{menu_text}'")
        await emulate_mouse_move_and_click(menu_item.center + Vec2(25, 8), human_delay_speed=20)
        return menu_item.widget.enabled
