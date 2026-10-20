from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, call, patch

import omni.kit.app
import omni.kit.undo
from omni.kit.widget.graph import GraphModel
from pxr import Gf, Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.models.graph.nodes.prim.model import PrimModel
from ...scripts.ui.sections.toolbar import actions as toolbar_actions_module
from ...scripts.ui.sections.toolbar.actions import ToolbarActionRegistry
from ...scripts.ui.sections.toolbar.controller import ToolbarController
from ..ui_base import MaterialGraphUiTestBase


class _DummyModel:
    """Graph model stub with pause and node storage."""

    def __init__(self, paused: bool = False) -> None:
        """Initialize pause state and node map."""
        self._pause = paused
        self.pause_history = []
        self.nodes = []
        self._node_map = {}

    @property
    def pause(self) -> bool:
        """Return the current pause state."""
        return self._pause

    @pause.setter
    def pause(self, value: bool) -> None:
        """Update the pause state and track history."""
        self._pause = value
        self.pause_history.append(value)

    def add_node(self, key: str) -> SimpleNamespace:
        """Add a node and return its namespace wrapper."""
        node = SimpleNamespace(expansion_state=None)
        self.nodes.append(key)
        self._node_map[key] = node
        return node

    def __getitem__(self, key: str | None) -> SimpleNamespace:
        """Return a node namespace or a placeholder."""
        if key is None:
            return SimpleNamespace(nodes=[])
        return self._node_map[key]


class _DummyWidget:
    """Widget stub used by toolbar controller tests."""

    def __init__(self) -> None:
        """Initialize widget stubs and mocks."""
        self.model = None
        self.graph_view = MagicMock()
        self.current_context = None
        self.isolation_model = None
        self.set_toolbar_items = MagicMock()
        self.get_toolbar_items = MagicMock(return_value=["items"])

    def new_graph(self) -> None:
        """No-op new graph handler."""
        pass

    def edit_graph(self) -> None:
        """No-op edit graph handler."""
        pass

    def rebuild_graph_toolbar(self) -> None:
        """No-op graph toolbar rebuild."""
        pass


def _prim_item(path: str, position=(0.0, 0.0)) -> PrimModel:
    # This deliberately bypasses PrimModel.__init__ for toolbar-only tests.
    # Keep _prim_path as Sdf.Path and _ui_state.position as Gf.Vec2f if
    # ToolbarController or PrimModel internals change.
    item = PrimModel.__new__(PrimModel)
    item._prim_path = Sdf.Path(path)
    item._path = item._prim_path
    item._ui_state = SimpleNamespace(position=Gf.Vec2f(*position))
    return item


