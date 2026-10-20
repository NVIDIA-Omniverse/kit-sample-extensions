# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Fast semantic smoke workflows over the real Material Graph widget tree."""

import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import omni.kit.ui_test as ui_test
import omni.ui
from pxr import Sdf, UsdShade

from ...scripts.config.logging import logger
from ...scripts.models.catalog.items.compound import CompoundItem
from ...scripts.models.catalog.items.group import GroupItem
from ...scripts.models.catalog.items.texture import TextureItem
from ...scripts.ui.controllers.catalog.context_menu import CatalogContextMenuController
from ...scripts.ui.controllers.core.context_visibility import ContextVisibilityController
from ...scripts.ui.controllers.core.startup import StartupController
from ...scripts.ui.controllers.drop.catalog import CatalogCreationHandler
from ...scripts.ui.controllers.drop.payloads import PayloadDropHandler
from ...scripts.ui.controllers.drop.textures import TextureDropHandler
from ...scripts.ui.controllers.interaction.events import InteractionController
from ...scripts.ui.graph_canvas_view import GraphCanvasView
from ...scripts.ui.sections.catalog.constants import (
    CATALOG_TAB_NODEGRAPHS,
    CATALOG_TAB_NODES,
    CATALOG_TAB_TEXTURES,
)
from ...scripts.ui.sections.catalog.delegate import MaterialGraphCatalogDelegate
from ...scripts.ui.sections.catalog.widget import MaterialGraphCatalog
from ...scripts.ui.sections.graph import widget as graph_widget_module
from ...scripts.ui.sections.graph.splitter import MaterialGraphSplitter
from ...scripts.ui.sections.toolbar.menus import ToolbarMenuBuilder
from ..ui_base import MaterialGraphUiTestBase


class _SmokeGraphView:
    """Minimal rendering boundary used while real widgets/controllers stay active."""

    def __init__(self) -> None:
        self.model = None
        self.selection = []
        self.validation_errors = {}
        self.breadcrumb_clicked_index = -1
        self.breadcrumb = []
        self.input_context = None

    def set_input_node_context(self, manager, context_name: str) -> None:
        self.input_context = (manager, context_name)

    def set_validation_errors(self, errors_by_path: dict) -> None:
        self.validation_errors = dict(errors_by_path)

    def focus_on_nodes(self, *_args) -> None:
        """Accept semantic focus requests without a rendered viewport."""

    def layout_all(self) -> None:
        """Accept semantic layout requests without a rendered viewport."""

    def is_point_over_header(self, _item) -> bool:
        return False

    def set_breadcrumb(self, values) -> None:
        self.breadcrumb = list(values)

    def clear_breadcrumb_clicked(self) -> None:
        self.breadcrumb_clicked_index = -1

    def clear(self) -> None:
        """Accept asynchronous graph clearing during model replacement."""

    def destroy(self) -> None:
        """Accept widget teardown at the rendering boundary."""


