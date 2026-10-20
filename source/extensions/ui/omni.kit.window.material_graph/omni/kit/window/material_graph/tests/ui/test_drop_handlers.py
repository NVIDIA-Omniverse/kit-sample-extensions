# pylint: disable=relative-beyond-top-level,no-member,protected-access
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.ui.controllers.drop.catalog import CatalogCreationHandler
from ...scripts.ui.controllers.drop.paths import PathDropHandler
from ...scripts.ui.controllers.drop.textures import TextureDropHandler
from ..base import MaterialGraphTestBase
from ..fixtures.context_stubs import DropHandlerContextManager
from ..fixtures.widget_stubs import DropHandlerWidget


class TestDropHandlers(MaterialGraphTestBase):
    """PathDropHandler, TextureDropHandler, and CatalogCreationHandler handle drag-drop of paths,
    texture URLs, and catalog items onto the graph. They must accept valid inputs and load or
    delegate correctly, and reject or handle invalid inputs without crashing or opening the wrong
    graph. We test can_accept/handle_drop for materials, invalid paths, texture edge cases, and
    catalog mime data forwarding."""

    async def test_path_drop_handler_material(self) -> None:
        """Material paths accepted and load."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/Material"))
        widget = DropHandlerWidget(prim=None)
        handler = PathDropHandler(widget, self._usd_context)
        self.assertTrue(handler.can_accept(str(material.GetPath())))
        self.assertTrue(handler.handle_drop(str(material.GetPath())))
        widget.edit_graph.assert_called()

    async def test_path_drop_handler_rejects_invalid(self) -> None:
        """Invalid paths rejected."""
        widget = DropHandlerWidget()
        handler = PathDropHandler(widget, self._usd_context)
        self.assertFalse(handler.can_accept("not-a-path"))
        self.assertFalse(handler.handle_drop("not-a-path"))

    async def test_texture_drop_handler_invalid(self) -> None:
        """Invalid texture info handled safely."""
        # Patch get_texture_info to return (False, None) so we don't need real texture resolution.
        widget = DropHandlerWidget()
        handler = TextureDropHandler(widget, DropHandlerContextManager())
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.get_texture_info",
            return_value=(False, None),
        ):
            self.assertTrue(handler.handle_drop("file.png", MagicMock(x=0, y=0)))
        widget.edit_graph.assert_not_called()
        widget.show_error.assert_not_called()

    async def test_texture_drop_handler_acceptance_uses_texture_validation(self) -> None:
        """Texture acceptance rejects unresolved/invalid paths and accepts validated textures."""
        handler = TextureDropHandler(DropHandlerWidget(), DropHandlerContextManager())
        texture_info = f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.get_texture_info"
        with patch(texture_info, side_effect=[None, (False, 4), (True, 4)]):
            self.assertFalse(handler.can_accept("missing.png"))
            self.assertFalse(handler.can_accept("invalid.png"))
            self.assertTrue(handler.can_accept("valid.png"))

    async def test_texture_drop_handler_missing_plugin(self) -> None:
        """Missing plugins logged and consumed."""
        # Patch get_texture_info to return valid info; handler should still not call edit_graph when plugin is missing.
        widget = DropHandlerWidget()
        handler = TextureDropHandler(widget, DropHandlerContextManager(plugin=None))
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.get_texture_info",
            return_value=(True, 3),
        ):
            self.assertTrue(handler.handle_drop("file.png", MagicMock(x=0, y=0)))
        widget.edit_graph.assert_not_called()

    async def test_texture_drop_handler_rejects_plugins_without_creation_choices(self) -> None:
        """A plugin without a callable creator or without choices is safely consumed and reported."""
        widget = DropHandlerWidget()
        event = MagicMock(x=0, y=0)
        texture_info = f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.get_texture_info"
        with patch(texture_info, return_value=(True, 3)):
            plugin = SimpleNamespace(create_texture=None)
            handler = TextureDropHandler(widget, DropHandlerContextManager(plugin=plugin))
            self.assertTrue(handler.handle_drop("file.png", event))

            plugin = MagicMock()
            plugin.create_texture.return_value = []
            handler = TextureDropHandler(widget, DropHandlerContextManager(plugin=plugin))
            self.assertTrue(handler.handle_drop("file.png", event))

        widget.clear_error.assert_not_called()

    async def test_texture_drop_handler_multichoice_falls_back_without_running_loop(self) -> None:
        """Texture drop shows chooser menu immediately when no asyncio loop is running."""
        plugin = MagicMock()
        shader_a = SimpleNamespace(name="Texture A", identifier="id.a", extra_mime_data={})
        shader_b = SimpleNamespace(name="Texture B", identifier="id.b", extra_mime_data={})
        plugin.create_texture.return_value = [(shader_a, "file"), (shader_b, "file")]
        widget = DropHandlerWidget()
        handler = TextureDropHandler(widget, DropHandlerContextManager(plugin=plugin))

        class DummyMenu:
            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.get_texture_info",
                return_value=(True, 3),
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.asyncio.get_running_loop",
                side_effect=RuntimeError("no running event loop"),
            ),
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.omni.ui.Menu", return_value=DummyMenu()),
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.omni.ui.MenuItem"),
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.show_menu_at_cursor") as show_menu,
        ):
            self.assertTrue(handler.handle_drop("file.png", MagicMock(x=10, y=20)))

        show_menu.assert_called_once()

    async def test_texture_drop_handler_rejects_malformed_shader_metadata(self) -> None:
        """Malformed catalog metadata should surface a widget error instead of escaping the callback."""
        plugin = MagicMock()
        shader = SimpleNamespace(name="Texture", identifier="id.texture", extra_mime_data=object())
        plugin.create_texture.return_value = [(shader, "file")]
        context_manager = DropHandlerContextManager(plugin=plugin)
        context_manager.get_node = MagicMock(return_value=MagicMock())
        widget = DropHandlerWidget()
        widget.graph_view.screen_to_canvas.return_value = (0.0, 0.0)
        widget.isolation_model = SimpleNamespace(root=SimpleNamespace(prim_path=Sdf.Path("/Material"), prim=None))
        handler = TextureDropHandler(widget, context_manager)

        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.get_texture_info",
            return_value=(True, 3),
        ):
            self.assertTrue(handler.handle_drop("file.png", MagicMock(x=0, y=0)))

        widget.show_error.assert_called_once_with(
            "texture shader definition has invalid creation metadata", log_message=False
        )
        widget.clear_error.assert_not_called()

    async def test_texture_drop_handler_choice_validation_and_command_result(self) -> None:
        """Texture choices validate definitions/models and report command failures without false success."""
        plugin = MagicMock()
        plugin.get_shader_source_type.return_value = "mdl"
        context_manager = DropHandlerContextManager(plugin=plugin)
        context_manager.get_node = MagicMock(return_value=None)
        widget = DropHandlerWidget()
        event = MagicMock(x=3, y=4)
        handler = TextureDropHandler(widget, context_manager)

        missing_identifier = SimpleNamespace(identifier="", extra_mime_data={})
        handler._create_choice_callback(plugin, event)((missing_identifier, "file"), "file.png")
        widget.show_error.assert_called_with("texture shader definition is missing an identifier", log_message=False)

        shader = SimpleNamespace(identifier="id.texture", extra_mime_data={})
        widget.isolation_model = None
        handler._create_choice_callback(plugin, event)((shader, "file"), "file.png")
        widget.show_error.assert_called_with(
            "texture drop ignored: no material graph is loaded; open or create a material and try again"
        )

        widget.isolation_model = SimpleNamespace(root=SimpleNamespace(prim_path=Sdf.Path("/Material"), prim=None))
        handler._create_choice_callback(plugin, event)((shader, "file"), "file.png")
        widget.show_error.assert_called_with("texture shader definition not found (id.texture)", log_message=False)

        context_manager.get_node.return_value = MagicMock()
        widget.graph_view.screen_to_canvas.return_value = (5.0, 6.0)
        failure = SimpleNamespace(success=False, payload=None, message="injected failure")
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.CreateShader", return_value=failure
        ) as create_shader:
            handler._create_choice_callback(plugin, event)((shader, "file"), "file.png")
        widget.show_error.assert_called_with(
            "texture shader 'id.texture' could not be created: injected failure",
            log_message=False,
        )
        _, kwargs = create_shader.call_args
        self.assertEqual(kwargs["context"], "mdl")
        self.assertIsNone(kwargs["stage"])
        self.assertEqual(kwargs["input_values"]["file"][1], Sdf.AssetPath("file.png"))

        create_shader.return_value = SimpleNamespace(success=True, payload=object(), message=None)
        with patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures.CreateShader", create_shader):
            handler._create_choice_callback(plugin, event)((shader, "file"), "file.png")
        widget.clear_error.assert_called_once()

    async def test_texture_choice_menu_replacement_and_destroy_release_ui(self) -> None:
        """Repeated drops replace the menu, cancel stale work, and hide UI during teardown."""

        class DummyMenu:
            def __init__(self):
                self.hide = MagicMock()

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

        class DummyTask:
            def __init__(self):
                self.cancel = MagicMock()

            @staticmethod
            def done():
                return False

        menus = [DummyMenu(), DummyMenu()]
        first_task = DummyTask()
        second_task = DummyTask()
        scheduled_tasks = [first_task, second_task]

        def _schedule(coroutine, _description):
            coroutine.close()
            return scheduled_tasks.pop(0)

        handler = TextureDropHandler(DropHandlerWidget(), DropHandlerContextManager())
        choice = (SimpleNamespace(name="Texture", identifier="id.texture"), "file")
        module = f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.textures"
        with (
            patch(f"{module}.omni.ui.Menu", side_effect=menus),
            patch(f"{module}.omni.ui.MenuItem"),
            patch(f"{module}.asyncio.get_running_loop", return_value=object()),
            patch(f"{module}.ensure_future_logged", side_effect=_schedule),
        ):
            handler._show_choices_menu([choice], MagicMock(), "a.png", MagicMock(x=1, y=2))
            handler._show_choices_menu([choice], MagicMock(), "b.png", MagicMock(x=3, y=4))

        menus[0].hide.assert_called_once()
        first_task.cancel.assert_called_once()
        self.assertIs(handler._menu_task, second_task)
        handler.destroy()
        menus[1].hide.assert_called_once()
        second_task.cancel.assert_called_once()

    async def test_catalog_creation_handler(self) -> None:
        """Catalog creation invokes drop handler with mime data."""
        widget = DropHandlerWidget()
        widget.graph_view.model = True
        catalog_model = MagicMock(get_drag_mime_data=MagicMock(return_value="data"))
        drop_fn = MagicMock()
        handler = CatalogCreationHandler(widget, catalog_model, drop_fn)
        handler.create_from_catalog(MagicMock(name="Item"), mouse_position=(1, 2))
        drop_event = drop_fn.call_args[0][0]
        self.assertEqual(drop_event.mime_data, "data")
        self.assertEqual(drop_event.x, 1)
        self.assertEqual(drop_event.y, 2)

    async def test_catalog_creation_handler_variant_menu_selects_payload(self) -> None:
        """Catalog creation should show variant menu and emit chosen variant payload."""
        widget = DropHandlerWidget()
        widget.graph_view.model = True
        payload = {
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
        }
        catalog_model = MagicMock(get_drag_mime_data=MagicMock(return_value=json.dumps(payload)))
        drop_fn = MagicMock()
        handler = CatalogCreationHandler(widget, catalog_model, drop_fn)

        callbacks = {}

        class DummyMenu:
            """Menu stub for capturing menu item callbacks."""

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

        def _menu_item(label, triggered_fn=None):
            callbacks[label] = triggered_fn

        with (
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.catalog.omni.ui.Menu", return_value=DummyMenu()),
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.catalog.omni.ui.MenuItem", side_effect=_menu_item),
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.drop.catalog.show_menu_at_cursor"),
        ):
            handler.create_from_catalog(MagicMock(name="Clamp"), mouse_position=(3, 4))

        self.assertFalse(drop_fn.called)
        self.assertIn("clamp(float2,float2,float) -> float2", callbacks)
        callbacks["clamp(float2,float2,float) -> float2"]()
        drop_event = drop_fn.call_args[0][0]
        selected_payload = json.loads(drop_event.mime_data)
        self.assertEqual(selected_payload["subidentifier"], "clamp(float2,float2,float)")
        self.assertEqual(selected_payload["identifier"], "clamp(float2,float2,float)")
