from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.plugins.impl.mdl import settings as mdl_settings
from ...scripts.plugins.impl.mdl.plugin import MdlPlugin
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestMdlPaths(MaterialGraphTestBase):
    """MDL path integration with plugin settings subscription."""

    async def setUp(self) -> None:
        """Reset MDL catalog modules before each test."""
        await super().setUp()
        self._settings_key = Settings.get_plugin_property_key(
            mdl_settings.MDL_PLUGIN_NAME, mdl_settings.MDL_CATALOG_MODULES_KEY
        )
        self._original_modules = self._settings.get(self._settings_key) if self._settings_key else None
        if self._settings_key:
            self._settings.set(self._settings_key, [])

    async def tearDown(self) -> None:
        """Restore MDL catalog modules after each test."""
        if self._settings_key:
            self._settings.set(self._settings_key, self._original_modules)
        self._original_modules = None
        self._settings_key = None
        await super().tearDown()

    async def test_mdl_settings_change_triggers_reload(self) -> None:
        """MDL plugin should reload when module list changes."""
        with (
            patch.object(mdl_settings, "_can_resolve_mdl_path", autospec=True, return_value=True),
            patch.object(MdlPlugin, "build_catalog_items", autospec=True, return_value=None),
        ):
            plugin = MdlPlugin(load_catalog=True)
        called: dict[str, int] = {"count": 0}
        plugin.reload = lambda: called.update(count=called["count"] + 1)

        if self._settings_key:
            self._settings.set(self._settings_key, ["a.mdl"])
        await self.wait_n_updates(2)
        self.assertGreaterEqual(called["count"], 1)
        plugin.destroy()

    async def test_invalid_mdl_module_rejected(self) -> None:
        """Invalid MDL module entries should be rejected."""
        with patch(
            f"{Paths.MODULE_ID}.scripts.plugins.impl.mdl.settings.logger.warning",
            autospec=True,
        ) as log_warn:
            mdl_settings.add_mdl_catalog_module("not_a_module.txt")
            value = Settings.get_plugin_property(mdl_settings.MDL_PLUGIN_NAME, mdl_settings.MDL_CATALOG_MODULES_KEY, [])
            self.assertEqual(value, [])
            self.assertTrue(any("invalid MDL module path" in str(call.args[0]) for call in log_warn.call_args_list))

    async def test_mdl_destroy_stops_reload(self) -> None:
        """After destroy, settings change should not trigger reload."""
        with (
            patch.object(mdl_settings, "_can_resolve_mdl_path", autospec=True, return_value=True),
            patch.object(MdlPlugin, "build_catalog_items", autospec=True, return_value=None),
        ):
            plugin = MdlPlugin(load_catalog=True)
        called: dict[str, int] = {"count": 0}
        plugin.reload = lambda: called.update(count=called["count"] + 1)

        plugin.destroy()
        if self._settings_key:
            self._settings.set(self._settings_key, ["b.mdl"])
        await self.wait_n_updates(2)
        self.assertEqual(called["count"], 0)
