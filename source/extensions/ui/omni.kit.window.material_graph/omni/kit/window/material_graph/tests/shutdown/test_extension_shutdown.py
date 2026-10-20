# pylint: disable=relative-beyond-top-level,protected-access,no-member
import importlib
from unittest.mock import patch

import omni.ui

from ...scripts.config.paths import Paths
from ..ui_base import MaterialGraphUiTestBase


class TestExtensionShutdown(MaterialGraphUiTestBase):
    """Extension shutdown cleanup behavior."""

    async def setUp(self) -> None:
        """Isolate synthetic shutdown calls from the live test extension."""

        await super().setUp()
        self._extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        self._live_extension_state = (
            self._extension_module.extension,
            self._extension_module._extension_shutdown,
            self._extension_module._extension_started,
            dict(self._extension_module._extension_registry),
        )
        # Synthetic GraphExtension instances must not deregister the live
        # suite's actions, commands, menus, catalogs, or Workspace hook.
        noop = lambda *_args, **_kwargs: None
        dummy_action_registry = type(
            "DummyActionRegistry",
            (),
            {"deregister_all_actions_for_extension": noop},
        )()
        self._shutdown_patchers = [
            patch.object(omni.ui.Workspace, "set_show_window_fn", new=noop),
            patch.object(self._extension_module.GraphExtension, "menu_shutdown", new=noop),
            patch.object(self._extension_module, "clear_node_menu_items", new=noop),
            patch.object(self._extension_module, "clear_background_menu_items", new=noop),
            patch.object(self._extension_module, "destroy_catalog_registries", new=noop),
            patch.object(self._extension_module, "cleanup_command_tasks", new=noop),
            patch.object(self._extension_module, "teardown_all_commands", new=noop),
            patch.object(self._extension_module, "remove_preferences_page", new=noop),
            patch("omni.kit.actions.core.get_action_registry", new=lambda: dummy_action_registry),
        ]
        for patcher in self._shutdown_patchers:
            patcher.start()

    async def tearDown(self) -> None:
        """Restore the live extension singleton and registries after each test."""

        for patcher in reversed(self._shutdown_patchers):
            patcher.stop()
        live_extension, shutdown, started, registry = self._live_extension_state
        self._extension_module.extension = live_extension
        self._extension_module._extension_shutdown = shutdown
        self._extension_module._extension_started = started
        self._extension_module._extension_registry.clear()
        self._extension_module._extension_registry.update(registry)
        self._shutdown_patchers = []
        self._live_extension_state = None
        self._extension_module = None
        await super().tearDown()

    async def test_shutdown_clears_hooks(self) -> None:
        """Shutdown should call cleanup hooks and clear show window fn."""

        # We import the module (not just the class) so we can patch module-level
        # cleanup functions in tests. Aliasing the class would not expose those.
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        ext_instance = extension_module.GraphExtension()
        ext_instance._extension_subscription = None
        ext_instance._preference_page = "dummy"
        destroyed = {"value": False}

        class DummyWindow:
            """Window stub that records destruction."""

            def destroy(self) -> None:
                """Mark the window as destroyed."""
                destroyed["value"] = True

        ext_instance._window = DummyWindow()
        ext_instance._ext_name = extension_module.GraphExtension._WINDOW_NAME
        ext_instance.menu_shutdown = lambda: None

        class DummyMenu:
            """Menu stub that records release calls."""

            def __init__(self, flag: dict[str, bool]) -> None:
                """Initialize with a shared flag dict."""
                self._flag = flag

            def release(self) -> None:
                """Record release on the flag dict."""
                self._flag["released"] = True

        stage_flag = {"released": False}
        thumb_flag = {"released": False}
        ext_instance._stage_context_menu = DummyMenu(stage_flag)
        ext_instance._thumb_context_menu = DummyMenu(thumb_flag)

        # Preserve the real extension instance. on_shutdown() resets the module-level
        # "extension" global, which would unregister actions and break the actions API test.
        original_extension = extension_module.extension
        try:
            extension_module.extension = ext_instance
            with (
                patch.object(omni.ui.Workspace, "set_show_window_fn") as set_show_fn,
                patch.object(extension_module, "cleanup_command_tasks", autospec=True) as cleanup_cmds,
                patch.object(extension_module, "destroy_catalog_registries", autospec=True) as cleanup_catalogs,
                patch.object(extension_module, "remove_preferences_page", autospec=True) as unregister_page,
            ):
                ext_instance.on_shutdown()
                set_show_fn.assert_called_once_with(extension_module.GraphExtension._WINDOW_NAME, None)
                cleanup_cmds.assert_called_once()
                cleanup_catalogs.assert_called_once()
                unregister_page.assert_called_once_with("dummy")
        finally:
            extension_module.extension = original_extension

        self.assertTrue(stage_flag["released"])
        self.assertTrue(thumb_flag["released"])
        self.assertIsNone(ext_instance._stage_context_menu)
        self.assertIsNone(ext_instance._thumb_context_menu)
        self.assertIsNone(ext_instance._window)
        self.assertTrue(destroyed["value"])

    async def test_menu_shutdown_failure_logged(self) -> None:
        """menu_shutdown failures should be logged and not stop shutdown."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")

        ext_instance = extension_module.GraphExtension()
        ext_instance._extension_subscription = None
        ext_instance._preference_page = None
        ext_instance._window = None
        ext_instance._ext_name = extension_module.GraphExtension._WINDOW_NAME

        ext_instance.menu_shutdown = lambda: (_ for _ in ()).throw(OSError("boom"))

        class DummySettings:
            """Settings stub for menu shutdown test."""

            def get(self, _key: str) -> bool:
                """Always return False for queried keys."""
                return False

            def set(self, _key: str, _value: object) -> None:
                """Accept settings restored by UI test cleanup."""

        with (
            patch.object(omni.ui.Workspace, "set_show_window_fn"),
            patch.object(extension_module.carb.settings, "get_settings", return_value=DummySettings()),
            patch.object(extension_module, "log_exception", autospec=True) as log_warn,
        ):
            ext_instance.on_shutdown()

        log_warn.assert_called()

    async def test_shutdown_idempotent(self) -> None:
        """Shutdown should be safe to call multiple times."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        ext_instance = extension_module.GraphExtension()
        ext_instance._extension_subscription = None
        ext_instance._preference_page = None
        ext_instance._window = None
        ext_instance._ext_name = extension_module.GraphExtension._WINDOW_NAME

        with (
            patch.object(omni.ui.Workspace, "set_show_window_fn"),
            patch.object(extension_module, "cleanup_command_tasks", autospec=True),
            patch.object(extension_module, "remove_preferences_page", autospec=True),
        ):
            ext_instance.on_shutdown()
            ext_instance.on_shutdown()

    async def test_shutdown_deregisters_actions(self) -> None:
        """Shutdown should deregister actions for the extension."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        ext_instance = extension_module.GraphExtension()
        ext_instance._extension_subscription = None
        ext_instance._preference_page = None
        ext_instance._window = None
        ext_instance._ext_name = extension_module.GraphExtension._WINDOW_NAME

        class DummyRegistry:
            """Action registry stub."""

            def __init__(self) -> None:
                self.called = False

            def deregister_all_actions_for_extension(self, _ext_id: str) -> None:
                """Record deregistration."""
                self.called = True

        registry = DummyRegistry()
        with (
            patch.object(omni.ui.Workspace, "set_show_window_fn"),
            patch.object(extension_module, "cleanup_command_tasks", autospec=True),
            patch.object(extension_module, "remove_preferences_page", autospec=True),
            patch("omni.kit.actions.core.get_action_registry", autospec=True, return_value=registry),
        ):
            ext_instance.on_shutdown()
        self.assertTrue(registry.called)

    async def test_shutdown_unregisters_commands(self) -> None:
        """Shutdown should unregister material graph commands."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        ext_instance = extension_module.GraphExtension()
        ext_instance._extension_subscription = None
        ext_instance._preference_page = None
        ext_instance._window = None
        ext_instance._ext_name = extension_module.GraphExtension._WINDOW_NAME

        with (
            patch.object(omni.ui.Workspace, "set_show_window_fn"),
            patch.object(extension_module, "cleanup_command_tasks", autospec=True),
            patch.object(extension_module, "remove_preferences_page", autospec=True),
            patch.object(extension_module, "teardown_all_commands", autospec=True) as unregister_commands,
        ):
            ext_instance.on_shutdown()
            unregister_commands.assert_called_once_with()

    async def test_shutdown_logs_lifecycle_cleanup_errors(self) -> None:
        """Lifecycle cleanup failures should be logged and not stop shutdown."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        ext_instance = extension_module.GraphExtension()
        ext_instance._extension_subscription = None
        ext_instance._preference_page = None
        ext_instance._window = None
        ext_instance._ext_name = extension_module.GraphExtension._WINDOW_NAME

        class DummyLifecycle:
            """Lifecycle registry stub raising on cleanup."""

            def cleanup(self) -> None:
                raise KeyError("boom")

        class DummySettings:
            """Settings stub for logging branch."""

            def get(self, _key: str) -> bool:
                return False

            def set(self, _key: str, _value: object) -> None:
                """Accept settings restored by UI test cleanup."""

        ext_instance._open_graph_lifecycle = DummyLifecycle()
        with (
            patch.object(omni.ui.Workspace, "set_show_window_fn"),
            patch.object(extension_module.carb.settings, "get_settings", return_value=DummySettings()),
            patch.object(extension_module, "log_exception", autospec=True) as log_warn,
            patch.object(extension_module, "cleanup_command_tasks", autospec=True),
            patch.object(extension_module, "remove_preferences_page", autospec=True),
        ):
            ext_instance.on_shutdown()
        log_warn.assert_called()

    async def test_get_extension_warns_after_shutdown(self) -> None:
        """get_extension should warn after shutdown."""
        extension_module = importlib.import_module(f"{Paths.MODULE_ID}.scripts.extension")
        original_extension = extension_module.extension
        original_shutdown = extension_module._extension_shutdown
        original_started = extension_module._extension_started
        try:
            extension_module.extension = None
            extension_module._extension_shutdown = True
            extension_module._extension_started = True
            with patch.object(extension_module.logger, "warning", autospec=True) as log_warn:
                self.assertIsNone(extension_module.get_extension())
            log_warn.assert_called_once_with(
                "Material Graph extension request ignored because extension shutdown has completed"
            )
        finally:
            extension_module.extension = original_extension
            extension_module._extension_shutdown = original_shutdown
            extension_module._extension_started = original_started
