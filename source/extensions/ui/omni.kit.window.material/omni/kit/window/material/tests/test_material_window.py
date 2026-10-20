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
from pathlib import Path

import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit.test_suite.helpers import select_prims, wait_stage_loading
from omni.ui.tests.test_base import OmniUiTest
from pxr import UsdShade

from ..widgets.new_material_menu import NewMaterialMenu
from ..widgets.panel_mode import PanelModes

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")


class TestMaterialUIWindow(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._opened = False
        test_stage = TEST_DATA_PATH.joinpath("test_material_window_materials.usd")

        def __on_stage_opened(*args):
            self._opened = True

        self._stage = omni.usd.get_context().open_stage_with_callback(str(test_stage), __on_stage_opened)

        while not self._opened:
            await omni.kit.app.get_app().next_update_async()

        self._stage = omni.usd.get_context().get_stage()
        self._browser = omni.kit.window.material.get_instance()
        self._window = self._browser._window

        await self.docked_test_window(window=self._window, width=1280, height=720, block_devices=False)

        # Make search bar has correct width
        self._window.width = 1200
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()
        self._window.width = 1280

        await self.__wait_collection_loaded()

        # Switch to panel scene
        self._ref_window = ui_test.WindowRef(self._window, "")
        ref_radio_current_scene = self._ref_window.find_all(f"**/RadioButton[*].text=='{PanelModes.CURRENT_SCENE}'")[0]
        await omni.kit.app.get_app().next_update_async()
        await ref_radio_current_scene.click()

        self._browser_widget = self._window.browser_widget
        self._prim_delegate = self._browser_widget._stage_widget._detail_view._delegate
        scene_thumbnail_widgets = self.__get_thumbnail_widgets()
        self._thumbnail_item, self._thumbnail = scene_thumbnail_widgets.get("OmniGlass")
        self._ref_thumbnail = ui_test.WidgetRef(self._thumbnail, "", self._window)

    # After running each test
    async def tearDown(self):
        await super().tearDown()

        def __on_stage_closed(*args):
            self._opened = False

        self._stage = omni.usd.get_context().close_stage_with_callback(__on_stage_closed)
        while self._opened:
            await omni.kit.app.get_app().next_update_async()

        self._window = None

    async def wait_five_seconds(self):
        await asyncio.sleep(5)
        # await self.wait_n_updates(5 * 60)

    async def test_panel_changed(self):
        # Switch to panel selected
        ref_radio_selected = self._ref_window.find_all(f"**/RadioButton[*].text=='{PanelModes.SELECTED}'")[0]
        radio_collection = ref_radio_selected.widget.radio_collection
        await ref_radio_selected.click()
        self.assertEqual(radio_collection.model.get_value_as_int(), 2)
        self.assertEqual(self._browser_widget._search_bar.navigation_button.text, "Graph")

        # Open material graph
        ref_navigation_button = ui_test.WidgetRef(
            self._browser_widget._search_bar._show_navigation_button, "", self._window
        )
        await ref_navigation_button.click()
        material_graph_window = ui_test.find("Material Graph")
        self.assertIsNotNone(material_graph_window)
        await self._ref_window.focus()

        # Switch to panel library
        ref_radio_library = self._ref_window.find_all(f"**/RadioButton[*].text=='{PanelModes.LIBRARY}'")[0]
        await ref_radio_library.click()
        self.assertEqual(radio_collection.model.get_value_as_int(), 0)
        self.assertEqual(self._browser_widget._search_bar.navigation_button.text, "Tree")
        await self.finalize_test_no_image()

    async def test_create_material(self):
        scene_thumbnail_widgets = self.__get_thumbnail_widgets()
        _, create_new_thumbnail = scene_thumbnail_widgets.get("Create New")
        ref_create_new_thumbnail = ui_test.WidgetRef(create_new_thumbnail, "", self._window)
        # click and right click opens the same menu
        await ref_create_new_thumbnail.click()
        await ref_create_new_thumbnail.right_click()
        ref_new_material_menu = ui_test.WidgetRef(NewMaterialMenu.get_instance()._menu, "", self._window)
        ref_create_material_menu = ref_new_material_menu.find(f"MenuItem[*].text=='USD Preview Surface Texture'")
        await ui_test.emulate_mouse_move_and_click(ref_create_material_menu.center)
        await asyncio.sleep(1)
        scene_thumbnail_widgets = self.__get_thumbnail_widgets()
        self.assertIn("PreviewSurfaceTexture", scene_thumbnail_widgets)
        await self.finalize_test_no_image()

    async def test_material_selection_and_preview(self):
        await self._ref_thumbnail.click()
        self.assertFalse(self._prim_delegate._hover_container[self._thumbnail_item].selected)
        ref_open_preview = ui_test.WidgetRef(self._prim_delegate._mark_triangle[self._thumbnail_item], "", self._window)
        await ref_open_preview.click()
        # Cannot accurately test visiblity of self._browser_widget._preview_widget._image._loading_label.visible
        # as ui build adds rendr->ImageProvide subscription, and a render may have been delivered before next line is run
        # self.assertTrue(self._browser_widget._preview_widget._image._loading_label.visible)
        ref_preview_widget_container = ui_test.WidgetRef(
            self._browser_widget._preview_widget._container, "", self._window
        )
        await self.wait_five_seconds()
        self.assertFalse(self._browser_widget._preview_widget._image._loading_label.visible)
        ref_close_preview = ref_preview_widget_container.find("**/Triangle[*].name=='hovered'")
        await ref_close_preview.click()
        await self.finalize_test_no_image()

    async def test_context_menu_and_drag(self):
        # Create and select the cube
        cube_path = "/World/Cube01"
        self._stage.DefinePrim(cube_path, "Cube")
        await select_prims([cube_path])
        await wait_stage_loading()
        await self._ref_thumbnail.right_click()
        ref_prim_menu = ui_test.WidgetRef(self._prim_delegate._context_menu, "", self._window)
        ref_assign = ref_prim_menu.find("MenuItem[*].text=='Assign to Selection'")
        await ui_test.emulate_mouse_move_and_click(ref_assign.center)
        # Verify binding
        bound_material, _ = UsdShade.MaterialBindingAPI(self._stage.GetPrimAtPath(cube_path)).ComputeBoundMaterial()
        self.assertTrue(bound_material.GetPrim().IsValid() == True)
        self.assertEqual(bound_material.GetPrim().GetPrimPath().pathString, f"/World/Looks/OmniGlass")

        # Test capture thumbnail
        await self._ref_thumbnail.right_click()
        ref_capture = ref_prim_menu.find("MenuItem[*].text=='Capture thumbnail'")
        await ui_test.emulate_mouse_move_and_click(ref_capture.center)
        # In CaptureThumbnailGenerator.capture_async we wait for 3 seconds
        await self.wait_five_seconds()
        self.assertTrue(self._prim_delegate._capture_thumbnails[self._thumbnail_item].visible)

        # Test duplicate
        await self._ref_thumbnail.right_click()
        ref_duplicate = ref_prim_menu.find("MenuItem[*].text=='Duplicate'")
        await ui_test.emulate_mouse_move_and_click(ref_duplicate.center)
        await asyncio.sleep(1)
        scene_thumbnail_widgets = self.__get_thumbnail_widgets()
        self.assertIn("OmniGlass_01", scene_thumbnail_widgets)

        # Test drag
        self.assertEqual(self._prim_delegate.on_drag(self._thumbnail_item), self._thumbnail_item.url)
        await self.finalize_test_no_image()

    async def __wait_collection_loaded(self, collection_index=0):
        browser_widget = self._window._widget._browser_widget
        browser_widget.collection_index = collection_index
        await omni.kit.app.get_app().next_update_async()
        model = self._window.browser_model
        collections = model.get_item_children(None)
        categories = model.get_item_children(collections[collection_index])
        browser_widget.category_selection = [categories[1]]
        while True:
            for category in categories:
                if hasattr(category, "folder") and not category.folder.prepared:
                    await omni.kit.app.get_app().next_update_async()
                    break
            else:
                # Always expand first category
                await omni.kit.app.get_app().next_update_async()
                collections = model.get_item_children(None)
                categories = model.get_item_children(collections[collection_index])
                browser_widget._category_view.set_expanded(categories[1], True, True)
                await omni.kit.app.get_app().next_update_async()
                return model.get_item_children(categories[1])

    # Cached thumbnail widgets can contain duplicates due to not being hashed and compared
    # by default operators
    def __get_thumbnail_widgets(self):
        d = self._prim_delegate._cached_thumbnail_widgets
        result = {}
        for item, widget in d.items():
            result[item.name] = (item, widget)
        return result
