# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb.settings
import omni.kit.test
import omni.kit.tool.measure
import omni.kit.ui_test as ui_test
import omni.ui as ui

from ..common import (
    SETTINGS_MEASURE_ENABLE_HOTKEYS,
    SETTINGS_MEASURE_NEXT_SNAP_HOTKEY,
    SETTINGS_MEASURE_NEXT_TOOL_HOTKEY,
    SETTINGS_MEASURE_OPEN_HOTKEY,
    SETTINGS_MEASURE_PREVIOUS_TOOL_HOTKEY,
)
from ..manager import Hotkey, HotkeyManager, ReferenceManager, StateMachine
from .test_util import TestMeasureBase


class TestHotkeys(TestMeasureBase):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._settings = carb.settings.get_settings()
        self._hotkey_calls = 0

        context = HotkeyManager().hotkey_context
        context.clean()  # measure window adds a context when becomes visible

    # After Running Each Test
    async def tearDown(self):
        await super().tearDown()

        self._settings = None
        self._hotkey_calls = 0

    async def test_hotkey_manager(self):
        # extension
        ext_name = "omni.whatever"
        HotkeyManager().extension_name = ext_name
        self.assertEqual(HotkeyManager().extension_name, ext_name)

        # get key
        self.assertIsNone(HotkeyManager().get_key("/setting/does/not/exist", None))
        self.assertEqual(HotkeyManager().get_key("/setting/does/not/exist", "SPACE"), "SPACE")
        setting_path = "/setting/that/exists"
        self._settings.set_string(setting_path, "ALT + K")
        self.assertEqual(HotkeyManager().get_key(setting_path, "SPACE"), "ALT + K")

        # test context
        context = HotkeyManager().hotkey_context
        context.push("a")
        context.push("b")
        context.push("c")
        context.push("b")

        self.assertEqual(context.get(), "b")
        HotkeyManager().remove_hotkey_context("b")
        self.assertEqual(context.get(), "c")
        HotkeyManager().remove_hotkey_context("a")
        self.assertEqual(context.get(), "c")
        HotkeyManager().remove_hotkey_context("c")
        self.assertIsNone(context.get())

        # create hotkey
        key = "CTRL+M"
        hotkey = Hotkey(name="h1", callback=self._on_hotkey, key=key)
        self.assertEqual(hotkey.name, "h1")
        self.assertEqual(hotkey.callback, self._on_hotkey)
        self.assertEqual(hotkey.key, key)
        self.assertIsNone(hotkey.filter_context)
        HotkeyManager().add_hotkey(hotkey)

        # hotkeys are disabled by default
        await ui_test.emulate_key_combo(key)
        target_calls = 0
        self.assertEqual(self._hotkey_calls, target_calls)

        # enable hotkeys
        self._settings.set_bool(SETTINGS_MEASURE_ENABLE_HOTKEYS, True)

        await ui_test.emulate_key_combo(key)
        target_calls = target_calls + 1
        self.assertEqual(self._hotkey_calls, target_calls)

        # deregister
        HotkeyManager().deregister_hotkey(hotkey)
        await ui_test.emulate_key_combo(key)
        self.assertEqual(self._hotkey_calls, target_calls)

        # filter
        filter_context = "just a context"
        key_2 = "ALT+W"
        hotkey = Hotkey(name="h2", callback=self._on_hotkey, key=key_2, filter_context=filter_context)
        self.assertEqual(hotkey.filter_context, filter_context)
        HotkeyManager().add_hotkey(hotkey)

        # context is inactive
        await ui_test.emulate_key_combo(key_2)
        self.assertEqual(self._hotkey_calls, target_calls)

        # context is active
        context.push(filter_context)
        await ui_test.emulate_key_combo(key_2)
        target_calls = target_calls + 1
        self.assertEqual(self._hotkey_calls, target_calls)

        # deregister all
        HotkeyManager().deregister_all_hotkeys()
        await ui_test.emulate_key_combo(key_2)
        self.assertEqual(self._hotkey_calls, target_calls)

        context.clean()

    async def test_measure_hotkeys(self):
        ui.Workspace.show_window("Measure", False)
        measure_window = ui.Workspace.get_window("Measure")
        self.assertFalse(measure_window.visible)
        context = HotkeyManager().hotkey_context
        context.clean()

        open_key = "M"
        self._settings.set_string(SETTINGS_MEASURE_OPEN_HOTKEY, open_key)
        await ui_test.emulate_key_combo(open_key)
        self.assertFalse(measure_window.visible)

        next_tool_key = "A"
        prev_tool_key = "S"
        next_snap_key = "Q"
        self._settings.set_string(SETTINGS_MEASURE_NEXT_TOOL_HOTKEY, next_tool_key)
        self._settings.set_string(SETTINGS_MEASURE_PREVIOUS_TOOL_HOTKEY, prev_tool_key)
        self._settings.set_string(SETTINGS_MEASURE_NEXT_SNAP_HOTKEY, next_snap_key)

        # enable settings
        self._settings.set_bool(SETTINGS_MEASURE_ENABLE_HOTKEYS, True)
        # dynamic reload is not implemented so we reload manually
        HotkeyManager().deinit()
        extension = omni.kit.tool.measure.get_instance()
        extension._register_hotkeys(extension._ext_name)

        # open
        await ui_test.emulate_key_combo(open_key)
        await ui_test.human_delay(5)
        self.assertTrue(measure_window.visible)
        self.assertIsNotNone(context.get())

        # next/previous tool
        sm = StateMachine()
        self.assertIsNotNone(sm)
        current_tool = sm.tool_mode
        await ui_test.emulate_key_combo(next_tool_key)
        await ui_test.human_delay(5)
        self.assertNotEqual(current_tool, sm.tool_mode)

        await ui_test.emulate_key_combo(prev_tool_key)
        await ui_test.human_delay(5)
        self.assertEqual(current_tool, sm.tool_mode)

        # next snap
        rm = ReferenceManager()
        self.assertIsNotNone(rm)
        self.assertIsNotNone(rm.ui_placement_panel)
        snap_group = rm.ui_placement_panel.snap_group
        self.assertIsNotNone(snap_group)
        current_snap = snap_group._snap_collection.model.as_int

        await ui_test.emulate_key_combo(next_snap_key)
        await ui_test.human_delay(5)
        self.assertNotEqual(current_snap, snap_group._snap_collection.model.as_int)

    def _on_hotkey(self):
        self._hotkey_calls = self._hotkey_calls + 1
