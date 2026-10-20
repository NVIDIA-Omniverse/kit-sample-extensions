from types import SimpleNamespace

from ...scripts.ui.controllers.core.context_switcher import ContextSwitcherController
from ..base import MaterialGraphTestBase


class _FakeWidget:
    """Widget stub for context switcher tests."""

    def __init__(self) -> None:
        self.current_context = None
        self.model = object()
        self._graph_toolbar_frame = None

    def set_context(self, context_name: str) -> None:
        self.current_context = context_name

    def rebuild_graph_toolbar(self) -> None:
        pass


class _FakeContextManager:
    """Context manager stub returning plugin list."""

    def __init__(self, plugins):
        self._plugins = plugins

    def get_plugins(self):
        return self._plugins


class TestContextSwitcherController(MaterialGraphTestBase):
    """ContextSwitcherController always enables context tabs and delegates rendering to the graph toolbar."""

    async def test_use_context_tabs_always_true(self) -> None:
        """use_context_tabs always returns True."""
        widget = _FakeWidget()
        manager = _FakeContextManager([])
        controller = ContextSwitcherController(widget, manager)
        self.assertTrue(controller.use_context_tabs)
        controller.destroy()

    async def test_refresh_tabs_tolerates_no_widget(self) -> None:
        """refresh_tabs does not raise when widget is None."""
        widget = _FakeWidget()
        manager = _FakeContextManager([])
        controller = ContextSwitcherController(widget, manager)
        controller._widget = None
        controller.refresh_tabs()
        controller.destroy()

    async def test_destroy_clears_references(self) -> None:
        """destroy releases all references."""
        widget = _FakeWidget()
        manager = _FakeContextManager([])
        controller = ContextSwitcherController(widget, manager)
        controller.destroy()
        self.assertIsNone(controller._widget)
        self.assertIsNone(controller._context_manager)
