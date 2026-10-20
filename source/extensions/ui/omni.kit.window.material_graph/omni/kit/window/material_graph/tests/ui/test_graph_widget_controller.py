"""Headless tests for GraphWidget orchestration and validation presentation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, call, patch

import omni.kit.test
from omni.kit.widget.graph import IsolationGraphModel
from pxr import Sdf

from ...scripts.ui.sections.graph import widget as graph_widget_module
from ...scripts.ui.sections.graph.mixins import catalog as catalog_mixin_module
from ...scripts.ui.sections.graph.mixins import drag_drop as drag_drop_mixin_module
from ...scripts.ui.sections.graph.widget import GraphWidget
from ...scripts.validation.issue import ValidationIssue
from ...scripts.validation.result import ValidationResult
from ...scripts.validation.severity import ValidationSeverity


class _GraphModel:
    def __init__(self, mapping=None) -> None:
        self.mapping = mapping or {}
        self.selection = ["selected"]
        self.prim = None
        self.notify_changed = MagicMock()
        self.set_validation_state = MagicMock()

    def __getitem__(self, item):
        return self.mapping[item]


class TestGraphWidgetController(omni.kit.test.AsyncTestCase):
    """Cover graph state transitions without creating windows or moving a pointer."""

    @staticmethod
    def _widget() -> GraphWidget:
        widget = GraphWidget.__new__(GraphWidget)
        widget._current_context = None
        widget._current_model = None
        widget._graph_view = None
        widget._graph_toolbar_frame = None
        widget._solo_controller = None
        widget._isolation_model = None
        widget._context_manager = None
        widget._context_model_controller = None
        widget._toolbar_controller = None
        widget._interaction_controller = None
        widget._stage_lifecycle_controller = None
        widget._catalog_model = None
        widget._catalog_widget = None
        widget._catalog_context_menu_controller = None
        widget._catalog_drop_cache = {}
        widget._graph_drop_overlay = None
        widget._graph_background_color = None
        widget._node_creation_controller = None
        widget._open_graph_lifecycle = None
        widget._upgrade_refresh_lifecycle = None
        widget._splitter_left = None
        widget._warning_overlay = None
        widget._error_label = MagicMock()
        widget._warning_label = MagicMock()
        widget._error_message = ""
        widget._warning_message = ""
        widget._dismissed_error_message = None
        widget._dismissed_warning_message = None
        widget._error_frame = None
        widget._warning_frame = None
        widget._last_validation_result = None
        widget._navigation = []
        widget._GraphEditorCoreWidget__style = {}
        return widget

    async def test_catalog_mixin_routes_payload_acceptance_and_persistence(self) -> None:
        """Catalog panel behavior should validate and persist every supported payload headlessly."""
        widget = self._widget()
        widget._catalog_model = object()
        catalog = MagicMock()
        delegate = MagicMock()
        with (
            patch.object(catalog_mixin_module, "MaterialGraphCatalog", return_value=catalog),
            patch.object(catalog_mixin_module, "MaterialGraphCatalogDelegate", return_value=delegate),
        ):
            widget.on_build_catalog()
        self.assertIs(widget._catalog_widget, catalog)

        item, event = object(), SimpleNamespace(mime_data="payload")
        catalog.accept_group_drop.return_value = True
        self.assertTrue(widget._on_catalog_group_accept_drop(item, "payload"))
        widget._on_catalog_group_drop(item, event)
        catalog.drop_on_group.assert_called_once_with(item, event)
        self.assertIsNone(widget._parse_catalog_payload("[]"))
        self.assertFalse(widget._is_catalog_payload(object()))
        self.assertTrue(widget._is_catalog_payload('{"type":"Texture"}'))

        input_type = IsolationGraphModel.InputNode.get_type_name()
        output_type = IsolationGraphModel.OutputNode.get_type_name()
        widget._isolation_model = SimpleNamespace(_input_nodes=[object()], _output_nodes=[])
        self.assertTrue(widget._should_show_input_output_indicator(f'{{"type":"{input_type}"}}'))
        self.assertFalse(widget._should_show_input_output_indicator(f'{{"type":"{output_type}"}}'))

        catalog.get_active_tab.return_value = "textures"
        self.assertFalse(widget.on_catalog_accept_drop('{"origin":"catalog","type":"Texture"}'))
        self.assertTrue(widget.on_catalog_accept_drop('{"type":"Texture"}'))
        widget._context_manager = SimpleNamespace(
            get_context=lambda _name: SimpleNamespace(plugin=SimpleNamespace(name="mdl"))
        )
        widget._current_context = "mdl"
        self.assertTrue(widget.on_catalog_accept_drop("module.mdl"))
        widget._context_manager.get_context = lambda _name: SimpleNamespace(plugin=SimpleNamespace(name="mtlx"))
        self.assertFalse(widget.on_catalog_accept_drop("module.mdl"))
        with (
            patch.object(catalog_mixin_module.Settings, "get_droppable_texture_formats", return_value=["png"]),
            patch.object(catalog_mixin_module, "is_existing_path", return_value=True),
        ):
            self.assertTrue(widget.on_catalog_accept_drop("albedo.png"))
            self.assertFalse(widget.on_catalog_accept_drop("albedo.txt"))

        texture_payload = '{"type":"Texture","source":"albedo.png"}'
        widget.on_catalog_drop(SimpleNamespace(mime_data=texture_payload))
        catalog.handle_texture_drop.assert_called_once()
        with patch.object(catalog_mixin_module.Settings, "add_mdl_catalog_module") as add_module:
            widget.on_catalog_drop(SimpleNamespace(mime_data="module.mdl"))
        add_module.assert_called_once_with("module.mdl")

        registry = SimpleNamespace(
            has_texture=MagicMock(return_value=False),
            add_texture=MagicMock(),
        )
        widget._catalog_drop_cache = {"old": object()}
        with (
            patch.object(catalog_mixin_module, "get_texture_registry", return_value=registry),
            patch.object(catalog_mixin_module, "is_existing_path", return_value=True),
        ):
            widget.on_catalog_drop(SimpleNamespace(mime_data="albedo.png"))
        registry.add_texture.assert_called_once_with("albedo.png")
        self.assertEqual(widget._catalog_drop_cache, {})

        widget._catalog_context_menu_controller = SimpleNamespace(show_menu=MagicMock())
        widget.on_catalog_context_menu([item])
        widget._catalog_context_menu_controller.show_menu.assert_called_once_with([item])
        widget._on_catalog_item_double_clicked(item)
        catalog.handle_item_double_clicked.assert_called_once_with(item)

    async def test_graph_drop_mixin_updates_overlay_style_and_controller_lifecycle(self) -> None:
        """Graph drop feedback should clear visual and modifier state on every exit path."""
        widget = self._widget()
        overlay = SimpleNamespace(show=MagicMock(), hide=MagicMock())
        widget._graph_drop_overlay = overlay
        widget._node_creation_controller = SimpleNamespace(
            accept_drop=MagicMock(return_value=True),
            drop=MagicMock(return_value="created"),
        )
        widget._should_show_input_output_indicator = MagicMock(return_value=False)
        widget._is_catalog_payload = MagicMock(return_value=False)
        self.assertTrue(widget.on_accept_drop("node"))
        overlay.show.assert_called_once_with(True)

        widget._should_show_input_output_indicator.return_value = True
        widget.on_accept_drop("input")
        overlay.show.assert_called_with(False)
        widget._should_show_input_output_indicator.return_value = False
        widget._is_catalog_payload.return_value = True
        widget.on_accept_drop("catalog")
        overlay.hide.assert_called()

        with patch.object(GraphWidget, "style", new_callable=PropertyMock) as style:
            style.return_value = {"Graph": {"background_color": 0x1234}}
            widget._set_graph_background_override(0x5678)
            self.assertEqual(style.call_args.args[0]["Graph"]["background_color"], 0x5678)
            widget._set_graph_background_override(None)
            self.assertEqual(style.call_args.args[0]["Graph"]["background_color"], 0x1234)

        with patch.object(drag_drop_mixin_module, "clear_active_modifier_flags") as clear_flags:
            self.assertEqual(widget.on_drop(SimpleNamespace(mime_data="node")), "created")
            widget._on_graph_hovered(False)
        self.assertEqual(clear_flags.call_count, 2)

        widget._interaction_controller = SimpleNamespace(hide_context_menu=MagicMock())
        widget._graph_view = SimpleNamespace(hide_port_context_menu=MagicMock())
        with (
            patch.object(drag_drop_mixin_module, "set_active_modifier_flags") as set_flags,
            patch.object(drag_drop_mixin_module, "clear_active_modifier_flags") as clear_flags,
        ):
            widget._on_graph_mouse_released(0, 0, 0, 7)
        set_flags.assert_called_once_with(7)
        clear_flags.assert_called_once_with()
        widget._interaction_controller.hide_context_menu.assert_called_once_with()
        widget._graph_view.hide_port_context_menu.assert_called_once_with()

    async def test_solo_toolbar_and_stage_listener_routing(self) -> None:
        widget = self._widget()
        solo = SimpleNamespace(soloed_context=None, toggle_solo=MagicMock(), clear=MagicMock())
        widget._solo_controller = solo
        widget._current_context = "mtlx"
        widget._on_solo_clicked()
        solo.toggle_solo.assert_called_once_with("mtlx")
        solo.soloed_context = "mtlx"
        widget._on_solo_clicked()
        solo.clear.assert_called_once_with()

        widget._graph_toolbar_frame = SimpleNamespace(rebuild=MagicMock())
        widget.rebuild_graph_toolbar()
        widget._graph_toolbar_frame.rebuild.assert_called_once_with()

        listener = SimpleNamespace(add_ignored_paths=MagicMock(), remove_ignored_paths=MagicMock())
        widget._isolation_model = SimpleNamespace(_stage_listener=listener)
        paths = [Sdf.Path("/Material.outputs:mtlx:surface")]
        widget.ignore_stage_listener_paths(paths)
        widget.unignore_stage_listener_paths(paths)
        listener.add_ignored_paths.assert_called_once_with(paths)
        listener.remove_ignored_paths.assert_called_once_with(paths)

    async def test_context_and_controller_facade_methods(self) -> None:
        widget = self._widget()
        widget._context_model_controller = SimpleNamespace(
            set_context=MagicMock(return_value=True),
            edit_graph=MagicMock(),
            new_graph=MagicMock(),
        )
        widget._interaction_controller = SimpleNamespace(
            on_left_mouse_button_double_clicked=MagicMock(return_value="double"),
            on_right_mouse_button_pressed=MagicMock(return_value="right"),
        )
        widget._toolbar_controller = SimpleNamespace(get_toolbar_items=MagicMock(return_value=["item"]))
        widget._catalog_model = object()
        widget._isolation_model = object()
        widget.current_context = "mdl"
        self.assertEqual(widget.current_context, "mdl")
        self.assertTrue(widget.set_context("mtlx"))
        self.assertEqual(widget.on_left_mouse_button_double_clicked(["node"]), "double")
        self.assertEqual(widget.on_right_mouse_button_pressed(["node"], 1, 2), "right")
        widget.edit_graph("prim")
        widget.new_graph()
        self.assertEqual(widget.get_toolbar_items(True), ["item"])
        self.assertIs(widget.catalog_model, widget._catalog_model)
        self.assertIs(widget.isolation_model, widget._isolation_model)
        self.assertIs(widget.current_model, widget._current_model)
        self.assertIs(widget.graph_view, widget._graph_view)
        self.assertIsNone(widget.set_toolbar_items([]))

    async def test_mouse_header_style_and_wait_ready_are_contained(self) -> None:
        widget = self._widget()
        widget._graph_view = SimpleNamespace(is_point_over_header=MagicMock(return_value=True))
        self.assertTrue(widget.is_mouse_over_node_header("node"))
        widget._graph_view.is_point_over_header.side_effect = RuntimeError("injected")
        self.assertFalse(widget.is_mouse_over_node_header("node"))
        widget._graph_view = object()
        self.assertFalse(widget.is_mouse_over_node_header("node"))

        widget._update_style = MagicMock(return_value="updated")
        self.assertEqual(widget.update_style(), "updated")
        with patch.object(graph_widget_module, "wait_for_updates", new=AsyncMock(return_value=True)) as wait:
            self.assertTrue(await widget.wait_ready(7))
        wait.assert_awaited_once()
        self.assertEqual(wait.await_args.kwargs["max_updates"], 7)

    async def test_open_graph_async_waits_then_routes_to_controller(self) -> None:
        widget = self._widget()
        widget._solo_controller = SimpleNamespace(clear=MagicMock())
        widget._context_model_controller = SimpleNamespace(open_graph=MagicMock())
        widget.wait_ready = AsyncMock(return_value=False)
        await widget.open_graph_async("prim", Sdf.Path("/Graph"), 3)
        widget._context_model_controller.open_graph.assert_not_called()

        widget.wait_ready.return_value = True
        next_update = AsyncMock()
        with patch.object(
            graph_widget_module.omni.kit.app,
            "get_app",
            return_value=SimpleNamespace(next_update_async=next_update),
        ):
            await widget.open_graph_async("prim", Sdf.Path("/Graph"), 3)
        self.assertEqual(next_update.await_count, 10)
        widget._context_model_controller.open_graph.assert_called_once_with("prim", Sdf.Path("/Graph"))
        self.assertEqual(widget._solo_controller.clear.call_count, 2)

    async def test_open_and_focus_tasks_use_lifecycle_without_rendering(self) -> None:
        widget = self._widget()
        lifecycle = SimpleNamespace(cleanup=MagicMock(), add_task=MagicMock())
        widget._open_graph_lifecycle = lifecycle
        widget.open_graph_async = MagicMock(return_value=AsyncMock()())
        widget.open_graph("prim", Sdf.Path("/Graph"), 4)
        lifecycle.cleanup.assert_called_once_with()
        lifecycle.add_task.assert_called_once()
        lifecycle.add_task.call_args.args[0].close()

        lifecycle.add_task.reset_mock()
        widget.focus_all_nodes(2)
        focus_coro = lifecycle.add_task.call_args.args[0]
        widget.wait_ready = AsyncMock(return_value=True)
        widget._graph_view = SimpleNamespace(focus_on_nodes=MagicMock())
        next_update = AsyncMock()
        with patch.object(
            graph_widget_module.omni.kit.app,
            "get_app",
            return_value=SimpleNamespace(next_update_async=next_update),
        ):
            await focus_coro
        self.assertEqual(next_update.await_count, 2)
        widget._graph_view.focus_on_nodes.assert_called_once_with()

    async def test_update_style_merges_plugin_or_default_style(self) -> None:
        widget = self._widget()
        widget.get_specialized_style = MagicMock(return_value={"base": 1})
        plugin = SimpleNamespace(get_style=MagicMock(return_value={"plugin": 2}))
        widget._context_manager = SimpleNamespace(get_context=MagicMock(return_value=SimpleNamespace(plugin=plugin)))
        widget._current_context = "mtlx"
        with patch.object(GraphWidget, "style", new_callable=PropertyMock) as style:
            widget._update_style()
            self.assertEqual(style.call_args.args[0], {"base": 1, "plugin": 2})

        widget._current_context = None
        with patch.object(GraphWidget, "style", new_callable=PropertyMock) as style:
            widget._update_style()
            self.assertIn("Graph.Node.Icon", style.call_args.args[0])

    async def test_set_current_compound_rebuilds_isolation_and_navigation(self) -> None:
        widget = self._widget()
        item = object()
        graph_model = _GraphModel({item: SimpleNamespace(nodes=["node"])})
        widget._graph_view = SimpleNamespace(model=None)
        widget._navigation = ["root"]
        old_isolation = SimpleNamespace(_root="other", destroy=MagicMock())
        widget._isolation_model = old_isolation
        widget.on_build_breadcrumbs = MagicMock()
        widget.focus_on_nodes = MagicMock()
        widget.request_model_refresh = MagicMock()
        new_isolation = SimpleNamespace(subscribe_item_changed=MagicMock(return_value="subscription"))
        with (
            patch.object(GraphWidget, "model", new_callable=PropertyMock, return_value=graph_model),
            patch.object(graph_widget_module, "MaterialGraphIsolationModel", return_value=new_isolation),
        ):
            widget.set_current_compound(item)
        old_isolation.destroy.assert_called_once_with()
        self.assertEqual(widget._navigation, ["root", item])
        self.assertIs(widget._graph_view.model, new_isolation)
        self.assertEqual(widget._isolation_changed_subscription, "subscription")
        self.assertEqual(graph_model.selection, [])
        widget.focus_on_nodes.assert_called_once_with()
        widget.request_model_refresh.assert_called_once_with()

    async def test_set_current_compound_logs_graph_view_assignment_failure(self) -> None:
        """A native-view assignment error is contained by the extension logger."""

        class _BrokenView:
            @property
            def model(self):
                return None

            @model.setter
            def model(self, _value) -> None:
                raise RuntimeError("native view rejected model")

        widget = self._widget()
        item = object()
        graph_model = _GraphModel({item: SimpleNamespace(nodes=["node"])})
        widget._graph_view = _BrokenView()
        widget.on_build_breadcrumbs = MagicMock()
        isolation = SimpleNamespace(subscribe_item_changed=MagicMock(return_value="subscription"))

        with (
            patch.object(GraphWidget, "model", new_callable=PropertyMock, return_value=graph_model),
            patch.object(graph_widget_module, "MaterialGraphIsolationModel", return_value=isolation),
            patch.object(graph_widget_module, "log_exception") as log_failure,
        ):
            widget.set_current_compound(item, focus=False, refresh=False)

        log_failure.assert_called_once()
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], RuntimeError)
        self.assertEqual(graph_model.selection, [])

    async def test_set_current_compound_handles_non_navigable_and_root(self) -> None:
        widget = self._widget()
        item = object()
        graph_model = _GraphModel({item: SimpleNamespace(nodes=None), None: SimpleNamespace(nodes=[])})
        widget._graph_view = SimpleNamespace(model=None)
        widget._navigation = []
        widget.on_build_breadcrumbs = MagicMock()
        widget.request_model_refresh = MagicMock()
        with patch.object(GraphWidget, "model", new_callable=PropertyMock, return_value=graph_model):
            widget.set_current_compound(item)
        self.assertIs(widget.current_model, item)
        self.assertEqual(widget._navigation, [])

        new_isolation = SimpleNamespace(subscribe_item_changed=MagicMock(return_value="subscription"))
        with (
            patch.object(GraphWidget, "model", new_callable=PropertyMock, return_value=graph_model),
            patch.object(graph_widget_module, "MaterialGraphIsolationModel", return_value=new_isolation),
        ):
            widget.set_current_compound(None)
        widget.request_model_refresh.assert_not_called()

    async def test_reset_and_visibility_cover_valid_invalid_and_error_models(self) -> None:
        widget = self._widget()
        widget._solo_controller = SimpleNamespace(clear=MagicMock())
        widget.clear_error = MagicMock()
        widget.clear_warning = MagicMock()
        widget._context_manager = SimpleNamespace(clear=MagicMock())
        widget._toolbar_controller = SimpleNamespace(get_toolbar_items=MagicMock(return_value=[]))
        widget._catalog_model = SimpleNamespace(clear=MagicMock())
        widget.rebuild_graph_toolbar = MagicMock()
        widget._stage_lifecycle_controller = SimpleNamespace(set_visible=MagicMock())
        startup_frame = SimpleNamespace(set_build_fn=MagicMock(), rebuild=MagicMock())
        widget._GraphEditorCoreWidget__startup_frame = startup_frame
        model = SimpleNamespace(prim_exists=MagicMock(return_value=True))
        with patch.object(GraphWidget, "model", new_callable=PropertyMock) as model_property:
            model_property.return_value = model
            widget.set_visibility(True)
            widget._stage_lifecycle_controller.set_visible.assert_called_with(True)
            model.prim_exists.side_effect = RuntimeError("injected")
            widget.reset = MagicMock()
            widget.set_visibility(True)
            widget.reset.assert_called_once_with()
            widget.set_visibility(False)

        widget.reset = GraphWidget.reset.__get__(widget, GraphWidget)
        with patch.object(GraphWidget, "model", new_callable=PropertyMock) as model_property:
            model_property.return_value = model
            widget.reset()
        widget._solo_controller.clear.assert_called()
        widget._context_manager.clear.assert_called_once_with()
        widget._catalog_model.clear.assert_called_once_with()
        startup_frame.rebuild.assert_called_once_with()

    async def test_error_warning_and_indicator_state(self) -> None:
        widget = self._widget()
        widget._error_frame = SimpleNamespace(visible=True)
        widget._warning_frame = SimpleNamespace(visible=True)
        widget.show_error("")
        widget.show_warning("")
        with patch.object(graph_widget_module.logger, "warning") as warning:
            widget.show_error("error")
            widget.show_error("error")
            widget.show_warning("warning")
            widget.show_warning("warning")
            widget.show_error("already logged", log_message=False)
        self.assertEqual(warning.call_args_list, [call("%s", "error"), call("%s", "warning")])
        self.assertEqual(widget._error_label.text, "already logged")
        self.assertEqual(widget._warning_label.text, "warning")
        self.assertTrue(widget._error_frame.visible)
        self.assertTrue(widget._warning_frame.visible)
        self.assertEqual(widget._error_frame.height.value, GraphWidget._banner_height("already logged"))
        self.assertEqual(widget._warning_frame.height.value, GraphWidget._banner_height("warning"))

        widget.dismiss_error()
        widget.dismiss_warning()
        self.assertFalse(widget._error_frame.visible)
        self.assertFalse(widget._warning_frame.visible)
        widget.restore_error()
        widget.restore_warning()
        self.assertIsNone(widget._dismissed_error_message)
        self.assertIsNone(widget._dismissed_warning_message)
        self.assertTrue(widget._error_frame.visible)
        self.assertTrue(widget._warning_frame.visible)

        widget.dismiss_error()
        widget.dismiss_warning()
        widget.show_error("already logged")
        widget.show_warning("warning")
        self.assertFalse(widget._error_frame.visible)
        self.assertFalse(widget._warning_frame.visible)
        widget.show_error("changed error", log_message=False)
        widget.show_warning("changed warning", log_message=False)
        self.assertTrue(widget._error_frame.visible)
        self.assertTrue(widget._warning_frame.visible)

        widget.clear_error()
        widget.clear_warning()
        self.assertEqual(widget._error_label.text, "")
        self.assertEqual(widget._warning_label.text, "")
        self.assertFalse(widget._error_frame.visible)
        self.assertFalse(widget._warning_frame.visible)
        self.assertEqual(widget._dismissed_error_message, "already logged")
        self.assertEqual(widget._dismissed_warning_message, "warning")

        widget.clear_error(reset_dismissal=True)
        widget.clear_warning(reset_dismissal=True)
        self.assertIsNone(widget._dismissed_error_message)
        self.assertIsNone(widget._dismissed_warning_message)
        self.assertGreaterEqual(GraphWidget._banner_height("one line"), GraphWidget._BANNER_MIN_HEIGHT)
        self.assertEqual(GraphWidget._banner_height("\n".join(["line"] * 100)), GraphWidget._BANNER_MAX_HEIGHT)

        with patch.object(graph_widget_module.logger, "warning") as warning:
            widget.show_error("already logged")
            widget.show_warning("warning")
        self.assertEqual(
            warning.call_args_list,
            [call("%s", "already logged"), call("%s", "warning")],
        )

        widget._error_indicator_frame = SimpleNamespace(visible=False, tooltip="old")
        widget._error_badge_frame = SimpleNamespace(visible=False, tooltip="")
        widget._warning_badge_frame = SimpleNamespace(visible=False, tooltip="")
        widget._upgrade_menu_frame = SimpleNamespace(visible=False, tooltip="")
        widget._error_count_label = SimpleNamespace(text="")
        widget._warning_count_label = SimpleNamespace(text="")
        widget._get_pending_upgrade_changes = MagicMock(return_value=[object(), object()])
        issues = [
            ValidationIssue("INVALID_NODE_DEFINITION_MISSING", "missing", prim_path="/A"),
            ValidationIssue(
                "INVALID_NODE_DEFINITION_MISSING",
                "warning",
                ValidationSeverity.WARNING,
                "/B",
            ),
            ValidationIssue("INVALID_CONNECTION_TYPE_MISMATCH_SOURCE", "source", prim_path="/C"),
        ]
        widget._apply_error_indicator(ValidationResult("mtlx", issues))
        self.assertTrue(widget._error_indicator_frame.visible)
        self.assertEqual(widget._error_count_label.text, "1")
        self.assertEqual(widget._warning_count_label.text, "1")
        self.assertIn("missing", widget._error_badge_frame.tooltip)
        self.assertIn("warning", widget._warning_badge_frame.tooltip)
        self.assertTrue(widget._upgrade_menu_frame.visible)

    async def test_upgrade_discovery_and_apply_flows_are_exception_safe(self) -> None:
        widget = self._widget()
        self.assertEqual(widget._get_pending_upgrade_changes(), [])
        from ...scripts.plugins.impl.materialx.plugin import MaterialXPlugin

        plugin = MaterialXPlugin.__new__(MaterialXPlugin)
        plugin._pending_upgrade_changes = ["change"]
        widget._context_manager = SimpleNamespace(get_plugins=MagicMock(return_value=[object(), plugin]))
        self.assertEqual(widget._get_pending_upgrade_changes(), ["change"])
        widget._context_manager.get_plugins.side_effect = RuntimeError("injected")
        with patch.object(graph_widget_module.logger, "warning") as warning:
            self.assertEqual(widget._get_pending_upgrade_changes(), [])
        warning.assert_called_once()

        change_ok = SimpleNamespace(prim_path="/A")
        change_fail = SimpleNamespace(prim_path="/B")
        widget._context_manager = SimpleNamespace(
            apply_single_upgrade=MagicMock(side_effect=[True, RuntimeError("injected")])
        )
        widget._get_pending_upgrade_changes = MagicMock(return_value=[change_ok, change_fail])
        widget._refresh_after_upgrade = MagicMock()
        widget._apply_all_upgrades()
        widget._refresh_after_upgrade.assert_called_once_with()
        widget._context_manager.apply_single_upgrade = MagicMock(return_value=True)
        widget._refresh_after_upgrade.reset_mock()
        widget._apply_single_upgrade(change_ok)
        widget._refresh_after_upgrade.assert_called_once_with()

    async def test_repeated_upgrade_menu_replaces_event_owned_container(self) -> None:
        """Repeated upgrade clicks must not clear an OmniUI menu in-place."""
        widget = self._widget()
        widget._upgrade_menu = None
        widget._get_pending_upgrade_changes = MagicMock(
            return_value=[
                SimpleNamespace(prim_path="/A", old_identifier="oldA", new_identifier="newA"),
                SimpleNamespace(prim_path="/B", old_identifier="oldB", new_identifier="newB"),
            ]
        )
        menus = [MagicMock(), MagicMock()]
        for menu in menus:
            menu.__enter__.return_value = menu
            menu.__exit__.return_value = False

        with (
            patch.object(graph_widget_module.omni.ui, "Menu", side_effect=menus),
            patch.object(graph_widget_module.omni.ui, "MenuItem"),
            patch.object(graph_widget_module.omni.ui, "Separator"),
        ):
            widget._show_upgrade_menu()
            widget._show_upgrade_menu()

        menus[0].hide.assert_called_once_with()
        menus[1].hide.assert_not_called()
        menus[1].show.assert_called_once_with()
        self.assertIs(widget._upgrade_menu, menus[1])

    async def test_upgrade_refresh_is_coalesced_and_lifecycle_owned(self) -> None:
        """Deferred upgrade reloads should cancel predecessors and never become orphaned tasks."""
        widget = self._widget()
        lifecycle = SimpleNamespace(cleanup=MagicMock(), add_task=MagicMock())
        widget._upgrade_refresh_lifecycle = lifecycle
        widget._context_model_controller = object()
        prim = SimpleNamespace(IsValid=MagicMock(return_value=True))
        with patch.object(GraphWidget, "model", new_callable=PropertyMock, return_value=SimpleNamespace(prim=prim)):
            widget._refresh_after_upgrade()

        lifecycle.cleanup.assert_called_once_with()
        lifecycle.add_task.assert_called_once()
        (coroutine,) = lifecycle.add_task.call_args.args
        self.assertEqual(lifecycle.add_task.call_args.kwargs["label"], "refresh graph after upgrade")
        coroutine.close()

    async def test_apply_validation_result_updates_models_overlays_and_messages(self) -> None:
        widget = self._widget()
        graph_model = _GraphModel()
        isolation = SimpleNamespace(
            _invalid_connection_paths={"/Old"},
            _warning_node_paths=set(),
        )
        graph_view = SimpleNamespace(set_validation_errors=MagicMock())
        widget._isolation_model = isolation
        widget._graph_view = graph_view
        widget._warning_overlay = SimpleNamespace(visible=False)
        widget._apply_error_indicator = MagicMock()
        widget.show_error = MagicMock()
        widget.clear_error = MagicMock()
        widget.show_warning = MagicMock()
        widget.clear_warning = MagicMock()
        widget.request_model_refresh = MagicMock()
        result = ValidationResult(
            "mtlx",
            [
                ValidationIssue("INVALID_CONNECTION_BROKEN_SOURCE", "broken", prim_path="/Connection"),
                ValidationIssue("INVALID_NODE_DEFINITION_MISSING", "missing", prim_path="/Node"),
                ValidationIssue(
                    "INVALID_NODE_DEFINITION_MISSING",
                    "warn",
                    ValidationSeverity.WARNING,
                    "/WarningNode",
                ),
                ValidationIssue("NO_PATH", "global"),
            ],
        )
        with patch.object(GraphWidget, "model", new_callable=PropertyMock, return_value=graph_model):
            widget.apply_validation_result(result)
        graph_model.set_validation_state.assert_called_once_with(True, True)
        self.assertEqual(isolation._invalid_connection_paths, {"/Connection"})
        self.assertEqual(isolation._warning_node_paths, {"/WarningNode"})
        graph_view.set_validation_errors.assert_called_once_with({"/Connection": "broken", "/Node": "missing"})
        widget.show_error.assert_called_once_with("broken\nmissing\nglobal")
        widget.clear_warning.assert_called_once_with()
        widget.request_model_refresh.assert_called_once_with()

    async def test_catalog_visibility_refresh_and_isolation_empty_state(self) -> None:
        widget = self._widget()
        widget._splitter_left = SimpleNamespace(set_panel_visible=MagicMock())
        widget.set_catalog_visible(True)
        widget._splitter_left.set_panel_visible.assert_called_once_with(True)
        model = _GraphModel()
        with patch.object(GraphWidget, "model", new_callable=PropertyMock, return_value=model):
            widget.request_model_refresh()
        model.notify_changed.assert_called_once_with()

        widget.clear_all = MagicMock()
        widget._isolation_model = SimpleNamespace(nodes=None)
        widget._on_isolation_item_changed(None)
        widget.clear_all.assert_called_once_with()
