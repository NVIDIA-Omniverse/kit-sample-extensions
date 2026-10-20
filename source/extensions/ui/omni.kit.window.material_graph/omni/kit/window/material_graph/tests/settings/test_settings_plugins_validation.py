# pylint: disable=relative-beyond-top-level,protected-access
from types import SimpleNamespace
from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.settings.plugins import set_plugin_property_schema
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestSettingsPluginsValidation(MaterialGraphTestBase):
    """Tests for plugin property validation."""

    async def test_allowed_values_validation(self) -> None:
        """Invalid allowed values should be rejected."""
        plugin_name = "validation_plugin"
        set_plugin_property_schema(
            plugin_name,
            [
                SimpleNamespace(
                    key="mode",
                    type="string",
                    default="a",
                    allowed_values=["a", "b"],
                )
            ],
        )
        with patch(
            f"{Paths.MODULE_ID}.scripts.settings.plugins.logger.warning",
            autospec=True,
        ) as log_warn:
            Settings.set_plugin_property(plugin_name, "mode", "c")
            self.assertIsNone(Settings.get_plugin_property(plugin_name, "mode"))
            log_warn.assert_called()

    async def test_type_validation_list(self) -> None:
        """Type validation should reject invalid list values."""
        plugin_name = "validation_plugin_list"
        set_plugin_property_schema(
            plugin_name,
            [
                SimpleNamespace(
                    key="paths",
                    type="string_list",
                    default=[],
                    allowed_values=None,
                )
            ],
        )
        with patch(
            f"{Paths.MODULE_ID}.scripts.settings.plugins.logger.warning",
            autospec=True,
        ) as log_warn:
            Settings.set_plugin_property(plugin_name, "paths", ["a", 5])
            self.assertIsNone(Settings.get_plugin_property(plugin_name, "paths"))
            log_warn.assert_called()
