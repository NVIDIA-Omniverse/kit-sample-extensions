import json
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

from omni.kit.widget.graph import IsolationGraphModel
from pxr import UsdShade, UsdUI

from ...scripts.config.paths import Paths
from ...scripts.ui.controllers.drop.payloads import PayloadDropHandler
from ..base import MaterialGraphTestBase
from ..fixtures.widget_stubs import DummyWidget

# pylint: disable=relative-beyond-top-level


class TestPayloadDropHandler(MaterialGraphTestBase):
    """PayloadDropHandler is the drag-drop handler for catalog items onto the graph: it parses JSON
    payloads (shader, backdrop, ImportNodeGraph, etc.), checks context and required fields, and
    delegates to the right creation path. We test it because bad or mismatched payloads must be
    rejected or surface an error instead of corrupting the graph, and compound imports must use
    the user-chosen name for the new prim."""

    async def test_invalid_payload_rejected(self) -> None:
        """Invalid payloads rejected and logged."""
        # Patch logger.warning to assert the warning and avoid log output.
        widget = DummyWidget(current_context="mdl")
        handler = PayloadDropHandler(widget, None, None, None)
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.logger.warning",
            autospec=True,
        ) as log_warn:
            self.assertFalse(handler.can_accept("not-json"))
            log_warn.assert_called()

    async def test_missing_type_rejected(self) -> None:
        """Missing type rejected and logged."""
        # Patch logger.warning to assert the warning and avoid log output.
        widget = DummyWidget(current_context="mdl")
        handler = PayloadDropHandler(widget, None, None, None)
        payload = json.dumps({"identifier": "foo"})
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.logger.warning",
            autospec=True,
        ) as log_warn:
            self.assertFalse(handler.can_accept(payload))
            log_warn.assert_called()

    async def test_can_accept_context_mismatch(self) -> None:
        """Shader payloads with mismatched context should be rejected."""
        widget = DummyWidget(current_context="mdl")
        handler = PayloadDropHandler(widget, None, None, None)
        payload = json.dumps({"type": "Shader", "context": "other"})
        self.assertFalse(handler.can_accept(payload))

    async def test_can_accept_supported_graph_and_texture_payloads(self) -> None:
        """Acceptance covers graph primitives, isolation nodes, and only validated texture payloads."""
        widget = DummyWidget(current_context="mdl")
        texture_drop = MagicMock()
        handler = PayloadDropHandler(widget, None, None, None, texture_drop_fn=texture_drop)
        for item_type in (
            UsdUI.Tokens.Backdrop,
            UsdShade.Tokens.NodeGraph,
            IsolationGraphModel.InputNode.get_type_name(),
            IsolationGraphModel.OutputNode.get_type_name(),
            "ImportNodeGraph",
        ):
            self.assertTrue(handler.can_accept(json.dumps({"type": item_type})))

        module = f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.get_texture_info"
        with patch(module, return_value=(True, 4)):
            self.assertTrue(handler.can_accept(json.dumps({"type": "Texture", "source": "valid.png"})))
            self.assertFalse(handler.can_accept(json.dumps({"type": "Texture"})))

        widget.graph_view.model = None
        self.assertFalse(handler.can_accept(json.dumps({"type": UsdUI.Tokens.Backdrop})))

    async def test_missing_identifier_shows_error(self) -> None:
        """Missing identifier shows error and warns."""
        # Patch logger.warning to assert the warning and avoid log output.
        widget = DummyWidget(current_context="mdl")
        handler = PayloadDropHandler(widget, None, None, None)
        payload = json.dumps({"type": "Shader", "context": widget.current_context})
        event = SimpleNamespace(x=10, y=10)
        widget.show_error = MagicMock()
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.logger.warning",
            autospec=True,
        ) as log_warn:
            self.assertTrue(handler.handle_drop(payload, event))
            log_warn.assert_called()
            widget.show_error.assert_called()

    async def test_context_mismatch_shows_error(self) -> None:
        """Context mismatch shows error and warns."""
        # Patch logger.warning to assert the warning and avoid log output.
        widget = DummyWidget(current_context="mdl")
        handler = PayloadDropHandler(widget, None, None, None)
        payload = json.dumps({"type": "Shader", "identifier": "foo", "context": "other"})
        event = SimpleNamespace(x=10, y=10)
        widget.show_error = MagicMock()
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.logger.warning",
            autospec=True,
        ) as log_warn:
            self.assertTrue(handler.handle_drop(payload, event))
            log_warn.assert_called()
            widget.show_error.assert_called()

    async def test_import_compound_uses_item_name(self) -> None:
        """ImportNodeGraph uses item name for prim creation."""
        # Patch CreateNode to avoid USD/command side effects and to capture prim_name argument.
        widget = DummyWidget(current_context="mdl")
        handler = PayloadDropHandler(widget, None, None, None)
        payload = json.dumps(
            {
                "type": "ImportNodeGraph",
                "source_asset": "compound.usda",
                "identifier": "/CompoundGraph",
                "name": "MyCompound",
            }
        )
        event = SimpleNamespace(x=10, y=10)
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.CreateNode",
            autospec=True,
        ) as create_node:
            handler.handle_drop(payload, event)
            _, kwargs = create_node.call_args
            self.assertEqual(kwargs.get("prim_name"), "MyCompound")

    async def test_shader_drop_with_variants_shows_menu_and_uses_selection(self) -> None:
        """Shader drops requiring variant selection should create selected variant only."""
        widget = DummyWidget(current_context="mdl")
        context_manager = MagicMock()
        context_manager.get_node.return_value = MagicMock()
        create_shader = MagicMock()
        handler = PayloadDropHandler(widget, context_manager, None, None, create_shader=create_shader)
        payload = json.dumps(
            {
                "type": "Shader",
                "origin": "catalog",
                "identifier": "clamp(float2,float2,float2)",
                "context": "mdl",
                "subidentifier": "clamp(float2,float2,float2)",
                "variant_subidentifiers": ["clamp(float2,float2,float2)", "clamp(float2,float2,float)"],
                "variant_identifiers": {
                    "clamp(float2,float2,float2)": "clamp(float2,float2,float2)",
                    "clamp(float2,float2,float)": "clamp(float2,float2,float)",
                },
                "variant_output_types": {
                    "clamp(float2,float2,float2)": "-> float2",
                    "clamp(float2,float2,float)": "-> float2",
                },
                "requires_variant_selection": True,
            }
        )
        event = SimpleNamespace(x=10, y=20)
        callbacks = {}

        class DummyMenu:
            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

        def _menu_item(label, triggered_fn=None):
            callbacks[label] = triggered_fn

        with (
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.omni.ui.Menu", return_value=DummyMenu()),
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.omni.ui.MenuItem", side_effect=_menu_item),
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.show_menu_at_cursor"),
        ):
            self.assertTrue(handler.handle_drop(payload, event))

        create_shader.assert_not_called()
        callbacks["clamp(float2,float2,float) -> float2"]()
        _, kwargs = create_shader.call_args
        self.assertEqual(kwargs.get("subidentifier"), "clamp(float2,float2,float)")
        self.assertEqual(kwargs.get("identifier"), "clamp(float2,float2,float)")
        self.assertFalse(kwargs.get("requires_variant_selection"))

    async def test_shader_variant_menu_replacement_and_destroy_hide_ui(self) -> None:
        """Repeated variant drops replace stale menus, and destruction hides the live menu."""

        class DummyMenu:
            def __init__(self):
                self.hide = MagicMock()

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

        widget = DummyWidget(current_context="mdl")
        handler = PayloadDropHandler(widget, MagicMock(), None, None)
        payload = {
            "type": "Shader",
            "identifier": "id.a",
            "context": "mdl",
            "variant_subidentifiers": ["a", "b"],
        }
        menus = [DummyMenu(), DummyMenu()]
        module = f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads"
        with (
            patch(f"{module}.omni.ui.Menu", side_effect=menus),
            patch(f"{module}.omni.ui.MenuItem"),
            patch(f"{module}.show_menu_at_cursor"),
        ):
            handler._show_shader_variant_menu(payload, widget.isolation_model.root, MagicMock(), MagicMock(x=1, y=2))
            handler._show_shader_variant_menu(payload, widget.isolation_model.root, MagicMock(), MagicMock(x=3, y=4))

        menus[0].hide.assert_called_once()
        handler.destroy()
        menus[1].hide.assert_called_once()

    async def test_shader_drop_syncs_graph_selection_to_created_prim(self) -> None:
        """Successful shader drop replaces graph selection with created node."""
        selected_item = object()
        selection_holder = []

        class DummyModel:
            prim_path = "/World/Looks/material"

            @property
            def selection(self):
                return selection_holder

            @selection.setter
            def selection(self, value):
                selection_holder.clear()
                selection_holder.extend(value or [])

            @staticmethod
            def get_item_model(_path):
                return selected_item

        created_path = "/World/Looks/material/newShader"
        created_prim = SimpleNamespace(GetPath=lambda: created_path)
        create_shader = MagicMock(return_value=SimpleNamespace(success=True, payload=created_prim))
        context_manager = MagicMock()
        context_manager.get_node.return_value = MagicMock()

        widget = DummyWidget(
            current_context="mdl",
            isolation_model=SimpleNamespace(root=DummyModel()),
        )
        handler = PayloadDropHandler(widget, context_manager, None, None, create_shader=create_shader)
        payload = json.dumps({"type": "Shader", "identifier": "foo", "context": "mdl"})
        event = SimpleNamespace(x=1, y=2)

        self.assertTrue(handler.handle_drop(payload, event))
        self.assertEqual(selection_holder, [selected_item])

    async def test_missing_shader_definition_shows_error_and_keeps_existing_graph(self) -> None:
        """An unresolved payload must not blank the graph or silently clear its error state."""
        widget = DummyWidget(current_context="mdl")
        existing_root = widget.isolation_model.root
        context_manager = MagicMock()
        context_manager.get_node.return_value = None
        create_shader = MagicMock()
        handler = PayloadDropHandler(widget, context_manager, None, None, create_shader=create_shader)
        payload = json.dumps({"type": "Shader", "identifier": "missing_shader", "context": "mdl"})

        with patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.logger.warning"):
            self.assertTrue(handler.handle_drop(payload, SimpleNamespace(x=1, y=2)))

        create_shader.assert_not_called()
        self.assertIs(widget.isolation_model.root, existing_root)
        widget.show_error.assert_called_once()
        self.assertIn("missing_shader", widget.show_error.call_args.args[0])
        widget.clear_error.assert_not_called()

    async def test_failed_creation_paths_show_error_without_false_success(self) -> None:
        """All command-backed payload types surface failures through the widget error framework."""
        failure = SimpleNamespace(success=False, payload=None, message="injected failure")
        graph_settings = MagicMock()
        graph_settings.get_backdrop_drop_settings.return_value = (None, None)
        graph_settings.get_nodegraph_drop_settings.return_value = (None, None)
        widget = DummyWidget(current_context="mdl")
        handler = PayloadDropHandler(
            widget,
            MagicMock(),
            graph_settings,
            MagicMock(),
            create_backdrop=MagicMock(return_value=failure),
            create_nodegraph=MagicMock(return_value=failure),
            create_node=MagicMock(return_value=failure),
        )
        event = SimpleNamespace(x=1, y=2)
        payloads = [
            {"type": "Backdrop"},
            {"type": "NodeGraph"},
            {
                "type": "ImportNodeGraph",
                "source_asset": "compound.usda",
                "identifier": "/Compound",
            },
        ]

        with patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.logger.warning"):
            for payload_data in payloads:
                widget.show_error.reset_mock()
                self.assertTrue(handler.handle_drop(json.dumps(payload_data), event))
                widget.show_error.assert_called_once()
                self.assertIn("injected failure", widget.show_error.call_args.args[0])

        widget.clear_error.assert_not_called()

    async def test_texture_and_isolation_drop_routes(self) -> None:
        """Texture and isolation payloads route to their semantic handlers without UI coordinates."""
        texture_drop = MagicMock()
        isolation = MagicMock()
        isolation.root = widget_root = DummyWidget().isolation_model.root
        widget = DummyWidget(current_context="mdl", isolation_model=isolation)
        handler = PayloadDropHandler(widget, None, None, None, texture_drop_fn=texture_drop)
        event = SimpleNamespace(x=None, y=None)

        self.assertTrue(handler.handle_drop(json.dumps({"type": "Texture", "source": "a.png"}), event))
        texture_drop.assert_called_once_with("a.png", event)

        for node_type, is_input in (
            (IsolationGraphModel.InputNode.get_type_name(), True),
            (IsolationGraphModel.OutputNode.get_type_name(), False),
        ):
            self.assertTrue(handler.handle_drop(json.dumps({"type": node_type}), SimpleNamespace(x=1, y=2)))
            isolation.add_input_or_output.assert_called_with(ANY, is_input)
        self.assertIs(isolation.root, widget_root)

    async def test_backdrop_and_nodegraph_drop_route_settings_and_created_selection(self) -> None:
        """Graph-primitive payloads preserve configured metadata and finish through the common path."""
        widget = DummyWidget(current_context="mdl")
        settings = MagicMock()
        settings.get_backdrop_drop_settings.return_value = ("pos:mdl", ["mdl"])
        settings.get_nodegraph_drop_settings.return_value = ("pos:mdl", ["mdl"])
        created_prim = MagicMock()
        created_prim.GetPath.return_value = "/World/Looks/Material/Created"
        result = SimpleNamespace(success=True, payload=created_prim)
        create_backdrop = MagicMock(return_value=result)
        create_nodegraph = MagicMock(return_value=result)
        handler = PayloadDropHandler(
            widget,
            None,
            settings,
            None,
            create_backdrop=create_backdrop,
            create_nodegraph=create_nodegraph,
        )

        for item_type in (UsdUI.Tokens.Backdrop, UsdShade.Tokens.NodeGraph):
            self.assertTrue(handler.handle_drop(json.dumps({"type": item_type}), SimpleNamespace(x=3, y=4)))

        create_backdrop.assert_called_once_with(
            widget.isolation_model.root.prim_path,
            ANY,
            "pos:mdl",
            ["mdl"],
            stage=None,
        )
        create_nodegraph.assert_called_once_with(
            widget.isolation_model.root.prim_path,
            ANY,
            "pos:mdl",
            ["mdl"],
            stage=None,
        )
        self.assertEqual(widget.clear_error.call_count, 2)

    async def test_missing_texture_and_compound_data_report_errors(self) -> None:
        """Incomplete texture/compound drops are consumed with visible errors and no creation."""
        widget = DummyWidget(current_context="mdl")
        create_node = MagicMock()
        handler = PayloadDropHandler(widget, None, None, None, create_node=create_node, texture_drop_fn=MagicMock())
        with patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.payloads.logger.warning"):
            self.assertTrue(handler.handle_drop(json.dumps({"type": "Texture"}), SimpleNamespace(x=1, y=2)))
            widget.show_error.assert_called_with("drop ignored: missing texture source", log_message=False)
            self.assertTrue(
                handler.handle_drop(
                    json.dumps({"type": "ImportNodeGraph", "identifier": "/Compound"}),
                    SimpleNamespace(x=1, y=2),
                )
            )
            widget.show_error.assert_called_with(
                "compound drop is missing source asset; refresh the catalog entry and try again",
                log_message=False,
            )
        create_node.assert_not_called()
