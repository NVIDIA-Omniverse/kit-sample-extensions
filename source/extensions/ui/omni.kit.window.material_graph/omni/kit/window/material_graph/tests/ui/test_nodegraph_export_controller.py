# pylint: disable=relative-beyond-top-level,no-member
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.ui.controllers.core.nodegraph_export import NodeGraphExportController
from ..base import MaterialGraphTestBase


class _DummyWidget:
    """Widget stub for nodegraph export controller."""

    def __init__(self, stage):
        self.model = MagicMock(stage=stage)


class TestNodeGraphExportController(MaterialGraphTestBase):
    """NodeGraph export controller behavior."""

    async def test_setup_and_unregister_menu(self) -> None:
        """Menu registration should add and remove entries."""
        widget = _DummyWidget(self._stage)
        controller = NodeGraphExportController(widget)
        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.controllers.core.nodegraph_export.add_node_menu_item",
                autospec=True,
            ) as register,
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.controllers.core.nodegraph_export.remove_node_menu_item",
                autospec=True,
            ) as deregister,
        ):
            controller.setup_menu_items()
            register.assert_called()
            controller.unregister_menu_items()
            deregister.assert_called()

    async def test_export_nodegraph_filters_materials(self) -> None:
        """Export should only run for NodeGraph prims."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/Nodegraph"))
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/Material"))
        widget = _DummyWidget(self._stage)
        controller = NodeGraphExportController(widget)
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.core.nodegraph_export.export_nodegraph",
            autospec=True,
        ) as export:
            controller.export_nodegraph(nodegraph.GetPath())
            controller.export_nodegraph(material.GetPath())
            export.assert_called_once()
