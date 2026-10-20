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
from omni.kit.ui_test.vec2 import Vec2

from ..slider import FloatSliderEx, TriangleCursorIntSlider
from ..spinner import FloatSpinner, IntSpinner
from ..switch import Switch, SwitchOrCheckbox
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestSlider(TestWidgetsCustomBase):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR
        self._window = await self.create_test_window(width=480, height=320, block_devices=False)
        with self._window.frame:
            with ui.ZStack(padding_x=0, padding_y=0):

                def _on_clicked(x, y, btn, a):
                    # print(f"Clicked at {x}, {y}")
                    pass

                style = {"Rectangle": {"background_color": 0x0, "border_width": 1, "border_color": 0xFF0000FF}}
                ui.Rectangle(style=style, mouse_pressed_fn=_on_clicked)

                self._test_stack = ui.VStack()

        self._hide_main_menu_bar()

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        self._window.destroy()
        self._window = None

    def _on_value_changed(self, value):
        self._cur_value = value
        # print(f"On_value changed, new value is {value}")

    async def test_slider(self):
        UI_STYLE = {
            "Slider": {
                "draw_mode": ui.SliderDrawMode.HANDLE,
                "background_color": 0xFF909090,
                "color": 0xFF454545,
                "secondary_color": 0xFF00FFFF,
                "secondary_selected_color": 0xFFFFFF00,
            },
            "Triangle::slider": {"background_color": 0xFF303030},
        }

        self._test_stack.clear()
        with self._test_stack:
            ui.Spacer(height=20)
            with ui.HStack(height=20):
                ui.Spacer(width=20)
                int_slider = TriangleCursorIntSlider(0, 100, 50, 400, 20, style=UI_STYLE)
                int_slider.set_value_changed_fn(self._on_value_changed)
                ui.Spacer()

            ui.Spacer(height=10)
            with ui.HStack(height=20):
                ui.Spacer(width=20)
                float_slider = FloatSliderEx(0.5, self._on_value_changed, width=400, height=20)
                ui.Spacer()

            ui.Spacer()

        await wait_frames(3)
        await self.compare_screen_with_golden("Slider-0", "slider-0.png")
        await wait_frames(3)
        int_slider.set_value(25)
        float_slider.value = 1.0
        await wait_frames(3)
        await self.compare_screen_with_golden("Slider-1", "slider-1.png")

        await wait_frames(3)
        self._cur_value = 0
        await ui_test.emulate_mouse_move_and_click(Vec2(320, 34))
        await wait_frames(3)
        self.assertEqual(self._cur_value, 75)

        self._cur_value = 0
        await ui_test.emulate_mouse_move_and_click(Vec2(320, 64))
        await wait_frames(3)
        self.assertFloatEqual(self._cur_value, 0.7)

    async def test_spinner(self):
        self._test_stack.clear()
        with self._test_stack:
            ui.Spacer(height=20)
            with ui.HStack(height=20):
                ui.Spacer(width=20)
                int_spinner = IntSpinner(self._on_value_changed, value=5, step=1, min_value=0, max_value=10)
                ui.Spacer()

            ui.Spacer(height=20)
            with ui.HStack(height=20):
                ui.Spacer(width=20)
                float_spinner = FloatSpinner(self._on_value_changed, value=0.5, step=0.1, min_value=0.0, max_value=10.0)
                ui.Spacer()
            ui.Spacer()

        await wait_frames(3)
        await self.compare_screen_with_golden("Spinner-0", "spinner-0.png")
        await wait_frames(3)

        # inc/dec int value
        await wait_frames(3)
        self._cur_value = 0
        await ui_test.emulate_mouse_move_and_click(Vec2(241, 32))
        await wait_frames(3)
        self.assertEqual(self._cur_value, 6)
        await self.compare_screen_with_golden("Spinner-1", "spinner-1.png")

        await wait_frames(3)
        self._cur_value = 0
        await ui_test.emulate_mouse_move_and_click(Vec2(241, 42))
        await wait_frames(3)
        await ui_test.emulate_mouse_move_and_click(Vec2(241, 42))
        await wait_frames(3)
        self.assertEqual(self._cur_value, 4)
        await self.compare_screen_with_golden("Spinner-2", "spinner-2.png")

        # inc/dec float value
        await wait_frames(3)
        self._cur_value = 0
        await ui_test.emulate_mouse_move_and_click(Vec2(241, 77))
        await wait_frames(3)
        self.assertFloatEqual(self._cur_value, 0.6)
        await self.compare_screen_with_golden("Spinner-3", "spinner-3.png")

        await wait_frames(3)
        self._cur_value = 0
        await ui_test.emulate_mouse_move_and_click(Vec2(241, 87))
        await wait_frames(3)
        await ui_test.emulate_mouse_move_and_click(Vec2(241, 87))
        await wait_frames(3)
        self.assertFloatEqual(self._cur_value, 0.4)
        await self.compare_screen_with_golden("Spinner-4", "spinner-4.png")

    async def test_switch(self):
        self._test_stack.clear()
        with self._test_stack:
            ui.Spacer(height=20)
            with ui.HStack(height=20):
                ui.Spacer(width=20)
                switch = Switch(True, self._on_value_changed)
                ui.Spacer()

            ui.Spacer(height=20)
            with ui.HStack(height=20):
                ui.Spacer(width=20)
                checkbox = SwitchOrCheckbox(True, self._on_value_changed)
                ui.Spacer()
            ui.Spacer()

        await wait_frames(3)
        await self.compare_screen_with_golden("Switch-0", "switch-0.png")
        await wait_frames(3)

        # Click on swith
        await wait_frames(3)
        self._cur_value = None
        await ui_test.emulate_mouse_move_and_click(Vec2(42, 40))
        await wait_frames(3)
        self.assertFalse(self._cur_value)
        await self.compare_screen_with_golden("Switch-1", "switch-1.png")

        await wait_frames(3)
        self._cur_value = None
        await ui_test.emulate_mouse_move_and_click(Vec2(42, 40))
        await wait_frames(3)
        self.assertTrue(self._cur_value)
        await self.compare_screen_with_golden("Switch-0", "switch-0.png")

        # Click on checkbox
        await wait_frames(3)
        self._cur_value = None
        await ui_test.emulate_mouse_move_and_click(Vec2(32, 82))
        await wait_frames(3)
        self.assertFalse(self._cur_value)
        await self.compare_screen_with_golden("Switch-2", "switch-2.png")

        await wait_frames(3)
        self._cur_value = None
        await ui_test.emulate_mouse_move_and_click(Vec2(32, 82))
        await wait_frames(3)
        self.assertTrue(self._cur_value)
        await self.compare_screen_with_golden("Switch-0", "switch-0.png")

    def assertFloatEqual(self, f1, f2):
        differ = abs(f1 - f2)
        max = abs(f1 + f2)
        self.assertTrue(differ * 1000 < max)
