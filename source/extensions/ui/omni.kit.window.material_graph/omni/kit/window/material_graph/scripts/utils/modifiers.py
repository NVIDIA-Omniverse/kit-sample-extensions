"""Keyboard modifier helpers for graph interactions."""

import threading
from typing import Any, Optional

import carb.input
import omni.appwindow

_active_modifier_flags: Optional[int] = None
_modifier_lock = threading.Lock()


def _flags_from_keyboard_buttons(input_iface: Any, keyboard: Optional[Any]) -> int:
    """Build modifier flags from per-key button state APIs when needed."""
    getter = getattr(input_iface, "get_keyboard_button_flags", None)
    if not callable(getter):
        return 0
    flags = 0
    control_keys = (carb.input.KeyboardInput.LEFT_CONTROL, carb.input.KeyboardInput.RIGHT_CONTROL)
    shift_keys = (carb.input.KeyboardInput.LEFT_SHIFT, carb.input.KeyboardInput.RIGHT_SHIFT)
    for key in control_keys:
        if bool(getter(keyboard, key) & carb.input.BUTTON_FLAG_DOWN):
            flags |= int(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL)
            break
    for key in shift_keys:
        if bool(getter(keyboard, key) & carb.input.BUTTON_FLAG_DOWN):
            flags |= int(carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
            break
    return flags


def _read_modifier_flags(input_iface: Any, app_window: Optional[Any]) -> int:
    """Return the current keyboard modifier flags, or 0 when unavailable."""
    if not input_iface:
        return 0
    keyboard = app_window.get_keyboard() if app_window and hasattr(app_window, "get_keyboard") else None
    for method_name in ("get_modifier_flags", "get_keyboard_modifiers"):
        getter = getattr(input_iface, method_name, None)
        if not callable(getter):
            continue
        if keyboard is not None:
            try:
                return int(getter(keyboard))
            except TypeError:
                pass
        try:
            return int(getter())
        except TypeError:
            continue
    return _flags_from_keyboard_buttons(input_iface, keyboard)


def set_active_modifier_flags(flags: Optional[int]) -> None:
    """Set the active UI-event modifier flags used during interactions."""
    global _active_modifier_flags
    with _modifier_lock:
        _active_modifier_flags = int(flags) if flags is not None else None


def clear_active_modifier_flags() -> None:
    """Clear cached UI-event modifier flags for canceled/ended interactions."""
    global _active_modifier_flags
    with _modifier_lock:
        _active_modifier_flags = None


def is_force_connection_modifier_pressed() -> bool:
    """Return True when Ctrl+Shift is currently held."""
    with _modifier_lock:
        flags = _active_modifier_flags
    if flags is None:
        input_iface = carb.input.acquire_input_interface()
        app_window = omni.appwindow.get_default_app_window()
        flags = _read_modifier_flags(input_iface, app_window)
    required = int(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL) | int(carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
    return (flags & required) == required
