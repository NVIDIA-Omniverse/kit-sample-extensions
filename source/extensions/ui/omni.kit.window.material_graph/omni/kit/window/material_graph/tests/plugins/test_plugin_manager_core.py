# pylint: disable=relative-beyond-top-level,no-member,protected-access
from unittest.mock import patch

from ...scripts.plugins.core import Plugin, PluginManager
from ...scripts.plugins.core import manager as manager_module
from ..base import MaterialGraphTestBase


class _CorePlugin(Plugin):
    """Minimal plugin used to test add_plugin."""

    def __init__(self, load_catalog: bool = True) -> None:
        super().__init__("core", "Core", None, load_catalog=load_catalog)

    def build_catalog_items(self) -> None:
        self._catalog_items.clear()

    def is_supported_prim(self, prim: object) -> bool:
        return False


class TestPluginManagerCore(MaterialGraphTestBase):
    """Core PluginManager API coverage."""

    async def test_add_plugin(self) -> None:
        """add_plugin should add a built-in-compatible plugin."""
        manager = PluginManager(auto_discover=False)
        manager.add_plugin(_CorePlugin)
        self.assertIsNotNone(manager.get_plugin("core"))
        manager.destroy()

    async def test_add_plugin_constructor_failure_is_logged_and_contained(self) -> None:
        """A third-party plugin constructor cannot terminate discovery."""

        class _BrokenPlugin:
            def __init__(self, load_catalog: bool = True) -> None:
                del load_catalog
                raise RuntimeError("plugin startup failed")

        manager = PluginManager(auto_discover=False)
        with patch.object(manager_module, "log_exception") as log_failure:
            manager.add_plugin(_BrokenPlugin)

        self.assertEqual(manager._plugins, {})
        log_failure.assert_called_once()
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], RuntimeError)
        manager.destroy()

    async def test_discover_plugins(self) -> None:
        """discover_plugins should only register built-in plugins."""
        manager = PluginManager(auto_discover=False)
        manager.discover_plugins()
        self.assertIsNotNone(manager.get_plugin("mdl"))
        self.assertIsNotNone(manager.get_plugin("mtlx"))
        self.assertIsNotNone(manager.get_plugin("universal"))
        manager.destroy()

    async def test_get_plugin_definitions_returns_expected_metadata(self) -> None:
        """get_plugin_definitions should expose built-in plugin metadata."""
        definitions = PluginManager.get_plugin_definitions()
        self.assertTrue(definitions)
        names = {entry["name"] for entry in definitions}
        self.assertIn("mdl", names)
        self.assertIn("mtlx", names)
        self.assertIn("universal", names)
        for entry in definitions:
            self.assertIn("display_name", entry)
            self.assertIn("properties", entry)
