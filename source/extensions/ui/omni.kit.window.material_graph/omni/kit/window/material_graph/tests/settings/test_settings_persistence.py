from ...scripts.plugins.core import PluginProperty
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestSettingsPersistence(MaterialGraphTestBase):
    """Persistence of settings values via carb settings."""

    async def test_show_catalog_persists(self) -> None:
        """Show Catalog should roundtrip through settings."""
        self._settings.set(Settings.SHOW_CATALOG, False)
        self.assertFalse(Settings.show_catalog())
        self._settings.set(Settings.SHOW_CATALOG, True)
        self.assertTrue(Settings.show_catalog())

    async def test_plugin_properties_roundtrip(self) -> None:
        """Plugin property accessors should roundtrip values."""
        key = Settings.get_plugin_property_key("mdl", "outputPorts")
        self.assertIn("plugins/mdl/outputPorts", key)

        Settings.set_plugin_property("mdl", "outputPorts", ["surface"])
        self.assertEqual(Settings.get_plugin_property("mdl", "outputPorts", []), ["surface"])

    async def test_plugin_property_validation_rejects_invalid(self) -> None:
        """Invalid plugin property values should be rejected."""
        Settings.set_plugin_property_schema(
            "test",
            [PluginProperty("enabled", "Enabled", "bool", default=True, allowed_values=[True, False])],
        )
        Settings.set_plugin_property("test", "enabled", "nope")
        self.assertIsNone(Settings.get_plugin_property("test", "enabled", None))
