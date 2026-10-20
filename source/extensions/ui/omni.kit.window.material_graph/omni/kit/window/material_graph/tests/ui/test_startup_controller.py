# pylint: disable=relative-beyond-top-level,no-member
from contextlib import contextmanager
from unittest.mock import MagicMock, PropertyMock, patch

from ...scripts.ui.controllers.core.startup import StartupController
from ...scripts.ui.sections.graph.widget import GraphWidget
from ..base import MaterialGraphTestBase


@contextmanager
def _dummy_stack(*_args, **_kwargs):
    yield


class _DummyWidget:
    """Widget stub for startup controller tests."""

    def __init__(self) -> None:
        self.set_toolbar_items = MagicMock()
        self.get_toolbar_items = MagicMock(return_value=["toolbar"])
        self.edit_graph = MagicMock()
        self.new_graph = MagicMock()
        self.on_accept_drop = MagicMock()
        self.on_drop = MagicMock()


class TestStartupController(MaterialGraphTestBase):
    """StartupController behavior."""

    async def test_build_startup_hides_buttons_once(self) -> None:
        """When show_startup_buttons is False, buttons are not built."""
        widget = _DummyWidget()
        controller = StartupController(widget, show_startup_buttons=False)
        with (
            patch("omni.ui.ZStack", _dummy_stack),
            patch("omni.ui.HStack", _dummy_stack),
            patch("omni.ui.VStack", _dummy_stack),
            patch("omni.ui.Rectangle", MagicMock()),
            patch("omni.ui.Button", MagicMock()) as button,
        ):
            controller.build_startup()
            button.assert_not_called()
        self.assertTrue(controller._show_startup_buttons)

    async def test_build_startup_sets_toolbar(self) -> None:
        """Startup should set toolbar items."""
        widget = _DummyWidget()
        controller = StartupController(widget, show_startup_buttons=True)
        with (
            patch("omni.ui.ZStack", _dummy_stack),
            patch("omni.ui.HStack", _dummy_stack),
            patch("omni.ui.VStack", _dummy_stack),
            patch("omni.ui.Rectangle", MagicMock()),
            patch("omni.ui.Button", MagicMock()),
        ):
            controller.build_startup()
        widget.set_toolbar_items.assert_called()

    async def test_reset_rebuilds_startup_and_toolbar_after_loaded_model(self) -> None:
        """Resetting a loaded graph should wire build_fn, rebuild startup frame, and toolbar."""
        widget = GraphWidget.__new__(GraphWidget)
        widget._solo_controller = MagicMock()
        widget._warning_overlay = None
        widget._context_manager = MagicMock()
        widget._catalog_model = MagicMock()
        widget.clear_error = MagicMock()
        widget.clear_warning = MagicMock()
        widget.get_toolbar_items = MagicMock(return_value=[])
        widget.set_toolbar_items = MagicMock()
        startup_frame = MagicMock()
        toolbar_frame = MagicMock()
        widget._GraphEditorCoreWidget__startup_frame = startup_frame
        widget._graph_toolbar_frame = toolbar_frame
        widget._current_context = None

        with patch.object(GraphWidget, "model", new_callable=PropertyMock) as model:
            model.return_value = object()
            GraphWidget.reset(widget)

        startup_frame.set_build_fn.assert_called_once_with(widget.on_build_startup)
        startup_frame.rebuild.assert_called_once()
        toolbar_frame.rebuild.assert_called_once()
