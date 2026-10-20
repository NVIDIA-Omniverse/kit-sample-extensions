# pylint: disable=relative-beyond-top-level
from types import SimpleNamespace
from unittest.mock import patch

import carb.input
import omni.kit.test

from ...scripts.utils.modifiers import (
    clear_active_modifier_flags,
    is_force_connection_modifier_pressed,
    set_active_modifier_flags,
)


class _InputWithGetModifierFlags:
    def __init__(self, value: int) -> None:
        self._value = value

    def get_modifier_flags(self, _keyboard: object) -> int:
        return self._value


class _InputWithGetKeyboardModifiers:
    def __init__(self, value: int) -> None:
        self._value = value

    def get_keyboard_modifiers(self) -> int:
        return self._value


class _InputWithButtonFlagsOnly:
    def __init__(self, ctrl_down: bool, shift_down: bool) -> None:
        self._ctrl_down = ctrl_down
        self._shift_down = shift_down

    def get_keyboard_button_flags(self, _keyboard: object, key: int) -> int:
        if self._ctrl_down and key in (
            carb.input.KeyboardInput.LEFT_CONTROL,
            carb.input.KeyboardInput.RIGHT_CONTROL,
        ):
            return int(carb.input.BUTTON_FLAG_DOWN)
        if self._shift_down and key in (
            carb.input.KeyboardInput.LEFT_SHIFT,
            carb.input.KeyboardInput.RIGHT_SHIFT,
        ):
            return int(carb.input.BUTTON_FLAG_DOWN)
        return 0


class TestModifierUtils(omni.kit.test.AsyncTestCase):
    async def test_force_connection_true_with_ctrl_shift(self) -> None:
        """Ctrl+Shift should enable force-connection mode."""
        flags = int(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL) | int(carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
        app_window = SimpleNamespace(get_keyboard=lambda: object())
        try:
            with (
                patch("carb.input.acquire_input_interface", return_value=_InputWithGetModifierFlags(flags)),
                patch("omni.appwindow.get_default_app_window", return_value=app_window),
            ):
                self.assertTrue(is_force_connection_modifier_pressed())
        finally:
            clear_active_modifier_flags()

    async def test_force_connection_false_without_shift(self) -> None:
        """Control-only should not enable force-connection mode."""
        flags = int(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL)
        app_window = SimpleNamespace(get_keyboard=lambda: object())
        try:
            with (
                patch("carb.input.acquire_input_interface", return_value=_InputWithGetModifierFlags(flags)),
                patch("omni.appwindow.get_default_app_window", return_value=app_window),
            ):
                self.assertFalse(is_force_connection_modifier_pressed())
        finally:
            clear_active_modifier_flags()

    async def test_force_connection_supports_keyboard_modifiers_fallback(self) -> None:
        """Fallback API variants should still be handled."""
        flags = int(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL) | int(carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
        try:
            with (
                patch("carb.input.acquire_input_interface", return_value=_InputWithGetKeyboardModifiers(flags)),
                patch("omni.appwindow.get_default_app_window", return_value=SimpleNamespace()),
            ):
                self.assertTrue(is_force_connection_modifier_pressed())
        finally:
            clear_active_modifier_flags()

    async def test_force_connection_prefers_active_event_flags(self) -> None:
        """Active UI-event flags should override input polling."""
        ctrl_shift = int(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL) | int(carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
        try:
            set_active_modifier_flags(ctrl_shift)
            with (
                patch("carb.input.acquire_input_interface", return_value=_InputWithGetModifierFlags(0)),
                patch(
                    "omni.appwindow.get_default_app_window", return_value=SimpleNamespace(get_keyboard=lambda: object())
                ),
            ):
                self.assertTrue(is_force_connection_modifier_pressed())
        finally:
            clear_active_modifier_flags()

    async def test_force_connection_supports_button_flags_fallback(self) -> None:
        """Button-state APIs should still enable force-connection detection."""
        app_window = SimpleNamespace(get_keyboard=lambda: object())
        try:
            with (
                patch(
                    "carb.input.acquire_input_interface",
                    return_value=_InputWithButtonFlagsOnly(ctrl_down=True, shift_down=True),
                ),
                patch("omni.appwindow.get_default_app_window", return_value=app_window),
            ):
                self.assertTrue(is_force_connection_modifier_pressed())
        finally:
            clear_active_modifier_flags()

    async def test_clear_active_modifier_flags_resets_cached_state(self) -> None:
        """Clearing active flags should force a fresh input-interface read."""
        ctrl_shift = int(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL) | int(carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
        try:
            set_active_modifier_flags(ctrl_shift)
            clear_active_modifier_flags()
            app_window = SimpleNamespace(get_keyboard=lambda: object())
            with (
                patch("carb.input.acquire_input_interface", return_value=_InputWithGetModifierFlags(0)),
                patch("omni.appwindow.get_default_app_window", return_value=app_window),
            ):
                self.assertFalse(is_force_connection_modifier_pressed())
        finally:
            clear_active_modifier_flags()
