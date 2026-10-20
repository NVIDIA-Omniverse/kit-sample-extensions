from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestSettingsDefaults(MaterialGraphTestBase):
    """Defaults from extension.toml."""

    async def test_boolean_defaults(self) -> None:
        """Default booleans should match extension.toml."""
        self.assertFalse(Settings.get_force_connect())
        self.assertTrue(Settings.show_catalog())
        self.assertTrue(Settings.confine_nodegraphs())
        self.assertTrue(Settings.confine_backdrops())

    async def test_supported_texture_format_defaults(self) -> None:
        """Supported texture format defaults should match extension.toml."""
        self.assertEqual(
            Settings.get_droppable_texture_formats(),
            ["bmp", "dds", "exr", "gif", "hdr", "jpeg", "jpg", "tif", "png", "psd", "tga"],
        )
