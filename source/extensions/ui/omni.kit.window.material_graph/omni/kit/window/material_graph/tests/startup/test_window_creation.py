from pxr import UsdShade

from ..ui_base import MaterialGraphUiTestBase


class TestGraphWindowCreation(MaterialGraphUiTestBase):
    """GraphWindow is the main graph UI window; open_graph loads a material prim and makes the
    window visible. We test that open_graph with a valid material shows the window and that when
    _main_widget never initializes (timeout branch) the async path exits cleanly without hanging."""

    async def test_open_graph_schedules(self) -> None:
        """open_graph makes window visible."""
        material = UsdShade.Material.Define(self._stage, "/Looks/Mat")

        self._graph_window.open_graph(material.GetPrim())
        await self.wait_n_updates(6)

        self.assertTrue(self._graph_window.visible)

    async def test_open_graph_timeout_no_widget(self) -> None:
        """open_graph exits cleanly if widget never initializes."""
        material = UsdShade.Material.Define(self._stage, "/Looks/MatTimeout")

        original_widget = self._graph_window._main_widget
        try:
            self._graph_window._main_widget = None
            self._graph_window.open_graph(material.GetPrim())

            await self.wait_n_updates(61)
            self.assertIsNone(self._graph_window._main_widget)
        finally:
            self._graph_window._main_widget = original_widget
