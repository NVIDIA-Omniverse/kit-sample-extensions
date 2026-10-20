# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from unittest.mock import Mock

import carb.input
import omni.kit.ui_test as ui_test
from carb.input import KeyboardInput as Keyboard
from omni.ui.tests.test_base import OmniUiTest

from ..hotkey_helper import Hotkey, HotkeyHelper
from .utils import wait_frames


class TestHotkey(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._hotkey = HotkeyHelper.acquire_reference()

        self._window = await self.create_test_window(width=360, height=240, block_devices=False)

        self._window.position_x = 0
        self._window.position_y = 0
        await wait_frames(3)
        self._window.focus()

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        self._window.destroy()
        self._window = None
        self._hotkey.release()
        self._hotkey = None

    def _on_hotkey(self, key_name):
        print(f"Enter _on_hotkey, name = {key_name}")
        self._key = key_name

    async def test_hotkey(self):
        self._hotkey.register_hotkey(
            Keyboard.T, carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL, lambda name="CTRL+T": self._on_hotkey(name)
        )
        self._hotkey.register_hotkey(Keyboard.T, 0, lambda name="T": self._on_hotkey(name))

        await wait_frames(3)

        # Press CTRL+T
        self._key = ""
        await ui_test.emulate_keyboard_press(Keyboard.T, carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL)
        # await ui_test.emulate_key_combo("CTRL+T")
        await wait_frames(3)
        self.assertEqual(self._key, "CTRL+T")

        # Press CTRL+T
        self._key = ""
        await ui_test.emulate_keyboard_press(Keyboard.T, 0)
        # await ui_test.emulate_key_combo("T")
        await wait_frames(3)
        self.assertEqual(self._key, "T")

        self._key = "Nothing"
        await ui_test.emulate_keyboard_press(Keyboard.T, carb.input.KEYBOARD_MODIFIER_FLAG_ALT)
        # await ui_test.emulate_key_combo("T")
        await wait_frames(3)
        self.assertEqual(self._key, "Nothing")

    async def test_hotkey_02(self):
        mock_action = Mock()
        hot_key = Hotkey(Keyboard.T, mock_action)
        await ui_test.emulate_keyboard_press(Keyboard.T)
        mock_action.assert_called_once()
        hot_key.clean()
