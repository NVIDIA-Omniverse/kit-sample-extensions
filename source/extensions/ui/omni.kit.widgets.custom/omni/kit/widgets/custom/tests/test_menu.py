# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.ui_test as ui_test
import omni.ui as ui

from ..menu import CustomMenu, CustomWidgetMenu
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames

# from ..samples.custommenu import SimpleCustomMenuWindow


class TestMenu(TestWidgetsCustomBase):
    def _on_selection_changed(self, index):
        self._selection_history.append(index)

    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR

        self._hide_main_menu_bar()
        self._selection_history = []

    async def tearDown(self):
        self._selection_history = []

        await super().tearDown()

    async def test_custom_menu(self):
        def create_widget_fn(value, widget_width, widget_height):
            return ui.Label(value, width=widget_width, height=widget_height)

        window = await self.create_test_window(block_devices=False)

        menu_items = [f"menu {i}" for i in range(5)]

        with window.frame:
            self._bg_widget = ui.Rectangle(width=50, height=50)
            menu = CustomMenu(
                menu_items,
                [create_widget_fn],
                menuitem_height=20,
                menuitem_width=50,
                on_selection_changed_fn=self._on_selection_changed,
            )
        await wait_frames(3)

        # basic display
        menu.show_at(self._bg_widget, alignment=ui.Alignment.BOTTOM)
        await wait_frames(3)
        await self.compare_screen_with_golden("menu_botton_align", "menu_bottom_align.png")

        # change alignment
        menu.show_at(self._bg_widget, alignment=ui.Alignment.RIGHT)
        await wait_frames(3)
        await self.compare_screen_with_golden("menu_right_bottom_align", "menu_right_align.png")

        # click and select
        menu_item0 = ui_test.find(f"CustomMenu//Frame/**/Label[*].text=='{menu_items[0]}'")
        menu_item3 = ui_test.find(f"CustomMenu//Frame/**/Label[*].text=='{menu_items[3]}'")
        await ui_test.emulate_mouse_move_and_click(menu_item0.center)
        self.assertEqual(self._selection_history[0], "menu 0")
        self.assertEqual(menu.selection, 0)
        self.assertFalse(menu.visible)

        menu.show_at(self._bg_widget, alignment=ui.Alignment.RIGHT)
        await wait_frames(3)
        await ui_test.emulate_mouse_move_and_click(menu_item3.center)
        self.assertEqual(f"{self._selection_history[1]}", "menu 3")
        self.assertEqual(menu.selection, 3)

        await self.finalize_test_no_image()

    async def test_custom_widget_menu_alignments(self):
        window = await self.create_test_window()

        menu_items = [f"menu {i}" for i in range(5)]

        with window.frame:
            self._bg_widget = ui.Rectangle(width=50, height=50)
            menu = CustomWidgetMenu(menu_items, width=100, on_selection_changed_fn=self._on_selection_changed)
        await wait_frames(3)

        # compare different alignments
        menu.show_at(self._bg_widget, alignment=ui.Alignment.CENTER)
        await wait_frames(3)
        await self.compare_screen_with_golden("widget_menu_center_align", "widget_menu_center_align.png")
        menu.show_at(self._bg_widget, alignment=ui.Alignment.BOTTOM)
        await wait_frames(3)
        await self.compare_screen_with_golden("widget_menu_botton_align", "widget_menu_bottom_align.png")
        menu.show_at(self._bg_widget, alignment=ui.Alignment.RIGHT)
        await wait_frames(3)
        await self.compare_screen_with_golden("widget_menu_right_bottom_align", "widget_menu_right_align.png")
        menu.show_at(self._bg_widget, alignment=ui.Alignment.RIGHT_BOTTOM)
        await wait_frames(3)
        await self.compare_screen_with_golden("widget_menu_right_bottom_align", "widget_menu_right_bottom_align.png")

        await self.finalize_test_no_image()

    async def test_custom_widget_menu_select(self):
        window = await self.create_test_window(block_devices=False)

        menu_items = [f"menu {i}" for i in range(5)]

        with window.frame:
            self._bg_widget = ui.Rectangle(width=50, height=50)
            menu = CustomWidgetMenu(
                menu_items, width=100, on_selection_changed_fn=self._on_selection_changed, selection=0
            )
        await wait_frames(3)
        menu.show_at(self._bg_widget)

        # click and select
        await wait_frames(3)
        menu_item3 = ui_test.find(f"##CustomWidgetMenu_{hash(menu)}//Frame/**/Label[*].text=='{menu_items[3]}'")
        await ui_test.emulate_mouse_move_and_click(menu_item3.center)
        self.assertEqual(self._selection_history[0], 3)
        self.assertEqual(menu.selection, 3)
        self.assertFalse(menu.visible)

        menu.show_at(self._bg_widget)
        await wait_frames(3)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="widget_menu_select.png")
