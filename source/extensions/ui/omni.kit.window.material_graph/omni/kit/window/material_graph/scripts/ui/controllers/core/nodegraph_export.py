"""Controller for registering and executing nodegraph export context-menu actions."""

# pylint: disable=no-member,protected-access
from typing import Optional, Tuple, Union

from pxr import Sdf, Usd, UsdShade

from ....api.context_menu import add_node_menu_item, remove_node_menu_item
from ....commands.export import export_nodegraph
from ....config.logging import logger
from ....utils.lifecycle_registry import LifecycleRegistry


class NodeGraphExportController:
    """Registers the node menu entry to export NodeGraph prims."""

    def __init__(self, widget: object) -> None:
        """Initialize the export controller."""
        self._widget = widget
        self._menu_callbacks: Optional[Tuple[str, object]] = None
        self._lifecycle = LifecycleRegistry()

    def setup_menu_items(self) -> None:
        """Register the export menu item for NodeGraph nodes."""

        def _callback(_node_type_name: str, prim_path: Union[Sdf.Path, str]) -> None:
            """Forward node-menu callback to export handler."""
            self.export_nodegraph(prim_path)

        self._menu_callbacks = ("NodeGraph", _callback)
        add_node_menu_item("Export Nodegraph...", _callback, node_types="NodeGraph")

    def unregister_menu_items(self) -> None:
        """Deregister the export menu item."""
        if not self._menu_callbacks:
            logger.debug("unregister_menu_items skipped: no export menu callbacks were registered")
            return
        _, callback = self._menu_callbacks
        remove_node_menu_item("Export Nodegraph...", callback)
        self._menu_callbacks = None

    def export_nodegraph(self, prim_path: Union[Sdf.Path, str]) -> None:
        """Show export UI for a NodeGraph prim."""
        prim = self._get_prim(prim_path)
        if not prim or not prim.IsA(UsdShade.NodeGraph) or prim.IsA(UsdShade.Material):
            logger.debug("export_nodegraph skipped: selected prim is not an exportable NodeGraph (%s)", prim_path)
            return
        export_nodegraph(prim)

    def _get_prim(self, prim_path: Union[Sdf.Path, str]) -> Optional[Usd.Prim]:
        """Return the prim at a path for the current model."""
        if not prim_path or not self._widget or not self._widget.model:
            logger.debug("get_prim skipped: missing prim path or widget/model context")
            return None
        stage = self._widget.model.stage
        if not stage:
            logger.debug("get_prim skipped: model stage is unavailable")
            return None
        path = Sdf.Path(str(prim_path)) if not isinstance(prim_path, Sdf.Path) else prim_path
        return stage.GetPrimAtPath(path)

    def destroy(self) -> None:
        """Release subscriptions, callbacks, and cached references owned by this controller."""
        self.unregister_menu_items()
        self._lifecycle.cleanup()
        self._lifecycle = None
        self._widget = None
