from unittest.mock import MagicMock

from ..ui_base import MaterialGraphUiTestBase


class TestGraphWindowUi(MaterialGraphUiTestBase):
    """Graph window initialization behavior."""

    async def test_window_initializes_widget(self) -> None:
        """Graph window should create a widget."""
        self.assertIsNotNone(self._window_handle)
        self.assertIsNotNone(self._graph_window.graph_widget)

    async def test_visibility_change_updates_widget(self) -> None:
        """Visibility changes should propagate to the widget."""
        widget = self._graph_window.graph_widget
        widget.set_visibility = MagicMock()

        self._graph_window._visibility_changed_fn(True)
        self._graph_window._visibility_changed_fn(False)

        widget.set_visibility.assert_any_call(True)
        widget.set_visibility.assert_any_call(False)
