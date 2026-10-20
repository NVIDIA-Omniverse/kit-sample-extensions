# pylint: disable=relative-beyond-top-level,no-member
from types import SimpleNamespace
from unittest.mock import patch

from ...scripts.ui.controllers.interaction.coords import get_graph_mouse_position
from ..base import MaterialGraphTestBase
from ..fixtures.graph_stubs import DummyGraphView


class TestGraphCoords(MaterialGraphTestBase):
    """get_graph_mouse_position maps the current mouse position into graph canvas space when the
    cursor is over the graph view, and returns None when outside or when the view is hidden. The
    graph uses this for hit-testing and context menus. We test inside/outside bounds and visibility
    so coordinate-dependent behavior doesn't fire when the user is not over the graph."""

    async def test_graph_coords_outside_returns_none(self) -> None:
        """Returns None when mouse outside graph view."""
        # Patch app window and input so we control mouse position; patch DPI scale for consistent math.
        graph_view = DummyGraphView(computed_width=10, computed_height=10)
        app_window = SimpleNamespace(get_mouse=lambda: 1)
        input_iface = SimpleNamespace(get_mouse_coords_pixel=lambda _mouse: (50, 50))
        with (
            patch("omni.appwindow.get_default_app_window", return_value=app_window),
            patch("carb.input.acquire_input_interface", return_value=input_iface),
            patch("omni.ui.Workspace.get_dpi_scale", return_value=1.0),
        ):
            self.assertIsNone(get_graph_mouse_position(graph_view))

    async def test_graph_coords_inside_returns_position(self) -> None:
        """Returns mouse position when inside graph bounds."""
        # Patch app window and input so mouse is inside the 10x10 view; patch DPI scale.
        graph_view = DummyGraphView(computed_width=10, computed_height=10)
        app_window = SimpleNamespace(get_mouse=lambda: 1)
        input_iface = SimpleNamespace(get_mouse_coords_pixel=lambda _mouse: (5, 5))
        with (
            patch("omni.appwindow.get_default_app_window", return_value=app_window),
            patch("carb.input.acquire_input_interface", return_value=input_iface),
            patch("omni.ui.Workspace.get_dpi_scale", return_value=1.0),
        ):
            self.assertEqual(get_graph_mouse_position(graph_view), (5, 5))

    async def test_graph_coords_hidden_returns_none(self) -> None:
        """Returns None when graph view not visible."""
        graph_view = DummyGraphView(visible=False)
        self.assertIsNone(get_graph_mouse_position(graph_view))
