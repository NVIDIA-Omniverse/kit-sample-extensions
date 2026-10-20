# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Test suite for the In-App Guide extension.

This module contains automated tests for the In-App Guide functionality,
including menu integration, navigation controls, and step progression.
"""

import carb
import omni.kit.menu.utils
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.ui.tests.test_base import OmniUiTest


class TestInAppGuide(OmniUiTest):
    """Test class for In-App Guide functionality.

    This class contains test cases that verify the proper functioning of the
    In-App Guide extension, including UI interactions, navigation, and step display.
    """

    async def setUp(self):
        """Set up test environment before each test.

        Creates a new USD stage and refreshes the Help menu to ensure
        the guide is properly initialized.
        """
        await omni.usd.get_context().new_stage_async()
        omni.kit.menu.utils.refresh_menu_items("Help")
        test_runner = ui.Workspace.get_window("Test Runner")
        if test_runner and not test_runner.docked:
            test_runner.dock_in(ui.Workspace.get_window("Viewport"), ui.DockPosition.BOTTOM, 0.3)
        await ui_test.human_delay(20)

    async def tearDown(self):
        """Clean up test environment after each test.

        Closes the guide window if it's open to ensure a clean state
        for subsequent tests.
        """
        try:
            # Close the guide window if it is open
            guide_window = ui.Workspace.get_window("In-App Guide")
            if guide_window:
                await self.press_button("close")
                await ui_test.human_delay(10)
                carb.log_info("Guide window closed")
        except Exception:
            pass

    async def test_verify_guide_menu(self):
        """Test that the Guide menu item exists in the Help menu."""
        guide_item = await self.get_menu_item("In-App Guide")
        self.assertIsNotNone(guide_item)

    async def test_guide_buttons(self):
        """Test guide navigation buttons and steps toggle functionality.

        This test verifies:
        - Previous button is disabled on the first step
        - Next button navigates forward
        - Previous button navigates backward
        - Steps toggle shows/hides the step list
        - Selecting a step from the list changes the current step
        """
        guide_item = await self.get_menu_item("In-App Guide")
        self.assertIsNotNone(guide_item)
        await ui_test.human_delay(10)
        await self._open_guide()

        # Making sure the disable button is disabled, since we are on the first step
        # Get current header title
        header_name = "In-App Guide//Frame/**/Label[*].name=='header'"
        header = ui_test.find(header_name)
        header_text = header.widget.text
        # Verify previous button is disabled
        await self.press_button("disabled_previous")
        # Check that the header has NOT changed
        new_header = ui_test.find(header_name)
        new_header_text = new_header.widget.text
        self.assertEqual(header_text, new_header_text)

        # Verify next button is enabled
        await self.press_button("enabled_next")

        # Verify previous button is enabled
        await self.press_button("enabled_previous")

        # Verify steps toggle button
        steps = ui_test.find("In-App Guide//Frame/**/ZStack[2]")
        self.assertFalse(steps.widget.visible)
        await self.press_button("steps_toggle")
        await ui_test.human_delay(10)
        self.assertTrue(steps.widget.visible)

        if steps.widget.visible:
            steps_list = ui_test.find("In-App Guide//Frame/**/TreeView[*].visible==True")
            treeview = steps_list.widget
            children = treeview.model.get_item_children()
            self.assertTrue(len(children) > 0)
            if len(children) > 1:
                # Get current header title
                header_name = "In-App Guide//Frame/**/Label[*].name=='header'"
                header = ui_test.find(header_name)
                header_text = header.widget.text
                # Select the second child
                second_child = steps_list.find("Label[1]")
                self.assertTrue(second_child)

                # Click on the second child
                await ui_test.emulate_mouse_move(second_child.center)
                await ui_test.emulate_mouse_click()
                await ui_test.human_delay(50)

                # Check that the header has changed
                new_header = ui_test.find(header_name)
                new_header_text = new_header.widget.text
                self.assertNotEqual(header_text, new_header_text)
        # Check that the steps are still visible
        self.assertTrue(steps.widget.visible)
        await self.press_button("steps_toggle")
        # Check that the steps are now hidden
        self.assertFalse(steps.widget.visible)

        # Close window
        await self.press_button("close")
        await ui_test.human_delay(10)

    async def test_composer_guide(self):
        """Test navigating through all guide steps.

        This test opens the guide and clicks through all steps to ensure
        each step can be displayed and navigated to successfully. It verifies
        that the final step is reached by confirming the next button becomes
        disabled.
        """
        await self._open_guide()

        # On the first step, the next button must be enabled (there must be more than one step).
        next_button = ui_test.find("In-App Guide//Frame/**/Button[*].name=='enabled_next'")
        self.assertIsNotNone(next_button, "Guide did not open or has no steps to navigate")

        # Walk through every step. Cap iterations so a stuck UI doesn't loop forever.
        max_steps = 100
        step_count = 0
        while next_button is not None and step_count < max_steps:
            await self.press_button("enabled_next")
            await ui_test.human_delay(30)
            next_button = ui_test.find("In-App Guide//Frame/**/Button[*].name=='enabled_next'")
            step_count += 1

        self.assertLessEqual(step_count, max_steps, "Step navigation exceeded the safety limit; possible infinite loop")

        # On the final step the next button switches to "disabled_next"; make sure that is the case.
        disabled_next = ui_test.find("In-App Guide//Frame/**/Button[*].name=='disabled_next'")
        self.assertIsNotNone(disabled_next, "Did not reach the final guide step")

        await self.press_button("close")
        await ui_test.human_delay(20)

    async def get_menu_item(self, menu_item_name):
        """Find and return a menu item by name.

        Args:
            menu_item_name: The text name of the menu item to find.

        Returns:
            The menu item widget if found, None otherwise.
        """
        menu_widget = ui_test.get_menubar()
        for w in menu_widget.find_all("**/"):
            if isinstance(w.widget, ui.MenuItem) and w.widget.text.strip() == menu_item_name:
                return w.widget
        return None

    async def _open_guide(self, attempts: int = 3):
        """Open the guide from the Help menu and wait (bounded) until its first step is shown.

        On Kit 111 the guide window can appear later than a fixed 20-frame delay after the menu click (the OVRTX
        viewport is still starting up on the new stage), so wait for the window and its navigation button. In some
        runs the item click also reaches a Help menu that was rebuilt under it and nothing opens; the popup then stays
        shown, and menu_click() does not reopen a shown menu, so it would click the same stale item again. Close the
        Help menu and click through it again (bounded) instead.
        """
        for _ in range(attempts):
            await ui_test.menu_click("Help/In-App Guide")
            for _ in range(100):
                window = ui.Workspace.get_window("In-App Guide")
                if window and window.visible and ui_test.find("In-App Guide//Frame/**/Button[*].name=='enabled_next'"):
                    await ui_test.human_delay(20)
                    return
                await omni.kit.app.get_app().next_update_async()
            carb.log_warn("In-App Guide did not open from the Help menu; closing the menu and clicking it again")
            await ui_test.menu_click("Help", show=False)
            await ui_test.human_delay(10)
        await ui_test.human_delay(20)

    async def press_button(self, button_name):
        """Find and click a button in the guide window.

        Args:
            button_name: The name attribute of the button to press.
        """
        button = ui_test.find(f"In-App Guide//Frame/**/Button[*].name=='{button_name}'")
        self.assertIsNotNone(button)
        await button.click()
        await ui_test.human_delay(50)
