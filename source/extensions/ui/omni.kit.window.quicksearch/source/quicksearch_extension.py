# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import carb.input
import omni.appwindow
import omni.ext
import omni.kit.commands

from .calculator_model import CalculatorModel
from .quicksearch_registry import QuickSearchRegistry
from .quicksearch_window import QuickSearchWindow


class QuickSearchExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self.__ext_id = omni.ext.get_extension_name(ext_id)
        self._hotkey = None
        self.__register_hotkey()

        # The default model is Calculator
        self._subscription = QuickSearchRegistry().register_quick_search_model("Calculator", CalculatorModel, None)

        # Window
        self._window = None

    def on_shutdown(self):
        self.__deregister_hotkey()

        self._subscription = None

        if self._window:
            self._window.destroy()
            self._window = None

    def __register_hotkey(self):
        try:
            from omni.kit.actions.core import get_action_registry
            from omni.kit.hotkeys.core import KeyCombination, get_hotkey_registry

            # In previous hotkeys.core, TAB is not a valid key
            key = KeyCombination(carb.input.KeyboardInput.TAB)
            if not key.as_string:
                raise ImportError

            # Register action and hotkey
            ACTION_ID = "ShowWindow"
            ACTION_DISPLAY_NAME = "QuickSearch->ShowWindow"
            self._action_registry = get_action_registry()
            self._action = self._action_registry.register_action(
                self.__ext_id, ACTION_ID, lambda: self.show_window(), display_name=ACTION_DISPLAY_NAME
            )
            self._hotkey_registry = get_hotkey_registry()
            self._hotkey = self._hotkey_registry.register_hotkey(self.__ext_id, key, self.__ext_id, ACTION_ID)

        except ImportError:
            # Watch the keyboard
            appwindow = omni.appwindow.get_default_app_window()
            keyboard = appwindow.get_keyboard()
            input = carb.input.acquire_input_interface()
            self._keyboard_sub_id = input.subscribe_to_keyboard_events(keyboard, self.on_input)

    def __deregister_hotkey(self):
        if self._hotkey:
            self._hotkey_registry.deregister_all_hotkeys_for_extension(self.__ext_id)
            self._hotkey = None
            self._action_registry.deregister_all_actions_for_extension(self.__ext_id)
            self._action = None
        else:
            # Unsubscribe the keyboard
            appwindow = omni.appwindow.get_default_app_window()
            keyboard = appwindow.get_keyboard()
            input = carb.input.acquire_input_interface()
            input.unsubscribe_to_keyboard_events(keyboard, self._keyboard_sub_id)
            self._keyboard_sub_id = None

    def on_input(self, event):
        """The keyboard callback"""
        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            if event.modifiers == 0 and event.input == carb.input.KeyboardInput.TAB:
                self.show_window()

        # Don't block the keyboard.
        return True

    def show_window(self):
        if not self._window:
            self._window = QuickSearchWindow()
        else:
            self._window.show()
