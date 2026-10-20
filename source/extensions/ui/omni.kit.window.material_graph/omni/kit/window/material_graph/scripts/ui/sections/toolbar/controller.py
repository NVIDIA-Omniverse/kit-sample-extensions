"""Toolbar controller that wires actions, menus, and context-aware button state."""

import webbrowser
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import omni.kit.undo
import omni.ui
from omni.kit.widget.graph import GraphModel
from pxr import Gf, Sdf, Usd, UsdShade

from ....commands.wrappers.isolation import DeleteInputOutputNodes
from ....commands.wrappers.prims import DeletePrims, GroupNodeGraph, UngroupNodeGraph
from ....config.logging import logger
from ....config.paths import Paths
from ....models.graph.nodes.prim.model import PrimModel
from ....utils.async_utils import wait_for_updates
from ....utils.lifecycle_registry import LifecycleRegistry
from .actions import ToolbarActionRegistry
from .item_builder import ToolbarItemBuilder
from .menus import ToolbarMenuBuilder

# pylint: disable=no-member


class ToolbarController:
    """Controls toolbar actions and menus."""

    def __init__(
        self,
        widget: object,
        ext_name: str,
        window_name: str,
        ext_manager: object,
        context_switcher: object,
    ) -> None:
        """Initialize toolbar state, actions, and subscriptions required by the toolbar UI."""
        self._widget = widget
        self._ext_name = ext_name
        self._window_name = window_name
        self._ext_manager = ext_manager
        self._context_switcher = context_switcher
        self._lifecycle = LifecycleRegistry()
        self._help_window = None
        self._menu_builder = ToolbarMenuBuilder(window_name)
        self._action_registry = ToolbarActionRegistry(
            Paths.MODULE_ID,
            window_name,
            ext_manager,
            {
                "delete_nodes": self.delete_nodes,
                "focus_nodes": self.focus_nodes,
                "layout_nodes": self.layout_nodes,
                "group_nodes": self.group_selected_nodes,
                "ungroup_nodegraph": self.ungroup_selected_nodegraphs,
                "expansion_state": self._apply_expansion_state,
                "toggle_pause": self.toggle_material_compilation,
                "unpause_and_pause": self.unpause_and_pause,
            },
        )

    def on_toolbar_create_graph_clicked(self) -> None:
        """Handle create-graph button clicks by invoking the configured graph creation flow."""
        self._widget.new_graph()

    def on_toolbar_edit_graph_clicked(self) -> None:
        """Handle edit-graph button clicks by invoking graph edit/open workflow commands."""
        self._widget.edit_graph()

    def on_toolbar_expansion_state_clicked(self, state: GraphModel.ExpansionState) -> None:
        """Set expansion state for all nodes."""
        if self._widget.model:
            with omni.kit.undo.group():
                for node in self._widget.model.nodes:
                    self._widget.model[node].expansion_state = state

    def _apply_expansion_state(self, state_name: str) -> None:
        """Translate a state name and apply expansion."""
        mapping = {
            "open": GraphModel.ExpansionState.OPEN,
            "minimized": GraphModel.ExpansionState.MINIMIZED,
            "closed": GraphModel.ExpansionState.CLOSED,
        }
        state = mapping.get(state_name)
        if state is not None:
            self.on_toolbar_expansion_state_clicked(state)

    def on_toolbar_edit_clicked(self) -> None:
        """Open the Edit menu anchored to toolbar actions."""
        self._menu_builder.show_edit_menu()

    def on_toolbar_view_clicked(self) -> None:
        """Open the View menu with actions enabled by current model state."""
        self._menu_builder.show_view_menu(
            bool(self._widget.model), self.layout_nodes, self.focus_nodes, self._apply_expansion_state
        )

    def on_toolbar_overflow_clicked(self) -> None:
        """Open the combined Edit + View + Help overflow menu."""
        self._menu_builder.show_overflow_menu(
            bool(self._widget.model),
            self.layout_nodes,
            self.focus_nodes,
            self._apply_expansion_state,
            self.on_toolbar_help_clicked,
        )

    def on_toolbar_help_clicked(self) -> None:
        """Display user documentation in browser."""
        webbrowser.open(Paths.DOCS_URL)

    def toggle_material_compilation(self) -> None:
        """Toggle material compilation pause state."""
        if not self._widget.model:
            return
        self._widget.model.pause = not self._widget.model.pause
        self._widget.rebuild_graph_toolbar()

    def unpause_and_pause(self) -> None:
        """Temporarily unpause and then re-pause."""

        async def toggle_pause() -> None:
            """Toggle pause state with a short delay."""
            self._widget.model.pause = not self._widget.model.pause
            await wait_for_updates(
                lambda: bool(self._widget.model and not self._widget.model.pause),
                max_updates=100,
                timeout_message="pause toggle timed out",
            )
            if self._widget.model:
                self._widget.model.pause = not self._widget.model.pause

        if not self._widget.model or not self._widget.model.pause:
            return

        self._lifecycle.add_task(toggle_pause())

    def get_toolbar_items(self, add_pause_button: bool) -> List[Dict[str, Any]]:
        """Return toolbar item descriptors."""
        return ToolbarItemBuilder(self, add_pause_button).build()

    def switch_context(self, context_name: str) -> None:
        """Switch render context and rebuild the graph toolbar to update active state."""
        solo = getattr(self._widget, "_solo_controller", None)
        was_soloed = solo and solo.soloed_context is not None
        if was_soloed:
            solo.clear()
        try:
            self._widget.set_context(context_name)
        except (RuntimeError, ValueError) as exc:
            logger.error("failed to switch context '%s': %s", context_name, exc)
            return
        if was_soloed and solo:
            solo.toggle_solo(context_name)
        else:
            self._widget.rebuild_graph_toolbar()

    def setup_actions_and_hotkeys(self) -> None:
        """Register actions and hotkeys."""
        self._action_registry.setup_actions_and_hotkeys()

    def clear_actions_and_hotkeys(self) -> None:
        """Deregister actions and hotkeys."""
        self._action_registry.clear_actions_and_hotkeys()

    def destroy(self) -> None:
        """Release subscriptions, callbacks, and cached references owned by this controller."""
        if self._help_window:
            self._help_window.destroy()
            self._help_window = None
        self._lifecycle.cleanup()
        self._lifecycle = None
        self._action_registry = None
        self._menu_builder = None
        self._context_switcher = None
        self._graph_view = None
        self._isolation_model = None
        self._widget = None

    def focus_nodes(self) -> None:
        """Focus the graph view on selected nodes."""
        graph_view = self._widget.graph_view
        if not graph_view:
            return
        graph_view.focus_on_nodes(graph_view.selection)

    def layout_nodes(self) -> None:
        """Layout nodes and then frame the view."""

        async def layout_and_focus() -> None:
            """Layout nodes, wait, then focus."""
            graph_view = self._widget.graph_view
            if not graph_view:
                return
            graph_view.layout_all()
            for _ in range(5):
                await omni.kit.app.get_app().next_update_async()
            graph_view.focus_on_nodes()

        self._lifecycle.add_task(layout_and_focus())

    def delete_nodes(self) -> None:
        """Delete selected nodes/prims, or disconnect a hovered connection."""
        graph_view = self._widget.graph_view
        if graph_view and graph_view.hovered_connection_index >= 0:
            if graph_view.disconnect_hovered_connection():
                return

        isolation_model = self._widget.isolation_model
        selection = isolation_model.selection if isolation_model else None
        if not selection:
            catalog = self._widget._catalog_widget if self._widget else None
            if catalog and catalog.should_block_delete_nodes():
                return
            return

        nodes = [n for n in selection if self._is_input_output_node(n)]
        if nodes:
            delete_io_result = DeleteInputOutputNodes(isolation_model, nodes, self._widget.model)
            if not delete_io_result.success:
                logger.warning(
                    "delete input/output nodes failed nodes=%s: %s; those nodes remain in the graph",
                    [getattr(node, "path", getattr(node, "name", "<unknown>")) for node in nodes],
                    delete_io_result.error_code or delete_io_result.message or "command returned no reason",
                )

        paths = list({n.path for n in selection if isinstance(n, PrimModel)})
        if paths:
            model = self._widget.model
            stage = model.stage if model else None
            if stage:
                paths = [path for path in paths if stage.GetPrimAtPath(path)]
            if paths:
                delete_result = DeletePrims(paths=paths, stage=stage)
                if not delete_result.success:
                    logger.warning(
                        "delete nodes failed targets=%s: %s; the delete transaction was not committed",
                        [str(path) for path in paths],
                        delete_result.error_code or delete_result.message or "command returned no reason",
                    )

    @staticmethod
    def _is_input_output_node(node: object) -> bool:
        """Return True for isolation InputNode/OutputNode wrappers."""
        try:
            return type(node).get_type_name() in {"InputNode", "OutputNode"}
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return False

    def group_selected_nodes(self) -> None:
        """Group selected nodes into a new NodeGraph."""
        model = self._widget.model
        if not model or not model.selection:
            return

        selection = [item for item in model.selection if isinstance(item, PrimModel)]
        if len(selection) < 1:
            return

        stage = model.stage
        if not stage:
            return

        root_path = model.prim_path
        if not root_path:
            return

        parent_path = selection[0].prim_path.GetParentPath()
        if (
            not parent_path
            or not parent_path.HasPrefix(root_path)
            or any(item.prim_path.GetParentPath() != parent_path for item in selection)
        ):
            logger.warning(
                "group rejected: selected nodes must share one parent under graph %s; selected=%s",
                root_path,
                ", ".join(str(item.prim_path) for item in selection),
            )
            return

        position = self._get_average_position(selection)
        position_key, visibility = self._widget._graph_settings_controller.get_nodegraph_drop_settings()

        selected_paths = [item.prim_path.pathString for item in selection]
        group_result = GroupNodeGraph(
            parent_path=parent_path,
            selected_paths=selected_paths,
            position=position,
            position_key=position_key,
            context_visibility=visibility,
            stage=stage,
        )
        if not group_result.success:
            logger.warning(
                "group nodegraph failed parent='%s' selected=%s: %s; selected nodes were not grouped",
                parent_path,
                selected_paths,
                group_result.error_code or group_result.message or "command returned no reason",
            )
        self._widget.request_model_refresh()

    def ungroup_selected_nodegraphs(self) -> None:
        """Ungroup selected NodeGraph prims."""
        model = self._widget.model
        if not model or not model.selection:
            return

        selection = [
            item
            for item in model.selection
            if isinstance(item, PrimModel) and item.prim and item.prim.IsA(UsdShade.NodeGraph)
        ]
        if not selection:
            return

        stage = model.stage
        if not stage:
            return

        for item in selection:
            ungroup_result = UngroupNodeGraph(nodegraph_path=item.prim_path, stage=stage)
            if not ungroup_result.success:
                logger.warning(
                    "ungroup nodegraph failed for '%s': %s; the nodegraph was preserved",
                    item.prim_path,
                    ungroup_result.error_code or ungroup_result.message or "command returned no reason",
                )
        self._widget.request_model_refresh()

    def _get_average_position(self, selection: Sequence[PrimModel]) -> Optional[Gf.Vec2f]:
        """Return the average node position for a selection."""
        positions = []
        for item in selection:
            position = item.position
            if position is not None:
                positions.append(Gf.Vec2f(position))
        if not positions:
            return None
        avg = sum((pos for pos in positions), Gf.Vec2f(0.0, 0.0)) / len(positions)
        return avg
