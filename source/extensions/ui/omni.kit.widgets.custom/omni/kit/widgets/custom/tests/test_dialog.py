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

import carb
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.ui_test.vec2 import Vec2

from ..dialog import Dialog, InputDialog, MessageDialog, QuestionDialog
from ..prompt import Prompt
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestDialog(TestWidgetsCustomBase):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR

        self._hide_main_menu_bar()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    def _on_dialog_button(self, btn_name):
        self._btn_clicked = btn_name

    async def test_Dialog(self):
        window = Dialog("Dialog", "Hello world", icon=Dialog.ICON_NOTIFICATION, width=480, height=320)
        window.add_button("Click", False, lambda name="Click": self._on_dialog_button(name))
        window.add_button("Close", True, lambda name="Close": self._on_dialog_button(name))
        window.show(False)
        window._window.position_x = 0
        window._window.position_y = 0

        await wait_frames(3)
        await self.create_test_area(480, 320, False)
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)
        await self.compare_screen_with_golden("Dialog", golden_img="dialog.png")

        await ui_test.emulate_mouse_move(Vec2(160, 280), 2)
        await wait_frames(3)
        self._btn_clicked = ""
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertEqual(self._btn_clicked, "Click")

        await ui_test.emulate_mouse_move(Vec2(320, 280), 2)
        await wait_frames(3)
        self._btn_clicked = ""
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertEqual(self._btn_clicked, "Close")
        self.assertFalse(window._window.visible)

        window = Dialog("Dialog", "Hello world", icon=Dialog.ICON_NOTIFICATION, width=480, height=320)
        window.add_button("Click", False, lambda name="Click": self._on_dialog_button(name))
        window.show(False)
        window._window.position_x = 0
        window._window.position_y = 0
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(320, 280), 2)
        await wait_frames(3)
        self._btn_clicked = ""
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertFalse(window._window.visible)

    async def test_MessageDialog(self):
        window = MessageDialog("MessageDialog", "Hello world")
        window._window.position_x = 0
        window._window.position_y = 0

        await wait_frames(3)
        await self.create_test_area(Dialog.DEFAULT_WIDTH, Dialog.DEFAULT_HEIGHT, False)
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)
        await self.compare_screen_with_golden("MessageDialog", golden_img="message_dialog.png")

        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(Dialog.DEFAULT_WIDTH / 2, 220), 2)
        await wait_frames(3)
        # Right click wont close the dialog
        await ui_test.emulate_mouse_click(True)
        await wait_frames(3)
        self.assertTrue(window._window.visible)
        # Left click wil close the dialog
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertFalse(window._window.visible)

    async def test_QuestionDialog(self):
        window = QuestionDialog(
            "QuestionDialog",
            "Is this a question dialog?",
            lambda btn_name="Yes": self._on_dialog_button(btn_name),
            True,
            Dialog.DEFAULT_WIDTH,
            lambda btn_name="No": self._on_dialog_button(btn_name),
        )

        await wait_frames(3)
        self.assertTrue(window._window.visible)
        window._window.position_x = 0
        window._window.position_y = 0
        await wait_frames(3)
        await self.create_test_area(Dialog.DEFAULT_WIDTH, Dialog.DEFAULT_HEIGHT, False)
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)
        await self.compare_screen_with_golden("QuestionDialog", golden_img="question_dialog.png")

        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(130, 220), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertFalse(window._window.visible)
        self.assertEqual(self._btn_clicked, "Yes")

        window = QuestionDialog(
            "QuestionDialog",
            "Is this a question dialog?",
            lambda btn_name="Yes": self._on_dialog_button(btn_name),
            False,
            Dialog.DEFAULT_WIDTH,
            lambda btn_name="No": self._on_dialog_button(btn_name),
        )

        window.show(False)
        await wait_frames(3)
        self.assertTrue(window._window.visible)
        window._window.position_x = 0
        window._window.position_y = 0

        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(260, 220), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertFalse(window._window.visible)
        self.assertEqual(self._btn_clicked, "No")

        await self.finalize_test_no_image()

    async def test_InputDialog(self):
        window = InputDialog(
            "InputDialog test - String",
            InputDialog.INPUT_TYPE_STRING,
            self._on_dialog_button,
            "",
            "Input a string",
            None,
            lambda btn_name="Cancel": self._on_dialog_button(btn_name),
            Dialog.ICON_NOTIFICATION,
            480,
            320,
        )

        window._window.position_x = 0
        window._window.position_y = 0
        await wait_frames(3)
        await self.create_test_area(480, 320, False)
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)
        await self.compare_screen_with_golden("InputDialog", golden_img="input_dialog.png")

        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(240, 96), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        await ui_test.emulate_char_press("String")
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(140, 280), 2)
        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertFalse(window._window.visible)
        self.assertEqual(self._btn_clicked, "String")

        window = InputDialog(
            "InputDialog test - String",
            InputDialog.INPUT_TYPE_STRING,
            self._on_dialog_button,
            "",
            "Input a string",
            None,
            lambda btn_name="Cancel": self._on_dialog_button(btn_name),
            Dialog.ICON_NOTIFICATION,
            480,
            320,
        )

        window._window.position_x = 0
        window._window.position_y = 0
        await wait_frames(3)
        await self.create_test_area(480, 320, False)
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(340, 280), 2)
        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertFalse(window._window.visible)
        self.assertEqual(self._btn_clicked, "Cancel")

        window = InputDialog(
            "InputDialog test - Int",
            InputDialog.INPUT_TYPE_INT,
            self._on_dialog_button,
            0,
            "Input an Int",
            None,
            lambda btn_name="Cancel": self._on_dialog_button(btn_name),
            Dialog.ICON_NOTIFICATION,
            480,
            320,
        )

        window._window.position_x = 0
        window._window.position_y = 0
        await wait_frames(3)
        await self.create_test_area(480, 320, False)
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(240, 96), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        await ui_test.emulate_char_press("120")
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(140, 280), 2)
        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertFalse(window._window.visible)
        self.assertEqual(self._btn_clicked, 120)

        window = InputDialog(
            "InputDialog test - Float",
            InputDialog.INPUT_TYPE_FLOAT,
            self._on_dialog_button,
            0.0,
            "Input a Float",
            None,
            lambda btn_name="Cancel": self._on_dialog_button(btn_name),
            Dialog.ICON_NOTIFICATION,
            480,
            320,
        )

        window._window.position_x = 0
        window._window.position_y = 0
        await wait_frames(3)
        await self.create_test_area(480, 320, False)
        await wait_frames(30)
        await ui_test.emulate_mouse_move(Vec2(240, 96), 2)
        await wait_frames(30)
        await ui_test.emulate_mouse_click(double=True)
        await wait_frames(30)
        await ui_test.emulate_char_press("3.14")
        await wait_frames(30)
        await ui_test.emulate_mouse_move(Vec2(140, 280), 2)
        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertFalse(window._window.visible)
        self.assertTrue(abs(self._btn_clicked - 3.14) < 0.001)

        await self.finalize_test_no_image()

    async def test_Prompt(self):
        window = Prompt(
            "Prompt test",
            "This is something to prompt",
            "Confirm",
            "Cancel",
            "Middle",
            lambda btn_name="Confirm": self._on_dialog_button(btn_name),
            lambda btn_name="Cancel": self._on_dialog_button(btn_name),
            lambda btn_name="Middle": self._on_dialog_button(btn_name),
        )

        await wait_frames(3)
        window.show()
        await wait_frames(3)
        window._window.position_x = 0
        window._window.position_y = 0
        window._window.width = 480
        window._window.height = 320
        await wait_frames(3)

        await self.create_test_area(480, 320, False)
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(1, 1), 2)
        await wait_frames(3)
        # Non-button is hovered
        await self.compare_screen_with_golden("Prompt", golden_img="prompt-0.png")

        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(180, 70), 2)
        # Confirm button is hovered
        await self.compare_screen_with_golden("Prompt", golden_img="prompt-1.png")

        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(240, 70), 2)
        # Middle button is hovered
        await self.compare_screen_with_golden("Prompt", golden_img="prompt-2.png")

        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(300, 70), 2)
        # Cancel button is hovered
        await self.compare_screen_with_golden("Prompt", golden_img="prompt-3.png")

        # Click confirm button
        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(180, 70), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertEqual(self._btn_clicked, "Confirm")
        self.assertFalse(window._window.visible)
        window.show()
        await wait_frames(3)

        # Click middle button
        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(240, 70), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertEqual(self._btn_clicked, "Middle")
        self.assertFalse(window._window.visible)
        window.show()
        await wait_frames(3)

        # Click cancel button
        self._btn_clicked = ""
        await wait_frames(3)
        await ui_test.emulate_mouse_move(Vec2(300, 70), 2)
        await wait_frames(3)
        await ui_test.emulate_mouse_click()
        await wait_frames(3)
        self.assertEqual(self._btn_clicked, "Cancel")
        self.assertFalse(window._window.visible)

        await self.finalize_test_no_image()
