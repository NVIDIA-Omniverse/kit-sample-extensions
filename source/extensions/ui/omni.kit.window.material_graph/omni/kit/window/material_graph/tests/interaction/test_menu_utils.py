from unittest.mock import MagicMock, patch

from ...scripts.ui.interaction import menu_utils
from ..base import MaterialGraphTestBase


class TestMenuUtils(MaterialGraphTestBase):
    """Menu utility behavior."""

    async def test_show_menu_at_cursor_uses_show_at(self) -> None:
        """show_menu_at_cursor should use show_at when available."""
        menu = MagicMock()

        app_window = MagicMock()
        mouse = MagicMock()
        app_window.get_mouse.return_value = mouse

        input_iface = MagicMock()
        input_iface.get_mouse_coords_pixel.return_value = (100, 200)

        with (
            patch("omni.appwindow.get_default_app_window", return_value=app_window),
            patch("carb.input.acquire_input_interface", return_value=input_iface),
            patch("omni.ui.Workspace.get_dpi_scale", return_value=2.0),
        ):
            menu_utils.show_menu_at_cursor(menu)

        menu.show_at.assert_called_once_with(50, 100)
        menu.show.assert_not_called()

    async def test_show_menu_at_cursor_fallback(self) -> None:
        """show_menu_at_cursor should use fallback position when needed."""
        menu = MagicMock()

        with (
            patch("omni.appwindow.get_default_app_window", return_value=None),
            patch("carb.input.acquire_input_interface", return_value=None),
        ):
            menu_utils.show_menu_at_cursor(menu, fallback_pos=(10, 20))

        menu.show_at.assert_called_once_with(10, 20)

    async def test_show_menu_at_cursor_show_when_no_show_at(self) -> None:
        """show_menu_at_cursor should call show when show_at is missing."""
        menu = MagicMock()
        del menu.show_at

        with (
            patch("omni.appwindow.get_default_app_window", return_value=None),
            patch("carb.input.acquire_input_interface", return_value=None),
        ):
            menu_utils.show_menu_at_cursor(menu, fallback_pos=(10, 20))

        menu.show.assert_called_once()