class _ExtensionDiagnosticHandler(logging.Handler):
    """Capture extension warnings/errors emitted during one smoke workflow."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.records = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class TestUiSmokeWorkflows(MaterialGraphUiTestBase):
    """Exercise user-visible workflows without coordinate or pixel automation."""

    async def setUp(self) -> None:
        """Capture extension diagnostics so clean workflows can assert on them."""
        await super().setUp()
        self._diagnostic_handler = _ExtensionDiagnosticHandler()
        logger.addHandler(self._diagnostic_handler)

    async def tearDown(self) -> None:
        """Detach the per-test diagnostic capture before destroying shared UI state."""
        logger.removeHandler(self._diagnostic_handler)
        self._diagnostic_handler = None
        await super().tearDown()

    def _assert_extension_log_clean(self, start_index: int) -> None:
        records = self._diagnostic_handler.records[start_index:]
        rendered = [f"{record.levelname}: {record.getMessage()}" for record in records]
        self.assertFalse(rendered, f"unexpected Material Graph diagnostics: {rendered}")

    async def _trigger_menu_item(self, menu: omni.ui.Menu, label: str) -> None:
        """Invoke an enabled real OmniUI menu item by its semantic label.

        Pointer delivery and popup hit testing belong to OmniUI.  Calling the callback stored on
        the live widget keeps this smoke layer focused on extension-owned menu construction and
        routing, and avoids coordinate/timing flakiness across Kit versions.
        """

        await self.wait_n_updates(2)

        def _find_path(parent, path):
            for child in omni.ui.Inspector.get_children(parent):
                if isinstance(child, omni.ui.MenuItem) and child.text == label:
                    return [*path, child]
                if isinstance(child, omni.ui.Menu):
                    found = _find_path(child, [*path, child])
                    if found:
                        return found
            return None

        widget_path = _find_path(menu, [])
        self.assertIsNotNone(widget_path, f"menu item not found: {label}")
        item = widget_path[-1]
        self.assertTrue(item.enabled, f"menu item is unexpectedly disabled: {label}")
        self.assertTrue(item.has_triggered_fn(), f"menu item has no extension callback: {label}")
        item.call_triggered_fn()
        menu.hide()
        await self.wait_n_updates(2)

    @staticmethod
    def _define_id_material(stage, name: str, context: str, identifier: str):
        """Create one material terminal driven by an identifier-authored shader."""

        material_path = Sdf.Path(f"/World/Looks/{name}")
        material = UsdShade.Material.Define(stage, material_path)
        shader = UsdShade.Shader.Define(stage, material_path.AppendChild("Surface"))
        shader.CreateIdAttr(identifier)
        output = shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        render_context = "" if context == "universal" else context
        material.CreateSurfaceOutput(render_context).ConnectToSource(output)
        return material, shader

    async def _open_material(self, material, context: str):
        """Open a material through the real window and wait for validation."""

        widget = self._graph_window.graph_widget
        widget._graph_view = _SmokeGraphView()
        widget._context_model_controller._default_context = context
        self._graph_window.open_graph(material.GetPrim())
        await self.wait_n_updates(14)
        self.assertEqual(widget.current_context, context)
        self.assertIsNotNone(widget.model)
        self.assertEqual(widget.model.prim_path, material.GetPath())
        self.assertIsInstance(widget.graph_view, _SmokeGraphView)
        self.assertIsNotNone(widget.isolation_model)
        return widget

    async def test_open_hide_show_and_catalog_toggle_workflow(self) -> None:
        """Open a graph, toggle its catalog control, and restore window visibility."""

        material, _shader = self._define_id_material(
            self._stage,
            "SmokePreview",
            "universal",
            "UsdPreviewSurface",
        )
        widget = await self._open_material(material, "universal")
        splitter_window = await self.create_test_window(width=700, height=360, block_devices=False)
        with splitter_window.frame:
            splitter = MaterialGraphSplitter(
                build_left_fn=lambda: omni.ui.Label("Catalog"),
                build_right_fn=lambda: omni.ui.Label("Graph"),
            )
            splitter.on_build()
        widget._splitter_left = splitter

        widget.set_catalog_visible(True)
        self.assertTrue(splitter.is_panel_visible())
        await self.wait_n_updates(2)
        splitter_buttons = ui_test.WindowRef(splitter_window, "").find_all("**/Button[*]")
        splitter_button = next(button for button in splitter_buttons if button.widget.text in {"<", ">"})
        await splitter_button.click()
        self.assertFalse(splitter.is_panel_visible())
        await splitter_button.click()
        self.assertTrue(splitter.is_panel_visible())

        await self.show_window(False)
        self.assertFalse(self.get_window_handle().visible)
        await self.show_window(True)
        self.assertTrue(self.get_window_handle().visible)
        self.assertEqual(widget.model.prim_path, material.GetPath())
        splitter.destroy()
        splitter_window.visible = False
        await self.finalize_test_no_image()

    async def test_real_graph_toolbar_repeated_menu_and_banner_builds_are_log_clean(self) -> None:
        """Build real toolbar widgets and click the overflow menu twice by semantic lookup."""
        log_start = len(self._diagnostic_handler.records)
        material, _shader = self._define_id_material(
            self._stage,
            "SmokeToolbar",
            "universal",
            "UsdPreviewSurface",
        )
        widget = await self._open_material(material, "universal")
        window = await self.create_test_window(width=900, height=220, block_devices=False)
        ref_names = (
            "_error_indicator_frame",
            "_error_badge_frame",
            "_warning_badge_frame",
            "_upgrade_menu_frame",
            "_error_count_label",
            "_warning_count_label",
            "_error_frame",
            "_warning_frame",
            "_error_label",
            "_warning_label",
            "_error_scroll_frame",
            "_warning_scroll_frame",
            "_error_close_button",
            "_warning_close_button",
        )
        previous_refs = {name: getattr(widget, name, None) for name in ref_names}

        try:
            with window.frame:
                with omni.ui.VStack():
                    widget._build_graph_toolbar()
                    widget._build_error_banner()
                    widget._build_warning_banner()
            await self.wait_n_updates(3)

            error_message = (
                "Invalid connection:\nsource: /Mat/Source.outputs:out\ntarget: /Mat/Target.inputs:in\nreason: mismatch"
            )
            widget.show_error(error_message, log_message=False)
            await self.wait_n_updates(3)
            self.assertEqual(widget._error_label.text, error_message)
            self.assertGreater(widget._error_frame.computed_height, 24)

            long_message = "\n".join(f"diagnostic line {index}" for index in range(20))
            widget.show_error(long_message, log_message=False)
            await self.wait_n_updates(3)
            self.assertLessEqual(widget._error_frame.computed_height, widget._BANNER_MAX_HEIGHT)
            self.assertGreater(widget._error_scroll_frame.scroll_y_max, 0)

            window_ref = ui_test.WindowRef(window, "")
            close_button = next(
                button
                for button in window_ref.find_all("**/Button[*].text=='×'")
                if button.widget is widget._error_close_button
            )
            await close_button.click()
            await self.wait_n_updates(2)
            self.assertFalse(widget._error_frame.visible)
            widget.show_error(long_message, log_message=False)
            self.assertFalse(widget._error_frame.visible)
            widget.show_error(f"{long_message}\nchanged", log_message=False)
            self.assertTrue(widget._error_frame.visible)

            title = window_ref.find("**/Button[*].text=='SmokeToolbar'")
            self.assertIsNotNone(title)
            buttons = window_ref.find_all("**/Button[*]")
            overflow = next(
                (
                    button
                    for button in buttons
                    if str(getattr(button.widget, "image_url", "")).endswith("hamburger.svg")
                ),
                None,
            )
            self.assertIsNotNone(overflow)

            await overflow.click()
            await self.wait_n_updates(2)
            menu_builder = widget._toolbar_controller._menu_builder
            first_menu = menu_builder._menu
            self.assertIsNotNone(first_menu)
            first_menu.hide()

            await overflow.click()
            await self.wait_n_updates(2)
            self.assertIsNot(menu_builder._menu, first_menu)
            menu_builder._menu.hide()
        finally:
            for name, value in previous_refs.items():
                setattr(widget, name, value)
            menu_builder = getattr(widget._toolbar_controller, "_menu_builder", None)
            if menu_builder and menu_builder._menu:
                menu_builder._menu.hide()
                menu_builder._menu = None
            window.visible = False
            await self.finalize_test_no_image()
        self._assert_extension_log_clean(log_start)

    async def test_startup_and_graph_toolbar_controls_route_by_semantic_click(self) -> None:
        """Real buttons should route callbacks without coordinate or application-launch automation."""
        log_start = len(self._diagnostic_handler.records)
        material, _shader = self._define_id_material(
            self._stage,
            "SmokeControls",
            "universal",
            "UsdPreviewSurface",
        )
        widget = await self._open_material(material, "universal")
        window = await self.create_test_window(width=1100, height=360, block_devices=False)
        startup_widget = SimpleNamespace(
            set_toolbar_items=MagicMock(),
            get_toolbar_items=MagicMock(return_value=[]),
            edit_graph=MagicMock(),
            new_graph=MagicMock(),
            on_accept_drop=MagicMock(return_value=True),
            on_drop=MagicMock(),
        )
        create_graph = MagicMock()
        edit_graph = MagicMock()
        switch_context = MagicMock()
        toggle_pause = MagicMock()
        recompile = MagicMock()
        toggle_solo = MagicMock()
        widget._toolbar_controller.on_toolbar_create_graph_clicked = create_graph
        widget._toolbar_controller.on_toolbar_edit_graph_clicked = edit_graph
        widget._toolbar_controller.switch_context = switch_context
        widget._toolbar_controller.toggle_material_compilation = toggle_pause
        widget._toolbar_controller.unpause_and_pause = recompile
        widget._on_solo_clicked = toggle_solo
        previous_pause = widget.model.pause
        widget.model.pause = True

        try:
            with patch.object(graph_widget_module, "is_solo_supported", return_value=(True, "")):
                with window.frame:
                    with omni.ui.VStack():
                        StartupController(startup_widget).build_startup()
                        widget._build_graph_toolbar()
            await self.wait_n_updates(4)

            window_ref = ui_test.WindowRef(window, "")
            await window_ref.find("**/Button[*].text=='Edit Selected Material'").click()
            await window_ref.find("**/Button[*].text=='New Material Graph'").click()

            buttons = window_ref.find_all("**/Button[*]")

            def by_icon(suffix: str):
                return next(
                    button for button in buttons if str(getattr(button.widget, "image_url", "")).endswith(suffix)
                )

            await by_icon("create_graph_dark.svg").click()
            await by_icon("edit_graph_dark.svg").click()
            await by_icon("pause_dark_a.svg").click()
            await by_icon("reload_dark.svg").click()
            await by_icon("solo_dark.svg").click()
            await window_ref.find("**/Button[*].text=='Universal'").click()
            await self.wait_n_updates(3)

            startup_widget.edit_graph.assert_called_once_with()
            startup_widget.new_graph.assert_called_once_with()
            create_graph.assert_called_once_with()
            edit_graph.assert_called_once_with()
            toggle_pause.assert_called_once_with()
            recompile.assert_called_once_with()
            toggle_solo.assert_called_once_with()
            switch_context.assert_called_once_with("universal")
        finally:
            widget.model.pause = previous_pause
            window.visible = False
            await self.finalize_test_no_image()
        self._assert_extension_log_clean(log_start)

    async def test_toolbar_menu_items_route_by_real_semantic_click(self) -> None:
        """Exercise every extension-owned toolbar menu item through real MenuItem widgets."""

        layout = MagicMock()
        frame = MagicMock()
        expansion = MagicMock()
        help_callback = MagicMock()
        builder = ToolbarMenuBuilder("Material Graph")

        try:
            for label, expected in (
                ("Auto Layout Nodes", layout),
                ("Frame Nodes", frame),
                ("Expand All", expansion),
                ("Minimize All", expansion),
                ("Close All", expansion),
            ):
                builder.show_view_menu(True, layout, frame, expansion)
                call_count = expected.call_count
                await self._trigger_menu_item(builder._menu, label)
                self.assertGreater(expected.call_count, call_count, f"toolbar menu callback did not fire: {label}")

            self.assertEqual([call.args[0] for call in expansion.call_args_list], ["open", "minimized", "closed"])

            builder.show_overflow_menu(True, layout, frame, expansion, help_callback)
            await self._trigger_menu_item(builder._menu, "Help / Documentation")
            help_callback.assert_called_once_with()

            page = SimpleNamespace(get_title=lambda: "Material Graph")
            preference_window = MagicMock()
            with (
                patch("omni.kit.window.preferences.get_page_list", return_value=[page]),
                patch("omni.kit.window.preferences.show_preferences_window") as show_preferences,
                patch("omni.kit.window.preferences.select_page") as select_page,
                patch.object(omni.ui.Workspace, "get_window", return_value=preference_window),
            ):
                builder.show_edit_menu()
                await self._trigger_menu_item(builder._menu, "Preferences...")

            show_preferences.assert_called_once_with()
            select_page.assert_called_once_with(page)
            preference_window.focus.assert_called_once_with()
        finally:
            if builder._menu:
                builder._menu.hide()

    async def test_diagnostic_upgrade_menu_routes_single_and_all_actions_semantically(self) -> None:
        """Click the upgrade badge and both real upgrade menu action shapes."""

        widget = self._graph_window.graph_widget
        window = await self.create_test_window(width=680, height=180, block_devices=False)
        changes = [
            SimpleNamespace(prim_path="/Material/First", old_identifier="old_a", new_identifier="new_a"),
            SimpleNamespace(prim_path="/Material/Second", old_identifier="old_b", new_identifier="new_b"),
        ]
        apply_single = MagicMock()
        apply_all = MagicMock()

        try:
            with window.frame:
                widget._build_error_indicator_inline()
            await self.wait_n_updates(2)
            widget._error_indicator_frame.visible = True
            widget._upgrade_menu_frame.visible = True
            with (
                patch.object(widget, "_get_pending_upgrade_changes", return_value=changes),
                patch.object(widget, "_apply_single_upgrade", apply_single),
                patch.object(widget, "_apply_all_upgrades", apply_all),
            ):
                upgrade_label = ui_test.WindowRef(window, "").find("**/Label[*].text=='Upgrade'")
                await upgrade_label.click()
                await self._trigger_menu_item(widget._upgrade_menu, "First: old_a -> new_a")
                apply_single.assert_called_once_with(changes[0])

                await upgrade_label.click()
                await self._trigger_menu_item(widget._upgrade_menu, "Upgrade All (2 nodes)")
                apply_all.assert_called_once_with()
        finally:
            if getattr(widget, "_upgrade_menu", None):
                widget._upgrade_menu.hide()
            window.visible = False
            await self.finalize_test_no_image()

    async def test_catalog_management_and_delete_menus_route_by_semantic_click(self) -> None:
        """Click registry management and item deletion controls on real context menus."""

        catalog_shell = SimpleNamespace(get_active_tab=MagicMock(return_value=CATALOG_TAB_NODEGRAPHS))
        controller = CatalogContextMenuController(SimpleNamespace(_catalog_widget=catalog_shell))
        actions = {
            "New Group": MagicMock(),
            "Refresh Compounds": MagicMock(),
            "Add Compounds Directory": MagicMock(),
            "Clear Compounds Directories": MagicMock(),
        }
        controller.create_group = actions["New Group"]
        controller.refresh_compounds = actions["Refresh Compounds"]
        controller.pick_folder = actions["Add Compounds Directory"]
        controller.clear_compound_dirs = actions["Clear Compounds Directories"]

        catalog = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        catalog._item_context_menu = None
        catalog._confirm_remove_groups = MagicMock()
        catalog._confirm_remove_textures = MagicMock()
        catalog._confirm_remove_compound_groups = MagicMock()
        catalog._confirm_remove_compounds = MagicMock()
        texture_group = GroupItem("Texture Group")
        texture_group.is_texture_group = True
        compound_group = GroupItem("Compound Group")
        compound_group.is_compound_group = True
        texture = TextureItem("Texture", "texture.png", "")
        compound = CompoundItem("Compound", "", "", "", "compound.usda", "/Compound")

        try:
            with patch(
                "omni.kit.window.material_graph.scripts.ui.controllers.catalog.context_menu.show_menu_at_cursor",
                side_effect=lambda menu, *_args: menu.show(),
            ):
                for label, callback in actions.items():
                    controller.show_menu([])
                    await self._trigger_menu_item(controller._menu, label)
                    callback.assert_called_once_with()

            catalog_module = "omni.kit.window.material_graph.scripts.ui.sections.catalog.widget.show_menu_at_cursor"
            with patch(catalog_module, side_effect=lambda menu, *_args: menu.show()):
                for label, selection, callback, expected in (
                    ("Delete Group", [texture_group], catalog._confirm_remove_groups, [texture_group]),
                    ("Delete Texture", [texture], catalog._confirm_remove_textures, [texture]),
                    ("Delete Group", [compound_group], catalog._confirm_remove_compound_groups, [compound_group]),
                    ("Delete Nodegraph", [compound], catalog._confirm_remove_compounds, [compound]),
                ):
                    if isinstance(selection[0], (TextureItem,)) or selection[0] is texture_group:
                        self.assertTrue(catalog._show_texture_context_menu(selection))
                    else:
                        self.assertTrue(catalog._show_nodegraph_context_menu(selection))
                    await self._trigger_menu_item(catalog._item_context_menu, label)
                    callback.assert_called_once_with(expected)
        finally:
            if controller._menu:
                controller._menu.hide()
            if catalog._item_context_menu:
                catalog._item_context_menu.hide()

    @staticmethod
    def _make_graph_canvas_menu_view():
        """Return a minimal real GraphCanvasView surface for one context-menu interaction."""
        view = GraphCanvasView.__new__(GraphCanvasView)
        model_node = object()
        model_port = object()
        inner_node = SimpleNamespace(type="SmokeNode")

        class _Model:
            def __getitem__(self, item):
                if item is model_node:
                    return inner_node
                return SimpleNamespace(inputs=[object()])

        view._model = _Model()
        view._scene_model_nodes = [model_node]
        view._node_context_menu = None
        view._io_node_context_menu = None
        view._port_context_menu = None
        view._remove_io_node = MagicMock()
        view._disconnect_port = MagicMock()
        view._find_port_owner_node = MagicMock(return_value=None)
        view._port_has_output_connections = MagicMock(return_value=False)
        return view, model_node, model_port

    async def test_graph_canvas_node_context_menu_routes_by_semantic_click(self) -> None:
        """Click a registered node action through a real MenuItem."""

        view, _model_node, _model_port = self._make_graph_canvas_menu_view()
        custom_callback = MagicMock()
        custom_item = SimpleNamespace(label="Inspect Smoke Node", callback=custom_callback)

        try:
            with (
                patch(
                    "omni.kit.window.material_graph.scripts.api.context_menu.get_node_menu_items",
                    return_value=[custom_item],
                ),
                patch(
                    "omni.kit.window.material_graph.scripts.ui.interaction.menu_utils.show_menu_at_cursor",
                    side_effect=lambda menu, *_args: menu.show(),
                ),
            ):
                view._show_node_context_menu(0)
                await self._trigger_menu_item(view._node_context_menu, "Inspect Smoke Node")
            custom_callback.assert_called_once()
            self.assertEqual(custom_callback.call_args.args[0], "SmokeNode")
        finally:
            if view._node_context_menu:
                view._node_context_menu.hide()

    async def test_graph_canvas_io_context_menu_routes_by_semantic_click(self) -> None:
        """Click the IO-node Remove action through a real MenuItem."""

        view, model_node, _model_port = self._make_graph_canvas_menu_view()
        try:
            view._show_io_node_context_menu(0)
            await self._trigger_menu_item(view._io_node_context_menu, "Remove")
            view._remove_io_node.assert_called_once_with(model_node)
        finally:
            if view._io_node_context_menu:
                view._io_node_context_menu.hide()

    async def test_graph_canvas_disconnect_context_menu_routes_by_semantic_click(self) -> None:
        """Click the port Disconnect action through a real MenuItem."""

        view, _model_node, model_port = self._make_graph_canvas_menu_view()
        try:
            view._show_port_context_menu(model_port)
            await self._trigger_menu_item(view._port_context_menu, "Disconnect")
            view._disconnect_port.assert_called_once_with(model_port)
        finally:
            if view._port_context_menu:
                view._port_context_menu.hide()

    async def test_graph_canvas_rename_port_context_menu_routes_by_semantic_click(self) -> None:
        """Click the nodegraph-port Rename action through a real MenuItem."""

        view, _model_node, model_port = self._make_graph_canvas_menu_view()
        view._show_nodegraph_port_rename_dialog = MagicMock()
        view._remove_nodegraph_port = MagicMock()
        view._is_nodegraph_interface_owner = MagicMock(return_value=True)
        view._find_port_owner_node.return_value = object()
        try:
            view._show_port_context_menu(model_port)
            await self._trigger_menu_item(view._port_context_menu, "Rename")
            view._show_nodegraph_port_rename_dialog.assert_called_once_with(model_port)
        finally:
            if view._port_context_menu:
                view._port_context_menu.hide()

    async def test_graph_canvas_remove_port_context_menu_routes_by_semantic_click(self) -> None:
        """Click the nodegraph-port Remove action through a real MenuItem."""

        view, _model_node, model_port = self._make_graph_canvas_menu_view()
        view._show_nodegraph_port_rename_dialog = MagicMock()
        view._remove_nodegraph_port = MagicMock()
        view._is_nodegraph_interface_owner = MagicMock(return_value=True)
        view._find_port_owner_node.return_value = object()
        try:
            view._show_port_context_menu(model_port)
            await self._trigger_menu_item(view._port_context_menu, "Remove")
            view._remove_nodegraph_port.assert_called_once_with(model_port)
        finally:
            if view._port_context_menu:
                view._port_context_menu.hide()

    async def test_background_menu_catalog_and_custom_actions_route_semantically(self) -> None:
        """Click both dynamic catalog creation and registered background action menu items."""

        child = SimpleNamespace(name="Smoke Catalog Node", filtered=True)
        group = SimpleNamespace(name="Smoke Group", children=[child], filtered=True)
        create_from_catalog = MagicMock()
        node_creation = SimpleNamespace(
            get_hovered_position=lambda: (12, 18),
            create_from_catalog=create_from_catalog,
        )
        controller = InteractionController(
            widget=SimpleNamespace(current_context="universal"),
            node_creation_controller=node_creation,
            catalog_model=SimpleNamespace(children=[group]),
        )
        background_callback = MagicMock()
        background_item = SimpleNamespace(label="Smoke Background Action", callback=background_callback)

        module = "omni.kit.window.material_graph.scripts.ui.controllers.interaction.events"
        try:
            with (
                patch(f"{module}.get_background_menu_items", return_value=[background_item]),
                patch(f"{module}.show_menu_at_cursor", side_effect=lambda menu, *_args: menu.show()),
            ):
                controller.on_right_mouse_button_pressed([])
                await self._trigger_menu_item(controller._right_click_menu, "Smoke Catalog Node")
                create_from_catalog.assert_called_once_with(child, (12, 18))

                controller.on_right_mouse_button_pressed([])
                await self._trigger_menu_item(controller._right_click_menu, "Smoke Background Action")
                background_callback.assert_called_once_with(items=[], mouse_position=(12, 18))
        finally:
            controller.destroy()

    async def test_variant_and_texture_choice_menus_route_by_semantic_click(self) -> None:
        """Select real menu entries for all extension-owned drop choice workflows."""

        payload = {
            "identifier": "id.default",
            "variant_subidentifiers": ["variant_a", "variant_b"],
            "variant_identifiers": {"variant_b": "id.variant_b"},
            "variant_output_types": {"variant_b": "-> color3f"},
            "requires_variant_selection": True,
        }
        menu_patch = patch(
            "omni.kit.window.material_graph.scripts.ui.controllers.drop.catalog.show_menu_at_cursor",
            side_effect=lambda menu, *_args: menu.show(),
        )

        graph_view = SimpleNamespace(model=True)
        drop_callback = MagicMock()
        catalog_handler = CatalogCreationHandler(
            SimpleNamespace(graph_view=graph_view),
            MagicMock(),
            drop_callback,
        )

        class _DropEvent:
            def __init__(self, mime_data, position):
                self.mime_data = mime_data
                self.x, self.y = position

        with menu_patch:
            catalog_handler._show_variant_menu(payload, payload["variant_subidentifiers"], (4, 6), _DropEvent)
            await self._trigger_menu_item(catalog_handler._variant_menu, "variant_b -> color3f")
        selected = json.loads(drop_callback.call_args.args[0].mime_data)
        self.assertEqual(selected["identifier"], "id.variant_b")
        self.assertEqual(selected["subidentifier"], "variant_b")
        self.assertFalse(selected["requires_variant_selection"])

        payload_widget = SimpleNamespace(current_context="mdl")
        payload_handler = PayloadDropHandler(payload_widget, MagicMock(), None, None)
        create_variant = MagicMock(return_value=True)
        payload_handler._create_shader_from_payload = create_variant
        model = object()
        position = object()
        with patch(
            "omni.kit.window.material_graph.scripts.ui.controllers.drop.payloads.show_menu_at_cursor",
            side_effect=lambda menu, *_args: menu.show(),
        ):
            payload_handler._show_shader_variant_menu(payload, model, position, SimpleNamespace(x=1, y=2))
            await self._trigger_menu_item(payload_handler._shader_variant_menu, "variant_b -> color3f")
        selected_payload = create_variant.call_args.args[0]
        self.assertEqual(selected_payload["identifier"], "id.variant_b")
        self.assertEqual(selected_payload["subidentifier"], "variant_b")

        choices = [
            (SimpleNamespace(name="Texture Color", identifier="texture_color"), "file"),
            (SimpleNamespace(name="Texture Float", identifier="texture_float"), "file"),
        ]
        create_texture = MagicMock()
        texture_handler = TextureDropHandler(SimpleNamespace(), MagicMock())
        with patch(
            "omni.kit.window.material_graph.scripts.ui.controllers.drop.textures.show_menu_at_cursor",
            side_effect=lambda menu, *_args: menu.show(),
        ):
            texture_handler._show_choices_menu(choices, create_texture, "smoke.png", SimpleNamespace(x=2, y=3))
            await self.wait_n_updates(3)
            await self._trigger_menu_item(texture_handler._texture_menu, "Texture Float")
        create_texture.assert_called_once_with(choices[1], "smoke.png")

        catalog_handler.destroy()
        payload_handler.destroy()
        texture_handler.destroy()

    async def test_context_visibility_menu_mutates_usd_by_semantic_click(self) -> None:
        """A real checkable context item should author visibility metadata through the command layer."""

        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/SmokeVisibility")
        plugins = [
            SimpleNamespace(name="universal", display_name="Universal"),
            SimpleNamespace(name="mdl", display_name="MDL"),
        ]
        widget = SimpleNamespace(
            model=SimpleNamespace(stage=self._stage),
            current_context="universal",
            _context_manager=SimpleNamespace(get_plugins=lambda: plugins),
            request_model_refresh=MagicMock(),
            show_error=MagicMock(),
        )
        controller = ContextVisibilityController(widget)

        try:
            controller.show_menu(nodegraph.GetPath())
            await self.wait_n_updates(3)
            await self._trigger_menu_item(controller._menu, "MDL")
            visibility = nodegraph.GetPrim().GetCustomDataByKey("omni:ui")["contextVisibility"]
            self.assertEqual(list(visibility), ["universal"])
            widget.request_model_refresh.assert_called_once_with()
            widget.show_error.assert_not_called()
        finally:
            controller.destroy()

    async def test_real_catalog_tabs_and_delegate_rendering_are_log_clean(self) -> None:
        """Render catalog controls/items and click tabs without coordinate automation."""
        log_start = len(self._diagnostic_handler.records)
        widget = self._graph_window.graph_widget
        window = await self.create_test_window(width=520, height=540, block_devices=False)
        delegate = MaterialGraphCatalogDelegate()
        catalog = None

        try:
            with window.frame:
                catalog = MaterialGraphCatalog(
                    model=widget.catalog_model,
                    delegate=delegate,
                    search_field_style=widget.style,
                    height=omni.ui.Percent(100),
                )
            await self.wait_n_updates(5)

            self.assertIsNotNone(catalog._tree_view)
            window_ref = ui_test.WindowRef(window, "")
            textures = window_ref.find("**/Button[*].text=='Textures'")
            self.assertIsNotNone(textures)

            await textures.click()
            await self.wait_n_updates(3)
            self.assertEqual(catalog.get_active_tab(), CATALOG_TAB_TEXTURES)
            nodegraphs = window_ref.find("**/Button[*].text=='NodeGraphs'")
            self.assertIsNotNone(nodegraphs)
            await nodegraphs.click()
            await self.wait_n_updates(3)
            self.assertEqual(catalog.get_active_tab(), CATALOG_TAB_NODEGRAPHS)
            nodes = window_ref.find("**/Button[*].text=='Nodes'")
            self.assertIsNotNone(nodes)
            await nodes.click()
            await self.wait_n_updates(3)
            self.assertEqual(catalog.get_active_tab(), CATALOG_TAB_NODES)

            filter_by_text = MagicMock()
            catalog._GraphEditorCoreCatalog__filter_by_text = filter_by_text
            search_model = catalog._GraphEditorCoreCatalog__search_field._search_field.model
            search_model.set_value("semantic search")
            await self.wait_n_updates(2)
            filter_by_text.assert_called_with("semantic search")

            group = GroupItem("Textures")
            group.is_texture_group = True
            texture = TextureItem("Invalid Texture", "missing.png", "", valid=False)
            value_models = {
                0: SimpleNamespace(as_string="Invalid Texture"),
                1: SimpleNamespace(as_string="Missing texture source"),
                3: SimpleNamespace(as_string="The source file could not be resolved."),
            }
            model = MagicMock()
            model.can_item_have_children.return_value = True
            model.get_item_value_model.side_effect = lambda _item, column: value_models.get(
                column, SimpleNamespace(as_string="Textures")
            )
            with window.frame:
                with patch.object(delegate, "build_icon_with_tooltip"):
                    delegate.build_branch(model, group, 0, 0, True)
                    delegate.build_section_widget(model, group, 0, 0, True)
                    delegate.build_item_widget(model, texture, 0, 1, False)
            await self.wait_n_updates(2)
        finally:
            if catalog:
                catalog.destroy()
            window.visible = False
            await self.finalize_test_no_image()
        self._assert_extension_log_clean(log_start)

    async def test_invalid_identifier_keeps_graph_open_with_visual_error_state(self) -> None:
        """Keep an unresolved shader visible and allow its live error banner to be dismissed."""

        widget = self._graph_window.graph_widget
        window = await self.create_test_window(width=900, height=220, block_devices=False)
        try:
            with window.frame:
                with omni.ui.VStack(width=omni.ui.Percent(100), height=omni.ui.Percent(100)):
                    with omni.ui.HStack(height=26):
                        widget._build_error_indicator_inline()
                        omni.ui.Spacer()
                    widget._build_validation_banners()
                    omni.ui.Spacer()
            await self.wait_n_updates(3)
            material, shader = self._define_id_material(
                self._stage,
                "SmokeInvalid",
                "universal",
                "DefinitelyMissingMaterialGraphSmokeDefinition",
            )
            widget = await self._open_material(material, "universal")
            await self.wait_n_updates(3)

            shader_path = shader.GetPath()
            shader_model = widget.model.get_item_model(shader_path)
            self.assertIsNotNone(shader_model)
            self.assertFalse(shader_model.valid)
            self.assertIsNotNone(widget._last_validation_result)
            self.assertTrue(
                any(
                    issue.code == "INVALID_NODE_DEFINITION_MISSING" and issue.prim_path == str(shader_path)
                    for issue in widget._last_validation_result.issues
                )
            )
            self.assertIn(str(shader_path), widget.graph_view.validation_errors)
            self.assertTrue(widget._error_frame.visible)
            self.assertGreater(widget._error_close_button.computed_width, 0)
            self.assertGreater(widget._error_close_button.computed_height, 0)

            window_ref = ui_test.WindowRef(window, "")
            close_button = next(
                button
                for button in window_ref.find_all("**/Button[*].text=='×'")
                if button.widget is widget._error_close_button
            )
            await close_button.click()
            await self.wait_n_updates(3)
            self.assertEqual(widget._dismissed_error_message, widget._error_message)
            self.assertFalse(widget._error_frame.visible)

            await ui_test.WidgetRef(widget._error_badge_frame, "", window).click()
            await self.wait_n_updates(3)
            self.assertIsNone(widget._dismissed_error_message)
            self.assertTrue(widget._error_frame.visible)

            await close_button.click()
            await self.wait_n_updates(3)
            self.assertFalse(widget._error_frame.visible)

            widget._context_model_controller._schedule_validation(widget.current_context)
            await self.wait_n_updates(5)
            self.assertFalse(widget._error_frame.visible)

            widget.clear_error()
            widget.show_warning("Material Graph warning smoke", log_message=False)
            await self.wait_n_updates(2)
            warning_close_button = next(
                button
                for button in window_ref.find_all("**/Button[*].text=='×'")
                if button.widget is widget._warning_close_button
            )
            await warning_close_button.click()
            await self.wait_n_updates(3)
            self.assertEqual(widget._dismissed_warning_message, widget._warning_message)
            self.assertFalse(widget._warning_frame.visible)

            widget._warning_badge_frame.visible = True
            widget._warning_count_label.text = "1"
            await self.wait_n_updates(2)
            await ui_test.WidgetRef(widget._warning_badge_frame, "", window).click()
            await self.wait_n_updates(3)
            self.assertIsNone(widget._dismissed_warning_message)
            self.assertTrue(widget._warning_frame.visible)
        finally:
            window.visible = False
            await self.finalize_test_no_image()

    async def test_context_tab_switch_workflow(self) -> None:
        """Switch between two authored render contexts through the widget controller."""

        material, _universal = self._define_id_material(
            self._stage,
            "SmokeContexts",
            "universal",
            "UsdPreviewSurface",
        )
        mtlx_shader = UsdShade.Shader.Define(self._stage, material.GetPath().AppendChild("MtlxSurface"))
        mtlx_shader.CreateIdAttr("ND_standard_surface_surfaceshader")
        mtlx_output = mtlx_shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("mtlx").ConnectToSource(mtlx_output)

        widget = await self._open_material(material, "universal")
        universal_model = widget.model
        self.assertTrue(widget.set_context("mtlx"))
        await self.wait_n_updates(3)
        self.assertEqual(widget.current_context, "mtlx")
        self.assertIsNot(widget.model, universal_model)
        self.assertEqual(widget.model.prim_path, material.GetPath())

        self.assertTrue(widget.set_context("universal"))
        await self.wait_n_updates(3)
        self.assertEqual(widget.current_context, "universal")
        self.assertIs(widget.model, universal_model)

    async def test_nodegraph_navigation_and_breadcrumb_workflow(self) -> None:
        """Navigate into a nested graph and return through the compound controller."""

        material_path = Sdf.Path("/World/Looks/SmokeNested")
        material = UsdShade.Material.Define(self._stage, material_path)
        nodegraph = UsdShade.NodeGraph.Define(self._stage, material_path.AppendChild("Compound"))
        shader = UsdShade.Shader.Define(self._stage, nodegraph.GetPath().AppendChild("Surface"))
        shader.CreateIdAttr("UsdPreviewSurface")
        shader_output = shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        graph_output = nodegraph.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        graph_output.ConnectToSource(shader_output)
        material.CreateSurfaceOutput("universal").ConnectToSource(graph_output)

        widget = await self._open_material(material, "universal")
        nodegraph_model = widget.model.get_item_model(nodegraph.GetPath())
        self.assertIsNotNone(nodegraph_model)

        widget.set_current_compound(nodegraph_model, focus=False, refresh=False)
        await self.wait_n_updates(2)
        self.assertIs(widget.current_model, nodegraph_model)
        self.assertIs(widget.isolation_model._root, nodegraph_model)

        widget.set_current_compound(widget.model, focus=False, refresh=False)
        self.assertIs(widget.current_model, widget.model)
        self.assertIs(widget.isolation_model._root, widget.model)
        widget._breadcrumbs.destroy()
        widget._breadcrumbs = None
