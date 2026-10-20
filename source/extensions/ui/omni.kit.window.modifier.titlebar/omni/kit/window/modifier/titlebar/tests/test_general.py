import sys
import unittest

import carb.settings
from omni.ui.tests.test_base import OmniUiTest

from ..extension import ModifierTitleBarExtension as Extension
from ..extension import kWINDOW_COLORS_PATH, kWINDOW_TITLE_FORMAT_PATH
from ..settings import SettingColor, kWINDOW_UISTYLE_PATH


@unittest.skipUnless(sys.platform == "win32", "Windows-only UI tests")
class GeneralTestCase(OmniUiTest):
    """Test custom application window style"""

    # Before running each test
    async def setUp(self, use_region=False):
        await super().setUp()
        # wait for some time to be safe that any undesired tooltip would clean out
        await self.wait_n_updates(30)

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_start_stop(self):
        ext = Extension.get_instance()
        self.assertIsNot(ext, None)

        # Re-startup will be ignored
        ext.startup()
        await self.wait_n_updates(50)
        ext.shutdown()
        await self.wait_n_updates(50)
        ext.startup()
        await self.wait_n_updates(50)

        self.assertTrue("start/stop cycle tested")

    async def test_settings_color(self):
        settings = carb.settings.get_settings()
        self.assertIsNot(settings, None)
        ext = Extension.get_instance()
        self.assertIsNot(ext, None)

        modifier = ext._modifier
        settings.set_string(kWINDOW_UISTYLE_PATH, "NvidiaDark")
        settings_color = SettingColor(kWINDOW_COLORS_PATH, modifier)
        await self.wait_n_updates(10)
        settings_color.destroy()
        settings_color = None
        await self.wait_n_updates(10)

        settings.set_string(kWINDOW_UISTYLE_PATH, "NvidiaLight")
        await self.wait_n_updates(10)
        settings_color = SettingColor(kWINDOW_COLORS_PATH, modifier)
        await self.wait_n_updates(10)
        settings_color.destroy()
        settings_color = None
        self.assertIsNot("SettingsColor test finished", None)

    async def test_change_title(self):
        settings = carb.settings.get_settings()
        self.assertIsNot(settings, None)

        # Backup the original title
        title_backup = settings.get_as_string(kWINDOW_TITLE_FORMAT_PATH)
        self.assertIsNot(title_backup, None)

        # Set a pure text title
        settings.set_string(kWINDOW_TITLE_FORMAT_PATH, "This is pure text title")
        await self.wait_n_updates(10)

        # Bad title fields
        settings.set_string(kWINDOW_TITLE_FORMAT_PATH, "Bad title {text:OMNIVERSE")
        await self.wait_n_updates(10)

        # Title with image
        title_str = "Title with image {image:${omni.kit.window.modifier.titlebar}/data/tests/test_image.bmp}"
        settings.set_string(kWINDOW_TITLE_FORMAT_PATH, title_str)
        await self.wait_n_updates(10)

        # Restore the title
        settings.set_string(kWINDOW_TITLE_FORMAT_PATH, title_backup)
        await self.wait_n_updates(10)

        self.assertIsNot("TitleString changes on-fly tested", None)
