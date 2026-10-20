# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from functools import partial

import carb
import carb.input


class HotkeyHelper:
    __singleton = None
    __ref_count = 0

    def __init__(self):
        self._hotkeys = {}
        self._keyboard_sub = None

    def __del__(self):
        self._cleanup()

    @staticmethod
    def acquire_reference():
        if not HotkeyHelper.__singleton:
            HotkeyHelper.__singleton = HotkeyHelper()

        HotkeyHelper.__ref_count += 1
        return HotkeyHelper.__singleton

    def release(self):
        HotkeyHelper.__ref_count -= 1
        if HotkeyHelper.__ref_count == 0:
            HotkeyHelper.__singleton = None

    def _setup(self):
        if not self._keyboard_sub:
            self._input = carb.input.acquire_input_interface()
            self._keyboard_sub = self._input.subscribe_to_keyboard_events(None, self._on_keyboard)

    def _cleanup(self):
        if self._keyboard_sub:
            self._input.unsubscribe_to_keyboard_events(None, self._keyboard_sub)
            self._input = None
            self._keyboard_sub = None

    def register_hotkey(self, key, modifier: int, fn: callable) -> bool:
        if key in self._hotkeys:
            hotkey = self._hotkeys[key]
            if modifier in hotkey:
                carb.log_error(f"Hot key already registered: {key} + {modifier}!")
                return False
            hotkey[modifier] = fn
        else:
            hotkey = {}
            hotkey[modifier] = fn
            self._hotkeys[key] = hotkey

        if not self._keyboard_sub:
            self._setup()

    def deregister_hotkey(self, key, modifier):
        if key not in self._hotkeys:
            return

        hotkey = self._hotkeys[key]
        if modifier not in hotkey:
            return

        hotkey.pop(modifier)
        if len(hotkey) == 0:
            self._hotkeys.pop(key)
            if len(self._hotkeys) == 0:
                self._cleanup()

    def _on_keyboard(self, event, *args, **kwargs):
        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            if event.input in self._hotkeys:
                hotkey = self._hotkeys[event.input]
                if event.modifiers in hotkey:
                    hotkey[event.modifiers]()
        return True


class Hotkey:
    def __init__(self, hotkey, on_action_fn: callable, modifier=0, hotkey_enabled_fn: callable = None):
        self._hotkey_helper = HotkeyHelper.acquire_reference()
        self._key = hotkey
        self._modifier = modifier

        def action_trigger(on_action_fn, hotkey_enabled_fn):
            if hotkey_enabled_fn is not None and not hotkey_enabled_fn():
                return

            if on_action_fn is not None:
                on_action_fn()

        self._hotkey_helper.register_hotkey(
            self._key, self._modifier, partial(action_trigger, on_action_fn, hotkey_enabled_fn)
        )

    def clean(self):
        self._hotkey_helper.deregister_hotkey(self._key, self._modifier)
        self._hotkey_helper.release()
        self._hotkey_helper = None
