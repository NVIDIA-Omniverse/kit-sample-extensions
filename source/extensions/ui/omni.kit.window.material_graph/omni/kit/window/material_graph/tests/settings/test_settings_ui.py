# pylint: disable=relative-beyond-top-level,no-member
from pxr import UsdShade

from ...scripts.settings.ui import (
    confine_backdrops,
    confine_nodegraphs,
    get_render_context,
    get_render_contexts,
    preview_texture_input,
    show_catalog,
)
from ...scripts.settings.utils import (
    CONFINE_BACKDROPS,
    CONFINE_NODEGRAPHS,
    PREVIEW_TEXTURE_INPUT,
    RENDER_CONTEXTS,
    SHOW_CATALOG,
    refresh_settings_prefix,
)
from ..base import MaterialGraphTestBase


class TestSettingsUi(MaterialGraphTestBase):
    """Direct tests for settings UI helpers."""

    async def test_defaults(self) -> None:
        """UI helpers should fall back to expected defaults."""
        for key in (
            SHOW_CATALOG,
            CONFINE_NODEGRAPHS,
            CONFINE_BACKDROPS,
            PREVIEW_TEXTURE_INPUT,
            RENDER_CONTEXTS,
        ):
            self._settings.destroy_item(key)

        self.assertTrue(show_catalog())
        self.assertTrue(confine_nodegraphs())
        self.assertTrue(confine_backdrops())
        self.assertFalse(preview_texture_input())
        self.assertEqual(get_render_context(), "universal")

    async def test_render_context_normalization(self) -> None:
        """Render context list should normalize universal token."""
        self._settings.set(
            RENDER_CONTEXTS,
            [UsdShade.Tokens.universalRenderContext, "mdl"],
        )
        self.assertEqual(get_render_contexts(), ["universal", "mdl"])
        self.assertEqual(get_render_context(), "universal")

    async def test_prefix_switch_affects_reads(self) -> None:
        """Prefix changes should redirect UI setting reads."""
        self._settings.set("/app/isTestRun", True)
        refresh_settings_prefix()
        self._settings.set(SHOW_CATALOG, False)
        self.assertFalse(show_catalog())

        self._settings.set("/app/isTestRun", False)
        refresh_settings_prefix()
        self.assertTrue(show_catalog())
