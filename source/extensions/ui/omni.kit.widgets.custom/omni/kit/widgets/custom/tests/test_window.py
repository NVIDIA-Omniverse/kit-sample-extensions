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
from carb.input import KeyboardInput, MouseEventType
from omni.kit.ui_test.vec2 import Vec2

from ..prompt import Prompt
from ..window import NoTitleWindowBase, PopupWindow, Rect, TitleWindowBase, WidgetRect, WindowRect
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestWindow(TestWidgetsCustomBase):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR
        await self.create_test_area(480, 360, False)

        self._hide_main_menu_bar()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_Rect(self):
        rect = Rect(100, 100, 100, 100)
        self.assertEqual(rect.left, 100)
        self.assertEqual(rect.right, 200)
        self.assertEqual(rect.top, 100)
        self.assertEqual(rect.bottom, 200)
        self.assertFalse(rect.is_inside(50, 100))
        self.assertFalse(rect.is_inside(250, 100))
        self.assertFalse(rect.is_inside(150, 50))
        self.assertFalse(rect.is_inside(150, 250))
        self.assertTrue(rect.is_inside(150, 150))

    async def test_PopupWindow(self):
        window_flags = (
            ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_MOVE
        )
        window = PopupWindow(
            "Test PopupWindow",
            ui.DockPreference.DISABLED,
            width=400,
            height=300,
            padding_x=0,
            padding_y=0,
            flags=window_flags,
            visible=True,
        )

        with window.frame:
            with ui.ZStack(padding_x=0, padding_y=0):

                def _on_clicked(x, y, btn, a):
                    # print(f"Clicked at {x}, {y}")
                    pass

                style = {"Rectangle": {"background_color": 0x0, "border_width": 1, "border_color": 0xFF0000FF}}
                ui.Rectangle(style=style, width=ui.Percent(100), height=ui.Percent(100), mouse_pressed_fn=_on_clicked)

                with ui.VStack():
                    ui.Spacer()
                    with ui.HStack():
                        ui.Spacer()
                        ui.Label("This is a test for PopupWindow")
                        ui.Spacer()
                    ui.Spacer()

                with ui.Placer(offset_x=20, offset_y=200):
                    style = {"Rectangle": {"background_color": 0xFFFF0000}}
                    rc = ui.Rectangle(style=style, width=360, height=60)

        window.setPosition(10, 10)
        await wait_frames(3)
        # TODO: some img compare not stable, change back threadhold to 100 when resolve
        await self.compare_screen_with_golden("PopupWindow-0", golden_img="popup_window-0.png", threadhold=1000)

        win_rect = WindowRect(window)
        widget_rect = WidgetRect(rc)
        window.visible = True
        self.assertEqual(win_rect.width, 400)
        self.assertEqual(win_rect.height, 300)
        self.assertEqual(widget_rect.width, 360)
        self.assertEqual(widget_rect.height, 60)

        await wait_frames(3)
        await ui_test.emulate_mouse_move_and_click(Vec2(5, 5))
        await wait_frames(3)

        self.assertFalse(window.visible)

        window.visible = True
        await wait_frames(3)
        window.setPosition(10, 10)
        await wait_frames(3)
        await self.compare_screen_with_golden("PopupWindow-1", golden_img="popup_window-1.png", threadhold=1000)
        await wait_frames(3)
        await ui_test.emulate_mouse_move_and_click(Vec2(5, 5))
        await wait_frames(3)
        self.assertFalse(window.visible)

        window.destroy()

    async def test_TitleWindowBase(self):
        class TitleWindow(TitleWindowBase):
            def __init__(self):
                icon_path = str(GOLDEN_IMG_DIR.parent.joinpath("image.svg").absolute())
                super().__init__("Test PopupWindow", ui.DockPreference.DISABLED, icon_path, width=400, height=300)

            def _build_content(self):
                with ui.ZStack(padding_x=0, padding_y=0):

                    def _on_clicked(x, y, btn, a):
                        # print(f"Clicked at {x}, {y}")
                        pass

                    style = {"Rectangle": {"background_color": 0x0, "border_width": 1, "border_color": 0xFF0000FF}}
                    ui.Rectangle(
                        style=style, width=ui.Percent(100), height=ui.Percent(100), mouse_pressed_fn=_on_clicked
                    )

                    with ui.VStack():
                        ui.Spacer()
                        with ui.HStack():
                            ui.Spacer()
                            ui.Label("This is a test for PopupWindow")
                            ui.Spacer()
                        ui.Spacer()

                    with ui.Placer(offset_x=20, offset_y=200):
                        style = {"Rectangle": {"background_color": 0xFFFF0000}}
                        ui.Rectangle(style=style, width=360, height=60)

        window = TitleWindow()
        window.show(10, 10)
        self.assertIsNotNone(window.get_window_handle())
        await ui_test.emulate_keyboard_press(KeyboardInput.ESCAPE)
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100), human_delay_speed=2)
        await wait_frames(3)
        # Intermediate capture must not tear down the test area; finalize_test restores the
        # main window size, which would leave the second capture at the pre-test resolution.
        await self.capture_and_compare(100, self._golden_img_dir, "title_window.png")

        await ui_test.emulate_keyboard_press(KeyboardInput.ESCAPE)
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100), human_delay_speed=2)
        await wait_frames(3)
        await self.finalize_test(100, self._golden_img_dir, "no_title_window.png")
        window.dock("Viewport")
        window.show(False)
        self.assertFalse(window.is_visible())
        window.destroy()

    async def test_NoTitleWindowBase(self):
        class NoTitleWindow(NoTitleWindowBase):
            def __init__(self):
                icon_path = str(GOLDEN_IMG_DIR.parent.joinpath("image.svg").absolute())
                super().__init__("Test PopupWindow", ui.DockPreference.DISABLED, icon_path, width=400, height=300)

            def _build_content(self):
                with ui.ZStack(padding_x=0, padding_y=0):

                    def _on_clicked(x, y, btn, a):
                        # print(f"Clicked at {x}, {y}")
                        pass

                    style = {"Rectangle": {"background_color": 0x0, "border_width": 1, "border_color": 0xFF0000FF}}
                    ui.Rectangle(
                        style=style, width=ui.Percent(100), height=ui.Percent(100), mouse_pressed_fn=_on_clicked
                    )

                    with ui.VStack():
                        ui.Spacer()
                        with ui.HStack():
                            ui.Spacer()
                            ui.Label("This is a test for PopupWindow")
                            ui.Spacer()
                        ui.Spacer()

                    with ui.Placer(offset_x=20, offset_y=200):
                        style = {"Rectangle": {"background_color": 0xFFFF0000}}
                        ui.Rectangle(style=style, width=360, height=60)

        window = NoTitleWindow()
        self.assertIsNotNone(window.get_window_handle())
        window.show(10, 10)
        await ui_test.emulate_keyboard_press(KeyboardInput.ESCAPE)
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100), human_delay_speed=2)
        await wait_frames(3)
        await self.finalize_test(100, self._golden_img_dir, "no_title_window.png")
        window.dock("Viewport")
        window.show(False)
        self.assertFalse(window.is_visible())
        window.destroy()
