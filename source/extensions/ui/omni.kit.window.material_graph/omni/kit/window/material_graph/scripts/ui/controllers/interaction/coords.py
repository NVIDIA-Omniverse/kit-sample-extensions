"""Coordinate conversion helpers for mapping screen pointers into graph canvas space."""

from typing import Any, Optional, Tuple

import carb.input
import omni.appwindow
import omni.ui


def get_graph_mouse_position(graph_view: Any) -> Optional[Tuple[float, float]]:
    """Return mouse position in graph coordinates if inside the view."""
    if not graph_view or not graph_view.visible:
        return None

    zoom = graph_view.zoom
    app_window = omni.appwindow.get_default_app_window()
    input_iface = carb.input.acquire_input_interface()
    if not app_window or not input_iface:
        return None
    dpi_scale = omni.ui.Workspace.get_dpi_scale()
    pos_x, pos_y = input_iface.get_mouse_coords_pixel(app_window.get_mouse())
    pos_x = pos_x / dpi_scale / zoom
    pos_y = pos_y / dpi_scale / zoom

    screen_x = graph_view.screen_position_x
    screen_y = graph_view.screen_position_y
    screen_w = graph_view.computed_width
    screen_h = graph_view.computed_height

    if screen_x < pos_x < screen_x + screen_w and screen_y < pos_y < screen_y + screen_h:
        return (pos_x, pos_y)
    return None
