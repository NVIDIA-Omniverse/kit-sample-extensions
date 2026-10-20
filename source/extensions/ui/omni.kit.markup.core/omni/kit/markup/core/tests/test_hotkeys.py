# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb.settings
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.markup.core import (
    MARKUP_TOOL_ORDER,
    SETTINGS_MARKUP_CURRENT_TOOL,
    SETTINGS_MARKUP_ENABLE_HOTKEYS,
    get_instance,
)
from omni.kit.markup.core.widgets.list_window import MarkupListWindow
from omni.ui.tests.test_base import OmniUiTest

from .. import extension
from ._viewport_frames import wait_for_viewport_frames


class TestHotkeys(OmniUiTest):
    async def setUp(self):
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        await wait_for_viewport_frames()
        self._ext = get_instance()
        self._settings = carb.settings.get_settings()

    async def tearDown(self):
        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, False)

        import omni.kit.hotkeys.core

        hotkey_context = omni.kit.hotkeys.core.get_hotkey_context()
        hotkey_context.clean()

    async def test_1_hotkeys_disabled(self):
        self.assertEqual(len(self._ext.get_markups()), 0)

        await ui_test.emulate_key_combo("M")
        await ui_test.human_delay()

        self.assertEqual(len(self._ext.get_markups()), 0)
        window = ui.Workspace.get_window("Markups")
        self.assertTrue(window is None or not window.visible)

    async def test_2_create(self):
        self.assertEqual(len(self._ext.get_markups()), 0)

        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        await ui_test.emulate_key_combo("M")
        await ui_test.human_delay()

        self.assertEqual(len(self._ext.get_markups()), 1)

    async def test_3_next_prev(self):
        self.assertEqual(len(self._ext.get_markups()), 0)
        self._ext.create_markup()
        self._ext.create_markup()
        self._ext.end_edit_markup(self._ext.current_markup, save=True)
        self.assertEqual(len(self._ext.get_markups()), 2)

        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        window = MarkupListWindow()
        self.assertIsNotNone(window)
        window.visible = True
        await ui_test.human_delay(5)  # focus is applied with a delay

        self.assertIsNone(window.selected_index)

        await ui_test.human_delay(10)

        # next, previous
        await ui_test.emulate_key_combo("RIGHT")
        await ui_test.human_delay(10)
        self.assertEqual(window.selected_index, 1)

        await ui_test.emulate_key_combo("LEFT")
        await ui_test.human_delay(10)
        self.assertEqual(window.selected_index, 0)

        window.visible = False
        window.destroy()
        del window

    async def test_4_del(self):
        self.assertEqual(len(self._ext.get_markups()), 0)
        self._ext.create_markup()
        self.assertEqual(len(self._ext.get_markups()), 1)

        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        window = MarkupListWindow()
        self.assertIsNotNone(window)
        window.visible = True
        await ui_test.human_delay(5)  # focus is applied with a delay

        # delete
        await ui_test.emulate_key_combo("DEL")
        await ui_test.human_delay(5)
        self.assertEqual(len(self._ext.get_markups()), 0)

        window.visible = False
        window.destroy()
        del window

    async def test_5_enter_and_escape(self):
        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        ext_instance = extension.get_instance()
        window = MarkupListWindow()
        self.assertIsNotNone(window)
        window.visible = True
        await ui_test.human_delay(5)  # focus is applied with a delay

        self.assertEqual(len(self._ext.get_markups()), 0)
        self._ext.create_markup()
        self.assertEqual(len(self._ext.get_markups()), 1)
        self.assertTrue(ext_instance.editing_markup)

        # Press Enter to complete markup
        await ui_test.human_delay(10)
        await ui_test.emulate_key_combo("ENTER")
        await ui_test.human_delay(10)

        self.assertFalse(ext_instance.editing_markup)

        # Create another markup and press ESC to cancel
        self._ext.create_markup()
        self.assertEqual(len(self._ext.get_markups()), 2)
        self.assertTrue(ext_instance.editing_markup)

        await ui_test.human_delay(10)
        await ui_test.emulate_key_combo("ESCAPE")
        await ui_test.human_delay(10)

        self.assertFalse(ext_instance.editing_markup)
        self.assertEqual(len(self._ext.get_markups()), 1)

        # Select one markup
        for index, w in enumerate(ui_test.find_all(f"{window.title}//Frame/**/ImageThumbnail")):
            await w.click()
            await ui_test.human_delay(2)
            self.assertEqual(index, window.selected_index)
            self.assertTrue(ext_instance.current_markup)
            break

        # Press ESC to exit current markup
        await ui_test.human_delay(5)
        await ui_test.emulate_key_combo("ESCAPE")

        await ui_test.human_delay(5)
        self.assertIsNone(ext_instance.current_markup)
        await ui_test.human_delay(5)

        window.destroy()

    async def test_hotkey_enter(self):

        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        self.assertEqual(len(self._ext.get_markups()), 0)
        self._ext.create_markup()
        self.assertEqual(len(self._ext.get_markups()), 1)

        mk = list(self._ext.get_markups())[0]

        self.assertEqual(self._ext.editing_markup, mk)

        # apply should call end_edit_markup:
        await ui_test.emulate_key_combo("ENTER")
        await ui_test.human_delay(5)
        self.assertEqual(self._ext.editing_markup, None)

    async def test_hotkey_escape(self):

        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        self.assertEqual(len(self._ext.get_markups()), 0)
        self._ext.create_markup()
        self.assertEqual(len(self._ext.get_markups()), 1)

        mk = list(self._ext.get_markups())[0]

        self._ext.current_markup = mk
        self.assertEqual(self._ext.current_markup, mk)
        self.assertEqual(self._ext.editing_markup, mk)

        # this should cancel editing:
        await ui_test.emulate_key_combo("ESCAPE")
        await ui_test.human_delay(5)

        self.assertEqual(self._ext.current_markup, None)
        self.assertEqual(self._ext.editing_markup, None)
        self.assertEqual(len(self._ext.get_markups()), 0)

    async def test_2_hotkey_escape(self):

        self.assertEqual(len(self._ext.get_markups()), 0)
        self._ext.create_markup()
        self.assertEqual(len(self._ext.get_markups()), 1)
        mk = list(self._ext.get_markups())[0]
        self._ext.end_edit_markup(mk, save=True)

        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        window = MarkupListWindow()
        self.assertIsNotNone(window)
        window.visible = True
        await ui_test.human_delay(5)

        # deselect
        await ui_test.emulate_key_combo("ESCAPE")
        await ui_test.human_delay(5)
        self.assertEqual(self._ext.current_markup, None)

        window.visible = False
        window.destroy()
        del window

    async def test_hotkey_pgup_pgdown(self):

        self._settings.set(SETTINGS_MARKUP_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        self.assertEqual(len(self._ext.get_markups()), 0)
        self._ext.create_markup()
        self.assertEqual(len(self._ext.get_markups()), 1)

        # does nothing if the tool is invalid:
        self._settings.set_string(SETTINGS_MARKUP_CURRENT_TOOL, "")
        await ui_test.emulate_key_combo("PAGE_UP")
        await ui_test.human_delay(5)

        self.assertEqual(self._settings.get(SETTINGS_MARKUP_CURRENT_TOOL), "")

        await ui_test.emulate_key_combo("PAGE_DOWN")
        await ui_test.human_delay(5)

        self.assertEqual(self._settings.get(SETTINGS_MARKUP_CURRENT_TOOL), "")

        # flip through the tools using page up/page down:
        self._settings.set_string(SETTINGS_MARKUP_CURRENT_TOOL, MARKUP_TOOL_ORDER[0])
        await ui_test.emulate_key_combo("PAGE_UP")
        await ui_test.human_delay(5)

        self.assertEqual(self._settings.get(SETTINGS_MARKUP_CURRENT_TOOL), MARKUP_TOOL_ORDER[1])

        await ui_test.emulate_key_combo("PAGE_DOWN")
        await ui_test.human_delay(5)

        self.assertEqual(self._settings.get(SETTINGS_MARKUP_CURRENT_TOOL), MARKUP_TOOL_ORDER[0])
