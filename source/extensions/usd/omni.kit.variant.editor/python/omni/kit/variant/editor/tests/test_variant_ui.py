# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import os
import pathlib

import carb.input
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.kit.undo
import omni.kit.variant.editor
import omni.ui as ui
import omni.usd
from omni.kit.variant.editor.core import VariantEditorCore
from omni.kit.window.content_browser.test_helper import ContentBrowserTestHelper
from omni.kit.window.file_importer.test_helper import FileImporterTestHelper
from omni.ui.tests.test_base import OmniUiTest

from ..extension import get_window
from .test_cleanup import reset_variant_editor_test_state

WINDOW_SIZE = 1024

ADD_PRIM_BUTTON = "Variant Editor//Frame/**/Button[*].text=='Add Prim'"
ADD_PROP_BUTTON = "Variant Editor//Frame/**/TreeView[0]/HStack[0]/**/Button[0].text=='Add Property'"
ADD_REL_TARGET_BUTTON = (
    "Variant Editor//Frame/**/Button[*].identifier=='sdf_relationship_array_proxyPrim.add_relationships'"
)
LAYER_PATH_FIELD = "Variant Editor//Frame/**/StringField[*].name=='layer_path'"


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test
class UITest(OmniUiTest):
    # SET-UP AND UTILITY
    async def click_fresh(self, path, right_click=False):
        """Look up a widget and click it in one step.

        The variant editor rebuilds its tree view after every edit, and the pickers
        rebuild their window on every open, so a WidgetRef held across an action goes
        stale: the click then lands on nothing, or on whatever now occupies that
        screen position. Always re-query immediately before clicking.

        The lookup retries across frames: a click only yields a handful of frames, which
        is not always enough for a picker to finish populating, and ui_test.find()
        reports "not there yet" by returning None rather than raising.
        """
        widget = await ui_test.find_with_retry(path)
        self.assertIsNotNone(widget, f"Can't find any widget at path: {path}")
        await widget.click(right_click=right_click)
        return widget

    async def find_all_when_count_is(self, path, count, max_frames=100):
        """Wait for a widget query to settle on an expected number of matches.

        Reference and payload rows appear at the end of an asynchronous chain: the pick
        dialog resolves its asset path in a task, the model authors the composition arc,
        and only then does the tree rebuild. A fixed delay races that chain -- find_all()
        then returns the rows built so far, which is how test_variant_content failed
        intermittently with "1 != 2" (OMPE-89478).

        Polls per frame and returns as soon as the count matches, so the settled case
        costs a frame rather than the whole budget. On timeout, asserts with the count
        actually found, which points at the step that never landed instead of at a later
        subscript raising IndexError.
        """
        for _ in range(max_frames):
            widgets = ui_test.find_all(path)
            if len(widgets) == count:
                return widgets
            await ui_test.wait_n_updates(1)

        widgets = ui_test.find_all(path)
        self.assertEqual(
            len(widgets),
            count,
            f"expected {count} widget(s) at path {path} within {max_frames} frames, found {len(widgets)}",
        )
        return widgets

    def assert_single_picker_window(self, title):
        """Assert a picker did not leave same-titled windows behind when it reopened.

        omni.ui_query resolves a window by title and, when several match, falls back to
        the first visible one -- so leaked pickers silently misdirect later lookups
        instead of failing outright. Pins the window teardown in picker.py/prop_selector.py.
        """
        windows = [w for w in ui.Workspace.get_windows() if isinstance(w, ui.Window) and w.title == title]
        self.assertEqual(len(windows), 1, f"expected exactly one {title!r} window, found {len(windows)}")

    async def setUp(self):
        await super().setUp()
        from omni.kit.variant.editor.extension import TEST_DATA_PATH

        self._usd_path = TEST_DATA_PATH.absolute()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

    async def tearDown(self):
        await reset_variant_editor_test_state()
        await super().tearDown()

    async def bootstrap_stage(self, stage_path):
        test_file_path = self._usd_path.joinpath(stage_path).absolute()
        await omni.usd.get_context().open_stage_async(str(test_file_path))
        await omni.kit.app.get_app().next_update_async()

    # TESTS

    async def capture_golden_image(self, filename):
        import omni.renderer_capture

        capture_next_frame = omni.renderer_capture.acquire_renderer_capture_interface().capture_next_frame_swapchain
        wait_async_capture = omni.renderer_capture.acquire_renderer_capture_interface().wait_async_capture

        capture_next_frame(str(self._golden_img_dir.joinpath(filename)))

        await omni.kit.app.get_app().next_update_async()

        wait_async_capture()

    async def test_empty_window(self):
        await self.bootstrap_stage("test_core.usda")

        get_window().show()
        await self.docked_test_window(window=get_window()._window, width=WINDOW_SIZE, height=WINDOW_SIZE)

        # Adding in 4 delays so the UI has time to load
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        # This is here to update the golden image.  NEVER CHECK IN WITH THE FOLLOWING LINE UNCOMMENTED
        # await self.capture_golden_image("test_window_empty.png")

        await self.finalize_test(
            threshold=120,
            use_log=True,
            golden_img_dir=self._golden_img_dir,
            golden_img_name="test_window_empty.png",
        )

    async def test_populated_window(self):
        await self.bootstrap_stage("test_core.usda")

        get_window().show()
        await self.docked_test_window(window=get_window()._window, width=WINDOW_SIZE, height=WINDOW_SIZE)

        variant_items = get_window()._variant_tree_view.model.get_item_children()[0].children

        get_window()._variant_tree_view.model.select_variant(variant_items[0])

        # Adding in 4 delays so the UI has time to load
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        # This is here to update the golden image.  NEVER CHECK IN WITH THE FOLLOWING LINE UNCOMMENTED
        # await self.capture_golden_image("test_window_populated.png")

        await self.finalize_test(
            threshold=120,
            use_log=True,
            golden_img_dir=self._golden_img_dir,
            golden_img_name="test_window_populated.png",
        )

    async def test_variant_tree(self):
        # Tests basic operations of variant set and variant. Use different images for undo and redo to avoid tooltip difference.
        prop_window = ui_test.find("Property")
        prop_window.window.visible = False

        await self.bootstrap_stage("test_core.usda")

        get_window().hide()  # Hide first to avoid failure caused by CoreTest.test_get_variant_specs()
        get_window().show()

        await self.docked_test_window(
            window=get_window()._window,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            block_devices=False,
        )

        # Add variant set
        add_variant_set_bn = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add New Variant Set'")
        await add_variant_set_bn.click()
        golden_img_dir = (
            pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "tests" / "golden_img"
        )
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_add_variant_set.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_org_variant_tree.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.redo()
        await asyncio.sleep(1)
        await self.capture_and_compare(
            golden_img_name="test_redo_add_variant_set.png",
            golden_img_dir=golden_img_dir,
        )

        # Remove variant set
        variant_set_widget = ui_test.find(
            "Variant Editor//Frame/**/TreeView[*]/VStack[*]/**/Label[*].text=='TestChildren'"
        )
        await variant_set_widget.right_click()
        await ui_test.select_context_menu("Delete Variant Set")
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_remove_variant_set.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_undo_remove_variant_set.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_redo_remove_variant_set.png",
            golden_img_dir=golden_img_dir,
        )

        # Rename variant set. The row can't be re-queried by label text between the
        # attempts: renaming replaces the Label with a StringField, and the first
        # attempt actually renames the set (invalid characters are sanitised to
        # underscores) rather than being rejected. The row itself never moves, so
        # capture its position once and drive the whole sequence by coordinate.
        variant_set_row = ui_test.find("Variant Editor//Frame/**/TreeView[*]/VStack[*]/**/Label[*].text=='TestDummy'")
        self.assertIsNotNone(variant_set_row)
        variant_set_pos = variant_set_row.center
        await ui_test.emulate_mouse_move_and_click(variant_set_pos, right_click=True)
        await ui_test.select_context_menu("Rename Variant Set")
        await ui_test.emulate_char_press("TestDummyNew*^^^(*&^(&^()))")
        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)
        await asyncio.sleep(5)
        await self.capture_and_compare(
            golden_img_name="test_rename_variant_set_bad_name.png",
            golden_img_dir=golden_img_dir,
        )
        omni.kit.undo.undo()

        await ui_test.emulate_mouse_move_and_click(variant_set_pos, right_click=True)
        await ui_test.select_context_menu("Rename Variant Set")
        await ui_test.emulate_char_press("Variant_Set")
        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)
        await asyncio.sleep(5)
        await self.capture_and_compare(
            golden_img_name="test_rename_variant_set_duplicated_name.png",
            golden_img_dir=golden_img_dir,
        )

        await ui_test.emulate_mouse_move_and_click(variant_set_pos, right_click=True)
        await ui_test.select_context_menu("Rename Variant Set")
        await ui_test.emulate_mouse_move_and_click(variant_set_pos)
        await ui_test.emulate_mouse_move_and_click(variant_set_pos, double=True)  # Select all text in the box
        await ui_test.emulate_char_press("TestDummyNew")
        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)
        await ui_test.emulate_mouse_move(ui_test.Vec2(0, 0))  # Moves mouse away to remove tooltip
        await asyncio.sleep(5)
        await self.capture_and_compare(golden_img_name="test_rename_variant_set.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_undo_rename_variant_set.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_rename_variant_set.png", golden_img_dir=golden_img_dir)

        # Select variant
        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Dummy1'")
        await variant_widget.click()
        await self.capture_and_compare(golden_img_name="test_select_variant.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_undo_select_variant.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_select_variant.png", golden_img_dir=golden_img_dir)

        # Clear variant selection
        await ui_test.emulate_mouse_move_and_click(variant_set_pos, right_click=True)
        await ui_test.select_context_menu("Clear Variant Selection")
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_clear_variant_selection.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_undo_clear_variant_selection.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_clear_variant_selection.png",
            golden_img_dir=golden_img_dir,
        )

        # Copy Variant to All
        await self.bootstrap_stage("test_core.usda")

        variant1 = "Variant Editor//Frame/**/TreeView[0]/HStack[*]/**/Label[*].text=='TestChildren'"
        variant2 = "Variant Editor//Frame/**/TreeView[0]/HStack[*]/**/Label[*].text=='TestChildren_1'"
        await self.click_fresh(variant1)
        await self.click_fresh(variant2)
        await self.click_fresh(variant2, right_click=True)
        await ui_test.select_context_menu("Copy Properties to All in Set")
        await self.click_fresh(variant1)  # the copy rebuilt the tree, so re-query
        await omni.kit.app.get_app().next_update_async()
        widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='xformOp:rotateXYZ'")
        self.assertTrue(widget)

        omni.kit.undo.undo()
        omni.kit.undo.undo()
        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='xformOp:rotateXYZ'")
        self.assertFalse(widget)

        omni.kit.undo.redo()
        omni.kit.undo.redo()
        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='xformOp:rotateXYZ'")
        self.assertTrue(widget)

        # Remove variant
        await self.bootstrap_stage("test_core.usda")

        variant_widget = ui_test.find("Variant Editor//Frame/**/TreeView[0]/HStack[*]/**/Label[*].text=='TestChildren'")
        await variant_widget.right_click()
        await ui_test.select_context_menu("Remove Variant")
        await asyncio.sleep(5)
        await self.capture_and_compare(golden_img_name="test_remove_variant.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await asyncio.sleep(5)
        await self.capture_and_compare(
            golden_img_name="test_undo_remove_variant.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        await asyncio.sleep(5)
        await self.capture_and_compare(golden_img_name="test_remove_variant.png", golden_img_dir=golden_img_dir)

        # Rename variant
        variant_widget = ui_test.find("Variant Editor//Frame/**/TreeView[0]/HStack[*]/**/Label[*].text=='Dummy1'")
        await variant_widget.right_click()
        await ui_test.select_context_menu("Rename Variant")
        await ui_test.emulate_char_press("Dummy2")
        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)
        await asyncio.sleep(5)
        await self.capture_and_compare(
            golden_img_name="test_rename_variant_duplicated_name.png",
            golden_img_dir=golden_img_dir,
        )

        await variant_widget.right_click()
        await ui_test.select_context_menu("Rename Variant")
        await ui_test.emulate_char_press("Dummy&^&(*^(*&))")
        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)
        await asyncio.sleep(5)  # Wait for message bubble to disappear
        await self.capture_and_compare(
            golden_img_name="test_rename_variant_bad_name.png",
            golden_img_dir=golden_img_dir,
        )
        omni.kit.undo.undo()

        variant_widget = ui_test.find(
            "Variant Editor//Frame/**/TreeView[0]/HStack[*]/**/Label[*].text=='TestChildren_1'"
        )
        await variant_widget.right_click()
        await ui_test.select_context_menu("Rename Variant")
        await ui_test.emulate_char_press("TestChildrenNew")
        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_rename_variant.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_undo_rename_variant.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_rename_variant.png", golden_img_dir=golden_img_dir)

        # Duplicate variant
        renamed_variant = "Variant Editor//Frame/**/TreeView[0]/HStack[*]/**/Label[*].text=='TestChildrenNew'"
        await self.click_fresh(renamed_variant, right_click=True)
        await ui_test.select_context_menu("Duplicate Variant")
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_duplicate_variant.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_undo_duplicate_variant.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_duplicate_variant.png", golden_img_dir=golden_img_dir)

        # Select and clear selection
        await self.click_fresh(renamed_variant)  # undo/redo above rebuilt the tree
        await self.click_fresh(renamed_variant, right_click=True)
        await ui_test.select_context_menu("Clear Selection")
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_clear_selection.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertTrue(asset_path_widget)
        self.assertEqual(
            os.path.basename(asset_path_widget.model.get_value_as_string()),
            "Rock_Small_01.usd",
        )

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_clear_selection.png", golden_img_dir=golden_img_dir)

        # Add variant
        add_variant_button = ui_test.find("Variant Editor//Frame/**/TreeView[*]/VStack[1]/**/Button[*]")
        await add_variant_button.click()
        await self.wait_n_updates()
        await self.capture_and_compare(golden_img_name="test_add_variant.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await self.wait_n_updates()
        await self.capture_and_compare(golden_img_name="test_undo_add_variant.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.redo()
        await self.wait_n_updates()
        await self.capture_and_compare(golden_img_name="test_add_variant.png", golden_img_dir=golden_img_dir)

        # Asset drag and drop
        # Docking doesn't work. So we manullay layout windows
        get_window()._window.height = WINDOW_SIZE / 2
        content_window = ui_test.find("Content").window
        content_window.position_x = get_window()._window.position_x
        content_window.position_y = get_window()._window.position_x + get_window()._window.height
        content_window.width = get_window()._window.width
        content_window.height = WINDOW_SIZE - get_window()._window.height

        await self.bootstrap_stage("test_core.usda")

        drag_target = ui_test.Vec2(100, 200)  # Somewhere in left variant tree pannel
        asset_folder = pathlib.Path(golden_img_dir).parent
        content_test_helper = ContentBrowserTestHelper()
        await content_test_helper.drag_and_drop_tree_view(
            str(asset_folder),
            ["Rock_Small_01.usd", "Rock_Small_02.usd", "Rock_Small_03.usd"],
            drag_target,
            focus_treeview_items=False,
        )

        await self.docked_test_window(
            window=get_window()._window,
            width=get_window()._window.width,
            height=get_window()._window.height,
            block_devices=False,
        )
        await asyncio.sleep(4)
        await self.capture_and_compare(
            golden_img_name="test_drag_and_drop_visiblility.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.undo()
        await asyncio.sleep(4)
        await self.capture_and_compare(
            golden_img_name="test_undo_drag_and_drop_visiblility.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        await asyncio.sleep(1)
        await self.capture_and_compare(
            golden_img_name="test_redo_drag_and_drop_visiblility.png",
            golden_img_dir=golden_img_dir,
        )

        await self.finalize_test_no_image()

        await self.bootstrap_stage("test_core.usda")

        option_button = ui_test.find("Variant Editor//Frame/**/HStack[*]/Button[*]")
        await option_button.click()
        await ui_test.select_context_menu("Drag and Drop Mode - Visibility")
        await content_test_helper.drag_and_drop_tree_view(
            str(asset_folder),
            ["Rock_Small_01.usd", "Rock_Small_02.usd", "Rock_Small_03.usd"],
            drag_target,
            focus_treeview_items=False,
        )
        await omni.kit.app.get_app().next_update_async()

        await self.docked_test_window(
            window=get_window()._window,
            width=get_window()._window.width,
            height=get_window()._window.height,
            block_devices=False,
        )

        threshold = 0.35  # Payload paths are different in different enviroment. So we allow some differences.

        await omni.kit.app.get_app().next_update_async()
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertTrue(asset_path_widget)
        self.assertEqual(
            os.path.basename(asset_path_widget.model.get_value_as_string()),
            "Rock_Small_03.usd",
        )

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertFalse(asset_path_widget)

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertTrue(asset_path_widget)
        self.assertEqual(
            os.path.basename(asset_path_widget.model.get_value_as_string()),
            "Rock_Small_03.usd",
        )

        await self.finalize_test_no_image()

    async def test_variant_content(self):
        await self.bootstrap_stage("test_core.usda")

        get_window().hide()  # Hide first to avoid failure caused by CoreTest.test_get_variant_specs()
        get_window().show()

        await self.docked_test_window(
            window=get_window()._window,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            block_devices=False,
        )

        # Select prims
        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Dummy1'")
        await variant_widget.click()

        async def add_prim(prim_name):
            await self.click_fresh(ADD_PRIM_BUTTON)
            self.assert_single_picker_window("Select Prims")
            select_prims_window = get_window()._picker_button._StageWindowButton__window
            select_prims_window.position_y = 0
            select_prims_window.height = WINDOW_SIZE
            await self.click_fresh(f"Select Prims//Frame/**/Label[*].text=='{prim_name}'")
            await self.click_fresh("Select Prims//Frame/**/Button[*].text=='Select'")

        await add_prim("ReferenceXForm")
        await add_prim("PayloadXForm")

        await asyncio.sleep(4)  # Wait for UI animation to complete

        golden_img_dir = (
            pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "tests" / "golden_img"
        )
        await self.capture_and_compare(golden_img_name="test_select_prims.png", golden_img_dir=golden_img_dir)

        async def add_property(prop_label):
            await self.click_fresh(ADD_PROP_BUTTON)
            self.assert_single_picker_window("Select Properties")
            await self.click_fresh(f"Select Properties//Frame/**/Label[*].text=='{prop_label}'")
            await self.click_fresh("Select Properties//Frame/**/Button[*].text=='Add'")

        # Add variant property
        await add_property("VariantSet: PayloadRocks")

        # Add an attribute
        await add_property("visibility")

        # Copies properties
        prim_button = ui_test.find("Variant Editor//Frame/**/Label[*].text=='/World/PayloadXForm'")
        await prim_button.click(right_click=True)
        await ui_test.select_context_menu("Copy All Properties")

        # Pastes properties
        prim_button = ui_test.find("Variant Editor//Frame/**/Label[*].text=='/World/ReferenceXForm'")
        await prim_button.click(right_click=True)
        await ui_test.select_context_menu("Paste Property")

        # Add and edit a relationship
        await add_property("proxyPrim")

        async def add_relationship_target(prim_name):
            await self.click_fresh(ADD_REL_TARGET_BUTTON)
            await self.click_fresh(f"Select Targets//Frame/**/Label[*].text=='{prim_name}'")
            await self.click_fresh("Select Targets//Frame/**/Button[*].text=='Select'")

        await add_relationship_target("ParentCube")
        await add_relationship_target("ParentXForm")
        await self.click_fresh("Variant Editor//Frame/**/Button[*].identifier=='sdf_relationship_proxyPrim[0].remove'")

        async def pick_rock_small_01():
            # The picker is opened by the async task the "Add" click kicked off (see
            # prim_property_tree.add_props), so it is not on screen yet when that click
            # returns. Driving the importer before it exists silently picks nothing and
            # the arc is never authored.
            select_button = await ui_test.find_with_retry("Select Reference//Frame/**/Button[*].text=='Select'")
            self.assertIsNotNone(select_button, "asset picker did not open")

            async with FileImporterTestHelper() as file_import_helper:
                dir = pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "tests"
                await file_import_helper.select_items_async(str(dir), ["Rock_Small_01.usd"])
                await file_import_helper.click_apply_async()

        # Add a reference. Waiting for its row before adding the payload keeps a pick that
        # never landed attributable to the arc that dropped it.
        await add_property("Reference")
        await pick_rock_small_01()
        await self.find_all_when_count_is(LAYER_PATH_FIELD, 1)

        # Add a payload
        await add_property("Payload")
        await pick_rock_small_01()
        asset_path_widgets = await self.find_all_when_count_is(LAYER_PATH_FIELD, 2)

        threshold = 0.264  # Threshold for path difference of references
        self.assertEqual(
            os.path.basename(asset_path_widgets[0].model.get_value_as_string()),
            "Rock_Small_01.usd",
        )
        self.assertEqual(
            os.path.basename(asset_path_widgets[1].model.get_value_as_string()),
            "Rock_Small_01.usd",
        )

        omni.kit.undo.undo()
        omni.kit.undo.undo()
        omni.kit.undo.undo()
        omni.kit.undo.undo()
        omni.kit.undo.undo()
        omni.kit.undo.undo()
        omni.kit.undo.undo()
        omni.kit.undo.undo()
        omni.kit.undo.undo()
        await ui_test.human_delay(1)
        await self.capture_and_compare(
            golden_img_name="test_undo_add_variant_content.png",
            golden_img_dir=golden_img_dir,
        )

        omni.kit.undo.redo()
        omni.kit.undo.redo()
        omni.kit.undo.redo()
        omni.kit.undo.redo()
        omni.kit.undo.redo()
        omni.kit.undo.redo()
        omni.kit.undo.redo()
        omni.kit.undo.redo()
        omni.kit.undo.redo()
        asset_path_widgets = await self.find_all_when_count_is(LAYER_PATH_FIELD, 2)
        self.assertEqual(
            os.path.basename(asset_path_widgets[0].model.get_value_as_string()),
            "Rock_Small_01.usd",
        )
        self.assertEqual(
            os.path.basename(asset_path_widgets[1].model.get_value_as_string()),
            "Rock_Small_01.usd",
        )

        # Remove prims
        prim_button = ui_test.find("Variant Editor//Frame/**/Label[*].text=='/World/PayloadXForm'")
        await prim_button.click(right_click=True)
        await ui_test.select_context_menu("Remove Item")
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_remove_prim.png", golden_img_dir=golden_img_dir)

        omni.kit.undo.undo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_undo_remove_prim.png",
            golden_img_dir=golden_img_dir,
            threshold=threshold,
        )

        omni.kit.undo.redo()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(golden_img_name="test_redo_remove_prim.png", golden_img_dir=golden_img_dir)

        await self.finalize_test_no_image()

    async def test_variant_in_ref(self):
        await self.bootstrap_stage("test_variant_in_ref.usda")

        get_window().hide()  # Hide first to avoid failure caused by CoreTest.test_get_variant_specs()
        get_window().show()

        await self.docked_test_window(
            window=get_window()._window,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            block_devices=False,
        )

        # Select variant set and display variant content
        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Variant_Set'")
        await variant_widget.click()

        # Tries to edit variant
        # Adds a prim
        add_prim_button = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add Prim'")
        await add_prim_button.click()

        # Adds property
        add_prop_button = ui_test.find(
            "Variant Editor//Frame/**/TreeView[0]/HStack[0]/**/Button[0].text=='Add Property'"
        )
        await add_prop_button.click()

        # Removes properties
        for index in range(1, 7):
            remove_prop_button = ui_test.find(
                f"Variant Editor//Frame/**/TreeView[*]/HStack[{index}]/**/VStack[*].identifier=='remove_prop_widget vstack'"
            )
            await remove_prop_button.click()

        # Removes local opinions
        for index in range(1, 7):
            local_opinion_button = ui_test.find(
                f"Variant Editor//Frame/**/TreeView[*]/HStack[{index}]/**/PropertyWatchButton[*]"
            )
            await local_opinion_button.click()

        # Adds payloads
        add_payload_button = ui_test.find("Variant Editor//Frame/**/Button[*].identifier=='Variant Add Payload'")
        await add_payload_button.click()
        add_reference_button = ui_test.find("Variant Editor//Frame/**/Button[*].identifier=='Variant Add Reference'")
        await add_reference_button.click()

        # Edits relationship
        rel_path_widget = ui_test.find("Variant Editor//Frame/**/sdf_relationship_array_proxyPrim/**/StringField[*]")
        await rel_path_widget.click()
        await ui_test.emulate_char_press("asdfasdf")

        rel_browse_button = ui_test.find(
            "Variant Editor//Frame/**/sdf_relationship_array_proxyPrim/**/Button[*].name!='remove'"
        )
        await rel_browse_button.click()
        rel_remove_button = ui_test.find(
            "Variant Editor//Frame/**/sdf_relationship_array_proxyPrim/**/Button[*].name=='remove'"
        )
        await rel_remove_button.click()

        rel_add_target_button = ui_test.find("Variant Editor//Frame/**/TreeView[0]/HStack[4]/**/ZStack[*]/Button[*]")
        await rel_add_target_button.click()

        # Edits token attribute
        vis_attr_widget = ui_test.find("Variant Editor//Frame/**/token_visibility")
        await vis_attr_widget.click()
        click_pos = vis_attr_widget.center
        click_pos.y += vis_attr_widget.size.y * 2
        await ui_test.emulate_mouse_move_and_click(click_pos)

        # Edits translate
        translate_x_widget = ui_test.find(
            "Variant Editor//Frame/**/drag_per_channel_xformOp:translate/HStack[0]/**/FloatDrag[*]"
        )

        await translate_x_widget.double_click()
        await ui_test.emulate_char_press("123")
        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_variant_in_ref.png",
            golden_img_dir=self._golden_img_dir,
        )

        self.assertFalse(omni.usd.get_context().get_stage().GetRootLayer().dirty)

        await self.finalize_test_no_image()

    async def test_create_variant_from_content_browser(self):
        # Creates a variant from assets
        await self.bootstrap_stage("test_picker.usda")

        get_window().hide()  # Hide first to avoid failure caused by CoreTest.test_get_variant_specs()
        get_window().show()

        await self.docked_test_window(
            window=get_window()._window,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            block_devices=False,
        )

        get_window()._window.height = WINDOW_SIZE / 2
        content_window = ui_test.find("Content").window
        content_window.position_x = get_window()._window.position_x
        content_window.position_y = get_window()._window.position_x + get_window()._window.height
        content_window.width = get_window()._window.width
        content_window.height = WINDOW_SIZE - get_window()._window.height

        content_test_helper = ContentBrowserTestHelper()
        await content_test_helper.toggle_grid_view_async(True)

        async def pick_asset(file_name):
            asset_folder = pathlib.Path(self._golden_img_dir).parent
            await content_test_helper.select_items_async(str(asset_folder), [file_name])
            await content_test_helper.get_gridview_item_async(file_name)
            file_widget = ui_test.find(
                f"Content//Frame/**/content_browser_treeview_grid_view/**/Label[*].text=='{file_name}'"
            )
            await file_widget.right_click()
            await ui_test.select_context_menu("Create Variant Set")
            prim_widget = ui_test.find(
                "Select Target Prim//Frame/VStack[0]/Frame[0]/Frame[0]/VStack[0]/ScrollingFrame[0]/ZStack[0]/TreeView[0]/Frame[0]/ZStack[0]/HStack[0]/HStack[0]/Label[0]"
            )
            await prim_widget.click()
            select_button = ui_test.find("Select Target Prim//Frame/**/Button[*].text=='Select'")
            await select_button.click()

        await pick_asset("mdl.usda")
        await pick_asset("test.mdl")
        await pick_asset("Rock_Small_01.usd")
        await pick_asset("Rock_Small_01.usdc")
        await pick_asset("Rock_Small_01.usdz")

        await self.docked_test_window(
            window=get_window()._window,
            width=get_window()._window.width,
            height=get_window()._window.height,
            block_devices=False,
        )
        await omni.kit.app.get_app().next_update_async()
        await self.capture_and_compare(
            golden_img_name="test_create_variant_from_content_browser.png",
            golden_img_dir=self._golden_img_dir,
        )

        await self.finalize_test_no_image()
