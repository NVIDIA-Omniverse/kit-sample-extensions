# pylint: disable=relative-beyond-top-level
import carb.settings

from ...scripts.settings import utils
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestSettingsPrefix(MaterialGraphTestBase):
    """Settings prefix refresh behavior."""

    async def test_refresh_settings_prefix_updates_keys(self) -> None:
        """Refreshing the prefix should update settings keys."""
        settings = carb.settings.get_settings()
        original_flag = settings.get("/app/isTestRun")
        try:
            settings.set("/app/isTestRun", True)
            utils.refresh_settings_prefix()
            expected = utils.get_settings_prefix()
            self.assertEqual(utils.SETTINGS_PREFIX, expected)
            self.assertEqual(Settings.SETTINGS_PREFIX, expected)
            self.assertTrue(Settings.FORCE_CONNECT.startswith(expected))

            settings.set("/app/isTestRun", False)
            utils.refresh_settings_prefix()
            expected = utils.get_settings_prefix()
            self.assertEqual(utils.SETTINGS_PREFIX, expected)
            self.assertEqual(Settings.SETTINGS_PREFIX, expected)
            self.assertTrue(Settings.FORCE_CONNECT.startswith(expected))
        finally:
            settings.set("/app/isTestRun", original_flag)
            utils.refresh_settings_prefix()
