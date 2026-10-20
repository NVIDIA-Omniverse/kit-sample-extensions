"""Implement material graph extension logic for `ui/interaction/menu_utils.py`."""

from typing import Any, Optional, Tuple

import carb.input
import omni.appwindow
import omni.ui

# pylint: disable=no-member


def show_menu_at_cursor(menu: Any, fallback_pos: Optional[Tuple[float, float]] = None) -> None:
    """Show a menu at the cursor position or fallback coordinates."""
    if not menu:
        return
    if hasattr(menu, "show_at"):
        app_window = omni.appwindow.get_default_app_window()
        input_iface = carb.input.acquire_input_interface()
        if app_window and input_iface:
            sx, sy = input_iface.get_mouse_coords_pixel(app_window.get_mouse())
            dpi_scale = omni.ui.Workspace.get_dpi_scale()
            menu.show_at(int(sx / dpi_scale), int(sy / dpi_scale))
            return
        if fallback_pos:
            menu.show_at(int(fallback_pos[0]), int(fallback_pos[1]))
            return
    menu.show()
