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

from ..button import BoolImageButton, DashButton, ImageButton, SimpleImageButton
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestButtons(TestWidgetsCustomBase):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR
        self._window = await self.create_test_window(width=360, height=240, block_devices=False)
        self._last_clicked_btn_name = None

        self._hide_main_menu_bar()

    # After running each test
    async def tearDown(self):
        await self.finalize_test_no_image()
        await super().tearDown()
        self._window.destroy()
        self._window = None

    async def reset_window(self):
        self._window.frame.clear()
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)
        await wait_frames(3)

    def _on_clicked(self, button_name, *_):
        self._last_clicked_btn_name = button_name

    async def test_dash_button(self):
        await self.reset_window()
        btn_desc = {
            "dash_button1": ui.Alignment.LEFT,
            "dash_button2": ui.Alignment.CENTER,
            "dash_button3": ui.Alignment.RIGHT,
        }
        image = self._golden_img_dir.parent.joinpath("image.svg").absolute()
        for btn_name, align in btn_desc.items():
            btn = None

            await wait_frames(3)
            self._window.frame.clear()
            await wait_frames(3)
            with self._window.frame:
                with ui.VStack():
                    ui.Spacer(height=20)
                    with ui.HStack():
                        ui.Spacer(width=5)
                        btn = DashButton(
                            name=btn_name,
                            image_source=str(image),
                            image_size=24,
                            alignment=align,
                            clicked_fn=lambda btn_name=btn_name, *_: self._on_clicked(btn_name),
                        )
                    ui.Spacer()
                ui.Spacer()

            await wait_frames(2)
            await self.compare_screen_with_golden(btn_name, golden_img=f"{btn_name}.png")

            await wait_frames(2)
            btn.enabled = False
            await wait_frames(2)
            self.assertFalse(btn.enabled)
            await wait_frames(2)
            btn.enabled = True
            await wait_frames(2)
            self.assertTrue(btn.enabled)
            await wait_frames(2)

            btn._on_clicked()
            await wait_frames(2)
            self.assertEqual(btn_name, self._last_clicked_btn_name)

    async def test_image_button(self, window=None):
        style = {
            "ImageButton": {
                "background_color": 0x00000000,
                "border_width": 1,
                "border_color": 0xFF00FF00,
                "border_radius": 2.0,
            },
            "ImageButton:hovered": {"background_color": 0xFF373737, "border_width": 1, "border_color": 0xFF0000FF},
            "ImageButton:selected": {"background_color": 0xFF1F2123, "border_width": 1, "border_color": 0xFFFF0000},
        }

        await self.reset_window()
        btn_name = "Test"
        with self._window.frame:
            with ui.VStack():
                ui.Spacer(height=20)
                image = self._golden_img_dir.parent.joinpath("image.svg").absolute()
                with ui.HStack():
                    ui.Spacer(width=30)
                    image_button = ImageButton(
                        btn_name,
                        32,
                        32,
                        str(image),
                        clicked_fn=lambda key, x, y, btn_name="ImageButton": self._on_clicked(btn_name, key, x, y),
                        enabled=False,
                    )
                    image_button.create(style=style)

                ui.Spacer()

        await wait_frames(3)
        self.assertFalse(image_button.enabled)
        await self.compare_screen_with_golden("Image-Button-disabled", "image_button-disabled.png")

        image_button.enabled = True
        await wait_frames(3)
        self.assertTrue(image_button.enabled)
        await self.compare_screen_with_golden("Image-Button-0", "image_button-0.png")

        x, y = image_button.get_widget_pos()
        await ui_test.emulate_mouse_move(Vec2(x + 10, y + 10), 2)
        await wait_frames(3)
        await self.compare_screen_with_golden("Image-Button-1", "image_button-1.png")

        await wait_frames(3)
        self._last_clicked_btn_name = ""
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertEqual(self._last_clicked_btn_name, "ImageButton")

        image_button.set_tooltip("ImageButton tooltip")

        def tooltip_fn(widget, name):
            pass

        image_button.set_tooltip_fn(tooltip_fn)

        await wait_frames(3)
        self.assertTrue(image_button.is_visible())
        image_button.set_visible(False)
        await wait_frames(3)
        self.assertFalse(image_button.is_visible())
        image_button.set_visible(True)
        await wait_frames(3)
        self.assertTrue(image_button.is_visible())

        await wait_frames(3)
        image_button.activate(True)
        await wait_frames(3)
        image_button.activate(True)
        await wait_frames(3)
        self.assertTrue(image_button.is_activated())
        image_button.activate(False)
        await wait_frames(3)
        self.assertFalse(image_button.is_activated())

        self.assertTrue(image_button.identify(btn_name))
        self.assertFalse(image_button.identify("Not My Name!"))
        self.assertEqual(image_button.get_name(), btn_name)

        await wait_frames(3)
        await self.reset_window()
        image_button.destroy()
        image_button = None

    async def test_simple_image_button(self, window=None):
        style = {
            "ImageButton": {
                "background_color": 0x00000000,
                "border_width": 1,
                "border_color": 0xFF00FF00,
                "border_radius": 2.0,
            },
            "ImageButton:hovered": {"background_color": 0xFF373737, "border_width": 1, "border_color": 0xFF0000FF},
            "ImageButton:selected": {"background_color": 0xFF1F2123, "border_width": 1, "border_color": 0xFFFF0000},
        }

        await self.reset_window()
        btn_name = "Test"
        with self._window.frame:
            with ui.VStack():
                ui.Spacer(height=20)
                image = self._golden_img_dir.parent.joinpath("image.svg").absolute()
                with ui.HStack():
                    ui.Spacer(width=30)
                    image_button = SimpleImageButton(
                        str(image),
                        32,
                        clicked_fn=None,
                        style=style,
                    )

                ui.Spacer()

        await wait_frames(3)
        self.assertEqual(image_button.clicked_fn, None)
        image_button.clicked_fn = lambda btn_name="SimpleImageButton": self._on_clicked(btn_name)
        self.assertNotEqual(image_button.clicked_fn, None)

        x, y = image_button.get_widget_pos()
        await ui_test.emulate_mouse_move(Vec2(x + 10, y + 10), 2)
        await wait_frames(3)
        self._last_clicked_btn_name = ""
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertEqual(self._last_clicked_btn_name, "SimpleImageButton")

        await wait_frames(3)
        await self.reset_window()
        image_button.destroy()
        image_button = None

    async def test_bool_image_button(self, window=None):
        await self.reset_window()
        image_button = None
        self._window.frame.clear()
        with self._window.frame:
            with ui.VStack():
                ui.Spacer(height=20)
                true_image = self._golden_img_dir.parent.joinpath("smile.png").absolute()
                false_image = self._golden_img_dir.parent.joinpath("sad.png").absolute()
                with ui.HStack():
                    ui.Spacer(width=30)
                    image_button = BoolImageButton(str(true_image), str(false_image), 32)
                    ui.Spacer()

                ui.Spacer()

        await wait_frames(100)
        await self.compare_screen_with_golden("Bool-Image-Button-0", "bool_image_button-0.png")
        self.assertTrue(image_button.state)

        x, y = image_button.get_widget_pos()
        await ui_test.emulate_mouse_move(Vec2(x + 10, y + 10), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)
        await wait_frames(3)
        await self.compare_screen_with_golden("Bool-Image-Button-1", "bool_image_button-1.png")
        self.assertFalse(image_button.state)
