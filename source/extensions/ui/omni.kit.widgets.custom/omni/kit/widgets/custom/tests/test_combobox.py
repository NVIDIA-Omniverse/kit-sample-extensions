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

import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.ui_test.vec2 import Vec2

from ..combobox import ComboBoxEx, CustomWidgetComboBox, SpaceComboBox
from ..delegate import LabelDelegate
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestCombobox(TestWidgetsCustomBase):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR
        self._window = await self.create_test_window(width=360, height=240, block_devices=False)

        self._hide_main_menu_bar()

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        self._window.destroy()
        self._window = None

    async def reset_window(self):
        self._window.frame.clear()
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)

    def _on_combobox_changed(self, value):
        self._com_value = value

    async def test_WidgetComboBox(self):
        await self.reset_window()
        with self._window.frame:
            with ui.VStack():
                ui.Spacer(height=20)
                with ui.HStack():
                    ui.Spacer(width=30)
                    combobox = SpaceComboBox(
                        3, "Item 0", "Item 1", "Item 2", "Item 3", name="test-combo", width=110, height=24
                    )
                    combobox.model.add_item_changed_fn(
                        lambda model, item: self._on_combobox_changed(model.get_item_value_model().as_int)
                    )
                    ui.Spacer()
                ui.Spacer()

        await wait_frames(3)
        items = combobox.values
        self.assertEqual(len(items), 4)

        model = combobox._create_value_model("Value")
        self.assertNotEqual(model, None)

    async def test_SpaceComboBox(self):
        await self.reset_window()
        with self._window.frame:
            with ui.VStack():
                ui.Spacer(height=20)
                with ui.HStack():
                    ui.Spacer(width=30)
                    combobox = SpaceComboBox(
                        3, "Item 0", "Item 1", "Item 2", "Item 3", name="test-combo", width=110, height=24
                    )
                    combobox.model.add_item_changed_fn(
                        lambda model, item: self._on_combobox_changed(model.get_item_value_model().as_int)
                    )
                    ui.Spacer()
                ui.Spacer()

        await wait_frames(3)
        await self.compare_screen_with_golden("SpaceComboBox", golden_img="space_combobox-0.png")

        x = combobox.screen_position_x
        y = combobox.screen_position_y
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(x + 5, y + 5), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)
        await wait_frames(3)
        await self.compare_screen_with_golden("SpaceComboBox", golden_img="space_combobox-1.png")

        await ui_test.emulate_mouse_move(Vec2(x + 5, y + 50), 2)
        await wait_frames(3)
        await self.compare_screen_with_golden("SpaceComboBox", golden_img="space_combobox-2.png")
        await wait_frames(3)
        self._com_value = -1
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        await self.compare_screen_with_golden("SpaceComboBox", golden_img="space_combobox-3.png")
        self.assertTrue(self._com_value, 1)

        model = combobox._delegate.get_value_model(0.1)
        self.assertNotEqual(model, None)

        model = combobox.model.get_item_value_model(combobox.model.get_item_children()[1])
        self.assertNotEqual(model, None)
        value = combobox._get_value(model)
        self.assertEqual(value, "Item 1")

    async def test_CustomWidgetComboBox(self):
        await self.reset_window()
        with self._window.frame:
            with ui.VStack():
                ui.Spacer(height=20)
                with ui.HStack():
                    ui.Spacer(width=30)
                    combobox = CustomWidgetComboBox(
                        1,  # Current index
                        "pre-item-0",
                        "pre-item-1",
                        "pre-item-2",
                        item_delegate=LabelDelegate(),
                        width=100,
                        height=28,
                    )
                    ui.Spacer()
                ui.Spacer()

        await wait_frames(3)
        await self.compare_screen_with_golden("CustomWidgetComboBox", golden_img="custom-widget-combobox-0.png")

        await wait_frames(3)
        self.assertTrue(combobox.enabled)
        combobox.enabled = False
        await wait_frames(3)
        self.assertFalse(combobox.enabled)
        combobox.enabled = True
        await wait_frames(3)
        self.assertTrue(combobox.enabled)

        await wait_frames(3)
        self.assertEqual(combobox.values_count, 3)
        for value in ["new-item-0", "new-item-1", "new-item-2"]:
            combobox.insert(value, value_type="string")
        await wait_frames(3)
        self.assertEqual(combobox.values_count, 6)

        await wait_frames(3)
        combobox.remove(3)
        self.assertEqual(combobox.values_count, 5)
        combobox.current_index = 3
        await wait_frames(3)
        await self.compare_screen_with_golden("CustomWidgetComboBox", golden_img="custom-widget-combobox-1.png")

        self.assertNotEqual(combobox.current, None)
        self.assertEqual(combobox.current_value, "new-item-1")

        await wait_frames(3)
        combobox.clear()
        self.assertEqual(combobox.values_count, 0)
