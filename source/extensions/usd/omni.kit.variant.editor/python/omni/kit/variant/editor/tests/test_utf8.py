# Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.stage_templates
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.usd
from carb.input import KeyboardInput
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf, Tf, Usd

from ..core import VariantEditorCore
from ..extension import get_window
from .test_cleanup import reset_variant_editor_test_state


class TestUTF8VariantRenaming(OmniUiTest):
    async def setUp(self):
        await super().setUp()
        await omni.kit.stage_templates.new_stage_async(template=None)
        self._stage = omni.usd.get_context().get_stage()
        self._core = VariantEditorCore.get_instance()
        self._core._update_context_and_stage()

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()
        await reset_variant_editor_test_state()
        await super().tearDown()

    async def open_variant_window(self):
        window = get_window()
        window.show()
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        return window

    async def test_utf8_variant_rename(self):
        # Test renaming a variant to UTF-8 name through the UI.

        # UTF-8 test string with accented characters
        utf8_variant_name = "test3ÄßÖÜäöü_variant"

        # Open the variant editor window
        window = await self.open_variant_window()

        # Select the World prim to add variant sets to
        world_prim = self._stage.GetPrimAtPath("/World")
        self.assertTrue(world_prim.IsValid(), "World prim should exist")

        # Tell the variant editor to focus on the World prim
        window._on_prim_picked(["/World"])

        # Wait for UI updates
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        #  Add a variant set (this should automatically create a variant)
        add_variant_set_button = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add New Variant Set'")
        self.assertIsNotNone(add_variant_set_button, "Add Variant Set button should be found")
        await add_variant_set_button.click()

        # Wait for the variant set and default variant to be created
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        # Find the variant label
        variant_widget = ui_test.find("Variant Editor//Frame/**/TreeView[*]/**/Label[*].text=='Variant'")
        self.assertIsNotNone(variant_widget, "Should find variant label to rename")

        # Right-click on the variant to open context menu
        await variant_widget.right_click()
        await ui_test.select_context_menu("Rename Variant")
        await ui_test.emulate_char_press(utf8_variant_name)
        await ui_test.emulate_keyboard_press(KeyboardInput.ENTER)

        # Wait for UI updates
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        # Find the variant label again (it should now show the new name)
        updated_variant_widget = ui_test.find(
            f"Variant Editor//Frame/**/TreeView[*]/**/Label[*].text=='{utf8_variant_name}'"
        )

        # Verify the name was set correctly
        self.assertIsNotNone(
            updated_variant_widget,
            f"Should find variant with new name '{utf8_variant_name}'",
        )
        actual_name = updated_variant_widget.widget.text
        print(f"Variant renamed to: '{actual_name}'")

        # Test if the UTF-8 name is preserved (main test assertion)
        self.assertEqual(
            actual_name,
            utf8_variant_name,
            f"Variant name should be '{utf8_variant_name}' but was '{actual_name}'",
        )

        window.hide()

        print("UTF-8 variant rename test completed successfully!")

    async def test_utf8_variant_set_rename(self):
        # Test renaming a variant set to UTF-8 name through the UI.

        # UTF-8 test string with accented characters
        utf8_variant_set_name = "test3ÄßÖÜäöü_variantSet"

        # Open the variant editor window
        window = await self.open_variant_window()

        # Select the World prim to add variant sets to
        world_prim = self._stage.GetPrimAtPath("/World")
        self.assertTrue(world_prim.IsValid(), "World prim should exist")

        # Tell the variant editor to focus on the World prim
        window._on_prim_picked(["/World"])

        # Wait for UI updates
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        #  Add a variant set
        add_variant_set_button = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add New Variant Set'")
        self.assertIsNotNone(add_variant_set_button, "Add Variant Set button should be found")
        await add_variant_set_button.click()

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        # Rename variant set
        variant_set_widget = ui_test.find(
            "Variant Editor//Frame/**/TreeView[*]/VStack[*]/**/Label[*].text=='Variant_Set'"
        )

        await variant_set_widget.right_click()
        await ui_test.select_context_menu("Rename Variant Set")
        await ui_test.emulate_char_press(utf8_variant_set_name)
        await ui_test.emulate_keyboard_press(KeyboardInput.ENTER)

        # Wait for UI updates
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        # Find the variant set label again (it should now show the new name)
        updated_variant_set_widget = ui_test.find(
            f"Variant Editor//Frame/**/TreeView[*]/VStack[*]/**/Label[*].text=='{utf8_variant_set_name}'"
        )

        # Verify the name was set correctly
        self.assertIsNotNone(
            updated_variant_set_widget,
            f"Should find variant set with new name '{utf8_variant_set_name}'",
        )
        actual_name = updated_variant_set_widget.widget.text
        print(f"Variant set renamed to: '{actual_name}'")

        # Test if the UTF-8 name is preserved (main test assertion)
        self.assertEqual(
            actual_name,
            utf8_variant_set_name,
            f"Variant set name should be '{utf8_variant_set_name}' but was '{actual_name}'",
        )

        window.hide()

        print("UTF-8 variant set rename test completed successfully!")