class TestToolbarControllerUi(MaterialGraphUiTestBase):
    """Toolbar controller UI interactions."""

    async def setUp(self) -> None:
        """Initialize the toolbar controller with a dummy widget."""
        await super().setUp()
        self._widget = _DummyWidget()
        self._context_switcher = SimpleNamespace(use_context_tabs=True)
        ext_manager = omni.kit.app.get_app_interface().get_extension_manager()
        self._toolbar = ToolbarController(
            self._widget,
            "material_graph",
            "Material Graph",
            ext_manager,
            self._context_switcher,
        )

    async def test_focus_nodes_uses_selection(self) -> None:
        """Focus should use current graph view selection."""
        self._widget.graph_view.selection = ["node_a"]
        self._toolbar.focus_nodes()

        self._widget.graph_view.focus_on_nodes.assert_called_with(["node_a"])

    async def test_layout_nodes_triggers_layout_and_focus(self) -> None:
        """Layout should trigger layout and then focus."""
        self._toolbar.layout_nodes()
        await self.wait_n_updates(6)

        self._widget.graph_view.layout_all.assert_called_once()
        self._widget.graph_view.focus_on_nodes.assert_called_once_with()

    async def test_expansion_state_updates_model_nodes(self) -> None:
        """Expansion state should propagate to all nodes."""
        model = _DummyModel()
        node_a = model.add_node("A")
        node_b = model.add_node("B")
        self._widget.model = model

        self._toolbar.on_toolbar_expansion_state_clicked(GraphModel.ExpansionState.MINIMIZED)

        self.assertEqual(node_a.expansion_state, GraphModel.ExpansionState.MINIMIZED)
        self.assertEqual(node_b.expansion_state, GraphModel.ExpansionState.MINIMIZED)

    async def test_pause_toggle_updates_model_and_toolbar(self) -> None:
        """Pause toggle should update model state and toolbar."""
        model = _DummyModel(paused=False)
        self._widget.model = model

        self._toolbar.toggle_material_compilation()

        self.assertTrue(model.pause)

    async def test_unpause_and_pause_cycles_state(self) -> None:
        """Unpause and pause should cycle and restore pause state."""
        model = _DummyModel(paused=True)
        self._widget.model = model

        self._toolbar.unpause_and_pause()
        await self.wait_n_updates(2)

        self.assertIn(False, model.pause_history)
        self.assertTrue(model.pause)

    async def test_toolbar_menus_forward_calls(self) -> None:
        """Toolbar menu handlers should forward to menu builder."""
        self._toolbar._menu_builder = MagicMock()

        self._toolbar.on_toolbar_edit_clicked()
        self._toolbar._menu_builder.show_edit_menu.assert_called_once()

        self._toolbar._menu_builder.reset_mock()
        self._widget.model = None
        self._toolbar.on_toolbar_view_clicked()
        self._toolbar._menu_builder.show_view_menu.assert_called_once_with(
            False, self._toolbar.layout_nodes, self._toolbar.focus_nodes, self._toolbar._apply_expansion_state
        )

        self._toolbar._menu_builder.reset_mock()
        self._widget.model = _DummyModel()
        self._toolbar.on_toolbar_view_clicked()
        self._toolbar._menu_builder.show_view_menu.assert_called_once_with(
            True, self._toolbar.layout_nodes, self._toolbar.focus_nodes, self._toolbar._apply_expansion_state
        )

        self._toolbar._menu_builder.reset_mock()
        self._toolbar.on_toolbar_overflow_clicked()
        self._toolbar._menu_builder.show_overflow_menu.assert_called_once_with(
            True,
            self._toolbar.layout_nodes,
            self._toolbar.focus_nodes,
            self._toolbar._apply_expansion_state,
            self._toolbar.on_toolbar_help_clicked,
        )

    async def test_action_registry_registers_every_hotkey_once_and_routes_callbacks(self) -> None:
        """The command registry must expose every documented graph hotkey without duplicates."""
        callbacks = {
            "delete_nodes": MagicMock(),
            "focus_nodes": MagicMock(),
            "layout_nodes": MagicMock(),
            "group_nodes": MagicMock(),
            "ungroup_nodegraph": MagicMock(),
            "expansion_state": MagicMock(),
            "toggle_pause": MagicMock(),
            "unpause_and_pause": MagicMock(),
        }
        registered = {}
        action_registry = MagicMock()
        action_registry.get_all_actions_for_extension.side_effect = lambda _ext: [
            SimpleNamespace(id=action_id) for action_id in registered
        ]

        def register_action(_ext, action_id, callback, **_kwargs):
            registered[action_id] = callback

        action_registry.register_action.side_effect = register_action
        ext_manager = MagicMock()
        ext_manager.is_extension_enabled.return_value = False
        with patch.object(toolbar_actions_module, "get_action_registry", return_value=action_registry):
            registry = ToolbarActionRegistry("material_graph", "Material Graph", ext_manager, callbacks)
            registry.setup_actions_and_hotkeys()
            registry.setup_actions_and_hotkeys()

        self.assertEqual(
            set(registered),
            {
                "delete_nodes",
                "focus_nodes",
                "layout_nodes",
                "group_nodes",
                "ungroup_nodegraph",
                "expand_nodes",
                "minimize_nodes",
                "close_nodes",
                "toggle_material_compilation",
                "material_unpause_and_pause",
            },
        )
        self.assertEqual(action_registry.register_action.call_count, 10)

        registered["delete_nodes"]()
        registered["focus_nodes"]()
        registered["layout_nodes"]()
        registered["group_nodes"]()
        registered["ungroup_nodegraph"]()
        registered["expand_nodes"]()
        registered["minimize_nodes"]()
        registered["close_nodes"]()
        registered["toggle_material_compilation"]()
        registered["material_unpause_and_pause"]()

        callbacks["delete_nodes"].assert_called_once_with()
        callbacks["focus_nodes"].assert_called_once_with()
        callbacks["layout_nodes"].assert_called_once_with()
        callbacks["group_nodes"].assert_called_once_with()
        callbacks["ungroup_nodegraph"].assert_called_once_with()
        self.assertEqual(
            callbacks["expansion_state"].call_args_list,
            [
                call("open"),
                call("minimized"),
                call("closed"),
            ],
        )
        callbacks["toggle_pause"].assert_called_once_with()
        callbacks["unpause_and_pause"].assert_called_once_with()

    async def test_graph_actions_and_named_expansion_states_route_to_widget(self) -> None:
        """Toolbar action entry points should invoke the intended widget behavior."""
        self._widget.new_graph = MagicMock()
        self._widget.edit_graph = MagicMock()
        model = _DummyModel()
        node = model.add_node("A")
        self._widget.model = model

        self._toolbar.on_toolbar_create_graph_clicked()
        self._toolbar.on_toolbar_edit_graph_clicked()
        self._toolbar._apply_expansion_state("closed")
        self._toolbar._apply_expansion_state("invalid")

        self._widget.new_graph.assert_called_once_with()
        self._widget.edit_graph.assert_called_once_with()
        self.assertEqual(node.expansion_state, GraphModel.ExpansionState.CLOSED)

    async def test_context_switch_preserves_solo_and_contains_failures(self) -> None:
        """Context changes should restore solo state and contain invalid-context failures."""
        solo = SimpleNamespace(soloed_context="mdl", clear=MagicMock(), toggle_solo=MagicMock())
        self._widget._solo_controller = solo
        self._widget.set_context = MagicMock()
        self._widget.rebuild_graph_toolbar = MagicMock()

        self._toolbar.switch_context("mtlx")

        solo.clear.assert_called_once_with()
        self._widget.set_context.assert_called_once_with("mtlx")
        solo.toggle_solo.assert_called_once_with("mtlx")
        self._widget.rebuild_graph_toolbar.assert_not_called()

        self._widget.set_context.side_effect = ValueError("unsupported")
        with patch(f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.logger.error") as log_error:
            self._toolbar.switch_context("invalid")

        log_error.assert_called_once()
        self._widget.rebuild_graph_toolbar.assert_not_called()

    async def test_help_opens_public_documentation(self) -> None:
        """Help should open the canonical public Material Graph guide."""
        with patch(f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.webbrowser.open") as open_browser:
            self._toolbar.on_toolbar_help_clicked()

        open_browser.assert_called_once_with(Paths.DOCS_URL)

    async def test_group_selected_nodes_allows_nested_nodegraph_parent(self) -> None:
        """Grouping inside a child nodegraph should use the selected nodes' parent path."""
        nested_parent = Sdf.Path("/World/Looks/Mat/NodeGraph")
        model = SimpleNamespace(
            selection=[
                _prim_item(str(nested_parent.AppendChild("abs")), (2.0, 4.0)),
                _prim_item(str(nested_parent.AppendChild("add")), (6.0, 8.0)),
            ],
            stage=object(),
            prim_path=Sdf.Path("/World/Looks/Mat"),
        )
        self._widget.model = model
        self._widget._graph_settings_controller = SimpleNamespace(
            get_nodegraph_drop_settings=lambda: ("ui:nodegraph:node:pos", "mdl")
        )
        self._widget.request_model_refresh = MagicMock()

        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.GroupNodeGraph",
            return_value=SimpleNamespace(success=True),
        ) as group_nodegraph:
            self._toolbar.group_selected_nodes()

        group_nodegraph.assert_called_once()
        self.assertEqual(group_nodegraph.call_args.kwargs["parent_path"], nested_parent)
        self.assertEqual(group_nodegraph.call_args.kwargs["context_visibility"], "mdl")

    async def test_delete_nodes_uses_type_name_for_io_wrappers(self) -> None:
        """Delete should recognize IO wrappers by type name, not dynamic class identity."""
        io_node = type("OldInputNodeClass", (), {"get_type_name": staticmethod(lambda: "InputNode")})()
        isolation_model = SimpleNamespace(
            selection=[io_node],
            InputNode=type("NewInputNodeClass", (), {}),
            OutputNode=type("NewOutputNodeClass", (), {}),
        )
        self._widget.isolation_model = isolation_model
        self._widget.model = object()
        self._widget.graph_view.hovered_connection_index = -1

        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.DeleteInputOutputNodes",
            return_value=SimpleNamespace(success=True),
        ) as delete_io:
            self._toolbar.delete_nodes()

        delete_io.assert_called_once_with(isolation_model, [io_node], self._widget.model)

    async def test_delete_nodes_reports_input_output_cleanup_failure(self) -> None:
        """The toolbar must surface structured isolation cleanup failures instead of claiming success."""
        io_node = type("InputNodeClass", (), {"get_type_name": staticmethod(lambda: "InputNode")})()
        self._widget.isolation_model = SimpleNamespace(selection=[io_node])
        self._widget.model = object()
        self._widget.graph_view.hovered_connection_index = -1

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.DeleteInputOutputNodes",
                return_value=SimpleNamespace(success=False, error_code="injected", message="failed"),
            ),
            patch(f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.logger.warning") as warning,
        ):
            self._toolbar.delete_nodes()
        warning.assert_called_once()

    async def test_delete_nodes_prioritizes_connection_then_valid_prim_selection(self) -> None:
        """Delete should disconnect a hovered edge first and only delete prims that still exist."""
        graph_view = self._widget.graph_view
        graph_view.hovered_connection_index = 2
        graph_view.disconnect_hovered_connection.return_value = True
        self._widget.isolation_model = SimpleNamespace(selection=[_prim_item("/World/Looks/Stale")])

        with patch(f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.DeletePrims") as delete_prims:
            self._toolbar.delete_nodes()
        delete_prims.assert_not_called()

        graph_view.hovered_connection_index = -1
        stage = self._stage
        valid_path = "/World/Looks/Valid"
        stage.DefinePrim(valid_path)
        self._widget.model = SimpleNamespace(stage=stage)
        self._widget.isolation_model = SimpleNamespace(
            selection=[_prim_item(valid_path), _prim_item("/World/Looks/Missing")]
        )
        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.DeletePrims",
                return_value=SimpleNamespace(success=False, error_code="injected", message="failed"),
            ) as delete_prims,
            patch(f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.logger.warning") as warning,
        ):
            self._toolbar.delete_nodes()

        delete_prims.assert_called_once_with(paths=[Sdf.Path(valid_path)], stage=stage)
        warning.assert_called_once()

    async def test_delete_nodes_undo_restores_connections_for_multi_selection(self) -> None:
        """The toolbar delete workflow must restore edges within and outside a multi-selection."""
        material = UsdShade.Material.Define(self._stage, "/World/Looks/DeleteUndoMaterial")
        node_a = UsdShade.Shader.Define(self._stage, material.GetPath().AppendChild("color_const"))
        node_b = UsdShade.NodeGraph.Define(self._stage, material.GetPath().AppendChild("NodeGraph_01"))
        node_c = UsdShade.NodeGraph.Define(self._stage, material.GetPath().AppendChild("NodeGraph"))
        a_out = node_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        b_in = node_b.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_out = node_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        c_in = node_c.CreateInput("in", Sdf.ValueTypeNames.Float)
        self.assertTrue(b_in.ConnectToSource(a_out))
        self.assertTrue(c_in.ConnectToSource(b_out))
        expected_b_sources = list(b_in.GetAttr().GetConnections())
        expected_c_sources = list(c_in.GetAttr().GetConnections())
        self._widget.model = SimpleNamespace(stage=self._stage)
        self._widget.isolation_model = SimpleNamespace(
            selection=[_prim_item(str(node_a.GetPath())), _prim_item(str(node_b.GetPath()))]
        )
        self._widget.graph_view.hovered_connection_index = -1
        omni.kit.undo.clear_stack()

        self._toolbar.delete_nodes()

        self.assertFalse(self._stage.GetPrimAtPath(node_a.GetPath()))
        self.assertFalse(self._stage.GetPrimAtPath(node_b.GetPath()))
        self.assertTrue(omni.kit.undo.undo())
        await self.wait_n_updates(2)
        restored_b = UsdShade.NodeGraph(self._stage.GetPrimAtPath(node_b.GetPath())).GetInput("in")
        restored_c = UsdShade.NodeGraph(self._stage.GetPrimAtPath(node_c.GetPath())).GetInput("in")
        self.assertEqual(restored_b.GetAttr().GetConnections(), expected_b_sources)
        self.assertEqual(restored_c.GetAttr().GetConnections(), expected_c_sources)

    async def test_group_rejects_cross_parent_selection_and_reports_command_failure(self) -> None:
        """Grouping should reject unsafe selections and surface command failures."""
        self._widget.request_model_refresh = MagicMock()
        self._widget._graph_settings_controller = SimpleNamespace(
            get_nodegraph_drop_settings=lambda: ("ui:nodegraph:node:pos", "mdl")
        )
        self._widget.model = SimpleNamespace(
            selection=[_prim_item("/World/Looks/Mat/A"), _prim_item("/World/Looks/Other/B")],
            stage=self._stage,
            prim_path=Sdf.Path("/World/Looks/Mat"),
        )
        with patch(f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.logger.warning") as warning:
            self._toolbar.group_selected_nodes()
        warning.assert_called_once_with(
            "group rejected: selected nodes must share one parent under graph %s; selected=%s",
            Sdf.Path("/World/Looks/Mat"),
            "/World/Looks/Mat/A, /World/Looks/Other/B",
        )
        self._widget.request_model_refresh.assert_not_called()

        self._widget.model.selection = [_prim_item("/World/Looks/Mat/A")]
        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.GroupNodeGraph",
                return_value=SimpleNamespace(success=False, error_code="injected", message="failed"),
            ),
            patch(f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.logger.warning") as warning,
        ):
            self._toolbar.group_selected_nodes()

        warning.assert_called_once()
        self._widget.request_model_refresh.assert_called_once_with()

    async def test_ungroup_routes_nodegraphs_and_reports_each_failure(self) -> None:
        """Ungroup should process only NodeGraphs and retain a visible failure signal."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/Looks/Mat/Group")
        item = _prim_item(str(nodegraph.GetPath()))
        item._prim = nodegraph.GetPrim()
        non_nodegraph = _prim_item("/World/Looks/Mat/Shader")
        non_nodegraph._prim = self._stage.DefinePrim(non_nodegraph.prim_path)
        self._widget.model = SimpleNamespace(selection=[item, non_nodegraph], stage=self._stage)
        self._widget.request_model_refresh = MagicMock()

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.UngroupNodeGraph",
                return_value=SimpleNamespace(success=False, error_code="injected", message="failed"),
            ) as ungroup,
            patch(f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.controller.logger.warning") as warning,
        ):
            self._toolbar.ungroup_selected_nodegraphs()

        ungroup.assert_called_once_with(nodegraph_path=nodegraph.GetPath(), stage=self._stage)
        warning.assert_called_once()
        self._widget.request_model_refresh.assert_called_once_with()

    async def test_average_position_returns_none_when_no_nodes_are_positioned(self) -> None:
        """Grouping should preserve the valid no-authored-position state."""
        item = _prim_item("/World/Looks/Mat/A")
        item._ui_state.position = None
        self.assertIsNone(self._toolbar._get_average_position([item]))
