# pylint: disable=protected-access
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import carb

from ...scripts.config.paths import Paths
from ...scripts.models.catalog.items.compound import CompoundItem
from ...scripts.models.catalog.items.group import GroupItem
from ...scripts.models.catalog.items.texture import TextureItem
from ...scripts.ui.sections.catalog import widget as catalog_widget_module
from ...scripts.ui.sections.catalog.constants import (
    CATALOG_TAB_NODEGRAPHS,
    CATALOG_TAB_NODES,
    CATALOG_TAB_TEXTURES,
)
from ...scripts.ui.sections.catalog.widget import MaterialGraphCatalog
from ..base import MaterialGraphTestBase


class TestCatalogWidget(MaterialGraphTestBase):
    """MaterialGraphCatalog shows the catalog tree; double-click renames (via dialog) and delete key
    triggers group removal with confirmation. We test rename flow (patch get_compound_registry and
    InputDialog so we don't need real UI) and delete key routing to _confirm_remove_groups."""

    async def test_rename_nodegraph_group_uses_dialog(self) -> None:
        """Double-click shows rename dialog and renames."""
        # Patch get_compound_registry and InputDialog so we control dialog result and avoid real UI.
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._active_tab = CATALOG_TAB_NODEGRAPHS
        widget._rename_dialog = None

        item = CompoundItem(
            name="CompoundA",
            info="info",
            icon="",
            tooltip="tooltip",
            source_asset="asset.usda",
            identifier="/GraphA",
            context_visibility=["mdl"],
            group="GroupA",
        )

        registry = MagicMock()

        class DummyDialog:
            def __init__(self, *_args, **kwargs):
                self._ok = kwargs.get("ok_handler")

            def get_value(self):
                return "Renamed"

            def hide(self):
                return None

            def show(self):
                if self._ok:
                    self._ok(self)

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.sections.catalog.widget.get_compound_registry",
                return_value=registry,
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.sections.catalog.widget.InputDialog",
                side_effect=DummyDialog,
            ),
        ):
            widget.handle_item_double_clicked(item)

        registry.rename_compound.assert_called_once_with(item, "Renamed")

    async def test_delete_group_flow_uses_confirm(self) -> None:
        """Delete key routes to group removal."""
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._active_tab = CATALOG_TAB_TEXTURES
        group = GroupItem("GroupA")
        setattr(group, "is_texture_group", True)
        widget._tree_view = SimpleNamespace(selection=[group])

        called = {"value": False}

        def _confirm_remove_groups(_items):
            called["value"] = True

        widget._confirm_remove_groups = _confirm_remove_groups

        handled = widget._on_key_pressed(int(carb.input.KeyboardInput.DEL), 0, True)
        self.assertTrue(handled)
        self.assertTrue(called["value"])

    async def test_parse_payload_invalid_json_returns_none_and_logs(self) -> None:
        """Invalid payload JSON returns None and logs."""
        # Patch logger.warning to assert warning is emitted.
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.sections.catalog.widget.logger.warning",
            autospec=True,
        ) as warn:
            payload = widget._parse_payload("{invalid json")
        self.assertIsNone(payload)
        warn.assert_called_once()

    async def test_parse_payload_plain_path_returns_none_without_warning(self) -> None:
        """Plain path payloads should be ignored without JSON parse warnings."""
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.sections.catalog.widget.logger.warning",
            autospec=True,
        ) as warn:
            payload = widget._parse_payload("C:/textures/albedo.png")
        self.assertIsNone(payload)
        warn.assert_not_called()

    async def test_extract_drop_data_supports_event_string_and_keyword_signatures(self) -> None:
        event = SimpleNamespace(mime_data="event-data")
        self.assertEqual(MaterialGraphCatalog._extract_drop_data(event), ("event-data", event))
        self.assertEqual(MaterialGraphCatalog._extract_drop_data("arg-data"), ("arg-data", None))
        self.assertEqual(MaterialGraphCatalog._extract_drop_data(source="kw-data"), ("kw-data", None))
        self.assertEqual(MaterialGraphCatalog._extract_drop_data(object()), (None, None))

    async def test_accept_drop_proxy_filters_catalog_and_updates_overlay(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._drop_overlay_controller = MagicMock()
        widget._accept_drop_proxy_fn = MagicMock(return_value=True)

        self.assertFalse(widget._on_accept_drop_proxy(object()))
        widget._drop_overlay_controller.hide.assert_called_once_with()

        widget._drop_overlay_controller.reset_mock()
        self.assertFalse(widget._on_accept_drop_proxy('{"origin": "catalog", "type": "Texture"}'))
        widget._accept_drop_proxy_fn.assert_not_called()
        widget._drop_overlay_controller.hide.assert_called_once_with()

        widget._drop_overlay_controller.reset_mock()
        self.assertTrue(widget._on_accept_drop_proxy("C:/textures/albedo.png"))
        widget._accept_drop_proxy_fn.assert_called_once_with("C:/textures/albedo.png")
        widget._drop_overlay_controller.show.assert_called_once_with(True)

    async def test_drop_proxy_forwards_real_and_synthetic_events(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._drop_overlay_controller = MagicMock()
        widget._drop_proxy_fn = MagicMock()
        event = SimpleNamespace(mime_data="event-data", x=1, y=2)

        widget._on_tree_drop(event)
        widget._drop_proxy_fn.assert_called_once_with(event)
        widget._drop_proxy_fn.reset_mock()
        widget._on_drop_proxy("synthetic-data")
        synthetic = widget._drop_proxy_fn.call_args.args[0]
        self.assertEqual((synthetic.mime_data, synthetic.x, synthetic.y), ("synthetic-data", None, None))
        self.assertEqual(widget._drop_overlay_controller.hide.call_count, 2)

        widget._drop_proxy_fn = None
        widget._on_drop_proxy("ignored")

    async def test_tab_filter_and_delete_blocking_follow_active_tab(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        model = MagicMock()
        widget._GraphEditorCoreCatalog__model = model
        widget._tree_view = None

        for tab in (CATALOG_TAB_NODES, CATALOG_TAB_NODEGRAPHS, CATALOG_TAB_TEXTURES):
            widget._active_tab = tab
            widget._apply_tab_filter()
            model.set_filter_group.assert_called_with(tab)
        self.assertFalse(widget.should_block_delete_nodes())

        texture_group = GroupItem("Textures")
        texture_group.is_texture_group = True
        compound_group = GroupItem("Graphs")
        compound_group.is_compound_group = True
        texture = TextureItem("Albedo", "albedo.png", "icon.png")
        compound = CompoundItem("Graph", "", "", "", "asset.usd", "Graph")
        widget._tree_view = SimpleNamespace(selection=[])
        self.assertFalse(widget.should_block_delete_nodes())
        widget._active_tab = CATALOG_TAB_TEXTURES
        widget._tree_view.selection = [texture_group, texture]
        self.assertTrue(widget.should_block_delete_nodes())
        widget._active_tab = CATALOG_TAB_NODEGRAPHS
        widget._tree_view.selection = [compound_group, compound]
        self.assertTrue(widget.should_block_delete_nodes())

    async def test_texture_drop_routes_registry_assignment_and_failures(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._active_tab = CATALOG_TAB_TEXTURES
        widget._resolve_drop_group = MagicMock(return_value=None)
        item = TextureItem("Albedo", "albedo.png", "icon.png", group="Old")
        registry = SimpleNamespace(
            get_item_by_source=MagicMock(return_value=item),
            assign_group=MagicMock(return_value=True),
        )
        with patch.object(catalog_widget_module, "get_texture_registry", return_value=registry):
            widget.handle_texture_drop({"source": "albedo.png"})
            registry.assign_group.assert_called_once_with(item, "")
            widget.handle_texture_drop({})

            target = GroupItem("New")
            target.is_texture_group = True
            item.group = "New"
            registry.assign_group.reset_mock()
            widget.handle_texture_drop({"source": "albedo.png"}, target_group=target)
            registry.assign_group.assert_not_called()

            item.group = "Old"
            registry.assign_group.return_value = False
            with patch.object(catalog_widget_module.logger, "warning") as warning:
                widget.handle_texture_drop({"source": "albedo.png"}, target_group=target)
            warning.assert_called_once()

        widget._active_tab = CATALOG_TAB_NODES
        registry.get_item_by_source.reset_mock()
        with patch.object(catalog_widget_module, "get_texture_registry", return_value=registry):
            widget.handle_texture_drop({"source": "albedo.png"})
        registry.get_item_by_source.assert_not_called()

    async def test_compound_drop_routes_registry_assignment_and_failures(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._active_tab = CATALOG_TAB_NODEGRAPHS
        widget._resolve_drop_group = MagicMock(return_value=None)
        item = CompoundItem("Graph", "", "", "", "asset.usd", "Graph", group="Old")
        registry = SimpleNamespace(
            get_item_by_identifier=MagicMock(return_value=item),
            assign_group=MagicMock(return_value=True),
        )
        payload = {"source_asset": "asset.usd", "identifier": "Graph"}
        with patch.object(catalog_widget_module, "get_compound_registry", return_value=registry):
            widget.handle_compound_drop(payload)
            registry.assign_group.assert_called_once_with(item, "")
            widget.handle_compound_drop({"source_asset": "asset.usd"})

            target = GroupItem("New")
            target.is_compound_group = True
            item.group = "New"
            registry.assign_group.reset_mock()
            widget.handle_compound_drop(payload, target_group=target)
            registry.assign_group.assert_not_called()

            item.group = "Old"
            registry.assign_group.return_value = False
            with patch.object(catalog_widget_module.logger, "warning") as warning:
                widget.handle_compound_drop(payload, target_group=target)
            warning.assert_called_once()

    async def test_payload_parsing_and_group_drop_validation(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        self.assertIsNone(widget._parse_payload(""))
        self.assertIsNone(widget._parse_payload("[]"))
        payload = {"type": "Texture", "source": "albedo.png"}
        self.assertEqual(widget._parse_payload('{"type": "Texture", "source": "albedo.png"}'), payload)

        texture_group = GroupItem("Textures")
        texture_group.is_texture_group = True
        compound_group = GroupItem("Graphs")
        compound_group.is_compound_group = True
        widget._active_tab = CATALOG_TAB_NODES
        self.assertFalse(widget.accept_group_drop(texture_group, "{}"))
        widget._active_tab = CATALOG_TAB_TEXTURES
        self.assertTrue(widget.accept_group_drop(texture_group, '{"type":"Texture","source":"a.png"}'))
        self.assertFalse(widget.accept_group_drop(texture_group, '{"type":"Texture"}'))
        widget._active_tab = CATALOG_TAB_NODEGRAPHS
        self.assertTrue(widget.accept_group_drop(compound_group, '{"type":"ImportNodeGraph"}'))
        self.assertFalse(widget.accept_group_drop(GroupItem("Other"), "{}"))

    async def test_drop_on_group_routes_matching_payloads_only(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget.handle_texture_drop = MagicMock()
        widget.handle_compound_drop = MagicMock()
        texture_group = GroupItem("Textures")
        texture_group.is_texture_group = True
        compound_group = GroupItem("Graphs")
        compound_group.is_compound_group = True

        widget.drop_on_group(object(), SimpleNamespace(mime_data="{}"))
        widget.drop_on_group(texture_group, SimpleNamespace(mime_data="not-json"))
        event = SimpleNamespace(mime_data='{"type":"Texture","source":"a.png"}')
        widget.drop_on_group(texture_group, event)
        widget.handle_texture_drop.assert_called_once_with(
            {"type": "Texture", "source": "a.png"}, event, target_group=texture_group
        )
        event = SimpleNamespace(mime_data='{"type":"ImportNodeGraph"}')
        widget.drop_on_group(compound_group, event)
        widget.handle_compound_drop.assert_called_once_with(
            {"type": "ImportNodeGraph"}, event, target_group=compound_group
        )
        self.assertIsNone(widget._resolve_drop_group())

    async def test_delete_key_and_selection_routing_are_headless(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._tree_view = SimpleNamespace(selection=[])
        widget._active_tab = CATALOG_TAB_TEXTURES
        self.assertFalse(widget._on_key_pressed(int(carb.input.KeyboardInput.DEL), 0, False))
        self.assertFalse(widget._on_key_pressed(999, 0, True))
        self.assertTrue(widget._on_key_pressed(int(carb.input.KeyboardInput.DEL), 0, True))

        texture_group = GroupItem("Textures")
        texture_group.is_texture_group = True
        texture = TextureItem("Albedo", "albedo.png", "icon.png")
        widget._confirm_remove_groups = MagicMock()
        widget._confirm_remove_textures = MagicMock()
        widget._handle_texture_delete_selection([texture_group, texture])
        widget._confirm_remove_groups.assert_called_once_with([texture_group])
        widget._handle_texture_delete_selection([texture])
        widget._confirm_remove_textures.assert_called_once_with([texture])

        compound_group = GroupItem("Graphs")
        compound_group.is_compound_group = True
        compound = CompoundItem("Graph", "", "", "", "asset.usd", "Graph")
        widget._confirm_remove_compound_groups = MagicMock()
        widget._confirm_remove_compounds = MagicMock()
        widget._handle_nodegraph_delete_selection([compound_group, compound])
        widget._confirm_remove_compound_groups.assert_called_once_with([compound_group])
        widget._handle_nodegraph_delete_selection([compound])
        widget._confirm_remove_compounds.assert_called_once_with([compound])

    async def test_confirmation_dialogs_apply_registry_mutations(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        dialogs = []

        class DummyDialog:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.show = MagicMock()
                self.hide = MagicMock()
                dialogs.append(self)

        texture = TextureItem("Albedo", "albedo.png", "icon.png")
        texture_group = GroupItem("Textures")
        compound = CompoundItem("Graph", "", "", "", "asset.usd", "Graph")
        compound_group = GroupItem("Graphs")
        texture_registry = SimpleNamespace(remove_texture=MagicMock(), remove_group=MagicMock())
        compound_registry = SimpleNamespace(remove_compound=MagicMock(), remove_group=MagicMock())
        with (
            patch.object(catalog_widget_module, "MessageDialog", DummyDialog),
            patch.object(catalog_widget_module, "get_texture_registry", return_value=texture_registry),
            patch.object(catalog_widget_module, "get_compound_registry", return_value=compound_registry),
        ):
            widget._confirm_remove_textures([texture])
            dialogs[-1].kwargs["ok_handler"](dialogs[-1])
            widget._confirm_remove_groups([texture_group])
            dialogs[-1].kwargs["ok_handler"](dialogs[-1])
            widget._confirm_remove_compounds([compound])
            dialogs[-1].kwargs["ok_handler"](dialogs[-1])
            widget._confirm_remove_compound_groups([compound_group])
            dialogs[-1].kwargs["ok_handler"](dialogs[-1])

        texture_registry.remove_texture.assert_called_once_with(texture)
        texture_registry.remove_group.assert_called_once_with("Textures")
        compound_registry.remove_compound.assert_called_once_with(compound)
        compound_registry.remove_group.assert_called_once_with("Graphs")
        self.assertTrue(all(dialog.show.called and dialog.hide.called for dialog in dialogs))

    async def test_double_click_rename_routes_tabs_items_and_validated_values(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._show_rename_dialog = MagicMock()
        texture = TextureItem("Albedo", "albedo.png", "icon.png")
        texture_group = GroupItem("Textures")
        texture_group.is_texture_group = True
        compound = CompoundItem("Graph", "", "", "", "asset.usd", "Graph")
        compound_group = GroupItem("Graphs")
        compound_group.is_compound_group = True
        texture_registry = SimpleNamespace(rename_texture=MagicMock(), rename_group=MagicMock())
        compound_registry = SimpleNamespace(rename_compound=MagicMock(), rename_group=MagicMock())

        with (
            patch.object(catalog_widget_module, "get_texture_registry", return_value=texture_registry),
            patch.object(catalog_widget_module, "get_compound_registry", return_value=compound_registry),
        ):
            widget._active_tab = CATALOG_TAB_NODES
            widget.handle_item_double_clicked(texture)
            widget._show_rename_dialog.assert_not_called()

            widget._active_tab = CATALOG_TAB_TEXTURES
            widget.handle_item_double_clicked(texture)
            callback = widget._show_rename_dialog.call_args.args[2]
            dialog = SimpleNamespace(get_value=lambda: "  Renamed Texture  ", hide=MagicMock())
            callback(dialog)
            texture_registry.rename_texture.assert_called_once_with(texture, "Renamed Texture")

            widget.handle_item_double_clicked(texture_group)
            callback = widget._show_rename_dialog.call_args.args[2]
            dialog = SimpleNamespace(get_value=lambda: "   ", hide=MagicMock())
            callback(dialog)
            texture_registry.rename_group.assert_not_called()

            widget._active_tab = CATALOG_TAB_NODEGRAPHS
            widget.handle_item_double_clicked(compound)
            callback = widget._show_rename_dialog.call_args.args[2]
            dialog = SimpleNamespace(get_value=lambda: "Renamed Graph", hide=MagicMock())
            callback(dialog)
            compound_registry.rename_compound.assert_called_once_with(compound, "Renamed Graph")

            widget.handle_item_double_clicked(compound_group)
            callback = widget._show_rename_dialog.call_args.args[2]
            dialog = SimpleNamespace(get_value=lambda: "Renamed Group", hide=MagicMock())
            callback(dialog)
            compound_registry.rename_group.assert_called_once_with("Graphs", "Renamed Group")

    async def test_overlay_background_hover_selection_and_destroy(self) -> None:
        widget = MaterialGraphCatalog.__new__(MaterialGraphCatalog)
        widget._drop_overlay_controller = MagicMock()
        widget._scroll_frame = SimpleNamespace(
            style={"TreeView.ScrollingFrame": {"other": 1}, "TreeView": {"other": 2}}
        )
        widget._catalog_filler = SimpleNamespace(style={})
        widget._wire_catalog_bg_overlay()
        set_background = widget._drop_overlay_controller.set_background_fn.call_args.args[0]
        set_background(0x12345678)
        self.assertEqual(
            widget._scroll_frame.style["TreeView.ScrollingFrame"]["background_color"],
            0x12345678,
        )
        self.assertEqual(widget._catalog_filler.style["background_color"], 0x12345678)
        set_background(None)
        self.assertEqual(widget._catalog_filler.style["background_color"], widget._PANEL_BG)

        widget._on_hovered(True)
        widget._drop_overlay_controller.hide.assert_not_called()
        widget._on_hovered(False)
        widget._drop_overlay_controller.hide.assert_called_once_with()
        self.assertIs(widget.drop_overlay_controller, widget._drop_overlay_controller)

        widget._last_clicked_group = None
        group = GroupItem("Group")
        widget._update_last_clicked_group([])
        widget._update_last_clicked_group([object()])
        self.assertIsNone(widget._last_clicked_group)
        widget._update_last_clicked_group([group])
        self.assertIs(widget._last_clicked_group, group)

        lifecycle = MagicMock()
        overlay = widget._drop_overlay_controller
        widget._lifecycle = lifecycle
        widget._item_context_menu = object()
        widget.destroy()
        lifecycle.cleanup.assert_called_once_with()
        overlay.destroy.assert_called_once_with()
        self.assertIsNone(widget._lifecycle)
        self.assertIsNone(widget._drop_overlay_controller)
