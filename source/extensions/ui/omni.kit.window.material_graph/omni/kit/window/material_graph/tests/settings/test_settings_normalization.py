from unittest.mock import patch

from pxr import UsdShade

from ...scripts.config.paths import Paths
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestSettingsNormalization(MaterialGraphTestBase):
    """Normalization helpers for settings accessors."""

    async def test_get_bool(self) -> None:
        """_get_bool should normalize None/bool/string values."""
        self._settings.set(Settings.SHOW_CATALOG, None)
        self.assertTrue(Settings.show_catalog())

        self._settings.set(Settings.SHOW_CATALOG, False)
        self.assertFalse(Settings.show_catalog())

        self._settings.set(Settings.SHOW_CATALOG, "0")
        self.assertTrue(Settings.show_catalog())

    async def test_get_list(self) -> None:
        """_get_list should normalize None/list/string values."""
        self.assertEqual(Settings._get_list(""), [])
        self.assertEqual(Settings._get_list("missing/key"), [])

        key = Settings.COMPOUND_PATHS
        self._settings.set(key, ["a", "b"])
        self.assertEqual(Settings._get_list(key), ["a", "b"])

        self._settings.set(key, "single")
        self.assertEqual(Settings._get_list(key), ["single"])

        self._settings.set(key, 123)
        self.assertEqual(Settings._get_list(key), [])

    async def test_render_context_normalization(self) -> None:
        """Render contexts should normalize universal token to 'universal'."""
        self._settings.set(Settings.RENDER_CONTEXTS, [UsdShade.Tokens.universalRenderContext, "mdl"])
        self.assertEqual(Settings.get_render_contexts(), ["universal", "mdl"])

    async def test_render_context_fallback(self) -> None:
        """Render context should fall back to 'universal' when empty."""
        self._settings.set(Settings.RENDER_CONTEXTS, [])
        self.assertEqual(Settings.get_render_context(), "universal")

    async def test_invalid_plugin_property_key(self) -> None:
        """Invalid plugin keys should not be written or read."""
        with patch(
            f"{Paths.MODULE_ID}.scripts.settings.plugins.logger.warning",
            autospec=True,
        ) as log_warn:
            value = Settings.get_plugin_property("", "bad/key", default="fallback")
            self.assertEqual(value, "fallback")
            log_warn.assert_called()
