# pylint: disable=relative-beyond-top-level,protected-access,no-member
import importlib
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Iterator, Tuple
from unittest.mock import MagicMock, patch

import omni.ext
import omni.kit.app
import omni.ui
from pxr import UsdGeom, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.extension import GraphExtension
from ..ui_base import MaterialGraphUiTestBase


class TestExtensionStartup(MaterialGraphUiTestBase):
    """Startup-level extension behavior."""

    @staticmethod
    @contextmanager
    def _isolated_extension_state(extension_module) -> Iterator[None]:
        """Snapshot and restore extension module globals for test isolation."""
        snapshot: Tuple[object, bool, bool, dict] = (
            extension_module.extension,
            extension_module._extension_shutdown,
            extension_module._extension_started,
            dict(extension_module._extension_registry),
        )
        try:
            yield
        finally:
            extension_module.extension = snapshot[0]
            extension_module._extension_shutdown = snapshot[1]
            extension_module._extension_started = snapshot[2]
            extension_module._extension_registry.clear()
            extension_module._extension_registry.update(snapshot[3])

    async def test_window_starts_hidden(self) -> None:
        """Window should start hidden before being shown."""
        if self._initial_window_handle is not None:
            self.assertIsNotNone(self._initial_window_visible)
            self.assertFalse(self._initial_window_visible)
        else:
            self.assertIsNone(self._initial_window_visible)

    async def test_show_window_fn_registered(self) -> None:
        """Workspace show_window should toggle visibility by name."""
        await self.show_window(True)
        await self.wait_n_updates(10)
        self.assertTrue(self._window_handle.visible)
        await self.show_window(False)
        self.assertFalse(self._window_handle.visible)

    async def test_window_visibility_toggle(self) -> None:
        """Workspace show_window should not recreate the window."""
        window_id = id(self._window_handle)

        await self.show_window(False)
        window_handle = self.get_window_handle()
        self.assertEqual(window_id, id(window_handle))

        await self.show_window(True)
        window_handle = self.get_window_handle()
        self.assertEqual(window_id, id(window_handle))

    async def test_stage_context_menu_registered(self) -> None:
        """Stage context menu should be registered."""
        ext_instance = GraphExtension()
        ext_instance._stage_context_menu = None
        ext_instance._thumb_context_menu = None
        ext_instance._setup_stage_menu()
        self.assertIsNotNone(ext_instance._stage_context_menu)
        self.assertIsNotNone(ext_instance._thumb_context_menu)
        ext_instance._unregister_stage_menu()

    async def test_startup_registers_commands(self) -> None:
        """Startup should register material graph commands."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        class DummyExtManager:
            def subscribe_to_extension_enable(self, *_args, **_kwargs):
                return None

            def is_extension_enabled(self, _name: str) -> bool:
                return False

        class DummyApp:
            def get_extension_manager(self) -> DummyExtManager:
                return DummyExtManager()

        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            with (
                patch.object(omni.kit.app, "get_app_interface", autospec=True, return_value=DummyApp()),
                patch.object(omni.ext, "get_extension_name", autospec=True, return_value="Test Ext"),
                patch.object(extension_module.GraphExtension, "menu_startup", lambda *_args, **_kwargs: None),
                patch.object(omni.ui.Workspace, "set_show_window_fn"),
                patch.object(extension_module, "add_preferences_page", autospec=True, return_value=None),
                patch.object(extension_module, "setup_all_commands", autospec=True) as register_commands,
            ):
                ext_instance.on_startup("test.ext")

            register_commands.assert_called_once_with()

    async def test_stage_context_menu_idempotent(self) -> None:
        """Stage context menu registration should be idempotent."""
        ext_instance = GraphExtension()
        ext_instance._stage_context_menu = None
        ext_instance._thumb_context_menu = None
        ext_instance._setup_stage_menu()
        stage_menu = ext_instance._stage_context_menu
        thumb_menu = ext_instance._thumb_context_menu
        ext_instance._setup_stage_menu()
        self.assertIs(stage_menu, ext_instance._stage_context_menu)
        self.assertIs(thumb_menu, ext_instance._thumb_context_menu)
        ext_instance._unregister_stage_menu()

    async def test_registers_stage_menu_when_stage_enabled(self) -> None:
        """Startup should register stage menu if stage ext is enabled."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        class DummyExtManager:
            """Extension manager stub."""

            def subscribe_to_extension_enable(self, *_args, **_kwargs) -> None:
                """Ignore extension enable subscriptions."""
                return None

            def is_extension_enabled(self, _name: str) -> bool:
                """Always report the extension enabled."""
                return True

        class DummyApp:
            """App stub that returns the dummy manager."""

            def get_extension_manager(self) -> DummyExtManager:
                """Return the dummy extension manager."""
                return DummyExtManager()

        called = {"value": False}

        def _register(*_args, **_kwargs) -> None:
            """Mark the menu registration as called."""
            called["value"] = True

        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            with (
                patch.object(omni.kit.app, "get_app_interface", autospec=True, return_value=DummyApp()),
                patch.object(omni.ext, "get_extension_name", autospec=True, return_value="Test Ext"),
                patch.object(
                    extension_module.GraphExtension,
                    "_setup_stage_menu",
                    autospec=True,
                    side_effect=_register,
                ),
                patch.object(extension_module.GraphExtension, "menu_startup", lambda *_args, **_kwargs: None),
                patch.object(omni.ui.Workspace, "set_show_window_fn"),
                patch.object(extension_module, "add_preferences_page", autospec=True, return_value=None),
            ):
                ext_instance.on_startup("test.ext")

        self.assertTrue(called["value"])

    async def test_startup_subscribes_to_quicksearch_extension(self) -> None:
        """Startup should subscribe for quicksearch extension state changes."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        subscribed_extensions = []

        class DummyExtManager:
            """Extension manager stub that records subscriptions."""

            def subscribe_to_extension_enable(self, *_args, **kwargs):
                subscribed_extensions.append(kwargs.get("ext_name"))
                return None

            def is_extension_enabled(self, _name: str) -> bool:
                return False

        class DummyApp:
            """App stub that returns the dummy manager."""

            def get_extension_manager(self) -> DummyExtManager:
                return DummyExtManager()

        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            with (
                patch.object(omni.kit.app, "get_app_interface", autospec=True, return_value=DummyApp()),
                patch.object(omni.ext, "get_extension_name", autospec=True, return_value="Test Ext"),
                patch.object(extension_module.GraphExtension, "menu_startup", lambda *_args, **_kwargs: None),
                patch.object(omni.ui.Workspace, "set_show_window_fn"),
                patch.object(extension_module, "add_preferences_page", autospec=True, return_value=None),
            ):
                ext_instance.on_startup("test.ext")

        self.assertIn("omni.kit.window.quicksearch", subscribed_extensions)

    async def test_quicksearch_extension_change_routes_register_and_unregister(self) -> None:
        """Quicksearch enable/disable events should register and unregister model hooks."""
        ext_instance = GraphExtension()
        with (
            patch.object(ext_instance, "_register_quicksearch", autospec=True) as register_quicksearch,
            patch.object(ext_instance, "_unregister_quicksearch", autospec=True) as unregister_quicksearch,
        ):
            ext_instance._on_quicksearch_extension_changed(True, "quicksearch.ext")
            register_quicksearch.assert_called_once_with()
            unregister_quicksearch.assert_not_called()

            register_quicksearch.reset_mock()
            ext_instance._on_quicksearch_extension_changed(False, "quicksearch.ext")
            unregister_quicksearch.assert_called_once_with()

    async def test_startup_failure_after_window_create(self) -> None:
        """Startup should flag failure when later steps fail."""
        app = omni.kit.app.get_app()
        ext_manager = app.get_extension_manager()
        ext_id = ext_manager.get_extension_id_by_module(self.MODULE_ID)
        self.assertIsNotNone(ext_id)

        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            with (
                patch.object(extension_module, "add_preferences_page", autospec=True, side_effect=OSError("boom")),
                patch.object(extension_module.GraphExtension, "menu_startup", lambda *_args, **_kwargs: None),
                patch.object(extension_module.GraphExtension, "menu_shutdown", lambda *_args, **_kwargs: None),
                patch.object(omni.ui.Workspace, "set_show_window_fn"),
                patch.object(extension_module, "log_exception", autospec=True) as log_error,
                patch("omni.kit.actions.core.get_action_registry", return_value=MagicMock()),
                patch.object(extension_module, "clear_node_menu_items", autospec=True),
                patch.object(extension_module, "clear_background_menu_items", autospec=True),
                patch.object(extension_module, "destroy_catalog_registries", autospec=True),
                patch.object(extension_module, "cleanup_command_tasks", autospec=True),
                patch.object(extension_module, "teardown_all_commands", autospec=True),
            ):
                ext_instance.on_startup(ext_id)
            self.assertTrue(ext_instance._startup_failed)
            self.assertIsNone(extension_module.extension)
            self.assertIsNone(ext_instance._window)
            log_error.assert_called()

    async def test_menu_startup_failure_logs_error(self) -> None:
        """Menu registration failures should log and flag startup failure."""
        app = omni.kit.app.get_app()
        ext_manager = app.get_extension_manager()
        ext_id = ext_manager.get_extension_id_by_module(self.MODULE_ID)
        self.assertIsNotNone(ext_id)

        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            with (
                patch.object(
                    extension_module.GraphExtension,
                    "menu_startup",
                    autospec=True,
                    side_effect=KeyError("boom"),
                ),
                patch.object(omni.ui.Workspace, "set_show_window_fn"),
                patch.object(extension_module, "log_exception", autospec=True) as log_error,
                patch.object(extension_module.GraphExtension, "on_shutdown", autospec=True),
            ):
                ext_instance.on_startup(ext_id)
            self.assertTrue(ext_instance._startup_failed)
            log_error.assert_called()

    async def test_extension_lifecycle_stress_toggle(self) -> None:
        """Repeated startup/shutdown with window toggles should be safe."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        class DummyExtManager:
            """Extension manager stub."""

            def subscribe_to_extension_enable(self, *_args, **_kwargs) -> None:
                return None

            def is_extension_enabled(self, _name: str) -> bool:
                return True

        class DummyApp:
            """App stub that returns the dummy manager."""

            def get_extension_manager(self) -> DummyExtManager:
                return DummyExtManager()

        class DummyWindow:
            """Window stub for show/hide toggles."""

            def __init__(self, *_args, **_kwargs) -> None:
                self.visible = True

            def set_visibility_changed_listener(self, *_args, **_kwargs) -> None:
                return None

            def destroy(self) -> None:
                return None

        class DummyRegistry:
            """Action registry stub."""

            def deregister_all_actions_for_extension(self, _ext_id: str) -> None:
                return None

        with self._isolated_extension_state(extension_module):
            show_window_cb = {"fn": None}

            def _capture_show_window(_name, fn):
                show_window_cb["fn"] = fn

            with (
                patch.object(omni.kit.app, "get_app_interface", autospec=True, return_value=DummyApp()),
                patch.object(omni.ext, "get_extension_name", autospec=True, return_value="Test Ext"),
                patch.object(extension_module.GraphExtension, "_setup_stage_menu", autospec=True),
                patch.object(extension_module.GraphExtension, "_unregister_stage_menu", autospec=True),
                patch.object(extension_module.GraphExtension, "menu_startup", lambda *_args, **_kwargs: None),
                patch.object(extension_module.GraphExtension, "menu_shutdown", lambda *_args, **_kwargs: None),
                patch.object(extension_module.GraphExtension, "menu_refresh", lambda *_args, **_kwargs: None),
                patch.object(extension_module, "add_preferences_page", autospec=True, return_value=None),
                patch.object(extension_module, "remove_preferences_page", autospec=True),
                patch.object(extension_module, "cleanup_command_tasks", autospec=True),
                patch.object(omni.ui.Workspace, "set_show_window_fn", side_effect=_capture_show_window),
                patch("omni.kit.actions.core.get_action_registry", autospec=True, return_value=DummyRegistry()),
                patch.object(extension_module, "GraphWindow", DummyWindow),
            ):
                ext_instance = extension_module.GraphExtension()
                for _ in range(3):
                    ext_instance.on_startup("test.ext")
                    self.assertTrue(callable(show_window_cb["fn"]))
                    show_window_cb["fn"](True)
                    show_window_cb["fn"](False)
                    ext_instance.on_shutdown()

    async def test_window_created_on_demand(self) -> None:
        """Window should be created on first show call."""
        app = omni.kit.app.get_app()
        ext_manager = app.get_extension_manager()
        ext_id = ext_manager.get_extension_id_by_module(self.MODULE_ID)
        self.assertIsNotNone(ext_id)

        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        created = {"value": False}

        class DummyWindow:
            """Window stub for startup tests."""

            def __init__(self) -> None:
                created["value"] = True
                self.visible = False
                self.show_docked = MagicMock()

            def destroy(self) -> None:
                """No-op destroy."""
                return None

            def set_visibility_changed_listener(self, _listener) -> None:
                """No-op visibility listener registration."""
                return None

        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            ext_instance._menu_entry = None
            show_window_cb = {"fn": None}

            def _capture_show_window(_name, fn):
                show_window_cb["fn"] = fn

            with (
                patch.object(extension_module, "GraphWindow", autospec=True, return_value=DummyWindow()),
                patch.object(extension_module.GraphExtension, "menu_startup", lambda *_args, **_kwargs: None),
                patch.object(omni.ui.Workspace, "set_show_window_fn", side_effect=_capture_show_window),
                patch.object(extension_module, "add_preferences_page", autospec=True, return_value=None),
            ):
                ext_instance.on_startup(ext_id)
                self.assertIsNone(extension_module.get_graph_window())
                self.assertTrue(callable(show_window_cb["fn"]))
                show_window_cb["fn"](True)
            self.assertTrue(created["value"])

    async def test_show_window_sets_visibility_when_hidden(self) -> None:
        """show_window should set visibility for hidden windows."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        class DummyWindow:
            """Window stub with show_docked support."""

            def __init__(self) -> None:
                self.visible = False
                self.show_docked = MagicMock()

        ext_instance = extension_module.GraphExtension()
        ext_instance._menu_entry = None
        ext_instance._window = DummyWindow()
        ext_instance.menu_refresh = MagicMock()
        show_window_cb = {"fn": None}

        def _capture_show_window(_name, fn):
            show_window_cb["fn"] = fn

        with patch.object(omni.ui.Workspace, "set_show_window_fn", side_effect=_capture_show_window):
            ext_instance._setup_show_window_hook()
        self.assertTrue(callable(show_window_cb["fn"]))
        show_window_cb["fn"](True)

        self.assertTrue(ext_instance._window.visible)
        ext_instance.menu_refresh.assert_called_once()

    async def test_show_window_refreshes_menu_on_visibility_change(self) -> None:
        """Visibility changes should refresh the menu state."""
        ext_instance = GraphExtension()
        ext_instance._menu_entry = None
        ext_instance.menu_refresh = MagicMock()

        ext_instance._visibility_changed_fn(True)

        ext_instance.menu_refresh.assert_called_once()

    async def test_get_graph_window_before_startup(self) -> None:
        """get_graph_window should return None before startup."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        with self._isolated_extension_state(extension_module):
            extension_module.extension = None
            extension_module._extension_shutdown = True
            extension_module._extension_started = False
            self.assertIsNone(extension_module.get_graph_window())

    async def test_startup_logs_info(self) -> None:
        """Startup should emit info logs for begin/end."""
        app = omni.kit.app.get_app()
        ext_manager = app.get_extension_manager()
        ext_id = ext_manager.get_extension_id_by_module(self.MODULE_ID)
        self.assertIsNotNone(ext_id)

        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            with (
                patch.object(extension_module.GraphExtension, "menu_startup", lambda *_args, **_kwargs: None),
                patch.object(omni.ui.Workspace, "set_show_window_fn"),
                patch.object(extension_module, "add_preferences_page", autospec=True, return_value=None),
                patch.object(extension_module.logger, "info", autospec=True) as log_info,
            ):
                ext_instance.on_startup(ext_id)

            log_info.assert_any_call("startup begin")
            log_info.assert_any_call("startup end")

    async def test_catalog_reload_applies_after_window_created(self) -> None:
        """Catalog reload requests should apply after window creation."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        class DummyCatalog:
            """Catalog stub that records reload calls."""

            def __init__(self) -> None:
                self.reload = MagicMock()

        class DummyGraphWidget:
            """Graph widget stub with a catalog model."""

            def __init__(self) -> None:
                self.catalog_model = DummyCatalog()

        class DummyWindow:
            """Window stub with graph widget."""

            def __init__(self) -> None:
                self.visible = False
                self.graph_widget = DummyGraphWidget()
                self.show_docked = MagicMock()

            def set_visibility_changed_listener(self, _listener) -> None:
                """No-op visibility listener registration."""
                return None

        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            ext_instance._menu_entry = None
            show_window_cb = {"fn": None}

            def _capture_show_window(_name, fn):
                show_window_cb["fn"] = fn

            with (
                patch.object(extension_module.Settings, "add_mdl_catalog_module", autospec=True),
                patch.object(extension_module, "GraphWindow", autospec=True, return_value=DummyWindow()),
                patch.object(omni.ui.Workspace, "set_show_window_fn", side_effect=_capture_show_window),
            ):
                extension_module.extension = ext_instance
                extension_module._extension_shutdown = False
                extension_module.add_mdl_catalog_module("foo.mdl")
                self.assertTrue(ext_instance._catalog_reload_pending)
                ext_instance._setup_show_window_hook()
                self.assertTrue(callable(show_window_cb["fn"]))
                show_window_cb["fn"](True)
                self.assertTrue(ext_instance._catalog_reload_pending)
                ext_instance._reload_catalog()

            self.assertFalse(ext_instance._catalog_reload_pending)
            ext_instance._window.graph_widget.catalog_model.reload.assert_called_once()

    async def test_startup_then_shutdown_registers_and_unregisters_commands(self) -> None:
        """Lifecycle should pair command registration on startup with unregister on shutdown."""
        # Patch extension startup dependencies (neuraylib/app/workspace/menu/page)
        # so we can isolate command registration lifecycle behavior without
        # creating real UI windows or depending on external extension state.
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        class DummyExtManager:
            def subscribe_to_extension_enable(self, *_args, **_kwargs):
                return None

            def is_extension_enabled(self, _name: str) -> bool:
                return False

        class DummyApp:
            def get_extension_manager(self) -> DummyExtManager:
                return DummyExtManager()

        with self._isolated_extension_state(extension_module):
            ext_instance = extension_module.GraphExtension()
            with (
                patch.object(omni.kit.app, "get_app_interface", autospec=True, return_value=DummyApp()),
                patch.object(omni.ext, "get_extension_name", autospec=True, return_value="Test Ext"),
                patch.object(extension_module.GraphExtension, "menu_startup", lambda *_args, **_kwargs: None),
                patch.object(extension_module.GraphExtension, "menu_shutdown", lambda *_args, **_kwargs: None),
                patch.object(omni.ui.Workspace, "set_show_window_fn"),
                patch.object(extension_module, "add_preferences_page", autospec=True, return_value=None),
                patch.object(extension_module, "setup_all_commands", autospec=True) as register_commands,
                patch.object(extension_module, "teardown_all_commands", autospec=True) as unregister_commands,
                patch("omni.kit.actions.core.get_action_registry", return_value=MagicMock()),
            ):
                ext_instance.on_startup("test.ext")
                ext_instance.on_shutdown()
            register_commands.assert_called_once_with()
            unregister_commands.assert_called_once_with()

    async def test_reload_catalog_noop_without_catalog_model(self) -> None:
        """Reload should be safe when catalog_model is missing."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        class DummyGraphWidget:
            """Graph widget stub without a catalog model."""

            __slots__ = ()

        class DummyWindow:
            """Window stub that holds a graph widget."""

            def __init__(self) -> None:
                self.graph_widget = DummyGraphWidget()

        ext_instance = extension_module.GraphExtension()
        ext_instance._window = DummyWindow()
        ext_instance._reload_catalog()
        self.assertTrue(ext_instance._catalog_reload_pending)

    async def test_open_material_from_context(self) -> None:
        """Open material handler should resolve bound materials."""
        ext_instance = GraphExtension()
        ext_instance._menu_entry = None
        captured = {"prim": None}

        class DummyWindow:
            """Window stub for open_graph."""

            def open_graph(self, prim) -> None:
                """Capture the prim passed to open_graph."""
                captured["prim"] = prim

        ext_instance._window = DummyWindow()

        material = UsdShade.Material.Define(self._stage, "/Looks/MatCtx")
        await ext_instance._open_graph_async({"prim": material.GetPrim()})
        self.assertEqual(captured["prim"], material.GetPrim())

        mesh = UsdGeom.Xform.Define(self._stage, "/Looks/Geom")
        UsdShade.MaterialBindingAPI(mesh).Bind(material)
        captured["prim"] = None
        await ext_instance._open_graph_async({"prim": mesh.GetPrim()})
        self.assertEqual(captured["prim"], material.GetPrim())

    async def test_open_material_creates_window(self) -> None:
        """Open material should create a window if needed."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        ext_instance = extension_module.GraphExtension()
        ext_instance._menu_entry = None
        opened = {"prim": None}

        class DummyWindow:
            """Window stub for open material tests."""

            def __init__(self) -> None:
                self.visible = False
                self.show_docked = MagicMock()

            def set_visibility_changed_listener(self, _listener) -> None:
                """No-op visibility listener registration."""
                return None

            def open_graph(self, prim) -> None:
                """Capture the prim passed to open_graph."""
                opened["prim"] = prim

        with self._isolated_extension_state(extension_module):
            with patch.object(extension_module, "GraphWindow", autospec=True, return_value=DummyWindow()):
                material = UsdShade.Material.Define(self._stage, "/Looks/MatOpen")
                ext_instance._open_material_from_context({"prim": material.GetPrim()})
                await self.wait_n_updates(5)
            self.assertIsNotNone(opened["prim"])

    async def test_open_material_from_context_cleanup_failure_logs_and_recovers(self) -> None:
        """Cleanup failure in open-material flow should log and still schedule task."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        ext_instance = extension_module.GraphExtension()
        ext_instance._menu_entry = None

        class FailingLifecycle:
            def __init__(self) -> None:
                self.add_task = MagicMock()

            def cleanup(self) -> None:
                raise OSError("cleanup failed")

        ext_instance._open_graph_lifecycle = FailingLifecycle()

        with patch.object(extension_module, "log_exception", autospec=True) as warn:
            ext_instance._open_material_from_context({})

        warn.assert_called()
        self.assertIsNotNone(ext_instance._open_graph_lifecycle)

    async def test_public_api_lookup_drop_and_catalog_routes_are_headless(self) -> None:
        """Public API routing and drop coordinates work without constructing a real window."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        ext_instance = extension_module.GraphExtension()
        catalog = SimpleNamespace(reload=MagicMock())
        graph_widget = SimpleNamespace(catalog_model=catalog, on_drop=MagicMock())
        ext_instance._window = SimpleNamespace(graph_widget=graph_widget, focused=True)
        ext_instance._open_material_from_context = MagicMock()

        with self._isolated_extension_state(extension_module):
            extension_module.extension = ext_instance
            extension_module._extension_shutdown = False
            self.assertIs(extension_module.get_extension(), ext_instance)
            self.assertIs(extension_module.get_graph_window(), ext_instance._window)
            extension_module.show_materials(["material"])
            ext_instance._open_material_from_context.assert_called_once_with({"prim_list": ["material"]})

            with patch.object(extension_module.GraphExtension, "_cursor_anchor_position", return_value=(10.0, 20.0)):
                extension_module.GraphExtension.add_node("payload")
            dropped = graph_widget.on_drop.call_args.args[0]
            self.assertEqual((dropped.mime_data, dropped.x, dropped.y), ("payload", 10.0, 20.0))

            with (
                patch.object(extension_module.Settings, "add_mdl_catalog_module", autospec=True) as add_module,
                patch.object(extension_module.Settings, "remove_mdl_catalog_module", autospec=True) as remove_module,
            ):
                extension_module.add_mdl_catalog_module("add.mdl")
                extension_module.remove_mdl_catalog_module("remove.mdl")
            add_module.assert_called_once_with("add.mdl")
            remove_module.assert_called_once_with("remove.mdl")
            self.assertEqual(catalog.reload.call_count, 2)

    async def test_extension_lookup_and_open_payload_failure_boundaries(self) -> None:
        """Absent runtime services and empty context payloads are safe no-op boundaries."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        ext_instance = extension_module.GraphExtension()
        ext_instance._show_window = MagicMock()

        await ext_instance._open_graph_async({})
        await ext_instance._open_graph_async({"prim_list": []})
        self.assertEqual(ext_instance._show_window.call_count, 2)

        with self._isolated_extension_state(extension_module):
            extension_module.extension = None
            extension_module._extension_shutdown = False
            extension_module._extension_started = False
            with patch.object(omni.kit.app, "get_app", side_effect=RuntimeError("unavailable")):
                self.assertIsNone(extension_module.get_extension())
            extension_module.GraphExtension.add_node("ignored")
            extension_module.GraphExtension.show_materials([])

            live = extension_module.GraphExtension()
            extension_module._extension_registry["test.ext"] = live
            manager = SimpleNamespace(get_extension_id_by_module=lambda _module: "test.ext")
            app = SimpleNamespace(get_extension_manager=lambda: manager)
            with patch.object(omni.kit.app, "get_app", return_value=app):
                self.assertIs(extension_module.get_extension(), live)

    async def test_cursor_anchor_position_runtime_boundaries(self) -> None:
        """Cursor lookup returns screen pixels and contains missing runtime components."""
        import carb.input
        import omni.appwindow

        mouse = object()
        app_window = SimpleNamespace(get_mouse=lambda: mouse)
        input_interface = SimpleNamespace(get_mouse_coords_pixel=lambda actual: (12, 34) if actual is mouse else None)
        with (
            patch.object(omni.appwindow, "get_default_app_window", return_value=app_window),
            patch.object(carb.input, "acquire_input_interface", return_value=input_interface),
        ):
            self.assertEqual(GraphExtension._cursor_anchor_position(), (12.0, 34.0))

        with patch.object(omni.appwindow, "get_default_app_window", return_value=None):
            self.assertEqual(GraphExtension._cursor_anchor_position(), (None, None))
        with patch.object(
            omni.appwindow,
            "get_default_app_window",
            return_value=SimpleNamespace(get_mouse=lambda: None),
        ):
            self.assertEqual(GraphExtension._cursor_anchor_position(), (None, None))
        with (
            patch.object(omni.appwindow, "get_default_app_window", return_value=app_window),
            patch.object(carb.input, "acquire_input_interface", return_value=None),
        ):
            self.assertEqual(GraphExtension._cursor_anchor_position(), (None, None))
        with (
            patch.object(omni.appwindow, "get_default_app_window", return_value=app_window),
            patch.object(
                carb.input,
                "acquire_input_interface",
                return_value=SimpleNamespace(get_mouse_coords_pixel=MagicMock(side_effect=RuntimeError("injected"))),
            ),
        ):
            self.assertEqual(GraphExtension._cursor_anchor_position(), (None, None))
